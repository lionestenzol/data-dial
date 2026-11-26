# Research registry — entry point

Research date: 2026-11-26. Scope: Recursive Information Virtualization prior-art screen.

1. Read RIV_Research_Report.md for findings and recommendation.
2. Read CAPABILITIES.md for authoritative capability mapping and decision classifications.
3. Consult PRIOR_ART.md or RESEARCH_INDEX.json/CSV for 33 discovery cards and primary-source URLs.
4. Check findings/VERIFICATION.md before making any independently-verified claim.
5. Read ARCHITECTURAL_GAPS.md and benchmarks/NEXT_EXPERIMENT.md before implementing anything further.
6. Use TOKEN_BUDGET.md and rejected_mechanisms/DECISIONS.md to avoid repeated research and unsupported claims.

Experiments: create a Python 3.12 virtual environment, install experiments/requirements.lock.txt, run experiments/smoke.py and experiments/stitch_smoke.py. The integration smoke removes its own canonical.db and baseline.db in the experiments folder before creating fresh local experiment databases. No upstream suite or real distributed benchmark is included.

Repository screening was primarily documentation/manifests/examples. No complete repositories or paper copies are bundled. papers/ and repositories/ contain source pointers rather than vendored content. Copying this bundle to Claude gives it a populated research handoff, not a requirement to rebuild the surveyed technologies.
