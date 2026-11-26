"""Experiment 003 - does a MEASURED cost function beat a structural one?

WHY THIS ONE
    PRIOR_ART.md closed the question of whether cost-driven selection among
    equivalent representations exists. It does, three times over. But egg's
    own limitation field says "extracted cost need not predict latency" and
    Stitch's says "shorter programs need not execute faster". Experiment 002
    reproduced that defect from scratch: its structural metric improved 2.80x
    while its physical metric improved 1.06x.

    So the gap is not the selector. It is the cost function feeding it.

DOMAIN CHOSEN SO THE PROXY MUST FAIL
    Convolution. conv(a,b) == ifft(fft(a) * fft(b)) exactly (within integer
    exactness limits we check explicitly). Direct convolution is O(n^2) and
    wins for small n. The FFT route is O(n log n) and wins for large n. The
    crossover is a property of THIS MACHINE and no structural reasoning can
    produce it.

    No backend compiler rescues this. It is an algorithmic choice, not
    instruction selection, which is what made the simpler arithmetic version
    of this experiment pointless.

ARMS
    1. ast_size     - fewest nodes. The proxy egg warns about.
    2. static_weight- hand-assigned per-operator weights, size independent.
                      ONE weight assignment must serve every n.
    3. measured     - per-operator cost microbenchmarked on this machine at
                      this n, injected through egglog's DagCostModel.
    4. oracle       - run both routes, keep the faster. Upper bound.

PRE-REGISTERED PREDICTIONS (committed before the first run)
    R1  A crossover n* exists on this machine; 64 <= n* <= 4096.
    R2  ast_size picks the direct route at EVERY n, because it is always
        fewer nodes, so it loses to the oracle above n* by a margin that
        grows with n.
    R3  static_weight cannot match the oracle across the whole range with a
        single weight assignment - it is wrong at one end or the other. This
        is a structural impossibility, not a tuning failure: one scalar per
        operator cannot encode an n-dependent crossover.
    R4  measured matches the oracle at every n, within measurement noise
        (<= 5% of oracle runtime).
    R5  measurement is not free. Expect the per-n calibration to cost more
        than a single resolution at that n, so measured-cost extraction only
        repays across repeated requests - a break-even count, as in 002.
    R6  exactness: all routes agree bit-for-bit on integer inputs at every n.

HOW THIS KILLS THE IDEA
    If R4 fails - if measured costs do not track actual runtime well enough
    to beat a hand-tuned static table - then the whole "measure, don't
    assume" premise is unsupported and the architecture should use static
    tables like everyone else.
    If R5 turns out so bad that calibration never repays in any realistic
    request volume, measured costing is a laboratory result, not a mechanism.
"""
from __future__ import annotations

import json
import time

import numpy as np
from egglog import DagCostModel, EGraph, Expr, StringLike, function, rewrite, ruleset, vars_

SIZES = (16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192)
REPEATS = 7


# -- the two equal routes, as real kernels -------------------------------
def conv_direct(a, b):
    return np.convolve(a, b)


def conv_fft(a, b):
    n = len(a) + len(b) - 1
    size = 1 << (n - 1).bit_length()
    fa = np.fft.rfft(a, size)
    fb = np.fft.rfft(b, size)
    return np.rint(np.fft.irfft(fa * fb, size)[:n]).astype(np.int64)


# -- the e-graph: one rule, the convolution theorem ----------------------
class Sig(Expr):
    @classmethod
    def var(cls, name: StringLike) -> "Sig": ...


@function
def conv(a: Sig, b: Sig) -> Sig: ...
@function
def fft(a: Sig) -> Sig: ...
@function
def ifft(a: Sig) -> Sig: ...
@function
def pointwise(a: Sig, b: Sig) -> Sig: ...


x, y = vars_("x y", Sig)
theorem = ruleset(
    rewrite(conv(x, y)).to(ifft(pointwise(fft(x), fft(y)))),
    rewrite(ifft(pointwise(fft(x), fft(y)))).to(conv(x, y)),
)

OPS = ("conv", "fft", "ifft", "pointwise")


def op_of(expr) -> str:
    s = str(expr)
    for name in OPS:
        if s.startswith(name + "("):
            return name
    return "var"


def extract_with(graph, root, weights):
    """Extraction driven by a weight table - the only thing that differs
    between arms 1, 2 and 3."""
    model = DagCostModel(
        marginal_cost=lambda _g, e: float(weights.get(op_of(e), 0.0)),
        identity=0.0,
    )
    return graph.extract(root, cost_model=model)


