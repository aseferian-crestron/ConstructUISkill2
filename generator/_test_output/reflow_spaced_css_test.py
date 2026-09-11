"""Reflow: parse CSS whether Construct wrote it compact or spaced.

Real project files come in both formats. Most are compact --
`@media (max-width: 99999px){#ixo7{left:105px;top:92px;...}}` -- but
`C:\\Solutions\\ClaudeSamples\\Components\\Component-Widgets-Media Player.cuig` is spaced:
`@media (max-width: 99999px) { #it8l { left: 124px; ... } }`.

Both assumptions that broke on the spaced form were silent: `find_media_block_span`
matched the literal `@media <query>{`, and `_FLAT_RULE_RE` required `{` immediately after
the id. A page in the spaced format therefore parsed as ZERO elements, so reflow_file
would rewrite nothing and report no warning -- the component would simply be missing at
the new resolution, which is the exact failure reflow exists to prevent.

The strictness was there for a reason and must survive: a descendant selector like
`#id .ch5-button :not(i):not(svg){...}` carries no position data and must still be
ignored. Only WHITESPACE between the id and its brace is now allowed, never other
selector text.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import layout  # noqa: E402

COMPACT = "#ixo7{display:block;left:105px;top:92px;position:absolute;z-index:1;width:118px;height:118px;}"
SPACED = "#it8l { width: 800px; height: 600px; display: block; left: 124px; top: 88px; position: absolute; z-index: 2 }"

# --- both formats parse to the same shape ---------------------------------------------
compact = layout.parse_position_rules(COMPACT)
assert compact == {"ixo7": {"left": 105, "top": 92, "width": 118, "height": 118,
                            "z_index": 1, "extra_vars": {}}}, compact

spaced = layout.parse_position_rules(SPACED)
assert spaced == {"it8l": {"left": 124, "top": 88, "width": 800, "height": 600,
                           "z_index": 2, "extra_vars": {}}}, spaced
print("compact and spaced flat rules both parse: OK")

# --- descendant selectors are still ignored, in BOTH formats --------------------------
for descendant in (
    '#ixo7 span:not(.dpad-btn-icon){font-family:"Roboto";}',
    '#it8l :not(i):not(svg) { font-family: "Roboto" }',
    "#i2jj .ch5-button .label { left: 5px; top: 5px }",   # has position decls, still not a flat rule
):
    assert layout.parse_position_rules(descendant) == {}, descendant
print("descendant selectors still ignored (they carry no element position): OK")

# A flat rule and a descendant rule for the same id, together: only the flat one counts.
mixed = '#it8l :not(i):not(svg) { font-family: "Roboto" } ' + SPACED
assert set(layout.parse_position_rules(mixed)) == {"it8l"}
assert layout.parse_position_rules(mixed)["it8l"]["left"] == 124
print("a flat rule is still found alongside a descendant rule for the same id: OK")

# --- CSS custom properties survive in both formats ------------------------------------
with_vars = "#ixo7 { left: 1px; top: 2px; --ch5-dpad--regular-size: 118px }"
assert layout.parse_position_rules(with_vars)["ixo7"]["extra_vars"] == {
    "--ch5-dpad--regular-size": "118px"}, layout.parse_position_rules(with_vars)
print("custom properties parsed from the spaced form too: OK")

# --- @media block location tolerates the space before the brace -----------------------
query = "(max-width: 99999px)"
for css in (
    "@media (max-width: 99999px){" + COMPACT + "}",
    "@media (max-width: 99999px) { " + SPACED + " }",
):
    assert layout.find_media_block(css, query) is not None, css[:40]
    found = layout.parse_all_position_rules(css, query)
    assert len(found) == 1, (css[:40], found)
print("@media blocks located whether or not a space precedes the brace: OK")

# --- against the real spaced file -----------------------------------------------------
REF = Path(r"C:\Solutions\ClaudeSamples\Components\Component-Widgets-Media Player.cuig")
if REF.is_file():
    raw = REF.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    css = ""
    for i, m in enumerate(headers):
        if m.group(1) == "Css":
            css = raw[m.end():headers[i + 1].start() if i + 1 < len(headers) else len(raw)]
    real = layout.parse_all_position_rules(css, query)
    assert real, "the real spaced file must yield elements -- it previously yielded none"
    assert "ihgyqfkbhk" in real, sorted(real)
    assert real["ihgyqfkbhk"]["width"] == 800 and real["ihgyqfkbhk"]["height"] == 600, real["ihgyqfkbhk"]
    print(f"real spaced reference file parses: {len(real)} elements: OK")
else:
    raise AssertionError(f"reference file missing: {REF}")

print("\nSpaced CSS parsing: all assertions passed.")
