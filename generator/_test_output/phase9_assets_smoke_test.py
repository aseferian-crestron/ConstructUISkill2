"""Phase 9 (pulled forward) smoke test: import a real image as a Construct asset --
verified via harness round-trip AND an exact structural comparison against the real
reference asset (C:\\Solutions\\ClaudeSamples\\Components\\assets\\CrimsonSilk.cuia), which
is also the exact asset the reference project's image-type button already references."""
import sys
import tomllib
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from assets import import_asset  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase9AssetsSmoke"
OUT.mkdir(parents=True, exist_ok=True)
REF_DIR = Path(r"C:\Solutions\ClaudeSamples\Components")


def parse_cuia(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    sections = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        sections[m.group(1)] = raw[start:end]
    return tomllib.loads(sections["AssetAttributes"])["Attributes"]


# --- import the REAL reference image, reproducing its own real asset exactly ----------
project_dir = OUT / "AssetProject"
info = import_asset(
    project_dir, name="CrimsonSilk",
    source_image_path=REF_DIR / "assets" / "CrimsonSilk.jpg",
    asset_id="498f8b9e-eade-4d9d-9475-49bb03d4324b",  # the real asset's own confirmed Id
)
assert compare.round_trip_check(info.cuia_path), ".cuia round-trip failed"
assert info.image_path.is_file() and info.image_path.stat().st_size > 0
print("asset import: .cuia round-trip OK, image file copied")

gen_attrs = parse_cuia(info.cuia_path)
ref_attrs = parse_cuia(REF_DIR / "assets" / "CrimsonSilk.cuia")
assert list(gen_attrs.keys()) == list(ref_attrs.keys()), (list(gen_attrs.keys()), list(ref_attrs.keys()))
assert gen_attrs == ref_attrs, {k: (gen_attrs[k], ref_attrs[k]) for k in ref_attrs if gen_attrs.get(k) != ref_attrs[k]}
print(f"asset attributes: {len(gen_attrs)}/{len(ref_attrs)} keys match real CrimsonSilk.cuia "
      f"EXACTLY (including AspectRatio computed independently in Python vs C#'s ImageSharp: "
      f"{gen_attrs['AspectRatio']!r})")

# --- wire the imported asset into an image-type button, exactly like the real project -
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sdk import read_sdk  # noqa: E402
from ch5_button import build_default_button_attributes  # noqa: E402

sdk = read_sdk("2.18.0")
btn_attrs = dict(build_default_button_attributes(
    sdk, component_name="ImageButton", element_id="ix",
    image_icon_type="imageasset", asset_id=info.id,
))
assert btn_attrs["assetid"] == "498f8b9e-eade-4d9d-9475-49bb03d4324b"
print("button wiring: assetid correctly set to the imported asset's Id")

print("\nPHASE 9 (ASSETS) SMOKE TEST: ALL CHECKS PASSED")
