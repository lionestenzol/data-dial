"""Experiment 004 - how often is structural cost wrong on a corpus nobody picked?

WHY THIS ONE
    003 showed structural (AST-size) cost can be 94x worse than optimal. But
    003's domain was CHOSEN so the proxy had to fail: convolution, where the
    cheap route has more nodes by construction. 94x is an existence proof, not
    a frequency claim. HANDOFF.md states the open question directly:

        How often is structural cost wrong on a workload nobody picked in
        advance?

    If structural cost is near-optimal almost always, then the measured-cost
    mechanism this programme has been building toward is a tail-risk fix, not
    a throughput win, and the architecture should say so.

CORPUS - chosen for provenance, not for outcome
    913 FPCore expressions from FPBench @090d8198 and Herbie's bench suite
    @884621aa, pinned in research/benchmarks/CORPUS_MANIFEST.json. Mined from
    Hamming ch.3, LULESH, CoolProp, mathjs, Octave, Rust libm, PBRT, basilisk,
    exasim, and the Rosa/Daisy/Salsa/FPTaylor verification suites.

    Both suites were assembled by the floating-point ACCURACY community to
    study rounding error, years before this project. Neither was selected for
    how cost models behave on it. That is the property 003 lacked.

    802 of 913 parse into scope. The 111 exclusions (array/tensor, if, while,
    user-defined FPCore calls, 7 oversized graphics cores) are counted by
    reason and reported, not hidden.

CANDIDATES - somebody else's rewrite engine
    Equivalent forms come from SymPy's documented simplification API
    (simplify, expand, factor, together, cancel, powsimp, radsimp, logcombine,
    trigsimp, horner) plus integer-power expansion (x**4 -> x*x*x*x), which
    every production compiler performs and SymPy will not represent.

    Power expansion is the one transform we added by hand, and it is exactly
    the kind of thing that could stack the deck - it creates candidates where
    node count and runtime disagree sharply. So every headline number is
    ALSO reported over the SymPy-only candidate set, with power expansion
    removed. If the two disagree, the result is an artifact of our transform
    and we say so.

ADMISSION BEFORE SELECTION (the semantic contract, gap #1)
    These are accuracy benchmarks: the as-written form is often the BUGGY one,
    so agreement-with-as-written is the wrong filter. Truth is computed per
    sample point from the as-written expression at 30 decimal digits, and a
    candidate is admitted only if its float64 relative error against truth is
    within tolerance at every valid point. Accuracy admits; cost selects.
    A candidate that is faster but wrong is never a candidate.

ARMS - identical structural walk, only the weight vector differs
    1. ast_size      every node costs 1. The proxy egg warns about.
    2. static_weight textbook relative latencies, one scalar per operator,
                     fixed below before the first run and never tuned.
    3. measured      per-operator cost microbenchmarked on THIS machine at
                     this array length, once, amortised over the whole corpus.
    4. oracle        time every admitted candidate, keep the fastest.

    All of 1-3 score a candidate as the weighted sum over its expression DAG,
    counting each distinct subexpression once - the shape of egglog's
    DagCostModel used in 003.

PRIMARY METRIC
    regret = time(arm's pick) / time(oracle's pick), per decision, where a
    decision is a core with >= 2 admitted candidates. The result is the
    DISTRIBUTION of regret - p50/p90/p95/p99/max and the fraction within the
    timing noise floor - not the maximum. The maximum is what 003 already gave.

HOW THIS KILLS THE IDEA
    If ast_size's p95 regret is within noise, structural cost is fine in
    practice, 003 was a curiosity, and measured costing should be scoped to
    declared-uncertain operators only - or dropped.
"""
from __future__ import annotations

import json
import math
import pathlib
import signal
import statistics
import sys
import time

import numpy as np
import sympy as sp

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from exp004_corpus import load  # noqa: E402

