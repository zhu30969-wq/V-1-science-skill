# STOV field forms

## Linear STOV vortex ansatz (Chong et al. 2020)

E(x, t) = (x + i·sgn(l)·t)^|l| · exp(−x²/wx² − t²/wt²)

- Phase for |l| = 1: φ = atan2(sgn(l)·t, x)
- The singularity sits at (x=0, t=0) — a phase singularity in the (x, t) plane.
- The Gaussian envelope localizes the vortex in space AND time — this is what
  distinguishes a STOV from a spatial vortex: the singularity lives in the
  spatiotemporal plane, and transverse OAM lies along y.

Source: A. Chong, C. Wan, J. Chen, Q. Zhan, Nature Photonics 14, 350 (2020),
DOI: 10.1038/s41566-020-0627-8.

## Standard spatial OAM vortex

E(x, y) = (x + i·sgn(l)·y)^|l| · exp(−x²/wx² − y²/wy²)

Source: Goodman 2017 (standard OAM construction), §5.5.

## Gaussian beam parameters (Goodman 2017 §3.3)

zR = π·w0²/λ (Rayleigh range); divergence half-angle θ = λ/(π·w0).

## Provenance chain (spec §20)

For each field form the platform requires:
primary source → reference record → convention → transcription →
unit/dimension check → limiting case → unit test → production use.

Forms failing any step are CANDIDATE_MODEL, not validated models.
