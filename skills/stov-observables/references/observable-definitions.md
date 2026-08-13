# Observable definitions

## Intensity and phase (Goodman 2017 §2)

I = |E|², φ = arg(E). All numerical derivatives use finite differences on
the field grid; phase unwrapping is avoided — winding uses branch-aware
increments instead.

## Centroid

⟨a⟩ = Σ a·|E|² / Σ |E|² along each axis (intensity-weighted first moment).

## Local frequencies

ω_inst(t) = ∂φ/∂t (instantaneous frequency); k_x(x) = ∂φ/∂x (local
wavenumber). Careful: np.angle wraps at ±π — large gradients are unreliable
near branch points.

## Spectral density

|U(ω)|² from the temporal FFT (convention `ft_time_exp_pos`).

## Topological charge (Chong et al. 2020)

q = (1/2π)∮ dφ — winding of the (x, t) phase around the singularity.
A topological (integer, noise-robust) observable.

## Transverse OAM moment — CANDIDATE_MODEL

L_y ∝ ∫∫ (x·∂φ/∂t − t·∂φ/∂x)·|E|² dx dt (Bliokh & Nori 2012). The
prefactor and normalization depend on the carrier/envelope conventions and
are NOT validated in this platform. Use the winding-based charge proxy for
validated statements; treat OAM moments as exploratory.

## Sources

- Chong et al., Nature Photonics 14, 350 (2020)
- Bliokh & Nori, Phys. Rev. A 86, 033824 (2012)
- Goodman, Introduction to Fourier Optics, 4th ed. (2017)
