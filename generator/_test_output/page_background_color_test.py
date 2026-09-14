"""page.py::set_page_background_color: setting a solid background color on an
EXISTING page/widget's {PageAttributes} table -- the missing "after the fact"
counterpart to build_page_attributes/build_widget_attributes' creation-time
DisplayBackgroundColor/BackgroundColor support.
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import page as page_module  # noqa: E402

SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "PageBackgroundColor"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)

page_path = OUT / "MainPage.cuig"
raw_before = page_path.read_text(encoding="utf-8")
assert 'DisplayBackgroundColor = "False"' in raw_before
assert not any(line.strip().startswith("BackgroundColor = ") for line in raw_before.splitlines())
html_before = re.search(r"\{Html\}\n(.*?)\n\n\{Css\}", raw_before, re.S).group(1)
css_before = re.search(r"\{Css\}\n(.*?)\n\n\{PageAttributes\}", raw_before, re.S).group(1)
print("baseline: MainPage.cuig has DisplayBackgroundColor=False, no BackgroundColor: OK")

page_module.set_page_background_color(page_path, "#f7f7f7")
raw_after = page_path.read_text(encoding="utf-8")
assert 'DisplayBackgroundColor = "True"' in raw_after
assert 'BackgroundColor = "#f7f7f7"' in raw_after
# BackgroundColor must appear immediately after DisplayBackgroundColor
assert 'DisplayBackgroundColor = "True"\nBackgroundColor = "#f7f7f7"\n' in raw_after
print("DisplayBackgroundColor flipped True, BackgroundColor inserted right after it: OK")

# Html/Css are completely untouched
html_after = re.search(r"\{Html\}\n(.*?)\n\n\{Css\}", raw_after, re.S).group(1)
css_after = re.search(r"\{Css\}\n(.*?)\n\n\{PageAttributes\}", raw_after, re.S).group(1)
assert html_after == html_before
assert css_after == css_before
print("Html/Css sections are byte-identical to before: OK")

assert compare.round_trip_check(page_path)
print("the rewritten .cuig still round-trips section-for-section: OK")

# --- applying again with a different color updates in place, no duplicate lines -------
page_module.set_page_background_color(page_path, "#222222")
raw_final = page_path.read_text(encoding="utf-8")
assert 'BackgroundColor = "#222222"' in raw_final
bg_lines = [line for line in raw_final.splitlines() if line.strip().startswith("BackgroundColor = ")]
assert len(bg_lines) == 1, bg_lines
assert compare.round_trip_check(page_path)
print("re-applying with a different color updates in place, no duplicate line, round-trips: OK")

# --- also works on a widget (.cuiw), whose real key order has no Start/Preload/Cache/---
# --- Visibility fields at all -- DisplayBackgroundColor is still the anchor key -------
widget_path = OUT / "MyWidget.cuiw"
raw_widget_before = widget_path.read_text(encoding="utf-8")
page_module.set_page_background_color(widget_path, "#b31b1b")
raw_widget_after = widget_path.read_text(encoding="utf-8")
assert 'BackgroundColor = "#b31b1b"' in raw_widget_after
assert compare.round_trip_check(widget_path)
print("set_page_background_color also works on a real widget (.cuiw): OK")

print("\nPage/widget background color: all assertions passed.")
