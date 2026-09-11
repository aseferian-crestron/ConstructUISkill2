"""Custom (non-catalog) resolutions: build, add to a project, confirm reflow triggers.

The gap this closes, self-documented in two places before today: `project.py::
build_project_attributes`'s docstring ("resolutions... catalog-sourced only -- this
module has no 'genuinely custom resolution' builder yet") and `devices.py::
to_project_resolution`'s ("This module still has no 'add a genuinely custom
resolution' builder... when one is added, only THAT dict should ever reach
{DeviceResolutionSource}"). Standard resolutions have been added-and-reflowed and
verified live many times this project; a genuinely custom one never has.

Shape verified against a REAL hand-authored custom resolution
(C:\\Solutions\\Polkampally Project\\Polkampally Project.cuip), not invented:
  id: "Custom-L-15cecc01-72fe-4aa9-94ea-9ed7dde33e89-1400-1050"
  resolutionId: "L-1400-1050", resolutionType: "custom", orientation: 1 (landscape)
  width/height: "1400px"/"1050px", IsCustom: true
The GUID embedded in `id` is NOT the project's own Id (confirmed: that file's real
`Id = "33c27476-..."`, unrelated to the `15cecc01-...` in the resolution id) -- it is
a fresh, per-resolution GUID.
"""
import re
import shutil
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import devices  # noqa: E402
from project import add_resolutions_to_project, read_cuip  # noqa: E402

# --- to_custom_resolution: shape matches the real file --------------------------------
custom = devices.to_custom_resolution(width=1400, height=1050, orientation="landscape",
                                      name="Tablet (Landscape)")
assert custom["resolutionType"] == "custom"
assert custom["IsCustom"] is True
assert custom["width"] == "1400px" and custom["height"] == "1050px"
assert custom["widthMedia"] == "1400px" and custom["heightMedia"] == "1050px"
assert custom["orientation"] == 1, "landscape must encode as 1, matching DisplayOrientation"
assert custom["idName"] == custom["VisitedName"] == custom["deviceSpecId"] == "Tablet (Landscape)"
assert custom["resolutionId"] == "L-1400-1050", custom["resolutionId"]
print("to_custom_resolution matches the real file's field values: OK")

# id shape: "Custom-<L|P>-<guid>-<width>-<height>", a FRESH guid each call.
id_match = re.match(r"^Custom-L-([0-9a-f-]{36})-1400-1050$", custom["id"])
assert id_match, custom["id"]
custom2 = devices.to_custom_resolution(width=1400, height=1050, orientation="landscape",
                                       name="Tablet (Landscape)")
assert custom["id"] != custom2["id"], "each custom resolution must get its own fresh guid"
print("id format matches the real file, with a fresh guid per call: OK")

# Portrait encodes correctly too (2, and the "P" id segment).
portrait = devices.to_custom_resolution(width=800, height=1280, orientation="portrait",
                                        name="My Portrait Thing")
assert portrait["orientation"] == 2
assert portrait["id"].startswith("Custom-P-"), portrait["id"]
assert portrait["resolutionId"] == "P-800-1280", portrait["resolutionId"]
print("portrait orientation encodes correctly: OK")

# A caller passing an id-worthy name Construct itself might reject is not this module's
# job to validate (matches the project's existing precedent -- devices.py trusts what
# the catalog/caller gives it, same as fonts.py's own explicit validation is the
# exception, not the rule, for anything that IS user-facing text going into a filename).

# --- add_resolutions_to_project: custom resolutions actually reach {DeviceResolutionSource} ---
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "CustomResolution"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
cuip = OUT / "GenTestProject2.cuip"

attrs_before, source_before, _ = read_cuip(cuip)
ids_before = dict(attrs_before)["DeviceResolutionIds"]
# NOTE 2026-09-11: the live GenTestProject2 now legitimately carries an earlier custom
# resolution ("Custom Panel", added live this same day) -- this test's own precondition
# only needs THIS test's own new resolution to not already be present, not that the
# project has zero custom resolutions at all.

new_custom = devices.to_custom_resolution(width=900, height=600, orientation="landscape",
                                          name="Odd Panel")
assert new_custom["id"] not in ids_before, "the test's own new resolution id must not already be present"
warnings = add_resolutions_to_project(cuip, [new_custom])
print(f"add_resolutions_to_project warnings: {warnings or '(none)'}")

# --- verify ON DISK, not from the function's return value -----------------------------
attrs_after, source_after, _ = read_cuip(cuip)
ids_after = dict(attrs_after)["DeviceResolutionIds"]
assert new_custom["id"] in ids_after.split(","), \
    f"new custom resolution id missing from DeviceResolutionIds: {ids_after}"
print("the new custom resolution's id is in DeviceResolutionIds: OK")

# THE ACTUAL GAP: its own definition must now be in {DeviceResolutionSource}, not just
# referenced by id -- the bug this test exists to catch is exactly a project where the
# id is listed but nothing defines it.
matching_source_entries = [e for e in source_after if e["id"] == new_custom["id"]]
assert len(matching_source_entries) == 1, (
    f"expected exactly one {{DeviceResolutionSource}} entry for the new custom "
    f"resolution, found {len(matching_source_entries)}")
assert matching_source_entries[0]["width"] == "900px"
assert matching_source_entries[0]["height"] == "600px"
print("the new custom resolution's own definition is in {DeviceResolutionSource}: OK")

# Any PRE-EXISTING {DeviceResolutionSource} entries (there are none in this project, but
# the function must not have dropped what was there) survive untouched.
assert source_before == [e for e in source_after if e["id"] != new_custom["id"]], \
    "pre-existing {DeviceResolutionSource} entries must be preserved, not dropped or altered"
print("pre-existing {DeviceResolutionSource} content is preserved: OK")

# --- the whole project still round-trips section-for-section --------------------------
assert compare.round_trip_check(cuip)
print("the rewritten .cuip still round-trips section-for-section: OK")

# --- reflow actually triggered: at least one page got a media block for the new size --
import layout
found_target_block = False
for page in list(OUT.glob("*.cuig")) + list(OUT.glob("*.cuiw")):
    css = page.read_text(encoding="utf-8")
    # landscape query shape confirmed by layout.py's own landscape_media_query
    query = layout.landscape_media_query(900, 600)
    block = layout.find_media_block(css, query)
    if block:
        found_target_block = True
        elements = layout.parse_position_rules(block)
        assert elements, f"{page.name}: a @media block exists for the new resolution but has no elements"
        print(f"{page.name}: reflow produced a populated @media block for 900x600 "
              f"({len(elements)} elements): OK")
assert found_target_block, "no page got a @media block for the new custom resolution -- reflow did not trigger"

print("\nCustom resolution: all assertions passed.")
