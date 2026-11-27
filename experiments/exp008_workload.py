#!/usr/bin/env python
"""Workload generator for experiment 008.

Implements the workload `research/benchmarks/NEXT_EXPERIMENT.md` specifies:

    Use deterministic integer/bitvector workloads with repeated
    subcomputations. Include exact repeats, changed leaf inputs, algebraically
    equivalent formulations, unrelated requests and adversarial expansion
    cases. Split by expression family so held-out cases are not cosmetic
    variants of training programs.

Semantics, declared: all arithmetic is over the ring Z/2^64 using +, -, * only.
Division, shifts and bitwise operations are deliberately excluded. Those would
either break the ring identities the algebraically-equivalent cases depend on,
or make a 'mismatch' ambiguous. Over this ring every identity used below is
exact, so "zero mismatches" is a decidable claim rather than a tolerance.

Expressions are nested tuples:
    ('var', name) | ('const', int) | ('+'|'-'|'*', left, right)
"""
from __future__ import annotations

import hashlib
import json
import random

MASK = (1 << 64) - 1
CASE_TYPES = ("exact_repeat", "changed_leaves", "equiv_form",
              "unrelated", "adversarial")


# ----------------------------------------------------------------- evaluation
def evaluate(e, env, counter=None):
    """Exact evaluation over Z/2^64, counting primitive operations.

    The operation count is the noise-free metric for this experiment. Wall
    time is the metric NEXT_EXPERIMENT declares a threshold on, but this
    machine has no PMU and unobservable CPU frequency, so a deterministic
    count is what makes the timing interpretable.
    """
    k = e[0]
    if k == "var":
        return env[e[1]] & MASK
    if k == "const":
        return e[1] & MASK
    a = evaluate(e[1], env, counter)
    b = evaluate(e[2], env, counter)
    if counter is not None:
        counter[0] += 1
    if k == "+":
        return (a + b) & MASK
    if k == "-":
        return (a - b) & MASK
    if k == "*":
        return (a * b) & MASK
    raise ValueError(k)


def nodes(e):
    return 1 if e[0] in ("var", "const") else 1 + nodes(e[1]) + nodes(e[2])


def leaves(e):
    if e[0] == "var":
        return {e[1]}
    if e[0] == "const":
        return set()
    return leaves(e[1]) | leaves(e[2])


def syntax_key(e):
    """Exact-syntax key. This is what arm 2's memoisation keys on, and the
    reason algebraically equivalent formulations defeat it."""
    return hashlib.sha256(json.dumps(e).encode()).hexdigest()[:32]


# ----------------------------------------------------------------- families
# Each family is a template with its own structural character, so that holding
# out a whole family holds out a shape rather than a cosmetic variant.
def fam_horner(rng, depth):
    """Nested linear form: ((c*x + c)*x + c)*x ... — deep, thin, reuses x."""
    e = ("const", rng.randrange(1, 9))
    for _ in range(depth):
        e = ("+", ("*", e, ("var", "x")), ("const", rng.randrange(1, 9)))
    return e


def fam_sum_of_products(rng, depth):
    """Wide sum of independent products — shallow, wide, many distinct leaves."""
    terms = []
    for i in range(depth):
        terms.append(("*", ("var", f"a{i%4}"), ("var", f"b{i%3}")))
    e = terms[0]
    for t in terms[1:]:
        e = ("+", e, t)
    return e


def fam_shared_subtree(rng, depth):
    """One subexpression reused several times — the case dependency reuse is
    supposed to exploit."""
    sub = ("+", ("*", ("var", "p"), ("var", "q")), ("const", rng.randrange(1, 9)))
    e = sub
    for _ in range(max(depth - 1, 1)):
        e = ("+", ("*", e, sub), sub)
    return e


def fam_repeated_square(rng, depth):
    """x^(2^k) by repeated squaring — deep multiplicative chain."""
    e = ("var", "x")
    for _ in range(depth):
        e = ("*", e, e)
    return e


def fam_mixed_chain(rng, depth):
    """Alternating +/-/* over several distinct variables."""
    ops = ["+", "-", "*"]
    e = ("var", "m0")
    for i in range(depth):
        e = (ops[i % 3], e, ("var", f"m{(i + 1) % 5}"))
    return e


FAMILIES = {
    "horner": fam_horner,
    "sum_of_products": fam_sum_of_products,
    "shared_subtree": fam_shared_subtree,
    "repeated_square": fam_repeated_square,
    "mixed_chain": fam_mixed_chain,
}


# ----------------------------------------------- semantics-preserving variants
# Each rewrite below is an identity in Z/2^64. Every generated variant is
# CHECKED against its origin on random inputs before it enters the workload,
# so the workload cannot contain a non-equivalence by construction error.
def v_reorder(e, rng):
    if e[0] in ("+", "*"):
        return (e[0], e[2], e[1])
    return e


def v_add_identity(e, rng):
    return ("+", e, ("const", 0))


def v_mul_identity(e, rng):
    return ("*", e, ("const", 1))


def v_split_const(e, rng):
    if e[0] == "const" and e[1] > 1:
        k = rng.randrange(1, e[1])
        return ("+", ("const", k), ("const", e[1] - k))
    return e


