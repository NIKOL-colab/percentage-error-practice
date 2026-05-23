from __future__ import annotations

import os
import re
import secrets

import sympy
from flask import Flask, jsonify, render_template, request, session
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

TRANS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

def _parse_rhs(rhs_str: str):

    try:
        expr = parse_expr(rhs_str, transformations=TRANS)
        variables = sorted(expr.free_symbols, key=lambda s: s.name)
        return expr, variables, None
    except Exception as exc:
        return None, None, str(exc)

def _is_monomial(expr) -> bool:

    return not expr.has(sympy.Add)

def _detect_powers(expr, variables: list) -> dict:

    powers: dict = {}
    for var in variables:
        try:
            log_diff = sympy.diff(sympy.ln(expr), var)
            power = sympy.simplify(var * log_diff)
            powers[var.name] = float(power)
        except Exception:
            powers[var.name] = None
    return powers

def _build_deriv_hints(lhs: str, expr, variables: list, powers: dict) -> list[str]:

    steps: list[str] = []

    steps.append(
        f"📌  Step 1 — Write the original equation\n\n"
        f"        {lhs}  =  {str(expr)}"
    )

    try:
        log_expanded = sympy.expand_log(sympy.ln(expr), force=True)
        log_str = str(log_expanded).replace("log(", "ln(")
    except Exception:
        log_str = f"ln({str(expr)})"

    steps.append(
        f"📌  Step 2 — Take the natural logarithm (ln) of both sides\n\n"
        f"        ln({lhs})  =  {log_str}\n\n"
        f"        💡  Use the rules:  ln(aᵐ·bⁿ) = m·ln(a) + n·ln(b)"
    )

    diff_parts: list[str] = []
    for var in variables:
        p = powers.get(var.name) or 1.0
        coef = f"{p:g}" if abs(p) != 1.0 else ("" if p > 0 else "−")
        sep = "·" if coef and coef not in ("", "−") else ""
        sign = "−" if p < 0 and abs(p) == 1 else ""
        if abs(p) == 1.0:
            diff_parts.append(f"{sign}d{var.name}/{var.name}")
        else:
            diff_parts.append(f"{coef}·d{var.name}/{var.name}")

    steps.append(
        f"📌  Step 3 — Differentiate both sides with respect to each variable\n\n"
        f"        d{lhs}/{lhs}  =  {' + '.join(diff_parts)}\n\n"
        f"        💡  Rule used:  d(ln u) = du/u"
    )

    abs_parts: list[str] = []
    for var in variables:
        p = abs(powers.get(var.name) or 1.0)
        if p == 1.0:
            abs_parts.append(f"δ{var.name}/{var.name}")
        else:
            abs_parts.append(f"|{p:g}|·δ{var.name}/{var.name}")

    steps.append(
        f"📌  Step 4 — Replace differentials with errors (δ) and take |absolute values|\n\n"
        f"        δ{lhs}/{lhs}  ≤  {' + '.join(abs_parts)}\n\n"
        f"        💡  Errors always add — we take the worst-case (all positive)."
    )

    pct_parts: list[str] = []
    for var in variables:
        p = abs(powers.get(var.name) or 1.0)
        if p == 1.0:
            pct_parts.append(f"%E({var.name})")
        else:
            pct_parts.append(f"{p:g} × %E({var.name})")

    steps.append(
        f"📌  Step 5 — Multiply both sides by 100 → Percentage Error Formula\n\n"
        f"        %E({lhs})  =  {' + '.join(pct_parts)}"
    )

    lines = [
        f"        • {v.name}:  coefficient  =  {abs(powers.get(v.name) or 1.0):g}"
        for v in variables
    ]
    steps.append(
        "✅  Summary — Coefficients (powers) you need to enter:\n\n"
        + "\n".join(lines)
        + "\n\n        Enter these values in the derivative quiz to proceed!"
    )

    return steps

