"""Rung 1: the peer abstraction between Engine (A-side) and the far side.

Today Engine reaches into device B directly in nine places - six via
`self.b.*` and three via `self.rx.*`.  To cross a real socket we route all
nine through a `Peer`.  `LocalPeer` keeps today's single-process path
bit-identical (same `Link`, same `Receiver` on the same `Device`), so every
existing test and demo is a zero-line diff.  `SocketPeer` is the new
transport.

The ledger stays the single authority on bytes.  `payload_bytes +
HEADER_BYTES` is charged per Message, on A's ledger, at exactly the same
points as today.  Control frames (HELLO/VERDICT/STATS/VIEW/BYE) do not
charge the ledger - they are the uncharged B-state reads the Engine already
performs today, just now travelling over a socket.

The actual bytes written on the socket (length prefix + frame-kind byte +
outer control-frame overhead) are reported separately by SocketPeer.wire_bytes
so the true framing cost is visible, without disturbing the comparable
`dial_bytes` figure.
"""
from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from . import frame, view
from .checker import Receiver, Verdict
from .device import Device
from .keys import Key
from .manifest import Manifest
from .wire import Faults, Ledger, Link, Message


# -- frame kinds (control plane over the socket) ---------------------------
KIND_MSG         = 0   # a wire.Message (encode_body)
KIND_VERDICT     = 1   # JSON verdict + optional regen delta
KIND_HELLO_REQ   = 2
KIND_HELLO_REPLY = 3
KIND_VIEW_REQ    = 4
KIND_VIEW_REPLY  = 5
KIND_BYE         = 6

_LEN = struct.Struct(">I")


def _send_frame(sock: socket.socket, kind: int, payload: bytes) -> int:
    hdr = _LEN.pack(1 + len(payload)) + bytes([kind])
    sock.sendall(hdr + payload)
    return len(hdr) + len(payload)


def _recv_frame(sock: socket.socket) -> Tuple[int, bytes, int]:
    prefix = frame._recvall(sock, 4)
    (n,) = _LEN.unpack(prefix)
    body = frame._recvall(sock, n)
    return body[0], body[1:], 4 + n


# -- the interface ---------------------------------------------------------
class Peer:
    """What Engine (A-side) sees of its counterpart."""

    can_generate: Set[str]

    def send_and_check(self, msg: Message) -> Verdict: ...
    def send_only(self, msg: Message) -> dict: ...
    def recv_answer(self, direction: str, form: str) -> bytes:
        """Receive a B->A answer Message (its body); charge it on A's ledger."""
        ...
    def send_raw_fallback(self, msg: Message, path: str, fk: Key) -> Verdict: ...
    def library_rows(self, manifest: Manifest) -> List[view.Row]: ...

    # tallies, pulled at end of run
    @property
    def regen_ms(self) -> float: ...
    @property
    def regen_count(self) -> int: ...

    def close(self) -> None: ...


# -- LocalPeer: today's single-process path, exactly ----------------------
class LocalPeer(Peer):
    """Wraps `Link`+`Receiver` on the same machine.  Byte-for-byte identical
    to the pre-rung-1 Engine; this is the compat path."""

    def __init__(self, dev_b: Device, ledger: Ledger,
                 faults: Optional[Faults] = None):
        self.b = dev_b
        self.link = Link(ledger, faults)
        self.rx = Receiver(dev_b)
        self.can_generate = set(dev_b.can_generate)

    def send_and_check(self, msg: Message) -> Verdict:
        got, rec = self.link.deliver(msg)
        v = self.rx.apply(got)
        rec["checker"] = "pass" if v.ok else "fail"
        rec["reason"] = v.reason
        return v

    def send_only(self, msg: Message) -> dict:
        _, rec = self.link.deliver(msg)
        rec["checker"] = "pass"
        return rec

    def recv_answer(self, direction: str, form: str) -> bytes:
        # Nothing to receive in the local path - Engine builds the answer
        # itself from b's state and charges it directly via send_only().
        # This method is only used by SocketPeer.
        raise NotImplementedError("LocalPeer does not use recv_answer")

    def send_raw_fallback(self, msg: Message, path: str, fk: Key) -> Verdict:
        got, rec = self.link.deliver(msg)
        v = self.rx.accept_raw_file(path, fk, got.blobs[0][1])
        rec["checker"] = "fallback" if v.ok else "fail"
        rec["reason"] = v.reason
        return v

    def library_rows(self, manifest: Manifest) -> List[view.Row]:
        return view.library(self.b, manifest)

    @property
    def regen_ms(self) -> float:
        return self.rx.regen_ms

    @property
    def regen_count(self) -> int:
        return self.rx.regen_count

    def close(self) -> None:
        pass