# ----------------------------------------------------------- declared setup
# Timing regime, chosen by measuring the noise floor BEFORE predictions were
# committed (see exp004_noise_calibration in FINDINGS): 16384 float64 = 128 KB,
# L2-resident vectorised NumPy, ~30 us per evaluation. Measured noise floor at
# this setting is p50 1.004x, p95 1.024x, max 1.050x on repeated timings of the
# SAME candidate. That is why NEAR_OPTIMAL is 1.05: anything below the noise
# max cannot be called a real loss. 4096 was noisier (p95 1.073x) and 262144
# was no quieter at 53x the cost.
M_POINTS = 16384         # array length for timing
N_ADMIT = 32             # sample points for the accuracy admission check
TRUTH_PREC = 30          # decimal digits for the reference value
REL_TOL = 1e-6           # primary admission tolerance
SENSITIVITY_TOLS = (1e-9, 1e-3)
REPEATS = 11             # best-of; 7 as in 003 left p95 noise at 1.073x
GEN_TIMEOUT_S = 2.0      # per rewrite transform
CORE_BUDGET_S = 10.0     # per core, all transforms
TRUTH_TIMEOUT_S = 5.0
NEAR_OPTIMAL = 1.05      # regret at or below this counts as near-optimal
SEED = 4004

# Textbook relative latencies. One scalar per operator, size independent.
# Fixed here before the first run. Not tuned afterwards.
STATIC_WEIGHT = {
    "add": 1.0, "mul": 1.0, "div": 4.0, "neg": 0.5, "abs": 0.5,
    "sqrt": 4.0, "pow_int": 3.0, "pow_gen": 25.0,
    "exp": 20.0, "log": 20.0,
    "sin": 25.0, "cos": 25.0, "tan": 30.0,
    "asin": 25.0, "acos": 25.0, "atan": 25.0, "atan2": 30.0,
    "sinh": 25.0, "cosh": 25.0, "tanh": 25.0,
    "asinh": 25.0, "acosh": 25.0, "atanh": 25.0,
    "floor": 1.0, "ceil": 1.0, "max": 1.0, "min": 1.0,
    "sign": 1.0, "mod": 5.0, "const": 0.0, "var": 0.0,
}
OPS = tuple(STATIC_WEIGHT)
AST_SIZE_WEIGHT = {k: (0.0 if k in ("const", "var") else 1.0) for k in OPS}

# ----------------------------------------------------------- op extraction
FUNC_OP = {
    sp.exp: "exp", sp.log: "log", sp.sin: "sin", sp.cos: "cos", sp.tan: "tan",
    sp.asin: "asin", sp.acos: "acos", sp.atan: "atan", sp.atan2: "atan2",
    sp.sinh: "sinh", sp.cosh: "cosh", sp.tanh: "tanh",
    sp.asinh: "asinh", sp.acosh: "acosh", sp.atanh: "atanh",
    sp.Abs: "abs", sp.floor: "floor", sp.ceiling: "ceil",
    sp.Max: "max", sp.Min: "min", sp.sign: "sign", sp.Mod: "mod",
}


def node_ops(expr):
    """Operators contributed by THIS node alone, as {op: count}."""
    if isinstance(expr, sp.Symbol):
        return {"var": 1}
    if expr.is_Number or isinstance(expr, sp.NumberSymbol):
        return {"const": 1}
    if isinstance(expr, sp.Add):
        return {"add": len(expr.args) - 1}
    if isinstance(expr, sp.Mul):
        neg = 1 if any(a is sp.S.NegativeOne for a in expr.args) else 0
        k = len(expr.args) - neg
        out = {"mul": max(k - 1, 0)}
        if neg:
            out["neg"] = 1
        return out
    if isinstance(expr, sp.Pow):
        e = expr.exp
        if e == -1:
            return {"div": 1}
        if e == sp.Rational(1, 2):
            return {"sqrt": 1}
        if e == sp.Rational(-1, 2):
            return {"sqrt": 1, "div": 1}
        if e.is_Integer and 2 <= abs(int(e)) <= 8:
            out = {"pow_int": 1}
            if int(e) < 0:
                out["div"] = 1
            return out
        return {"pow_gen": 1}
    for cls, name in FUNC_OP.items():
        if isinstance(expr, cls):
            return {name: 1}
    return {"pow_gen": 1}      # unknown function: priced as expensive


