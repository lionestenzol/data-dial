"""Build step 6 - the router: four steps, 1 MiB packing.

For each item B is missing, in order:

  1. B has the key            -> send the key
  2. B has all the chunks     -> send the recipe
  3. it's a photo preview     -> send thumb-v1
  4. otherwise                -> send the missing raw chunks, 1 MiB per message

Originals use only steps 1, 2 or 4: a thumbnail never stands in for an
original.  Cost order is exact first (a hard rule), then fewest bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Set

from .keys import EXACT, PREVIEW, THUMB, Key
from .store import ChunkStore
from .wire import PACK_LIMIT, Message, compress


@dataclass
class Want:
    """One thing B needs: an original, or a preview of one."""
    path: str
    key: Key
    full_size: int        # the original's size, for the full-sync baseline
    photo: bool

    @property
    def exact(self) -> bool:
        return self.key.exactness == EXACT


def _hash_of(kid: str) -> str:
    return kid.rsplit(":", 1)[1]


def plan_one(want: Want, store: ChunkStore,
             have_keys: Set[str], have_chunks: Set[str]) -> List[Message]:
    key = want.key
    d = "A->B"

    # Step 1 - B has the key already (same bytes under another path, or from
    # an earlier day): just bind the path to it.
    if key.kid in have_keys or (key.points_to == THUMB and key.hash in have_chunks):
        return [Message(d, "key", want.path, 1, body=key.wire(False), kid=key.kid)]

    children = key.child_keys or getattr(store.get_key(key.kid), "child_keys", ())

    # Step 2 - B has every chunk: the recipe is enough.
    if children and all(_hash_of(c) in have_chunks for c in children):
        return [Message(d, "recipe", want.path, 2,
                        body=Key(**{**key.as_dict(False), "child_keys": tuple(children)}
                                 ).wire(True), kid=key.kid)]

    # Step 3 - a photo preview: send thumb-v1.  Never for an exact want.
    if not want.exact:
        blob = store.get_chunk(key.hash)
        return [Message(d, "thumb", want.path, 3, body=key.wire(False),
                        blobs=[(key.hash, blob, "raw")], kid=key.kid)]

    # Step 4 - the missing raw chunks, packed 1 MiB to a message, then the
    # recipe that tells B how to put them back together.
    msgs: List[Message] = []
    batch: List = []
    size = 0
    packed: Set[str] = set()
    for c in children:
        h = _hash_of(c)
        if h in have_chunks or h in packed:
            continue
        packed.add(h)
        data, codec = compress(store.get_chunk(h), photo=want.photo)
        if batch and size + len(data) > PACK_LIMIT:
            msgs.append(Message(d, "raw_chunk", want.path, 4, blobs=batch, kid=key.kid))
            batch, size = [], 0
        batch.append((h, data, codec))
        size += len(data)
    if batch:
        msgs.append(Message(d, "raw_chunk", want.path, 4, blobs=batch, kid=key.kid))
    msgs.append(Message(d, "recipe", want.path, 4,
                        body=Key(**{**key.as_dict(False), "child_keys": tuple(children)}
                                 ).wire(True), kid=key.kid,
                        note="recipe for raw chunks"))
    return msgs


def plan(wants: Iterable[Want], store: ChunkStore,
         have_keys: Set[str], have_chunks: Set[str]) -> List[Message]:
    """Plan the whole run.  A chunk sent for one file is not sent again for
    the next one, and a key sent once is not sent twice."""
    keys, chunks = set(have_keys), set(have_chunks)
    out: List[Message] = []
    for w in wants:
        msgs = plan_one(w, store, keys, chunks)
        out.extend(msgs)
        keys.add(w.key.kid)
        for m in msgs:
            for h, _, _ in m.blobs:
                chunks.add(h)
            if m.step in (2, 4) and m.form == "recipe":
                for c in (store.get_key(w.key.kid).child_keys if store.get_key(w.key.kid) else ()):
                    chunks.add(_hash_of(c))
    return out
