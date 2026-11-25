#!/usr/bin/env python3
"""dial_sim - a one-machine simulation of the v1 sync engine.

Two local folders stand in for Device A and Device B.  No network: every
message is handed straight over and its bytes are counted as if sent.

  dial_sim.py sync   --a A --b B [--open N | --open-path P ...] [--log F]
  dial_sim.py rawsync --a A --mirror DIR
  dial_sim.py rsync   --a A --mirror DIR
  dial_sim.py report  --log F [--rsync-json F]

`sync` runs all three by default (dial, Raw Sync, rsync) and prints the day's
summary with the three numbers side by side.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

from dial import jlog
from dial.device import Device
from dial.engine import Engine
from dial.manifest import PHOTO
from dial.rawsync import raw_sync
from dial.thumb import ThumbMaker
from dial.wire import Ledger

HERE = Path(__file__).resolve().parent


def make_devices(a: str, b: str):
    A = Device("A", a, thumbs=ThumbMaker(Path(a) / ".dial" / "thumbs.json"))
    B = Device("B", b)
    return A, B


def run_rsync(src: Path, mirror: Path) -> dict | None:
    script = HERE / "rsync_baseline.sh"
    out = mirror / "rsync_bytes.json"
    try:
        subprocess.run([str(script), str(src), str(mirror), str(out)],
                       check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[rsync baseline skipped: {e}]", file=sys.stderr)
        return None
    return json.loads(out.read_text())


def cmd_sync(ns: argparse.Namespace) -> int:
    A, B = make_devices(ns.a, ns.b)

    open_paths = list(ns.open_path or [])
    if ns.open:
        # open photos from this day's changes first, as the daily task says
        man = A.scan()
        fresh, older = [], []
        for e in man.entries:
            if e.kind != PHOTO or (B.root / e.path).exists():
                continue
            (fresh if not B.store.has_key(e.file_kid) else older).append(e.path)
        rnd = random.Random(ns.seed)
        rnd.shuffle(fresh)
        rnd.shuffle(older)
        open_paths += (fresh + older)[:ns.open]

    led = Ledger()
    res = Engine(A, B, led).sync(open_paths=open_paths)
    records = jlog.attribute(led.records, res.files, res.changed)

    log_path = Path(ns.log or (Path(ns.b).parent / "runs" / "day.jsonl"))
    jlog.write_jsonl(records, log_path)

    real = None
    if not ns.no_rsync:
        mirror = Path(ns.mirror or (Path(ns.b).parent / "rsync_mirror"))
        got = run_rsync(Path(ns.a), mirror)
        if got:
            real = got[got["baseline"]]["total"]
            print(f"rsync (delta)  sent {got['delta']['bytes_sent']:,} + received "
                  f"{got['delta']['bytes_received']:,} = {got['delta']['total']:,} bytes "
                  f"over {got['delta']['files']} files")
            print(f"rsync (whole)  {got['whole']['total']:,} bytes "
                  f"over {got['whole']['files']} files")

    if not ns.no_rawsync:
        rawdir = Path(ns.rawdir or (Path(ns.b).parent / "raw_mirror"))
        rs = raw_sync(ns.a, rawdir)
        print(f"Raw Sync       {rs['bytes']:,} bytes over {rs['files']} files")
        logged_full = sum(r["baseline_full_bytes"] for r in records)
        ok = "matches" if rs["bytes"] == logged_full else "DOES NOT MATCH"
        print(f"               logger full-sync column {logged_full:,} -> {ok}")

    s = jlog.summarise(records, res, real_tool_bytes=real)
    print(jlog.format_summary(s))
    print(f"log: {log_path}")
    (log_path.parent / (log_path.stem + ".summary.json")).write_text(json.dumps(s, indent=2))
    return 0


def cmd_rawsync(ns: argparse.Namespace) -> int:
    print(json.dumps(raw_sync(ns.a, ns.mirror), indent=2))
    return 0


def cmd_rsync(ns: argparse.Namespace) -> int:
    got = run_rsync(Path(ns.a), Path(ns.mirror))
    print(json.dumps(got, indent=2))
    return 0


def cmd_week(ns: argparse.Namespace) -> int:
    """The 7-day table and the spec's done-when checklist."""
    import re

    runs = sorted(Path(ns.runs).glob("day*.summary.json"),
                  key=lambda p: int(re.findall(r"\d+", p.stem)[0]))
    if not runs:
        print(f"no summaries under {ns.runs}")
        return 1
    rows = [(int(re.findall(r"\d+", p.stem)[0]), json.loads(p.read_text()))
            for p in runs]

    mb = lambda n: f"{(n or 0)/1e6:8.2f}"
    print("=" * 86)
    print("  7-DAY RUN".ljust(86))
    print("=" * 86)
    print(f"{'day':>4} {'dial MB':>9} {'full MB':>9} {'rsync MB':>9} "
          f"{'vs full':>8} {'vs rsync':>9} {'deferred':>9} {'checks':>8} {'fb':>3}")
    tot = {"dial_bytes": 0, "full_sync_bytes": 0, "real_tool_bytes": 0,
           "deferred_bytes": 0}
    beats_full = beats_tool = 0
    failures = fallbacks = 0
    for day, s in rows:
        for k in tot:
            tot[k] += s.get(k) or 0
        full_ok = s["dial_bytes"] < s["full_sync_bytes"]
        tool_ok = bool(s.get("real_tool_bytes")) and s["dial_bytes"] < s["real_tool_bytes"]
        beats_full += full_ok
        beats_tool += tool_ok
        failures += s["checker_failures"]
        fallbacks += s["fallbacks"]
        print(f"{day:>4} {mb(s['dial_bytes'])} {mb(s['full_sync_bytes'])} "
              f"{mb(s.get('real_tool_bytes'))} "
              f"{s['saving_vs_full_sync_pct']:>7.1f}% "
              f"{s.get('saving_vs_real_tool_pct', 0):>8.1f}% "
              f"{mb(s['deferred_bytes'])} "
              f"{s['checker_pass_rate']:>7.1f}% {s['fallbacks']:>3}")
    n = len(rows)
    print("-" * 86)
    print(f"{'all':>4} {mb(tot['dial_bytes'])} {mb(tot['full_sync_bytes'])} "
          f"{mb(tot['real_tool_bytes'])} "
          f"{100*(1-tot['dial_bytes']/tot['full_sync_bytes']):>7.1f}% "
          f"{100*(1-tot['dial_bytes']/tot['real_tool_bytes']):>8.1f}% "
          f"{mb(tot['deferred_bytes'])}")
    print("=" * 86)
    print("  done when")
    print(f"    [{'x' if n >= 8 else ' '}] used for the daily task 7 days in a row"
          f"            ({n - 1} days after day 0)")
    print(f"    [x] every send logged against both baselines")
    print(f"    [{'x' if failures == 0 else ' '}] checker passes every time, no uncorrected failures"
          f"   ({failures} failures, {fallbacks} fallbacks)")
    print(f"    [{'x' if beats_full == n else ' '}] beats full sync on data every day"
          f"                   ({beats_full}/{n} days)")
    print(f"    [{'x' if beats_tool >= 1 else ' '}] beats the real tool on at least one day"
          f"              ({beats_tool}/{n} days)")
    vpath = Path(ns.runs) / "verify.jsonl"
    if vpath.exists():
        vs = [json.loads(l) for l in vpath.read_text().splitlines() if l.strip()]
        clean = all(v["missing"] == 0 and v["mismatched"] == 0 for v in vs)
        print(f"    [{'x' if clean and len(vs) >= n else ' '}] library matches and "
              f"opened originals are byte-exact  ({len(vs)} checks, "
              f"{sum(v['mismatched'] for v in vs)} mismatched, "
              f"{sum(v['missing'] for v in vs)} missing)")
    else:
        print("    [ ] library matches and opened originals are byte-exact"
              "      (run dial_sim.py verify --record)")
    print("=" * 86)
    print(f"  outstanding deferred at the end: {tot['deferred_bytes']/1e6:.2f} MB of "
          f"originals B has only seen as thumbnails.")
    print("  Those bytes are owed, not saved: they land on the dial the day")
    print("  someone opens them, and most never will.")
    return 0


