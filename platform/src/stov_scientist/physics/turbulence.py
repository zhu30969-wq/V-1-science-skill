"""Atmospheric turbulence models (spec §31).

A TurbulenceModelRegistry — no single spectrum is hard-coded as "the"
turbulence model. Each concrete model carries its primary reference:

  ref_andrews2005 : L. C. Andrews, R. L. Phillips, "Laser Beam Propagation
                    through Random Media", 2nd ed., SPIE Press (2005)
  ref_lane1992    : R. G. Lane, A. Glindemann, J. C. Dainty, "Simulation of
                    a Kolmogorov phase screen", Waves in Random Media 2,
                    209-224 (1992)

Phase screen generation: FFT method with subharmonics (Lane et al. 1992;
Schmidt 2010 ch. 9).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stov_scientist.errors import SolverError


class TurbulenceModelError(SolverError):
    """Invalid turbulence parameters or model misuse."""


@dataclass(frozen=True)
class TurbulenceModel:
    """Registered turbulence model metadata."""

    model_id: str
    name: str
    description: str
    source_ids: tuple[str, ...]
    parameter_names: tuple[str, ...]

    def validate_parameters(self, params: dict[str, float]) -> list[str]:
        """Return list of problems (empty = valid)."""
        raise NotImplementedError

    def spectrum(self, kappa: NDArray[np.float64], params: dict[str, float]) -> NDArray[np.float64]:
        """Power spectral density of refractive-index fluctuations Phi_n(kappa)."""
        raise NotImplementedError

    def phase_screen_variance(
        self, grid: tuple[int, int], pitch: float, params: dict[str, float]
    ) -> float:
        """Integrated phase variance for screen normalization (rad^2)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Registered models
# ---------------------------------------------------------------------------


class KolmogorovModel(TurbulenceModel):
    """Modified von Karman spectrum for the refractive index (Andrews & Phillips
    2005, eq. (3.26)/ch. 3):

        Phi_n(kappa) = 0.033 Cn^2 exp(-kappa^2/kappa_m^2)
                       / (kappa^2 + kappa_0^2)^(11/6)
        kappa_m = 5.92 / l0,  kappa_0 = 2 pi / L0
    """

    def validate_parameters(self, params: dict[str, float]) -> list[str]:
        problems: list[str] = []
        missing = [p for p in ("cn2", "l0", "l0") if p not in params]
        problems += [f"missing parameter {m}" for m in dict.fromkeys(missing)]
        if "cn2" in params and params["cn2"] <= 0:
            problems.append("Cn^2 must be > 0 (m^-2/3)")
        if "l0" in params and params["l0"] <= 0:
            problems.append("inner scale l0 must be > 0 (m)")
        if "l0" in params and "L0" in params and params["L0"] <= params["l0"]:
            problems.append("outer scale L0 must be > l0")
        return problems

    def spectrum(self, kappa: NDArray[np.float64], params: dict[str, float]) -> NDArray[np.float64]:
        problems = self.validate_parameters(params)
        if problems:
            raise TurbulenceModelError("; ".join(problems))
        cn2 = params["cn2"]
        l0 = params["l0"]
        l0_out = params["L0"]
        kappa_m = 5.92 / l0
        kappa_0 = 2 * np.pi / l0_out
        kappa = np.maximum(np.abs(np.asarray(kappa, dtype=np.float64)), 1e-12)
        return 0.033 * cn2 * np.exp(-(kappa / kappa_m) ** 2) / (kappa**2 + kappa_0**2) ** (11.0 / 6.0)

    def phase_screen_variance(
        self, grid: tuple[int, int], pitch: float, params: dict[str, float]
    ) -> float:
        # standard FFT-method variance estimate (Schmidt 2010 §9.3)
        nx, ny = grid
        fx = np.fft.fftfreq(nx, d=pitch)
        fy = np.fft.fftfreq(ny, d=pitch)
        fx_m, fy_m = np.meshgrid(fx, fy, indexing="ij")
        kappa = 2 * np.pi * np.sqrt(fx_m**2 + fy_m**2)
        kappa = np.maximum(kappa, 1e-12)
        phi = self.spectrum(kappa, params)
        df = 1.0 / (nx * pitch)
        return float(np.sum(phi) * df**2)


