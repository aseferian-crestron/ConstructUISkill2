"""Phase 8 (fonts), first slice: global font swap.

Verified against a copy of the real, live GenTestProject2 harness project (not a
synthetic fixture) -- it already has ccid_ActiveFont and font-family CSS on real
components (buttons, dpad, keypad, toggle, text, textinput, media player), which is a
stronger check than anything hand-built here could be. That is exactly how this test
caught the two casing/quoting bugs AND how the user, applying the first version live,
caught the validation gap this file now pins.
"""
import re
import shutil
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import fonts  # noqa: E402
from fonts import available_fonts, replace_font_in_text, set_page_font, set_project_font  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")

OUT = Path(__file__).resolve().parent / "FontsGlobalSwap"
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")

if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)

# --- unit-level: the raw text substitution (no validation -- see set_page_font for that) --
html = '<ch5-button ccid_ActiveFont="\'Roboto\'" id="i1"></ch5-button>'
new_html, n = replace_font_in_text(html, "Arial")
assert n == 1 and new_html == '<ch5-button ccid_ActiveFont="\'Arial\'" id="i1"></ch5-button>', new_html

toml_line = 'ccid_ActiveFont = "\'Roboto\'"'
new_toml, n = replace_font_in_text(toml_line, "Arial")
assert n == 1 and new_toml == 'ccid_ActiveFont = "\'Arial\'"', new_toml

css = '#i1 .ch5-button :not(i):not(svg){font-family:"Roboto";}'
new_css, n = replace_font_in_text(css, "Arial")
assert n == 1 and new_css == '#i1 .ch5-button :not(i):not(svg){font-family:"Arial";}', new_css

# Attribute name casing: Construct's own Html view lowercases attribute names on
# save (confirmed against the reference project -- every file's Html section carries
# `ccid_activefont`, its mirrored PageAttributes TOML carries `ccid_ActiveFont`, 0
# exceptions across 12 files). The generator itself currently writes camelCase into
# both, so this must handle either without re-casing the key that is actually there.
Q = "'"
for key in ("ccid_ActiveFont", "ccid_activefont", "CCID_ACTIVEFONT"):
    out, n = replace_font_in_text(f'{key}="{Q}Roboto{Q}"', "Arial")
    assert n == 1 and out == f'{key}="{Q}Arial{Q}"', (key, out)
print("ccid_ActiveFont matches regardless of case, preserving the key as found: OK")

# font-family quote style: layout.py always writes double quotes WITH a space
# (`font-family: "Roboto"`); a real file (ReflowTest.cuig) carries single quotes with
# NO space (`font-family:'Roboto'`) in 21 places. Both must work, each preserving its
# own quote character rather than normalizing to one style.
for css, quote in (("font-family:'Roboto';", "'"), ('font-family: "Roboto";', '"')):
    out, n = replace_font_in_text(css, "Inter")
    assert n == 1 and out == css.replace("Roboto", "Inter"), (css, out)
    assert out.count(quote) == css.count(quote), (css, out)
print("font-family matches single or double quotes, preserving whichever is used: OK")

# All four selector shapes from FontSupportConstants, confirmed against the reference
# project byte-for-byte (see fonts.py's module docstring).
for shape in (
    '#i1 .ch5-button :not(i):not(svg){font-family:"Roboto";}',
    '#i1 :not(i):not(svg){font-family:"Roboto";}',
    '#i1 span:not(.has-icon, .has-icon span){font-family:"Roboto";}',
    '#i1 span:not(.dpad-btn-icon){font-family:"Roboto";}',
):
    out, n = replace_font_in_text(shape, "Inter")
    assert n == 1 and '"Inter"' in out and "Roboto" not in out, (shape, out)
print("raw substitution handles the attribute and all four CSS selector shapes: OK")

# Text with neither pattern is untouched, count 0 -- no spurious rewrite.
plain = "<div>hello</div>"
out, n = replace_font_in_text(plain, "Arial")
assert n == 0 and out == plain
print("text with no font mention is untouched: OK")

# --- available_fonts: exactly the SDK's system default + Crestron custom list --------
# The user applied an earlier version with "Montserrat" and every component's Font
# Family field went EMPTY in the Properties Grid: the attribute/CSS were written
# correctly, but that dropdown only ever offers these names (plus imported webfonts,
# which this phase defers) -- see fonts.py's module docstring for the client-side trace.
fonts_list = available_fonts(sdk)
assert fonts_list == ["Roboto", "Crestron AV", "Crestron General",
                      "Crestron Lighting-HVAC", "Crestron Simple Icons"], fonts_list
print(f"available_fonts: {fonts_list}: OK")

# --- set_page_font / set_project_font now REFUSE anything not on that list -----------
button_page = OUT / "ButtonVariants.cuig"
before_bytes = button_page.read_bytes()
try:
    set_page_font(button_page, "Montserrat", sdk)
except ValueError as e:
    assert "Montserrat" in str(e) and "Crestron AV" in str(e), str(e)
    assert button_page.read_bytes() == before_bytes, "a rejected font must not touch the file"
    print("set_page_font refuses a non-selectable font and leaves the file untouched: OK")
else:
    raise AssertionError("set_page_font must reject a font not in available_fonts")

