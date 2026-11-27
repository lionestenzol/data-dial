# Tool mechanics: rsync and egg, read from source

Prompted by a fair criticism: across this project I used rsync (reimplemented)
and egg/egglog (black box) by reasoning from their interfaces, not from how they
are built — and it cost me (crashes I should have predicted, a reimplementation
I mischaracterised). This is the correction: both read at source, mechanics
documented, compared to what we built.

Sources read: **rsync @`df0bb4e`** (RsyncProject/rsync) — `checksum.c`,
`match.c`, `generator.c`, `sender.c`. **egg @`73975c9`** (egraphs-good/egg) —
`egraph.rs`, `run.rs`, `extract.rs`, `unionfind.rs`.

---

## 1. rsync — how it actually works

**Two-level checksum.** Every basis block gets a *weak* rolling checksum and a
*strong* hash. The weak one is cheap and rollable; the strong one (MD5-family)
is computed only when the weak one hits.

- Weak checksum (`checksum.c get_checksum1`): an Adler-32-style pair —
  `s1 = Σ bytes`, `s2 = Σ weighted bytes`, packed as `(s1 & 0xffff) + (s2 << 16)`.
- **It rolls** (`match.c:392-398`): sliding the window one byte right updates the
  checksum in O(1) — `s1 -= out; s1 += in; s2 -= k*out; s2 += s1` — instead of
  recomputing over the whole block. This is the core trick: the sender slides
  byte-by-byte across the new file at *every offset*, cheaply, and only does real
  work on a weak hit.

**Match search** (`match.c hash_search`, `build_hash_table`):
- Basis block signatures go in a hash table keyed on the weak checksum
  (`SUM2HASH`), with chaining for collisions, sized for ~80% load.
- On a weak hit, confirm with the strong hash. On a full match, emit a copy
  reference and jump forward a whole block; else emit one literal byte and roll
  on.
- **`MAX_CHAIN_LEN` = 1024** (`match.c`): a cap added after issue #217, where a
  basis whose blocks all share one weak checksum turned the inner loop into
  O(file²) and hung for hours on multi-GB files. Over the cap, blocks are sent
  as literals — always correct, only slightly larger. A real-world safety valve.
- **`want_i`** biases toward *adjacent* matches so the output run-length-encodes
  better — consecutive copies/literals compress in the token stream.

**Delta stream**: literal runs (length-prefixed) and copy tokens (block
references), not per-byte. The receiver (`receiver.c`) reconstructs by copying
referenced basis blocks and splicing literals, then verifies a whole-file strong
checksum.

### What exp009's reimplementation got right and wrong
- **Right:** two-level weak+strong, hash-by-weak-checksum, check every offset
  (advance by 1 on a miss), copy-on-full-match. The delta *size* it computes is a
  reasonable approximation.
- **Wrong / omitted, precisely:**
  1. **No rolling.** It recomputes the full weak checksum at each offset
     (`_weak(blk)` over the whole block) — O(block) per offset where rsync is
     O(1). Same matches found, so **delta size is ~correct; it is just slow**.
     (Last turn I called this a "block-aligned bug" — that was wrong; it does
     check every offset. The real gap is performance, not correctness.)
  2. **No `MAX_CHAIN_LEN` cap** — would hang on adversarial inputs rsync handles.
  3. **No adjacent-match / run-length encoding of the token stream.** Real rsync
     RLE-compresses literal and copy runs, so its wire delta is **slightly
     smaller** than exp009's `literals + copies·8`. Net: exp009 was mildly
     *unfair to rsync* — real rsync would do a bit better in the delta regime.
     This does **not** touch the 009 headline, which came from the *recompute*
     regime rsync cannot enter at all; but it means "4x over rsync" is very
     slightly generous where rsync actually competes.

---

## 2. egg — how it actually works

**An e-graph is three things** (`egraph.rs`): a set of **e-classes** (each an
equivalence class of **e-nodes**), a **union-find** over e-class ids
(`unionfind.rs`), and a **hashcons** (`memo`) mapping canonical e-nodes to their
e-class. `add` hashconses an e-node and returns its e-class id; `union` merges
two e-classes.

