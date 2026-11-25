"""Synthetic photographs for the test batch.

No camera and no network here, so the batch is made locally.  A real photo is
mostly smooth with a few sharp edges and a layer of sensor grain, and that is
what decides how it compresses - so that is what these are: a smooth colour
field, some blurred subject shapes, a couple of hard edges, and grain, saved
as JPEG at quality 88 like a phone would.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def scene(width: int = 4032, height: int = 3024, seed: int = 0) -> Image.Image:
    rng = np.random.default_rng(seed)

    # a smooth colour field: low-resolution noise, scaled up
    base = rng.random((max(2, height // 64), max(2, width // 64), 3))
    im = Image.fromarray((base * 255).astype(np.uint8)).resize(
        (width, height), Image.BICUBIC).filter(ImageFilter.GaussianBlur(width / 180))

    # subject shapes, soft-edged
    d = ImageDraw.Draw(im)
    for _ in range(rng.integers(3, 7)):
        x, y = rng.integers(0, width), rng.integers(0, height)
        r = int(rng.integers(width // 12, width // 4))
        col = tuple(int(c) for c in rng.integers(0, 255, 3))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    im = im.filter(ImageFilter.GaussianBlur(width / 400))

    # a few hard edges, as a real frame has
    d = ImageDraw.Draw(im)
    for _ in range(rng.integers(2, 5)):
        x0, y0 = rng.integers(0, width), rng.integers(0, height)
        d.rectangle([x0, y0, x0 + int(rng.integers(40, width // 6)),
                     y0 + int(rng.integers(40, height // 6))],
                    outline=tuple(int(c) for c in rng.integers(0, 255, 3)),
                    width=int(rng.integers(3, 12)))

    # sensor grain
    arr = np.asarray(im).astype(np.int16)
    arr += rng.normal(0, 6, arr.shape).astype(np.int16)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def save_photo(path: str | Path, seed: int = 0, size=(4032, 3024),
               quality: int = 88) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene(size[0], size[1], seed).save(path, quality=quality,
                                       subsampling=2, optimize=False)
    return path
