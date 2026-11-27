#!/usr/bin/env python
"""Experiment 008 arms — see EXP008_PREREGISTRATION.md.

Five implemented arms, each a policy for answering a stream of requests:

    1 direct       evaluate everything, no cache
    2 memo         cache on (exact syntax, env)
    3 memo_canon   constant-fold + sort commutative operands, then cache
    4 memo_sympy   SymPy normalisation, then cache
    5 memo_egglog  egglog equality saturation + extraction, then cache

Arm 6 (Stitch) is declared not run in the pre-registration.

Every arm is charged for its own normalisation. Arms 4 and 5 get a per-request
time budget; a timeout falls back to the un-normalised form and is COUNTED,
because silently dropping the expensive cases would flatter them.
"""
from __future__ import annotations

import json
import signal
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from exp008_workload import MASK, evaluate, leaves, nodes, syntax_key

NORM_TIMEOUT_S = 2.0


class _TO(Exception):
    pass


def _alarm(*_a):
    raise _TO()


def _guard(fn, arg, seconds=NORM_TIMEOUT_S):
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn(arg)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def env_key(expr, env):
    """Only the variables the expression actually reads matter."""
    return tuple(sorted((k, env[k]) for k in leaves(expr) if k in env))


# ------------------------------------------------------------ normalisers
def norm_identity(e):
    return e


COMMUTATIVE = ("+", "*")


def norm_canon(e):
    """Constant folding plus a canonical order for commutative operands.

    Free, standard, no algebra engine. This is the strong baseline: whatever
    share of the equivalent-formulation cases this catches is a share the
    architecture cannot claim credit for.
    """
    if e[0] in ("var", "const"):
        return e
    a, b = norm_canon(e[1]), norm_canon(e[2])
    op = e[0]
    if a[0] == "const" and b[0] == "const":
        if op == "+":
            return ("const", (a[1] + b[1]) & MASK)
        if op == "-":
            return ("const", (a[1] - b[1]) & MASK)
        if op == "*":
            return ("const", (a[1] * b[1]) & MASK)
    # identities
    if op == "+" and b == ("const", 0):
        return a
    if op == "+" and a == ("const", 0):
        return b
    if op == "*" and b == ("const", 1):
        return a
    if op == "*" and a == ("const", 1):
        return b
    if op == "*" and (a == ("const", 0) or b == ("const", 0)):
        return ("const", 0)
    if op == "-" and b == ("const", 0):
        return a
    if op in COMMUTATIVE:
        ka, kb = json.dumps(a), json.dumps(b)
        if kb < ka:
            a, b = b, a
    return (op, a, b)


_SP = None


def _sympy():
    global _SP
    if _SP is None:
        import sympy
        _SP = sympy
    return _SP


def to_sympy(e, sp):
    if e[0] == "var":
        return sp.Symbol(e[1], integer=True)
    if e[0] == "const":
        return sp.Integer(e[1])
    a, b = to_sympy(e[1], sp), to_sympy(e[2], sp)
    return {"+": a + b, "-": a - b, "*": a * b}[e[0]]


def from_sympy(x, sp):
    if x.is_Integer:
        return ("const", int(x) & MASK)
    if x.is_Symbol:
        return ("var", x.name)
    if isinstance(x, sp.Add):
        args = [from_sympy(a, sp) for a in x.args]
    elif isinstance(x, sp.Mul):
        args = [from_sympy(a, sp) for a in x.args]
    elif isinstance(x, sp.Pow) and x.exp.is_Integer and x.exp > 0:
        base = from_sympy(x.base, sp)
        out = base
        for _ in range(int(x.exp) - 1):
            out = ("*", out, base)
        return out
    else:
        raise ValueError(f"unsupported {type(x)}")
    op = "+" if isinstance(x, sp.Add) else "*"
    out = args[0]
    for a in args[1:]:
        out = (op, out, a)
    return out


def norm_sympy(e):
    sp = _sympy()
    x = sp.expand(to_sympy(e, sp))
    return from_sympy(x, sp)


# ---- egglog: a genuine e-graph arm -----------------------------------------
# Budget declared from a probe, not guessed: with distributivity and i64
# constant folding, 3-4 saturation iterations prove 2x+3x == 5x in ~2.5 ms,
# while 7 iterations exhausted 1.5 GB on that same two-term expression. So the
# iteration count is capped at 4 and expressions above EGG_NODE_CAP skip
# egglog entirely. Every skip and every failure is COUNTED, because an arm that
# silently drops its hard cases is not a measurement.
EGG_ITERS = 4
EGG_NODE_CAP = 40
_EGG = None