def dag_op_counts(expr):
    """Operator histogram over the expression DAG, each distinct
    subexpression counted ONCE. SymPy caches structurally identical
    subexpressions to the same object, so set membership gives DAG semantics
    and shared work is not double charged."""
    seen, counts = set(), {}
    stack = [expr]
    while stack:
        e = stack.pop()
        key = id(e) if isinstance(e, sp.Basic) else e
        if key in seen:
            continue
        seen.add(key)
        for op, n in node_ops(e).items():
            counts[op] = counts.get(op, 0) + n
        stack.extend(e.args)
    return counts


def tree_op_counts(expr):
    """Operator histogram over the expression TREE, shared subexpressions
    counted once PER OCCURRENCE.

    This is not redundant with the DAG count. SymPy's lambdify performs no
    common-subexpression elimination - it emits (sin(x)+1)*(sin(x)+2)
    literally, so NumPy evaluates sin(x) twice. Measured here: 228.8 us
    without CSE against 118.5 us with it. So for this backend the tree count
    is the faithful model and the DAG count systematically under-charges
    shared work. 003 used egglog's DagCostModel, so DAG is kept as the
    primary for continuity and tree is reported beside it. Whether counting
    or weighting dominates the error is itself a result.
    """
    counts = {}
    stack = [expr]
    while stack:
        e = stack.pop()
        for op, n in node_ops(e).items():
            counts[op] = counts.get(op, 0) + n
        stack.extend(e.args)
    return counts


def has_square_powexp(expr):
    """True if this form contains an unevaluated x*x that came from x**2.
    NumPy computes a**2 FASTER than a*a (3.2 us vs 7.2 us) but a**3 SLOWER
    than a*a*a (41.9 us vs 14.6 us), so a single pow_int weight is wrong at
    one end of the exponent range by construction - the 003 phenomenon,
    arising here without anyone choosing it."""
    stack = [expr]
    while stack:
        e = stack.pop()
        if isinstance(e, sp.Mul) and len(e.args) == 2 and e.args[0] == e.args[1]:
            return True
        stack.extend(e.args)
    return False


def dag_cost(counts, weights):
    return sum(weights.get(op, 1.0) * n for op, n in counts.items())


# ----------------------------------------------------------- candidates
class _TO(Exception):
    pass


def _alarm(*_a):
    raise _TO()


def _guard(fn, arg, seconds):
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn(arg)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def horner_form(e):
    syms = sorted(e.free_symbols, key=str)
    if len(syms) != 1:
        raise ValueError("not univariate")
    return sp.horner(sp.Poly(e, syms[0]))


def expand_int_powers(e):
    """x**4 -> x*x*x*x, built unevaluated so SymPy will not fold it back.
    Every production compiler does this; SymPy has no representation for it."""
    def rec(z):
        if not z.args:
            return z
        args = [rec(a) for a in z.args]
        if isinstance(z, sp.Pow):
            b, ex = args[0], z.exp
            if ex.is_Integer and 2 <= int(ex) <= 8:
                return sp.Mul(*([b] * int(ex)), evaluate=False)
            if ex.is_Integer and -8 <= int(ex) <= -2:
                return sp.Pow(sp.Mul(*([b] * -int(ex)), evaluate=False), -1,
                              evaluate=False)
        return z.func(*args) if args else z
    out = rec(e)
    if sp.srepr(out) == sp.srepr(e):
        raise ValueError("no integer powers")
    return out


SYMPY_GENERATORS = [
    ("as_written", lambda e: e),
    ("simplify", sp.simplify),
    ("expand", sp.expand),
    ("factor", sp.factor),
    ("together", sp.together),
    ("cancel", sp.cancel),
    ("powsimp", sp.powsimp),
    ("radsimp", sp.radsimp),
    ("logcombine", sp.logcombine),
    ("trigsimp", sp.trigsimp),
    ("horner", horner_form),
]


