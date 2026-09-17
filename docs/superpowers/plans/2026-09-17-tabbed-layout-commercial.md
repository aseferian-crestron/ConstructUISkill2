# Tabbed Layout (Commercial) Phase 1 Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Tabbed layout pattern's navigational shell (commercial) —
Splash → Main Panel transition, a 2-row header whose bottom row is a tab strip
driving per-mode content-swap widgets, a 3-zone footer with a caller-configurable
subsystem list, and one fully real modal (Camera) wired to a new subsystem-control
composite — with every other subsystem's modal present but empty.

**Architecture:** Three new modules, matching this project's primitive →
composite → layout-pattern tiers. `generator/modal.py` (primitive tier): a
generic modal, built as a WIDGET from an `html-div` backdrop + centered `html-div`
card + `ch5-text` title + optional close/dismiss `ch5-button`s, since neither
`ch5-modal-dialog` nor `ch5-overlay-panel` is exposed in Construct's own editor
(confirmed via `viewProperties.showOnUI` — see the spec). `generator/
camera_control.py` (subsystem-control tier): `ch5-dpad` + Zoom `ch5-button`s +
`ch5-button-list` presets + power `ch5-toggle`, standalone. `layout_patterns.py`
gains `build_tabbed_shell` (layout-pattern tier): composes the above plus a new
header/footer/tab-strip/tab-content-widget shape into one Splash page + one Main
Panel page + N widgets.

**Tech Stack:** Python 3, no new dependencies. Test convention: standalone
scripts under `generator/_test_output/`, run directly with `python <file>.py` (no
pytest; a test passes when it prints its OK lines and exits 0).

**Spec:** `docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md`.

## Global Constraints

- **Every primitive this plan touches is already confirmed real and exposed in
  Construct** (`ch5-tab-button`, `ch5-dpad`, `ch5-button-list`, `ch5-slider`,
  `ch5-toggle`, `ch5-button`, `ch5-text`, `ch5-datetime`, `ch5-image`, `html-div`)
  — no new SDK-grounding work is needed or expected in this plan.
- **Content is always caller-supplied**, per `ConstructUISkill.md` §11: room
  name, splash tiles, system modes beyond "System Power", footer subsystem
  names, and camera presets are all parameters, never hardcoded.
- **"System Power" is always the first system mode** — baked into
  `build_tabbed_shell` itself (not left to caller discipline), per the
  reference spec's "always included by default" line.
- **Modal geometry is a centered card over a dimmed backdrop**, not
  edge-to-edge — confirmed with the user 2026-09-17.
