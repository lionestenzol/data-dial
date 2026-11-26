"""Build step 8 - the JSONL log and the daily summary.

One JSON line per message.  The two baselines are charged per path: the
full-sync cost of a file lands on the first message that mentions it, and the
bytes still owed on the original - the deferred bytes - land on the last one.
Summing a column over the log then gives the day's number.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

SPEC_FIELDS = ["ts", "direction", "path", "form", "payload_bytes", "header_bytes",
               "baseline_full_bytes", "deferred_bytes", "checker", "elapsed_ms"]
EXTRA_FIELDS = ["step", "kid", "note", "reason", "at_ms"]


def attribute(records: List[dict], files: Dict[str, object],
              changed: Iterable[str]) -> List[dict]:
    """Charge each path's baselines once, onto its own messages."""
    changed = set(changed)
    first: Dict[str, int] = {}
    last: Dict[str, int] = {}
    paid: Dict[str, int] = {}
    for i, r in enumerate(records):
        p = r.get("path") or ""
        if not p:
            continue
        first.setdefault(p, i)
        last[p] = i
        paid[p] = paid.get(p, 0) + r["payload_bytes"]

    out = []
    for i, r in enumerate(records):
        rec = dict(r)
        p = rec.get("path") or ""
        rec["baseline_full_bytes"] = 0
        rec["deferred_bytes"] = 0
        st = files.get(p)
        if st is not None:
            if first.get(p) == i and p in changed:
                rec["baseline_full_bytes"] = st.full_size
            if last.get(p) == i:
                if getattr(st, "final", "") == "original":
                    rec["deferred_bytes"] = 0          # B holds the original
                else:
                    rec["deferred_bytes"] = max(0, st.full_size - paid.get(p, 0))
        out.append({k: rec.get(k) for k in SPEC_FIELDS + EXTRA_FIELDS})
    return out


def write_jsonl(records: List[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return path


def read_jsonl(path: str | Path) -> List[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def summarise(records: List[dict], result=None,
              real_tool_bytes: Optional[int] = None,
              real_tool_name: str = "rsync") -> dict:
    dial = sum(r["payload_bytes"] + r["header_bytes"] for r in records)
    full = sum(r["baseline_full_bytes"] for r in records)
    deferred = sum(r["deferred_bytes"] for r in records)
    checks = [r["checker"] for r in records if r["checker"]]
    passes = sum(1 for c in checks if c in ("pass", "fallback"))
    by_form: Dict[str, int] = {}
    for r in records:
        by_form[r["form"]] = by_form.get(r["form"], 0) + r["payload_bytes"] + r["header_bytes"]

    s = {
        "messages": len(records),
        "dial_bytes": dial,
        "full_sync_bytes": full,
        "real_tool_bytes": real_tool_bytes,
        "real_tool_name": real_tool_name,
        "deferred_bytes": deferred,
        "dial_plus_deferred_bytes": dial + deferred,
        "saving_vs_full_sync": full - dial,
        "saving_vs_full_sync_pct": (100.0 * (full - dial) / full) if full else 0.0,
        "checker_pass_rate": (100.0 * passes / len(checks)) if checks else 100.0,
        "checker_failures": sum(1 for c in checks if c == "fail"),
        "fallbacks": sum(1 for c in checks if c == "fallback"),
        "bytes_by_form": by_form,
    }
    if real_tool_bytes:
        s["saving_vs_real_tool"] = real_tool_bytes - dial
        s["saving_vs_real_tool_pct"] = 100.0 * (real_tool_bytes - dial) / real_tool_bytes
        s["saving_vs_real_tool_after_deferred"] = real_tool_bytes - (dial + deferred)
    if result is not None:
        s["time_to_visible_ms"] = round(result.time_to_visible_ms, 1)
        s["time_to_open_original_ms"] = round(result.time_to_open_ms, 1)
        s["files"] = len(result.files)
        s["originals_on_b"] = sum(1 for f in result.files.values() if f.final == "original")
        s["previews_on_b"] = sum(1 for f in result.files.values() if f.final == "preview")
        s["missing_on_b"] = sum(1 for f in result.files.values() if f.final == "missing")
        # The liability as it stands now, over the whole library: originals B
        # still has not got.  Not the same as summing the per-day deferred
        # column, which counts a photo again every time it is first seen and
        # does not retract it once the original is finally fetched.
        s["outstanding_deferred_bytes"] = sum(
            f.full_size for f in result.files.values() if f.final != "original")
    return s


def _mb(n) -> str:
    return "-" if n is None else f"{n/1e6:10.3f} MB"


def format_summary(s: dict) -> str:
    L = []
    add = L.append
    add("=" * 62)
    add("DAILY SUMMARY")
    add("=" * 62)
    add(f"  dial bytes              {_mb(s['dial_bytes'])}   ({s['messages']} messages)")
    add(f"  full-sync bytes         {_mb(s['full_sync_bytes'])}")
    add(f"  {s['real_tool_name']+' bytes':<23} {_mb(s.get('real_tool_bytes'))}")
    add(f"  deferred bytes          {_mb(s['deferred_bytes'])}   (originals not opened yet)")
    add(f"  dial + deferred         {_mb(s['dial_plus_deferred_bytes'])}")
    add("-" * 62)
    add(f"  saving vs full sync     {_mb(s['saving_vs_full_sync'])}"
        f"   ({s['saving_vs_full_sync_pct']:.1f}%)")
    if s.get("real_tool_bytes"):
        add(f"  saving vs {s['real_tool_name']:<13} {_mb(s['saving_vs_real_tool'])}"
            f"   ({s['saving_vs_real_tool_pct']:.1f}%)")
        add(f"  ... after deferred      {_mb(s['saving_vs_real_tool_after_deferred'])}")
    add("-" * 62)
    add(f"  checker pass rate       {s['checker_pass_rate']:.1f}%"
        f"   failures {s['checker_failures']}  fallbacks {s['fallbacks']}")
    if "time_to_visible_ms" in s:
        add(f"  time to visible         {s['time_to_visible_ms']:.0f} ms"
            f"   (engine time; no link latency)")
        add(f"  time to open original   {s['time_to_open_original_ms']:.0f} ms avg")
        add(f"  on B: {s['originals_on_b']} originals, {s['previews_on_b']} previews, "
            f"{s['missing_on_b']} missing, of {s['files']} files")
    add("-" * 62)
    add("  dial bytes by form:")
    for form, n in sorted(s["bytes_by_form"].items(), key=lambda kv: -kv[1]):
        add(f"      {form:<14} {_mb(n)}")
    add("=" * 62)
    return "\n".join(L)
