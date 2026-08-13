"""Tests for the phase screen simulation skill script."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.errors import SolverError
from stov_scientist.physics.turbulence import PhaseScreenGenerator

PARAMS = {"cn2": 1e-14, "l0": 1e-3, "L0": 10.0}


def test_deterministic_seed():
    a = PhaseScreenGenerator(seed=11).generate_phase_screen((64, 64), 5e-3, PARAMS)
    b = PhaseScreenGenerator(seed=11).generate_phase_screen((64, 64), 5e-3, PARAMS)
    assert np.allclose(a, b)


def test_variance_positive_finite():
    screen = PhaseScreenGenerator(seed=1).generate_phase_screen((64, 64), 5e-3, PARAMS)
    assert np.isfinite(screen).all()
    assert 0 < float(np.var(screen)) < 1e3


def test_invalid_cn2_rejected():
    with pytest.raises(SolverError):
        PhaseScreenGenerator(seed=1).generate_phase_screen(
            (64, 64), 5e-3, {"cn2": -1e-14, "l0": 1e-3, "L0": 10.0}
        )


def test_ensemble_members_differ():
    screens = PhaseScreenGenerator(seed=2).generate_ensemble(
        (64, 64), 5e-3, PARAMS, n_screens=3
    )
    assert len(screens) == 3
    assert not np.allclose(screens[0], screens[1])