- **Raise rather than silently overflow/degrade**, same discipline as every
  other layout-pattern builder in this project (`_layout_row`,
  `build_bento_box_page`'s touch-target/height checks).
- **`README.md`'s Log gets an entry in the same turn as any completed task.**
- **`generator/_test_output/` test scripts are the only tracked files in that
  directory** — running a test creates output files that do NOT need `git add`.

---

## Task 1: `generator/modal.py` — the generic modal widget

**Files:**
- Create: `generator/modal.py`
- Test: `generator/_test_output/modal_test.py` (new)

**Interfaces:**
- Consumes: `component.build_component` (existing), `html_div.build_html_div`
  (existing), `page.build_widget_attributes`/`default_widget_html_css`/
  `generate_element_id` (existing), `spacing.EDGE_PADDING`/`MIN_TOUCH_TARGET`
  (existing).
- Produces: `modal.content_area(card_width, card_height) -> (x, y, width,
  height)` and `modal.build_modal_widget(sdk, *, widget_width, widget_height,
  widget_name, title, card_width, card_height, content_builder, resolution=None,
  active_font="Roboto", closable=True, dismissable=True) -> (widget_id,
  widget_attrs, html, css, elements)`, where `content_builder(x, y, width,
  height, z_index) -> (html, css, list[Element])`. Raises `ValueError` if the
  card doesn't fit the panel, or the card is too small to leave a positive
  content area below the title bar.

### Step 1: Write the failing test

Create `generator/_test_output/modal_test.py`:

```python
"""modal.py -- generic modal/dialog widget (primitive tier, any layout can use
it). See docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md
for why this is built from html-div + ch5-button rather than ch5-modal-dialog
(not exposed in Construct's own editor)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from modal import build_modal_widget, content_area  # noqa: E402
from page import build_page_attributes, generate_element_id, write_cuig  # noqa: E402
from component import build_component  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "Modal"
OUT.mkdir(parents=True, exist_ok=True)


def trivial_content(x, y, width, height, z_index):
    # content_builder's contract is (html, css, list[Element]) --
    # build_component returns a single Element, not a list, so it's wrapped
    # here the same way camera_control.build_camera_control returns its own
    # multi-element list in Task 2.
    html, css, element = build_component(
        ui_sdk, "ch5-text", component_name="Trivial Content", element_id=generate_element_id(),
        x=x, y=y, width=width, height=height, z_index=z_index, active_font="Roboto",
        label="content", overrides={"labelinnerhtml": "content"},
    )
    return html, css, [element]


# --- content_area: a real card leaves a positive area below the title bar ----------
x, y, w, h = content_area(600, 500)
assert x > 0 and y > 0 and w > 0 and h > 0
assert y > x, "content must start below the title bar, not at the same inset as the left edge"
print("content_area: positive area below the title bar for a real card size: OK")

try:
    content_area(200, 60)
    raise AssertionError("expected ValueError for a card too short to hold any content")
except ValueError:
    pass
print("content_area: a too-short card raises ValueError: OK")

# --- build_modal_widget: default (closable + dismissable) --------------------------
widget_id, widget_attrs, html, css, elements = build_modal_widget(
    ui_sdk, widget_width=1280, widget_height=800, widget_name="Test Modal",
    title="Test Modal", card_width=600, card_height=500, content_builder=trivial_content,
)
# container + backdrop + dismiss button + card + title + close button + content = 7
assert len(elements) == 7, len(elements)
print("build_modal_widget: default (closable+dismissable) produces 7 elements: OK")

assert 'labelinnerhtml="content"' in html
assert 'labelinnerhtml="Test Modal"' in html  # the title text
print("build_modal_widget: content and title both present in the written Html: OK")

widget_path = OUT / "TestModal.cuiw"
write_cuig(widget_path, widget_attrs, html=html, css=css, elements=elements)
assert compare.round_trip_check(widget_path), "modal widget failed round-trip"
print("build_modal_widget: written .cuiw round-trips byte-identical: OK")

# --- closable=False / dismissable=False each drop exactly one element --------------
_, _, _, _, no_close_elements = build_modal_widget(
    ui_sdk, widget_width=1280, widget_height=800, widget_name="Test Modal",
    title="Test Modal", card_width=600, card_height=500, content_builder=trivial_content,
    closable=False,
)
assert len(no_close_elements) == 6, len(no_close_elements)
print("build_modal_widget: closable=False omits the close button: OK")

_, _, _, _, no_dismiss_elements = build_modal_widget(
    ui_sdk, widget_width=1280, widget_height=800, widget_name="Test Modal",
    title="Test Modal", card_width=600, card_height=500, content_builder=trivial_content,
    dismissable=False,
)
assert len(no_dismiss_elements) == 6, len(no_dismiss_elements)
print("build_modal_widget: dismissable=False omits the backdrop-tap dismiss button: OK")

# --- a card bigger than the panel raises rather than silently mispositioning -------
try:
    build_modal_widget(
        ui_sdk, widget_width=400, widget_height=300, widget_name="TooBig",
        title="Too Big", card_width=600, card_height=500, content_builder=trivial_content,
    )
    raise AssertionError("expected ValueError for a card bigger than its panel")
except ValueError:
    pass
print("build_modal_widget: a card bigger than the panel raises ValueError: OK")

print("Modal: all assertions passed.")
```

- [ ] **Run it to confirm it fails:**

```bash
cd generator/_test_output && python modal_test.py
```

Expected: `ModuleNotFoundError: No module named 'modal'`.

### Step 2: Implement `generator/modal.py`

```python
"""
Generic modal/dialog widget (primitive tier) -- reusable by any layout
pattern, not Tabbed-specific. Construct's CH5 SDK schema defines
ch5-modal-dialog and ch5-overlay-panel with plausible-looking attributes, but
neither carries `viewProperties.showOnUI: true` in component-context.json
(confirmed 2026-09-17 against the installed 2.18.0 SDK, cross-checked against
zero real authored .cuig/.cuiw files anywhere in C:\\Solutions\\ClaudeSamples or
C:\\Git\\CCIDE using either tag) -- neither is actually exposed in Construct's
own editor, so neither can be used (user, 2026-09-17: "you cant use components
that are not exposed in Construct").

Built instead entirely from primitives already confirmed real: a full-panel
backdrop html-div (semi-transparent, low z-index), a centered card html-div
(the visible dialog box), a title ch5-text, an optional close-icon ch5-button,
and -- since the real html-div reference files carry no click/tap signal of
their own (confirmed: no sendevent* attribute anywhere in
`Component - DIV.cuig`) -- a transparent full-panel ch5-button behind the card
for backdrop-tap dismiss. The whole thing is a WIDGET; its own
Visibility=Contract (set by the caller when referencing it from a page, see
page.py::add_widget_reference_to_page) is the open/close signal -- reuses the
project's already-proven mechanism (ConstructUISkill.md §5), not a new one.

See docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md.
"""
from __future__ import annotations

from typing import Callable
from uuid import uuid4

import component
import palette
import spacing
from elements import Element
from html_div import build_html_div
from page import build_widget_attributes, default_widget_html_css, generate_element_id
from sdk import UiSdk

#: Judgment calls (not a Construct spec), consistent with every other named
#: constant in this project's layout-pattern modules.
TITLE_BAR_HEIGHT = 56
CARD_PADDING = spacing.EDGE_PADDING
CLOSE_BUTTON_SIZE = spacing.MIN_TOUCH_TARGET
BACKDROP_COLOR = "rgba(0, 0, 0, 0.5)"
CARD_BACKGROUND_COLOR = "#ffffff"
CARD_TEXT_COLOR = "#1a1a1a"
CARD_RADIUS = 12

#: (x, y, width, height, z_index) -> (html, css, list[Element]), called once
#: with the content area already computed inside the card.
ContentBuilder = Callable[[int, int, int, int, int], "tuple[str, str, list[Element]]"]


def content_area(card_width: int, card_height: int) -> tuple[int, int, int, int]:
    """(x, y, width, height) of the content region INSIDE a card_width x
    card_height card, relative to the card's own top-left corner -- below the
    title bar, inset by CARD_PADDING on every side. Raises ValueError if the
    card is too small to leave a positive content area."""
    content_x = CARD_PADDING
    content_y = TITLE_BAR_HEIGHT + CARD_PADDING
    content_width = card_width - 2 * CARD_PADDING
    content_height = card_height - TITLE_BAR_HEIGHT - 2 * CARD_PADDING
    if content_width <= 0 or content_height <= 0:
        raise ValueError(
            f"a {card_width}x{card_height} card leaves no room for content below "
            f"the {TITLE_BAR_HEIGHT}px title bar and {CARD_PADDING}px padding on "
            f"every side -- use a larger card_width/card_height"
        )
    return content_x, content_y, content_width, content_height


def build_modal_widget(
    sdk: UiSdk, *, widget_width: int, widget_height: int, widget_name: str,
    title: str, card_width: int, card_height: int, content_builder: ContentBuilder,
    resolution: tuple[int, int] | None = None, active_font: str = "Roboto",
    closable: bool = True, dismissable: bool = True,
) -> tuple[str, list[tuple[str, str]], str, str, list[Element]]:
    """One modal, as a WIDGET (see module docstring for why -- no native
    ch5-modal-dialog is available). `widget_width`/`widget_height` are the full
    panel's own size (the backdrop covers all of it); `card_width`/
    `card_height` the visible dialog box, centered within that.
    `content_builder` is called once with the content area INSIDE the card
    (below the title bar -- see content_area()), already offset to the card's
    real on-widget position; its own return is merged into this widget's
    assembly.

    `closable` adds a close-icon ch5-button in the card's top-right corner.
    `dismissable` adds a transparent, full-panel ch5-button BEHIND the card so
    a tap anywhere on the backdrop closes the modal too (see module
    docstring). This module only builds the buttons -- wiring a press to the
    widget's own Visibility signal is the caller's job (same division of
    responsibility as every other button-driven contract signal in this
    project, ConstructUISkill.md §6).

    Returns `(widget_id, widget_attrs, html, css, elements)` -- the widget_id
    is returned (unlike build_footer_widget/build_header_widget) since a
    modal may be referenced from more than one page.

    Raises ValueError if the card doesn't fit within the panel, or is too
    small to leave a positive content area (see content_area()).
    """
    if card_width > widget_width or card_height > widget_height:
        raise ValueError(
            f"a {card_width}x{card_height} card doesn't fit within the "
            f"{widget_width}x{widget_height} panel it's centered in"
        )
    inner_x, inner_y, inner_w, inner_h = content_area(card_width, card_height)
    card_x = (widget_width - card_width) // 2
    card_y = (widget_height - card_height) // 2

    widget_id = str(uuid4())
    widget_attrs = build_widget_attributes(name=widget_name, widget_id=widget_id)
    container_html, container_css, container_element = default_widget_html_css(
        generate_element_id(), widget_width, widget_height, resolution, is_global=False)

    parts: list[tuple[str, str, Element]] = []

    backdrop_html, backdrop_css, backdrop_element = build_html_div(
        component_name=f"{widget_name} Backdrop", element_id=generate_element_id(),
        x=0, y=0, width=widget_width, height=widget_height, z_index=1,
        resolution=resolution, background_color=BACKDROP_COLOR,
    )
    parts.append((backdrop_html, backdrop_css, backdrop_element))

    if dismissable:
        dismiss_html, dismiss_css, dismiss_element = component.build_component(
            sdk, "ch5-button", component_name=f"{widget_name} Dismiss",
            element_id=generate_element_id(), x=0, y=0, width=widget_width,
            height=widget_height, z_index=2, resolution=resolution, label="",
            active_font=active_font, overrides={"labelinnerhtml": ""},
        )
        dismiss_css = palette.apply_palette(
            dismiss_css, dict(dismiss_element.attributes)["id"], sdk, "ch5-button",
            {"background_color": "transparent", "border_width": "0px"},
        )
        parts.append((dismiss_html, dismiss_css, dismiss_element))

    card_html, card_css, card_element = build_html_div(
        component_name=f"{widget_name} Card", element_id=generate_element_id(),
        x=card_x, y=card_y, width=card_width, height=card_height, z_index=3,
        resolution=resolution, background_color=CARD_BACKGROUND_COLOR,
        border_radius=CARD_RADIUS,
    )
    parts.append((card_html, card_css, card_element))

    title_width = card_width - 2 * CARD_PADDING - (CLOSE_BUTTON_SIZE + CARD_PADDING if closable else 0)
    title_html, title_css, title_element = component.build_component(
        sdk, "ch5-text", component_name=f"{widget_name} Title",
        element_id=generate_element_id(), x=card_x + CARD_PADDING, y=card_y + CARD_PADDING,
        width=title_width, height=TITLE_BAR_HEIGHT - 2 * CARD_PADDING, z_index=4,
        resolution=resolution, active_font=active_font, label=title,
        overrides={"labelinnerhtml": title},
    )
    parts.append((title_html, title_css, title_element))

    if closable:
        close_html, close_css, close_element = component.build_component(
            sdk, "ch5-button", component_name=f"{widget_name} Close",
            element_id=generate_element_id(),
            x=card_x + card_width - CARD_PADDING - CLOSE_BUTTON_SIZE, y=card_y + CARD_PADDING,
            width=CLOSE_BUTTON_SIZE, height=CLOSE_BUTTON_SIZE, z_index=4,
            resolution=resolution, active_font=active_font, label="",
            icon_class="fa-solid fa-xmark", icon_library="FA Classic Solid",
            overrides={"labelinnerhtml": ""},
        )
        parts.append((close_html, close_css, close_element))

    content_html, content_css, content_elements = content_builder(
        card_x + inner_x, card_y + inner_y, inner_w, inner_h, 5)

    html = container_html + "".join(h for h, _, _ in parts) + content_html
    css = container_css + "".join(c for _, c, _ in parts) + content_css
    elements = [container_element] + [e for _, _, e in parts] + list(content_elements)
    return widget_id, widget_attrs, html, css, elements
```

- [ ] **Run the test to verify it passes:**

```bash
cd generator/_test_output && python modal_test.py
```

Expected: every OK line prints, `Modal: all assertions passed.` at the end.

- [ ] **Run the full existing suite to confirm no regressions:**

```bash
cd generator/_test_output && for f in *_test.py; do python "$f" || echo "FAIL: $f"; done
```

Expected: no `FAIL:` lines except the two known pre-existing unrelated failures
(`page_background_color_test.py`'s live-project drift, `phase5_smoke_test.py`'s
74-vs-75 catalog count).

- [ ] **Commit:**

```bash
git add generator/modal.py generator/_test_output/modal_test.py
git commit -m "feat: add generic modal widget (backdrop + card, no native ch5-modal-dialog available)"
```

---

## Task 2: `generator/camera_control.py` — the Camera subsystem composite

**Files:**
- Create: `generator/camera_control.py`
- Test: `generator/_test_output/camera_control_test.py` (new)

**Interfaces:**
- Consumes: `component.build_component` (existing), `style.set_html_attribute`
  (existing), `spacing.EDGE_PADDING`/`SPACING_UNIT`/`MIN_TOUCH_TARGET`
  (existing), `page.generate_element_id` (existing).
- Produces: `camera_control.build_camera_control(sdk, *, x, y, width, height,
  z_index, resolution, presets, active_font="Roboto") -> (html, css,
  list[Element])`. Raises `ValueError` if the 3 bands (presets/position/power)
  don't fit within `height`, or the position band is too narrow for a square
  dpad plus zoom buttons.

### Step 1: Write the failing test

Create `generator/_test_output/camera_control_test.py`:

```python
"""camera_control.py -- the Camera subsystem-control composite (subsystem-
control tier): PTZ dpad + zoom buttons + preset tile group + power toggle.
Standalone, no knowledge of modals or pages -- matches modal.py's
ContentBuilder signature directly. See
docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from camera_control import build_camera_control  # noqa: E402
from page import build_page_attributes, write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "CameraControl"
OUT.mkdir(parents=True, exist_ok=True)

presets = ["Wide", "Speaker Track", "Presenter"]
html, css, elements = build_camera_control(
    ui_sdk, x=0, y=0, width=560, height=500, z_index=5, resolution=(1280, 800),
    presets=presets, active_font="Roboto",
)
# preset button-list + dpad + zoom in + zoom out + power toggle = 5 top-level elements
assert len(elements) == 5, len(elements)
print("build_camera_control: 5 top-level elements (presets, dpad, 2 zoom buttons, power): OK")

assert "<ch5-dpad " in html
assert html.count("<ch5-button ") >= 2  # zoom in + zoom out (button-list's own children are nested)
assert "<ch5-button-list " in html
assert "<ch5-toggle " in html
print("build_camera_control: dpad, button-list, 2 zoom buttons, and power toggle all present: OK")

for label in presets:
    assert f'labelinnerhtml="{label}"' in html
print("build_camera_control: every preset's own label present on its button-list child: OK")

page_attrs = build_page_attributes(name="CameraControlDemo")
page_path = OUT / "CameraControl.cuig"
write_cuig(page_path, page_attrs, html=html, css=css, elements=elements)
assert compare.round_trip_check(page_path), "camera control page failed round-trip"
print("build_camera_control: written .cuig round-trips byte-identical: OK")

# --- too short for the 3 bands raises ------------------------------------------------
try:
    build_camera_control(
        ui_sdk, x=0, y=0, width=560, height=120, z_index=5, resolution=(1280, 800),
        presets=presets,
    )
    raise AssertionError("expected ValueError for a box too short for the 3 bands")
except ValueError:
    pass
print("build_camera_control: a box too short for the 3 bands raises ValueError: OK")

# --- too narrow for a square dpad + zoom buttons raises -------------------------------
try:
    build_camera_control(
        ui_sdk, x=0, y=0, width=140, height=500, z_index=5, resolution=(1280, 800),
        presets=presets,
    )
    raise AssertionError("expected ValueError for a box too narrow for dpad + zoom buttons")
except ValueError:
    pass
print("build_camera_control: a box too narrow for dpad + zoom buttons raises ValueError: OK")

print("Camera Control: all assertions passed.")
```

- [ ] **Run it to confirm it fails:**

```bash
cd generator/_test_output && python camera_control_test.py
```

Expected: `ModuleNotFoundError: No module named 'camera_control'`.

### Step 2: Implement `generator/camera_control.py`

```python
"""
Camera subsystem-control composite (subsystem-control tier, per the two-tier
split the user asked for 2026-09-17: this has zero knowledge of Tabbed,
modals, or pages -- it drops into a modal today, a Bento Box popup or a
future layout's own container unchanged, matching modal.py's ContentBuilder
signature: (x, y, width, height, z_index) -> (html, css, list[Element])).

Three bands, top to bottom, per the reference spec's Camera modal section:
Presets (ch5-button-list, single-select tile group) / Position (ch5-dpad,
whose native center/home button covers the "home/reset" requirement, plus
separate Zoom In/Zoom Out ch5-buttons beside it -- zoom is not part of any
dpad in the real SDK schema) / Power (ch5-toggle). All 5 component types
(ch5-button-list, ch5-dpad, ch5-button, ch5-toggle) are confirmed real and
exposed in Construct (viewProperties.showOnUI: true) with real reference
files already in this project's sample solution.

Preset labels: component.build_children's ch5-button-list path (confirmed
real, already used by this project) auto-generates `numberofitems` generic
children -- this module relabels each one's own `labelinnerhtml` in place via
style.set_html_attribute, using that child's own id (each carries a real,
unique one -- confirmed via component.py's _child()/_AUTO_ID), the same
post-build attribute-flip precedent already used elsewhere in this project
(e.g. shape.py::apply_radius_preset's shape="custom" flip).

See docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md.
"""
from __future__ import annotations

import component
import spacing
import style
from elements import Element
from page import generate_element_id
from sdk import UiSdk

#: Fraction of the given box's height given to each band, top to bottom.
#: Judgment call (not a Construct spec), same precedent as room_card.py's own
#: band fractions -- verified against this module's own test to fit without
#: overflow at a real modal card's content-area scale.
PRESETS_BAND_FRACTION = 0.20
POSITION_BAND_FRACTION = 0.55
POWER_BAND_FRACTION = 0.15


def build_camera_control(
    sdk: UiSdk, *, x: int, y: int, width: int, height: int, z_index: int,
    resolution: tuple[int, int] | None, presets: list[str], active_font: str = "Roboto",
) -> tuple[str, str, list[Element]]:
    """`(html, css, elements)` for one Camera subsystem control, laid out
    within the given box. See module docstring for the full mechanism.
    Raises `ValueError` if the 3 bands don't fit within `height`, or if the
    position band is too narrow for a square dpad plus zoom buttons."""
    gap = spacing.SPACING_UNIT
    inner_x = x + spacing.EDGE_PADDING
    inner_width = width - 2 * spacing.EDGE_PADDING
    presets_h = round(height * PRESETS_BAND_FRACTION)
    position_h = round(height * POSITION_BAND_FRACTION)
    power_h = round(height * POWER_BAND_FRACTION)
    consumed = presets_h + position_h + power_h + 2 * gap + 2 * spacing.EDGE_PADDING
    if inner_width <= 0 or consumed > height:
        raise ValueError(
            f"a {width}x{height} box can't fit the presets/position/power bands "
            f"({consumed}px needed, {inner_width}px usable width) -- "
            f"build_camera_control needs a bigger box"
        )

    elements: list[Element] = []
    html_parts: list[str] = []
    css_parts: list[str] = []
    y_cursor = y + spacing.EDGE_PADDING

    # --- Presets: single-select tile group ---------------------------------------
    presets_html, presets_css, presets_element = component.build_component(
        sdk, "ch5-button-list", component_name="Camera Presets",
        element_id=generate_element_id(), x=inner_x, y=y_cursor, width=inner_width,
        height=presets_h, z_index=z_index, resolution=resolution, active_font=active_font,
        overrides={"numberofitems": str(len(presets)), "orientation": "horizontal"},
    )
    child_ids = [dict(child.attributes)["id"] for child in presets_element.components]
    for child_id, preset_label in zip(child_ids, presets):
        presets_html = style.set_html_attribute(presets_html, child_id, "labelinnerhtml", preset_label)
    elements.append(presets_element)
    html_parts.append(presets_html)
    css_parts.append(presets_css)
    y_cursor += presets_h + gap

    # --- Position: square dpad + Zoom In/Out stacked beside it --------------------
    dpad_size = position_h
    zoom_width = inner_width - dpad_size - gap
    if zoom_width < spacing.MIN_TOUCH_TARGET:
        raise ValueError(
            f"a {inner_width}px wide box leaves only {zoom_width}px for zoom buttons "
            f"after a {dpad_size}px square dpad -- build_camera_control needs a wider box"
        )
    dpad_html, dpad_css, dpad_element = component.build_component(
        sdk, "ch5-dpad", component_name="Camera Position", element_id=generate_element_id(),
        x=inner_x, y=y_cursor, width=dpad_size, height=dpad_size, z_index=z_index,
        resolution=resolution, active_font=active_font,
    )
    elements.append(dpad_element)
    html_parts.append(dpad_html)
    css_parts.append(dpad_css)

    zoom_x = inner_x + dpad_size + gap
    zoom_h = max((position_h - gap) // 2, spacing.MIN_TOUCH_TARGET)
    if 2 * zoom_h + gap > position_h:
        raise ValueError(
            f"the {position_h}px position band is too short for two "
            f"{spacing.MIN_TOUCH_TARGET}px-floor zoom buttons"
        )
    for label, icon, dy in (
        ("Zoom In", "fa-solid fa-magnifying-glass-plus", 0),
        ("Zoom Out", "fa-solid fa-magnifying-glass-minus", zoom_h + gap),
    ):
        zoom_html, zoom_css, zoom_element = component.build_component(
            sdk, "ch5-button", component_name=label, element_id=generate_element_id(),
            x=zoom_x, y=y_cursor + dy, width=zoom_width, height=zoom_h, z_index=z_index,
            resolution=resolution, active_font=active_font, label=label,
            icon_class=icon, icon_library="FA Classic Solid",
        )
        elements.append(zoom_element)
        html_parts.append(zoom_html)
        css_parts.append(zoom_css)
    y_cursor += position_h + gap

    # --- Power toggle ---------------------------------------------------------------
    power_html, power_css, power_element = component.build_component(
        sdk, "ch5-toggle", component_name="Camera Power", element_id=generate_element_id(),
        x=inner_x, y=y_cursor, width=inner_width, height=power_h, z_index=z_index,
        resolution=resolution, active_font=active_font, label="Power",
    )
    elements.append(power_element)
    html_parts.append(power_html)
    css_parts.append(power_css)

    return "".join(html_parts), "".join(css_parts), elements
```

- [ ] **Run the test to verify it passes:**

```bash
cd generator/_test_output && python camera_control_test.py
```

Expected: every OK line prints, `Camera Control: all assertions passed.` at the end.

- [ ] **Run the full existing suite to confirm no regressions:**

```bash
cd generator/_test_output && for f in *_test.py; do python "$f" || echo "FAIL: $f"; done
```

Expected: no `FAIL:` lines except the two known pre-existing unrelated failures.

- [ ] **Commit:**

```bash
git add generator/camera_control.py generator/_test_output/camera_control_test.py
git commit -m "feat: add Camera subsystem-control composite (dpad + zoom + presets + power)"
```

---

## Task 3: `layout_patterns.py::build_tabbed_shell` — the navigational shell

**Files:**
- Modify: `generator/layout_patterns.py`
- Test: `generator/_test_output/tabbed_shell_test.py` (new)

**Interfaces:**
- Consumes: `modal.build_modal_widget` (Task 1), `camera_control.build_camera_control`
  (Task 2), `component.build_component`, `style.set_html_attribute`,
  `page.build_page_attributes`/`build_widget_attributes`/`default_widget_html_css`/
  `generate_element_id`/`add_widget_reference_to_page` (existing), this module's own
  `_DATETIME_WIDTH`/`_DATETIME_HEIGHT` (existing) and a new `_layout_tabbed_row`
  helper this task adds (deliberately NOT the existing `_layout_row` — see Step 2).
- Produces: `build_tabbed_shell(sdk, *, room_name, splash_tiles,
  additional_system_modes, subsystems, camera_presets, panel_width, panel_height,
  header_height=160, footer_height=120, resolution=None, active_font="Roboto",
  logo_asset_id="0") -> dict` — see Step 2 for the exact return shape. Raises
  `ValueError` for a panel too narrow for the header's logo/tab-strip, a header
  too short for the room-name/date-time stack, a footer zone too narrow for its
  content, or an empty `subsystems` list.

### Step 1: Write the failing test

Create `generator/_test_output/tabbed_shell_test.py`:

```python
"""layout_patterns.py::build_tabbed_shell -- the Tabbed layout pattern's
navigational shell (Phase 1: splash->main-panel, tab strip <-> per-mode
content-swap widgets, 3-zone footer, one real modal). See
docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from layout_patterns import build_tabbed_shell  # noqa: E402
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "TabbedShell"
OUT.mkdir(parents=True, exist_ok=True)

result = build_tabbed_shell(
    ui_sdk, room_name="Boardroom A",
    splash_tiles=[("Join Video Call", "fa-solid fa-video"), ("Join Audio Call", "fa-solid fa-phone")],
    additional_system_modes=["Presentation", "Video Call", "Audio Call"],
    subsystems=["Environment", "Audio", "Camera"],
    camera_presets=["Wide", "Speaker Track", "Presenter"],
    panel_width=1280, panel_height=800,
)

# --- System Power is always first, ahead of the caller-supplied modes --------------
splash_attrs, splash_html, splash_css, splash_elements = result["splash_page"]
main_attrs, main_html, main_css, main_elements = result["main_panel_page"]
tab_content_widgets = result["tab_content_widgets"]
assert list(tab_content_widgets.keys()) == ["System Power", "Presentation", "Video Call", "Audio Call"]
print("build_tabbed_shell: 'System Power' is always the first system mode: OK")

# --- header: tab strip carries every mode's own label -------------------------------
header_widget_id, header_attrs, header_html, header_css, header_elements = result["header_widget"]
for mode in tab_content_widgets:
    assert f'labelinnerhtml="{mode}"' in header_html
assert "<ch5-datetime " in header_html
assert "<ch5-image " in header_html
print("build_tabbed_shell: header carries room name, date/time, logo, and every mode's tab label: OK")

# --- footer: one button per subsystem + Privacy Mute + volume + mute ---------------
footer_widget_id, footer_attrs, footer_html, footer_css, footer_elements = result["footer_widget"]
for label in ["Environment", "Audio", "Camera"]:
    assert f'componentName="Footer {label}"' in footer_html
assert 'componentName="Privacy Mute"' in footer_html
assert "<ch5-slider " in footer_html  # volume
assert 'componentName="Volume Mute"' in footer_html
print("build_tabbed_shell: footer carries one button per subsystem, Privacy Mute, and volume+mute: OK")

# --- modals: Camera gets real content, everything else stays empty this phase ------
modal_widgets = result["modal_widgets"]
assert set(modal_widgets.keys()) == {"Environment", "Audio", "Camera"}
_, _, camera_modal_html, _, camera_modal_elements = modal_widgets["Camera"]
assert "<ch5-dpad " in camera_modal_html
_, _, environment_modal_html, _, environment_modal_elements = modal_widgets["Environment"]
assert "<ch5-dpad " not in environment_modal_html
# camera's modal has real content elements beyond the modal chrome itself; an empty
# modal has exactly the chrome (container + backdrop + dismiss + card + title + close)
assert len(camera_modal_elements) > len(environment_modal_elements)
print("build_tabbed_shell: Camera modal has real content, other modals stay empty this phase: OK")

# --- Main Panel page references every widget exactly once --------------------------
widget_ref_count = main_html.count("<ch5-template ")
expected_widgets = 2 + len(tab_content_widgets) + len(modal_widgets)  # header + footer + N tabs + N modals
assert widget_ref_count == expected_widgets, (widget_ref_count, expected_widgets)
print(f"build_tabbed_shell: Main Panel page references all {expected_widgets} widgets exactly once: OK")

# --- every page/widget round-trips byte-identical -----------------------------------
write_cuig(OUT / "Splash.cuig", splash_attrs, html=splash_html, css=splash_css, elements=splash_elements)
assert compare.round_trip_check(OUT / "Splash.cuig")
write_cuig(OUT / "MainPanel.cuig", main_attrs, html=main_html, css=main_css, elements=main_elements)
assert compare.round_trip_check(OUT / "MainPanel.cuig")
write_cuig(OUT / "Header.cuiw", header_attrs, html=header_html, css=header_css, elements=header_elements)
assert compare.round_trip_check(OUT / "Header.cuiw")
write_cuig(OUT / "Footer.cuiw", footer_attrs, html=footer_html, css=footer_css, elements=footer_elements)
assert compare.round_trip_check(OUT / "Footer.cuiw")
for mode, (wid, attrs, html, css, elements) in tab_content_widgets.items():
    path = OUT / f"Tab_{mode.replace(' ', '')}.cuiw"
    write_cuig(path, attrs, html=html, css=css, elements=elements)
    assert compare.round_trip_check(path), mode
for label, (wid, attrs, html, css, elements) in modal_widgets.items():
    path = OUT / f"Modal_{label}.cuiw"
    write_cuig(path, attrs, html=html, css=css, elements=elements)
    assert compare.round_trip_check(path), label
print("build_tabbed_shell: every page/widget round-trips byte-identical: OK")

# --- an empty subsystems list raises rather than building a footer with nothing ----
try:
    build_tabbed_shell(
        ui_sdk, room_name="Empty", splash_tiles=[], additional_system_modes=[],
        subsystems=[], camera_presets=[], panel_width=1280, panel_height=800,
    )
    raise AssertionError("expected ValueError for an empty subsystems list")
except ValueError:
    pass
print("build_tabbed_shell: an empty subsystems list raises ValueError: OK")

print("Tabbed Shell: all assertions passed.")
```

- [ ] **Run it to confirm it fails:**

```bash
cd generator/_test_output && python tabbed_shell_test.py
```

Expected: `ImportError: cannot import name 'build_tabbed_shell' from 'layout_patterns'`.

### Step 2: Implement `build_tabbed_shell` in `generator/layout_patterns.py`

`generator/layout_patterns.py` already imports `from uuid import uuid4` and
`from page import build_page_attributes, build_widget_attributes,
default_widget_html_css, generate_element_id` at the top of the file. Add
`camera_control`, `modal`, and `add_widget_reference_to_page` to that same
area:

```python
import camera_control
import modal
```

and change the existing `from page import ...` line to also pull in
`add_widget_reference_to_page`:

```python
from page import (
    add_widget_reference_to_page, build_page_attributes, build_widget_attributes,
    default_widget_html_css, generate_element_id,
)
```

Append this helper and function at the end of `generator/layout_patterns.py`:

```python
def _layout_tabbed_row(
    item_count: int, row_width: int, row_height: int,
) -> list[tuple[int, int, int, int]]:
    """`(x, y, width, height)` for `item_count` items evenly spaced in a
    single row spanning `row_width`, honoring spacing.EDGE_PADDING at both
    ends and spacing.SPACING_UNIT gaps between items -- the same shape as
    `_layout_row`, deliberately NOT reusing it: `_layout_row`'s own
    `snap_to_spacing` step rounds each item's width up to the nearest
    spacing-unit multiple, which can push the summed row width a few pixels
    over `row_width` in cases `_layout_row`'s existing callers never hit
    (verified directly: both a 2-tile splash row at a full panel size and a
    3-button footer subsystem zone overflow this way with real Phase 1
    numbers -- `_layout_row(3, 1280 // 3, 120)` and `_layout_row(2, 1280,
    800)` both raise `ValueError` on numbers that clearly ought to fit).
    Floor division only, no snapping -- items come out a few px narrower
    than `_layout_row` would produce, never wider than the row, so the
    summed width can never exceed it. Raises ValueError if `item_count`
    doesn't fit at the touch-target floor.
    """
    item_height = max(row_height - 2 * spacing.EDGE_PADDING, spacing.MIN_TOUCH_TARGET)
    usable_width = row_width - 2 * spacing.EDGE_PADDING
    gap_total = spacing.SPACING_UNIT * (item_count - 1)
    item_width = (usable_width - gap_total) // item_count
    if item_width < spacing.MIN_TOUCH_TARGET:
        raise ValueError(
            f"{item_count} items at the {spacing.MIN_TOUCH_TARGET}px touch-target floor "
            f"need more than the {row_width}px available width -- reduce item_count "
            f"or use a wider row"
        )
    positions = []
    x = spacing.EDGE_PADDING
    for _ in range(item_count):
        positions.append((x, spacing.EDGE_PADDING, item_width, item_height))
        x += item_width + spacing.SPACING_UNIT
    return positions


def build_tabbed_shell(
    sdk: UiSdk, *, room_name: str, splash_tiles: list[tuple[str, str]],
    additional_system_modes: list[str], subsystems: list[str],
    camera_presets: list[str], panel_width: int, panel_height: int,
    header_height: int = 160, footer_height: int = 120,
    resolution: tuple[int, int] | None = None, active_font: str = "Roboto",
    logo_asset_id: str = "0",
) -> dict:
    """Tabbed layout pattern, commercial, Phase 1 shell (design-system §2's
    Tabbed pattern) -- Splash page, Main Panel page (2-row header + tab-strip-
    driven per-mode content widgets + 3-zone footer), and one modal widget per
    footer subsystem (Camera's is real content, the rest are empty this
    phase). See docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md.

    "System Power" is always the first system mode -- the reference spec's
    own "always included by default" rule, baked in here rather than left to
    caller discipline. `additional_system_modes` are whichever of
    Presentation/Video Call/Audio Call (or a future project's own set) the
    caller asked the user for, per ConstructUISkill.md §11.

    Returns a dict: `splash_page`/`main_panel_page` ->
    `(page_attrs, html, css, elements)`; `header_widget`/`footer_widget` ->
    `(widget_id, widget_attrs, html, css, elements)`; `tab_content_widgets`/
    `modal_widgets` -> `{name: (widget_id, widget_attrs, html, css,
    elements)}`, keyed by system mode / subsystem name respectively. The
    caller writes each entry with page.py::write_cuig.

    Raises ValueError for a panel too narrow for the header's logo + tab
    strip, a header too short for the room-name/date-time stack, a footer
    zone too narrow for its content, or an empty `subsystems` list.
    """
    system_modes = ["System Power", *additional_system_modes]
    if not subsystems:
        raise ValueError("build_tabbed_shell needs at least one footer subsystem")

    # --- header: 2 rows, logo spans both -------------------------------------------
    logo_size = header_height
    left_column_width = panel_width - logo_size - spacing.SPACING_UNIT
    if left_column_width <= 0:
        raise ValueError(
            f"a {panel_width}px wide panel is too narrow for a {logo_size}px "
            f"square logo spanning the full header height"
        )
    top_row_height = round(header_height * 0.6)
    bottom_row_height = header_height - top_row_height
    room_name_height = top_row_height - _DATETIME_HEIGHT - spacing.SPACING_UNIT
    if room_name_height <= 0:
        raise ValueError(
            f"a {header_height}px header is too short for the room-name/date-time "
            f"stack (needs {_DATETIME_HEIGHT + spacing.SPACING_UNIT}px+ in the top row)"
        )

    header_widget_id = str(uuid4())
    header_widget_attrs = build_widget_attributes(name="Header", widget_id=header_widget_id)
    header_container_html, header_container_css, header_container_element = default_widget_html_css(
        generate_element_id(), panel_width, header_height, resolution, is_global=True)
    header_parts: list[tuple[str, str, Element]] = []

    room_name_html, room_name_css, room_name_element = component.build_component(
        sdk, "ch5-text", component_name="Room Name", element_id=generate_element_id(),
        x=spacing.EDGE_PADDING, y=spacing.EDGE_PADDING,
        width=left_column_width - 2 * spacing.EDGE_PADDING, height=room_name_height,
        z_index=1, resolution=resolution, active_font=active_font, label=room_name,
        overrides={"labelinnerhtml": room_name},
    )
    header_parts.append((room_name_html, room_name_css, room_name_element))

    datetime_html, datetime_css, datetime_element = component.build_component(
        sdk, "ch5-datetime", component_name="Header DateTime", element_id=generate_element_id(),
        x=spacing.EDGE_PADDING, y=spacing.EDGE_PADDING + room_name_height + spacing.SPACING_UNIT,
        width=_DATETIME_WIDTH, height=_DATETIME_HEIGHT, z_index=1, resolution=resolution,
        active_font=active_font,
    )
    header_parts.append((datetime_html, datetime_css, datetime_element))

    logo_html, logo_css, logo_element = component.build_component(
        sdk, "ch5-image", component_name="Logo", element_id=generate_element_id(),
        x=panel_width - logo_size, y=0, width=logo_size, height=logo_size,
        z_index=1, resolution=resolution, active_font=active_font,
        overrides={"assetid": logo_asset_id},
    )
    header_parts.append((logo_html, logo_css, logo_element))

    tab_strip_html, tab_strip_css, tab_strip_element = component.build_component(
        sdk, "ch5-tab-button", component_name="System Mode Tabs", element_id=generate_element_id(),
        x=0, y=top_row_height, width=left_column_width, height=bottom_row_height,
        z_index=1, resolution=resolution, active_font=active_font,
        overrides={"numberofitems": str(len(system_modes))},
    )
    tab_child_ids = [dict(child.attributes)["id"] for child in tab_strip_element.components]
    for child_id, mode_label in zip(tab_child_ids, system_modes):
        tab_strip_html = style.set_html_attribute(tab_strip_html, child_id, "labelinnerhtml", mode_label)
    header_parts.append((tab_strip_html, tab_strip_css, tab_strip_element))

    header_html = header_container_html + "".join(h for h, _, _ in header_parts)
    header_css = header_container_css + "".join(c for _, c, _ in header_parts)
    header_elements = [header_container_element] + [e for _, _, e in header_parts]

    # --- one tab-content widget per system mode, placeholder text this phase --------
    content_area_height = panel_height - header_height - footer_height
    if content_area_height <= 0:
        raise ValueError(
            f"a {panel_height}px panel has no room left for tab content after a "
            f"{header_height}px header and {footer_height}px footer"
        )
    tab_content_widgets: dict[str, tuple] = {}
    for mode in system_modes:
        widget_id = str(uuid4())
        widget_attrs = build_widget_attributes(name=f"{mode} Content", widget_id=widget_id)
        container_html, container_css, container_element = default_widget_html_css(
            generate_element_id(), panel_width, content_area_height, resolution, is_global=False)
        placeholder_html, placeholder_css, placeholder_element = component.build_component(
            sdk, "ch5-text", component_name=f"{mode} Placeholder", element_id=generate_element_id(),
            x=spacing.EDGE_PADDING, y=spacing.EDGE_PADDING,
            width=panel_width - 2 * spacing.EDGE_PADDING, height=spacing.MIN_TOUCH_TARGET,
            z_index=1, resolution=resolution, active_font=active_font, label=mode,
            overrides={"labelinnerhtml": f"{mode} (placeholder -- follow-on phase)"},
        )
        html = container_html + placeholder_html
        css = container_css + placeholder_css
        elements = [container_element, placeholder_element]
        tab_content_widgets[mode] = (widget_id, widget_attrs, html, css, elements)

    # --- footer: N subsystem buttons (left) + Privacy Mute (center) + volume (right) -
    footer_widget_id = str(uuid4())
    footer_widget_attrs = build_widget_attributes(name="Footer", widget_id=footer_widget_id)
    footer_container_html, footer_container_css, footer_container_element = default_widget_html_css(
        generate_element_id(), panel_width, footer_height, resolution, is_global=True)
    footer_parts: list[tuple[str, str, Element]] = []

    # Center/right zones are sized to their own real fixed content (a square
    # toggle, a comfortably-usable slider + a mute button), not an equal
    # 3-way split -- equal thirds starves the left zone at low subsystem
    # counts and wastes space at high ones. The left zone gets whatever's
    # left of the panel width.
    center_zone_width = max(footer_height, spacing.MIN_TOUCH_TARGET) + 2 * spacing.EDGE_PADDING
    volume_slider_width = 120  # judgment call: comfortably usable, not just the touch-target floor
    right_zone_width = (
        volume_slider_width + spacing.MIN_TOUCH_TARGET + spacing.SPACING_UNIT + 2 * spacing.EDGE_PADDING
    )
    left_zone_width = panel_width - center_zone_width - right_zone_width
    if left_zone_width <= 0:
        raise ValueError(
            f"a {panel_width}px panel has no room left for footer subsystem buttons "
            f"after the center Privacy Mute and right volume/mute zones"
        )

    left_positions = _layout_tabbed_row(len(subsystems), left_zone_width, footer_height)
    for label, (x, y, w, h) in zip(subsystems, left_positions):
        html, css, element = component.build_component(
            sdk, "ch5-button", component_name=f"Footer {label}", element_id=generate_element_id(),
            x=x, y=y, width=w, height=h, z_index=1, resolution=resolution,
            active_font=active_font, label=label,
        )
        footer_parts.append((html, css, element))

    center_size = max(min(center_zone_width, footer_height) - 2 * spacing.EDGE_PADDING, spacing.MIN_TOUCH_TARGET)
    privacy_html, privacy_css, privacy_element = component.build_component(
        sdk, "ch5-toggle", component_name="Privacy Mute", element_id=generate_element_id(),
        x=left_zone_width + (center_zone_width - center_size) // 2, y=(footer_height - center_size) // 2,
        width=center_size, height=center_size, z_index=1, resolution=resolution,
        active_font=active_font, label="Privacy Mute",
    )
    footer_parts.append((privacy_html, privacy_css, privacy_element))

    right_x = left_zone_width + center_zone_width
    volume_height = max(footer_height - 2 * spacing.EDGE_PADDING, spacing.MIN_TOUCH_TARGET)
    volume_html, volume_css, volume_element = component.build_component(
        sdk, "ch5-slider", component_name="Volume", element_id=generate_element_id(),
        x=right_x + spacing.EDGE_PADDING, y=(footer_height - volume_height) // 2,
        width=volume_slider_width, height=volume_height, z_index=1, resolution=resolution,
        active_font=active_font,
    )
    footer_parts.append((volume_html, volume_css, volume_element))
    mute_html, mute_css, mute_element = component.build_component(
        sdk, "ch5-toggle", component_name="Volume Mute", element_id=generate_element_id(),
        x=right_x + spacing.EDGE_PADDING + volume_slider_width + spacing.SPACING_UNIT,
        y=(footer_height - spacing.MIN_TOUCH_TARGET) // 2,
        width=spacing.MIN_TOUCH_TARGET, height=spacing.MIN_TOUCH_TARGET, z_index=1,
        resolution=resolution, active_font=active_font, label="Mute",
    )
    footer_parts.append((mute_html, mute_css, mute_element))

    footer_html = footer_container_html + "".join(h for h, _, _ in footer_parts)
    footer_css = footer_container_css + "".join(c for _, c, _ in footer_parts)
    footer_elements = [footer_container_element] + [e for _, _, e in footer_parts]

    # --- modals: one per subsystem, Camera gets real content, everything else empty -
    modal_widgets: dict[str, tuple] = {}
    modal_card_width = round(panel_width * 0.6)
    # Tall enough that Camera's real content (3 stacked bands, see
    # camera_control.py) fits its content area with room to spare -- verified
    # directly: a 0.6 fraction leaves Camera's content area 9px too short at
    # this plan's own default panel size, a 0.85 fraction leaves 11px margin.
    modal_card_height = round(panel_height * 0.85)
    for label in subsystems:
        if label == "Camera":
            def content_builder(x, y, width, height, z_index, _presets=camera_presets):
                return camera_control.build_camera_control(
                    sdk, x=x, y=y, width=width, height=height, z_index=z_index,
                    resolution=resolution, presets=_presets, active_font=active_font)
        else:
            def content_builder(x, y, width, height, z_index):
                return "", "", []
        widget_id, widget_attrs, html, css, elements = modal.build_modal_widget(
            sdk, widget_width=panel_width, widget_height=panel_height,
            widget_name=f"{label} Modal", title=label, card_width=modal_card_width,
            card_height=modal_card_height, content_builder=content_builder,
            resolution=resolution, active_font=active_font,
        )
        modal_widgets[label] = (widget_id, widget_attrs, html, css, elements)

    # --- splash page: caller-supplied action tiles, may be empty --------------------
    splash_page_attrs = build_page_attributes(name="Splash", is_start_page=True)
    splash_parts: list[tuple[str, str, Element]] = []
    if splash_tiles:
        tile_positions = _layout_tabbed_row(len(splash_tiles), panel_width, panel_height)
        for (label, icon_class), (x, y, w, h) in zip(splash_tiles, tile_positions):
            html, css, element = component.build_component(
                sdk, "ch5-button", component_name=f"Splash {label}", element_id=generate_element_id(),
                x=x, y=y, width=w, height=h, z_index=1, resolution=resolution,
                active_font=active_font, label=label, icon_class=icon_class,
                icon_library="FA Classic Solid",
            )
            splash_parts.append((html, css, element))
    splash_html = "".join(h for h, _, _ in splash_parts)
    splash_css = "".join(c for _, c, _ in splash_parts)
    splash_elements = [e for _, _, e in splash_parts]

    # --- main panel page: header/footer/tab-content/modal widget references ---------
    main_panel_attrs = build_page_attributes(name="Main Panel")
    main_panel_html = ""
    main_panel_elements: list[Element] = []
    widget_refs = [
        (header_widget_id, "Header"),
        (footer_widget_id, "Footer"),
        *[(wid, f"{mode} Content") for mode, (wid, *_rest) in tab_content_widgets.items()],
        *[(wid, f"{label} Modal") for label, (wid, *_rest) in modal_widgets.items()],
    ]
    for widget_id, widget_name in widget_refs:
        main_panel_html, main_panel_elements = add_widget_reference_to_page(
            sdk, main_panel_html, main_panel_elements, widget_id, widget_name)

    return {
        "splash_page": (splash_page_attrs, splash_html, splash_css, splash_elements),
        "main_panel_page": (main_panel_attrs, main_panel_html, "", main_panel_elements),
        "header_widget": (header_widget_id, header_widget_attrs, header_html, header_css, header_elements),
        "footer_widget": (footer_widget_id, footer_widget_attrs, footer_html, footer_css, footer_elements),
        "tab_content_widgets": tab_content_widgets,
        "modal_widgets": modal_widgets,
    }
```

- [ ] **Run the test to verify it passes:**

```bash
cd generator/_test_output && python tabbed_shell_test.py
```

Expected: every OK line prints, `Tabbed Shell: all assertions passed.` at the end.

- [ ] **Run the full existing suite to confirm no regressions:**

```bash
cd generator/_test_output && for f in *_test.py; do python "$f" || echo "FAIL: $f"; done
```

Expected: no `FAIL:` lines except the two known pre-existing unrelated failures.

- [ ] **Commit:**

```bash
git add generator/layout_patterns.py generator/_test_output/tabbed_shell_test.py
git commit -m "feat: add build_tabbed_shell (splash, 2-row header/tab-strip, footer, modals)"
```

- [ ] **Update `README.md`'s Log** (this project's hard rule) with what was
  built, what's confirmed vs. still a judgment call (band fractions, the
  header's 60/40 row split, footer zone thirds), and that this is now
  available for a live-project regeneration if the user wants to see it in
  Construct next. Commit that too, same turn.

---

## After this plan

Not built here (explicitly deferred in the spec): real content for the Power/
Presentation/Video Call/Audio Call tab bodies; real content for the
Environment/Audio/Security/etc. modals (`lights_control.py`/`shades_control.py`/
`audio_control.py`/`security_control.py`, same tier as `camera_control.py`); the
residential Tabbed pass; HVAC subsystem composite. Also not resolved: how a tab
press or a footer button press actually gets wired to the right contract signal
in the control system (this generator's job per `ConstructUISkill.md` §6 is to
expose correctly-named signals, not program control-system logic) — worth a live
Construct check once this shell is regenerated, same as every other unverified-
in-the-real-editor mechanism this project has shipped. If the user wants any of
these next, each is its own real scope question needing its own brainstorming
pass, not a silent extension of this plan.