def candidates_for(expr, stats):
    """Distinct equivalent forms, tagged by which transform produced them."""
    out, seen = [], set()
    t_start = time.perf_counter()

    def offer(tag, e):
        if e is None:
            return
        try:
            key = sp.srepr(e)
        except Exception:
            return
        if key in seen:
            return
        seen.add(key)
        out.append((tag, e))

    offer("as_written", expr)
    for tag, fn in SYMPY_GENERATORS[1:]:
        if time.perf_counter() - t_start > CORE_BUDGET_S:
            stats["gen_budget_exhausted"] = stats.get("gen_budget_exhausted", 0) + 1
            break
        try:
            offer(tag, _guard(fn, expr, GEN_TIMEOUT_S))
        except _TO:
            stats["gen_timeout:" + tag] = stats.get("gen_timeout:" + tag, 0) + 1
        except Exception:
            pass
    # power expansion of every distinct form found so far
    for tag, e in list(out):
        if time.perf_counter() - t_start > CORE_BUDGET_S:
            break
        try:
            offer("powexp/" + tag, _guard(expand_int_powers, e, GEN_TIMEOUT_S))
        except Exception:
            pass
    return out


# ----------------------------------------------------------- sampling, truth
WIDE_DECADES = 1e3      # span above which a domain is sampled log-uniformly
CLAMP_MAG = 1e12        # magnitude cap for mixed-sign unbounded domains


def sample_points(core, rng, n):
    """Sample the declared :pre domain.

    13 of the 802 in-scope cores declare domains spanning many orders of
    magnitude - Hamming's large-x examples go to 1e308, and one demo core
    declares the whole float range. Uniform sampling there is both
    meaningless (every draw lands at the top decade) and impossible
    (rng.uniform overflows when hi-lo exceeds the float range; this crashed
    the first full run). Sign-consistent wide domains are therefore sampled
    LOG-uniformly, which is what Herbie's own sampler does and what the
    benchmarks intend; mixed-sign unbounded domains are clamped in magnitude
    and the clamp is reported as a limitation.
    """
    cols = {}
    for name in core.args:
        lo, hi, nonzero = core.domain[name]
        if lo > 0 and hi / lo > WIDE_DECADES:
            v = np.exp(rng.uniform(math.log(lo), math.log(hi), size=n))
        elif hi < 0 and lo / hi > WIDE_DECADES:
            v = -np.exp(rng.uniform(math.log(-hi), math.log(-lo), size=n))
        else:
            a = max(min(lo, CLAMP_MAG), -CLAMP_MAG)
            b = max(min(hi, CLAMP_MAG), -CLAMP_MAG)
            if b < a:
                a, b = b, a
            v = rng.uniform(a, b, size=n)
        if nonzero:
            bad = np.abs(v) < 1e-3
            v[bad] = np.where(v[bad] >= 0, 1e-3, -1e-3)
        cols[name] = v
    return cols


def truth_values(expr, args, cols, stats):
    """Reference values at TRUTH_PREC digits. Exact rational substitution so
    the reference is not itself a float computation."""
    vals = []
    try:
        signal.setitimer(signal.ITIMER_REAL, TRUTH_TIMEOUT_S)
        for i in range(len(next(iter(cols.values())))):
            sub = {sp.Symbol(a, real=True): sp.Rational(float(cols[a][i]))
                   for a in args}
            v = sp.N(expr.subs(sub, simultaneous=True), TRUTH_PREC)
            try:
                f = float(v)
            except (TypeError, ValueError):
                f = math.nan
            vals.append(f if math.isfinite(f) else math.nan)
    except _TO:
        stats["truth_timeout"] = stats.get("truth_timeout", 0) + 1
        return None
    except Exception:
        stats["truth_error"] = stats.get("truth_error", 0) + 1
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    return np.array(vals, dtype=float)


def rel_err(got, truth):
    with np.errstate(all="ignore"):
        denom = np.where(np.abs(truth) > 0, np.abs(truth), 1.0)
        return np.abs(np.asarray(got, dtype=float) - truth) / denom


