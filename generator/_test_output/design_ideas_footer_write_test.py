"""design_ideas_subsystem.py::design_ideas_read_footer_groups /
design_ideas_write_footer_groups -- tested against a disposable COPY of the real
Footer - Main.cuiw (never the live template or AraTestProject)."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
from design_ideas_subsystem import (  # noqa: E402
    FOOTER_DEFAULT_GROUPS, design_ideas_read_footer_groups, design_ideas_remove_subsystem_page,
    design_ideas_write_footer_groups,
)
from sdk import read_sdk  # noqa: E402

# The master template's OWN file, never the live DesignIdeasCopy sandbox --
# that project is a real, user-driven workspace whose footer can and does
# change (confirmed live, 2026-09-18: a real subsystem removal/addition
# during a live test left it permanently different from FOOTER_DEFAULT_
# GROUPS), so it is not a safe "pristine" fixture source.
REAL_REFERENCE = Path(r"C:\Solutions\CrestronDesignIdeas\BasicTemplate_v1_0_2\Footer - Main.cuiw")
TEST_DIR = Path(__file__).resolve().parent / "footer_write_test"
SOURCE = TEST_DIR / "Footer - Main.cuiw"
TEST_DIR.mkdir(exist_ok=True)
shutil.copy(REAL_REFERENCE, SOURCE)
sdk = read_sdk("2.18.0")

# --- 1. read on the pristine file reproduces the real default groups exactly --------
groups = design_ideas_read_footer_groups(SOURCE)
assert groups == FOOTER_DEFAULT_GROUPS, (groups, FOOTER_DEFAULT_GROUPS)
print("design_ideas_read_footer_groups: pristine file reproduces FOOTER_DEFAULT_GROUPS exactly: OK")

# --- 2. remove Shades/Phone/VideoCall (the user's real AraTestProject request) ------
work = TEST_DIR / "remove_test.cuiw"
shutil.copy(SOURCE, work)
new_groups = [["Power"], ["Lights"], ["Camera"], ["Audio"]]
report = design_ideas_write_footer_groups(work, sdk, new_groups)
print("write (remove) report:", report)
assert set(report["removed"]) == {"Shades", "Phone", "VideoCall"}, report
assert report["added"] == [], report
assert compare.round_trip_check(work)
print("design_ideas_write_footer_groups (remove): round-trip OK, correct removed set")

# re-reading the edited file should now report the NEW groups
reread = design_ideas_read_footer_groups(work)
assert reread == new_groups, (reread, new_groups)
print("design_ideas_write_footer_groups (remove): re-read confirms new groups, self-check passes")

# --- 3. add a brand-new subsystem button to a group ---------------------------------
work2 = TEST_DIR / "add_test.cuiw"
shutil.copy(SOURCE, work2)
new_groups2 = [["Power"], ["Lights", "Shades", "Fan"], ["Camera", "Phone", "VideoCall"], ["Audio"]]
report2 = design_ideas_write_footer_groups(
    work2, sdk, new_groups2, icon_classes={"Fan": "fa-solid fa-fan"})
print("write (add) report:", report2)
assert report2["added"] == ["Fan"], report2
assert report2["removed"] == [], report2
assert compare.round_trip_check(work2)
print("design_ideas_write_footer_groups (add): round-trip OK, Fan added")

reread2 = design_ideas_read_footer_groups(work2)
assert reread2 == new_groups2, (reread2, new_groups2)
print("design_ideas_write_footer_groups (add): re-read confirms new groups, self-check passes")

# --- 4. combined add + remove + reposition in one call (still <=4 groups -- see the ---
# DividerGroup4/Privacy_Mute collision guard tested in step 4b) ----------------------
work3 = TEST_DIR / "combined_test.cuiw"
shutil.copy(SOURCE, work3)
new_groups3 = [["Power"], ["Lights"], ["Camera", "VideoCall"], ["Audio", "RoomVolume"]]
report3 = design_ideas_write_footer_groups(
    work3, sdk, new_groups3, icon_classes={"RoomVolume": "fa-solid fa-volume-high"})
print("write (combined) report:", report3)
assert set(report3["removed"]) == {"Shades", "Phone"}, report3
assert report3["added"] == ["RoomVolume"], report3
assert compare.round_trip_check(work3)
reread3 = design_ideas_read_footer_groups(work3)
assert reread3 == new_groups3, (reread3, new_groups3)
print("design_ideas_write_footer_groups (combined): round-trip + self-check OK")

# --- 4b. a 5th group's own internal divider must NOT collide with "DividerGroup4" ---
# -- the real, already-taken name of Privacy_Mute's own fixed divider. Removing 2
# subsystems first (Shades, Phone) frees enough real footer width for a 5th, small
# group to fit before Privacy_Mute without overflowing -- confirmed live, 2026-09-18,
# on the real DesignIdeasCopy project (a live test: remove Shades, then add a new
# "Pool" subsystem as its own 5th group -- caught this exact collision as a real,
# overly-conservative refusal in an earlier version of this function; the ACTUAL
# constraint is physical fit before Privacy_Mute, already reported via `overflow`,
# not the group count itself).
work3b = TEST_DIR / "five_groups_test.cuiw"
shutil.copy(SOURCE, work3b)
five_groups = [["Power"], ["Lights"], ["Camera"], ["Audio"], ["RoomVolume"]]
report3b = design_ideas_write_footer_groups(
    work3b, sdk, five_groups, icon_classes={"RoomVolume": "fa-solid fa-volume-high"})
assert report3b["added"] == ["DividerGroup5", "RoomVolume"], report3b
assert report3b["overflow"] == [], report3b
assert compare.round_trip_check(work3b)
reread3b = design_ideas_read_footer_groups(work3b)
assert reread3b == five_groups, (reread3b, five_groups)
print("design_ideas_write_footer_groups: a 5th group fits, names its divider DividerGroup5"
      " (not a DividerGroup4 collision), round-trips, self-check passes: OK")

# --- 4c. a 5th group that does NOT actually fit must be flagged via `overflow`, ------
# not silently written overlapping DividerGroup4 -- a real live bug (found 2026-09-18
# from a screenshot of the real DesignIdeasCopy project): removing only Shades (not
# Phone/VideoCall too) frees LESS real footer width than 4b's scenario above, just
# enough to visually LOOK like room for one more icon, but not enough for a full new
# group (icon + its own internal divider + the standard 10px gap on both sides) before
# DividerGroup4. An earlier version of this check compared the new last item only
# against Privacy_Mute's OWN left edge (728px) and missed that Pool's real end (723px)
# already overlapped DividerGroup4 itself (715-718px) -- reporting a clean
# `overflow: []` for an actually-broken layout.
work3c = TEST_DIR / "five_groups_overflow_test.cuiw"
shutil.copy(SOURCE, work3c)
design_ideas_write_footer_groups(work3c, sdk, [["Power"], ["Lights"], ["Camera", "Phone", "VideoCall"], ["Audio"]])
report3c = design_ideas_write_footer_groups(
    work3c, sdk, [["Power"], ["Lights"], ["Camera", "Phone", "VideoCall"], ["Audio"], ["Pool"]],
    icon_classes={"Pool": "fa-solid fa-water"})
assert report3c["overflow"], "expected a real overflow report for Pool's actual overlap with DividerGroup4"
assert "DividerGroup4" in report3c["overflow"][0], report3c
print("design_ideas_write_footer_groups: a 5th group that overlaps DividerGroup4 is"
      " correctly flagged via overflow (not silently written broken): OK")

# --- 5. calling write again on an already-edited file (idempotent no-op) -------------
report4 = design_ideas_write_footer_groups(work3, sdk, new_groups3)
assert report4 == {
    "added": [], "removed": [], "removed_pages": [], "repositioned": [],
    "overflow": report4["overflow"],
}, report4
assert compare.round_trip_check(work3)
print("design_ideas_write_footer_groups: re-applying the same groups is a true no-op: OK")

# --- 6. removing a subsystem also deletes its OWN page, leaves its widget alone -------
# (the user's explicit 2026-09-17 instruction: page goes, widget stays for a possible
# later re-add). Set up a realistic project folder: the footer file + a couple of real
# subsystem pages + their popup widgets, matching the reference template's own
# confirmed 1:1 page<->popup naming (Shades.cuig/"Popup - Shades.cuiw", etc). VideoCall
# deliberately gets NO page file, matching the real template (it has none either) --
# proves "not every removed subsystem has a page" is tolerated, not an error.
work4 = TEST_DIR / "page_delete_test.cuiw"
shutil.copy(SOURCE, work4)
project_dir = work4.parent
for name in ("Shades", "Phone", "Lights"):  # Lights is KEPT -- must survive untouched
    (project_dir / f"{name}.cuig").write_text(f"-- fake {name} page --", encoding="utf-8")
    (project_dir / f"Popup - {name}.cuiw").write_text(f"-- fake {name} popup --", encoding="utf-8")

report5 = design_ideas_write_footer_groups(work4, sdk, [["Power"], ["Lights"], ["Camera"], ["Audio"]])
print("write (page delete) report:", report5)
assert set(report5["removed"]) == {"Shades", "Phone", "VideoCall"}, report5
assert set(report5["removed_pages"]) == {"Shades", "Phone"}, report5  # VideoCall had no page
assert not (project_dir / "Shades.cuig").exists(), "Shades.cuig should have been deleted"
assert not (project_dir / "Phone.cuig").exists(), "Phone.cuig should have been deleted"
assert (project_dir / "Lights.cuig").exists(), "Lights.cuig (kept subsystem) must survive"
assert (project_dir / "Popup - Shades.cuiw").exists(), "Popup - Shades.cuiw (widget) must survive"
assert (project_dir / "Popup - Phone.cuiw").exists(), "Popup - Phone.cuiw (widget) must survive"
assert compare.round_trip_check(work4)
print("design_ideas_write_footer_groups: removed subsystems' PAGES deleted, WIDGETS left in place: OK")

# delete_pages=False must leave every page file alone, even for a removed subsystem.
work5 = TEST_DIR / "page_delete_opt_out_test.cuiw"
shutil.copy(SOURCE, work5)
(work5.parent / "Shades.cuig").write_text("-- fake Shades page --", encoding="utf-8")
report6 = design_ideas_write_footer_groups(
    work5, sdk, [["Power"], ["Lights"], ["Camera"], ["Audio"]], delete_pages=False)
assert report6["removed_pages"] == [], report6
assert (work5.parent / "Shades.cuig").exists(), "delete_pages=False must not delete any page"
print("design_ideas_write_footer_groups: delete_pages=False leaves page files untouched: OK")

# --- 7. design_ideas_remove_subsystem_page standalone: missing page is a clean no-op -
assert design_ideas_remove_subsystem_page(TEST_DIR, "NoSuchSubsystem") is False
print("design_ideas_remove_subsystem_page: missing page returns False, no error: OK")

print("Design Ideas Footer Write: all assertions passed.")
