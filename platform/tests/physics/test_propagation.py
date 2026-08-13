"""Propagation tests (spec §67): FFT round trip, vacuum translation,
energy conservation, evanescent handling, alias warnings."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.errors import SchemaError, SolverError
from stov_scientist.physics.fields import gaussian_envelope, make_axis, stov_vortex
from stov_scientist.physics.propagation import (
    AngularSpectrumPropagator,
    FresnelPropagator,
    SplitStepConfig,
    SplitStepPropagator,
)


def make_xt_field(n=128):
    x = make_axis(0.0, 2e-3, n)
    t = make_axis(0.0, 2e-12, n)
    return stov_vortex(x, t, 1e-3, 1e-12, charge=1)


def make_xy_field(n=128, wavelength=800e-9):
    x = make_axis(0.0, 1e-3, n)
    y = make_axis(0.0, 1e-3, n)
    return gaussian_envelope({"x": x, "y": y}, {"x": 2e-4, "y": 2e-4})


# ---------------------------------------------------------------------------
# FFT round trip
# ---------------------------------------------------------------------------


def test_fft_round_trip_identity():
    """FFT+IFFT returns the original field (forward/inverse consistency)."""
    field = make_xt_field(64)
    recovered = np.fft.ifftn(np.fft.fftn(field.values))
    assert np.allclose(recovered, field.values, atol=1e-12)


# ---------------------------------------------------------------------------
# angular spectrum
# ---------------------------------------------------------------------------


def test_angular_spectrum_zero_distance_identity():
    field = make_xt_field(64)
    result = AngularSpectrumPropagator().propagate_spatiotemporal(field, z=0.0)
    assert np.allclose(result.field.values, field.values, atol=1e-12)


def test_vacuum_temporal_envelope_translation():
    """In vacuum kz(omega) is linear near axis: a Gaussian temporal
    envelope must translate rigidly, not spread (no vacuum GVD)."""
    n = 128
    x = make_axis(0.0, 2e-3, n)
    t = make_axis(0.0, 3e-12, n)
    # narrow in kx: plane-wave-like pulse so the vacuum dispersion is linear
    field = gaussian_envelope({"x": x, "t": t}, {"x": 4e-3, "t": 5e-13})
    z = 0.02
    carrier = 2 * np.pi * 299_792_458.0 / 800e-9
    result = AngularSpectrumPropagator().propagate_spatiotemporal(
        field, z, carrier_omega=carrier
    )
    # translate by z/c
    shift = z / 299_792_458.0
    dt = field.spacing("t")
    n_shift = round(shift / dt)
    # compare envelope after compensating the translation
    src = np.abs(field.values)
    dst = np.abs(result.field.values)
    src_shifted = np.roll(src, n_shift, axis=1) if n_shift > 0 else src
    # normalized cross-correlation peak should be near 1
    src_norm = src_shifted / np.sqrt((src_shifted**2).sum())
    dst_norm = dst / np.sqrt((dst**2).sum())
    corr = np.correlate(src_norm.ravel(), dst_norm.ravel(), mode="full")
    assert float(corr.max()) > 0.99


def test_energy_conservation_vacuum():
    field = make_xt_field(128)
    before = field.energy()
    carrier = 2 * np.pi * 299_792_458.0 / 800e-9
    result = AngularSpectrumPropagator().propagate_spatiotemporal(
        field, z=0.01, carrier_omega=carrier
    )
    after = result.field.energy()
    assert np.isclose(before, after, rtol=1e-4)


def test_evanescent_components_damped():
    """Backward-propagating components are impossible: no growth."""
    field = make_xt_field(64)
    result = AngularSpectrumPropagator().propagate_spatiotemporal(field, z=0.01)
    assert result.field.energy() <= field.energy() * (1 + 1e-9)


def test_negative_distance_rejected():
    field = make_xt_field(64)
    with pytest.raises(SolverError):
        AngularSpectrumPropagator().propagate_spatiotemporal(field, z=-1.0)


def test_wrong_axes_rejected():
    field = make_xy_field(64)
    with pytest.raises(SchemaError):
        AngularSpectrumPropagator(wavelength=800e-9).propagate_spatiotemporal(field, z=0.01)


def test_spatial_gaussian_diffraction_sanity():
    """A Gaussian beam spreads under propagation (diffraction sanity check)."""
    field = make_xy_field(128)
    z = 0.2
    result = AngularSpectrumPropagator(wavelength=800e-9).propagate_spatial(field, z)
    src_sigma = np.sqrt(np.sum(field.intensity() * np.meshgrid(field.axis("x"), field.axis("y"), indexing="ij")[0] ** 2) / field.energy())
    dst_sigma = np.sqrt(
        np.sum(
            result.field.intensity()
            * np.meshgrid(result.field.axis("x"), result.field.axis("y"), indexing="ij")[0] ** 2
        )
        / result.field.energy()
    )
    assert dst_sigma >= src_sigma


def test_alias_free_warning():
    """Propagating beyond the Voelz alias-free bound warns."""
    n = 64
    x = make_axis(0.0, 1e-3, n)
    y = make_axis(0.0, 1e-3, n)
    field = gaussian_envelope({"x": x, "y": y}, {"x": 2e-4, "y": 2e-4})
    dx = field.spacing("x")
    zmax = n * dx**2 / 800e-9
    result = AngularSpectrumPropagator(wavelength=800e-9).propagate_spatial(
        field, z=zmax * 5
    )
    assert any("alias-free" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Fresnel
# ---------------------------------------------------------------------------


def test_fresnel_zero_distance_identity():
    field = make_xy_field(64)
    result = FresnelPropagator(wavelength=800e-9).propagate_spatial(field, z=0.0)
    assert np.allclose(result.field.values, field.values, atol=1e-12)


def test_fresnel_paraxial_matches_angular_spectrum():
    """For small angles the paraxial result approximates the full solution."""
    n = 128
    x = make_axis(0.0, 1.5e-3, n)
    y = make_axis(0.0, 1.5e-3, n)
    field = gaussian_envelope({"x": x, "y": y}, {"x": 4e-4, "y": 4e-4})
    z = 0.1
    fresnel = FresnelPropagator(wavelength=800e-9).propagate_spatial(field, z)
    full = AngularSpectrumPropagator(wavelength=800e-9).propagate_spatial(field, z)
    overlap = np.abs(
        np.vdot(fresnel.field.values, full.field.values)
    ) / np.sqrt(fresnel.field.energy() * full.field.energy())
    assert float(overlap) > 0.95


# ---------------------------------------------------------------------------
# split-step
# ---------------------------------------------------------------------------


def test_split_step_linear_matches_single_shot():
    """Split-step with no nonlinearity must equal the linear propagator."""
    field = make_xt_field(128)
    z = 0.01
    linear = AngularSpectrumPropagator().propagate_spatiotemporal(field, z)
    split = SplitStepPropagator(
        SplitStepConfig(
            linear_propagator=AngularSpectrumPropagator(),
            n_steps=10,
        )
    ).propagate(field, z)
    assert np.allclose(split.field.values, linear.field.values, atol=1e-12)


def test_split_step_rejects_nonpositive_steps():
    with pytest.raises(SchemaError):
        SplitStepConfig(linear_propagator=AngularSpectrumPropagator(), n_steps=0)


def test_sampling_rejection_nonpositive_spacing():
    """Sampling validation rejects zero spacing before propagation."""
    from stov_scientist.schemas import ConvergencePlan, GridSpec, SimulationSpec

    spec = SimulationSpec(
        simulation_id="sim-bad",
        model_id="model-x",
        domain="free space",
        grid=GridSpec(
            grid_id="g-bad",
            kind="x-t",
            axes=["x", "t"],
            shape=[64, 64],
            spacing={"x": 0.0, "t": 1e-14},
            domain_extent={"x": 0.0, "t": 64e-14},
        ),
        parameters={},
        convergence_plan=ConvergencePlan(
            strategy="GRID_REFINEMENT",
            refinement_levels=[0, 1],
            target_observable="energy",
            acceptance_rule="r1",
        ),
    )
    from stov_scientist.validators.sampling import validate_sampling

    result, report = validate_sampling(spec)
    assert not result.passed
    assert not report.usable_for_conclusions
