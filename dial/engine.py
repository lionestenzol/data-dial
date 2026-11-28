"""The session: manifest, have-check, router, checker, ledger.

One sync run is two phases.  The library phase gets every new or changed item
onto B - previews for photos, originals for documents.  The open phase pulls
the originals of the photos B actually opens.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from . import router, view
from .checker import Receiver, Verdict
from .device import Device, pack_bits
from .peer import LocalPeer, Peer
from .keys import EXACT, Key
from .manifest import Manifest, PHOTO
from .wire import HEADER_BYTES, Faults, Ledger, Link, LinkDown, Message

HASH_BYTES = 32          # a chunk question is a binary digest on the wire


@dataclass
class FileState:
    full_size: int
    kind: str
    final: str = "missing"      # original | preview | missing


@dataclass
class RunResult:
    manifest: Manifest
    files: Dict[str, FileState]
    rows: list
    opened: List[str]
    changed: Set[str] = field(default_factory=set)
    time_to_visible_ms: float = 0.0
    time_to_open_ms: float = 0.0
    fallbacks: int = 0
    regen_ms: float = 0.0        # CPU B spent regenerating (the arm's trade)
    regen_count: int = 0         # how many artifacts arrived as recipes


class Engine:
    def __init__(self, a: Device, b, ledger: Ledger,
                 faults: Optional[Faults] = None):
        """`b` may be a Device (compat: auto-wrapped in LocalPeer) or a Peer
        instance (SocketPeer for the socket transport)."""
        self.a = a
        self.ledger = ledger
        if isinstance(b, Peer):
            self.peer: Peer = b
        else:
            self.peer = LocalPeer(b, ledger, faults)
        self.raw_done: Set[str] = set()

    # -- protocol bookkeeping --------------------------------------------
    def _send(self, msg: Message) -> Verdict:
        return self.peer.send_and_check(msg)

    def _charge_only(self, msg: Message) -> dict:
        """A message whose content needs no check (have-answers, queries)."""
        return self.peer.send_only(msg)

    # -- phase 0: manifest and have-check ---------------------------------
    def exchange_manifest(self, man: Manifest) -> None:
        body = man.key  # the key carries the canonical body's hash and size
        msg = Message("A->B", "manifest", "", None,
                      body=json.dumps([e.wire_dict() for e in man.entries],
                                      sort_keys=True, separators=(",", ":")).encode(),
                      kid=body.kid)
        v = self._send(msg)
        if not v.ok:                      # ask for it again
            v = self._send(msg)
            if not v.ok:
                raise RuntimeError("manifest failed twice")

    def have_check(self, wants: Sequence["router.Want"]):
        """Step 4 of the build order: B reports what it has.

        Two bits per item: whether it holds the key at all, and whether that
        path already shows it.  An item it already shows costs nothing more.
        """
        if not wants:
            return set(), set()
        q = Message("A->B", "have_query", "", None,
                    body=b"".join(bytes.fromhex(w.key.hash) for w in wants))
        self._charge_only(q)
        held, bound = self.peer.have_answers(wants)
        self._charge_only(Message("B->A", "have", "", None,
                                  body=pack_bits(held + bound)))
        return ({w.path for w, ok in zip(wants, bound) if ok},
                {w.key.kid for w, ok in zip(wants, held) if ok})

    def chunk_check(self, hashes: Sequence[str]) -> Set[str]:
        if not hashes:
            return set()
        q = Message("A->B", "chunk_query", "", None,
                    body=b"".join(bytes.fromhex(h) for h in hashes))
        self._charge_only(q)
        bits = self.peer.chunk_answers(hashes)
        self._charge_only(Message("B->A", "have", "", None, body=pack_bits(bits)))
        return {h for h, ok in zip(hashes, bits) if ok}

    # -- the send loop, with retry and raw fallback -----------------------
    def run_plan(self, wants: Sequence[router.Want]) -> int:
        settled, have_keys = self.have_check(wants)
        wants = [w for w in wants if w.path not in settled]
        if not wants:
            return 0
        ask: List[str] = []
        seen: Set[str] = set()
        for w in wants:
            if w.key.kid in have_keys:
                continue
            for c in w.key.child_keys:
                h = c.rsplit(":", 1)[1]
                if h not in seen:
                    seen.add(h)
                    ask.append(h)
        have_chunks = self.chunk_check(ask)

        by_kid = {w.key.kid: w for w in wants}
        fallbacks = 0
        for msg in router.plan(wants, self.a.store, have_keys, have_chunks):
            if msg.kid in self.raw_done:      # already sent whole; skip the rest
                continue
            fallbacks += self._deliver(msg, by_kid.get(msg.kid))
        return fallbacks

    def _deliver(self, msg: Message, want: Optional[router.Want]) -> int:
        """One retry, in the shape the checker table asks for, then raw."""
        v = self._send(msg)
        if v.ok:
            return 0
        if msg.form == "generate" and want is not None:
            # A regenerate that did not reproduce the bytes (absent generator,
            # version skew, nondeterminism) is not worth retrying: go to raw.
            self._raw_fallback(want)
            self.raw_done.add(want.key.kid)
            return 1
        if want is not None and v.missing_hashes:
            # rebuilt file short of chunks: ask for them, then try again
            self._send(self._chunk_msg(want, v.missing_hashes,
                                       "checker: missing chunks"))
            v = self._send(msg)
        elif want is not None and v.bad_hashes and msg.form == "raw_chunk":
            v = self._send(self._chunk_msg(want, v.bad_hashes,
                                           "checker: retry chunk"))
        else:
            v = self._send(msg)
        if v.ok:
            return 0
        if want is None:
            return 0
        self._raw_fallback(want)
        self.raw_done.add(want.key.kid)
        return 1

    def _chunk_msg(self, want: router.Want, hashes: Iterable[str], note: str) -> Message:
        from .wire import compress
        blobs = []
        for h in hashes:
            data, codec = compress(self.a.store.get_chunk(h), photo=want.photo)
            blobs.append((h, data, codec))
        return Message("A->B", "raw_chunk", want.path, 4, blobs=blobs,
                       kid=want.key.kid, note=note)

    def _raw_fallback(self, want: router.Want) -> None:
        """Rule: one retry, then raw.  Every fallback is logged."""
        data = (self.a.root / want.path).read_bytes()
        fk = want.file_key
        msg = Message("A->B", "raw_chunk", want.path, 4,
                      blobs=[(fk.hash, data, "raw")], kid=fk.kid,
                      note="raw fallback")
        self.peer.send_raw_fallback(msg, want.path, fk)

    def _attach_gen(self, want: router.Want) -> router.Want:
        """If A kept a recipe for this exact original and B can run it, mark the
        want so the router ships the recipe instead of the bytes.  Only for the
        original itself (not a thumbnail stand-in)."""
        rec = self.a.provenance.get(want.path)
        if (rec is not None
                and want.key.kid == want.file_key.kid
                and rec.generator in self.peer.can_generate):
            want.gen = rec
        return want

    # -- the day's change set --------------------------------------------
    def _snapshot_path(self) -> Path:
        return self.a.state / "sent_manifest.json"

    def _change_set(self, man: Manifest) -> Set[str]:
        p = self._snapshot_path()
        before = json.loads(p.read_text()) if p.exists() else {}
        return {e.path for e in man.entries if before.get(e.path) != e.file_kid}

    def _remember(self, man: Manifest) -> None:
        p = self._snapshot_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({e.path: e.file_kid for e in man.entries}))

    # -- a whole day ------------------------------------------------------
    def sync(self, open_paths: Sequence[str] = ()) -> RunResult:
        man = self.a.scan()
        self.exchange_manifest(man)
        entries = man.by_path()
        files = {e.path: FileState(e.size, e.kind) for e in man.entries}
        # Measurement, not protocol: what a full sync would send whole today.
        # That is "new or changed since the last run", kept on A's own side -
        # a full-sync tool holds every original, so a photo B chose to defer
        # is not something it would send again tomorrow.
        changed = self._change_set(man)

        library: List[router.Want] = []
        for e in man.entries:
            fk = self.a.store.get_key(e.file_kid)
            if e.kind == PHOTO and e.thumb_kid:
                tk = self.a.store.get_key(e.thumb_kid)
                library.append(router.Want(e.path, tk, e.size, True, fk))
            else:
                library.append(self._attach_gen(
                    router.Want(e.path, fk, e.size, e.kind == PHOTO, fk)))
        t0 = time.perf_counter()
        falls = self.run_plan(library)
        t_visible = (time.perf_counter() - t0) * 1000.0

        opened = [p for p in open_paths if p in entries]
        t_open = 0.0
        if opened:
            wants = []
            for p in opened:
                e = entries[p]
                fk = self.a.store.get_key(e.file_kid)
                wants.append(self._attach_gen(
                    router.Want(p, fk, e.size, e.kind == PHOTO, fk)))
            t1 = time.perf_counter()
            falls += self.run_plan(wants)
            t_open = (time.perf_counter() - t1) * 1000.0 / len(opened)

        self._remember(man)
        rows = self.peer.library_rows(man)
        for r in rows:
            if r.path in files:
                files[r.path].final = r.shown_as
        return RunResult(man, files, rows, opened, changed,
                         t_visible, t_open, falls,
                         self.peer.regen_ms, self.peer.regen_count)
