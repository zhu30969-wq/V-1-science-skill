"""Phase topology analysis (spec §25).

  * analyze_phase_winding()           — winding number along a closed contour
  * detect_candidate_singularity()    — branch-point cells in a phase field
  * estimate_topological_charge()     — winding of a large contour around the
                                        support of the field

Winding convention: counterclockwise contour, phase phi, charge
q = (1/2pi) sum of branch-aware phase increments. Tested against known
+1/-1/0 windings, singularities outside the contour and noisy fields.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from stov_scientist.errors import SamplingError, SchemaError


def _wrap(delta: float) -> float:
    """Wrap a phase increment into (-pi, pi]."""
    return (delta + np.pi) % (2 * np.pi) - np.pi


def analyze_phase_winding(
    phase: NDArray,
    contour: NDArray[np.float64],
) -> float:
    """Winding number along a closed contour of pixel coords.

    Accepts either a real phase field (wrapped-phase increments, valid for
    |charge| <= 1 branch cuts) or a COMPLEX field (ratio method
    angle(z[k+1]/z[k]) — exact for arbitrary integer charges, the standard
    argument-principle form).

    ``contour``: (M, 2) array of [row, col] pixel coordinates (closed loop).
    Returns q = (1/2pi) sum of increments (float, ~integer for a valid
    vortex phase). Counterclockwise contours give the positive-charge
    convention (unit-tested: charge +1 -> +1, charge -1 -> -1).

    Raises SamplingError if the contour does not close or samples outside
    the field.
    """
    values = np.asarray(phase)
    contour = np.asarray(contour, dtype=np.float64)
    if contour.ndim != 2 or contour.shape[1] != 2 or contour.shape[0] < 4:
        raise SchemaError("contour must be (M, 2) with M >= 4")
    if not np.allclose(contour[0], contour[-1]):
        raise SamplingError("contour must be closed (first == last point)")
    n_rows, n_cols = values.shape[:2]
    if np.any(contour[:, 0] < 0) or np.any(contour[:, 1] < 0):
        raise SamplingError("contour has negative pixel coordinates")
    if np.any(contour[:, 0] > n_rows - 1) or np.any(contour[:, 1] > n_cols - 1):
        raise SamplingError("contour exceeds field bounds")

    # sample with bilinear interpolation at sub-pixel contour points
    r = np.clip(contour[:, 0], 0, n_rows - 1)
    c = np.clip(contour[:, 1], 0, n_cols - 1)
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    r1 = np.minimum(r0 + 1, n_rows - 1)
    c1 = np.minimum(c0 + 1, n_cols - 1)
    fr = r - r0
    fc = c - c0

    def sample(a: NDArray) -> NDArray:
        return (
            a[r0, c0] * (1 - fr) * (1 - fc)
            + a[r1, c0] * fr * (1 - fc)
            + a[r0, c1] * (1 - fr) * fc
            + a[r1, c1] * fr * fc
        )

    total = 0.0
    if np.iscomplexobj(values):
        z = sample(values)
        for i in range(len(z) - 1):
            total += np.angle(z[i + 1] / z[i])
    else:
        p = sample(values.real)
        for i in range(len(p) - 1):
            total += _wrap(p[i + 1] - p[i])
    return total / (2 * np.pi)


def detect_candidate_singularity(
    phase: NDArray[np.float64],
) -> list[dict[str, float]]:
    """Locate branch points by the sum of wrapped phase differences around
    each 2x2 cell: +1 -> positive vortex candidate, -1 -> negative.

    Returns list of {row, col, charge, reliability} for candidate cells.
    Reliability 1.0 = all four differences unwrapped cleanly.
    """
    phase = np.asarray(phase, dtype=np.float64)
    n_rows, n_cols = phase.shape
    if n_rows < 3 or n_cols < 3:
        raise SamplingError("phase field too small for singularity detection")

    candidates: list[dict[str, float]] = []
    for i in range(n_rows - 1):
        for j in range(n_cols - 1):
            # counterclockwise cell path (E -> N -> W -> S) in (col, row):
            d1 = _wrap(phase[i + 1, j + 1] - phase[i + 1, j])  # east, bottom edge
            d2 = _wrap(phase[i, j + 1] - phase[i + 1, j + 1])  # north, right edge
            d3 = _wrap(phase[i, j] - phase[i, j + 1])  # west, top edge
            d4 = _wrap(phase[i + 1, j] - phase[i, j])  # south, left edge
            s = d1 + d2 + d3 + d4
            if abs(abs(s) - 2 * np.pi) < 1e-9:
                charge = 1.0 if s > 0 else -1.0
                candidates.append(
                    {
                        "row": float(i) + 0.5,
                        "col": float(j) + 0.5,
                        "charge": charge,
                        "reliability": 1.0,
                    }
                )
    return candidates


def estimate_topological_charge(
    phase: NDArray,
    contour: NDArray[np.float64] | None = None,
) -> float:
    """Total topological charge inside a contour (default: field boundary).

    Accepts a real phase field or a complex field (ratio method — exact for
    arbitrary integer charges). Robust to noise: contour winding integrates
    over many samples.
    """
    values = np.asarray(phase)
    if contour is None:
        n_rows, n_cols = values.shape[:2]
        contour = _rectangle_contour(0.5, 0.5, n_rows - 1.5, n_cols - 1.5)
    return analyze_phase_winding(values, contour)


def _rectangle_contour(r0: float, c0: float, r1: float, c1: float) -> NDArray[np.float64]:
    """Counterclockwise rectangle in (col, row) space: E -> N -> W -> S.

    The first array axis (row) plays the analytic y role: for the standard
    vortex phase atan2(row, col), the counterclockwise contour yields the
    positive charge convention (tested: charge +1 -> +1).
    """
    steps = 8 * int(max(r1 - r0, c1 - c0)) + 1
    edge_r = np.linspace(r0, r1, steps)
    edge_c = np.linspace(c0, c1, steps)
    east = np.stack([np.full(steps, r1), edge_c], axis=1)  # bottom edge, E
    north = np.stack([edge_r[::-1], np.full(steps, c1)], axis=1)  # right edge, N
    west = np.stack([np.full(steps, r0), edge_c[::-1]], axis=1)  # top edge, W
    south = np.stack([edge_r, np.full(steps, c0)], axis=1)  # left edge, S
    return np.concatenate([east, north, west, south, east[:1]], axis=0)
