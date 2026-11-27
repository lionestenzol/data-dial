#!/usr/bin/env bash
# Rebuild bench/corpus/ exactly as experiment 004 saw it.
# bench/ is gitignored; the corpus is pinned by commit SHA in
# research/benchmarks/CORPUS_MANIFEST.json and verified by SHA256.
set -euo pipefail
FP_SHA=090d81982edc0d2a597f4c15644253d4f266a6ef
HB_SHA=884621aac3aa8a0b8f0801b67330d885ada158b0
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$root/bench/corpus/fpbench" "$root/bench/corpus/herbie"

git clone -q https://github.com/FPBench/FPBench.git "$tmp/fpbench"
git -C "$tmp/fpbench" checkout -q "$FP_SHA"
cp "$tmp"/fpbench/benchmarks/*.fpcore "$root/bench/corpus/fpbench/"
cp "$tmp"/fpbench/LICENSE.txt "$root/bench/corpus/fpbench/"

git clone -q https://github.com/herbie-fp/herbie.git "$tmp/herbie"
git -C "$tmp/herbie" checkout -q "$HB_SHA"
find "$tmp/herbie/bench" -name '*.fpcore' | while read -r f; do
  rel="${f#"$tmp"/herbie/bench/}"
  cp "$f" "$root/bench/corpus/herbie/${rel//\//__}"
done
cp "$tmp"/herbie/LICENSE.md "$root/bench/corpus/herbie/" 2>/dev/null || true
echo "corpus restored under $root/bench/corpus"
echo "verify with: experiments/exp004_verify_corpus.py"
