"""OverrideThemeColor/ThemePageColor default: every project this generator creates
must default to black-pinned, per the user's standing rule ("between page flips you
see the default theme color and black is more pleasing").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from project import build_project_attributes  # noqa: E402

attrs, _ = build_project_attributes(name="ThemeColorTest", sdk_id="CH5:2.18.0")
d = dict(attrs)
assert d["ThemePageColor"] == "#000000", d["ThemePageColor"]
assert d["OverrideThemeColor"] == "True", d["OverrideThemeColor"]
print("new projects default to OverrideThemeColor=True, ThemePageColor=#000000: OK")

# still explicitly overridable, for a caller with a real reason to differ
attrs2, _ = build_project_attributes(
    name="ThemeColorTest2", sdk_id="CH5:2.18.0",
    theme_page_color="#ffffff", override_theme_color=False,
)
d2 = dict(attrs2)
assert d2["ThemePageColor"] == "#ffffff" and d2["OverrideThemeColor"] == "False"
print("explicit caller values still override the default: OK")

print("\nTheme page color default: all assertions passed.")
