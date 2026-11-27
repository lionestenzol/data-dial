# The village: the motivating application

The north-star use case for this whole project, in the user's framing. It is
**vision, not a built thing** — but it is the scenario that makes the measured
results (009/010) matter, and it sharpens what is worth building next. Read
`THESIS.md` for the mechanism; this is why it is worth having.

## The scenario

A remote village. Its entire access to the outside world is **one thin, slow,
expensive, or fragile connection** — a single satellite link, a weak cell
signal, a line that drops. For the whole community, bandwidth is the scarce
resource. Compute and storage are not: you can put a cheap box with a disk and
a processor in the one building with power, and you can buy a bigger one.

The usual assumption — bandwidth is cheap, conserve compute — is **backwards
here.** So invert it: spend compute freely, make what crosses the wire as close
to nothing as possible.

## Why the village makes the idea *stronger*, not more far-fetched

A village is **shared**, and that is the key. It is not one phone; it is a
community plus a **local hub** (storage + compute) that accumulates a common
store over time: the generators ("ovens"), the files many people have already
pulled, everything the village has already seen.

That shared store is exactly the precondition the recipe trick needs — "the
receiver already has the ingredients." For one phone it is often unmet. For a
village with a growing hub, it is met more and more. So the thin pipe only ever
has to carry what is **genuinely new to the entire village, once.** After that:

| a villager wants… | pipe cost |
|---|---|
| something already pulled by anyone | **zero** — served from the local hub (cache) |
| a new version of something local | a small **diff** |
| something rebuildable from a local generator | a tiny **recipe** |
| something genuinely new and not derivable | **full cost — once**, then it joins the store |

**The compounding property.** The longer the system runs, the larger the local
store grows, so the more becomes derivable locally, so the *less* the pipe has
to carry. A thin connection that effectively widens the longer you use it. That
is the property worth building for.

## How this maps to what was actually measured

This is not hand-waving; the pieces are measured in this repo:

- **The dial works where things are regenerable** (009): on a mixed pile, the
  per-object chooser — cache / diff / regenerate / send — moved ~4x fewer bytes
  than rsync (3.98x against the real rsync binary, exp011), and the margin was
  entirely the *regenerate* regime rsync cannot enter. A photo crossed as a
  60-byte recipe instead of 86 KB.
- **Discovery is nearly free** (010): the hub advertising what it holds and can
  rebuild cost 0.012% of the payload. The thin pipe is not eaten by coordination.
- **The real gate is provenance** (010): the win scales with whether the sender
  (or the hub) has the *recipe* for a thing. That is an architecture discipline
  — keep the generators — not a runtime cost.

## The honest bounds (the same ones, at village scale)

- **Genuinely-new, non-derivable information still crosses the pipe once, at
  full cost.** You cannot pour unlimited *new* knowledge through a straw. The
  pipe's capacity still bounds how much brand-new information the village can
  take in per day. What the system removes is paying twice, re-sending the
  derivable, and one-pull-serves-one instead of one-pull-serves-everyone.
- **The open question is frequency** (`O-provenance-freq`): what fraction of
  what a village actually wants is cacheable, diffable, or regenerable versus
  genuinely novel. If most of it is shared/derivable (software, media, maps,
  educational content, updates), the hub is transformative. If most of what they
  want is unique and non-derivable, it degrades toward "a good cache." Unknown,
  and it is the thing to measure.

## Prior art it is not inventing from scratch

Content-centric / named-data networking and content caches already reach for
"serve it locally, don't re-fetch what's near" (see `research/DR-001.md`,
cards for NDN/NFN and CAS). The twist that is genuinely this project's: **cache
it, diff it, *or regenerate it* — whichever is cheapest — over a shared local
hub.** The regenerate move, and choosing among all of them per object, is the
contribution.

## What building it would actually take

Not a miracle; a build, with the hard parts known and nameable:

1. A **local hub** in the village: storage + modest compute (the shared "B").
2. The **chooser** deciding per request — cache hit? local diff? regenerable
   from a local generator? or genuinely new (pay the pipe)? The rule exists
   (`experiments/exp009_crossover.py:selector`); it needs to become a real
   service, not a measurement script.
3. The **generators** provisioned on the hub — the processes that rebuild
   derivable content locally.
4. The hard part, already named: **getting recipes for incoming content**
   (provenance). Easy for things that arrive *with* their process — software,
   rendered media, structured/derived data. Harder for arbitrary web content,
   where the hub leans more on cache-and-diff than on regenerate.

## Status

Vision and motivation. The mechanism under it is measured (009/010/011); the
village node is not built. This document exists so the north star is written
down and the next session builds toward a real target instead of another file
pile. The one experiment standing between "nice idea" and "worth building for a
village" is `O-provenance-freq` — how much real demand is derivable.
