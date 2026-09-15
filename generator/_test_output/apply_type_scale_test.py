"""typography.py::apply_type_scale applied to a real component in a scratch copy --
same discipline as custom_style_test.py: verify against real GenTestProject2 files,
never a synthetic fixture."""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
import typography  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- a nonexistent role raises KeyError up front, nothing written ----------------------
try:
    typography.apply_type_scale("", "ibtnicon", ui_sdk, "ch5-button", "subtitle")
    raise AssertionError("expected KeyError for an unknown type-scale role")
except KeyError:
    pass
print("apply_type_scale: an unknown role raises KeyError before writing anything: OK")

# --- applied to a real component in a scratch copy -------------------------------------
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "TypeScale"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
page_path = OUT / "ButtonVariants.cuig"

raw_before = page_path.read_text(encoding="utf-8")
parsed = compare.split_sections(raw_before, ".cuig")
css_before = next(c for n, _, c in parsed.sections if n == "Css")

elements_before = layout.parse_all_position_rules(css_before, "(max-width: 99999px)")
before = elements_before["ibtnicon"]
assert before["width"] == 150 and before["height"] == 50
print("baseline: ibtnicon's existing position/size confirmed before any edit: OK")

new_css = typography.apply_type_scale(css_before, "ibtnicon", ui_sdk, "ch5-button", "heading")

after = layout.parse_all_position_rules(new_css, "(max-width: 99999px)")["ibtnicon"]
assert after["left"] == before["left"] and after["top"] == before["top"]
assert after["width"] == before["width"] and after["height"] == before["height"]
assert after["extra_vars"]["--ch5-button--regular-font-size"] == "28px", after["extra_vars"]
print("ibtnicon: heading role (28px) written to the real --ch5-* var, position/size preserved: OK")

ibtnicon_rule_match = re.search(r"#ibtnicon\{([^{}]*)\}", new_css)
assert ibtnicon_rule_match, "no #ibtnicon{} rule found"
assert "Label_font-size: 28px" in ibtnicon_rule_match.group(1), ibtnicon_rule_match.group(1)
print("the sector-prefixed pseudo-property (Label_font-size) is written alongside the CSS var: OK")

# --- round-trips the whole file byte-identical outside the edited value ----------------
new_full = raw_before.replace(css_before, new_css)
page_path.write_text(new_full, encoding="utf-8", newline="")
assert compare.round_trip_check(page_path), "type-scale edit broke the file's round-trip"

# --- a sibling element the caller did NOT touch is completely unaffected ---------------
sibling_before = elements_before["ibtnimage"]
sibling_after = layout.parse_all_position_rules(new_css, "(max-width: 99999px)")["ibtnimage"]
assert sibling_before == sibling_after, "an untouched sibling element changed"
print("a sibling element not passed to apply_type_scale is completely unaffected: OK")

print("Apply type scale: all assertions passed.")
