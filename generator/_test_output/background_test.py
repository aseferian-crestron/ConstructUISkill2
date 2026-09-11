"""Page/widget background placement (generator/background.py): choose_background_tag,
the ch5-image PROFILES entry verified against its own real reference instance (see
component_flat_types_test.py's NO_REFERENCE_IN_THIS_PROJECT note), then
add_page_background applied to a real page in a scratch copy of GenTestProject2 --
initial placement AND propagation into every other already-configured resolution,
then a FURTHER resolution added afterward to prove reflow.py's background-forcing
works on the ongoing add-resolution path too, not just at initial placement.
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import background  # noqa: E402
import compare  # noqa: E402
import component as component_module  # noqa: E402
import devices  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
from project import add_resolutions_to_project, read_cuip  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- choose_background_tag -------------------------------------------------------------
assert background.choose_background_tag(needs_video=False) == "ch5-image"
assert background.choose_background_tag(needs_video=True) == "ch5-background"
print("choose_background_tag: image by default, background when video is needed: OK")

# --- ch5-image PROFILES entry verified against ITS OWN real reference instance --------
# (no instance in C:\Solutions\ClaudeSamples\Components -- see component_flat_types_
# test.py's NO_REFERENCE_IN_THIS_PROJECT -- grounded instead against this file)
real_raw = Path(r"C:\Solutions\ClaudeSamples\ClaudeCustomModeProject\Page1.cuig").read_text(encoding="utf-8")
real_tag = re.search(r"<ch5-image\b[^>]*>", real_raw).group(0)
real_attrs = {k: v.replace("&quot;", '"') for k, v in re.findall(r'([\w-]+)="([^"]*)"', real_tag)}
ours = dict(component_module.build_component_attributes(
    ui_sdk, "ch5-image", component_name=real_attrs["componentname"], element_id=real_attrs["id"]))
ours_lower = {k.lower(): v for k, v in ours.items()}
real_lower = {k.lower(): v for k, v in real_attrs.items() if k not in ("id", "componentname")}
ours_lower.pop("id", None)
ours_lower.pop("componentname", None)
missing = set(real_lower) - set(ours_lower)
extra = set(ours_lower) - set(real_lower)
assert not missing, f"reference has attributes we do not generate: {sorted(missing)}"
assert not extra, f"we generate attributes the reference lacks: {sorted(extra)}"
for k in real_lower:
    assert ours_lower[k] == real_lower[k], f"{k}: ours {ours_lower[k]!r} != real {real_lower[k]!r}"
print("ch5-image PROFILES entry matches its own real reference instance exactly: OK")

# --- add_page_background: initial placement + propagation to every existing resolution -
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "Background"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
cuip = OUT / "GenTestProject2.cuip"
page_path = OUT / "MainPage.cuig"

attrs, _, _ = read_cuip(cuip)
existing_resolutions = [i for i in dict(attrs)["DeviceResolutionIds"].split(",") if i]
assert len(existing_resolutions) >= 2, "test needs a project with multiple resolutions already"

raw_before = page_path.read_text(encoding="utf-8")
before_elements = layout.parse_all_position_rules(
    compare.split_sections(raw_before, ".cuig").sections[2][2], "(max-width: 99999px)")

warnings = background.add_page_background(page_path, cuip, ui_sdk, needs_video=False)
print(f"add_page_background warnings: {warnings or '(none)'}")

raw_after = page_path.read_text(encoding="utf-8")
parsed_after = compare.split_sections(raw_after, ".cuig")
html_after = next(c for n, _, c in parsed_after.sections if n == "Html")
css_after = next(c for n, _, c in parsed_after.sections if n == "Css")

bg_match = re.search(r'<ch5-image\b[^>]*\bid="([^"]+)"[^>]*>', html_after)
assert bg_match, "no ch5-image tag found in the rewritten page"
bg_id = bg_match.group(1)
assert 'ccid_pageBackground="true"' in bg_match.group(0)
print(f"background element {bg_id!r} placed with the pageBackground marker: OK")

catch_all = layout.parse_all_position_rules(css_after, "(max-width: 99999px)")[bg_id]
assert catch_all["left"] == 0 and catch_all["top"] == 0
assert catch_all["width"] == 1280 and catch_all["height"] == 800  # TSW-1070, this project's landscape primary
assert catch_all["z_index"] == -99
print(f"catch-all placement: (0,0), 1280x800 (primary), z-index -99: OK")

# every pre-existing element on the page is completely untouched
for eid, before in before_elements.items():
    after = layout.parse_all_position_rules(css_after, "(max-width: 99999px)")[eid]
    assert before == after, f"{eid}: pre-existing element changed unexpectedly"
print("every pre-existing element on the page is completely unaffected: OK")

# propagated into EVERY other already-configured resolution, always (0,0) + exact size
for rid in existing_resolutions:
    catalog = devices.read_catalog()
    try:
        entry = devices.to_project_resolution(catalog.by_id(rid))
    except KeyError:
        _, source, _ = read_cuip(cuip)
        entry = next(e for e in source if e["id"] == rid)
    width = int(entry["width"].removesuffix("px")) if isinstance(entry["width"], str) else entry["width"]
    height = int(entry["height"].removesuffix("px")) if isinstance(entry["height"], str) else entry["height"]
    orientation = "landscape" if entry["orientation"] in ("landscape", 1) else "portrait"
    query = (layout.landscape_media_query(width, height) if orientation == "landscape"
             else layout.orientation_media_query("portrait", width, height))
    elements = layout.parse_all_position_rules(css_after, query)
    assert bg_id in elements, f"{rid}: background not propagated into this resolution's block"
    e = elements[bg_id]
    assert e["left"] == 0 and e["top"] == 0 and e["width"] == width and e["height"] == height, \
        f"{rid}: background not forced to (0,0)+{width}x{height}, got {e}"
print(f"background correctly propagated into all {len(existing_resolutions)} pre-existing resolutions: OK")

assert compare.round_trip_check(page_path)
print("the rewritten .cuig still round-trips section-for-section: OK")

# --- a FURTHER resolution added afterward also gets the background, via reflow.py's ---
# --- own background-forcing on the ongoing add-resolution path, not just initial place -
new_custom = devices.to_custom_resolution(width=500, height=400, orientation="landscape", name="Tiny Panel")
add_warnings = add_resolutions_to_project(cuip, [new_custom])
print(f"add_resolutions_to_project warnings: {add_warnings or '(none)'}")

raw_final = page_path.read_text(encoding="utf-8")
css_final = compare.split_sections(raw_final, ".cuig").sections[2][2]
new_query = layout.landscape_media_query(500, 400)
new_elements = layout.parse_all_position_rules(css_final, new_query)
assert bg_id in new_elements, "background not forced into a resolution added AFTER initial placement"
e = new_elements[bg_id]
assert e["left"] == 0 and e["top"] == 0 and e["width"] == 500 and e["height"] == 400, e
print("a resolution added AFTER initial background placement also gets it forced to (0,0)+full size: OK")

print("\nPage/widget background: all assertions passed.")