def _build_calc_hints(
    lhs: str, powers: dict, var_errors: dict, total: float
) -> list[str]:

    steps: list[str] = []

    formula_parts = [
        (f"{abs(p):g} × %E({n})" if abs(p) != 1.0 else f"%E({n})")
        for n, p in powers.items()
    ]
    steps.append(
        f"📌  Step 1 — Write the percentage error formula\n\n"
        f"        %E({lhs})  =  {' + '.join(formula_parts)}"
    )

    sub_parts = [
        (f"{abs(p):g} × {var_errors[n]}%" if abs(p) != 1.0 else f"{var_errors[n]}%")
        for n, p in powers.items()
    ]
    steps.append(
        f"📌  Step 2 — Substitute the given percentage errors\n\n"
        f"        %E({lhs})  =  {' + '.join(sub_parts)}"
    )

    contrib_lines: list[str] = []
    contribs: list[float] = []
    for n, p in powers.items():
        c = round(abs(p) * var_errors[n], 6)
        contribs.append(c)
        if abs(p) == 1.0:
            contrib_lines.append(f"        • {n}:  {var_errors[n]}%  →  {c}%")
        else:
            contrib_lines.append(
                f"        • {n}:  {abs(p):g} × {var_errors[n]}%  =  {c}%"
            )
    steps.append(
        "📌  Step 3 — Calculate each contribution\n\n" + "\n".join(contrib_lines)
    )

    c_str = " + ".join(f"{c}%" for c in contribs)
    steps.append(
        f"📌  Step 4 — Add all contributions\n\n"
        f"        %E({lhs})  =  {c_str}\n\n"
        f"        %E({lhs})  =  {total}%"
    )

    steps.append(f"✅  Final Answer:   %E({lhs})  =  {total}%")
    return steps

@app.route("/")
def index():

    session.clear()
    return render_template("index.html")

@app.route("/api/parse", methods=["POST"])
def api_parse():
    data = request.get_json(force=True, silent=True) or {}
    raw: str = (data.get("equation") or "").strip()

    if not raw:
        return jsonify(success=False, error="Please enter an equation.")

    if "=" in raw:
        lhs, rhs_str = raw.split("=", 1)
        lhs = lhs.strip()
        rhs_str = rhs_str.strip()
    else:
        lhs = "Z"
        rhs_str = raw

    if not lhs:
        return jsonify(success=False, error="Left-hand side cannot be empty.")

    expr, variables, err = _parse_rhs(rhs_str)
    if err:
        return jsonify(success=False, error=f"Could not parse expression: {err}")
    if not variables:
        return jsonify(success=False, error="No variables were detected in the expression.")

    if not _is_monomial(expr):
        return jsonify(
            success=False,
            error=(
                "Only multiplicative / power expressions are supported "
                "(e.g. V = l*b*h, P = I^2*R). "
                "Expressions containing + or − are not supported yet."
            ),
        )

    powers = _detect_powers(expr, variables)
    if None in powers.values():
        failed = [n for n, v in powers.items() if v is None]
        return jsonify(
            success=False,
            error=f"Could not determine the exponent for: {', '.join(failed)}",
        )

    session.update(
        lhs=lhs,
        expr_str=str(expr),
        var_names=[v.name for v in variables],
        powers={k: float(v) for k, v in powers.items()},
    )

    return jsonify(
        success=True,
        lhs_name=lhs,
        var_names=[v.name for v in variables],
        powers={k: float(v) for k, v in powers.items()},
    )

@app.route("/api/deriv-hints", methods=["GET"])
def api_deriv_hints():
    lhs = session.get("lhs")
    expr_str = session.get("expr_str")
    var_names = session.get("var_names")
    powers = session.get("powers")

    if not all([lhs, expr_str, var_names, powers]):
        return jsonify(success=False, error="Session expired — please restart.")

    expr = parse_expr(expr_str, transformations=TRANS)
    variables = [sympy.Symbol(n) for n in var_names]
    steps = _build_deriv_hints(lhs, expr, variables, powers)
    return jsonify(success=True, steps=steps)

_TERM_RE = re.compile(
    r'^'                                         
    r'((?:\d+(?:\.\d*)?|\.\d+)'                  
    r'(?:/(?:\d+(?:\.\d*)?|\.\d+))?'             
    r'\s*\*?\s*)?'                               
    r'd([A-Za-z]\w*)'                            
    r'\s*/\s*'                                   
    r'([A-Za-z]\w*)$'                            
)

