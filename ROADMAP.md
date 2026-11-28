# data-dial — rungs

**Not an end date. A ladder.**

The concept is proven. "Done" isn't one far-off finish you can schedule — it's a
series of rungs, each a thing someone could actually use, each a decision you only
make once you've climbed the one below.

---

## Two things, kept separate

| | |
|---|---|
| **North Star** · never "done" | **A thin pipe behaves like a fat one.** People on a bad, slow, or costly connection get the same access as people on a good one. This points the way. You don't ship it or cross it off. |
| **Deliverable** · finishable | **The smallest real thing.** Something a stranger could use, that answers one question. This is what you build, hold, and cross off — one rung at a time. |

---

## The ladder — climb one, learn one thing, then choose the next

### Rung 0 — Prove the concept · **DONE**
- **The thing:** the engine runs on one machine and picks, per file, the cheapest
  honest way across — reuse, diff, or *regenerate* — and verifies every rebuild is
  bit-for-bit identical.
- **Done when:** all four arms run and verify byte-exact. ✓ A 357 KB photo crossed
  as an 84-byte recipe; the demo moved 21× fewer bytes on regenerable data, 0 fallbacks.
- **Answered:** does the concept hold? — **Yes.**

### Rung 1 — Leave the one machine · **YOU ARE HERE**
- **The thing:** `dial sync` between **two real devices over a real network** — your
  laptop and a cheap server or your phone. Move a folder; watch it send almost nothing.
- **Done when:** you sync a folder between two of your own devices over a socket,
  byte-exact, and can show it to another person.
- **Decision gate:** does it survive leaving one machine? If yes → a shared hub is
  worth building.

### Rung 2 — The shared hub · later
- **The thing:** one box, many clients, behind a single thin link. The second person
  to want a thing pays almost nothing — the village primitive.
- **Done when:** two+ clients behind one link; the hub serves repeats from local
  store/recipes and the pipe carries each new thing once.
- **Decision gate:** does the compounding property show up for real — does the pipe
  effectively widen with use?

### Rung 3 — Pick one real domain · later
- **The thing:** aim it at **one** place regenerate pays — app/software delivery, map
  tiles, offline education, or OS/package updates. A real payload, to a real bad pipe.
- **Done when:** a real-world payload reaches a device on a genuinely constrained
  connection and measurably beats shipping the bytes.
- **Decision gate:** research result, or product? This is where you earn the right to
  decide — not before.

### Rung 4 — The big visions · directions
- **The thing:** cloud phone, instant apps, an alternative computer/protocol. These
  aren't separate projects — they're rung 3 at scale. The same engine, pointed at a
  bigger room.
- **Treat as:** a compass heading, not a commitment. You don't owe this decision now.

---

## The one thing that decides niche vs. transformative

How much of what people actually want is rebuildable or already-held, versus genuinely
new? Genuinely-new data still crosses the pipe once, at full size. Measuring that
fraction (`O-provenance-freq`) is the open question riding underneath every rung above.

---

*No calendar — order is real, dates aren't yet. Dates arrive at rung 3, with users.*

*Live version: https://claude.ai/artifact/ECREXthiqq8dEBfk5ExBNQ*
