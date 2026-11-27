"""FPCore corpus loader for experiment 004.

Parses the pinned FPBench/Herbie corpus into SymPy expressions plus a
sampling domain. Deliberately boring: the experiment's credibility rests on
this stage being faithful, so every expression it cannot handle is COUNTED
AND REPORTED rather than quietly dropped.
"""
from __future__ import annotations

import math
import pathlib
import re
import signal
from dataclasses import dataclass, field

import sympy as sp

# ---------------------------------------------------------------- s-expr
# FPCore writes let-bindings with square brackets: (let ([x 1] [y 2]) body).
# Brackets are delimiters, exactly like parens.
TOKEN = re.compile(r'[()\[\]]|"[^"]*"|;[^\n]*|[^\s()\[\]";]+')


def tokenize(text: str):
    for m in TOKEN.finditer(text):
        t = m.group(0)
        if not t.startswith(";"):
            yield t


def parse_all(text: str):
    """Return every top-level s-expression in the file."""
    stack, out = [], []
    for t in tokenize(text):
        if t in "([":
            stack.append([])
        elif t in ")]":
            if not stack:
                continue
            done = stack.pop()
            (stack[-1] if stack else out).append(done)
        else:
            if stack:
                stack[-1].append(t)
    return out


# ---------------------------------------------------------------- operators
# FPCore op -> sympy builder. Only real-valued, side-effect-free ops.
UNARY = {
    "sqrt": sp.sqrt, "exp": sp.exp, "log": sp.log, "sin": sp.sin,
    "cos": sp.cos, "tan": sp.tan, "atan": sp.atan, "asin": sp.asin,
    "acos": sp.acos, "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "asinh": sp.asinh, "acosh": sp.acosh, "atanh": sp.atanh,
    "fabs": sp.Abs, "cbrt": sp.real_root and (lambda a: sp.real_root(a, 3)),
    "exp2": lambda a: sp.Pow(2, a), "log2": lambda a: sp.log(a, 2),
    "log10": lambda a: sp.log(a, 10), "expm1": lambda a: sp.exp(a) - 1,
    "log1p": lambda a: sp.log(1 + a), "floor": sp.floor, "ceil": sp.ceiling,
}
BINARY = {
    "pow": lambda a, b: sp.Pow(a, b),
    "atan2": lambda a, b: sp.atan2(a, b),
    "hypot": lambda a, b: sp.sqrt(a ** 2 + b ** 2),
    "fmax": sp.Max, "fmin": sp.Min,
    "fmod": sp.Mod, "copysign": lambda a, b: sp.Abs(a) * sp.sign(b),
}
# Constructs this experiment does not model. Counted, not hidden.
REJECT_HEADS = {"while", "while*", "for", "for*", "tensor", "tensor*",
                "array", "dim", "ref", "size", "if", "digits"}


class Unsupported(Exception):
    pass


CONSTANTS = {
    "PI": sp.pi, "E": sp.E, "INFINITY": sp.oo, "NAN": sp.nan,
    "LOG2E": 1 / sp.log(2), "LOG10E": 1 / sp.log(10), "LN2": sp.log(2),
    "LN10": sp.log(10), "PI_2": sp.pi / 2, "PI_4": sp.pi / 4,
    "M_1_PI": 1 / sp.pi, "M_2_PI": 2 / sp.pi, "SQRT2": sp.sqrt(2),
    "SQRT1_2": 1 / sp.sqrt(2), "TRUE": sp.true, "FALSE": sp.false,
}


def _num(tok: str):
    """FPCore numbers, including the Racket literal forms this corpus uses:
    exact rationals (1/2) and single-float suffixes (0.6931f0)."""
    try:
        if re.fullmatch(r'[+-]?\d+', tok):
            return sp.Integer(int(tok))
        m = re.fullmatch(r'([+-]?\d+)/(\d+)', tok)
        if m:
            return sp.Rational(int(m.group(1)), int(m.group(2)))
        t = re.sub(r'[fdFD]0?$', '', tok)
        return sp.Float(float(t), 17)
    except (ValueError, ZeroDivisionError):
        return None