# ----------------------------------------------------------- timing
def compile_fn(args, expr):
    f = sp.lambdify([sp.Symbol(a, real=True) for a in args], expr, "numpy")
    return f


def time_fn(f, arrays, repeats=REPEATS):
    with np.errstate(all="ignore"):
        f(*arrays)                                  # warm
        best = math.inf
        for _ in range(repeats):
            t = time.perf_counter()
            f(*arrays)
            best = min(best, (time.perf_counter() - t) * 1000.0)
    return best


def calibrate(rng):
    """Per-operator cost on THIS machine at this array length. One call,
    amortised over every decision in the corpus. Its price is charged."""
    t0 = time.perf_counter()
    a = rng.uniform(0.5, 2.0, size=M_POINTS)
    b = rng.uniform(0.5, 2.0, size=M_POINTS)
    probes = {
        "add": lambda: a + b, "mul": lambda: a * b, "div": lambda: a / b,
        "neg": lambda: -a, "abs": lambda: np.abs(a), "sqrt": lambda: np.sqrt(a),
        "pow_int": lambda: a ** 3, "pow_gen": lambda: a ** b,
        "exp": lambda: np.exp(a), "log": lambda: np.log(a),
        "sin": lambda: np.sin(a), "cos": lambda: np.cos(a),
        "tan": lambda: np.tan(a), "asin": lambda: np.arcsin(a * 0.4),
        "acos": lambda: np.arccos(a * 0.4), "atan": lambda: np.arctan(a),
        "atan2": lambda: np.arctan2(a, b),
        "sinh": lambda: np.sinh(a), "cosh": lambda: np.cosh(a),
        "tanh": lambda: np.tanh(a), "asinh": lambda: np.arcsinh(a),
        "acosh": lambda: np.arccosh(a + 1.0), "atanh": lambda: np.arctanh(a * 0.4),
        "floor": lambda: np.floor(a), "ceil": lambda: np.ceil(a),
        "max": lambda: np.maximum(a, b), "min": lambda: np.minimum(a, b),
        "sign": lambda: np.sign(a), "mod": lambda: np.mod(a, b),
    }
    w = {"const": 0.0, "var": 0.0}
    for name, fn in probes.items():
        with np.errstate(all="ignore"):
            fn()
            w[name] = min((lambda: (lambda s: (fn(), time.perf_counter() - s)[1])(
                time.perf_counter()))() for _ in range(REPEATS)) * 1000.0
    return w, (time.perf_counter() - t0) * 1000.0


# ----------------------------------------------------------- main
def quantiles(xs):
    if not xs:
        return {}
    s = sorted(xs)
    def q(p):
        if len(s) == 1:
            return s[0]
        i = min(int(math.ceil(p * len(s))) - 1, len(s) - 1)
        return s[max(i, 0)]
    return {"n": len(s), "min": s[0], "p50": q(0.50), "p90": q(0.90),
            "p95": q(0.95), "p99": q(0.99), "max": s[-1],
            "mean": statistics.fmean(s)}


