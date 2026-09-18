"""design_ideas_subsystem.py -- Presentation source-selection buttons
(Sources - Center.cuiw's Source_*/_Sync/_NoSync triplets), tested against
a disposable COPY of the real master template file (never the live
DesignIdeasCopy sandbox -- see design_ideas_footer_write_test.py's own
note on why: that project is a real, user-driven workspace, not a safe
"pristine" fixture)."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
from design_ideas_subsystem import (  # noqa: E402
    SOURCE_SYNC_OFFSET_Y, design_ideas_read_sources, design_ideas_source_layout_landscape,
    design_ideas_source_layout_portrait, design_ideas_write_sources,
)
from sdk import read_sdk  # noqa: E402

REAL_REFERENCE = Path(r"C:\Solutions\CrestronDesignIdeas\BasicTemplate_v1_0_2\Sources - Center.cuiw")
TEST_DIR = Path(__file__).resolve().parent / "sources_write_test"
SOURCE = TEST_DIR / "Sources - Center.cuiw"
TEST_DIR.mkdir(exist_ok=True)
shutil.copy(REAL_REFERENCE, SOURCE)
sdk = read_sdk("2.18.0")

REAL_5 = ["1", "2", "3", "4", "5"]

# --- 1. layout math reproduces the real template's own measured positions exactly ---
landscape = {n: x for n, x, y in design_ideas_source_layout_landscape(REAL_5)}
assert landscape == {"1": 15, "2": 223, "3": 431, "4": 639, "5": 847}, landscape
print("design_ideas_source_layout_landscape: reproduces the real 5-source positions exactly: OK")

portrait = {n: (x, y) for n, x, y in design_ideas_source_layout_portrait(REAL_5)}
# y matches exactly; x is within 2px of the real file (real: 126/334/126/334/233 --
# a small, consistent authoring-time rounding this module's own centering formula
# doesn't reproduce bit-for-bit, documented in the module's own comments).
assert [y for _x, y in portrait.values()] == [169, 169, 370, 370, 579], portrait
for name, (x, _y) in portrait.items():
    real_x = {"1": 126, "2": 334, "3": 126, "4": 334, "5": 233}[name]
    assert abs(x - real_x) <= 2, (name, x, real_x)
print("design_ideas_source_layout_portrait: reproduces the real 5-source row/column"
      " rhythm (y exact, x within 2px): OK")

# --- 2. read on the pristine file reproduces the real 5 sources exactly -------------
sources = design_ideas_read_sources(SOURCE)
assert sources == REAL_5, sources
print("design_ideas_read_sources: pristine file reproduces the real 5 sources exactly: OK")

# --- 3. remove a source: all 3 elements gone, remaining sources re-centered --------
work = TEST_DIR / "remove_test.cuiw"
shutil.copy(SOURCE, work)
report = design_ideas_write_sources(work, sdk, ["1", "2", "3", "4"])
print("write (remove) report:", report)
assert report["removed"] == ["5"], report
assert set(report["repositioned"]) == {"1", "2", "3", "4"}, report  # grid re-centers
assert compare.round_trip_check(work)
reread = design_ideas_read_sources(work)
assert reread == ["1", "2", "3", "4"], reread
# all 3 real elements for the removed source are gone
text = work.read_text(encoding="utf-8")
for suffix in ("", "_Sync", "_NoSync"):
    assert f'componentName="Source_5{suffix}"' not in text, suffix
print("design_ideas_write_sources: removing a source deletes all 3 of its elements,"
      " re-centers the rest, round-trips, self-check passes: OK")

# --- 3b. portrait reposition: Sync/NoSync bars get their OWN top (button top + ------
# SOURCE_SYNC_OFFSET_Y), not the button's raw top -- real live bug, 2026-09-18 (user
# screenshot: a source moved to a new portrait ROW, and its sync bar rendered at the
# wrong height). Removing "3" and "4" from the real 5 (-> ["1","2","5"]) moves "5"
# from portrait row2 to row1, a real Y change -- exactly the scenario the earlier
# "remove one source" test above does NOT exercise (removing only "5" leaves "1"-"4"
# in their ALREADY-correct positions, so nothing about their Sync bars ever gets
# rewritten, and this exact bug could hide behind a passing suite).
import re as _re2  # noqa: E402
work1b = TEST_DIR / "portrait_reposition_test.cuiw"
shutil.copy(SOURCE, work1b)
design_ideas_write_sources(work1b, sdk, ["1", "2", "5"])
assert compare.round_trip_check(work1b)
text1b = work1b.read_text(encoding="utf-8")
css1b = text1b.split("{Css}", 1)[-1].split("{PageAttributes}", 1)[0]
portrait1b = css1b[css1b.find("@media (orientation: portrait)"):]
attrs1b = text1b.split("{PageAttributes}", 1)[-1]

def _id_for(component_name: str) -> str:
    m = _re2.search(r'componentName = "' + _re2.escape(component_name) + r'"[\s\S]*?id = "([^"]+)"|'
                     r'id = "([^"]+)"[\s\S]{0,400}?componentName = "' + _re2.escape(component_name) + r'"',
                     attrs1b)
    ids = [g for g in (m.group(1), m.group(2)) if g] if m else []
    assert ids, component_name
    return ids[0]

btn_id = _id_for("Source_5")
sync_id = _id_for("Source_5_Sync")
btn_top = int(_re2.search(r"#" + _re2.escape(btn_id) + r"\s*\{[^}]*top:\s*([0-9]+)px", portrait1b).group(1))
sync_top = int(_re2.search(r"#" + _re2.escape(sync_id) + r"\s*\{[^}]*top:\s*([0-9]+)px", portrait1b).group(1))
assert sync_top == btn_top + SOURCE_SYNC_OFFSET_Y, (sync_top, btn_top)
print("design_ideas_write_sources: portrait reposition gives Sync/NoSync bars their"
      " own top (button top + SOURCE_SYNC_OFFSET_Y), not the button's raw top: OK")

# --- 4. add a source: all 3 elements present, existing sources re-centered ---------
# Start from a 4-source file (real template minus "5") and add "6" back -- 5 total,
# fits one landscape row (the real template's own capacity, already confirmed above).
work2 = TEST_DIR / "add_test.cuiw"
shutil.copy(SOURCE, work2)
design_ideas_write_sources(work2, sdk, ["1", "2", "3", "4"])
report2 = design_ideas_write_sources(
    work2, sdk, ["1", "2", "3", "4", "6"], icon_classes={"6": "fa-solid fa-display"})
print("write (add) report:", report2)
assert report2["added"] == ["6"], report2
assert compare.round_trip_check(work2)
reread2 = design_ideas_read_sources(work2)
assert reread2 == ["1", "2", "3", "4", "6"], reread2
text2 = work2.read_text(encoding="utf-8")
for suffix in ("", "_Sync", "_NoSync"):
    assert f'componentName="Source_6{suffix}"' in text2, suffix
print("design_ideas_write_sources: adding a source builds all 3 of its elements,"
      " round-trips, self-check passes: OK")

# --- 5. adding without an icon_class raises, not silently defaults -----------------
work3 = TEST_DIR / "add_no_icon_test.cuiw"
shutil.copy(SOURCE, work3)
design_ideas_write_sources(work3, sdk, ["1", "2", "3", "4"])
try:
    design_ideas_write_sources(work3, sdk, ["1", "2", "3", "4", "6"])
    raise AssertionError("expected ValueError for a new source with no icon_class")
except ValueError as e:
    assert "icon_class" in str(e), e
print("design_ideas_write_sources: a new source with no icon_class raises: OK")

# --- 6. landscape overflow (too many sources for one row) raises, not silently wraps -
try:
    design_ideas_source_layout_landscape([str(i) for i in range(10)])
    raise AssertionError("expected ValueError for 10 sources not fitting in one landscape row")
except ValueError as e:
    assert "landscape" in str(e), e
print("design_ideas_source_layout_landscape: too many sources for one row raises: OK")

print("Design Ideas Sources: all assertions passed.")