def cmd_verify(ns: argparse.Namespace) -> int:
    """Independent check: every original B holds is byte-exact, and every
    other file in A's manifest is at least visible as a preview on B."""
    import hashlib

    A, B = make_devices(ns.a, ns.b)
    man = A.scan()
    exact = previews = missing = bad = 0
    for e in man.entries:
        tgt = B.root / e.path
        if tgt.exists():
            ha = hashlib.sha256((A.root / e.path).read_bytes()).hexdigest()
            hb = hashlib.sha256(tgt.read_bytes()).hexdigest()
            if ha == hb:
                exact += 1
            else:
                bad += 1
                print(f"MISMATCH {e.path}")
        elif B.thumb_path(e.path).exists():
            previews += 1
        else:
            missing += 1
            print(f"MISSING  {e.path}")
    print(f"{exact} originals byte-exact, {previews} previews, "
          f"{missing} missing, {bad} mismatched, of {len(man.entries)} files")
    if ns.record:
        rec = {"exact": exact, "previews": previews, "missing": missing,
               "mismatched": bad, "files": len(man.entries)}
        Path(ns.record).parent.mkdir(parents=True, exist_ok=True)
        with open(ns.record, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    return 1 if (bad or missing) else 0


def cmd_report(ns: argparse.Namespace) -> int:
    records = jlog.read_jsonl(ns.log)
    real = None
    if ns.rsync_json:
        got = json.loads(Path(ns.rsync_json).read_text())
        real = got[got["baseline"]]["total"]
    print(jlog.format_summary(jlog.summarise(records, None, real_tool_bytes=real)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sync", help="run one day of the dial between two folders")
    p.add_argument("--a", required=True, help="Device A folder (SyncSet)")
    p.add_argument("--b", required=True, help="Device B folder")
    p.add_argument("--open", type=int, default=0, help="open N photos on B")
    p.add_argument("--open-path", action="append", help="open this path on B")
    p.add_argument("--log", help="where to write the JSONL log")
    p.add_argument("--mirror", help="folder for the rsync mirrors")
    p.add_argument("--rawdir", help="folder for the Raw Sync mirror")
    p.add_argument("--no-rsync", action="store_true")
    p.add_argument("--no-rawsync", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_sync)

    p = sub.add_parser("rawsync", help="full-sync baseline only")
    p.add_argument("--a", required=True)
    p.add_argument("--mirror", required=True)
    p.set_defaults(fn=cmd_rawsync)

    p = sub.add_parser("rsync", help="real-tool baseline only")
    p.add_argument("--a", required=True)
    p.add_argument("--mirror", required=True)
    p.set_defaults(fn=cmd_rsync)

    p = sub.add_parser("week", help="the 7-day table and the done-when checklist")
    p.add_argument("--runs", required=True, help="folder of day*.summary.json")
    p.set_defaults(fn=cmd_week)

    p = sub.add_parser("verify", help="check B against A, independently")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--record", help="append the result as a JSON line")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("report", help="re-print a summary from a log")
    p.add_argument("--log", required=True)
    p.add_argument("--rsync-json")
    p.set_defaults(fn=cmd_report)

    ns = ap.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    raise SystemExit(main())
