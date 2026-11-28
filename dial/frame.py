"""Rung 1: codec for Message over a byte stream.

`wire.Message` is unchanged; this just encodes/decodes it for a socket.  The
frame is a 4-byte big-endian total-length prefix followed by a canonical-JSON
header and the raw blob bytes concatenated after it:

    [4 bytes: total frame length (not counting these 4 bytes)]
      [4 bytes: JSON header length]
      [header_len bytes: JSON header]
      [blob_0 bytes][blob_1 bytes]...

The ledger still charges `payload_bytes + HEADER_BYTES` per message, exactly
as in the single-process path, so a run over this transport must produce
identical byte totals.  The on-the-wire framing is reported separately by
SocketPeer; it is NOT what `dial_bytes` counts.
"""
from __future__ import annotations

import base64
import json
import socket
import struct
from typing import List, Tuple

from .wire import Message


LEN_PREFIX = struct.Struct(">I")
HEADER_LEN_PREFIX = struct.Struct(">I")


def encode_body(msg: Message) -> bytes:
    """Serialise one Message to the payload bytes (no outer length prefix)."""
    hdr = {
        "direction": msg.direction,
        "form": msg.form,
        "path": msg.path,
        "step": msg.step,
        "kid": msg.kid,
        "note": msg.note,
        "body_b64": base64.b64encode(msg.body).decode("ascii"),
        "blobs": [(h, codec, len(data)) for (h, data, codec) in msg.blobs],
    }
    header_bytes = json.dumps(hdr, separators=(",", ":")).encode("utf-8")
    parts = [HEADER_LEN_PREFIX.pack(len(header_bytes)), header_bytes]
    for (_h, data, _codec) in msg.blobs:
        parts.append(data)
    return b"".join(parts)


def decode_body(body: bytes) -> Message:
    """Inverse of encode_body."""
    (header_len,) = HEADER_LEN_PREFIX.unpack(body[:4])
    header_bytes = body[4:4 + header_len]
    hdr = json.loads(header_bytes.decode("utf-8"))
    offset = 4 + header_len
    blobs: List[Tuple[str, bytes, str]] = []
    for (h, codec, n) in hdr["blobs"]:
        data = body[offset:offset + n]
        offset += n
        blobs.append((h, data, codec))
    return Message(
        direction=hdr["direction"],
        form=hdr["form"],
        path=hdr["path"],
        step=hdr["step"],
        body=base64.b64decode(hdr["body_b64"]),
        blobs=blobs,
        kid=hdr["kid"],
        note=hdr["note"],
    )


def _recvall(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from sock, or raise ConnectionError."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError(f"peer closed after {len(buf)} of {n} bytes")
        buf.extend(chunk)
    return bytes(buf)


def send_message(sock: socket.socket, msg: Message) -> int:
    """Serialise and send one Message.  Returns on-wire bytes
    (length prefix + payload) so callers can tally framing overhead."""
    payload = encode_body(msg)
    sock.sendall(LEN_PREFIX.pack(len(payload)) + payload)
    return 4 + len(payload)


def recv_message(sock: socket.socket) -> Tuple[Message, int]:
    """Read one Message from sock.  Returns (msg, on_wire_bytes)."""
    (length,) = LEN_PREFIX.unpack(_recvall(sock, 4))
    body = _recvall(sock, length)
    return decode_body(body), 4 + length
