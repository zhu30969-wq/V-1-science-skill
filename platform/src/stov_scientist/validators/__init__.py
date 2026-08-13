"""Deterministic validators (spec PHASE 6 §22).

Order: Schema -> Units -> Dimensions -> Symbols -> Limits -> Boundary ->
Topology -> Sampling -> Physics consistency.

Pydantic validates shapes; Pint validates units; SymPy validates symbols;
NumPy/SciPy validate numerically; the LLM is the LAST resort, never the
first validator.
"""

from stov_scientist.validators.runner import ValidatorContext, run_validators

__all__ = ["ValidatorContext", "run_validators"]