def _parse_coef(raw: str) -> float:

    s = raw.replace("*", "").strip()
    if not s:
        return 1.0
    if "/" in s:
        num, den = s.split("/", 1)
        return float(num.strip()) / float(den.strip())
    return float(s)

def _parse_deriv_formula(formula_str: str) -> tuple[dict | None, str | None]:

    formula = formula_str.strip()

    if "=" in formula:
        formula = formula.split("=", 1)[1].strip()

    if not formula:
        return None, "Formula is empty after the '=' sign."

    terms = re.split(r"\s*\+\s*", formula)
    found: dict = {}

    for raw_term in terms:
        term = raw_term.strip()
        m = _TERM_RE.match(term)
        if not m:
            return None, (
                f"Could not parse term: '{raw_term}'.\n"
                f"Expected format: dl/l  or  2*di/i  or  1/2*dg/g"
            )

        coef_str, d_var, div_var = m.groups()

        if d_var != div_var:
            return None, (
                f"Term 'd{d_var}/{div_var}' is inconsistent — "
                f"numerator '{d_var}' and denominator '{div_var}' must be the same variable."
            )

        coef = _parse_coef(coef_str or "")
        found[d_var] = coef

    return found, None

@app.route("/api/check-deriv", methods=["POST"])
def api_check_deriv():
    data = request.get_json(force=True, silent=True) or {}
    formula_str: str = (data.get("formula") or "").strip()
    correct: dict = session.get("powers", {})
    var_names: list = session.get("var_names", [])

    if not correct:
        return jsonify(success=False, error="Session expired — please restart.")

    if not formula_str:
        return jsonify(success=True, correct=False,
                       message="Please enter the derivative formula.")

    parsed, err = _parse_deriv_formula(formula_str)
    if err:
        return jsonify(success=True, correct=False, message=err)

    for name in var_names:
        if name not in parsed:
            return jsonify(
                success=True, correct=False,
                message=f"Variable '{name}' is missing from your formula."
            )

    for name in parsed:
        if name not in correct:
            return jsonify(
                success=True, correct=False,
                message=f"Unknown variable '{name}' found in your formula."
            )

    for name in var_names:
        c_p = abs(correct[name])
        u_p = abs(parsed[name])
        if abs(c_p - u_p) > 0.001:
            return jsonify(
                success=True, correct=False,
                message=(
                    f"The coefficient for '{name}' is incorrect. "
                    f"Use log differentiation and try again."
                )
            )

    return jsonify(success=True, correct=True, message="Correct derivative! 🎉")

@app.route("/api/set-errors", methods=["POST"])
def api_set_errors():
    data = request.get_json(force=True, silent=True) or {}
    raw_errors: dict = data.get("var_errors", {})
    powers: dict = session.get("powers", {})
    lhs: str = session.get("lhs", "Z")
    var_names: list = session.get("var_names", [])

    if not powers:
        return jsonify(success=False, error="Session expired — please restart.")

    var_errors: dict = {}
    for name in var_names:
        try:
            var_errors[name] = float(raw_errors.get(name, ""))
        except (ValueError, TypeError):
            return jsonify(
                success=False,
                error=f"Invalid percentage error for '{name}'. Enter a number."
            )

    total = round(
        sum(abs(powers[n]) * var_errors[n] for n in var_names), 4
    )
    hints = _build_calc_hints(lhs, powers, var_errors, total)

    session.update(
        var_errors=var_errors,
        correct_answer=total,
        calc_steps=hints,
    )
    return jsonify(success=True)

@app.route("/api/check-answer", methods=["POST"])
def api_check_answer():
    data = request.get_json(force=True, silent=True) or {}
    try:
        user_ans = float(data.get("answer", ""))
    except (ValueError, TypeError):
        return jsonify(success=False, error="Please enter a valid number.")

    correct = session.get("correct_answer")
    if correct is None:
        return jsonify(success=False, error="Session expired — please restart.")

    return jsonify(success=True, correct=abs(user_ans - correct) <= 0.01)

@app.route("/api/calc-hints", methods=["GET"])
def api_calc_hints():
    steps = session.get("calc_steps", [])
    if not steps:
        return jsonify(success=False, error="No hints available. Submit errors first.")
    return jsonify(success=True, steps=steps)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
