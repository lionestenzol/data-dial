#!/usr/bin/env python
"""Verify bench/corpus/ matches the manifest exp004 was run against."""
import hashlib, json, pathlib, sys

man = json.load(open("research/benchmarks/CORPUS_MANIFEST.json"))
bad = []
for path, rec in man["files"].items():
    p = pathlib.Path(path)
    if not p.exists():
        bad.append((path, "MISSING")); continue
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != rec["sha256"]:
        bad.append((path, f"sha mismatch {got[:12]} != {rec['sha256'][:12]}"))
print(f"{len(man['files'])} files, {man['total_fpcores']} FPCores expected")
for path, why in bad:
    print(f"  FAIL {path}: {why}")
print("corpus OK" if not bad else f"{len(bad)} file(s) differ")
sys.exit(1 if bad else 0)