# -- SocketPeer: the A side of a real socket -------------------------------
class SocketPeer(Peer):
    """A-side peer talking to a B process over a socket.

    Faults (bit-flip / drop-after) are applied on A's side just before the
    bytes hit the socket - same semantics as `Link.deliver` today.
    """

    def __init__(self, sock: socket.socket, ledger: Ledger,
                 faults: Optional[Faults] = None):
        self.sock = sock
        self.ledger = ledger
        self.faults = faults or Faults()
        self.count = 0                 # messages charged
        self.wire_bytes_sent = 0       # true socket I/O (incl. framing)
        self.wire_bytes_recv = 0
        self._regen_ms = 0.0
        self._regen_count = 0
        # Learn B's capabilities at hello (uncharged).
        self.can_generate = self._hello()

    # -- framing helpers (not charged) ------------------------------------
    def _send_control(self, kind: int, obj: dict) -> None:
        payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        self.wire_bytes_sent += _send_frame(self.sock, kind, payload)

    def _recv_control(self, expected_kind: int) -> dict:
        kind, body, wire = _recv_frame(self.sock)
        self.wire_bytes_recv += wire
        if kind != expected_kind:
            raise RuntimeError(f"expected frame kind {expected_kind}, got {kind}")
        return json.loads(body.decode("utf-8")) if body else {}

    def _hello(self) -> Set[str]:
        self._send_control(KIND_HELLO_REQ, {})
        reply = self._recv_control(KIND_HELLO_REPLY)
        return set(reply.get("can_generate", []))

    # -- ledger-charging send of a Message --------------------------------
    def _send_msg_charged(self, msg: Message) -> Tuple[Message, dict]:
        """Charge the Message on A's ledger and ship it over the socket.
        Returns (what was sent, ledger record).  Faults apply to the bytes
        actually written - the same place `Link.deliver` applies them now."""
        import time as _t
        if self.faults.drop_after is not None and self.count >= self.faults.drop_after:
            from .wire import LinkDown
            raise LinkDown(f"link down after {self.count} messages")
        t = _t.perf_counter()
        self.count += 1
        # Apply bit-flip corruption to blob bytes on the way out, matching
        # Link.deliver: the receiver sees the corrupted bytes, A's ledger
        # charges the same count either way.
        blobs = []
        for h, data, codec in msg.blobs:
            if self.faults.hit(h):
                data = (b"\x00" + data[1:]) if data else b"\x00"
            blobs.append((h, data, codec))
        sent_msg = Message(direction=msg.direction, form=msg.form,
                           path=msg.path, step=msg.step, body=msg.body,
                           blobs=blobs, kid=msg.kid, note=msg.note)
        # Charge on A's ledger based on the ORIGINAL msg's payload_bytes -
        # this matches today's Link.deliver behaviour: payload_bytes is
        # computed before the possibly-corrupted bytes are swapped in, and
        # bit-flipping preserves length.
        payload = frame.encode_body(sent_msg)
        self.wire_bytes_sent += _send_frame(self.sock, KIND_MSG, payload)
        rec = self.ledger.charge(msg, (_t.perf_counter() - t) * 1000.0)
        return sent_msg, rec

    def send_and_check(self, msg: Message) -> Verdict:
        _, rec = self._send_msg_charged(msg)
        vd = self._recv_verdict()
        rec["checker"] = "pass" if vd["ok"] else "fail"
        rec["reason"] = vd.get("reason", "")
        return Verdict(vd["ok"], vd.get("reason", ""),
                       bad_hashes=list(vd.get("bad_hashes", ())),
                       missing_hashes=list(vd.get("missing_hashes", ())))

    def send_only(self, msg: Message) -> dict:
        _, rec = self._send_msg_charged(msg)
        rec["checker"] = "pass"
        return rec

    def recv_answer(self, direction: str, form: str) -> bytes:
        """Receive a B->A Message and charge it on A's ledger.  Returns the
        body (the pack_bits bitmap for have/chunk answers)."""
        kind, body, wire = _recv_frame(self.sock)
        self.wire_bytes_recv += wire
        if kind != KIND_MSG:
            raise RuntimeError(f"expected MSG frame, got {kind}")
        incoming = frame.decode_body(body)
        if incoming.direction != direction or incoming.form != form:
            raise RuntimeError(f"expected {direction}/{form}, got "
                               f"{incoming.direction}/{incoming.form}")
        rec = self.ledger.charge(incoming, 0.0)
        rec["checker"] = "pass"
        return incoming.body

    def send_raw_fallback(self, msg: Message, path: str, fk: Key) -> Verdict:
        _, rec = self._send_msg_charged(msg)
        vd = self._recv_verdict()
        rec["checker"] = "fallback" if vd["ok"] else "fail"
        rec["reason"] = vd.get("reason", "")
        return Verdict(vd["ok"], vd.get("reason", ""))

    def _recv_verdict(self) -> dict:
        kind, body, wire = _recv_frame(self.sock)
        self.wire_bytes_recv += wire
        if kind != KIND_VERDICT:
            raise RuntimeError(f"expected VERDICT frame, got {kind}")
        d = json.loads(body.decode("utf-8"))
        self._regen_ms += d.get("regen_ms_delta", 0.0)
        self._regen_count += d.get("regen_count_delta", 0)
        return d

    def library_rows(self, manifest: Manifest) -> List[view.Row]:
        req = {"entries": [e.wire_dict() for e in manifest.entries]}
        self._send_control(KIND_VIEW_REQ, req)
        reply = self._recv_control(KIND_VIEW_REPLY)
        return [view.Row(r["path"], r["shown_as"], int(r["bytes_held"]))
                for r in reply["rows"]]

    @property
    def regen_ms(self) -> float:
        return self._regen_ms

    @property
    def regen_count(self) -> int:
        return self._regen_count

    def close(self) -> None:
        try:
            self._send_control(KIND_BYE, {})
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


