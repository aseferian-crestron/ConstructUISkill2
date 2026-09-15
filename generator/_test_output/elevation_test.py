"""shape.py::ELEVATION_LEVELS -- the border/background-contrast substitute for real
shadows (design doc §6, confirmed 2026-09-15: zero shadow/elevation style properties
exist in any mapped type's schema). No new writer: values are meant to be passed as
palette.apply_palette's existing border_width key, verified here against a real
button in a scratch copy."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
import palette  # noqa: E402
import shape  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

assert shape.ELEVATION_LEVELS == {"flat": "0px", "raised": "2px", "raised_more": "4px"}, shape.ELEVATION_LEVELS
print("ELEVATION_LEVELS: flat < raised < raised_more, in px: OK")

# --- applied via the EXISTING palette.apply_palette mechanism, no new writer -----------
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "Elevation"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
page_path = OUT / "ButtonVariants.cuig"

raw_before = page_path.read_text(encoding="utf-8")
parsed = compare.split_sections(raw_before, ".cuig")
css_before = next(c for n, _, c in parsed.sections if n == "Css")

new_css = palette.apply_palette(
    css_before, "ibtncheck", ui_sdk, "ch5-button",
    {"border_width": shape.ELEVATION_LEVELS["raised_more"]},
)
after = layout.parse_all_position_rules(new_css, "(max-width: 99999px)")["ibtncheck"]
assert after["extra_vars"]["--ch5-button--default-border-width"] == "4px", after["extra_vars"]
assert after["extra_vars"]["--ch5-button--regular-width"] == "150px"
print("raised_more (4px) written as ibtncheck's border-width via the existing apply_palette path: OK")

new_full = raw_before.replace(css_before, new_css)
page_path.write_text(new_full, encoding="utf-8", newline="")
assert compare.round_trip_check(page_path), "elevation edit broke the file's round-trip"
print("round-trips byte-identical outside the edited value: OK")

print("Elevation: all assertions passed.")
