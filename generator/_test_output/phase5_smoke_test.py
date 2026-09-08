"""Phase 5 smoke test: real device/resolution catalog + add-resolutions-to-an-existing-
project -- verified via harness round-trip and structural checks (no real Construct-
authored multi-resolution .cuip exists in the reference project to diff against; this is
the same "confirmed the writer mirrors build_project_attributes' own shape" standard
already used for solution/project creation in Phase 2)."""
import sys
import tomllib
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from project import build_project_attributes, write_cuip, add_resolutions_to_project  # noqa: E402
from devices import read_catalog, to_project_resolution  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase5Smoke"
OUT.mkdir(parents=True, exist_ok=True)


def parse_cuip(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    sections = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        sections[m.group(1)] = raw[start:end]
    return {
        "attrs": tomllib.loads(sections["ProjectAttributes"])["Attributes"],
        "device_resolution_source": __import__("json").loads(sections["DeviceResolutionSource"]),
    }


catalog = read_catalog()
assert len(catalog.entries) == 74, f"expected the real 74-entry catalog, got {len(catalog.entries)}"

# --- 1. TSW-1070 is landscape-only real hardware -- no portrait entry exists ---------
assert not catalog.supports_both_orientations("TSW-1070")
assert catalog.supports_both_orientations("TST-1080")
print("catalog: TSW-1070 correctly landscape-only, TST-1080 correctly supports both "
      "orientations (corrects an earlier unconfirmed 'TSW-1070 Portrait' guess)")

# --- 2. create a project with ONE resolution, then ADD a second afterward ------------
tsw = to_project_resolution(catalog.by_id_name("TSW-1070"))
attrs, drs = build_project_attributes(name="ResTest", sdk_id="CH5:2.18.0", resolutions=[tsw])
cuip_path = OUT / "ResTest.cuip"
write_cuig_path = cuip_path
write_cuip(cuip_path, attrs, drs)
assert compare.round_trip_check(cuip_path), "single-resolution project round-trip failed"

before = parse_cuip(cuip_path)
assert before["attrs"]["DeviceResolutionIds"] == "D-L-TSW1070-1280-0800"
assert before["attrs"]["ContractIsStale"] == "true"  # already true from creation

tst_landscape = to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape"))
tst_portrait = to_project_resolution(catalog.by_id_name("TST-1080", orientation="portrait"))
add_resolutions_to_project(cuip_path, [tst_landscape, tst_portrait])
assert compare.round_trip_check(cuip_path), "add-resolutions round-trip failed"

after = parse_cuip(cuip_path)
assert after["attrs"]["DeviceResolutionIds"] == "D-L-TSW1070-1280-0800,D-L-TST1080-1280-0800,D-P-TST1080-0800-1280"
assert len(after["device_resolution_source"]) == 3
assert all(e["ProjectId"] == after["attrs"]["Id"] for e in after["device_resolution_source"])
# everything else about the project (Id, ThemeId, SdkId, ...) must be untouched
for key in ("Id", "ThemeId", "SdkId", "ComponentKey", "Name"):
    assert before["attrs"][key] == after["attrs"][key], f"{key} changed unexpectedly"
print("add_resolutions_to_project: DeviceResolutionIds/DeviceResolutionSource correctly "
      "extended, ProjectId wired on new entries, rest of the project untouched, round-trip OK")

# --- 3. add a resolution to a project that starts with ZERO resolutions --------------
attrs0, drs0 = build_project_attributes(name="ZeroResTest", sdk_id="CH5:2.18.0")
assert "DeviceResolutionIds" not in dict(attrs0)
zero_path = OUT / "ZeroResTest.cuip"
write_cuip(zero_path, attrs0, drs0)
add_resolutions_to_project(zero_path, [tsw])
assert compare.round_trip_check(zero_path), "add-resolution-from-zero round-trip failed"
zero_after = parse_cuip(zero_path)
assert zero_after["attrs"]["DeviceResolutionIds"] == "D-L-TSW1070-1280-0800"
# key order must still match build_project_attributes' own order (inserted right after DefaultFontFamily)
keys = list(zero_after["attrs"].keys())
assert keys.index("DeviceResolutionIds") == keys.index("DefaultFontFamily") + 1
print("add_resolutions_to_project: correctly inserts DeviceResolutionIds (right after "
      "DefaultFontFamily, matching build_project_attributes' own key order) for a "
      "project that started with zero resolutions")

print("\nPHASE 5 SMOKE TEST: ALL CHECKS PASSED")
