"""Tests for the topology analysis skill script (spec: scripts/ => tests/)."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.physics.fields import make_axis, stov_vortex
from stov_scientist.physics.topology import estimate_topological_charge


def _phase(n=128, charge=1):
    x = make_axis(0.0, 3e-3, n)
    t = make_axis(0.0, 3e-12, n)
    return stov_vortex(x, t, 1e-3, 1e-12, charge=charge).phase()


def test_charge_plus_one():
    assert abs(estimate_topological_charge(_phase(charge=1)) - 1.0) < 0.5


def test_charge_minus_one():
    assert abs(estimate_topological_charge(_phase(charge=-1)) + 1.0) < 0.5


def test_charge_zero():
    assert abs(estimate_topological_charge(np.zeros((64, 64)))) < 0.5


def test_charge_two():
    assert abs(estimate_topological_charge(_phase(charge=2)) - 2.0) < 0.5