**The congruence invariant and deferred `rebuild`** (`egraph.rs rebuild`,
`process_unions`): the efficiency idea that made egg (POPL 2021). Maintaining
"if two nodes have equal children they are in the same class" after *every* union
is expensive. egg **defers** it: do a batch of unions, then call `rebuild()`
once to restore congruence in bulk (`process_unions`). This is why egg is fast
and why saturation proceeds in iterations.

**Equality saturation** (`run.rs Runner`): repeatedly match rewrite rules and
apply unions, rebuilding each iteration, **until a fixpoint or a declared
limit**. The limits are first-class and defaulted:
- `iter_limit` (default **30**), `node_limit` (example **10_000**),
  `time_limit` — `run.rs:162-186`. It stops with `StopReason::Saturated`,
  `IterationLimit`, `NodeLimit`, or `TimeLimit`.
- **This is the whole answer to exp008's OOM.** egg is *designed* to stop before
  the e-graph explodes; the node limit exists precisely because distributivity-
  like rules grow it combinatorially.

**Extraction** (`extract.rs find_best`): for a given e-class, take its canonical
id (`egraph.find`), look up the precomputed minimum-cost node for that class
(`self.costs[&canonical]`), and build the expression bottom-up, recursively
picking the min-cost node per child (`build_recexpr` / `find_best_node`). So
**extraction is deterministic within one e-graph given a cost function** — it is
the per-e-class argmin over a `CostFunction` (ships `AstSize`, `AstDepth`).

### What exp008 got wrong vs real egg
1. **The OOM was me using the tool without its built-in safety.** egg's `Runner`
   caps nodes/iters/time by default; my egglog usage ran saturation controlled
   only by a hand-set iteration count (2 survived, 4 exhausted memory). The
   explosion wasn't a surprise property — it is the exact thing `node_limit`
   exists to stop, and I didn't set one. Reading `run.rs` first would have
   predicted it.
2. **"Extracts differently from two separate e-graphs" is correct usage of a
   wrong setup.** `find_best` returns the min-cost node *within one e-graph's*
   e-class structure. Two expressions saturated in **separate** e-graphs are in
   separate structures, so they can extract to different representatives — there
   is no canonical form *across* e-graphs. The right usage (which exp008's
   persistent-e-graph arm was groping toward) is to add *both* expressions to the
   **same** e-graph, saturate, and ask whether they landed in one e-class — then
   extraction gives them the same canonical node. The persistent arm was right in
   principle and only failed for reason (1): no node limit.

---

## 3. Comparison to what we have, and what to reuse

Both tools are not just baselines — each is a **working embodiment of a piece of
the thesis**, which DR-001's policy (ACQUISITION > REINVENTION) said to study
before building:

- **rsync = the "exploit what B already has" engine**, exactly `delta` /
  GIR NODE_06. We reimplemented a size-faithful but slow, safety-free version.
  **Next session: use the real `librsync`/`rdiff` (or port the rolling checksum
  + chain cap) rather than the exp009 stand-in**, so the delta arm is both fast
  and fair to rsync. The rolling checksum (`get_checksum1`) and `MAX_CHAIN_LEN`
  are the two pieces to copy.
- **egg = the "store many equivalent forms, extract the cheapest" engine**,
  exactly the recipe-selection problem (002–008). It is a *better-built* version
  of what exp003–006 hand-rolled. If that line is ever revisited, **use egg's
  `Runner` with explicit `node_limit`/`iter_limit` and one shared e-graph**, not
  per-request egglog saturation. The exp008 crashes were self-inflicted by
  skipping the engine's own guardrails.

### The meta-lesson, recorded so the next session inherits it
Understand the machine before benchmarking it. Three of this project's "findings"
(the egglog OOM, the cross-e-graph non-canonicity, the mischaracterised rsync
reimplementation) were me discovering, by crashing or by error, properties that
are plainly visible in ~200 lines of the tools' own source. Reading first would
have been faster than racing.
