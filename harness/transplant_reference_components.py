"""Build GenTestProject2/ComplexContracts.cuig: the five COMPLEX component types that
have contract signals, so their contract generation can be checked in Construct.

We have no generator builders for these types yet (Phase 4 only built ch5-button), so
each component's element/html/css is copied verbatim out of the user's reference project
(read-only). What this verifies is the part we DO own: the signals our contracts.py
writes onto them, and ContractIsStale driving regeneration.

Each component gets its per-type defaults from DEFAULT_SIGNALS plus one deliberately
NON-default extra signal. If a complex component's own contract strategy ignores what
the file says, the extra will be missing from the generated contract -- which is the
failure mode this whole exercise is looking for.
"""
import re
import sys
from pathlib import Path

GEN = Path(r"C:\ClaudeProjects\ConstructUISkill2\generator")
sys.path.insert(0, str(GEN))

import tomllib  # noqa: E402
from contracts import (  # noqa: E402
    CONTRACT_ENABLED, DEFAULT_SIGNALS, enable_contract_signals, mark_contract_stale,
    resolve_signals, signal_map,
)
from elements import Element  # noqa: E402
from page import build_page_attributes, write_cuig  # noqa: E402
from sdk import read_sdk  # noqa: E402

REF = Path(r"C:\Solutions\ClaudeSamples\Components")
PROJ = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
CATCH_ALL = "@media (max-width: 99999px){"

# tag -> reference file. EXTRA is the deliberately non-default signal: "Enable"
# (pd-receivestateenable) exists on all five and is a default on none of them, so its
# presence in the generated contract can only have come from what we wrote to the file.
# (pd-receivestateshow would not do -- its contract name varies by type: "Show" on the
# dpad/keypad, "List Visible" on the button list, "Visible" on the tab button.)
# Named by raw attribute rather than friendly name on purpose: the SAME attribute is
# called "Enable" on the dpad/keypad/tab button, "List Enabled" on the button list.
EXTRA = "pd-receivestateenable"

# Explicit placement, hand-fitted to the project's primary 1280x800 (TSW-1070). Auto-flow
# put the 800x600 media player at y=368, hanging 168px off the bottom of the panel.
POSITIONS = {
    "ch5-media-player": (40, 40),    # 800x600
    "ch5-dpad": (880, 40),           # 150x150
    "ch5-keypad": (880, 210),        # 310x200
    "ch5-button-list": (40, 670),    # 510x68
    "ch5-tab-button": (570, 670),    # 510x68
}
TARGETS = [
    ("ch5-dpad", "Component - Keypad - DPad.cuig", EXTRA),
    ("ch5-keypad", "Component - Keypad - Keypad.cuig", EXTRA),
    ("ch5-button-list", "Component - Lists - Button Lis.cuig", EXTRA),
    ("ch5-tab-button", "Component - TabButtons.cuig", EXTRA),
    ("ch5-media-player", "Component-Widgets-Media Player.cuig", EXTRA),
]

sdk = read_sdk("2.18.0")


