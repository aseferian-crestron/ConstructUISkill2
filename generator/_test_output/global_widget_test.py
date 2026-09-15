"""ConstructUISkill.md hard requirement (added by user): any widget added to every page
(a header/footer/common widget) must have its "Global Contract" property set true.

Confirmed against C:\\Git\\CCIDE's SubpageTemplate.json (the widgetContainer root
element's `globalControlContract` DefaultAttribute) and GlobalSubpageConverter.cs, which
writes the SAME value ("on" if true, unconditionally present) into both the Html section
and the TOML [[Elements]].Attributes -- see page.py::default_widget_html_css's
`is_global` docstring for the full citation.
"""
import re
import sys
import tomllib
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from page import build_widget_attributes, default_widget_html_css, write_cuig  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "GlobalWidget"
OUT.mkdir(parents=True, exist_ok=True)


def parse_attrs(path: Path) -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    sections = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        sections[m.group(1)] = raw[start:end]
    return tomllib.loads(sections["PageAttributes"])


# --- a common (all-pages) widget: globalControlContract="on" in Html AND TOML ----------
w_attrs = build_widget_attributes(name="FooterWidget", widget_id=str(uuid4()))
html, css, element = default_widget_html_css("ifooter01", width=1920, height=120, is_global=True)
assert 'globalControlContract="on"' in html, html
path = OUT / "FooterWidget.cuiw"
write_cuig(path, w_attrs, html=html, css=css, elements=[element])
assert compare.round_trip_check(path), "global widget round-trip failed"

parsed = parse_attrs(path)
el_attrs = parsed["Elements"][0]["Attributes"]
assert el_attrs["globalControlContract"] == "on", el_attrs
print("common widget: globalControlContract=\"on\" written to Html and TOML: OK")

# --- an ordinary (single-page) widget: no globalControlContract anywhere ---------------
html2, css2, element2 = default_widget_html_css("iordinary01", width=500, height=500)
assert "globalControlContract" not in html2, html2
w_attrs2 = build_widget_attributes(name="OrdinaryWidget", widget_id=str(uuid4()))
path2 = OUT / "OrdinaryWidget.cuiw"
write_cuig(path2, w_attrs2, html=html2, css=css2, elements=[element2])
assert compare.round_trip_check(path2), "ordinary widget round-trip failed"

parsed2 = parse_attrs(path2)
el_attrs2 = parsed2["Elements"][0]["Attributes"]
assert "globalControlContract" not in el_attrs2, el_attrs2
print("ordinary (non-global) widget: globalControlContract absent from Html and TOML: OK")

print("Global widget contract: all assertions passed.")