def run(limit=None, probe=False, out_path="experiments/exp004_results.json"):
    rng = np.random.default_rng(SEED)
    cores, cstats = load()
    if limit:
        step = max(1, len(cores) // limit)
        cores = cores[::step][:limit]
    print(f"corpus: {cstats['fpcores']} FPCores, {cstats['ok']} in scope, "
          f"running {len(cores)}", flush=True)

    measured_w, cal_ms = calibrate(rng)
    print(f"calibration: {cal_ms:.1f} ms  "
          f"(add={measured_w['add']*1e3:.1f}us exp={measured_w['exp']*1e3:.1f}us "
          f"sin={measured_w['sin']*1e3:.1f}us div={measured_w['div']*1e3:.1f}us "
          f"pow_int={measured_w['pow_int']*1e3:.1f}us pow_gen={measured_w['pow_gen']*1e3:.1f}us)",
          flush=True)

    stats = dict(cstats); stats["corpus_rejected"] = cstats["rejected"]
    rows, t_begin = [], time.perf_counter()

    for idx, core in enumerate(cores):
        if idx % 50 == 0:
            print(f"  [{idx}/{len(cores)}] {time.perf_counter()-t_begin:.0f}s "
                  f"decisions={sum(1 for r in rows if r['n_admitted']>=2)}", flush=True)
        try:
            cands = candidates_for(core.expr, stats)
        except Exception:
            stats["gen_error"] = stats.get("gen_error", 0) + 1
            continue
        if len(cands) < 2:
            stats["single_candidate"] = stats.get("single_candidate", 0) + 1

        acols = sample_points(core, rng, N_ADMIT)
        truth = truth_values(core.expr, core.args, acols, stats)
        if truth is None or np.count_nonzero(np.isfinite(truth)) < 8:
            stats["no_truth"] = stats.get("no_truth", 0) + 1
            continue
        finite = np.isfinite(truth)

        tcols = sample_points(core, rng, M_POINTS)
        tarrays = [tcols[a] for a in core.args]
        aarrays = [acols[a] for a in core.args]

        admitted = []
        for tag, e in cands:
            try:
                f = compile_fn(core.args, e)
                with np.errstate(all="ignore"):
                    got = np.asarray(f(*aarrays), dtype=float)
                if got.shape != truth.shape:
                    got = np.broadcast_to(got, truth.shape)
            except Exception:
                stats["compile_error"] = stats.get("compile_error", 0) + 1
                continue
            err = rel_err(got, truth)
            ok_mask = finite & np.isfinite(got)
            if np.count_nonzero(ok_mask) < 8:
                stats["reject_nonfinite"] = stats.get("reject_nonfinite", 0) + 1
                continue
            worst = float(np.max(err[ok_mask]))
            if worst > REL_TOL:
                stats["reject_tolerance"] = stats.get("reject_tolerance", 0) + 1
                continue
            try:
                ms = time_fn(f, tarrays)
            except Exception:
                stats["time_error"] = stats.get("time_error", 0) + 1
                continue
            counts = dag_op_counts(e)
            tcounts = tree_op_counts(e)
            admitted.append({
                "tag": tag, "ms": ms, "worst_rel_err": worst,
                "counts": counts,
                "cost_ast_size": dag_cost(counts, AST_SIZE_WEIGHT),
                "cost_static": dag_cost(counts, STATIC_WEIGHT),
                "cost_measured": dag_cost(counts, measured_w),
                "cost_ast_size_tree": dag_cost(tcounts, AST_SIZE_WEIGHT),
                "cost_static_tree": dag_cost(tcounts, STATIC_WEIGHT),
                "cost_measured_tree": dag_cost(tcounts, measured_w),
                "nodes": sum(counts.values()),
                "tree_nodes": sum(tcounts.values()),
                "sq_powexp": has_square_powexp(e),
            })

        if not admitted:
            stats["no_admitted"] = stats.get("no_admitted", 0) + 1
            continue

        # timing noise floor: re-time the fastest candidate
        best = min(admitted, key=lambda c: c["ms"])
        try:
            noise = time_fn(compile_fn(core.args, dict(
                (t, e) for t, e in cands)[best["tag"]]), tarrays) / best["ms"]
        except Exception:
            noise = math.nan

        rows.append({
            "source": core.source, "name": core.name, "args": core.args,
            "n_candidates": len(cands), "n_admitted": len(admitted),
            "noise_ratio": noise,
            "admitted": admitted,
        })

    elapsed = time.perf_counter() - t_begin
    summary = summarise(rows, stats, cal_ms, measured_w, elapsed)
    if not probe:
        with open(out_path, "w") as fh:
            json.dump({"summary": summary, "rows": rows,
                       "static_weight": STATIC_WEIGHT,
                       "measured_weight": measured_w,
                       "config": {"M_POINTS": M_POINTS, "N_ADMIT": N_ADMIT,
                                  "TRUTH_PREC": TRUTH_PREC, "REL_TOL": REL_TOL,
                                  "REPEATS": REPEATS, "SEED": SEED,
                                  "NEAR_OPTIMAL": NEAR_OPTIMAL}}, fh, indent=2)
    if probe:
        probe_report(summary, stats)
    else:
        report(summary)
    return summary


def pick_regret(admitted, cost_key):
    best = min(admitted, key=lambda c: (c[cost_key], c["nodes"], c["tag"]))
    oracle = min(c["ms"] for c in admitted)
    return best, best["ms"] / oracle if oracle > 0 else math.nan


ARMS = (("ast_size", "cost_ast_size"), ("static_weight", "cost_static"),
        ("measured", "cost_measured"))
TREE_ARMS = (("ast_size", "cost_ast_size_tree"),
             ("static_weight", "cost_static_tree"),
             ("measured", "cost_measured_tree"))


def summarise(rows, stats, cal_ms, measured_w, elapsed):
    decisions = [r for r in rows if r["n_admitted"] >= 2]
    out = {"cores_evaluated": len(rows), "decisions": len(decisions),
           "calibration_ms": cal_ms, "elapsed_s": elapsed,
           "corpus": {k: v for k, v in stats.items() if k != "rejected"},
           "arms": {}, "sympy_only": {}, "noise": {}}
    nz = [r["noise_ratio"] for r in decisions if math.isfinite(r.get("noise_ratio", math.nan))]
    out["noise"] = quantiles(nz)

    def arm_block(sel, arms=ARMS):
        block = {}
        for arm, key in arms:
            regs, matched = [], 0
            for r in sel:
                adm = r["_adm"]
                if len(adm) < 2:
                    continue
                best = min(adm, key=lambda c: (c[key], c["nodes"], c["tag"]))
                oracle_ms = min(c["ms"] for c in adm)
                regs.append(best["ms"] / oracle_ms if oracle_ms > 0 else math.nan)
                if best["ms"] <= oracle_ms * 1.0000001:
                    matched += 1
            regs = [x for x in regs if math.isfinite(x)]
            q = quantiles(regs)
            q["picked_oracle"] = matched
            q["frac_picked_oracle"] = matched / len(regs) if regs else 0.0
            q["frac_near_optimal"] = (sum(1 for x in regs if x <= NEAR_OPTIMAL)
                                      / len(regs)) if regs else 0.0
            q["frac_regret_ge_1_5"] = (sum(1 for x in regs if x >= 1.5)
                                       / len(regs)) if regs else 0.0
            q["frac_regret_ge_2"] = (sum(1 for x in regs if x >= 2.0)
                                     / len(regs)) if regs else 0.0
            block[arm] = q
        return block

    full = [{**r, "_adm": r["admitted"]} for r in decisions]
    out["arms"] = arm_block(full)
    out["tree_arms"] = arm_block(full, TREE_ARMS)

    # T8: decisions that contain a squared power-expansion candidate, where
    # one pow_int weight is wrong by construction, against those that do not.
    with_sq = [r for r in full if any(c["sq_powexp"] for c in r["_adm"])]
    without_sq = [r for r in full if not any(c["sq_powexp"] for c in r["_adm"])]
    out["square_split"] = {
        "with_sq_n": len(with_sq), "without_sq_n": len(without_sq),
        "with_sq": arm_block(with_sq), "without_sq": arm_block(without_sq)}

    sonly = []
    for r in decisions:
        adm = [c for c in r["admitted"] if not c["tag"].startswith("powexp/")]
        if len(adm) >= 2:
            sonly.append({**r, "_adm": adm})
    out["sympy_only"] = arm_block(sonly)
    out["sympy_only_decisions"] = len(sonly)

    # what the oracle costs: timing every admitted candidate, every request
    oc = [sum(c["ms"] for c in r["admitted"]) * REPEATS for r in decisions]
    ob = [min(c["ms"] for c in r["admitted"]) for r in decisions]
    out["oracle_cost"] = {"mean_timing_ms_per_decision": statistics.fmean(oc) if oc else 0,
                          "mean_best_ms": statistics.fmean(ob) if ob else 0}
    out["calibration_breakeven_decisions"] = None
    return out


def probe_report(s, stats):
    """Mechanics only. Deliberately prints NO regret numbers: this runs before
    the predictions are committed and must not let us see the outcome first."""
    print("\n" + "=" * 72)
    print("PROBE - mechanics and cost only, no arm comparison")
    print(f"cores evaluated       : {s['cores_evaluated']}")
    print(f"decisions (>=2 admit) : {s['decisions']}")
    print(f"sympy-only decisions  : {s['sympy_only_decisions']}")
    print(f"calibration           : {s['calibration_ms']:.1f} ms")
    print(f"elapsed               : {s['elapsed_s']:.1f}s "
          f"({s['elapsed_s']/max(s['cores_evaluated'],1):.2f}s per core)")
    n = s["noise"]
    if n:
        print(f"timing noise floor    : p50 {n['p50']:.4f}x p95 {n['p95']:.4f}x "
              f"max {n['max']:.4f}x  (n={n['n']})")
    print("counters:")
    for k, v in sorted(stats.items(), key=lambda kv: str(kv[0])):
        if k in ("rejected", "corpus_rejected", "files", "fpcores", "ok"):
            continue
        print(f"  {str(v):>6}  {k}")


def report(s):
    print("\n" + "=" * 72)
    print(f"decisions (>=2 admitted candidates): {s['decisions']} "
          f"of {s['cores_evaluated']} cores evaluated")
    n = s["noise"]
    if n:
        print(f"timing noise floor (re-time of same candidate): "
              f"p50 {n['p50']:.4f}x  p95 {n['p95']:.4f}x  max {n['max']:.4f}x")
    for label, key in (("FULL candidate set, DAG counting", "arms"),
                       ("FULL candidate set, TREE counting", "tree_arms"),
                       ("SymPy-only (no power expansion), DAG", "sympy_only")):
        print(f"\n-- {label} --")
        if key == "sympy_only":
            print(f"   decisions: {s['sympy_only_decisions']}")
        print(f"{'arm':>14} {'=oracle':>9} {'<=1.05':>8} {'p50':>8} {'p90':>8} "
              f"{'p95':>8} {'p99':>8} {'max':>9} {'>=1.5':>7}")
        for arm, _ in ARMS:
            q = s[key].get(arm) or {}
            if not q:
                continue
            print(f"{arm:>14} {q['frac_picked_oracle']*100:>8.1f}% "
                  f"{q['frac_near_optimal']*100:>7.1f}% "
                  f"{q['p50']:>8.3f} {q['p90']:>8.3f} {q['p95']:>8.3f} "
                  f"{q['p99']:>8.3f} {q['max']:>9.2f} "
                  f"{q['frac_regret_ge_1_5']*100:>6.1f}%")
    print(f"\ncalibration: {s['calibration_ms']:.1f} ms once, amortised over "
          f"{s['decisions']} decisions")
    sq = s.get("square_split", {})
    if sq:
        print(f"\nsquared-power split: {sq['with_sq_n']} decisions with an x*x "
              f"candidate, {sq['without_sq_n']} without")
        for arm, _ in ARMS:
            w = sq["with_sq"].get(arm) or {}
            o = sq["without_sq"].get(arm) or {}
            if w and o:
                print(f"  {arm:>14}  =oracle with x*x {w['frac_picked_oracle']*100:>5.1f}%  "
                      f"without {o['frac_picked_oracle']*100:>5.1f}%")
    print(f"oracle cost: {s['oracle_cost']['mean_timing_ms_per_decision']:.3f} ms "
          f"of timing per decision vs {s['oracle_cost']['mean_best_ms']:.4f} ms "
          f"to just run the best form")
    print(f"elapsed: {s['elapsed_s']:.0f}s")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--out", default="experiments/exp004_results.json")
    a = ap.parse_args()
    signal.signal(signal.SIGALRM, _alarm)
    run(limit=a.limit, probe=a.probe, out_path=a.out)