# -- measurement ---------------------------------------------------------
def time_route(fn, a, b, repeats=REPEATS):
    fn(a, b)                                     # warm
    best = min(_timed(fn, a, b) for _ in range(repeats))
    return best


def _timed(fn, a, b):
    t = time.perf_counter()
    fn(a, b)
    return (time.perf_counter() - t) * 1000.0


def calibrate(n, rng):
    """Microbenchmark each operator at this n. This is the measured arm's
    cost model, and its price is charged in the results."""
    a = rng.integers(0, 64, size=n).astype(np.int64)
    t0 = time.perf_counter()
    size = 1 << (2 * n - 2).bit_length()
    fa = np.fft.rfft(a, size)
    ms_fft = min(_time_call(lambda: np.fft.rfft(a, size)) for _ in range(3))
    ms_ifft = min(_time_call(lambda: np.fft.irfft(fa * fa, size)) for _ in range(3))
    ms_point = min(_time_call(lambda: fa * fa) for _ in range(3))
    ms_conv = min(_time_call(lambda: np.convolve(a, a)) for _ in range(3))
    cal_ms = (time.perf_counter() - t0) * 1000.0
    return {"conv": ms_conv, "fft": ms_fft, "ifft": ms_ifft,
            "pointwise": ms_point, "var": 0.0}, cal_ms


def _time_call(fn):
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000.0


ARMS = {
    "ast_size": {"conv": 1.0, "fft": 1.0, "ifft": 1.0, "pointwise": 1.0, "var": 1.0},
    # one scalar per operator, chosen once, must serve every n
    "static_weight": {"conv": 4.0, "fft": 1.0, "ifft": 1.0, "pointwise": 0.5, "var": 0.0},
}


def run():
    rng = np.random.default_rng(11)
    rows = []
    for n in SIZES:
        a = rng.integers(0, 64, size=n).astype(np.int64)
        b = rng.integers(0, 64, size=n).astype(np.int64)

        exact = np.array_equal(conv_direct(a, b), conv_fft(a, b))
        ms_direct = time_route(conv_direct, a, b)
        ms_fft = time_route(conv_fft, a, b)
        oracle_route = "direct" if ms_direct <= ms_fft else "fft"
        oracle_ms = min(ms_direct, ms_fft)

        measured_w, cal_ms = calibrate(n, rng)

        picks = {}
        for arm, weights in {**ARMS, "measured": measured_w}.items():
            graph = EGraph()
            root = conv(Sig.var("a"), Sig.var("b"))
            graph.register(root)
            graph.run(theorem * 3)
            got = extract_with(graph, root, weights)
            picks[arm] = "direct" if op_of(got) == "conv" else "fft"

        row = {
            "n": n, "exact": bool(exact),
            "ms_direct": ms_direct, "ms_fft": ms_fft,
            "oracle_route": oracle_route, "oracle_ms": oracle_ms,
            "calibration_ms": cal_ms,
            **{f"pick_{k}": v for k, v in picks.items()},
            **{f"regret_{k}": (ms_direct if picks[k] == "direct" else ms_fft) / oracle_ms
               for k in picks},
        }
        rows.append(row)
        print(f"n={n:>5} exact={str(exact):>5} direct={ms_direct:8.3f}ms "
              f"fft={ms_fft:8.3f}ms oracle={oracle_route:>6} | "
              + " ".join(f"{k}={picks[k]:>6}(x{row['regret_'+k]:.2f})" for k in picks)
              + f" | calib={cal_ms:.2f}ms")

    with open("experiments/exp003_results.json", "w") as fh:
        json.dump(rows, fh, indent=2)

    print("\n-- summary --")
    for arm in ("ast_size", "static_weight", "measured"):
        worst = max(r[f"regret_{arm}"] for r in rows)
        matched = sum(1 for r in rows if r[f"pick_{arm}"] == r["oracle_route"])
        print(f"{arm:>14}: matches oracle {matched}/{len(rows)}, worst regret x{worst:.2f}")
    xover = [r["n"] for r in rows if r["oracle_route"] == "fft"]
    print(f"crossover n* = {min(xover) if xover else 'none in range'}")
    print(f"exact at every n: {all(r['exact'] for r in rows)}")


if __name__ == "__main__":
    run()