def _egg_setup():
    """Build the expression type and ring ruleset once."""
    global _EGG
    if _EGG is not None:
        return _EGG
    from egglog import EGraph, Expr, StringLike, i64, i64Like, rewrite, ruleset, vars_

    class M(Expr):
        def __init__(self, v: i64Like) -> None: ...
        @classmethod
        def var(cls, n: StringLike) -> "M": ...
        def __add__(self, o: "M") -> "M": ...
        def __mul__(self, o: "M") -> "M": ...
        def __sub__(self, o: "M") -> "M": ...

    a, b, c = vars_("a b c", M)
    i, j = vars_("i j", i64)
    rs = ruleset(
        rewrite(a + b).to(b + a),
        rewrite(a * b).to(b * a),
        rewrite((a + b) + c).to(a + (b + c)),
        rewrite((a * b) * c).to(a * (b * c)),
        rewrite(a * (b + c)).to(a * b + a * c),
        rewrite(a * b + a * c).to(a * (b + c)),
        rewrite(a + M(0)).to(a),
        rewrite(a * M(1)).to(a),
        rewrite(a * M(0)).to(M(0)),
        rewrite(a - M(0)).to(a),
        rewrite(M(0) - (M(0) - a)).to(a),
        # i64 two's-complement +,-,* share bit patterns with mod 2^64
        rewrite(M(i) + M(j)).to(M(i + j)),
        rewrite(M(i) * M(j)).to(M(i * j)),
        rewrite(M(i) - M(j)).to(M(i - j)),
    )
    _EGG = (EGraph, M, rs)
    return _EGG


def _to_egg(e, M):
    if e[0] == "var":
        return M.var(e[1])
    if e[0] == "const":
        v = e[1] & MASK
        return M(v - (1 << 64) if v >= (1 << 63) else v)   # to signed i64
    a, b = _to_egg(e[1], M), _to_egg(e[2], M)
    return {"+": a + b, "-": a - b, "*": a * b}[e[0]]


_EGG_TOK = None


def _parse_egg(text):
    """Parse egglog's extracted term into tuple form.

    A tokenising recursive-descent parser, not a string split. The first
    version scanned for the lowest-precedence top-level operator but failed to
    reset its paren depth between the +/- and * passes, so it cut terms in
    half on any nested expression and every egglog request errored.
    """
    global _EGG_TOK
    import re
    if _EGG_TOK is None:
        _EGG_TOK = re.compile(r'M\.var\("([^"]*)"\)|M\((-?\d+)\)|([()+*-])|\s+')
    toks = []
    i = 0
    while i < len(text):
        m = _EGG_TOK.match(text, i)
        if not m:
            raise ValueError(f"lex error at {i}: {text[i:i+30]!r}")
        if m.group(1) is not None:
            toks.append(("var", m.group(1)))
        elif m.group(2) is not None:
            toks.append(("const", int(m.group(2)) & MASK))
        elif m.group(3) is not None:
            toks.append(("op", m.group(3)))
        i = m.end()

    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def eat():
        t = toks[pos[0]]
        pos[0] += 1
        return t

    def atom():
        t = eat()
        if t[0] in ("var", "const"):
            return t
        if t == ("op", "("):
            e = addsub()
            if peek() != ("op", ")"):
                raise ValueError("expected )")
            eat()
            return e
        raise ValueError(f"unexpected {t}")

    def mul():
        e = atom()
        while peek() == ("op", "*"):
            eat()
            e = ("*", e, atom())
        return e

    def addsub():
        e = mul()
        while peek() in (("op", "+"), ("op", "-")):
            op = eat()[1]
            e = (op, e, mul())
        return e

    e = addsub()
    if pos[0] != len(toks):
        raise ValueError(f"trailing tokens at {pos[0]}")
    return e


def norm_egglog(e):
    """Equality saturation over the ring axioms, then extract the smallest
    representative. Two equivalent inputs saturate in SEPARATE e-graphs, so
    whether they extract to the same term is exactly what this arm measures."""
    if nodes(e) > EGG_NODE_CAP:
        raise _Skipped(f"nodes {nodes(e)} > cap {EGG_NODE_CAP}")
    EGraph, M, rs = _egg_setup()
    g = EGraph()
    root = g.let("root", _to_egg(e, M))
    g.run(rs * EGG_ITERS)
    return _parse_egg(str(g.extract(root)))


class _Skipped(Exception):
    pass


