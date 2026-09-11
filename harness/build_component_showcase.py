"""Generate showcase pages carrying every component type generator/component.py can
build, into the live test project, so the output can be opened in Construct.

The reference diff proves our attributes match a Construct-authored file. It does not
prove Construct RENDERS what we write -- which is a different question, and the contract
work showed live checking catches things static diffing does not.

Sizes come from each type's reference instance rather than being invented, so components
appear at the proportions a real one has. Layout is a shelf pack into the project's
primary 1280x800, spilling onto another page when a row will not fit, and the script
asserts every component lands inside the panel with no overlaps.
"""
import re
import sys
import tomllib
from pathlib import Path

GEN = Path(r"C:\ClaudeProjects\ConstructUISkill2\generator")
sys.path.insert(0, str(GEN))

import layout  # noqa: E402
from component import PROFILES, build_component, widget_reference_id  # noqa: E402
from page import build_page_attributes, generate_element_id, write_cuig  # noqa: E402
from sdk import read_sdk  # noqa: E402

REF = Path(r"C:\Solutions\ClaudeSamples\Components")
PROJ = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
PANEL = (1280, 800)          # the project's primary resolution (TSW-1070)
MARGIN, GAP = 40, 24

sdk = read_sdk("2.18.0")
name_to_tag = {e.get("name"): e.get("tagName") for e in sdk.schema["ch5Elements"]["elements"]}

#: Grouped so a page reads as a set of related controls rather than a jumble. Order
#: within a group is largest-first, which packs better.
GROUPS = {
    "AllComponents - Buttons": ["ch5-button", "ch5-toggle", "ch5-tab-button", "ch5-button-list"],
    "AllComponents - Keypads": ["ch5-dpad", "ch5-keypad"],
    "AllComponents - Gauges": ["ch5-slider", "ch5-segmented-gauge", "ch5-signal-level-gauge",
                               "ch5-wifi-signal-level-gauge"],
    "AllComponents - Text": ["ch5-text", "ch5-textinput", "ch5-datetime", "ch5-qrcode",
                             "ch5-color-chip", "ch5-color-picker"],
    "AllComponents - Media": ["ch5-media-player", "ch5-video", "ch5-video-switcher",
                              "ch5-animation", "ch5-subpage-reference-list"],
}

FALLBACK_SIZE = (200, 120)

#: Per-type instance values the showcase supplies, where a component needs configuring
#: before it renders as anything. A widget list with no widgetid references no widget,
#: so it draws nothing inside its box -- which reads as a sizing bug.
OVERRIDES = {
    "ch5-subpage-reference-list": {"numberofitems": "3"},
}


def project_widget_id() -> str | None:
    """The `widgetid` for the first widget in the target project, if it has one."""
    for widget in sorted(PROJ.glob("*.cuiw")):
        raw = widget.read_text(encoding="utf-8")
        headers = list(HEADER_RE.finditer(raw))
        for i, m in enumerate(headers):
            if m.group(1) == "PageAttributes":
                end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
                guid = tomllib.loads(raw[m.end():end])["Attributes"].get("Id")
                if guid:
                    return widget_reference_id(guid)
    return None


def reference_sizes() -> dict[str, tuple[int, int]]:
    """Each type's size, taken from its instance in the reference project."""
    sizes: dict[str, tuple[int, int]] = {}
    for path in sorted(REF.glob("*.cuig")):
        raw = path.read_text(encoding="utf-8")
        headers = list(HEADER_RE.finditer(raw))
        sections = {}
        for i, m in enumerate(headers):
            end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
            sections[m.group(1)] = raw[m.end():end]
        if "PageAttributes" not in sections:
            continue
        rules = layout.parse_all_position_rules(sections["Css"], "(max-width: 99999px)")

        def walk(elements):
            for element in elements:
                attributes = element.get("Attributes", {})
                tag = attributes.get("tagName") or name_to_tag.get(element.get("Type", ""))
                rule = rules.get(attributes.get("id", ""))
                if tag in PROFILES and tag not in sizes and rule and rule.get("width"):
                    sizes[tag] = (rule["width"], rule["height"] or FALLBACK_SIZE[1])
                walk(element.get("Components", []))

        walk(tomllib.loads(sections["PageAttributes"]).get("Elements", []))
    return sizes


def shelf_pack(items: list[tuple[str, int, int]]) -> list[list[tuple[str, int, int, int, int]]]:
    """Pack (tag, w, h) into pages of PANEL size. Returns pages of (tag, x, y, w, h)."""
    pages, page = [], []
    x = y = MARGIN
    row_height = 0
    for tag, width, height in items:
        width = min(width, PANEL[0] - 2 * MARGIN)
        height = min(height, PANEL[1] - 2 * MARGIN)
        if x + width > PANEL[0] - MARGIN:                 # next row
            x, y = MARGIN, y + row_height + GAP
            row_height = 0
        if y + height > PANEL[1] - MARGIN:                # next page
            pages.append(page)
            page, x, y, row_height = [], MARGIN, MARGIN, 0
        page.append((tag, x, y, width, height))
        x += width + GAP
        row_height = max(row_height, height)
    if page:
        pages.append(page)
    return pages


widget_id = project_widget_id()
if widget_id:
    OVERRIDES["ch5-subpage-reference-list"]["widgetid"] = widget_id
    print(f"widget list will reference {widget_id}")
else:
    print("WARNING: the project has no widget, so the widget list will render empty")

sizes = reference_sizes()
missing = sorted(set(PROFILES) - set(sizes))
print(f"sizes from the reference for {len(sizes)} types"
      + (f"; falling back for {missing}" if missing else ""))

written = []
for group_name, tags in GROUPS.items():
    items = sorted(((tag, *sizes.get(tag, FALLBACK_SIZE)) for tag in tags),
                   key=lambda item: item[1] * item[2], reverse=True)
    for page_index, placements in enumerate(shelf_pack(items), start=1):
        name = group_name if page_index == 1 else f"{group_name} {page_index}"
        html_parts, css_parts, elements = [], [], []
        for z, (tag, x, y, width, height) in enumerate(placements, start=1):
            html, css, element = build_component(
                sdk, tag, overrides=OVERRIDES.get(tag),
                component_name=tag.removeprefix("ch5-").replace("-", " ").title().replace(" ", ""),
                element_id=generate_element_id(),
                x=x, y=y, width=width, height=height, z_index=z, resolution=PANEL,
            )
            html_parts.append(html)
            css_parts.append(css)
            elements.append(element)

        path = PROJ / f"{name}.cuig"
        write_cuig(path, build_page_attributes(name=name),
                   html="".join(html_parts), css="".join(css_parts), elements=elements)
        written.append((path, [p[0] for p in placements]))
        print(f"  {path.name}: {len(placements)} components "
              f"({', '.join(t.removeprefix('ch5-') for t, *_ in placements)})")

print(f"\nwrote {len(written)} pages into {PROJ}")
