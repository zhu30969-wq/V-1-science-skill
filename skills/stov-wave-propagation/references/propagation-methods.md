# Propagation methods

## Angular spectrum (Goodman 2017 §3.10)

U(fx, fy; z) = U(fx, fy; 0)·exp(i·kz·z), kz = √(k² − kx² − ky²).
Transfer function exactly solves the Helmholtz equation for forward
propagation; evanescent components (kz² < 0) decay.

Spatiotemporal variant: kz(ω) = √((ω/c)² − kx²). On axis (kx = 0):
kz = ω/c → linear dispersion → rigid translation in vacuum (no GVD).

## Fresnel paraxial (Goodman 2017 §4.1)

H(fx, fy) = exp(ikz)·exp(−iπλz(fx² + fy²)). Valid in the paraxial regime
(Fresnel number considerations); equivalent to angular spectrum to second
order in the transverse frequencies.

## Split-step (Schmidt 2010 ch. 6)

Per step: linear propagation (dz) → optional nonlinear phase accumulation.
Framework status: VALIDATED as a framework. Any concrete nonlinear model
must carry its own validated source chain; otherwise CANDIDATE_MODEL.

## Alias-free sampling bound (Voelz 2011)

For the TF-form propagators with N samples at pitch dx:
z ≤ N·dx²/λ — beyond this bound wrap-around aliasing is possible and the
sampling validator fails the spec.

## Sources

- Goodman, Introduction to Fourier Optics, 4th ed. (2017)
- Voelz, Computational Fourier Optics (2011)
- Schmidt, Numerical Simulation of Optical Wave Propagation (2010)