cuip = OUT / "GenTestProject2.cuip"
before_cuip_bytes = cuip.read_bytes()
try:
    set_project_font(cuip, "Montserrat", sdk)
except ValueError:
    assert cuip.read_bytes() == before_cuip_bytes, ".cuip must not change on a rejected font"
    print("set_project_font refuses project-wide and leaves the .cuip untouched: OK")
else:
    raise AssertionError("set_project_font must reject a font not in available_fonts")

# --- file-level: FileMetadata is never touched, using a VALID font -------------------
before = button_page.read_text(encoding="utf-8")
before_metadata = re.search(r"\{FileMetadata\}.*?(?=\{Html\})", before, re.DOTALL).group(0)

# Target chosen to guarantee it differs from whatever font the live project currently
# holds -- hardcoding one (as an earlier version of this test did) broke the moment this
# session's own live-project font fix landed and the source file's starting font
# happened to match the hardcoded target, silently turning the "swap" into a no-op.
page_starting_font = re.search(r"ccid_ActiveFont=\"'([^']*)'\"", before).group(1)
page_target_font = next(f for f in fonts_list if f != page_starting_font)

count = set_page_font(button_page, page_target_font, sdk)
assert count > 0, "ButtonVariants.cuig is expected to mention some font"
after = button_page.read_text(encoding="utf-8")
after_metadata = re.search(r"\{FileMetadata\}.*?(?=\{Html\})", after, re.DOTALL).group(0)
assert before_metadata == after_metadata, "FileMetadata (Modified timestamp) must not change"
assert page_starting_font not in after and after.count(f'"{page_target_font}"') >= 1
print(f"set_page_font ({page_starting_font!r} -> {page_target_font!r}): Html/Css/"
      "PageAttributes rewritten, FileMetadata untouched: OK")

# Idempotent: swapping to the same font twice is a byte-for-byte no-op.
after2 = button_page.read_text(encoding="utf-8")
set_page_font(button_page, page_target_font, sdk)
assert button_page.read_text(encoding="utf-8") == after2
print("re-applying the same font is a content no-op: OK")

# --- Html and the mirrored TOML element attribute stay in agreement -------------------
raw = after
headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
sections = {}
for i, m in enumerate(headers):
    end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
    sections[m.group(1)] = raw[m.end():end]
page = tomllib.loads(sections["PageAttributes"])
toml_fonts = {e["Attributes"].get("ccid_ActiveFont") for e in page["Elements"]
              if "ccid_ActiveFont" in e["Attributes"]}
assert toml_fonts == {f"'{page_target_font}'"}, toml_fonts
html_fonts = set(re.findall(r'ccid_ActiveFont="([^"]*)"', sections["Html"]))
assert html_fonts == {f"'{page_target_font}'"}, html_fonts
print("Html and TOML element attributes agree after the swap: OK")

# --- round-trip: only content changed, structure survives ------------------------------
assert compare.round_trip_check(button_page)
print("the rewritten file still round-trips section-for-section: OK")

# --- project-wide: .cuip + every page/widget in one call, with a valid font ------------
# The starting font is whatever the live source project currently holds -- not assumed
# to be "Roboto". (This is not academic: an earlier manual run of this session's own
# unvalidated fonts.py against the real GenTestProject2 left its DefaultFontFamily as
# the invalid "Montserrat", which a hardcoded "Roboto" assumption here would have missed.)
before_cuip = cuip.read_text(encoding="utf-8")
starting_font = re.search(r'DefaultFontFamily = "([^"]*)"', before_cuip).group(1)
project_target_font = next(f for f in fonts_list if f != starting_font)

results = fonts.set_project_font(cuip, project_target_font, sdk)
assert results[cuip.name] == 1
assert sum(v for k, v in results.items() if k != cuip.name) > 0, \
    "at least one page/widget in the project should have mentioned a font"

after_cuip = cuip.read_text(encoding="utf-8")
assert f'DefaultFontFamily = "{project_target_font}"' in after_cuip
print(f"set_project_font touched {len(results)} files: {results}")

# Every page/widget in the project now mentions the new font wherever it mentioned any.
for name, count in results.items():
    if name == cuip.name or count == 0:
        continue
    text = (OUT / name).read_text(encoding="utf-8")
    assert starting_font not in text, f"{name} still mentions {starting_font} after the swap"
    assert project_target_font in text, f"{name} does not mention the new font"
print("every touched file carries the new font and none carries the old one: OK")

# Re-applying the SAME font project-wide is a no-op on the .cuip (count 0) and leaves
# every page byte-identical (already-in-place text substituted with itself).
before_snapshot = {p.name: p.read_text(encoding="utf-8")
                   for p in OUT.glob("*.cuig")}
results2 = fonts.set_project_font(cuip, project_target_font, sdk)
assert results2[cuip.name] == 0, "re-applying the same project font must not touch the .cuip"
for p in OUT.glob("*.cuig"):
    assert p.read_text(encoding="utf-8") == before_snapshot[p.name], f"{p.name} changed on a no-op swap"
print("re-applying the same project-wide font is a true no-op: OK")

# --- files with no font mention are left untouched -------------------------------------
untouched = [name for name, count in results.items() if name != cuip.name and count == 0]
if untouched:
    print(f"files with no font mention, left untouched: {untouched}")

print("\nGlobal font swap: all assertions passed.")
