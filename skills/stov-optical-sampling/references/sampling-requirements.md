# Sampling requirements

## Nyquist

A signal with maximum frequency f_max requires sampling rate ≥ 2·f_max.
For the STOV envelope the "signal" is the envelope (the carrier is handled
analytically by the envelope model); the grid must resolve the envelope
gradients AND the vortex core.

## Alias-free propagation bound (Voelz 2011)

For TF-form propagation with N samples at pitch Δx:
z ≤ N·Δx²/λ. Beyond this, the quadratic phase of the transfer function is
undersampled and wrap-around aliasing contaminates the field.

Practical STOV consequence: for Δx = 6·wx/N (envelope spanning ±3·wx):
z_max ≈ 36·wx²/(N·λ).

## FFT consistency

- Uniform spacing (all FFT solvers).
- Extent = N·Δ per axis, consistently declared.
- Grid units must parse as Pint units.

## Source

- Voelz, "Computational Fourier Optics", SPIE Press (2011), ch. 6–7.
