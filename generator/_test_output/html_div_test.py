"""html_div.py -- Construct's real "pure HTML5" grouping/border component
(design-system §7's missing mechanism). Not a ch5-* schema type, so this is
grounded directly against two real reference instances rather than
component-context.json. Verified: attribute-for-attribute against the real
reference, a written .cuiw round-trips, restyling an existing div in place only
touches the properties asked for, and the result stays parseable by the same
reflow machinery every other component already relies on."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
from html_div import build_html_div, style_html_div  # noqa: E402
from page import build_page_attributes, write_cuig  # noqa: E402

REFERENCE = Path(r"C:\Solutions\ClaudeSamples\Components\Component - DIV.cuig")
reference_text = REFERENCE.read_text(encoding="utf-8")
reference_html = re.search(r"<div [^>]*></div>", reference_text).group()
# devicesVisited's own value carries literal embedded quotes (`[&quot;...&quot;]`
# in the reference, unescaped in this generator's own established convention --
# see Footer.cuiw), so a generic attribute tokenizer can't cleanly split past it.
# Compare only the fixed prefix up to that value, which covers every other
# attribute's name, order, and bare-vs-valued shape.
reference_prefix = reference_html.split('devicesVisited="')[0]

# --- attribute-for-attribute against the real reference ----------------------------------
html, css, element = build_html_div(
    component_name="Html-div", element_id="iupx", x=129, y=75, width=200, height=200,
    z_index=1, background_color="#B6C6D5", border_color="#1B4B7C", border_width=5,
    border_radius=15,
)

assert html.startswith("<div "), html
assert html.endswith("</div>"), html
assert 'labelmode="advanced"' in html
assert " ccid_lteHTMLOnly " in html or html.count("ccid_lteHTMLOnly") == 1, html
# the real Html attribute is BARE -- no "=" immediately after it (a real, confirmed
# Html/TOML asymmetry, not an oversight)
assert "ccid_lteHTMLOnly=" not in html, html
assert 'componentName="Html-div"' in html
assert 'id="iupx"' in html
assert 'ccid_ComponentType="Html-div"' in html
print("build_html_div: Html shape matches the real reference (bare ccid_lteHTMLOnly, tag is <div>): OK")

our_prefix = html.split('devicesVisited="')[0]
assert our_prefix == reference_prefix, (our_prefix, reference_prefix)
assert "devicesVisited=" in html
print("build_html_div: attribute name/order/bare-vs-valued shape matches the real reference exactly: OK")

assert element.type == "html-div", element
assert element.editable is None, element  # the real reference carries no Editable key at all
attr_dict = dict(element.attributes)
assert attr_dict["ccid_lteHTMLOnly"] == "true"
assert attr_dict["ccid_ComponentType"] == "Html-div"
assert attr_dict["labelmode"] == "advanced"
print("build_html_div: TOML [[Elements]] shape matches the real reference: OK")

# every literal style property from the real reference's catch-all rule is present
for prop_value in (
    "background-color:#B6C6D5", "border-style:solid", "border-width:5px",
    "border-color:#1B4B7C", "border-radius:15px 15px 15px 15px",
):
    prop, _, value = prop_value.partition(":")
    assert re.search(rf"{prop}:\s*{re.escape(value)}\s*;", css), (prop_value, css)
print("build_html_div: catch-all CSS carries every real reference style property: OK")

# confirmed duplicated into the PRIMARY resolution block too (same rule as every
# other themed property in this project)
device_block = css.split("@media", 2)[2]
assert "background-color: #B6C6D5" in device_block, device_block
assert "border-radius: 15px 15px 15px 15px" in device_block, device_block
print("build_html_div: style properties duplicated into the primary-resolution block too: OK")

# --- a real .cuig page, written and round-tripped -----------------------------------------
OUT = Path(__file__).resolve().parent / "HtmlDiv"
OUT.mkdir(parents=True, exist_ok=True)
page_attrs = build_page_attributes(name="DivTest")
page_path = OUT / "DivTest.cuig"
write_cuig(page_path, page_attrs, html=html, css=css, elements=[element])
assert compare.round_trip_check(page_path), "html-div page failed round-trip"
print("build_html_div: written .cuig round-trips byte-identical: OK")

# the written CSS stays parseable by the same reflow machinery every other
# component already relies on -- a div's literal style declarations must coexist
# peacefully with position/size parsing, the same way a ch5-button's --ch5-*
# custom properties already do
positions = layout.parse_all_position_rules(css, "(max-width: 99999px)")
rect = positions["iupx"]
assert rect["width"] == 200 and rect["height"] == 200
assert rect["left"] == 129 and rect["top"] == 75
print("build_html_div: position/size still parses correctly alongside the extra style declarations: OK")

# --- style_html_div: restyle an EXISTING div, touching only what's given -----------------
html2, css2, element2 = build_html_div(
    component_name="Plain", element_id="iplain", x=0, y=0, width=100, height=100, z_index=1,
)
assert "background-color" not in css2, css2  # no fill/border given -> none written
new_css, blocks_updated = style_html_div(css2, "iplain", background_color="#ff0000")
assert blocks_updated >= 1
assert "background-color:#ff0000" in new_css.replace(" ", "").replace(";", ";")
# white-space, set by build_html_div, is untouched by a restyle that never mentioned it
assert "white-space:normal" in new_css.replace(" ", "")
print("style_html_div: restyling an existing plain div adds only the requested property: OK")

new_css2, _ = style_html_div(new_css, "iplain", border_color="#00ff00", border_width=3)
assert "background-color:#ff0000" in new_css2.replace(" ", "")  # earlier value untouched
assert "border-color:#00ff00" in new_css2.replace(" ", "")
assert "border-width:3px" in new_css2.replace(" ", "")
print("style_html_div: a second restyle call adds new properties without disturbing earlier ones: OK")

print("Html-div: all assertions passed.")
