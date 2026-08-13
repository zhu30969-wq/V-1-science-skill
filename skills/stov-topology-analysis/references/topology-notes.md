# Topology analysis notes

## Winding number definition

q = (1/2π) ∮ ∇φ · dl — for a closed contour C. Discretized with branch-aware
wrapped increments (each increment wrapped to (−π, π]).

For the STOV charge +1 vortex (φ = atan2(t, x)), q = +1 counterclockwise in
the (x, t) plane (Chong et al. 2020).

## Cell-level singularity detection

Around each 2×2 cell, the sum of wrapped phase differences is
±2π exactly at a branch point (modulo sampling): +2π → charge +1 candidate,
−2π → charge −1 candidate.

## Noise robustness

Winding is a topological invariant: adding phase noise with σ ≪ π changes
the phase locally but the winding integral is unchanged as long as the
contour avoids the singularity and the noise does not create/annihilate
vortex pairs across the contour (standard homotopy argument).

## Sampling caveat

If the vortex core is unresolved (grid spacing comparable to the core
scale), cell detection fails — see `stov-optical-sampling` and
`stov-numerical-convergence` skills. Charge estimates must be reported
together with the grid resolution and the convergence result.

## Sources

- Chong et al., Nature Photonics 14, 350 (2020)
- Goodman, Introduction to Fourier Optics, 4th ed. (2017), §5.5 (vortex phase)
