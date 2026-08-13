"""Topology tests (spec §25): +1 / -1 / 0 winding, singularity outside
contour, noisy synthetic field."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.errors import SamplingError, SchemaError
from stov_scientist.physics.topology import (
    analyze_phase_winding,
    detect_candidate_singularity,
    estimate_topological_charge,
)


def make_vortex_phase(n=128, charge=1):
    x = np.linspace(-1, 1, n)
    y = np.linspace(-1, 1, n)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    phase = np.angle((xx + 1j * (1 if charge > 0 else -1) * yy) ** abs(charge))
    return phase


def rectangle_contour(n=128, inset=4):
    """Counterclockwise rectangle in (col, row) space: E -> N -> W -> S."""
    lo, hi = inset, n - 1 - inset
    steps = 16
    edge = np.linspace(lo, hi, steps)
    east = np.stack([np.full(steps, hi), edge], axis=1)  # bottom edge, E
    north = np.stack([edge[::-1], np.full(steps, hi)], axis=1)  # right edge, N
    west = np.stack([np.full(steps, lo), edge[::-1]], axis=1)  # top edge, W
    south = np.stack([edge, np.full(steps, lo)], axis=1)  # left edge, S
    return np.concatenate([east, north, west, south, east[:1]], axis=0)


def test_known_positive_winding():
    phase = make_vortex_phase(charge=1)
    q = analyze_phase_winding(phase, rectangle_contour())
    assert np.isclose(q, 1.0, atol=1e-6)


def test_known_negative_winding():
    phase = make_vortex_phase(charge=-1)
    q = analyze_phase_winding(phase, rectangle_contour())
    assert np.isclose(q, -1.0, atol=1e-6)


def test_zero_winding():
    n = 128
    phase = np.zeros((n, n))
    q = analyze_phase_winding(phase, rectangle_contour())
    assert np.isclose(q, 0.0, atol=1e-9)


def test_singularity_outside_contour_gives_zero():
    phase = make_vortex_phase(charge=1)
    # small contour far from the central singularity
    lo, hi = 10, 30
    steps = 16
    edge = np.linspace(lo, hi, steps)
    top = np.stack([np.full(steps, lo), edge], axis=1)
    right = np.stack([edge, np.full(steps, hi)], axis=1)
    bottom = np.stack([np.full(steps, hi), edge[::-1]], axis=1)
    left = np.stack([edge[::-1], np.full(steps, lo)], axis=1)
    contour = np.concatenate([top, right, bottom, left, top[:1]], axis=0)
    q = analyze_phase_winding(phase, contour)
    assert np.isclose(q, 0.0, atol=1e-6)


def test_noisy_synthetic_field_keeps_winding():
    rng = np.random.default_rng(42)
    x = np.linspace(-1, 1, 128)
    y = np.linspace(-1, 1, 128)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    # complex field with multiplicative phase noise: winding is topological
    noisy_field = (xx + 1j * yy) * np.exp(1j * rng.normal(0, 0.05, size=(128, 128)))
    q = estimate_topological_charge(noisy_field)
    assert abs(q - 1.0) < 0.5


def test_singularity_detection_single_positive():
    phase = make_vortex_phase(charge=1)
    candidates = detect_candidate_singularity(phase)
    assert len(candidates) == 1
    assert candidates[0]["charge"] == 1.0


def test_singularity_detection_negative():
    phase = make_vortex_phase(charge=-1)
    candidates = detect_candidate_singularity(phase)
    assert len(candidates) == 1
    assert candidates[0]["charge"] == -1.0


def test_unclosed_contour_rejected():
    phase = make_vortex_phase()
    contour = rectangle_contour()[:-2]
    with pytest.raises(SamplingError):
        analyze_phase_winding(phase, contour)


def test_bad_contour_shape_rejected():
    phase = make_vortex_phase()
    with pytest.raises(SchemaError):
        analyze_phase_winding(phase, np.ones((5, 3)))


def test_charge_two_vortex():
    # |l| = 2 needs the complex ratio method: the wrapped phase has 2pi
    # branch jumps that wrapped increments cannot see
    x = np.linspace(-1, 1, 128)
    y = np.linspace(-1, 1, 128)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    field = (xx + 1j * yy) ** 2
    q = estimate_topological_charge(field)
    assert np.isclose(q, 2.0, atol=1e-6)
