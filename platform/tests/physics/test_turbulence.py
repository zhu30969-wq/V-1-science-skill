"""Turbulence model tests (spec §31, §67): parameter validation, spectrum,
deterministic seeds, ensemble generation."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.errors import SolverError
from stov_scientist.physics.turbulence import (
    TURBULENCE_MODEL_REGISTRY,
    PhaseScreenGenerator,
)

PARAMS = {"cn2": 1e-14, "l0": 1e-3, "L0": 10.0}


def test_registry_contains_multiple_models():
    """Not a single hard-coded spectrum: the registry has alternatives."""
    assert "kolmogorov_vk" in TURBULENCE_MODEL_REGISTRY
    assert "tatarskii" in TURBULENCE_MODEL_REGISTRY
    assert len(TURBULENCE_MODEL_REGISTRY) >= 2


def test_parameter_validation():
    model = TURBULENCE_MODEL_REGISTRY["kolmogorov_vk"]
    assert model.validate_parameters(PARAMS) == []
    problems = model.validate_parameters({"cn2": -1.0, "l0": 1e-3, "L0": 10.0})
    assert any("Cn^2" in p for p in problems)
    problems = model.validate_parameters({"cn2": 1e-14, "l0": 1e-3, "L0": 1e-4})
    assert any("L0" in p for p in problems)


def test_spectrum_positive_and_decays():
    model = TURBULENCE_MODEL_REGISTRY["kolmogorov_vk"]
    kappa = np.logspace(-3, 5, 100)
    phi = model.spectrum(kappa, PARAMS)
    assert np.all(phi > 0)
    # von Karman: flat low-kappa plateau (outer scale), kappa^-11/3 inertial
    # range, then the exponential inner-scale cutoff — monotonically
    # non-increasing overall
    assert np.all(np.diff(phi) <= 0.0)
    # exponential cutoff: high-kappa tail decays far faster than the
    # power law would
    assert phi[-1] < phi[-10] / 10


def test_unknown_model_rejected():
    with pytest.raises(SolverError):
        PhaseScreenGenerator(model_id="not_a_model")


def test_phase_screen_deterministic_with_seed():
    gen1 = PhaseScreenGenerator(seed=7)
    gen2 = PhaseScreenGenerator(seed=7)
    s1 = gen1.generate_phase_screen((64, 64), 5e-3, PARAMS)
    s2 = gen2.generate_phase_screen((64, 64), 5e-3, PARAMS)
    assert np.allclose(s1, s2)


def test_phase_screen_different_seeds_differ():
    s1 = PhaseScreenGenerator(seed=1).generate_phase_screen((64, 64), 5e-3, PARAMS)
    s2 = PhaseScreenGenerator(seed=2).generate_phase_screen((64, 64), 5e-3, PARAMS)
    assert not np.allclose(s1, s2)


def test_phase_screen_variance_positive_and_finite():
    screen = PhaseScreenGenerator(seed=0).generate_phase_screen((64, 64), 5e-3, PARAMS)
    assert np.isfinite(screen).all()
    assert float(np.var(screen)) > 0


def test_phase_screen_invalid_params_rejected():
    with pytest.raises(SolverError):
        PhaseScreenGenerator(seed=0).generate_phase_screen(
            (64, 64), 5e-3, {"cn2": -1.0, "l0": 1e-3, "L0": 10.0}
        )


def test_ensemble_generation():
    screens = PhaseScreenGenerator(seed=3).generate_ensemble(
        (64, 64), 5e-3, PARAMS, n_screens=4
    )
    assert len(screens) == 4
    assert all(s.shape == (64, 64) for s in screens)


def test_tiny_grid_rejected():
    with pytest.raises(SolverError):
        PhaseScreenGenerator(seed=0).generate_phase_screen((4, 4), 5e-3, PARAMS)