def to_sympy(node, env: dict):
    """FPCore AST -> sympy. Raises Unsupported for anything out of scope."""
    if isinstance(node, str):
        if node in env:
            return env[node]
        if node in CONSTANTS:
            return CONSTANTS[node]
        n = _num(node)
        if n is not None:
            return n
        raise Unsupported(f"free symbol {node!r}")

    if not node:
        raise Unsupported("empty form")
    head = node[0]

    if isinstance(head, list):
        raise Unsupported("computed head")
    if head in REJECT_HEADS:
        raise Unsupported(head)

    if head == "!":                       # (! :prop val ... body)
        return to_sympy(node[-1], env)

    if head in ("let", "let*"):
        bindings = node[1]
        if not isinstance(bindings, list):
            raise Unsupported("malformed let")
        local = dict(env)
        for b in bindings:
            if not (isinstance(b, list) and len(b) == 2):
                raise Unsupported("malformed binding")
            name, val = b
            # let* binds sequentially; let is simultaneous. Inlining the
            # sequential reading is safe for let too because FPCore forbids
            # rebinding a name inside its own simultaneous group.
            local[name] = to_sympy(val, local if head == "let*" else env)
        return to_sympy(node[2], local)

    args = node[1:]
    if head == "-" and len(args) == 1:
        return -to_sympy(args[0], env)
    if head == "+":
        return sp.Add(*[to_sympy(a, env) for a in args])
    if head == "*":
        return sp.Mul(*[to_sympy(a, env) for a in args])
    if head == "-":
        acc = to_sympy(args[0], env)
        for a in args[1:]:
            acc = acc - to_sympy(a, env)
        return acc
    if head == "/":
        if len(args) == 1:
            return 1 / to_sympy(args[0], env)
        acc = to_sympy(args[0], env)
        for a in args[1:]:
            acc = acc / to_sympy(a, env)
        return acc
    if head == "fma":
        a, b, c = (to_sympy(x, env) for x in args)
        return a * b + c
    if head in UNARY and len(args) == 1:
        return UNARY[head](to_sympy(args[0], env))
    if head in BINARY and len(args) == 2:
        return BINARY[head](*[to_sympy(a, env) for a in args])
    raise Unsupported(f"op {head}/{len(args)}")


# ---------------------------------------------------------------- domains
INTERVAL_DEFAULT = (0.5, 2.0)   # declared default when :pre says nothing


def _flt(tok):
    if isinstance(tok, str):
        if tok in CONSTANTS:
            try:
                return float(CONSTANTS[tok])
            except TypeError:
                return None
        n = _num(tok)
        if n is not None:
            try:
                return float(n)
            except TypeError:
                return None
    return None


def parse_pre(pre, names):
    """Extract per-variable intervals from a :pre clause.

    Handles the shapes that actually occur in this corpus: (and ...),
    (<= a x b), (< a x b), (<= x b), (>= x a), (> x a), (!= x 0).
    Anything else contributes no bound; that variable keeps the default.
    """
    lo = {n: None for n in names}
    hi = {n: None for n in names}
    nonzero = set()

    def visit(f):
        if not isinstance(f, list) or not f:
            return
        h = f[0]
        if h in ("and", "or"):
            for sub in f[1:]:
                visit(sub)
            return
        if h == "!=":
            for a in f[1:]:
                if isinstance(a, str) and a in lo:
                    for b in f[1:]:
                        if _flt(b) == 0.0:
                            nonzero.add(a)
            return
        if h not in ("<=", "<", ">=", ">"):
            return
        parts = f[1:]
        asc = h in ("<=", "<")
        for i, p in enumerate(parts):
            if not (isinstance(p, str) and p in lo):
                continue
            left = _flt(parts[i - 1]) if i > 0 else None
            right = _flt(parts[i + 1]) if i + 1 < len(parts) else None
            l, r = (left, right) if asc else (right, left)
            if l is not None:
                lo[p] = l if lo[p] is None else max(lo[p], l)
            if r is not None:
                hi[p] = r if hi[p] is None else min(hi[p], r)

    if pre is not None:
        visit(pre)

    out = {}
    for n in names:
        a, b = lo[n], hi[n]
        if a is None and b is None:
            a, b = INTERVAL_DEFAULT
        elif a is None:
            a = b - abs(b) - 1.0 if math.isfinite(b) else INTERVAL_DEFAULT[0]
        elif b is None:
            b = a + abs(a) + 1.0 if math.isfinite(a) else INTERVAL_DEFAULT[1]
        if not (math.isfinite(a) and math.isfinite(b)):
            a, b = INTERVAL_DEFAULT
        if a > b:
            a, b = b, a
        if a == b:
            b = a + 1e-6
        out[n] = (a, b, n in nonzero)
    return out


