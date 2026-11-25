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
        photos = [p.name for p in sorted(Path(ns.a).rglob("*"))
                  if p.is_file() and ".dial" not in p.parts]
        man = A.scan()
        cands = [e.path for e in man.entries
                 if e.kind == PHOTO and not (B.root / e.path).exists()]
        random.Random(ns.seed).shuffle(cands)
        open_paths += cands[:ns.open]

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

    p = sub.add_parser("report", help="re-print a summary from a log")
    p.add_argument("--log", required=True)
    p.add_argument("--rsync-json")
    p.set_defaults(fn=cmd_report)

    ns = ap.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    raise SystemExit(main())
