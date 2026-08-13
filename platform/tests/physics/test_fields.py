"""Physics field tests (spec §67). No LLM calls."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.errors import SchemaError
from stov_scientist.physics.fields import (
    gaussian_envelope,
    make_axis,
    plane_wave_xt,
    spatial_vortex,
    stov_vortex,
)


def make_xt(n=128, half=2e-3):
    x = make_axis(0.0, half, n)
    t = make_axis(0.0, 2e-12, n)
    return x, t


# ---------------------------------------------------------------------------
# Gaussian envelope
# ---------------------------------------------------------------------------


def test_gaussian_envelope_shape_and_peak():
    x, t = make_xt()
    field = gaussian_envelope({"x": x, "t": t}, {"x": 1e-3, "t": 1e-12})
    assert field.values.shape == (len(x), len(t))
    assert np.isclose(field.energy() > 0, True)
    # even n: the grid does not contain exactly (0,0), so the sampled peak
    # is exp(-(dx/2)^2 / w^2) slightly below 1
    assert np.isclose(np.abs(field.values).max(), 1.0, atol=1e-2)


def test_gaussian_limiting_case_wide_widths():
    """Limiting case: widths -> inf give a constant field."""
    x, t = make_xt(64)
    field = gaussian_envelope({"x": x, "t": t}, {"x": 1e6, "t": 1e6})
    assert np.allclose(field.values, 1.0, atol=1e-8)


def test_gaussian_missing_width_rejected():
    x, _ = make_xt()
    with pytest.raises(SchemaError):
        gaussian_envelope({"x": x}, {"t": 1e-12})


# ---------------------------------------------------------------------------
# STOV vortex
# ---------------------------------------------------------------------------


def test_stov_vortex_limiting_axes():
    """t -> 0: imaginary part -> 0; x -> 0: real part -> 0.

    The even grid does not sample exactly x=0/t=0, so the assertion is
    stated at the grid resolution: residuals must be bounded by the
    nearest-sample offsets, and the sign structure must follow the
    analytic form (imag sign = sign(t) at fixed positive x)."""
    x, t = make_xt()
    field = stov_vortex(x, t, 1e-3, 1e-12, charge=1)
    ix = int(np.argmin(np.abs(x)))
    it = int(np.argmin(np.abs(t)))
    # at the row nearest t=0, |imag| <= c0*|t| (envelope <= 1)
    c0 = 299_792_458.0
    assert np.abs(field.values[:, it].imag).max() <= c0 * abs(t[it]) * 1.01 + 1e-15
    # at the column nearest x=0, |real| <= |x| (envelope <= 1)
    assert np.abs(field.values[ix, :].real).max() <= abs(x[ix]) * 1.01 + 1e-15
    # sign structure at fixed positive x: imag follows sign(t)
    pos_x = int(np.where(x > 0)[0][0])
    imag_row = field.values[pos_x, :].imag
    assert imag_row[np.argmax(t)] > 0
    assert imag_row[np.argmin(t)] < 0


def test_stov_vortex_charge_zero_is_gaussian():
    x, t = make_xt()
    vortex = stov_vortex(x, t, 1e-3, 1e-12, charge=0)
    gauss = gaussian_envelope({"x": x, "t": t}, {"x": 1e-3, "t": 1e-12})
    assert np.allclose(vortex.values, gauss.values)


def test_stov_vortex_negative_charge_conjugates():
    x, t = make_xt()
    plus = stov_vortex(x, t, 1e-3, 1e-12, charge=1)
    minus = stov_vortex(x, t, 1e-3, 1e-12, charge=-1)
    assert np.allclose(minus.values, np.conj(plus.values))


def test_spatial_vortex_standard_form():
    x, t = make_xt(64)
    field = spatial_vortex(x, t, 1e-3, 1e-12, charge=1)
    mid = len(t) // 2
    assert np.allclose(field.values[:, mid].imag, 0.0, atol=1e-12)


# ---------------------------------------------------------------------------
# plane wave + normalization
# ---------------------------------------------------------------------------


def test_plane_wave_zero_frequency_is_unit_field():
    x, t = make_xt(64)
    field = plane_wave_xt(x, t, kx=0.0, omega0=0.0)
    assert np.allclose(field.values, 1.0)


def test_plane_wave_phase_gradient_matches_k():
    x, t = make_xt(64)
    kx = 1e3
    field = plane_wave_xt(x, t, kx=kx, omega0=0.0)
    phase_grad = np.gradient(field.phase(), field.spacing("x"), axis=0)
    assert np.allclose(phase_grad, kx, atol=1e-6)


def test_normalization_unit_energy():
    x, t = make_xt(64)
    field = stov_vortex(x, t, 1e-3, 1e-12, charge=1).normalized()
    assert np.isclose(field.energy(), 1.0)
