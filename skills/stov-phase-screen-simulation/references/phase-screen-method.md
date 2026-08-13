# Phase screen method

## FFT method (Lane et al. 1992)

φ(x, y) = IFFT[ √Φn(κ)·H(κ) ] with H complex unit-variance Gaussian noise
per frequency cell; the real part forms the screen. The variance is
normalized to the analytic integral σ² = ∫∫ Φn d²κ (thin-layer: × Δz).

## Subharmonics

Low spatial frequencies (large eddies) are undersampled by the FFT grid;
Lane et al. (1992) add subharmonic screens. **Status in this platform**:
base FFT method implemented and unit-tested; subharmonic augmentation is a
known limitation (see BUILD_REPORT).

## Determinism and reproducibility

The platform uses numpy's PCG64 via `np.random.default_rng(seed)` — every
screen is reproducible from (model_id, params, grid, pitch, seed).

## Sources

- Lane, Glindemann, Dainty, Waves in Random Media 2, 209–224 (1992)
- Schmidt, Numerical Simulation of Optical Wave Propagation (2010), ch. 9
- Andrews & Phillips (2005), ch. 3
