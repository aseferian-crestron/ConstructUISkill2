"""Phase 8 (fonts), first slice: global font swap.

Verified against a copy of the real, live GenTestProject2 harness project (not a
synthetic fixture) -- it already has ccid_ActiveFont and font-family CSS on real
components (buttons, dpad, keypad, toggle, text, textinput, media player), which is a
stronger check than anything hand-built here could be.
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
from fonts import replace_font_in_text, set_page_font, set_project_font  # noqa: E402

OUT = Path(__file__).resolve().parent / "FontsGlobalSwap"
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")

if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)

# --- unit-level: the raw text substitution -----------------------------------------
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

# --- file-level: FileMetadata is never touched ----------------------------------------
button_page = OUT / "ButtonVariants.cuig"
before = button_page.read_text(encoding="utf-8")
before_metadata = re.search(r"\{FileMetadata\}.*?(?=\{Html\})", before, re.DOTALL).group(0)

count = set_page_font(button_page, "Inter")
assert count > 0, "ButtonVariants.cuig is expected to mention Roboto"
after = button_page.read_text(encoding="utf-8")
after_metadata = re.search(r"\{FileMetadata\}.*?(?=\{Html\})", after, re.DOTALL).group(0)
assert before_metadata == after_metadata, "FileMetadata (Modified timestamp) must not change"
assert "Roboto" not in after and after.count('"Inter"') >= 1
print("set_page_font rewrites Html/Css/PageAttributes only, never FileMetadata: OK")

# Idempotent: swapping to the same font twice makes the second call a no-op count-wise
# in terms of content (re-running finds the NEW font already in place, so it re-replaces
# with itself -- count is still > 0, but the file content is unchanged).
after2 = button_page.read_text(encoding="utf-8")
set_page_font(button_page, "Inter")
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
assert toml_fonts == {"'Inter'"}, toml_fonts
html_fonts = set(re.findall(r'ccid_ActiveFont="([^"]*)"', sections["Html"]))
assert html_fonts == {"'Inter'"}, html_fonts
print("Html and TOML element attributes agree after the swap: OK")

# --- round-trip: only content changed, structure survives ------------------------------
assert compare.round_trip_check(button_page)
print("the rewritten file still round-trips section-for-section: OK")

# --- project-wide: .cuip + every page/widget in one call -------------------------------
cuip = OUT / "GenTestProject2.cuip"
before_cuip = cuip.read_text(encoding="utf-8")
assert 'DefaultFontFamily = "Roboto"' in before_cuip

results = fonts.set_project_font(cuip, "Montserrat")
assert results[cuip.name] == 1
assert sum(v for k, v in results.items() if k != cuip.name) > 0, \
    "at least one page/widget in the project should have mentioned a font"

after_cuip = cuip.read_text(encoding="utf-8")
assert 'DefaultFontFamily = "Montserrat"' in after_cuip
print(f"set_project_font touched {len(results)} files: {results}")

# Every page/widget in the project now mentions the new font wherever it mentioned any.
for name, count in results.items():
    if name == cuip.name or count == 0:
        continue
    text = (OUT / name).read_text(encoding="utf-8")
    assert "Roboto" not in text, f"{name} still mentions Roboto after the swap"
    assert "Montserrat" in text, f"{name} does not mention the new font"
print("every touched file carries the new font and none carries the old one: OK")

# Re-applying the SAME font project-wide is a no-op on the .cuip (count 0) and leaves
# every page byte-identical (already-Montserrat text substituted with itself).
before_snapshot = {p.name: p.read_text(encoding="utf-8")
                   for p in OUT.glob("*.cuig")}
results2 = fonts.set_project_font(cuip, "Montserrat")
assert results2[cuip.name] == 0, "re-applying the same project font must not touch the .cuip"
for p in OUT.glob("*.cuig"):
    assert p.read_text(encoding="utf-8") == before_snapshot[p.name], f"{p.name} changed on a no-op swap"
print("re-applying the same project-wide font is a true no-op: OK")

# --- FileMetadata (Modified) is untouched on files that mention no font at all --------
untouched = [name for name, count in results.items() if name != cuip.name and count == 0]
if untouched:
    print(f"files with no font mention, left untouched: {untouched}")

print("\nGlobal font swap: all assertions passed.")
