"""Symbolic validation with SymPy (spec §24): symbol coverage, simplification,
limiting-expression evaluation and algebraic equivalence where possible."""

from __future__ import annotations

import sympy

from stov_scientist.errors import SchemaError
from stov_scientist.schemas import Equation, ScientificModelSpec, ValidationLevel, ValidationResult


def parse_equation(eq: Equation) -> sympy.Expr:
    text = eq.symbolic_form
    try:
        if "=" in text:
            lhs_s, rhs_s = text.split("=", 1)
            return sympy.sympify(lhs_s.strip()) - sympy.sympify(rhs_s.strip())
        return sympy.sympify(text.strip())
    except (sympy.SympifyError, TypeError, ValueError) as exc:
        raise SchemaError(f"equation {eq.equation_id!r} not SymPy-parsable: {exc}") from exc


def validate_symbol_coverage(model: ScientificModelSpec, check_id: str = "symbols-model") -> ValidationResult:
    """Every free symbol of every equation must be declared in model.symbols.

    Undeclared symbols that are known SymPy constants (pi, E, I, oo) are fine;
    everything else is a contract violation.
    """
    declared = {sympy.Symbol(s) for s in model.symbols}
    allowed_builtin = {sympy.pi, sympy.E, sympy.I, sympy.oo, sympy.zoo}
    problems: list[str] = []
    per_eq: dict[str, list[str]] = {}
    for eq in model.equations:
        try:
            expr = parse_equation(eq)
        except SchemaError as exc:
            problems.append(str(exc))
            continue
        undeclared = sorted(
            {str(s) for s in expr.free_symbols if s not in declared and s not in allowed_builtin}
        )
        if undeclared:
            problems.append(f"{eq.equation_id}: undeclared symbols {undeclared}")
        per_eq[eq.equation_id] = undeclared
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.SYMBOLS,
        name="symbol coverage (SymPy)",
        passed=not problems,
        message="; ".join(problems) if problems else "all equation symbols are declared",
        details={"per_equation": per_eq},
    )


def simplify_equation(eq: Equation) -> sympy.Expr:
    return sympy.simplify(parse_equation(eq))


def check_algebraic_equivalence(eq_a: Equation, eq_b: Equation) -> bool:
    """True when two equations are algebraically equivalent (simplified
    difference is identically zero)."""
    try:
        diff = sympy.simplify(parse_equation(eq_a) - parse_equation(eq_b))
    except (SchemaError, TypeError, ValueError):
        return False
    return bool(diff == 0)


def evaluate_limiting_expression(
    expression: str,
    symbol: str,
    value: str | float,
    subs: dict[str, str | float] | None = None,
) -> str:
    """Substitute a limiting value (e.g. t -> 0, w -> oo) and return the
    simplified symbolic/numeric result string."""
    expr = sympy.sympify(expression)
    all_subs = dict(subs or {})
    all_subs[symbol] = value
    evaluated = expr.subs(all_subs)
    return str(sympy.simplify(evaluated))
