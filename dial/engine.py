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


class Engine:
    def __init__(self, a: Device, b: Device, ledger: Ledger,
                 faults: Optional[Faults] = None):
        self.a, self.b = a, b
        self.ledger = ledger
        self.link = Link(ledger, faults)
        self.rx = Receiver(b)
        self.raw_done: Set[str] = set()

    # -- protocol bookkeeping --------------------------------------------
    def _send(self, msg: Message) -> Verdict:
        got, rec = self.link.deliver(msg)
        v = self.rx.apply(got)
        rec["checker"] = "pass" if v.ok else "fail"
        rec["reason"] = v.reason
        return v

    def _charge_only(self, msg: Message) -> dict:
        """A message whose content needs no check (have-answers, queries)."""
        _, rec = self.link.deliver(msg)
        rec["checker"] = "pass"
        return rec

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

    def have_check(self, kids: Sequence[str]) -> Set[str]:
        """Step 4 of the build order: B reports the keys it has."""
        if not kids:
            return set()
        q = Message("A->B", "have_query", "", None,
                    body=b"".join(bytes.fromhex(k.rsplit(":", 1)[1]) for k in kids))
        self._charge_only(q)
        bits = self.b.have_keys(kids)
        self._charge_only(Message("B->A", "have", "", None, body=pack_bits(bits)))
        return {k for k, ok in zip(kids, bits) if ok}

    def chunk_check(self, hashes: Sequence[str]) -> Set[str]:
        if not hashes:
            return set()
        q = Message("A->B", "chunk_query", "", None,
                    body=b"".join(bytes.fromhex(h) for h in hashes))
        self._charge_only(q)
        bits = self.b.have_chunks(hashes)
        self._charge_only(Message("B->A", "have", "", None, body=pack_bits(bits)))
        return {h for h, ok in zip(hashes, bits) if ok}

    # -- the send loop, with retry and raw fallback -----------------------
    def run_plan(self, wants: Sequence[router.Want]) -> int:
        have_keys = self.have_check([w.key.kid for w in wants])
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
        got, rec = self.link.deliver(msg)
        v = self.rx.accept_raw_file(want.path, fk, got.blobs[0][1])
        rec["checker"] = "fallback" if v.ok else "fail"
        rec["reason"] = v.reason

    # -- a whole day ------------------------------------------------------
    def sync(self, open_paths: Sequence[str] = ()) -> RunResult:
        man = self.a.scan()
        self.exchange_manifest(man)
        entries = man.by_path()
        files = {e.path: FileState(e.size, e.kind) for e in man.entries}
        # measurement, not protocol: which files a full sync would send whole
        changed = {e.path for e in man.entries if not self.b.store.has_key(e.file_kid)}

        library: List[router.Want] = []
        for e in man.entries:
            fk = self.a.store.get_key(e.file_kid)
            if e.kind == PHOTO and e.thumb_kid:
                tk = self.a.store.get_key(e.thumb_kid)
                library.append(router.Want(e.path, tk, e.size, True, fk))
            else:
                library.append(router.Want(e.path, fk, e.size,
                                           e.kind == PHOTO, fk))
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
                wants.append(router.Want(p, fk, e.size, e.kind == PHOTO, fk))
            t1 = time.perf_counter()
            falls += self.run_plan(wants)
            t_open = (time.perf_counter() - t1) * 1000.0 / len(opened)

        rows = view.library(self.b, man)
        for r in rows:
            if r.path in files:
                files[r.path].final = r.shown_as
        return RunResult(man, files, rows, opened, changed,
                         t_visible, t_open, falls)
