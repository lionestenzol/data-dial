#!/usr/bin/env python
"""Render and validate research/OBJECTIVES.json.

Read-only. Exits non-zero on any inconsistency, in the shape of
exp004_verify_corpus.py - the only other validated manifest in this repo.

Why a script rather than a markdown table: objective status here used to live
as prose in whichever document raised it, and it drifted. 005's recommendation
was reversed by 006 while 005's own findings section still read as current
advice; three documents each claimed to name "the next experiment". A table
would drift the same way. This makes a false "closed" an error instead of
something a reader has to catch.

Usage:
    .venv-research/bin/python -I experiments/objectives_status.py
    .venv-research/bin/python -I experiments/objectives_status.py --drift
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

LEDGER = pathlib.Path("research/OBJECTIVES.json")
STATUSES = ("closed", "closed-superseded", "queued", "blocked", "dormant",
            "spec-gap", "abandoned")
# Status order for display: what is done, what is next, what is parked.
ORDER = {s: i for i, s in enumerate(
    ("closed", "closed-superseded", "queued", "blocked", "dormant",
     "spec-gap", "abandoned"))}
OPEN_STATUSES = ("queued", "blocked", "dormant", "spec-gap")

SEARCH_DOCS = ("HANDOFF.md", "README.md", "RESULTS.md",
               "experiments/FINDINGS.md", "research/ARCHITECTURAL_GAPS.md",
               "research/CAPABILITIES.md", "research/RIV_Research_Report.md",
               "research/benchmarks/NEXT_EXPERIMENT.md",
               "research/findings/SELECTOR_GAP.md",
               "research/findings/VERIFICATION.md",
               "research/rejected_mechanisms/DECISIONS.md")


def fail(errors, msg):
    errors.append(msg)


def check(led):
    """Every rule here exists because something actually went wrong once."""
    errors, warnings = [], []
    objs = led["objectives"]
    ids = {o["id"] for o in objs}

    if len(ids) != len(objs):
        fail(errors, "duplicate objective ids")

    for o in objs:
        oid = o["id"]

        # 1. status is in the vocabulary
        if o["status"] not in STATUSES:
            fail(errors, f"{oid}: status {o['status']!r} not in vocabulary")

        # 2. closed rows must cite evidence that resolves
        if o["status"].startswith("closed"):
            ev = o.get("evidence")
            if not ev:
                fail(errors, f"{oid}: {o['status']} with no evidence")
            else:
                sc = ev.get("scorecard")
                fs = ev.get("findings_section")
                if sc:
                    p = pathlib.Path(sc)
                    if not p.exists():
                        fail(errors, f"{oid}: scorecard {sc} does not exist")
                elif fs:
                    doc = fs.split("#")[0]
                    if not pathlib.Path(doc).exists():
                        fail(errors, f"{oid}: evidence document {doc} does not exist")
                else:
                    fail(errors, f"{oid}: evidence cites neither scorecard nor "
                                 f"findings_section")
        elif o.get("evidence"):
            fail(errors, f"{oid}: status {o['status']} but carries evidence")
        for k, v in (o.get("evidence_pending") or {}).items():
            if not pathlib.Path(v).exists():
                fail(errors, f"{oid}: evidence_pending {k} {v} does not exist")

        # 3. superseded_by must name a real objective
        if o["status"] == "closed-superseded":
            sb = o.get("superseded_by")
            if not sb:
                fail(errors, f"{oid}: closed-superseded with no superseded_by")
            elif sb not in ids:
                fail(errors, f"{oid}: superseded_by {sb!r} is not an objective id")
        elif o.get("superseded_by"):
            fail(errors, f"{oid}: superseded_by set but status is {o['status']}")

        # 4. stated_in must exist - catches objectives orphaned by a rename
        doc = o["stated_in"].split("#")[0]
        if not pathlib.Path(doc).exists():
            fail(errors, f"{oid}: stated_in document {doc} does not exist")

        # 5. blocked_by must resolve, and must not be already closed
        for b in o.get("blocked_by", []):
            if b not in ids:
                fail(errors, f"{oid}: blocked_by {b!r} is not an objective id")
            else:
                dep = next(x for x in objs if x["id"] == b)
                if dep["status"].startswith("closed"):
                    fail(errors, f"{oid}: blocked_by {b} which is already "
                                 f"{dep['status']} - unblock it")
        if o["status"] == "blocked" and not o.get("blocked_by"):
            fail(errors, f"{oid}: status blocked with no blocked_by")
        # dormant means nothing is stopping it, only that nobody is on it.
        # An item with a live prerequisite is blocked, and the distinction
        # matters: HANDOFF called O-recursive and O-transfer merely dormant
        # when both need two unfixed defects repaired first.
        if o["status"] == "dormant" and o.get("blocked_by"):
            fail(errors, f"{oid}: dormant but has blocked_by - use 'blocked'")

    # 6. exit criteria must depend on objectives that exist
    for key in ("exit_criteria", "abandon_criteria"):
        for c in led.get(key, []):
            for d in c["depends_on"]:
                if d not in ids:
                    fail(errors, f"{c['id']}: depends_on {d!r} is not an objective id")
            src = c["source"].split("#")[0].split(" ")[0]
            if src.endswith(".md") and not pathlib.Path(src).exists():
                fail(errors, f"{c['id']}: source document {src} does not exist")

    # warning, not an error: a queued objective with no pre-registration cannot
    # start under working practice 1. That is the true state of O-007 today.
    for o in objs:
        if o["status"] == "queued" and not o.get("is_prereg"):
            # a queued row cannot carry `evidence` (it is not closed), so its
            # pre-registration lives under `evidence_pending`
            ev = o.get("evidence_pending") or o.get("evidence") or {}
            pre = ev.get("preregistration")
            if not pre or not pathlib.Path(pre).exists():
                warnings.append(f"{o['id']}: queued but not yet pre-registered "
                                f"(working practice 1 blocks the run)")
    return errors, warnings


def drift_report(led):
    """For each superseded objective, list documents that still mention it.

    This is the check for what actually went wrong: 005's findings section kept
    presenting a reversed recommendation as current. The script cannot judge
    tone, so it points a human at every place that needs an eye.
    """
    print("\n-- drift watch: documents mentioning a superseded objective --")
    any_hit = False
    for o in led["objectives"]:
        if o["status"] != "closed-superseded":
            continue
        ev = o.get("evidence") or {}
        exp = str(ev.get("experiment", ""))
        needles = [n for n in {exp, o["id"]} if n]
        hits = []
        for doc in SEARCH_DOCS:
            p = pathlib.Path(doc)
            if not p.exists():
                continue
            text = p.read_text(errors="replace")
            for n in needles:
                if re.search(r"\b" + re.escape(n) + r"\b", text):
                    hits.append(doc)
                    break
        if hits:
            any_hit = True
            print(f"  {o['id']} (superseded by {o['superseded_by']}) is "
                  f"mentioned in:")
            for h in sorted(set(hits)):
                print(f"      {h}")
    if not any_hit:
        print("  no superseded objectives mentioned anywhere")
    print("  -> confirm by eye that none of these states the superseded "
          "conclusion as current advice")


def render(led):
    # ORDER.get, not ORDER[...]: an unknown status must be reported by check()
    # as an inconsistency, not crash the renderer before check() ever runs.
    objs = sorted(led["objectives"],
                  key=lambda o: (ORDER.get(o["status"], 99), o["id"]))
    counts = {}
    for o in objs:
        counts[o["status"]] = counts.get(o["status"], 0) + 1

    print("OBJECTIVES  " + " · ".join(
        f"{counts[s]} {s}" for s in STATUSES if s in counts))
    print()
    print(f"{'ID':<22} {'STATUS':<18} {'EVIDENCE / BLOCKER':<34} OBJECTIVE")
    print("-" * 118)
    for o in objs:
        ev = o.get("evidence") or {}
        if o["status"].startswith("closed"):
            sc = ev.get("scorecard")
            if sc and pathlib.Path(sc).exists():
                d = json.load(open(sc))
                detail = f"{ev.get('commit','?')} {d['hits']}/{d['total']} preds"
            else:
                detail = f"{ev.get('commit','?')} (prose)"
            if o["status"] == "closed-superseded":
                detail += f" → {o['superseded_by']}"
        elif o.get("blocked_by"):
            detail = "needs " + ", ".join(o["blocked_by"])
        else:
            detail = ""
        if len(detail) > 33:
            detail = detail[:30] + "..."
        print(f"{o['id']:<22} {o['status']:<18} {detail:<34} {o['objective'][:58]}")

    print("\n## Done when")
    print("   (computed from objective status - never hand-ticked)")
    by_id = {o["id"]: o for o in led["objectives"]}
    for key, label in (("exit_criteria", "ESTABLISHED if all of"),
                       ("abandon_criteria", "ABANDON if")):
        print(f"\n  {label}:")
        for c in led.get(key, []):
            deps = [by_id[d] for d in c["depends_on"]]
            done = all(d["status"].startswith("closed") for d in deps)
            open_deps = [d["id"] for d in deps if not d["status"].startswith("closed")]
            mark = "x" if done else " "
            print(f"    [{mark}] {c['criterion']}")
            print(f"        threshold: {c.get('threshold','-')}")
            print(f"        blocked on: {', '.join(open_deps) or 'nothing'}"
                  f"   [{c['source']}]")

    openq = [o for o in objs if o["status"] in OPEN_STATUSES]
    ready = [o for o in openq if not o.get("blocked_by")]
    print(f"\n{len(openq)} open objectives; {len(ready)} have nothing blocking them.")
    nxt = [o for o in objs if o["status"] == "queued" and not o.get("blocked_by")]
    if nxt:
        print(f"Next action: {nxt[0]['id']} — {nxt[0]['objective']}")


def main():
    if not LEDGER.exists():
        print(f"{LEDGER} not found (run from the repository root)")
        return 1
    led = json.load(open(LEDGER))
    # check first: a malformed ledger must produce a diagnosis, not a traceback
    # from the renderer. Found by deliberately corrupting a status string.
    errors, warnings = check(led)
    render(led)
    if "--drift" in sys.argv:
        drift_report(led)
    print()
    for w in warnings:
        print(f"  NOTE  {w}")
    for e in errors:
        print(f"  FAIL  {e}")
    print("ledger OK" if not errors else f"{len(errors)} inconsistency(ies)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