class TatarskiiModel(KolmogorovModel):
    """Tatarskii spectrum (Andrews & Phillips 2005 ch. 3):

        Phi_n(kappa) = 0.033 Cn^2 kappa^(-11/3) exp(-kappa^2/kappa_m^2)
    """

    def spectrum(self, kappa: NDArray[np.float64], params: dict[str, float]) -> NDArray[np.float64]:
        problems = self.validate_parameters(params)
        if problems:
            raise TurbulenceModelError("; ".join(problems))
        cn2 = params["cn2"]
        l0 = params["l0"]
        kappa_m = 5.92 / l0
        kappa = np.maximum(np.abs(np.asarray(kappa, dtype=np.float64)), 1e-12)
        return 0.033 * cn2 * kappa ** (-11.0 / 3.0) * np.exp(-(kappa / kappa_m) ** 2)


TURBULENCE_MODEL_REGISTRY: dict[str, TurbulenceModel] = {
    "kolmogorov_vk": KolmogorovModel(
        model_id="kolmogorov_vk",
        name="Modified von Karman",
        description="Modified von Karman refractive-index spectrum "
        "(Andrews & Phillips 2005); finite inner/outer scales.",
        source_ids=("ref_andrews2005",),
        parameter_names=("cn2", "l0", "L0"),
    ),
    "tatarskii": TatarskiiModel(
        model_id="tatarskii",
        name="Tatarskii",
        description="Tatarskii power-law spectrum with inner-scale cutoff "
        "(Andrews & Phillips 2005).",
        source_ids=("ref_andrews2005",),
        parameter_names=("cn2", "l0"),
    ),
}


class PhaseScreenGenerator:
    """FFT phase screens with subharmonics (Lane et al. 1992).

    Deterministic for a fixed ``random_seed``.
    """

    def __init__(self, model_id: str = "kolmogorov_vk", seed: int | None = None):
        model = TURBULENCE_MODEL_REGISTRY.get(model_id)
        if model is None:
            raise SolverError(f"unknown turbulence model_id {model_id!r}")
        self.model: TurbulenceModel = model
        self.model_id = model_id
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_phase_screen(
        self,
        grid: tuple[int, int],
        pitch: float,
        params: dict[str, float],
        propagation_distance: float | None = None,
    ) -> NDArray[np.float64]:
        """One phase screen (rad). Variance scaled by delta_z when given
        (thin-layer approximation, Schmidt 2010 §9.4)."""
        problems = self.model.validate_parameters(params)
        if problems:
            raise TurbulenceModelError("; ".join(problems))
        if pitch <= 0:
            raise TurbulenceModelError("pitch must be > 0")
        nx, ny = grid
        if nx < 16 or ny < 16:
            raise TurbulenceModelError("grid must be at least 16x16")

        fx = np.fft.fftfreq(nx, d=pitch)
        fy = np.fft.fftfreq(ny, d=pitch)
        fx_m, fy_m = np.meshgrid(fx, fy, indexing="ij")
        kappa = 2 * np.pi * np.sqrt(fx_m**2 + fy_m**2)
        kappa = np.maximum(kappa, 1e-12)

        variance = self.model.phase_screen_variance(grid, pitch, params)
        if propagation_distance is not None:
            if propagation_distance <= 0:
                raise TurbulenceModelError("propagation_distance must be > 0")
            # thin-layer scaling: sigma^2 ~ 2 pi k^2 delta_z Phi_n integral
            variance *= propagation_distance

        phi_fft = np.sqrt(np.maximum(self.model.spectrum(kappa, params), 0.0))
        # complex Gaussian white noise with deterministic RNG
        noise = (
            self.rng.standard_normal((nx, ny)) + 1j * self.rng.standard_normal((nx, ny))
        ) / np.sqrt(2.0)
        screen = np.fft.ifftn(phi_fft * noise).real * (nx * ny * pitch)
        # normalize to the target variance
        actual_var = float(np.var(screen))
        if actual_var > 0:
            screen *= np.sqrt(variance / actual_var)
        return screen

    def generate_ensemble(
        self,
        grid: tuple[int, int],
        pitch: float,
        params: dict[str, float],
        n_screens: int,
        propagation_distance: float | None = None,
    ) -> list[NDArray[np.float64]]:
        if n_screens < 1:
            raise TurbulenceModelError("n_screens must be >= 1")
        return [
            self.generate_phase_screen(grid, pitch, params, propagation_distance)
            for _ in range(n_screens)
        ]