# -- extended control-frame kinds (for the uncharged sidecars) ------------
KIND_HAVE_META_REQ   = 7   # [{kid,path,file_kid}, ...]
KIND_HAVE_META_REPLY = 8   # {held: [bool], bound: [bool]}
KIND_CHUNK_META_REQ   = 9  # {hashes: [hex,...]}
KIND_CHUNK_META_REPLY = 10 # {bits: [bool,...]}


# These extend both peers.  LocalPeer resolves everything locally against its
# Device; SocketPeer uses uncharged sidecar frames.
def _localpeer_have_answers(self, wants) -> "Tuple[list, list]":
    held = [self.b.store.has_key(w.key.kid) for w in wants]
    bound = [self.b.settled(w.path, w.key.kid, w.file_key.kid) for w in wants]
    return held, bound


def _localpeer_chunk_answers(self, hashes) -> "list":
    return self.b.have_chunks(list(hashes))


LocalPeer.have_answers = _localpeer_have_answers     # type: ignore[attr-defined]
LocalPeer.chunk_answers = _localpeer_chunk_answers   # type: ignore[attr-defined]


def _socketpeer_have_answers(self, wants):
    req = {"tuples": [{"kid": w.key.kid, "path": w.path,
                       "file_kid": w.file_key.kid} for w in wants]}
    self._send_control(KIND_HAVE_META_REQ, req)
    reply = self._recv_control(KIND_HAVE_META_REPLY)
    return list(reply["held"]), list(reply["bound"])


def _socketpeer_chunk_answers(self, hashes):
    hashes = list(hashes)
    req = {"hashes": hashes}
    self._send_control(KIND_CHUNK_META_REQ, req)
    reply = self._recv_control(KIND_CHUNK_META_REPLY)
    return list(reply["bits"])


SocketPeer.have_answers = _socketpeer_have_answers     # type: ignore[attr-defined]
SocketPeer.chunk_answers = _socketpeer_chunk_answers   # type: ignore[attr-defined]