def sections(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8")
    headers = list(HEADER_RE.finditer(raw))
    out = {}
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        out[m.group(1)] = raw[m.end():end]
    return out


def to_element(node: dict) -> Element:
    """A parsed [[Elements]] dict back into the Element dataclass, field for field."""
    return Element(
        type=node.get("Type"),
        name=node.get("Name"),
        status=node.get("Status"),
        content=node.get("Content"),
        removable=node.get("Removable"),
        draggable=node.get("Draggable"),
        highlightable=node.get("Highlightable"),
        copyable=node.get("Copyable"),
        editable=node.get("Editable"),
        selectable=node.get("Selectable"),
        hoverable=node.get("Hoverable"),
        inner_text=node.get("_InnerText"),
        classes=node.get("Classes"),
        components=[to_element(c) for c in node.get("Components", [])],
        attributes=list(node.get("Attributes", {}).items()),
        style=list(node.get("Style", {}).items()),
    )


def subtree_ids(node: dict) -> set[str]:
    ids = set()
    attrs = node.get("Attributes", {})
    if "id" in attrs:
        ids.add(attrs["id"])
    for child in node.get("Components", []):
        ids |= subtree_ids(child)
    return ids


def find_component(nodes: list[dict], tag: str) -> dict | None:
    """The instance of `tag` that the user actually configured -- i.e. the one carrying
    contract signals. Several reference pages hold more than one of a type (three dpads,
    for instance), and only one is the configured exemplar."""
    fallback = None
    for node in nodes:
        attrs = node.get("Attributes", {})
        if attrs.get("tagName") == tag or node.get("Type", "").lower().replace(" ", "-") == tag:
            if any(v == CONTRACT_ENABLED for v in attrs.values()):
                return node
            fallback = fallback or node
        found = find_component(node.get("Components", []), tag)
        if found is not None:
            return found
    return fallback


def html_for(html: str, element_id: str) -> str:
    """The balanced tag whose id attribute is `element_id`, children included."""
    start = None
    for m in re.finditer(r"<([a-zA-Z0-9-]+)\b[^>]*?\bid=\"" + re.escape(element_id) + r"\"", html):
        start, tag = m.start(), m.group(1)
        break
    if start is None:
        raise LookupError(f"no html tag with id={element_id!r}")

    depth = 0
    pos = start
    # (?![-\w]) so <ch5-dpad-button> is not counted as a nested <ch5-dpad>: \b matches
    # there, since "-" is a non-word character, and the depth would never unwind.
    open_re = re.compile(r"<" + re.escape(tag) + r"(?![-\w])")
    close_re = re.compile(r"</" + re.escape(tag) + r">")
    while pos < len(html):
        nxt_open = open_re.search(html, pos)
        nxt_close = close_re.search(html, pos)
        if nxt_close is None:
            raise LookupError(f"unbalanced <{tag}> for id={element_id!r}")
        if nxt_open is not None and nxt_open.start() < nxt_close.start():
            depth += 1
            pos = nxt_open.end()
            continue
        depth -= 1
        pos = nxt_close.end()
        if depth == 0:
            return html[start:pos]
    raise LookupError(f"unbalanced <{tag}> for id={element_id!r}")


def catch_all_rules(css: str) -> list[tuple[str, str]]:
    """[(selector, declarations)] from the catch-all @media block.

    Real files are not uniformly formatted: most are compact (`@media (max-width:
    99999px){#id{left:105px;...}`) but Component-Widgets-Media Player.cuig is spaced
    (`@media (max-width: 99999px) { #it8l { left: 124px; ... } }`), so every pattern here
    has to tolerate whitespace.
    """
    m = re.search(r"@media\s*\(\s*max-width:\s*99999px\s*\)\s*\{", css)
    if m is None:
        raise LookupError("no catch-all @media block")
    start = m.end()
    depth = 1
    pos = start
    while depth:
        if css[pos] == "{":
            depth += 1
        elif css[pos] == "}":
            depth -= 1
        pos += 1
    body = css[start:pos - 1]
    return re.findall(r"([^{}]+)\{([^{}]*)\}", body)


def set_html_attribute(tag_html: str, name: str, value: str) -> str:
    """Set an attribute on the OPENING tag only, leaving children untouched. The element
    TOML and the html view must agree -- a signal present in one but not the other is a
    page whose contract does not match what it renders."""
    end = tag_html.index(">")
    head, rest = tag_html[:end], tag_html[end:]
    pattern = re.compile(r"(\s" + re.escape(name) + r'=")[^"]*(")')
    if pattern.search(head):
        return pattern.sub(lambda m: m.group(1) + value + m.group(2), head, count=1) + rest
    return head + f' {name}="{value}"' + rest


def reposition(decls: str, left: int, top: int) -> str:
    decls = re.sub(r"left:\s*-?\d+px", f"left:{left}px", decls)
    decls = re.sub(r"top:\s*-?\d+px", f"top:{top}px", decls)
    return decls


def px(decls: str, prop: str, default: int) -> int:
    m = re.search(prop + r":\s*(\d+)px", decls)
    return int(m.group(1)) if m else default


# --- assemble -------------------------------------------------------------------------
page_elements: list[Element] = []
page_html_parts: list[str] = []
page_rules: list[str] = []

x, y, row_height = 40, 40, 0
for tag, filename, extra in TARGETS:
    src = sections(REF / filename)
    nodes = tomllib.loads(src["PageAttributes"]).get("Elements", [])
    node = find_component(nodes, tag)
    if node is None:
        raise LookupError(f"{tag} not found in {filename}")

    element = to_element(node)
    element_id = dict(element.attributes)["id"]
    ids = subtree_ids(node)

    # signals: the per-type defaults, plus one non-default extra
    known = signal_map(sdk, tag)
    if extra not in known:
        raise LookupError(f"{tag} has no {extra!r} signal to use as the extra")
    wanted = tuple(DEFAULT_SIGNALS.get(tag, ())) + (extra,)
    enable_contract_signals(element.attributes, sdk, tag, wanted)
    enabled = [k for k, v in element.attributes if v == CONTRACT_ENABLED]

    # css for the whole subtree, from the catch-all block only
    rules = [(sel, decls) for sel, decls in catch_all_rules(src["Css"])
             if any(f"#{i}" in sel for i in ids)]
    own = next((d for sel, d in rules if sel.strip() == f"#{element_id}"), "")
    width = px(own, "width", 200)
    height = px(own, "height", 200)

    x, y = POSITIONS[tag]
    assert x + width <= 1280 and y + height <= 800, (
        f"{tag} at ({x},{y}) size {width}x{height} does not fit the 1280x800 panel")
    for sel, decls in rules:
        if sel.strip() == f"#{element_id}":
            decls = reposition(decls, x, y)
        page_rules.append(f"{sel}{{{decls}}}")
    print(f"{tag:<18} id={element_id:<16} {width}x{height} at ({x},{y})  signals={enabled}")
    x += width + 30
    row_height = max(row_height, height)

    # html, with the same repositioning applied to any inline style (there is none today,
    # but a stale inline left/top would silently override the stylesheet)
    tag_html = html_for(src["Html"], element_id)
    for attribute in enabled:
        tag_html = set_html_attribute(tag_html, attribute, CONTRACT_ENABLED)
        assert f'{attribute}="{CONTRACT_ENABLED}"' in tag_html, (tag, attribute)
    page_html_parts.append(tag_html)
    page_elements.append(element)

css = CATCH_ALL + "".join(page_rules) + "}"
out = PROJ / "ComplexContracts.cuig"
write_cuig(out, build_page_attributes(name="ComplexContracts"),
           html="".join(page_html_parts), css=css, elements=page_elements)
print(f"\nwrote {out}")

mark_contract_stale(PROJ / "GenTestProject2.cuip")
print("project marked stale")
