# Turbulence model references

## Modified von Kármán spectrum

Φn(κ) = 0.033·Cn²·exp(−κ²/κm²) / (κ² + κ₀²)^(11/6),
κm = 5.92/l0, κ₀ = 2π/L0.

Source: Andrews & Phillips, "Laser Beam Propagation through Random Media",
2nd ed., SPIE Press (2005), ch. 3 (eq. 3.26 family).

## Tatarskii spectrum

Φn(κ) = 0.033·Cn²·κ^(−11/3)·exp(−κ²/κm²).

Source: Andrews & Phillips (2005), ch. 3.

## Parameter meanings

- Cn²: refractive-index structure constant (m^(−2/3))
- l0: inner scale (m) — dissipation cutoff
- L0: outer scale (m) — energy-input scale

## Phase screen method

FFT-based screens with subharmonics: Lane, Glindemann, Dainty,
"Simulation of a Kolmogorov phase screen", Waves in Random Media 2,
209–224 (1992); also Schmidt (2010) ch. 9.

Thin-layer scaling: the screen variance scales with Δz for a given
spectrum integral (Schmidt 2010 §9.4).

## Scientific integrity notes

- Different spectra (Kolmogorov vs non-Kolmogorov, inner/outer scale
  choices) give different answers — always record WHICH model and WHICH
  parameters produced a result.
- Cn² values are site/altitude dependent; a simulation result is only valid
  for the declared turbulence profile.
