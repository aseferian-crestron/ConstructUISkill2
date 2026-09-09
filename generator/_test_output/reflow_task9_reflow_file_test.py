"""Task 9: reflow_file -- both modes, against a hand-built minimal .cuig-shaped file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase5bReflowSmoke"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, css: str) -> None:
    # Minimal but structurally real .cuig: FileMetadata/Html/Css/PageAttributes, in
    # the confirmed fixed order (harness/compare.py::SECTION_ORDER), so
    # harness.compare.round_trip_check can verify this task never corrupts the file
    # outside the Css section.
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        "\n{Html}\n<div id=\"i1\"></div><div id=\"i2\"></div><div id=\"i3\"></div>\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


primary = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
smaller = {"width": 640, "height": 400, "orientation": ORIENTATION_ENUM["landscape"]}

primary_query = layout.orientation_media_query("landscape", 1280, 800)
smaller_query = layout.orientation_media_query("landscape", 640, 400)
source_css = (
    f"@media {primary_query}{{"
    "#i1{display: block; left: 800px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#i2{display: block; left: 950px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "}"
)

# --- Case A: pin_existing with an EMPTY target block (Trigger 1's case) --------------
path_a = OUT / "CaseA.cuig"
make_file(path_a, source_css)
result_a = reflow_file(path_a, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert result_a.warnings == [], f"expected no warnings, got {result_a.warnings}"
assert compare.round_trip_check(path_a), "reflow_file must not corrupt Html/PageAttributes/FileMetadata"
new_css = compare.parse_file(path_a).sections[2][2]  # Css is the 3rd section: FileMetadata, Html, Css, PageAttributes
new_block = layout.find_media_block(new_css, smaller_query)
assert new_block is not None, "expected a new @media block for the smaller resolution"
new_elements = layout.parse_position_rules(new_block)
assert set(new_elements) == {"i1", "i2"}
assert new_elements["i1"]["left"] + new_elements["i1"]["width"] <= 640
assert new_elements["i2"]["left"] + new_elements["i2"]["width"] <= 640
print("Case A (pin_existing, empty target = Trigger 1): OK")

# --- Case B: pin_existing with a NON-EMPTY target -- pinned element must be byte-identical,
#     new element i3 is positioned (via row/wrap/stack) already on-canvas at (20,10),
#     deliberately overlapping the pinned i1's TARGET rect (0,0,50,50) -- this is what
#     actually gets checked for the overlap warning, not i3's source-resolution position.
path_b = OUT / "CaseB.cuig"
existing_target_block = "#i1{display: block; left: 0px; top: 0px; position: absolute; width: 50px; height: 50px;}"
source_with_new = (
    f"@media {primary_query}{{"
    "#i1{display: block; left: 800px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#i3{display: block; left: 20px; top: 10px; position: absolute; width: 40px; height: 20px;}"
    "}"
    f"@media {smaller_query}{{{existing_target_block}}}"
)
make_file(path_b, source_with_new)
result_b = reflow_file(path_b, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert compare.round_trip_check(path_b)
css_b = compare.parse_file(path_b).sections[2][2]
block_b = layout.find_media_block(css_b, smaller_query)
elements_b = layout.parse_position_rules(block_b)
assert elements_b["i1"] == {"left": 0, "top": 0, "width": 50, "height": 50, "z_index": None, "extra_vars": {}}, "pinned element must be untouched"
assert elements_b["i3"] == {"left": 20, "top": 10, "width": 40, "height": 20, "z_index": None, "extra_vars": {}}, "i3 is already on-canvas at its source position, so X/Y Tier 1 apply zero offset"
assert any("i3" in w and "i1" in w for w in result_b.warnings), f"expected an overlap warning naming i3 and i1, got {result_b.warnings}"
print("Case B (pin_existing, non-empty target, pinned preserved + overlap flagged): OK")

# --- Case C: full_refit -- ignores whatever was in target, refits everything fresh --
path_c = OUT / "CaseC.cuig"
make_file(path_c, source_with_new)
result_c = reflow_file(path_c, target_resolution=smaller, source_resolution=primary, mode="full_refit")
assert compare.round_trip_check(path_c)
css_c = compare.parse_file(path_c).sections[2][2]
block_c = layout.find_media_block(css_c, smaller_query)
elements_c = layout.parse_position_rules(block_c)
assert set(elements_c) == {"i1", "i3"}
assert elements_c["i1"] != {"left": 0, "top": 0, "width": 50, "height": 50, "z_index": None, "extra_vars": {}}, "full_refit must NOT preserve the old target position -- proves the two modes differ"
print("Case C (full_refit, old target position discarded): OK")

# --- Case D (added 2026-09-09, task review): regression guard for two bugs found by
#     review -- (1) universal-newline translation in Path.read_text/write_text
#     silently rewrote every line ending in the file (LF -> CRLF on Windows), breaking
#     the "leave everything outside Css byte-identical" contract for any non-native-
#     newline file; (2) compare.round_trip_check alone can't catch this since it only
#     verifies the file splits/reassembles self-consistently, not that content matches
#     what was there BEFORE reflow_file ran -- which is exactly why Case A/B/C's
#     round_trip_check calls didn't catch it. This case writes a hand-built LF-only
#     file with write_bytes (never silently re-encoded to the platform's native line
#     ending the way write_text would), and compares the non-Css sections' bytes
#     before vs. after reflow_file, not just internal self-consistency.
path_d = OUT / "CaseD.cuig"
path_d.write_bytes(
    b'{FileMetadata}\nSchema = "1.0.0.0"\n'
    b'\n{Html}\n<div id="i1"></div><div id="i2"></div>\n'
    + f"\n{{Css}}\n{source_css}\n".encode("utf-8")
    + b'\n{PageAttributes}\n\n[Attributes]\nName = "P"\n'
)
before_sections = {name: content for name, _, content in compare.parse_file(path_d).sections}
result_d = reflow_file(path_d, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert result_d.warnings == [], f"expected no warnings, got {result_d.warnings}"
assert compare.round_trip_check(path_d)
after_sections = {name: content for name, _, content in compare.parse_file(path_d).sections}
for section_name in ("FileMetadata", "Html", "PageAttributes"):
    assert after_sections[section_name] == before_sections[section_name], (
        f"{section_name} section must be byte-identical (including line endings) "
        "before vs. after reflow_file -- reflow_file must only ever touch Css"
    )
assert b"\r\n" not in path_d.read_bytes(), "reflow_file must not introduce CRLF into an LF-only file"
print("Case D (LF-only file, non-Css sections byte-identical before/after reflow_file): OK")

# --- Case E (added 2026-09-09, task review): malformed input must produce a warning,
#     never raise -- reflow_file's first draft let a StopIteration (missing {Css}
#     section) escape uncaught.
path_e = OUT / "CaseE.cuig"
path_e.write_text(
    "{FileMetadata}\nSchema = \"1.0.0.0\"\n\n{Html}\n<div id=\"i1\"></div>\n"
    "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",  # no {Css} section at all
    encoding="utf-8",
)
result_e = reflow_file(path_e, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert any("Css" in w for w in result_e.warnings), f"expected a warning naming the missing Css section, got {result_e.warnings}"
print("Case E (missing {Css} section produces a warning, does not raise): OK")

# --- Case F (added 2026-09-09, task review): an invalid mode must always raise,
#     regardless of whether the target block happens to be empty -- the first draft
#     only validated mode AFTER branching on the target block's emptiness, so a typo'd
#     mode silently performed a full refit instead of raising when the target was empty.
path_f = OUT / "CaseF.cuig"
make_file(path_f, source_css)  # empty target block -- the branch that used to skip validation
try:
    reflow_file(path_f, target_resolution=smaller, source_resolution=primary, mode="pin_exsiting")  # typo, deliberate
    assert False, "expected ValueError for an invalid mode, even with an empty target block"
except ValueError:
    pass
print("Case F (invalid mode always raises, independent of target-block emptiness): OK")

# --- Case G (added 2026-09-09, final whole-branch review): the single most important
#     regression guard in this file. Every case above hand-authors ONE @media block
#     containing every element's #id{} rule together -- a shape the real generator
#     NEVER produces. layout.py::build_position_css is called once per element, so a
#     real 3-button page has THREE separate `@media (max-width: 99999px){...}` blocks
#     (one per button), all with the byte-identical query string -- confirmed against
#     a real ButtonVariants.cuig. The old find_media_block/find_media_block_span
#     (single-match) silently found only the FIRST element and produced zero
#     warnings; this case would have failed loudly against that bug.
path_g = OUT / "CaseG.cuig"
buttons = [("ibtnicon", 10), ("ibtnimage", 200), ("ibtncheck", 400)]
per_element_css = "".join(
    f"@media (max-width: 99999px){{#{bid}{{display: block; left: {left}px; top: 10px; position: absolute; z-index: 1; width: 100px; height: 50px;}}}}"
    f"@media {primary_query}{{#{bid}{{display: block; left: {left}px; top: 10px; position: absolute; width: 100px; height: 50px;}}}}"
    for bid, left in buttons
)
make_file(path_g, per_element_css)
result_g = reflow_file(path_g, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert result_g.warnings == [], f"expected no warnings, got {result_g.warnings}"
assert compare.round_trip_check(path_g)
css_g = compare.parse_file(path_g).sections[2][2]
elements_g = layout.parse_all_position_rules(css_g, smaller_query)
assert set(elements_g) == {"ibtnicon", "ibtnimage", "ibtncheck"}, (
    f"expected all 3 real-shape elements to be found and fit, got {set(elements_g)} -- "
    "this is exactly the multi-block-per-query bug if it regresses"
)
for eid, e in elements_g.items():
    assert e["left"] + e["width"] <= 640, f"{eid} must be on-canvas (right edge)"
    assert e["top"] + e["height"] <= 400, f"{eid} must be on-canvas (bottom edge)"
print("Case G (real per-element-block CSS shape, all 3 elements found and fit): OK")

# --- Case H (added 2026-09-09, final whole-branch review): the write-path mirror of
#     Case G -- a TARGET resolution that already has multiple per-element blocks
#     (e.g. from an earlier reflow run under the old bug) must consolidate down to
#     exactly one block for that query, never leave duplicate #id{} rules under the
#     same query with a stale one silently winning the CSS cascade.
path_h = OUT / "CaseH.cuig"
stale_target_blocks = "".join(
    f"@media {smaller_query}{{#{bid}{{display: block; left: 0px; top: 0px; position: absolute; width: 40px; height: 20px;}}}}"
    for bid, _ in buttons[:2]  # only 2 of the 3 already (mis-)reflowed, one per stale block
)
make_file(path_h, per_element_css + stale_target_blocks)
result_h = reflow_file(path_h, target_resolution=smaller, source_resolution=primary, mode="full_refit")
assert compare.round_trip_check(path_h)
css_h = compare.parse_file(path_h).sections[2][2]
target_spans_h = layout.find_media_block_spans(css_h, smaller_query)
assert len(target_spans_h) == 1, f"expected exactly one consolidated block for the target query, found {len(target_spans_h)}"
elements_h = layout.parse_all_position_rules(css_h, smaller_query)
assert set(elements_h) == {"ibtnicon", "ibtnimage", "ibtncheck"}, "consolidation must not lose or duplicate any element"
print("Case H (multiple stale target blocks for one query consolidate to exactly one, no duplicates/losses): OK")

print("\nTASK 9: reflow_file -- ALL CHECKS PASSED")
