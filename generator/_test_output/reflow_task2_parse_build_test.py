"""Task 2: find_media_block(_span)/parse_position_rules/build_reflow_block."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from layout import (  # noqa: E402
    find_media_block, find_media_block_span, parse_position_rules, build_reflow_block,
    orientation_media_query,
)

CSS = (
    '@media (max-width: 99999px){'
    '#i1{display: block; left: 10px; top: 20px; position: absolute; z-index: 1; width: 100px; height: 50px; --ch5-button--regular-width: 100px; --ch5-button--regular-height: 50px;}'
    '#i1 .ch5-button :not(i):not(svg) {font-family: "Roboto";}'
    '#i2{display: block; left: 200px; top: 20px; position: absolute; z-index: 2; width: 80px; height: 40px;}'
    '}'
    '@media (orientation: landscape) and (max-width: 1281px) and (max-height: 801px), (orientation: landscape) and (max-width: 1279px){'
    '#i1{display: block; left: 10px; top: 20px; position: absolute; width: 100px; height: 50px;}'
    '}'
)

# find_media_block(_span) locates by exact query string.
catch_all_query = "(max-width: 99999px)"
span = find_media_block_span(CSS, catch_all_query)
assert span is not None and CSS[span[0]:span[1]].startswith("@media (max-width: 99999px){")
block = find_media_block(CSS, catch_all_query)
assert block is not None and block.startswith("#i1{") and block.endswith("}")
missing = find_media_block(CSS, "(orientation: portrait) and (max-height: 999px)")
assert missing is None

# parse_position_rules: only the two flat #id{} rules, NOT the theme-selector rule.
elements = parse_position_rules(block)
assert set(elements) == {"i1", "i2"}, f"theme-selector rule leaked into result: {elements}"
assert elements["i1"] == {
    "left": 10, "top": 20, "width": 100, "height": 50, "z_index": 1,
    "extra_vars": {"--ch5-button--regular-width": "100px", "--ch5-button--regular-height": "50px"},
}
assert elements["i2"] == {"left": 200, "top": 20, "width": 80, "height": 40, "z_index": 2, "extra_vars": {}}

# device-specific block found by its landscape query has no extra_vars/z-index issue either.
device_block = find_media_block(CSS, orientation_media_query("landscape", 1280, 800))
assert device_block == "#i1{display: block; left: 10px; top: 20px; position: absolute; width: 100px; height: 50px;}"

# build_reflow_block: matches the shape of a real device block -- no z-index, extra_vars carried.
built = build_reflow_block(
    {"i1": {"left": 5, "top": 6, "width": 100, "height": 50, "z_index": 1, "extra_vars": {"--x": "100px"}}},
    "portrait", 1024, 1322,
)
assert built == (
    f"@media {orientation_media_query('portrait', 1024, 1322)}"
    "{#i1{display: block; left: 5px; top: 6px; position: absolute; width: 100px; height: 50px; --x: 100px;}}"
)

print("TASK 2: CSS block parsing/building. PASSED")
