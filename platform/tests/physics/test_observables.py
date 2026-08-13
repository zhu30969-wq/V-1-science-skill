"""Observable extraction tests (spec §67)."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.errors import SchemaError
from stov_scientist.physics.fields import make_axis, stov_vortex
from stov_scientist.physics.observables import (
    centroid,
    extract,
    instantaneous_frequency,
    on_axis_spectral_density,
    transverse_oam_moment_xt,
    transverse_oam_proxy,
)


def make_field(n=128, charge=1):
    x = make_axis(0.0, 2e-3, n)
    t = make_axis(0.0, 2e-12, n)
    return stov_vortex(x, t, 1e-3, 1e-12, charge=charge)


def test_intensity_nonnegative_and_peak_positive():
    field = make_field()
    obs = extract(field)
    assert np.all(field.intensity() >= 0)
    assert obs.peak_intensity > 0


def test_centroid_at_origin_for_symmetric_field():
    field = make_field()
    c = centroid(field)
    assert abs(c["x"]) < field.spacing("x") / 2
    assert abs(c["t"]) < field.spacing("t") / 2


def test_topological_charge_proxy_matches_declared_charge():
    for charge in (+1, -1, +2):
        field = make_field(charge=charge)
        obs = extract(field)
        assert abs(obs.topological_charge - charge) < 0.5


def test_transverse_oam_moment_sign_tracks_charge():
    plus = transverse_oam_moment_xt(make_field(charge=1))
    minus = transverse_oam_moment_xt(make_field(charge=-1))
    assert plus > 0 and minus < 0  # CANDIDATE_MODEL observable, sign test only


def test_instantaneous_frequency_requires_t_axis():
    field = make_field()
    freq = instantaneous_frequency(field)
    assert freq.shape == field.values.shape


def test_spectral_density_peaks_at_zero_for_gaussian():
    field = make_field(charge=0)
    freqs, density = on_axis_spectral_density(field, "t")
    peak = freqs[np.argmax(density)]
    assert np.isclose(peak, 0.0, atol=1e-12)


def test_oam_proxy_rejects_non_xt_field():
    x = make_axis(0.0, 1e-3, 64)
    y = make_axis(0.0, 1e-3, 64)
    from stov_scientist.physics.fields import spatial_vortex

    field = spatial_vortex(x, y, 5e-4, 5e-4, charge=1)
    with pytest.raises(SchemaError):
        transverse_oam_proxy(field)