# ---- the persistent e-graph: the architecture's actual design ---------------
# Added AFTER discovering that per-request egglog extraction is not canonical:
# egglog proves a*b == b*a, but two separate e-graphs extract different
# representatives, so a fresh e-graph per request cannot produce a cache key.
# One accumulating e-graph can, by asking whether the new request is already
# equal to a term it holds - which is also what "dependency reuse" means in the
# architecture's own description. Declared as an addition, not pre-registered
# as a separate arm.
class PersistentEgraph:
    def __init__(self, iters=EGG_ITERS, node_cap=EGG_NODE_CAP):
        self.EGraph, self.M, self.rs = _egg_setup()
        self.g = self.EGraph()
        self.iters, self.node_cap = iters, node_cap
        self.roots = []          # (label, egg_root)
        self.saturations = 0
        self._n = 0              # monotonic: let-labels must never be reused

    def canonical_for(self, e):
        """Return a stable label for e's equivalence class, or None."""
        from egglog import eq
        if nodes(e) > self.node_cap:
            raise _Skipped(f"nodes {nodes(e)} > cap {self.node_cap}")
        self._n += 1
        label = f"r{self._n}"
        root = self.g.let(label, _to_egg(e, self.M))
        self.g.run(self.rs * self.iters)
        self.saturations += 1
        for prev_label, prev_root in self.roots:
            try:
                self.g.check(eq(root).to(prev_root))
                return prev_label           # already known equivalent
            except Exception:
                continue
        self.roots.append((label, root))
        return label


# ------------------------------------------------------------ arms
ARMS = ("direct", "memo", "memo_canon", "memo_sympy", "memo_egglog")
NORMALISERS = {"direct": None, "memo": norm_identity, "memo_canon": norm_canon,
               "memo_sympy": norm_sympy, "memo_egglog": norm_egglog}


def run_arm(arm, requests, op_cost_us=0.0):
    """Answer every request under one policy.

    op_cost_us simulates a primitive operation that costs more than integer
    arithmetic does, which is how the break-even in Y7 is found. It is charged
    as accounted time per executed operation, not by busy-waiting, so the
    sweep is exact rather than noisy.
    """
    norm = NORMALISERS[arm]
    cache = {}
    stats = {"arm": arm, "requests": len(requests), "executed": 0, "hits": 0,
             "ops_executed": 0, "norm_timeouts": 0, "norm_ms": 0.0,
             "exec_ms": 0.0, "lookup_ms": 0.0, "mismatches": 0,
             "norm_node_growth": 0, "norm_skipped": 0, "norm_errors": 0,
             "per_request": []}
    results = []

    for r in requests:
        e, env = tuple_of(r["expr"]), r["env"]
        t_req = time.perf_counter()

        key = None
        if norm is not None:
            t0 = time.perf_counter()
            if arm in ("memo_sympy", "memo_egglog"):
                try:
                    ne = _guard(norm, e)
                except _TO:
                    stats["norm_timeouts"] += 1
                    ne = e
                except _Skipped:
                    stats["norm_skipped"] += 1
                    ne = e
                except Exception:
                    stats["norm_errors"] += 1
                    ne = e
            else:
                ne = norm(e)
            stats["norm_ms"] += (time.perf_counter() - t0) * 1000.0
            stats["norm_node_growth"] += nodes(ne) - nodes(e)
            t0 = time.perf_counter()
            key = (syntax_key(ne), env_key(ne, env))
            stats["lookup_ms"] += (time.perf_counter() - t0) * 1000.0
        else:
            ne = e

        if key is not None and key in cache:
            val = cache[key]
            stats["hits"] += 1
        else:
            c = [0]
            t0 = time.perf_counter()
            val = evaluate(ne, env, c)
            stats["exec_ms"] += (time.perf_counter() - t0) * 1000.0
            stats["ops_executed"] += c[0]
            stats["executed"] += 1
            if key is not None:
                cache[key] = val

        results.append(val)
        stats["per_request"].append({
            "id": r["id"], "case": r["case"], "split": r["split"],
            "ms": (time.perf_counter() - t_req) * 1000.0})

    stats["cache_entries"] = len(cache)
    stats["cache_bytes"] = len(json.dumps(
        [[list(map(str, k)), v] for k, v in cache.items()]))
    # accounted total: measured time plus the simulated per-operation cost
    stats["total_ms"] = stats["norm_ms"] + stats["exec_ms"] + stats["lookup_ms"]
    stats["accounted_ms"] = stats["total_ms"] + \
        stats["ops_executed"] * op_cost_us / 1000.0
    return stats, results


def tuple_of(x):
    """JSON round-trips tuples to lists; expressions must be hashable."""
    if isinstance(x, (list, tuple)):
        return tuple(tuple_of(i) for i in x)
    return x
