"""The eight cases from the spec's Tests table.

Test                 Expected
-------------------  --------------------------------------------------
New unique photo     B gets the thumbnail at once; original on open; SHA-256 passes
Duplicate chunk      Only a key or recipe sent; no raw copy
Edited document      Recipe sent; rebuilt file passes SHA-256
Corrupt chunk        Check fails, retry, fall back to raw, logged
Offline mid-send     Resumes without counting bytes twice
Open 5 photos        Exactly 5 originals pulled; thumbnails for the rest
Raw Sync check       Logger's full-sync number equals the real raw bytes
Real-tool run        rsync bytes logged for the same day's changes
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from dial import jlog
from dial.engine import Engine
from dial.rawsync import raw_sync
from dial.wire import Faults, Ledger, LinkDown
from tests.helpers import (devices, document, edit_document, edit_document as edit,
                           forms_for, payload_for, photo, same)

ROOT = Path(__file__).resolve().parent.parent


def run(a, b, ledger=None, faults=None, open_paths=()):
    led = ledger or Ledger()
    res = Engine(a, b, led, faults).sync(open_paths=open_paths)
    return led, res, jlog.attribute(led.records, res.files, res.changed)


# 1 -----------------------------------------------------------------------
def test_new_unique_photo(tmp_path):
    a, b = devices(tmp_path)
    photo(a.root / "IMG_001.jpg", seed=1)

    led, res, recs = run(a, b)
    assert forms_for(recs, "IMG_001.jpg") == ["thumb"]          # thumbnail at once
    assert res.files["IMG_001.jpg"].final == "preview"
    assert b.thumb_path("IMG_001.jpg").exists()
    assert not (b.root / "IMG_001.jpg").exists()                # no original yet
    thumb_bytes = payload_for(recs, "IMG_001.jpg")
    assert thumb_bytes < res.files["IMG_001.jpg"].full_size / 10

    led2, res2, recs2 = run(a, b, open_paths=["IMG_001.jpg"])   # ... then it is opened
    assert res2.files["IMG_001.jpg"].final == "original"
    assert same(a.root / "IMG_001.jpg", b.root / "IMG_001.jpg")  # SHA-256 passes
    assert all(r["checker"] == "pass" for r in recs + recs2)


# 2 -----------------------------------------------------------------------
def test_duplicate_chunk(tmp_path):
    a, b = devices(tmp_path)
    document(a.root / "report.txt", lines=3000, seed=2)
    run(a, b)

    shutil.copy2(a.root / "report.txt", a.root / "report_copy.txt")   # same bytes
    led, res, recs = run(a, b)

    forms = forms_for(recs, "report_copy.txt")
    assert forms and set(forms) <= {"key", "recipe"}       # only a key or a recipe
    assert "raw_chunk" not in forms                        # no raw copy
    assert payload_for(recs, "report_copy.txt") < 1000
    assert same(a.root / "report_copy.txt", b.root / "report_copy.txt")


# 3 -----------------------------------------------------------------------
def test_edited_document(tmp_path):
    a, b = devices(tmp_path)
    doc = document(a.root / "notes.md", lines=6000, seed=3)
    run(a, b)
    full = doc.stat().st_size

    edit_document(doc)
    led, res, recs = run(a, b)

    assert "recipe" in forms_for(recs, "notes.md")          # recipe sent
    assert same(a.root / "notes.md", b.root / "notes.md")   # rebuilt file passes SHA-256
    assert all(r["checker"] == "pass" for r in recs)
    assert payload_for(recs, "notes.md") < full / 4         # and it is much cheaper


# 4 -----------------------------------------------------------------------
@pytest.mark.parametrize("times,expect_fallback", [(1, False), (99, True)])
def test_corrupt_chunk(tmp_path, times, expect_fallback):
    a, b = devices(tmp_path)
    doc = document(a.root / "notes.md", lines=5000, seed=4)
    man = a.scan()
    fk = a.store.get_key(man.entries[0].file_kid)
    victim = fk.child_keys[1].rsplit(":", 1)[1]

    led, res, recs = run(a, b, faults=Faults(corrupt={victim: times}))
    checks = [r["checker"] for r in recs]

    assert "fail" in checks                                  # the check fails
    assert checks.count("fail") >= 1                         # ... and it is retried
    assert same(a.root / "notes.md", b.root / "notes.md")    # the file is still exact
    if expect_fallback:
        assert "fallback" in checks                          # fell back to raw
        assert res.fallbacks == 1
        assert any(r["note"] == "raw fallback" for r in recs)   # logged
    else:
        assert "fallback" not in checks                      # the retry was enough
        assert any(r["note"] == "checker: retry chunk" for r in recs)


# 5 -----------------------------------------------------------------------
def test_offline_mid_send(tmp_path):
    a, b = devices(tmp_path)
    for i in range(4):
        photo(a.root / f"IMG_{i}.jpg", seed=10 + i)
    document(a.root / "notes.md", lines=4000, seed=5)

    led = Ledger()
    with pytest.raises(LinkDown):
        Engine(a, b, led, Faults(drop_after=6)).sync()
    cut = led.dial_bytes
    assert cut > 0

    _, res, recs = run(a, b, ledger=led)                     # resume on the same ledger
    assert all(f.final != "missing" for f in res.files.values())
    assert same(a.root / "notes.md", b.root / "notes.md")

    a2, b2 = devices(tmp_path / "clean")
    for i in range(4):
        shutil.copy2(a.root / f"IMG_{i}.jpg", a2.root / f"IMG_{i}.jpg")
    shutil.copy2(a.root / "notes.md", a2.root / "notes.md")
    led2, _, recs2 = run(a2, b2)

    content = lambda rs: sum(r["payload_bytes"] for r in rs
                             if r["form"] in ("raw_chunk", "thumb"))
    handshake = lambda rs: sum(r["payload_bytes"] + r["header_bytes"] for r in rs
                               if r["form"] in ("manifest", "have",
                                                "have_query", "chunk_query"))
    assert content(recs) == content(recs2)         # no item paid for twice
    # every extra byte the resumed run cost is the second handshake, nothing else
    assert led.dial_bytes - led2.dial_bytes == handshake(recs) - handshake(recs2)
    assert cut < led.dial_bytes


# 6 -----------------------------------------------------------------------
def test_open_5_photos(tmp_path):
    a, b = devices(tmp_path)
    for i in range(12):
        photo(a.root / f"IMG_{i:03d}.jpg", seed=100 + i)
    opened = [f"IMG_{i:03d}.jpg" for i in (1, 3, 5, 7, 9)]

    led, res, recs = run(a, b, open_paths=opened)

    originals = [p for p, f in res.files.items() if f.final == "original"]
    previews = [p for p, f in res.files.items() if f.final == "preview"]
    assert sorted(originals) == sorted(opened)        # exactly 5 originals pulled
    assert len(previews) == 7                         # thumbnails for the rest
    for p in opened:
        assert same(a.root / p, b.root / p)
    for p in previews:
        assert "raw_chunk" not in forms_for(recs, p)
        assert b.thumb_path(p).exists()


# 7 -----------------------------------------------------------------------
def test_raw_sync_check(tmp_path):
    a, b = devices(tmp_path)
    for i in range(5):
        photo(a.root / f"IMG_{i}.jpg", seed=200 + i)
    document(a.root / "doc.txt", lines=2000, seed=7)

    led, res, recs = run(a, b, open_paths=["IMG_0.jpg"])
    logged_full = sum(r["baseline_full_bytes"] for r in recs)

    real = raw_sync(a.root, tmp_path / "raw_mirror")
    assert logged_full == real["bytes"]               # the numbers match
    assert real["files"] == len(res.files)
    s = jlog.summarise(recs, res)
    assert s["full_sync_bytes"] == real["bytes"]


# 8 -----------------------------------------------------------------------
@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_real_tool_run(tmp_path):
    a, b = devices(tmp_path)
    for i in range(6):
        photo(a.root / f"IMG_{i}.jpg", seed=300 + i)
    doc = document(a.root / "doc.txt", lines=4000, seed=8)
    run(a, b)                                          # day 1 for both sides
    mirror = tmp_path / "rsync_mirror"
    subprocess.run([str(ROOT / "rsync_baseline.sh"), str(a.root), str(mirror)],
                   check=True, capture_output=True, text=True)

    edit_document(doc)                                 # the same day's changes
    photo(a.root / "IMG_new.jpg", seed=400)
    led, res, recs = run(a, b, open_paths=["IMG_new.jpg"])

    out = mirror / "rsync_bytes.json"
    subprocess.run([str(ROOT / "rsync_baseline.sh"), str(a.root), str(mirror), str(out)],
                   check=True, capture_output=True, text=True)
    got = json.loads(out.read_text())

    for mode in ("delta", "whole"):
        assert got[mode]["total"] > 0
        assert got[mode]["files"] == 2                 # the edited doc and the new photo
    s = jlog.summarise(recs, res, real_tool_bytes=got[got["baseline"]]["total"])
    assert s["real_tool_bytes"] == got["delta"]["total"]
    assert "saving_vs_real_tool" in s
    assert jlog.format_summary(s).count("rsync") >= 1
