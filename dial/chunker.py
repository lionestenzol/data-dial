"""Build step 3a - FastCDC content-defined chunking.

Normalised chunking (level 2) with a gear hash, as in the FastCDC paper: a
strict mask before the average point, a lax mask after it, so chunk sizes
cluster near the average and a byte inserted in the middle of a file only
disturbs the chunk it lands in.
"""
from __future__ import annotations

import random
from typing import Iterator, List, Tuple

MIN_SIZE = 2 * 1024
AVG_SIZE = 8 * 1024
MAX_SIZE = 64 * 1024

# Masks from the FastCDC paper for an 8 KiB average.
MASK_S = 0x0003590703530000   # strict, used before the average point
MASK_L = 0x0000D90003530000   # lax, used after it
_M64 = (1 << 64) - 1


def _gear_table() -> List[int]:
    rnd = random.Random(0x1F2E3D4C)
    return [rnd.getrandbits(64) for _ in range(256)]


GEAR = _gear_table()


def cut_points(buf: memoryview | bytes,
               min_size: int = MIN_SIZE,
               avg_size: int = AVG_SIZE,
               max_size: int = MAX_SIZE) -> Iterator[Tuple[int, int]]:
    """Yield (offset, length) for every chunk in buf."""
    gear = GEAR
    n = len(buf)
    i = 0
    while i < n:
        left = n - i
        if left <= min_size:
            yield (i, left)
            return
        end = i + max_size if left > max_size else n
        normal = i + avg_size
        if normal > end:
            normal = end
        fp = 0
        j = i + min_size
        cut = 0
        while j < normal:
            fp = ((fp << 1) + gear[buf[j]]) & _M64
            if not (fp & MASK_S):
                cut = j + 1
                break
            j += 1
        if not cut:
            while j < end:
                fp = ((fp << 1) + gear[buf[j]]) & _M64
                if not (fp & MASK_L):
                    cut = j + 1
                    break
                j += 1
        if not cut:
            cut = end
        yield (i, cut - i)
        i = cut


def chunks(data: bytes, **kw) -> Iterator[bytes]:
    mv = memoryview(data)
    for off, ln in cut_points(mv, **kw):
        yield bytes(mv[off:off + ln])
