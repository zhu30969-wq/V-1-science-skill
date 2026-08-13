# Convergence notes

## Why policy-driven thresholds

A fixed "1e-6 is converged" rule is meaningless across observables (charge
is integer-valued; energy varies with grid truncation; centroids drift with
domain size). The campaign declares, per observable, what relative change
between refinement levels counts as converged.

## Charge as a convergence target

Topological charge converges non-smoothly (integer-valued) — a charge
convergence rule with target 0.05 effectively demands the SAME integer at
both refinement levels, which is the correct requirement for topology
claims.

## Ensemble refinement

Stochastic observables converge in ensemble size; report
`stochastic_uncertainty.std` per ensemble size (spec §30).

## Sources

- Voelz, "Computational Fourier Optics" (2011)
- Schmidt, "Numerical Simulation of Optical Wave Propagation" (2010)