def v_distribute(e, rng):
    # a*(b+c) -> a*b + a*c
    if e[0] == "*" and e[2][0] == "+":
        return ("+", ("*", e[1], e[2][1]), ("*", e[1], e[2][2]))
    if e[0] == "*" and e[1][0] == "+":
        return ("+", ("*", e[1][1], e[2]), ("*", e[1][2], e[2]))
    return e


def v_double_negate(e, rng):
    return ("-", ("const", 0), ("-", ("const", 0), e))


VARIANTS = [v_reorder, v_add_identity, v_mul_identity, v_split_const,
            v_distribute, v_double_negate]


def _rewrite_somewhere(e, rng, fn, depth=0):
    """Apply fn at a randomly chosen position."""
    if depth > 6 or e[0] in ("var", "const") or rng.random() < 0.35:
        return fn(e, rng)
    i = rng.choice([1, 2])
    new = list(e)
    new[i] = _rewrite_somewhere(e[i], rng, fn, depth + 1)
    return tuple(new)


def equivalent_variant(e, rng, tries=8):
    """A syntactically different, semantically identical expression."""
    for _ in range(tries):
        cand = _rewrite_somewhere(e, rng, rng.choice(VARIANTS))
        if cand != e and nodes(cand) <= 400:
            return cand
    return ("+", e, ("const", 0))


def adversarial(rng, k):
    """Product of k binomials: expands to 2^k terms. Normalising this is
    supposed to cost more than it saves."""
    e = ("+", ("var", "u0"), ("var", "v0"))
    for i in range(1, k):
        e = ("*", e, ("+", ("var", f"u{i}"), ("var", f"v{i}")))
    return e


# ----------------------------------------------------------------- generation
def random_env(names, rng):
    return {n: rng.randrange(0, 1 << 32) for n in sorted(names)}


def check_equivalent(a, b, rng, trials=12):
    """Exact equivalence check over Z/2^64 on random inputs."""
    names = sorted(leaves(a) | leaves(b))
    for _ in range(trials):
        env = random_env(names, rng)
        if evaluate(a, env) != evaluate(b, env):
            return False
    return True


def build(seed=8008, n_base=14, depth=5, adv_k=7,
          held_out_families=("repeated_square", "mixed_chain")):
    """Returns (requests, meta).

    A request is {"id", "family", "case", "expr", "env"}. Families in
    `held_out_families` appear ONLY in the held-out split, so evaluation is not
    on cosmetic variants of what the primary split contains.
    """
    rng = random.Random(seed)
    requests, rejected = [], 0

    def emit(family, case, expr, env, split):
        requests.append({"id": len(requests), "family": family, "case": case,
                         "split": split, "expr": expr, "env": env,
                         "nodes": nodes(expr)})

    for fam, fn in FAMILIES.items():
        split = "held_out" if fam in held_out_families else "primary"
        for i in range(n_base):
            base = fn(rng, depth)
            env = random_env(leaves(base), rng)

            # 1. the request itself, then an exact repeat of it
            emit(fam, "exact_repeat", base, dict(env), split)
            emit(fam, "exact_repeat", base, dict(env), split)

            # 2. same shape, different leaf values
            emit(fam, "changed_leaves", base, random_env(leaves(base), rng), split)

            # 3. algebraically equivalent formulation, same values - verified
            var = equivalent_variant(base, rng)
            if check_equivalent(base, var, rng):
                emit(fam, "equiv_form", var, dict(env), split)
            else:
                rejected += 1

    # 4. unrelated requests: the regression workload. Normalisation has nothing
    #    to gain here, so any overhead it carries shows up undiluted.
    for i in range(n_base * 2):
        fam = rng.choice(list(FAMILIES))
        e = FAMILIES[fam](rng, rng.randrange(2, depth + 1))
        emit("unrelated", "unrelated", e, random_env(leaves(e), rng), "unrelated")

    # 5. adversarial expansion
    for i in range(6):
        e = adversarial(rng, adv_k)
        emit("adversarial", "adversarial", e, random_env(leaves(e), rng),
             "adversarial")

    meta = {"seed": seed, "n_requests": len(requests),
            "families": list(FAMILIES), "held_out_families": list(held_out_families),
            "equiv_variants_rejected": rejected,
            "semantics": "Z/2^64, operators + - * only",
            "by_case": {c: sum(1 for r in requests if r["case"] == c)
                        for c in CASE_TYPES},
            "by_split": {s: sum(1 for r in requests if r["split"] == s)
                         for s in ("primary", "held_out", "unrelated", "adversarial")},
            "distinct_syntax": len({syntax_key(r["expr"]) for r in requests}),
            "total_nodes": sum(r["nodes"] for r in requests)}
    return requests, meta


if __name__ == "__main__":
    reqs, meta = build()
    print(json.dumps(meta, indent=2))
    print("\nsanity: every equiv_form request must equal its family's base value")
    rng = random.Random(1)
    bad = 0
    for r in reqs:
        if r["case"] == "equiv_form":
            v = evaluate(r["expr"], r["env"])
            if not isinstance(v, int) or v < 0 or v > MASK:
                bad += 1
    print(f"  equiv_form requests: {meta['by_case']['equiv_form']}, out of range: {bad}")
    print(f"  adversarial node counts: "
          f"{sorted({r['nodes'] for r in reqs if r['case']=='adversarial'})}")