# ---------------------------------------------------------------- guards
# Three Herbie graphics cores (fidget bear/colonnade/prospero) are
# implicit-surface CSG expressions thousands of nodes deep. SymPy's automatic
# evaluation does not terminate on them in any useful time. They are excluded
# by an explicit node cap and counted, not silently skipped.
NODE_CAP = 2000
CONVERT_TIMEOUT_S = 10.0


def ast_nodes(node):
    if isinstance(node, str):
        return 1
    return 1 + sum(ast_nodes(c) for c in node)


class _Timeout(Exception):
    pass


def _alarm(*_a):
    raise _Timeout()


# ---------------------------------------------------------------- records
@dataclass
class Core:
    source: str
    name: str
    args: list
    expr: object
    domain: dict
    props: dict = field(default_factory=dict)


def props_of(core):
    """Read :key value pairs between the arg list and the body."""
    out, i = {}, 2
    while i < len(core) - 1:
        k = core[i]
        if isinstance(k, str) and k.startswith(":"):
            out[k[1:]] = core[i + 1]
            i += 2
        else:
            break
    return out, i


def arg_names(spec):
    names = []
    for a in spec:
        if isinstance(a, str):
            names.append(a)
        elif isinstance(a, list):
            # (! :prop v x) or (x dims...) - take the last plain symbol
            plain = [t for t in a if isinstance(t, str) and not t.startswith(":")]
            if plain:
                names.append(plain[-1])
    return names


def load(root="bench/corpus"):
    """Yield (cores, stats). Every rejection is tallied by reason."""
    cores, stats = [], {"files": 0, "fpcores": 0, "ok": 0, "rejected": {}}
    signal.signal(signal.SIGALRM, _alarm)
    for path in sorted(pathlib.Path(root).rglob("*.fpcore")):
        stats["files"] += 1
        try:
            forms = parse_all(path.read_text(errors="replace"))
        except Exception as exc:
            stats["rejected"]["parse:" + type(exc).__name__] = \
                stats["rejected"].get("parse:" + type(exc).__name__, 0) + 1
            continue
        for form in forms:
            if not (isinstance(form, list) and form and form[0] == "FPCore"):
                continue
            stats["fpcores"] += 1
            try:
                spec = form[1]
                if isinstance(spec, str):       # named FPCore: (FPCore name (args) ...)
                    spec = form[2]
                    body_off = 3
                else:
                    body_off = 2
                names = arg_names(spec)
                props, _ = props_of(form if body_off == 2 else form[1:])
                body = form[-1]
                nodes = ast_nodes(body)
                if nodes > NODE_CAP:
                    raise Unsupported(f"node-cap({nodes})")
                env = {n: sp.Symbol(n, real=True) for n in names}
                signal.setitimer(signal.ITIMER_REAL, CONVERT_TIMEOUT_S)
                try:
                    expr = to_sympy(body, env)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                if not names:
                    raise Unsupported("no arguments")
                if expr.free_symbols - set(env.values()):
                    raise Unsupported("unbound symbol in body")
                dom = parse_pre(props.get("pre"), names)
                cores.append(Core(
                    source=str(path), name=props.get("name", path.stem),
                    args=names, expr=expr, domain=dom, props=props))
                stats["ok"] += 1
            except _Timeout:
                stats["rejected"]["convert-timeout"] = \
                    stats["rejected"].get("convert-timeout", 0) + 1
            except Unsupported as exc:
                key = str(exc).split()[0]
                stats["rejected"][key] = stats["rejected"].get(key, 0) + 1
            except Exception as exc:
                key = "error:" + type(exc).__name__
                stats["rejected"][key] = stats["rejected"].get(key, 0) + 1
    return cores, stats


if __name__ == "__main__":
    cores, stats = load()
    print(f"files={stats['files']} fpcores={stats['fpcores']} parsed={stats['ok']}")
    print("rejected:")
    for k, v in sorted(stats["rejected"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:>4}  {k}")
    print("\nsample:")
    for c in cores[:6]:
        print(f"  [{pathlib.Path(c.source).stem}] {c.name}")
        print(f"      args={c.args} dom={ {k:(round(v[0],3),round(v[1],3)) for k,v in c.domain.items()} }")
        print(f"      {c.expr}")
