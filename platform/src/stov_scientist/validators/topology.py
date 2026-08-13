"""Topology validation (spec §25): phase winding, candidate singularities,
topological charge estimation. Deterministic NumPy only — no LLM."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from stov_scientist.physics.topology import (
    detect_candidate_singularity,
    estimate_topological_charge,
)
from stov_scientist.schemas import ValidationLevel, ValidationResult


def validate_topological_charge(
    phase: NDArray,
    expected_charge: int,
    contour: NDArray[np.float64] | None = None,
    tolerance: float = 0.5,
    check_id: str = "topology-charge",
) -> ValidationResult:
    """Compare the measured winding against a declared expected charge.

    Accepts a real phase field (wrapped-increment method, |charge| <= 1)
    or a COMPLEX field (ratio method — exact for arbitrary charges)."""
    measured = estimate_topological_charge(phase, contour)
    passed = bool(abs(measured - expected_charge) <= tolerance)
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.TOPOLOGY,
        name="topological charge winding check",
        passed=passed,
        message=(
            f"measured charge {measured:+.3f} vs expected {expected_charge:+d} "
            f"(tolerance {tolerance})"
        ),
        details={"measured_charge": float(measured), "expected_charge": expected_charge},
    )


def validate_singularity_detection(
    phase: NDArray[np.float64],
    expected_singularities: int,
    expected_charge_sum: int,
    check_id: str = "topology-singularities",
) -> ValidationResult:
    """Cell-wise branch-point detection must match the declared vortex content."""
    candidates = detect_candidate_singularity(phase)
    charge_sum = sum(c["charge"] for c in candidates)
    n_ok = len(candidates) == expected_singularities
    sum_ok = round(charge_sum) == expected_charge_sum
    passed = n_ok and sum_ok
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.TOPOLOGY,
        name="singularity cell detection",
        passed=passed,
        message=(
            f"detected {len(candidates)} singularities (charge sum {charge_sum:+.0f}); "
            f"expected {expected_singularities} singularities, total charge {expected_charge_sum:+d}"
        ),
        details={
            "detected_count": len(candidates),
            "detected_charge_sum": float(charge_sum),
            "candidates": candidates,
        },
    )


def validate_winding_noise_robustness(
    phase: NDArray[np.float64],
    contour: NDArray[np.float64] | None = None,
    expected_charge: int = 0,
    check_id: str = "topology-noise",
) -> ValidationResult:
    """Winding on a noisy field: charge estimate must still round to the
    expected integer (winding is a topological, not metric, observable)."""
    noisy = phase + np.random.default_rng(0).normal(0, 0.05, size=phase.shape)
    measured = estimate_topological_charge(noisy, contour)
    passed = bool(abs(measured - expected_charge) <= 0.5)
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.TOPOLOGY,
        name="winding robustness under phase noise (sigma=0.05 rad)",
        passed=passed,
        message=f"noisy measured charge {measured:+.3f} vs expected {expected_charge:+d}",
        details={"measured_charge": float(measured)},
    )
