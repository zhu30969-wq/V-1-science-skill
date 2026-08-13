"""Dimensional validation of equations (Pint dimensionality via SymPy AST).

Deterministic rule set:
  * every additive term of an equation shares one dimensionality
  * arguments of exp(...)/log(...)/sin(...)/cos(...) are dimensionless
  * declared symbol units come from ScientificModelSpec.symbols
"""

from __future__ import annotations

from typing import Any

import sympy

from stov_scientist.errors import SchemaError
from stov_scientist.schemas import Equation, ScientificModelSpec, ValidationLevel, ValidationResult
from stov_scientist.validators.units import get_ureg


def _as_dict(x: Any) -> dict[str, float]:
    """Normalize a pint dimensionality (Unit or UnitsContainer) to a plain
    {base_dimension: exponent} dict — uniform, dependency-free algebra."""
    from pint.util import UnitsContainer, to_units_container

    def _num(v: Any) -> float:
        if isinstance(v, complex):
            return float(v.real)
        return float(v)

    if isinstance(x, UnitsContainer):
        return {str(k): _num(v) for k, v in x.items()}
    if isinstance(x, dict):
        return {str(k): _num(v) for k, v in x.items()}
    try:
        container = to_units_container(x)
        return {str(k): _num(v) for k, v in container.items()}
    except Exception:
        return {str(k): _num(v) for k, v in x.items()}


def _dim_eq(a: Any, b: Any) -> bool:
    return _as_dict(a) == _as_dict(b)


def _dim_mul(a: Any, b: Any) -> dict[str, float]:
    """Product of two dimensionalities (exponent addition)."""
    da, db = _as_dict(a), _as_dict(b)
    out = dict(da)
    for key, value in db.items():
        out[key] = out.get(key, 0.0) + value
    return {k: v for k, v in out.items() if v != 0.0}


def _dim_pow(a: Any, n: float) -> dict[str, float]:
    """Power of a dimensionality by a numeric exponent."""
    da = _as_dict(a)
    return {k: v * n for k, v in da.items()}

_TRANSCENDENTAL = (sympy.exp, sympy.log, sympy.sin, sympy.cos, sympy.tan, sympy.sinh, sympy.cosh)


def _symbol_dimensions(model: ScientificModelSpec) -> dict[sympy.Symbol, Any]:
    ureg = get_ureg()
    out: dict[sympy.Symbol, Any] = {}
    for symbol, unit_str in model.symbols.items():
        try:
            out[sympy.Symbol(symbol)] = ureg.Unit(unit_str).dimensionality
        except Exception as exc:
            raise SchemaError(f"cannot resolve dimensions of symbol {symbol!r}: {exc}") from exc
    # numeric constants are dimensionless
    return out


def _expr_dimensionality(
    expr: sympy.Expr,
    dims: dict[sympy.Symbol, Any],
    problems: list[str],
    path: str,
) -> Any | None:
    """Best-effort dimensionality of an expression; None when indeterminate."""
    ureg = get_ureg()
    if isinstance(expr, sympy.Symbol):
        return dims.get(expr, ureg.dimensionless)
    if isinstance(expr, sympy.Number):
        return ureg.dimensionless
    if isinstance(expr, sympy.Float):
        return ureg.dimensionless
    if isinstance(expr, sympy.Pow):
        base_d = _expr_dimensionality(expr.base, dims, problems, path)
        exp = expr.exp
        if base_d is None:
            return None
        if isinstance(exp, (sympy.Rational, sympy.Integer, sympy.Float)):
            try:
                return _dim_pow(base_d, float(exp))
            except Exception:
                problems.append(f"{path}: non-integer power of dimensional base")
                return None
        if isinstance(exp, sympy.Symbol):
            if exp in dims and not _dim_eq(dims[exp], ureg.dimensionless):
                problems.append(f"{path}: dimensional exponent {exp}")
                return None
            return ureg.dimensionless
        # composite exponent (e.g. abs(l)): try to evaluate numerically when
        # every free symbol of the exponent is dimensionless
        exp_dims = [_expr_dimensionality(t, dims, problems, path) for t in exp.free_symbols]
        if all(_dim_eq(d, ureg.dimensionless) for d in exp_dims if d is not None):
            try:
                numeric = float(exp.subs({s: 1 for s in exp.free_symbols}))
                return _dim_pow(base_d, numeric)
            except Exception:
                return None
        problems.append(f"{path}: indeterminate exponent {exp}")
        return None
    if isinstance(expr, sympy.Mul):
        # product of factor dimensionalities (dimensionless start)
        product: dict[str, float] = _as_dict(ureg.dimensionless)
        for factor in expr.args:
            d = _expr_dimensionality(factor, dims, problems, path)
            if d is None:
                return None
            product = _dim_mul(product, d)
        return product
    if isinstance(expr, sympy.Add):
        terms = list(expr.args)
        ds = [_expr_dimensionality(t, dims, problems, path) for t in terms]
        ds = [d for d in ds if d is not None]
        if len({str(d) for d in ds}) > 1:
            problems.append(
                f"{path}: additive terms have mismatched dimensions "
                f"{sorted({str(d) for d in ds})}"
            )
        return ds[0] if ds else None
    if expr.func in _TRANSCENDENTAL:
        arg = expr.args[0]
        arg_d = _expr_dimensionality(arg, dims, problems, path)
        if arg_d is not None and not _dim_eq(arg_d, ureg.dimensionless):
            problems.append(f"{path}: argument of {expr.func.__name__} is not dimensionless")
        return ureg.dimensionless
    # unknown function or atom: skip deterministically, do not guess
    return None


def _eq_to_expr(eq: Equation) -> tuple[sympy.Expr, str]:
    """Parse 'lhs = rhs' (or bare expression) into (lhs - rhs, label)."""
    text = eq.symbolic_form
    try:
        if "=" in text:
            lhs_s, rhs_s = text.split("=", 1)
            lhs = sympy.sympify(lhs_s.strip())
            rhs = sympy.sympify(rhs_s.strip())
            return lhs - rhs, text
        return sympy.sympify(text.strip()), text
    except sympy.SympifyError as exc:
        raise SchemaError(f"equation {eq.equation_id!r} is not SymPy-parsable: {exc}") from exc


def validate_dimensions(model: ScientificModelSpec, check_id: str = "dimensions-model") -> ValidationResult:
    dims = _symbol_dimensions(model)
    problems: list[str] = []
    for eq in model.equations:
        try:
            expr, label = _eq_to_expr(eq)
        except SchemaError as exc:
            problems.append(str(exc))
            continue
        _expr_dimensionality(expr, dims, problems, f"{eq.equation_id} ({label})")
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.DIMENSIONS,
        name="dimensional consistency (Pint x SymPy)",
        passed=not problems,
        message="; ".join(problems) if problems else "equations are dimensionally consistent",
        details={"problems": problems},
    )
