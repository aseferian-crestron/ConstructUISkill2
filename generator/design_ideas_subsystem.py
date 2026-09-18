"""
Subsystem popup authoring for the DESIGN IDEAS TEMPLATE ONLY -- Header-Content-
Footer's own subsystem control surface (Lights/Shades/Climate/...), reachable
from a persistent footer menu via the same Visibility=Contract widget-toggle
mechanism this project already uses everywhere (ConstructUISkill.md §5).

Every constant below is transcribed from `docs/DesignIdeasTemplate.md` §2
(the template's own documented custom-style values), NOT guessed and NOT
learned by inspecting a donor sample file. This module intentionally does
NOT read, clone, or fall back to any existing project file -- everything is
built from scratch via this project's own schema-grounded primitives
(component.py/html_div.py/palette.py/typography.py), the same "template-
independent mechanics, template-specific values" split every other layout-
pattern module in this project already follows. The `design_ideas_` prefix
on every public function exists for the same reason the old (now retired)
v1 skill used it: these VALUES are specific to this one template's own
documented design language and are never safe to assume for a project that
didn't start from it -- see `C:\\ClaudeProjects\\ConstructUISkill\\
design_ideas_subsystem.py` (the old, donor-cloning v1 implementation this
module replaces, kept there only as a values/behavior reference, never
imported from here).

Per DesignIdeasTemplate.md §1 ("all components should be set to theme mode
... unless part of the use case defined in the Custom Style values section"):
this module is deliberately NOT uniform. The icon button uses the template's
own named "Info" theme style (`type="info"`, still theme mode -- a real,
confirmed `type` attribute value, not a custom color). The close button and
the two container divs use the doc's own literal custom values (§2). Ordinary
GROUP CONTROL buttons are left in THEME MODE (`customvstheme="theme"`,
`type="default"`) with no palette.apply_palette call at all -- deliberately,
per the doc's own default rule -- so they inherit whatever the project's real
theme defines, not a value this module invents.

Header (icon + title + close) + N groups laid out left-to-right and
centered, each a bordered group container with its own title. A group's
content is normally a plain list of theme-mode control buttons stacked
vertically, or one of the marker types below for a different shape in the
same frame -- D-pad cross (DpadGroup/design_ideas_dpad_group()), scrollable
contract-driven list (ButtonListGroup/design_ideas_button_list_group()), or
numeric keypad (KeypadGroup/design_ideas_keypad_group()) -- each grounded
against v1's own already-learned real measurement or (for the keypad/
button-list, both native CH5 components) this project's own schema-grounded
component.py. An optional `message=` on the popup builder adds a
warning/alert-dialog shape (header + message + Close, `groups=[]`). NOT yet
built: the "-More" secondary popup shape v1 also supported (a second,
linked popup for overflow controls).
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import re
from pathlib import Path

import component
import contracts
import layout
import palette
import shape
import spacing
import typography
from elements import Element
from html_div import build_html_div
from page import (
    add_widget_reference_to_page, build_page_attributes, build_widget_attributes,
    default_widget_html_css, generate_element_id, make_widget_reference,
    widget_reference_position_css,
)
from sdk import UiSdk

# --- DesignIdeasTemplate.md §2, transcribed verbatim -------------------------------

#: "Default Font Family for all text in the project: Quicksand-VaribaleFont_wght"
#: -- the doc's own stated value. NOT used as this module's default: the old v1
#: implementation's own FONT_FAMILY constant (design_ideas_subsystem.py, which
#: this module replaces) was "Roboto" instead, with no comment explaining the
#: discrepancy -- since that value shipped in v1's real, presumably live-tested
#: code while the doc's value was never independently confirmed rendering,
#: DEFAULT_FONT follows the code, not the doc. Callers with a project that
#: really does carry the Quicksand webfont can override via `active_font`.
DEFAULT_FONT = "Roboto"

ICON_SIZE = (68, 72)  # "Subsystem Controls Popup - Icon"
CLOSE_SIZE_SUBSYSTEM = (68, 72)  # "Subsystem Controls Popup - Close"
CLOSE_SIZE_DEVICE = (84, 72)  # "Device Controls - Close"

#: Header title's own real fixed width -- confirmed directly against the real
#: `Popup - SubsystemTemplate.cuiw` (C:\Solutions\CrestronDesignIdeas\
#: BasicTemplate_v1_0_2, 2026-09-18, user: "to determine the sub system widget
#: size and layout, you can reference the Popup - SubsystemTemplate in the
#: design ideas project"): Subsystem_Title is left=67,width=333 -- a FIXED
#: box, not stretched to fill the gap up to the close button (this module's
#: earlier `panel_width - icon_w - close_w` computation was wrong, found and
#: fixed while grounding against this real file).
TITLE_WIDTH = 333

#: "Subsystem Controls Popup - Container DIV"
CONTAINER_FILL = "rgba(137, 137, 137, 0.11)"
CONTAINER_BORDER = "rgba(192, 192, 192, 0.5)"
CONTAINER_BORDER_WIDTH = 1
CONTAINER_RADIUS = 20

#: "Generic Group Controls - Container DIV"
GROUP_FILL = "rgba(255, 255, 255, 0)"
GROUP_BORDER = "rgba(192, 192, 192, 0.5)"
GROUP_BORDER_WIDTH = 1
GROUP_RADIUS = 10

DEFAULT_BUTTON_SIZE = (157, 75)
LARGE_BUTTON_SIZE = (250, 75)

#: "Formatted Text - Subsystem Title" / "- Control Group Title" / "- Generic
#: Text Label" all share this color; only font-size differs (title/group 28
#: and 26 respectively -- Generic Text Label's own 26 is not used by this
#: module yet, no generic-label content shape exists here).
TEXT_COLOR = "rgba(255, 255, 255, 0.95)"
TITLE_FONT_SIZE = 28
GROUP_TITLE_FONT_SIZE = 26

#: Real measured layout geometry, transcribed from v1's own already-learned
#: constants (design_ideas_subsystem.py's ST_* names) -- v1 arrived at these
#: by inspecting the template's real sample files directly, a fact-finding
#: step this module doesn't need to repeat. Judgment calls beyond this point
#: (how they compose for an arbitrary N-group/M-button layout) are this
#: module's own, not the template's.
GROUP_WIDTH = 291
GROUP_TOP = 119
GROUP_GAP = 40  # horizontal gap between side-by-side groups
GROUP_PAD_TOP = 17  # gap from group top to its first control
CONTROL_INSET = 20  # control's left inset within its group
CONTROL_STEP = 86  # vertical step between stacked controls in a group
#: Bottom margin below a group's own last control, before Group_Container's
#: own border -- a judgment call (no real multi-height reference exists to
#: measure this from), mirroring GROUP_PAD_TOP's top margin for visual
#: symmetry. Group_Container's height is sized to CONTENT (GROUP_PAD_TOP +
#: content height + this), never the popup's full available height -- found
#: live, 2026-09-18 (user, from a real screenshot of a 4-button "Pool" group
#: beside a 2-button "Filter" group): both boxes were stretched to the
#: popup's full height regardless of how many controls were actually
#: inside, leaving a large empty band below the real content in both.
GROUP_BOTTOM_PAD = GROUP_PAD_TOP

#: Group_Title's own real position -- confirmed directly against
#: `Popup - SubsystemTemplate.cuiw` (see TITLE_WIDTH's comment above): the
#: title sits ABOVE Group_Container entirely (top=78, height=39, ending at
#: 117 -- just 2px before the container's own top at GROUP_TOP=119), not
#: overlapping the container's own top edge as this module's earlier
#: `y=GROUP_TOP` placement assumed (found and fixed alongside TITLE_WIDTH).
GROUP_TITLE_TOP = 78
GROUP_TITLE_HEIGHT = 39


# --- Extra group CONTENT shapes -- D-pad cross / button-list / keypad ----------------
# A group's `labels` value is normally a plain `list[str]` (stacked theme-mode
# buttons, the original first-pass scope -- see module docstring above). Passing one
# of the small marker instances below instead renders a DIFFERENT content shape in
# the SAME Group_Container/Group_Title frame -- construct with
# design_ideas_dpad_group()/design_ideas_button_list_group()/
# design_ideas_keypad_group(), never instantiated directly.

@dataclass(frozen=True)
class DpadGroup:
    """Marker: render a D-pad cross (Up/Down/Left/Right/Ok) instead of stacked
    buttons. Build with `design_ideas_dpad_group()`."""


@dataclass(frozen=True)
class ButtonListGroup:
    """Marker: render one scrollable, contract-driven `ch5-button-list`
    (Construct's native list component) instead of stacked buttons -- e.g. "show a
    list of recordings/favorites/presets". Build with
    `design_ideas_button_list_group(num_items)`. `num_items` is the authored slot
    count; which ones are populated/visible at runtime is a contract concern
    (`pd-receivestatenumberofitems`), not this module's."""
    num_items: int


@dataclass(frozen=True)
class KeypadGroup:
    """Marker: render a numeric `ch5-keypad` (Construct's native 13-button keypad,
    a fixed child set -- see component.py::KEYPAD_KEYS) instead of stacked buttons.
    Build with `design_ideas_keypad_group()`. `display=True` adds a contract-driven
    readout row above the keypad for the digits typed so far."""
    display: bool = False


def design_ideas_dpad_group() -> DpadGroup:
    """Build a group entry that renders as a D-pad cross -- pass directly as a
    group's control value, e.g. `("Navigation", design_ideas_dpad_group())`."""
    return DpadGroup()


def design_ideas_button_list_group(num_items: int) -> ButtonListGroup:
    """Build a group entry that renders as one scrollable `ch5-button-list` --
    pass directly as a group's control value, e.g.
    `("Recordings", design_ideas_button_list_group(10))`."""
    return ButtonListGroup(num_items)


def design_ideas_keypad_group(display: bool = False) -> KeypadGroup:
    """Build a group entry that renders as a numeric keypad -- pass directly as a
    group's control value, e.g. `("Code Entry", design_ideas_keypad_group(display=True))`."""
    return KeypadGroup(display)


#: D-pad cross (DesignIdeasTemplate.md §5: "the custom Dpad component ... located
#: in the All Components page ... a collection of individual button objects" --
#: NOT the native `<ch5-dpad>` web component, which is a different, single atomic
#: component with its own fixed internal 5-button layout, confirmed via
#: component.py's own DPAD_KEYS/build_children and already used elsewhere in this
#: project for a DIFFERENT design system, camera_control.py's Position control).
#: This template's own bespoke Dpad is 5 separate custom-styled ch5-button
#: elements in a cross plus a 6th decorative theme-mode background circle --
#: geometry and CSS transcribed VERBATIM from v1's own already-learned real
#: measurement (v1 read `Controls - Apple TV.cuiw`'s real Dpad_* components
#: directly; this module does not re-measure, matching this file's existing
#: "real measured layout geometry, transcribed from v1's own already-learned
#: constants" precedent already used for the footer above).
DPAD_KEYS = ("Up", "Down", "Left", "Right", "Ok")
DPAD_BTN_SIZE = 86
DPAD_ICON_LIBRARY = "FA Classic Solid"
DPAD_ICONS = {
    "Up": "fa-solid fa-chevron-up", "Down": "fa-solid fa-chevron-down",
    "Left": "fa-solid fa-chevron-left", "Right": "fa-solid fa-chevron-right",
}
#: (dx, dy) of each button's top-left relative to Ok's top-left -- NOT a
#: symmetric grid (Up's offset differs from Down's), preserved exactly as v1
#: measured it, not idealized into a "clean" grid.
DPAD_OFFSETS = {"Ok": (0, 0), "Up": (0, -92), "Down": (0, 96), "Left": (-96, 0), "Right": (96, 0)}
DPAD_CROSS_W = 96 + DPAD_BTN_SIZE + 96
DPAD_CROSS_H = 92 + DPAD_BTN_SIZE + 96
#: A 6th real component: a circular BACKGROUND plate sitting behind the 5-button
#: cross (real componentname is just "Button" in Controls - Apple TV.cuiw --
#: generic/unnamed since it's decorative -- named "Dpad_Background" here for
#: clarity). THEME mode (not custom like the 5 foreground buttons) --
#: `type="default"` matches "Default/Regular Style: Common Buttons" per
#: DesignIdeasTemplate.md §2. No icon, no label.
DPAD_BG_SIZE = 281
DPAD_BG_OFFSET = (-98, -95)  # (dx, dy) of the background's top-left relative to Ok's
#: Real measured custom style (Dpad_Up's own rule): gray border, transparent
#: fill, light overlay + darker icon/label on press/select -- distinct from
#: DPAD_BG's theme-mode look, since it's a genuinely different use case with its
#: own real data. Passed through palette.derive_states (pressed_border_color/
#: pressed_border_width/selected_border_color/selected_border_width are all
#: identical to normal in the real file, so they're left for derive_states'
#: own "copy unchanged" default rather than repeated here).
DPAD_BUTTON_PALETTE: dict[str, str] = {
    "background_color": "rgba(137, 137, 137, 0)",
    "border_color": "rgb(137, 137, 137)",
    "border_width": "0px",
    "text_color": "rgba(255, 255, 255, 0.95)",
    "icon_color": "rgba(255, 255, 255, 0.95)",
    "pressed_background_color": "rgba(255, 255, 255, 0.22)",
    "pressed_text_color": "rgba(82, 82, 82, 0.9)",
    "pressed_icon_color": "rgba(82, 82, 82, 0.9)",
    "selected_background_color": "rgba(255, 255, 255, 0.22)",
    "selected_text_color": "rgba(82, 82, 82, 0.9)",
    "selected_icon_color": "rgba(82, 82, 82, 0.9)",
}

#: Numeric keypad -- ch5-keypad is a native, fully schema-covered component
#: (component.py's own KEYPAD_KEYS/build_children already emit its real 13-button
#: child set; writes_css_size already emits `height: auto` for it, since it's
#: aspect-locked from width alone -- see component.py::is_aspect_locked). This
#: module only needs to place ONE ch5-keypad plus an optional contract-driven
#: digits readout above it -- no per-key geometry to hand-author, unlike the
#: D-pad above (whose "custom Dpad" is 5 separate buttons, not one atomic
#: component -- see DPAD_KEYS's own comment for why these two are NOT the same
#: kind of control despite both being directional/numeric input).
KEYPAD_SLOT_WIDTH = 267  # v1's own already-learned real ch5-keypad rendered width
KEYPAD_DISPLAY_HEIGHT = 40
KEYPAD_DISPLAY_GAP = spacing.SPACING_UNIT
KEYPAD_DISPLAY_FONT_SIZE = 32

#: Optional "Message" text -- a second, contract-driven multi-line text element
#: below the header, spanning most of the canvas width -- used for warning/alert
#: dialogs (a header + message + Close, no control groups at all) as well as an
#: optional addition to an ordinary subsystem popup. `title`'s own text ALSO
#: carries `pd-receivestatescriptlabelhtml="Contract Enabled"` by default (every
#: ch5-text component.py builds already does, via ComponentProfile("Formatted-
#: Text", ...)), so making the message dynamic needs no extra wiring either.
MESSAGE_TOP = 90
MESSAGE_MARGIN_X = 40
MESSAGE_MARGIN_BOTTOM = 40
MESSAGE_FONT_SIZE = 26  # DesignIdeasTemplate.md §2 "Formatted Text - Generic Text Label"


# --- PAGE-level geometry, transcribed from a real subsystem page's own CSS -----------
# (C:\Solutions\ClaudeGenTest\DesignIdeasCopy\Lights.cuig, primary 1280x800 block,
# 2026-09-18) -- a subsystem page is NOT just "Header/Footer/Popup widget refs":
# it also carries its own per-page Background ch5-image (full canvas, contract-
# driven URL -- confirmed real, `pd-receivestateurl="Contract Enabled"`, matching
# EVERY page's own image, not a shared widget) and its own "CenterDIV" html-div,
# a semi-transparent black backdrop confined to the header-to-footer band (NOT
# the full canvas -- the header and footer stay undimmed above/below it, only
# the content strip between them dims when a popup is open, confirmed via real
# z-index order: Background(60) < Header(62) < CenterDIV(64) < Footer(66) <
# Footer-Volume(98) < the actual popup content(113+), so the popup itself
# floats above its own backdrop, and the backdrop floats above the header but
# BELOW the footer).
PAGE_HEADER_HEIGHT = 104
PAGE_FOOTER_HEIGHT = 80
PAGE_BACKDROP_COLOR = "rgba(0, 0, 0, 0.62)"
#: Popup canvas size + position within the page -- the real file's own
#: measured values (matches v1's already-learned CANVAS_LANDSCAPE_W/H),
#: centered horizontally in a 1280px canvas (116px each side) and vertically
#: within the header-to-footer band with a small bottom margin (matches the
#: real file's own 121px top / ~9px bottom gap before the footer, not a
#: perfect mathematical center).
POPUP_CANVAS_WIDTH = 1048
POPUP_CANVAS_HEIGHT = 590
POPUP_LEFT = 116
POPUP_TOP = 121

# --- Footer subsystem-icon GROUPS, transcribed from the real Footer - Main.cuiw's ---
# own catch-all CSS (C:\Solutions\ClaudeGenTest\DesignIdeasCopy, 2026-09-18) -- the
# footer's subsystem icons are laid out in NAMED GROUPS separated by a vertical
# divider bar, confirmed directly (user, 2026-09-18): "Power, Environment, Call,
# Settings" -- Environment={Lights, Shades}, Call={Camera, Phone, VideoCall},
# Settings={Audio}. Real measured rhythm (every value below is a DIRECT
# measurement, not a guess): each button 87x70 (top=5); each divider 3px wide x
# 60 tall (top=10); a 6px gap between two buttons in the SAME group; a 10px gap
# on BOTH sides of every divider (button-to-divider and divider-to-button). The
# footer starts at x=10. A subsystem added to or removed from a group must
# recompute every FOLLOWING element's x position from this same rhythm -- a
# stale gap (or an over/under-sized one) is exactly the live bug report this
# fixes ("you need to adjust the spacing in the footer to account for the
# removal of the sub system icon from a group").
FOOTER_BUTTON_WIDTH = 87
FOOTER_BUTTON_HEIGHT = 70
FOOTER_BUTTON_TOP = 5
FOOTER_DIVIDER_WIDTH = 3
FOOTER_DIVIDER_HEIGHT = 60
FOOTER_DIVIDER_TOP = 10
FOOTER_WITHIN_GROUP_GAP = 6
FOOTER_GROUP_GAP = 10
FOOTER_START_X = 10

#: (subsystem label -> its real Footer - Main.cuiw componentName) -- the
#: template's own naming (`Menu_Lights`, not `Menu_lights` or `Lights`,
#: confirmed directly against the real file). A caller adding/removing by
#: subsystem label (e.g. "Lights") needs this to find/build the matching
#: `Menu_*` button.
FOOTER_DEFAULT_GROUPS: list[list[str]] = [
    ["Power"], ["Lights", "Shades"], ["Camera", "Phone", "VideoCall"], ["Audio"],
]


#: Portrait rhythm -- transcribed from the SAME real Footer - Main.cuiw's
#: portrait media query block (2026-09-18). Structurally DIFFERENT from
#: landscape, not just different numbers: buttons stack VERTICALLY (fixed
#: left=7, varying top) and each divider ROTATES to a horizontal bar
#: (80x3, not 3x60). The gap is 12px EXCEPT the very first one (Power to
#: DividerGroup1, measured 10px, confirmed a real, consistent 2px offset
#: -- not noise: every position downstream was off by exactly the same
#: 2px until this was special-cased) -- treated as the template's own
#: one-time original-authoring quirk on that first gap specifically, not a
#: second general rule. Privacy_Mute (and the divider before it,
#: DividerGroup4) is
#: NOT part of this rhythm in portrait at all -- confirmed directly: it
#: sits at top=728 with ~376px of empty space below it in a 1174px-tall
#: widget, not flush with the bottom and not reachable by extending the
#: rhythm (would land around y=642, not 728). User confirmed (2026-09-18):
#: leave it fixed, never reflow it -- this function stops after the last
#: subsystem group and does not place Privacy_Mute or its divider at all;
#: a caller writing the file leaves those two elements completely
#: untouched regardless of what `groups` contains.
FOOTER_PORTRAIT_BUTTON_LEFT = 7
FOOTER_PORTRAIT_DIVIDER_LEFT = 10
FOOTER_PORTRAIT_DIVIDER_WIDTH = 80
FOOTER_PORTRAIT_DIVIDER_HEIGHT = 3
FOOTER_PORTRAIT_GAP = 12
FOOTER_PORTRAIT_START_Y = 14


def _internal_divider_name(gi: int) -> str:
    """Real componentName for the divider BEFORE group index `gi` (1-based
    among non-empty groups) in a reflow-managed layout -- `DividerGroup{gi}`,
    the template's own real sequential naming for the 3 original internal
    dividers (DividerGroup1/2/3 sit between the 4 original subsystem
    groups). `DividerGroup4` itself is NEVER produced here -- it is the
    real, DIFFERENT, permanently-fixed divider immediately before
    Privacy_Mute (see the module note above the footer-editing section),
    already present in every real file this module writes to and never
    touched by it. A 4th INTERNAL divider (a 5th subsystem group) would
    naturally fall at this same sequential number -- found live, 2026-09-18
    (user: pointed out real, visible empty footer space after a removal
    freed room for a 5th group, correctly rejecting an earlier version of
    this module that refused ANY 5th group outright over exactly this name
    collision) -- so `gi==4` skips straight to `DividerGroup5` and every
    index beyond it shifts by one, permanently reserving the literal number
    4 for Privacy_Mute's own divider. Whether a 5th (or 6th, ...) group
    actually FITS before Privacy_Mute is a real physical question this
    function has no opinion on -- see `design_ideas_write_footer_groups`'s
    own `overflow` report, the mechanism that already exists to catch
    exactly that."""
    return f"DividerGroup{gi if gi < 4 else gi + 1}"


def design_ideas_footer_layout_portrait(
    groups: list[list[str]],
) -> list[tuple[str, str, int]]:
    """Portrait-orientation sibling of `design_ideas_footer_layout` --
    `(name, kind, y)` for every subsystem button/divider, stacked vertically
    (all buttons share `FOOTER_PORTRAIT_BUTTON_LEFT`, all dividers share
    `FOOTER_PORTRAIT_DIVIDER_LEFT`, a caller writing CSS positions each
    accordingly). Privacy_Mute and its divider are deliberately NOT
    produced here -- see the module comment above `FOOTER_PORTRAIT_GAP`.
    """
    non_empty = [g for g in groups if g]
    layout: list[tuple[str, str, int]] = []
    y = FOOTER_PORTRAIT_START_Y
    for gi, group in enumerate(non_empty):
        if gi > 0:
            # The very first gap (before DividerGroup1) measures 10px in
            # the real file, every subsequent one 12px -- see the module
            # comment above FOOTER_PORTRAIT_GAP.
            y += 10 if gi == 1 else FOOTER_PORTRAIT_GAP
            layout.append((_internal_divider_name(gi), "divider", y))
            y += FOOTER_PORTRAIT_DIVIDER_HEIGHT + FOOTER_PORTRAIT_GAP
        for bi, name in enumerate(group):
            if bi > 0:
                y += FOOTER_PORTRAIT_GAP
            layout.append((name, "button", y))
            y += FOOTER_BUTTON_HEIGHT
    return layout


def design_ideas_footer_layout(
    groups: list[list[str]],
) -> list[tuple[str, str, int]]:
    """`(name, kind, x)` for every button/divider in `groups`, left to right,
    using the real measured rhythm above -- `kind` is `"button"` or
    `"divider"`. One divider is placed between every pair of CONSECUTIVE
    groups (never before the first or after the last), named via
    `_internal_divider_name` -- NOT capped at the real template's original 4
    groups; any number of groups is accepted here (a real footer that
    doesn't physically fit them all before Privacy_Mute is a separate
    concern, caught by `design_ideas_write_footer_groups`'s own `overflow`
    report, not this function's). Privacy_Mute's OWN fixed divider (real
    name "DividerGroup4", separating the last subsystem group from
    Privacy_Mute in the original template) is never placed here at all --
    Privacy_Mute isn't a subsystem, callers that need it position it
    themselves at the x this function's own return value ends on.

    A group with zero items is skipped entirely (no empty group, no orphan
    divider before/after it) -- this is what makes removing the LAST item
    from a group correctly close the resulting gap rather than leaving a
    divider next to nothing.
    """
    non_empty = [g for g in groups if g]
    layout: list[tuple[str, str, int]] = []
    x = FOOTER_START_X
    for gi, group in enumerate(non_empty):
        if gi > 0:
            x += FOOTER_GROUP_GAP
            layout.append((_internal_divider_name(gi), "divider", x))
            x += FOOTER_DIVIDER_WIDTH + FOOTER_GROUP_GAP
        for bi, name in enumerate(group):
            if bi > 0:
                x += FOOTER_WITHIN_GROUP_GAP
            layout.append((name, "button", x))
            x += FOOTER_BUTTON_WIDTH
    return layout


_GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


def design_ideas_learn_project_shared(project_dir: Path) -> dict[str, str]:
    """Read an EXISTING subsystem page in `project_dir` (any `.cuig` carrying
    the template's own real refs -- confirmed identical across every real
    subsystem page checked, e.g. Lights.cuig/Camera.cuig both reference the
    SAME Header/Footer/Footer-Volume-Percent widget GUIDs and the SAME
    Background asset GUID) to learn the project's own shared identifiers, so
    a new page can reference the SAME instances rather than inventing new
    ones -- this is a READ, not a clone (see module docstring: cloning a
    donor file is what this module replaces; reading an already-COPIED
    project's own real, already-GUID-reconciled content to stay consistent
    with it is a different, safe operation).

    Returns `{"header_widget_id", "header_widget_name", "footer_widget_id",
    "footer_widget_name", "volume_widget_id", "volume_widget_name",
    "background_asset_id"}`. Raises `ValueError` if no `.cuig` in
    `project_dir` carries all of these (not a Design-Ideas-derived project,
    or the template's own naming has changed).
    """
    patterns = {
        "header": re.compile(r'templateid="w(' + _GUID + r')"[^>]*ccid_widgetname="(Header)"'),
        "footer": re.compile(r'templateid="w(' + _GUID + r')"[^>]*ccid_widgetname="(Footer - Main)"'),
        "volume": re.compile(r'templateid="w(' + _GUID + r')"[^>]*ccid_widgetname="(Footer - Volume Percent)"'),
        "background": re.compile(r'<ch5-image\b[^>]*componentname="Background"[^>]*>'),
    }
    for page_path in sorted(Path(project_dir).glob("*.cuig")):
        text = page_path.read_text(encoding="utf-8")
        html = text.split("{Html}", 1)[-1].split("{Css}", 1)[0]
        found: dict[str, str] = {}
        m = patterns["header"].search(html)
        if m:
            found["header_widget_id"], found["header_widget_name"] = m.group(1), m.group(2)
        m = patterns["footer"].search(html)
        if m:
            found["footer_widget_id"], found["footer_widget_name"] = m.group(1), m.group(2)
        m = patterns["volume"].search(html)
        if m:
            found["volume_widget_id"], found["volume_widget_name"] = m.group(1), m.group(2)
        m = patterns["background"].search(html)
        if m:
            asset_m = re.search(r'assetid="(' + _GUID + r')"', m.group(0))
            if asset_m:
                found["background_asset_id"] = asset_m.group(1)
        if len(found) == 7:
            return found
    raise ValueError(
        f"no .cuig in {project_dir} carries the Design Ideas template's own "
        f"Header/Footer/Footer - Volume Percent widget refs and Background "
        f"asset ref -- not a Design-Ideas-derived project"
    )


def design_ideas_build_subsystem_page(
    sdk: UiSdk, *, page_name: str, project_shared: dict[str, str],
    popup_widget_id: str, popup_widget_name: str,
    panel_width: int = 1280, panel_height: int = 800,
    resolution: tuple[int, int] | None = (1280, 800),
    footer_volume_position: tuple[int, int] = (922, 720),
) -> tuple[list[tuple[str, str]], str, str, list[Element]]:
    """One subsystem PAGE -- NOT just Header/Footer/Popup widget references
    (a page-level composition this module never needed before this fix, see
    module docstring above `PAGE_HEADER_HEIGHT`): its own per-page Background
    `ch5-image` (contract-driven URL, real assetid learned from the project
    via `design_ideas_learn_project_shared` -- NOT a shared widget, each
    page carries its own instance pointed at the same asset) + a
    semi-transparent "CenterDIV" backdrop confined to the header-to-footer
    band + Header/Footer/Footer-Volume-Percent widget REFERENCES (the
    project's own shared instances, from `project_shared`) + the new
    subsystem's own Popup widget reference, centered per `POPUP_LEFT`/
    `POPUP_TOP`.

    `footer_volume_position`: the real template's own observed (left, top)
    for the "Footer - Volume Percent" widget reference at a 1280x800 panel
    -- a directly measured constant (this sub-widget has no learnable
    width/height of its own, per `widget_reference_position_css`), not
    computed; override for a different panel size.

    Returns `(page_attrs, html, css, elements)`, ready for
    `page.py::write_cuig`. The `-More` secondary popup shape and the actual
    footer NAV BUTTON to reach this page are both explicitly out of scope
    here -- see README.md for why.
    """
    # Element ORDER here is the real, confirmed stacking mechanism Construct
    # actually uses (its Layer Manager, and real click hit-testing) --
    # FIRST in the list is FRONTMOST, LAST is BACKMOST. Confirmed two ways,
    # 2026-09-18: (1) a live screenshot of Construct's own Layer Manager on
    # a generated popup, showing an EARLIER version of this project's
    # backdrop container listed (and rendering) as the frontmost layer,
    # blocking every control beneath it; (2) the real `Lights.cuig`'s own
    # `[[Elements.Components]]` order, read directly: Popup(-More)/Popup,
    # Footer-Volume, Footer, CenterDIV, Header, Background -- Background
    # dead LAST. An EARLIER version of this function built Background
    # FIRST (the exact reverse), which would have made the full-canvas
    # background image the frontmost element, blocking the entire page --
    # z-index alone does NOT protect against this; list/append order is
    # what Construct's own layering actually keys off. Every build_*/
    # component.build_component call below is unchanged; only the ORDER
    # `parts.append` happens in changed, to build front-to-back like the
    # real file does.

    # --- the new subsystem's own Popup widget, centered (FRONTMOST) ----------------
    popup_html, popup_element = make_widget_reference(sdk, popup_widget_id, popup_widget_name)
    popup_id = dict(popup_element.attributes)["id"]
    popup_css = widget_reference_position_css(
        popup_id, x=POPUP_LEFT, y=POPUP_TOP, z_index=6, resolution=resolution)

    # --- Header/Footer/Footer-Volume-Percent: the project's own shared instances --
    volume_html, volume_element = make_widget_reference(
        sdk, project_shared["volume_widget_id"], project_shared["volume_widget_name"])
    volume_id = dict(volume_element.attributes)["id"]
    vol_x, vol_y = footer_volume_position
    volume_css = widget_reference_position_css(volume_id, x=vol_x, y=vol_y, z_index=5, resolution=resolution)

    footer_html, footer_element = make_widget_reference(
        sdk, project_shared["footer_widget_id"], project_shared["footer_widget_name"])
    footer_id = dict(footer_element.attributes)["id"]
    footer_css = widget_reference_position_css(
        footer_id, x=0, y=panel_height - PAGE_FOOTER_HEIGHT, z_index=4, resolution=resolution)

    # --- CenterDIV: semi-transparent backdrop, header-to-footer band only ---------
    backdrop_height = panel_height - PAGE_HEADER_HEIGHT - PAGE_FOOTER_HEIGHT
    cd_html, cd_css, cd_element = build_html_div(
        component_name="CenterDIV", element_id=generate_element_id(),
        x=0, y=PAGE_HEADER_HEIGHT, width=panel_width, height=backdrop_height, z_index=2,
        resolution=resolution, background_color=PAGE_BACKDROP_COLOR,
    )

    header_html, header_element = make_widget_reference(
        sdk, project_shared["header_widget_id"], project_shared["header_widget_name"])
    header_id = dict(header_element.attributes)["id"]
    header_css = widget_reference_position_css(header_id, x=0, y=0, z_index=3, resolution=resolution)

    # --- Background: per-page ch5-image, full canvas, contract-driven URL (BACKMOST)
    # pd-receivestateurl="Contract Enabled" -- confirmed real on every page's own
    # Background image (friendly name "Url", confirmed via contracts.
    # contract_signals -- NOT "Receive Serial Feedback URL", that's the
    # signal's CATEGORY, not its name). Drives a program-fed URL at runtime;
    # a static assetid alone gets silently overridden as long as this stays
    # bound, the same lesson v1's own design_ideas_set_background_image
    # already learned the hard way.
    bg_html, bg_css, bg_element = component.build_component(
        sdk, "ch5-image", component_name="Background", element_id=generate_element_id(),
        x=0, y=0, width=panel_width, height=panel_height, z_index=1, resolution=resolution,
        overrides={"assetid": project_shared["background_asset_id"]},
        contract_signals=("Url",),
    )

    parts: list[tuple[str, str, Element]] = [
        (popup_html, popup_css, popup_element),
        (volume_html, volume_css, volume_element),
        (footer_html, footer_css, footer_element),
        (cd_html, cd_css, cd_element),
        (header_html, header_css, header_element),
        (bg_html, bg_css, bg_element),
    ]

    page_attrs = build_page_attributes(name=page_name)
    html = "".join(h for h, _, _ in parts)
    css = "".join(c for _, c, _ in parts)
    elements = [e for _, _, e in parts]
    return page_attrs, html, css, elements


def _header_and_container(
    sdk: UiSdk, *, panel_width: int, panel_height: int, title: str,
    icon_class: str, icon_library: str, resolution: tuple[int, int] | None,
    active_font: str, close_size: tuple[int, int], message: str | None = None,
) -> tuple[list[tuple[str, str, Element]], tuple[str, str, Element], int]:
    """Icon + title + close (+ optional message) -- the fixed header pieces
    every subsystem/device-controls popup shares -- PLUS the Container_
    Controls backdrop, returned SEPARATELY so the caller can place it dead
    LAST overall (backmost). Returns `(content_parts, container_part,
    title_left)` -- `title_left` unused today (kept for a future caller that
    wants content to avoid the icon).

    Element ORDER matters for more than just visuals here -- see the note
    above `design_ideas_build_subsystem_page`'s own `parts` assembly: this
    was a real, confirmed live bug (Construct's Layer Manager treats FIRST
    in the components list as FRONTMOST, so a backdrop built first blocks
    everything drawn after it, regardless of its z-index). Confirmed exactly
    against the real `Popup - SubsystemTemplate.cuiw`'s own order: `Control,
    Group_Title, Group_Container, Controls_Close, Subsystem_Title,
    Subsystem_Icon, Container_Controls` -- Container_Controls dead LAST,
    which is why this function no longer builds it as its first part.

    `message` (optional): adds a second, contract-driven multi-line "Message"
    text element below the header, spanning most of the canvas width -- see
    MESSAGE_TOP's module comment. Used by warning/alert dialogs (header +
    message + Close, no control groups) as well as an optional addition to an
    ordinary subsystem popup."""
    parts: list[tuple[str, str, Element]] = []

    icon_w, icon_h = ICON_SIZE
    icon_html, icon_css, icon_element = component.build_component(
        sdk, "ch5-button", component_name="Subsystem_Icon", element_id=generate_element_id(),
        x=0, y=0, width=icon_w, height=icon_h, z_index=2, resolution=resolution,
        active_font=active_font, label="", icon_class=icon_class, icon_library=icon_library,
        overrides={"labelinnerhtml": "", "type": "info", "customvstheme": "theme"},
    )
    parts.append((icon_html, icon_css, icon_element))

    close_w, close_h = close_size
    title_left = icon_w
    # Fixed real width (TITLE_WIDTH=333), NOT stretched to fill the gap up to
    # the close button -- see TITLE_WIDTH's own comment.
    title_width = TITLE_WIDTH
    title_html, title_css, title_element = component.build_component(
        sdk, "ch5-text", component_name="Subsystem_Title", element_id=generate_element_id(),
        x=title_left, y=0, width=title_width, height=icon_h, z_index=2, resolution=resolution,
        active_font=active_font, label=title,
        overrides={"labelinnerhtml": title, "horizontalalignment": "left", "verticalalignment": "middle"},
    )
    title_id = dict(title_element.attributes)["id"]
    title_css = typography.apply_font_size(title_css, title_id, sdk, "ch5-text", TITLE_FONT_SIZE)
    title_css = palette.apply_palette(
        title_css, title_id, sdk, "ch5-text",
        palette.applicable_subset("ch5-text", palette.derive_states({"text_color": TEXT_COLOR})))
    parts.append((title_html, title_css, title_element))

    # Close: NOT theme mode -- DesignIdeasTemplate.md §2 names "Info Style"
    # for the icon only; the close button carries its own fixed custom look
    # (transparent background, white icon, every state) confirmed directly
    # in v1's own code comment ("Close: not a named theme style -- kept
    # CUSTOM with the real template's own fixed values").
    close_html, close_css, close_element = component.build_component(
        sdk, "ch5-button", component_name="Controls_Close", element_id=generate_element_id(),
        x=panel_width - close_w, y=0, width=close_w, height=close_h, z_index=2, resolution=resolution,
        active_font=active_font, label="", icon_class="fa-solid fa-xmark", icon_library="FA Classic Solid",
        overrides={"labelinnerhtml": ""},
    )
    close_id = dict(close_element.attributes)["id"]
    close_css = palette.apply_palette(
        close_css, close_id, sdk, "ch5-button",
        palette.applicable_subset("ch5-button", palette.derive_states({
            "background_color": "transparent",
            "pressed_background_color": "transparent",
            "selected_background_color": "transparent",
            "border_width": "0px",
            "icon_color": "#ffffff",
        })),
    )
    parts.append((close_html, close_css, close_element))

    if message is not None:
        msg_width = panel_width - 2 * MESSAGE_MARGIN_X
        msg_height = panel_height - MESSAGE_TOP - MESSAGE_MARGIN_BOTTOM
        msg_html, msg_css, msg_element = component.build_component(
            sdk, "ch5-text", component_name="Message", element_id=generate_element_id(),
            x=MESSAGE_MARGIN_X, y=MESSAGE_TOP, width=msg_width, height=msg_height,
            z_index=2, resolution=resolution, active_font=active_font, label=message,
            overrides={"labelinnerhtml": message, "horizontalalignment": "left",
                       "verticalalignment": "middle", "multilinesupport": "true"},
        )
        msg_id = dict(msg_element.attributes)["id"]
        msg_css = typography.apply_font_size(msg_css, msg_id, sdk, "ch5-text", MESSAGE_FONT_SIZE)
        msg_css = palette.apply_palette(
            msg_css, msg_id, sdk, "ch5-text",
            palette.applicable_subset("ch5-text", palette.derive_states({"text_color": TEXT_COLOR})))
        parts.append((msg_html, msg_css, msg_element))

    container_html, container_css, container_element = build_html_div(
        component_name="Container_Controls", element_id=generate_element_id(),
        x=0, y=0, width=panel_width, height=panel_height, z_index=1,
        resolution=resolution, background_color=CONTAINER_FILL,
        border_color=CONTAINER_BORDER, border_width=CONTAINER_BORDER_WIDTH,
        border_radius=CONTAINER_RADIUS,
    )
    container_part = (container_html, container_css, container_element)

    return parts, container_part, title_left


def _dpad_content(
    sdk: UiSdk, *, group_x: int, slot_width: int, content_top: int, available_height: int,
    resolution: tuple[int, int] | None, active_font: str, z_index: int,
) -> list[tuple[str, str, Element]]:
    """5-button cross + decorative background circle, centered within the
    given content box -- see the DPAD_* constants' own module comments above
    for the real measured geometry/style this reproduces."""
    parts: list[tuple[str, str, Element]] = []
    ok_left = group_x + (slot_width - DPAD_CROSS_W) // 2 + 96
    ok_top = content_top + (available_height - DPAD_CROSS_H) // 2 + 92

    bg_dx, bg_dy = DPAD_BG_OFFSET
    bg_html, bg_css, bg_element = component.build_component(
        sdk, "ch5-button", component_name="Dpad_Background", element_id=generate_element_id(),
        x=ok_left + bg_dx, y=ok_top + bg_dy, width=DPAD_BG_SIZE, height=DPAD_BG_SIZE,
        z_index=z_index, resolution=resolution, active_font=active_font, label="",
        overrides={"labelinnerhtml": "", "customvstheme": "theme", "type": "default"},
    )
    bg_id = dict(bg_element.attributes)["id"]
    bg_html, bg_css = shape.apply_radius_px(bg_html, bg_css, bg_id, sdk, "ch5-button", DPAD_BG_SIZE // 2)
    parts.append((bg_html, bg_css, bg_element))

    dpad_palette = palette.applicable_subset("ch5-button", palette.derive_states(dict(DPAD_BUTTON_PALETTE)))
    for key in DPAD_KEYS:
        dx, dy = DPAD_OFFSETS[key]
        label = "OK" if key == "Ok" else ""
        icon_class = DPAD_ICONS.get(key, "")
        btn_html, btn_css, btn_element = component.build_component(
            sdk, "ch5-button", component_name=f"Dpad_{key}", element_id=generate_element_id(),
            x=ok_left + dx, y=ok_top + dy, width=DPAD_BTN_SIZE, height=DPAD_BTN_SIZE,
            z_index=z_index + 1, resolution=resolution, active_font=active_font,
            label=label, icon_class=icon_class, icon_library=DPAD_ICON_LIBRARY if icon_class else "",
            overrides={"labelinnerhtml": label},
        )
        btn_id = dict(btn_element.attributes)["id"]
        btn_html, btn_css = shape.apply_radius_px(btn_html, btn_css, btn_id, sdk, "ch5-button", DPAD_BTN_SIZE // 2)
        btn_css = palette.apply_palette(btn_css, btn_id, sdk, "ch5-button", dpad_palette)
        parts.append((btn_html, btn_css, btn_element))
    return parts


def _button_list_content(
    sdk: UiSdk, *, group_x: int, slot_width: int, content_top: int, content_height: int,
    num_items: int, z_index: int, resolution: tuple[int, int] | None, active_font: str,
) -> list[tuple[str, str, Element]]:
    """One scrollable, contract-driven ch5-button-list filling the group's
    content area -- theme mode by default (ComponentProfile's own
    `vstheme="theme"` for this tag, no override needed, unlike ch5-button's
    own theme-mode fix elsewhere in this module)."""
    list_width = slot_width - 2 * CONTROL_INSET
    list_html, list_css, list_element = component.build_component(
        sdk, "ch5-button-list", component_name="Control_List", element_id=generate_element_id(),
        x=group_x + CONTROL_INSET, y=content_top, width=list_width, height=content_height,
        z_index=z_index, resolution=resolution, active_font=active_font,
        overrides={"numberofitems": str(num_items), "orientation": "vertical"},
    )
    return [(list_html, list_css, list_element)]


def _keypad_content(
    sdk: UiSdk, *, group_x: int, slot_width: int, content_top: int, display: bool,
    z_index: int, resolution: tuple[int, int] | None, active_font: str,
) -> list[tuple[str, str, Element]]:
    """One native ch5-keypad (its real 13-button child set comes for free
    from component.py's own build_children/KEYPAD_KEYS) plus an optional
    contract-driven digits readout above it."""
    parts: list[tuple[str, str, Element]] = []
    keypad_top = content_top
    if display:
        disp_html, disp_css, disp_element = component.build_component(
            sdk, "ch5-text", component_name="Keypad_Display", element_id=generate_element_id(),
            x=group_x, y=content_top, width=slot_width, height=KEYPAD_DISPLAY_HEIGHT,
            z_index=z_index, resolution=resolution, active_font=active_font, label="",
            overrides={"labelinnerhtml": "", "horizontalalignment": "center", "verticalalignment": "middle"},
        )
        disp_id = dict(disp_element.attributes)["id"]
        disp_css = typography.apply_font_size(disp_css, disp_id, sdk, "ch5-text", KEYPAD_DISPLAY_FONT_SIZE)
        disp_css = palette.apply_palette(
            disp_css, disp_id, sdk, "ch5-text",
            palette.applicable_subset("ch5-text", palette.derive_states({"text_color": TEXT_COLOR})))
        parts.append((disp_html, disp_css, disp_element))
        keypad_top = content_top + KEYPAD_DISPLAY_HEIGHT + KEYPAD_DISPLAY_GAP

    kp_html, kp_css, kp_element = component.build_component(
        sdk, "ch5-keypad", component_name="Control_Keypad", element_id=generate_element_id(),
        x=group_x, y=keypad_top, width=KEYPAD_SLOT_WIDTH, height=KEYPAD_SLOT_WIDTH,
        z_index=z_index, resolution=resolution, active_font=active_font,
    )
    parts.append((kp_html, kp_css, kp_element))
    return parts


def design_ideas_build_subsystem_popup(
    sdk: UiSdk, *, widget_name: str, title: str, icon_class: str,
    groups: list[tuple[str, list[str] | DpadGroup | ButtonListGroup | KeypadGroup]],
    panel_width: int, panel_height: int,
    icon_library: str = "FA Classic Solid", resolution: tuple[int, int] | None = None,
    active_font: str = DEFAULT_FONT, large_buttons: bool = False,
    device_controls: bool = False, message: str | None = None,
    widget_id: str | None = None, control_icons: dict[str, str] | None = None,
) -> tuple[str, list[tuple[str, str]], str, str, list[Element]]:
    """One subsystem (or, with `device_controls=True`, device controls) popup
    WIDGET -- icon + title + close header, then `groups` laid out left-to-
    right and centered below the header, each a bordered container with its
    own title and CONTENT. A group's control value is normally a plain
    `list[str]` (stacked theme-mode buttons, the original first-pass scope),
    or one of `DpadGroup`/`ButtonListGroup`/`KeypadGroup` (see their own
    docstrings and `design_ideas_dpad_group()`/`design_ideas_button_list_
    group()`/`design_ideas_keypad_group()`) for a different content shape in
    the same frame. Every value is DesignIdeasTemplate.md §2's own documented
    default, cross-checked directly against the real `Popup -
    SubsystemTemplate.cuiw` (see TITLE_WIDTH/GROUP_TITLE_TOP's own comments)
    -- entirely from scratch, no donor file read or cloned.

    Group control buttons are left in THEME MODE (no custom colors written)
    per the doc's own default rule -- they inherit the project's real theme.
    Every plain-list control EXPANDS to fill its group box's own width,
    centered with `CONTROL_INSET`'s margin on both sides (found live,
    2026-09-18: a fixed-width button left a large, uneven gap on the right
    only) -- `large_buttons` currently has no visible effect on width for
    that reason (DEFAULT_BUTTON_SIZE/LARGE_BUTTON_SIZE's height component,
    75px either way, is all that's still used; kept for API stability, not
    removed). Has no effect on a DpadGroup/ButtonListGroup/KeypadGroup,
    whose own controls have their own fixed/native sizing.

    `message` (optional): see `_header_and_container`'s own docstring -- a
    header + message + Close with `groups=[]` is a warning/alert dialog.

    `control_icons` (optional): `{label: "fa-solid fa-..."}` for any
    plain-list control that should carry a left-side icon alongside its
    label -- one ch5-button, icon+label together (`iconposition="first"` is
    already the real schema default), NOT the real template's own two-
    overlaid-buttons pattern (checked live, 2026-09-18, against the real
    `Popup - Lights.cuiw`, then explicitly told to skip it: "with support
    for icon and text offsets, you can handle this in a single component").
    The LABEL stays centered, unchanged -- only the ICON shifts, via its
    own real `margin-left` offset (`typography.apply_icon_offset`,
    Construct's own "Icon Styles > Horizontal Offset" property, confirmed
    live from a screenshot of that panel; an earlier version of this fix
    moved the whole button's `halignlabel` instead, which shifted the label
    too -- corrected per direct instruction: "leave the text centered"). A
    label not in this dict gets no icon, same as before. Only applies to
    plain-list controls (not Dpad/ButtonList/Keypad, whose own controls are
    built differently).

    `widget_id` (optional): pass the widget's OWN EXISTING real Id when
    regenerating a popup a page already references (e.g. fixing a real bug
    in its layout) -- a fresh one is used otherwise. Found necessary live,
    2026-09-18: rebuilding an existing `Popup - Pool.cuiw` with a fresh
    uuid4 (this function's previous unconditional behavior) orphaned the
    page's own already-written `templateid="w<old-id>"` reference, since
    nothing here read the file it was overwriting.

    Returns `(widget_id, widget_attrs, html, css, elements)` -- same shape as
    `modal.py::build_modal_widget`, ready for `page.py::write_cuig` and
    `page.py::add_widget_reference_to_page`. Raises ValueError if the groups
    don't fit within `panel_width`, or any group's content doesn't fit
    within `panel_height`.
    """
    close_size = CLOSE_SIZE_DEVICE if device_controls else CLOSE_SIZE_SUBSYSTEM
    widget_id = widget_id or str(uuid4())
    widget_attrs = build_widget_attributes(name=widget_name, widget_id=widget_id)
    root_html, root_css, root_element = default_widget_html_css(
        generate_element_id(), panel_width, panel_height, resolution, is_global=False)

    header_parts, container_part, _ = _header_and_container(
        sdk, panel_width=panel_width, panel_height=panel_height, title=title,
        icon_class=icon_class, icon_library=icon_library, resolution=resolution,
        active_font=active_font, close_size=close_size, message=message,
    )

    # A plain-list control's WIDTH is no longer DEFAULT_BUTTON_SIZE/
    # LARGE_BUTTON_SIZE's own fixed value -- found live, 2026-09-18 (user,
    # from a screenshot): buttons must EXPAND to fill their group box,
    # centered with a symmetric margin on both sides ("the left side gap is
    # a good margin" -- CONTROL_INSET -- applied to the right side too,
    # instead of a fixed-width button leaving a large uneven gap only on
    # the right). Computed per-group below instead (`width - 2 *
    # CONTROL_INSET`, `width` = that group's own slot_width). Only the
    # HEIGHT component of DEFAULT_BUTTON_SIZE/LARGE_BUTTON_SIZE is still
    # used -- both are 75px in the real doc, so `large_buttons` currently
    # has no visible effect (kept for API stability / a future real height
    # distinction, not removed).
    button_h = LARGE_BUTTON_SIZE[1] if large_buttons else DEFAULT_BUTTON_SIZE[1]
    group_height = panel_height - GROUP_TOP
    if group_height <= GROUP_PAD_TOP:
        raise ValueError(
            f"a {panel_height}px popup leaves no room for group content below "
            f"the {GROUP_TOP}px header/group-top offset"
        )

    def slot_width(labels) -> int:
        # KeypadGroup gets its own, wider slot (v1's own already-learned real
        # ch5-keypad rendered width, KEYPAD_SLOT_WIDTH=267, wider than the
        # standard 291px group minus its 2*20px control insets) -- every
        # other group type shares the standard GROUP_WIDTH slot.
        return KEYPAD_SLOT_WIDTH if isinstance(labels, KeypadGroup) else GROUP_WIDTH

    def content_height(labels) -> int:
        # Pure CONTENT height (no top/bottom padding) -- shared by the
        # too-tall check below and the actual Group_Container sizing, so the
        # two can never drift apart.
        if isinstance(labels, DpadGroup):
            return DPAD_CROSS_H
        if isinstance(labels, ButtonListGroup):
            # UNLIKE every other group type, a scrollable ch5-button-list's
            # own `numberofitems` does NOT need its own full stacked height
            # -- it scrolls, so filling the available box is the correct,
            # expected behavior for a scrollable component (more visible
            # rows before a scroll is needed), not wasted dead space the way
            # a fixed stack of individual buttons in an oversized box is.
            # Deliberately still uses the full remaining height, unlike the
            # content-fit sizing every other branch below now uses.
            return group_height - GROUP_PAD_TOP - GROUP_BOTTOM_PAD
        if isinstance(labels, KeypadGroup):
            # ch5-keypad's own true rendered height is unknown (native
            # component, aspect-derived from width -- see component.py's
            # writes_css_size) -- KEYPAD_SLOT_WIDTH used as a nominal
            # square-ish estimate for CONTAINER sizing purposes only, an
            # approximation flagged for live confirmation, not a measured
            # fact like DPAD_CROSS_H.
            extra = KEYPAD_DISPLAY_HEIGHT + KEYPAD_DISPLAY_GAP if labels.display else 0
            return extra + KEYPAD_SLOT_WIDTH
        return (len(labels) - 1) * CONTROL_STEP + button_h if labels else 0

    def needed_height(labels) -> int:
        return GROUP_PAD_TOP + content_height(labels) + GROUP_BOTTOM_PAD

    total_groups_width = (
        sum(slot_width(labels) for _title, labels in groups) + (len(groups) - 1) * GROUP_GAP
        if groups else 0
    )
    if total_groups_width > panel_width:
        raise ValueError(
            f"{len(groups)} groups don't fit within a {panel_width}px popup "
            f"({total_groups_width}px needed) -- fewer groups needed"
        )
    groups_left = (panel_width - total_groups_width) // 2

    group_parts: list[tuple[str, str, Element]] = []
    group_x = groups_left
    for group_title, labels in groups:
        width = slot_width(labels)
        needed = needed_height(labels)
        if needed > group_height:
            raise ValueError(
                f"group {group_title!r} needs {needed}px, but only {group_height}px "
                f"is available below the header -- fewer/smaller controls or a "
                f"taller popup needed"
            )

        # Sized to THIS group's own content (GROUP_PAD_TOP + content +
        # GROUP_BOTTOM_PAD), never the popup's full available height -- see
        # GROUP_BOTTOM_PAD's own comment. `needed` (already computed and
        # validated above) IS this height; reusing it keeps the two from
        # ever drifting apart.
        container_height = needed
        gc_html, gc_css, gc_element = build_html_div(
            component_name=f"Group_Container_{group_title}", element_id=generate_element_id(),
            x=group_x, y=GROUP_TOP, width=width, height=container_height, z_index=2,
            resolution=resolution, background_color=GROUP_FILL, border_color=GROUP_BORDER,
            border_width=GROUP_BORDER_WIDTH, border_radius=GROUP_RADIUS,
        )
        # NOT appended yet -- built here (needs `width`/`container_height`
        # computed in this scope) but appended dead LAST for this group,
        # after its title and content, matching the real confirmed order
        # (`Control, Group_Title, Group_Container` -- see
        # `_header_and_container`'s own docstring for the full finding).
        group_container_part = (gc_html, gc_css, gc_element)

        # Group_Title sits ABOVE Group_Container entirely (real measured
        # position, see GROUP_TITLE_TOP's own comment) -- NOT the first row
        # inside the container.
        gt_html, gt_css, gt_element = component.build_component(
            sdk, "ch5-text", component_name=f"Group_Title_{group_title}", element_id=generate_element_id(),
            x=group_x, y=GROUP_TITLE_TOP, width=width, height=GROUP_TITLE_HEIGHT,
            z_index=3, resolution=resolution, active_font=active_font, label=group_title,
            overrides={"labelinnerhtml": group_title, "horizontalalignment": "left"},
        )
        gt_id = dict(gt_element.attributes)["id"]
        gt_css = typography.apply_font_size(gt_css, gt_id, sdk, "ch5-text", GROUP_TITLE_FONT_SIZE)
        gt_css = palette.apply_palette(
            gt_css, gt_id, sdk, "ch5-text",
            palette.applicable_subset("ch5-text", palette.derive_states({"text_color": TEXT_COLOR})))
        group_parts.append((gt_html, gt_css, gt_element))

        content_top = GROUP_TOP + GROUP_PAD_TOP
        if isinstance(labels, DpadGroup):
            # The container is now sized to DPAD_CROSS_H exactly (see
            # content_height above), so the cross's own centering offset
            # within `available_height` is always zero -- pass its real
            # content height directly rather than the old shared/oversized
            # group_height.
            group_parts.extend(_dpad_content(
                sdk, group_x=group_x, slot_width=width, content_top=content_top,
                available_height=content_height(labels), resolution=resolution,
                active_font=active_font, z_index=3))
        elif isinstance(labels, ButtonListGroup):
            group_parts.extend(_button_list_content(
                sdk, group_x=group_x, slot_width=width, content_top=content_top,
                content_height=content_height(labels), num_items=labels.num_items,
                z_index=3, resolution=resolution, active_font=active_font))
        elif isinstance(labels, KeypadGroup):
            group_parts.extend(_keypad_content(
                sdk, group_x=group_x, slot_width=width, content_top=content_top,
                display=labels.display, z_index=3, resolution=resolution, active_font=active_font))
        else:
            # Expand to fill the group box, centered with CONTROL_INSET's
            # own margin on BOTH sides (not just the left) -- see the
            # comment above button_h's own definition.
            button_w = width - 2 * CONTROL_INSET
            for ci, label in enumerate(labels):
                # Theme mode ("Default/Regular Style: Common Buttons",
                # DesignIdeasTemplate.md §2) -- `overrides={"customvstheme":
                # "theme"}` was silently dropped for every ch5-button before
                # a real fix in component.py::build_component_attributes
                # (found while building this module: the ch5-button branch
                # delegated to `ch5_button.py::build_default_button_
                # attributes`, which has no `overrides` parameter at all, so
                # `overrides` never reached a button's attributes). Now
                # applies correctly.
                control_icon = (control_icons or {}).get(label)
                ctrl_html, ctrl_css, ctrl_element = component.build_component(
                    sdk, "ch5-button", component_name=label, element_id=generate_element_id(),
                    x=group_x + CONTROL_INSET, y=content_top + ci * CONTROL_STEP,
                    width=button_w, height=button_h, z_index=3, resolution=resolution,
                    active_font=active_font, label=label,
                    icon_class=control_icon or "", icon_library="FA Classic Solid" if control_icon else "",
                    overrides={"customvstheme": "theme", "type": "default"},
                )
                if control_icon:
                    # NO icon `margin-left` offset -- tried live, 2026-09-18,
                    # and the real render showed it does NOT move the icon
                    # independently of the label (as `apply_icon_offset`'s
                    # own selector-scoping assumed): icon and label are one
                    # flowing inline unit under `halignlabel`, so a large
                    # negative margin-left dragged BOTH flush against the
                    # left edge, leaving neither centered. Corrected per
                    # direct user feedback ("text is not centered and the
                    # icons are right against the left side"): apply ONLY
                    # `apply_icon_gap` (small, real, already-tested
                    # spacing between icon and label -- see typography.py)
                    # and leave `halignlabel` at its schema default
                    # (center), so the icon+label PAIR centers together as
                    # one readable unit -- not an independently-positioned
                    # icon, which this component doesn't actually support.
                    ctrl_id = dict(ctrl_element.attributes)["id"]
                    ctrl_css = typography.apply_icon_gap(ctrl_css, ctrl_id, sdk, "ch5-button", spacing.SPACING_UNIT)
                group_parts.append((ctrl_html, ctrl_css, ctrl_element))

        # Group_Container appended LAST for this group, behind its own
        # title and content -- see the note above where it was built.
        group_parts.append(group_container_part)

        group_x += width + GROUP_GAP

    # Front-to-back overall: every group's content (built front-to-back
    # already, see above), then the header pieces (icon/title/close/
    # message), then Container_Controls dead LAST -- matching the real
    # `Popup - SubsystemTemplate.cuiw` order exactly (see
    # `_header_and_container`'s own docstring for the full finding).
    all_parts = group_parts + header_parts + [container_part]
    html = root_html + "".join(h for h, _, _ in all_parts)
    css = root_css + "".join(c for _, c, _ in all_parts)
    elements = [root_element] + [e for _, _, e in all_parts]
    return widget_id, widget_attrs, html, css, elements


# --- Footer editing -- writing real reflowed positions into an existing --------------
# Footer - Main.cuiw, the piece SKILL.md flagged as "not done yet" and the user
# confirmed as the next priority ("yes, footer editing first", 2026-09-17).
#
# Grounded directly against the real footer file
# (C:\Solutions\ClaudeGenTest\DesignIdeasCopy\Footer - Main.cuiw), inspected structurally
# (not guessed) immediately before writing this code:
#
# - {PageAttributes} has exactly ONE top-level `[[Elements]]`, with every rendered
#   component as a nested `[[Elements.Components]]` sibling (flat buttons/dividers have
#   no children of their own -- component.py::build_children returns [] for ch5-button,
#   confirmed -- so a top-level sibling's span runs from its own `[[Elements.Components]]`
#   marker line to the NEXT one, found by an exact-line regex that does not also match
#   the deeper `[[Elements.Components.Components]]` some hand-authored buttons carry).
# - {Css} carries FOUR kinds of @media block for this widget: the catch-all
#   (`max-width: 99999px`, the canonical/source-of-truth values), a landscape block
#   matching the project's PRIMARY resolution (deltas only -- confirmed empty of any
#   button/divider rule in the reference file, matching layout.py::
#   update_element_declarations's own documented "only a delta from catch-all" rule), a
#   SECOND, non-primary landscape block that happens to fully duplicate catch-all's
#   button/divider values (left alone here except mirroring an existing delta, same as
#   the primary block -- never given a fresh entry for a brand-new element, since a new
#   element legitimately has no delta from catch-all yet), and exactly one portrait
#   block, structurally different (vertical stack, some dividers rotated 3x60->80x3) --
#   see design_ideas_footer_layout_portrait's own docstring.
# - Privacy_Mute and its own divider (DividerGroup4, whichever one immediately precedes
#   it) are NEVER touched by any function below, in either orientation -- matching the
#   user's own explicit, already-recorded decision ("leave it fixed, never reflow it")
#   and design_ideas_footer_layout('s own long-standing behavior of never producing
#   either name. A group's worth of buttons moving away from Privacy_Mute (e.g. removing
#   enough subsystems that Audio ends up far short of where DividerGroup4 used to sit)
#   is therefore a REAL, known gap this module does not paper over -- flag it to the
#   caller/user rather than inventing a new formula for a button explicitly decided to
#   be exempt from reflow.

FOOTER_DIVIDER_FILL = "rgba(255, 255, 255, 0.7)"
FOOTER_DIVIDER_BORDER_COLOR = "#ffffff"


def _read_sections(path: Path) -> tuple[str, list[list]]:
    """Same section-splitting rule as reflow.py's own local copy (see that module's
    docstring for why this is duplicated per-module rather than shared) -- kept as
    mutable `[name, header, content]` lists (not tuples) so a caller can rewrite one
    section's content in place before calling _write_sections."""
    section_re = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    matches = list(section_re.finditer(raw))
    preamble = raw[: matches[0].start()] if matches else raw
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        sections.append([m.group(1), m.group(0), raw[start:end]])
    return preamble, sections


def _write_sections(path: Path, preamble: str, sections: list[list]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(preamble + "".join(header + content for _, header, content in sections))


_TOP_COMPONENT_MARKER_RE = re.compile(r"^\[\[Elements\.Components\]\]\r?$", re.MULTILINE)


def _split_top_components(page_attrs_text: str) -> list[tuple[int, int, str]]:
    """(start, end, block_text) for each TOP-LEVEL `[[Elements.Components]]` sibling in
    page_attrs_text, found by an exact-line match so a deeper
    `[[Elements.Components.Components]]` (a component's own icon/label children, when
    present -- confirmed real for at least one hand-authored button in the reference
    file) is correctly treated as part of the PARENT's span, never a sibling boundary."""
    starts = [m.start() for m in _TOP_COMPONENT_MARKER_RE.finditer(page_attrs_text)]
    spans = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(page_attrs_text)
        spans.append((start, end, page_attrs_text[start:end]))
    return spans


_TOP_PAGE_ELEMENT_MARKER_RE = re.compile(r"^\[\[Elements\]\]\r?$", re.MULTILINE)


def _split_top_page_elements(page_attrs_text: str) -> list[tuple[int, int, str]]:
    """(start, end, block_text) for each top-level `[[Elements]]` block in a real
    PAGE's own PageAttributes -- the sibling of `_split_top_components`, for the
    OTHER real TOML shape this project writes: a page's own top-level elements each
    get their OWN `[[Elements]]` block directly (`page.py::write_cuig` calls
    `el.to_toml_lines("Elements")` for each), unlike a WIDGET's single `[[Elements]]`
    (the widgetContainer) with children nested as `[[Elements.Components]]`.
    Confirmed live, 2026-09-18: the real `Presentation.cuig` has 12 top-level
    `[[Elements]]` blocks, not one -- `_split_top_components` (built for widgets)
    found only 1 "component" in it, a real parsing bug found before it could write
    anything wrong."""
    starts = [m.start() for m in _TOP_PAGE_ELEMENT_MARKER_RE.finditer(page_attrs_text)]
    spans = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(page_attrs_text)
        spans.append((start, end, page_attrs_text[start:end]))
    return spans


def _component_name_and_id(block_text: str) -> tuple[str | None, str | None]:
    name_m = re.search(r'^componentName\s*=\s*"([^"]*)"', block_text, re.MULTILINE)
    id_m = re.search(r'^id\s*=\s*"([^"]*)"', block_text, re.MULTILINE)
    return (name_m.group(1) if name_m else None, id_m.group(1) if id_m else None)


def _all_media_queries(css_text: str) -> list[tuple[str, int, int]]:
    """(query_text, start, end) for EVERY `@media ...{...}` block in css_text, in
    document order -- same brace-depth walk as layout.py::find_all_media_block_spans,
    generalized to also return each block's own query text (that function only returns
    spans, not the query string, so it can't tell a portrait block from a landscape
    one)."""
    results: list[tuple[str, int, int]] = []
    idx = 0
    while True:
        idx = css_text.find("@media", idx)
        if idx == -1:
            break
        open_brace = css_text.find("{", idx + len("@media"))
        if open_brace == -1:
            break
        query = css_text[idx + len("@media"): open_brace].strip()
        depth = 0
        end = None
        for i in range(open_brace, len(css_text)):
            if css_text[i] == "{":
                depth += 1
            elif css_text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise ValueError(f"unterminated @media block starting at char {idx}")
        results.append((query, idx, end))
        idx = end
    return results


def _upsert_rule_in_block(css_text: str, query: str, element_id: str, declarations: dict[str, str]) -> str:
    """Update `element_id`'s own `#id{...}` rule inside the ONE block matching `query`
    exactly (merging into whatever declarations already exist there, same per-key merge
    semantics as layout.py::update_element_declarations) -- or, if that block has no
    rule for this id yet, insert a new one just before the block's own closing brace.

    Deliberately touches ONLY this one block, never the catch-all -- unlike
    update_element_declarations, which always ALSO writes the catch-all (correct for a
    primary-resolution delta, wrong here: a portrait-specific top/left must never leak
    into catch-all's landscape-canonical left/top for the same element)."""
    span = layout.find_media_block_span(css_text, query)
    if span is None:
        raise ValueError(f"no @media block for query {query!r} found")
    start, end = span
    id_pattern = re.compile(r"#" + re.escape(element_id) + r"\s*\{(?P<decls>[^{}]*)\}")
    m = id_pattern.search(css_text, start, end)
    if m is not None:
        decl_pairs: list[list[str]] = []
        for decl in m.group("decls").split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            key, _, value = decl.partition(":")
            decl_pairs.append([key.strip(), value.strip()])
        by_key = {pair[0]: pair for pair in decl_pairs}
        for key, value in declarations.items():
            if key in by_key:
                by_key[key][1] = value
            else:
                new_pair = [key, value]
                decl_pairs.append(new_pair)
                by_key[key] = new_pair
        new_rule = f"#{element_id}{{" + "; ".join(f"{k}: {v}" for k, v in decl_pairs) + ";}"
        return css_text[:m.start()] + new_rule + css_text[m.end():]
    decls_text = "; ".join(f"{k}: {v}" for k, v in declarations.items())
    new_rule = f"#{element_id}{{{decls_text};}}"
    insertion_point = end - 1  # just before this block's own closing brace
    return css_text[:insertion_point] + new_rule + css_text[insertion_point:]


def _insert_into_block(css_text: str, query: str, addition: str) -> str:
    """Splice raw `addition` text just before the closing brace of the ONE block
    matching `query` exactly -- used to add a brand-new element's full catch-all rule
    (position/size/theme-selector rule together), which _upsert_rule_in_block's
    single-rule-at-a-time shape doesn't fit."""
    span = layout.find_media_block_span(css_text, query)
    if span is None:
        raise ValueError(f"no @media block for query {query!r} found")
    _start, end = span
    insertion_point = end - 1
    return css_text[:insertion_point] + addition + css_text[insertion_point:]


def _remove_html_element(html_text: str, element_id: str) -> str:
    """Strip one `<tag ... id="element_id" ...>...</tag>` occurrence, whole tag through
    its own matching close tag -- safe as long as `tag`'s own content never nests
    another instance of the SAME tag name (true for a flat ch5-button or div footer
    element, confirmed: component.py::build_children returns [] for ch5-button, and
    html_div's div has no children at all)."""
    needle = f'id="{element_id}"'
    idx = html_text.find(needle)
    if idx == -1:
        raise ValueError(f"no HTML element with id={element_id!r} found")
    tag_start = html_text.rfind("<", 0, idx)
    if tag_start == -1:
        raise ValueError(f"malformed HTML near id={element_id!r} -- no opening '<' found")
    m = re.match(r"<([a-zA-Z0-9-]+)", html_text[tag_start:])
    if not m:
        raise ValueError(f"malformed HTML near id={element_id!r} -- no tag name found")
    close = f"</{m.group(1)}>"
    close_idx = html_text.find(close, idx)
    if close_idx == -1:
        raise ValueError(f"no {close!r} found for id={element_id!r}")
    end = close_idx + len(close)
    return html_text[:tag_start] + html_text[end:]


def _remove_toml_component(page_attrs_text: str, element_id: str) -> str:
    for start, end, block in _split_top_components(page_attrs_text):
        _cname, cid = _component_name_and_id(block)
        if cid == element_id:
            return page_attrs_text[:start] + page_attrs_text[end:]
    raise ValueError(f"no [[Elements.Components]] block with id={element_id!r} found")


def _remove_css_rules(css_text: str, element_id: str) -> str:
    """Strip EVERY rule this element has anywhere in css_text -- a bare `#id{...}`
    AND a descendant-selector rule like `#id .ch5-button :not(i):not(svg){...}`
    (build_position_css's own theme-selector rule for a themed button), in every
    @media block (catch-all, any duplicate landscape block, portrait)."""
    pattern = re.compile(r"#" + re.escape(element_id) + r"(?:\s[^{}]*)?\{[^{}]*\}")
    return pattern.sub("", css_text)


def design_ideas_read_footer_groups(footer_path: Path) -> list[list[str]]:
    """The CURRENT subsystem groups in a real `Footer - Main.cuiw`, read from the
    file's own catch-all CSS + PageAttributes -- never assumed to still be
    FOOTER_DEFAULT_GROUPS, since the file may already have been edited by a prior call.

    Menu_* buttons are ordered by their real catch-all `left` position (file order is
    not meaningful -- TOML array-of-tables order need not match visual order), bucketed
    into groups by DividerGroup* position (a button belongs to the group before the
    next divider to its right). Privacy_Mute and its own trailing divider are excluded
    entirely (see this section's module-level note above), as is anything whose
    componentName doesn't start with "Menu_"/"DividerGroup" (a footer can carry other,
    non-subsystem buttons -- confirmed one exists in the reference file -- that this
    reflow mechanism has no business touching).

    Self-verifying: replays design_ideas_footer_layout against the inferred groups and
    raises ValueError if it doesn't reproduce the file's own real positions exactly --
    a footer whose rhythm doesn't match this function's model is not safe to write
    blind changes into, and this is the only place that can catch that before any write
    happens.
    """
    _preamble, sections = _read_sections(footer_path)
    by_name = {name: content for name, _header, content in sections}
    css_text = by_name.get("Css", "")
    attrs_text = by_name.get("PageAttributes", "")

    name_by_id: dict[str, str] = {}
    for _s, _e, block in _split_top_components(attrs_text):
        cname, cid = _component_name_and_id(block)
        if cname and cid:
            name_by_id[cid] = cname

    positions = layout.parse_all_position_rules(css_text, layout.CATCH_ALL_QUERY)
    entries: list[tuple[int, str, str]] = []  # (x, display_name, kind)
    for eid, pos in positions.items():
        cname = name_by_id.get(eid)
        if cname is None or pos["left"] is None:
            continue
        if cname.startswith("Menu_"):
            entries.append((pos["left"], cname[len("Menu_"):], "button"))
        elif cname.startswith("DividerGroup") and cname != "DividerGroup4":
            entries.append((pos["left"], cname, "divider"))
    entries.sort(key=lambda e: e[0])

    groups: list[list[str]] = [[]]
    for _x, name, kind in entries:
        if kind == "divider":
            groups.append([])
        else:
            groups[-1].append(name)
    groups = [g for g in groups if g]

    replay = {name: x for name, _kind, x in design_ideas_footer_layout(groups)}
    for x, name, _kind in entries:
        if replay.get(name) != x:
            raise ValueError(
                f"design_ideas_read_footer_groups: inferred groups {groups} do not "
                f"reproduce {footer_path}'s own real position for {name!r} (file has "
                f"{x}px, replaying the inferred groups computes {replay.get(name)}px) "
                f"-- this footer's layout doesn't match the expected rhythm; refusing "
                f"to write changes to it blind")
    return groups


def design_ideas_remove_subsystem_page(project_dir: Path, display_name: str) -> bool:
    """Delete a subsystem's own page (`{display_name}.cuig`) from a Design-Ideas-derived
    project, leaving its popup widget(s) (`Popup - {display_name}.cuiw`, and a secondary
    "- More" popup where one exists) untouched on disk -- per the user's own explicit
    instruction (2026-09-17): leaving the widget in place means the subsystem can be
    re-added later without rebuilding its popup content from scratch.

    Confirmed real naming convention directly against the reference template (not
    guessed): `Power.cuig` references `Popup - Power`, `Lights.cuig` references
    `Popup - Lights` + `Popup - Lights - More`, etc -- always a same-display-name
    page<->popup pair, one page per subsystem. Also confirmed directly: the project's
    `.cuip` carries no page manifest or navigation-order list at all (pages are
    discovered purely by file presence, matching project.py's own reflow logic), and
    every footer button's own `pageflip` attribute is unconfigured (`"0"`) in the
    reference template -- subsystem popups are shown/hidden entirely via
    `Visibility=Contract`, not page navigation. So deleting the file is the complete
    operation; nothing else references a page by name or id.

    Not every subsystem has its own page in the real template (VideoCall does not, in
    the reference project) -- returns `False` rather than raising when the page file is
    simply absent, since "nothing to remove" is a legitimate, expected outcome here.
    Marks the project's contract stale on an actual deletion, same as every other
    structural change in this project.
    """
    page_path = project_dir / f"{display_name}.cuig"
    if not page_path.exists():
        return False
    page_path.unlink()
    contracts.mark_project_stale_for(page_path)
    return True


def design_ideas_write_footer_groups(
    footer_path: Path,
    sdk: UiSdk,
    new_groups: list[list[str]],
    *,
    icon_classes: dict[str, str] | None = None,
    icon_library: str = "FA Classic Solid",
    active_font: str = DEFAULT_FONT,
    delete_pages: bool = True,
) -> dict[str, list[str]]:
    """Rewrite a real `Footer - Main.cuiw` so its Menu_*/DividerGroup* elements match
    `new_groups` -- adding brand-new buttons/dividers, removing ones no longer present,
    and repositioning everything else, in BOTH landscape and portrait CSS, using the
    already-proven design_ideas_footer_layout/_portrait math. Diffs against
    design_ideas_read_footer_groups's OWN read of the file's current state, not any
    assumed default, so this is safe to call again on a file it (or a human) already
    edited.

    `icon_classes`: `{display_name: "fa-solid fa-..."}` for every NEWLY ADDED button
    (required for each one -- there is no default icon to fall back to; raises if
    missing). Not needed for a button that already exists (repositioning never touches
    its icon).

    `delete_pages` (default True): for every REMOVED button, also call
    design_ideas_remove_subsystem_page (deletes `{display_name}.cuig`, leaves its popup
    widget in place -- see that function's own docstring). Pass False for a purely
    cosmetic footer edit that should not touch any page file.

    Privacy_Mute and its own trailing divider are NEVER touched, in either orientation
    -- see this section's module-level note. If removing subsystems leaves a large gap
    before them, or adding subsystems would collide with them, that is reported back to
    the caller as `overflow` rather than silently invented around.

    Returns `{"added": [...], "removed": [...], "removed_pages": [...],
    "repositioned": [...], "overflow": [...]}` (display names; `removed_pages` is a
    subset of `removed` -- only the ones that actually had a page file to delete).
    Marks the project's contract stale on success, same as every other structural write
    in this project (page.py::write_cuig's own rule).
    """
    icon_classes = icon_classes or {}
    # NOT capped at 4 groups: a 5th (or more) subsystem group's own internal
    # divider never collides with Privacy_Mute's fixed "DividerGroup4" --
    # _internal_divider_name skips that literal number. Whether it actually
    # FITS before Privacy_Mute is a real, separate physical question, caught
    # below by the `overflow` check, not refused here up front (an earlier
    # version of this function refused ANY 5th group outright over exactly
    # this naming collision -- found live, 2026-09-18, when the user pointed
    # out real, visible footer space a removal had freed up).
    current_groups = design_ideas_read_footer_groups(footer_path)

    preamble, sections = _read_sections(footer_path)
    index_by_name = {name: i for i, (name, _h, _c) in enumerate(sections)}
    html_i, css_i, attrs_i = index_by_name["Html"], index_by_name["Css"], index_by_name["PageAttributes"]
    html_text = sections[html_i][2]
    css_text = sections[css_i][2]
    attrs_text = sections[attrs_i][2]

    id_by_name: dict[str, str] = {}
    for _s, _e, block in _split_top_components(attrs_text):
        cname, cid = _component_name_and_id(block)
        if cname and cid:
            id_by_name[cname] = cid

    old_layout = design_ideas_footer_layout(current_groups)
    new_layout = design_ideas_footer_layout(new_groups)
    old_by_name = {name: (kind, x) for name, kind, x in old_layout}
    new_by_name = {name: (kind, x) for name, kind, x in new_layout}
    old_portrait_by_name = {name: y for name, _kind, y in design_ideas_footer_layout_portrait(current_groups)}
    new_portrait_by_name = {name: y for name, _kind, y in design_ideas_footer_layout_portrait(new_groups)}

    old_names, new_names = set(old_by_name), set(new_by_name)
    to_remove = old_names - new_names
    to_add = new_names - old_names
    to_reposition = old_names & new_names

    def real_component_name(display_name: str, kind: str) -> str:
        return f"Menu_{display_name}" if kind == "button" else display_name

    all_queries = _all_media_queries(css_text)
    landscape_extra = [q for q, _s, _e in all_queries if "orientation: landscape" in q]
    portrait_queries = [q for q, _s, _e in all_queries if "orientation: portrait" in q]
    if len(portrait_queries) != 1:
        raise ValueError(
            f"expected exactly one portrait @media block in {footer_path.name}, found "
            f"{len(portrait_queries)} -- refusing to guess which one to write into")
    portrait_query = portrait_queries[0]

    removed: list[str] = []
    removed_pages: list[str] = []
    added: list[str] = []
    repositioned: list[str] = []

    for display_name in sorted(to_remove):
        kind, _x = old_by_name[display_name]
        cname = real_component_name(display_name, kind)
        eid = id_by_name.get(cname)
        if eid is None:
            raise ValueError(f"{cname!r} is in the file's inferred groups but has no element id")
        html_text = _remove_html_element(html_text, eid)
        attrs_text = _remove_toml_component(attrs_text, eid)
        css_text = _remove_css_rules(css_text, eid)
        removed.append(display_name)
        # Dividers have no page of their own -- only a removed BUTTON is a subsystem.
        if delete_pages and kind == "button":
            if design_ideas_remove_subsystem_page(footer_path.parent, display_name):
                removed_pages.append(display_name)

    for display_name in sorted(to_reposition, key=lambda n: new_by_name[n][1]):
        kind, new_x = new_by_name[display_name]
        old_x = old_by_name[display_name][1]
        new_y = new_portrait_by_name[display_name]
        old_y = old_portrait_by_name[display_name]
        if new_x == old_x and new_y == old_y:
            continue
        cname = real_component_name(display_name, kind)
        eid = id_by_name.get(cname)
        if eid is None:
            raise ValueError(f"{cname!r} is in the file's inferred groups but has no element id")
        if new_x != old_x:
            css_text, _n = layout.update_element_declarations(
                css_text, eid, {"left": f"{new_x}px"}, extra_queries=tuple(landscape_extra))
        if new_y != old_y:
            p_left = FOOTER_PORTRAIT_DIVIDER_LEFT if kind == "divider" else FOOTER_PORTRAIT_BUTTON_LEFT
            css_text = _upsert_rule_in_block(
                css_text, portrait_query, eid, {"left": f"{p_left}px", "top": f"{new_y}px"})
        repositioned.append(display_name)

    existing_positions = layout.parse_all_position_rules(css_text, layout.CATCH_ALL_QUERY)
    z_indices = [p["z_index"] for p in existing_positions.values() if p["z_index"] is not None]
    next_z = (max(z_indices) + 1) if z_indices else 1

    for display_name in sorted(to_add, key=lambda n: new_by_name[n][1]):
        kind, x = new_by_name[display_name]
        new_id = generate_element_id()
        if kind == "button":
            icon_class = icon_classes.get(display_name)
            if not icon_class:
                raise ValueError(
                    f"no icon_class given for new footer button {display_name!r} -- "
                    f"pass icon_classes={{{display_name!r}: '<fa class>'}}")
            b_html, b_css, b_element = component.build_component(
                sdk, "ch5-button", component_name=f"Menu_{display_name}", element_id=new_id,
                x=x, y=FOOTER_BUTTON_TOP, width=FOOTER_BUTTON_WIDTH, height=FOOTER_BUTTON_HEIGHT,
                z_index=next_z, resolution=None, active_font=active_font, label="",
                icon_class=icon_class, icon_library=icon_library,
                overrides={"customvstheme": "theme", "type": "primary"},
            )
        else:
            b_html, b_css, b_element = build_html_div(
                component_name=display_name, element_id=new_id,
                x=x, y=FOOTER_DIVIDER_TOP, width=FOOTER_DIVIDER_WIDTH, height=FOOTER_DIVIDER_HEIGHT,
                z_index=next_z, resolution=None,
                background_color=FOOTER_DIVIDER_FILL, border_color=FOOTER_DIVIDER_BORDER_COLOR,
                border_width=0,
            )
        next_z += 1

        # Blind end-of-string concatenation would land AFTER the section's own
        # trailing blank-line whitespace (real files end Html/PageAttributes content
        # with several \r\n before the next section header) -- gluing the new tag
        # directly onto the following `{Css}`/EOF with no separator at all. Strip that
        # trailing whitespace off first, insert, then restore it after.
        html_stripped = html_text.rstrip("\r\n")
        html_trailing = html_text[len(html_stripped):]
        html_text = html_stripped + b_html + html_trailing

        catch_all_inner = layout.find_media_block(b_css, layout.CATCH_ALL_QUERY)
        if catch_all_inner is None:
            raise ValueError(f"newly built element {display_name!r} has no catch-all CSS block")
        css_text = _insert_into_block(css_text, layout.CATCH_ALL_QUERY, catch_all_inner)

        y = new_portrait_by_name[display_name]
        p_decls = {
            "left": f"{FOOTER_PORTRAIT_DIVIDER_LEFT if kind == 'divider' else FOOTER_PORTRAIT_BUTTON_LEFT}px",
            "top": f"{y}px",
        }
        if kind == "divider":
            p_decls["width"] = f"{FOOTER_PORTRAIT_DIVIDER_WIDTH}px"
            p_decls["height"] = f"{FOOTER_PORTRAIT_DIVIDER_HEIGHT}px"
        css_text = _upsert_rule_in_block(css_text, portrait_query, new_id, p_decls)

        attrs_stripped = attrs_text.rstrip("\r\n")
        attrs_trailing = attrs_text[len(attrs_stripped):]
        new_block = "\n".join(b_element.to_toml_lines("Elements.Components"))
        attrs_text = attrs_stripped + "\n" + new_block + "\n" + attrs_trailing
        added.append(display_name)

    # Privacy_Mute/DividerGroup4 overflow check: neither is ever moved, so flag rather
    # than hide a real visual gap or collision against wherever the (possibly very
    # different) new last group now ends. The real boundary is DividerGroup4's OWN
    # fixed left edge minus the standard FOOTER_GROUP_GAP rhythm -- NOT Privacy_Mute's
    # raw left edge, which sits FOOTER_GROUP_GAP + DividerGroup4's own width further
    # right. An earlier version of this check compared against Privacy_Mute directly
    # and missed a real live bug (found live, 2026-09-18, from a screenshot showing
    # the new group's icon rendered flush against/overlapping DividerGroup4): a last
    # item can end AFTER DividerGroup4's own position (silently overlapping the fixed
    # divider, or leaving far less than the standard 10px gap before it) while still
    # ending BEFORE Privacy_Mute's own left edge, so the old check reported a clean
    # `overflow: []` for a layout that was actually broken.
    overflow: list[str] = []
    if new_layout:
        last_name, last_kind, last_x = new_layout[-1]
        last_width = FOOTER_DIVIDER_WIDTH if last_kind == "divider" else FOOTER_BUTTON_WIDTH
        last_end = last_x + last_width
        boundary_name = "DividerGroup4" if "DividerGroup4" in id_by_name else "Privacy_Mute"
        boundary_id = id_by_name.get(boundary_name)
        boundary_pos = boundary_id and (existing_positions.get(boundary_id) or layout.parse_all_position_rules(
            css_text, layout.CATCH_ALL_QUERY).get(boundary_id))
        if boundary_pos and boundary_pos.get("left") is not None:
            safe_end = boundary_pos["left"] - FOOTER_GROUP_GAP
            if last_end > safe_end:
                overflow.append(
                    f"new layout's last item ({last_name}) ends at {last_end}px, which "
                    f"leaves less than the standard {FOOTER_GROUP_GAP}px gap before "
                    f"{boundary_name}'s fixed position at {boundary_pos['left']}px (needs "
                    f"to end at {safe_end}px or earlier) -- {boundary_name}/Privacy_Mute "
                    f"is never reflowed, remove more subsystems, combine groups, or widen "
                    f"the footer")

    sections[html_i][2] = html_text
    sections[css_i][2] = css_text
    sections[attrs_i][2] = attrs_text
    _write_sections(footer_path, preamble, sections)
    contracts.mark_project_stale_for(footer_path)

    return {
        "added": added, "removed": removed, "removed_pages": removed_pages,
        "repositioned": repositioned, "overflow": overflow,
    }


# --- Presentation source-selection buttons -- editing a real ------------------------
# Sources - Center.cuiw. DesignIdeasTemplate.md §3: "When adding new source selection
# buttons, new buttons should be cloned from an existing source button. This is due
# to the fact that a source button uses all custom styling and includes two stacked
# DIVs that are used for sync/no-sync detection." This module does NOT clone (see the
# module docstring's "template-independent mechanics" rule) -- it reproduces the same
# 3-element-per-source shape from scratch via this project's own schema-grounded
# primitives, grounded directly against the real `Sources - Center.cuiw`
# (C:\Solutions\CrestronDesignIdeas\BasicTemplate_v1_0_2, 2026-09-18), the same
# read-the-real-file-first discipline used everywhere else in this module. User,
# 2026-09-18: "presentation sources in Design Ideas are composed of 3 elements: Button
# with text/icon, a horizontal line for video sync detected (green) and a horizontal
# line for video sync not detected (red). When users add/remove presentation sources,
# you need to account for 3 objects per source for removal and also addition/
# re-centering/reflow" -- exactly the footer's own "remove/add must recompute every
# FOLLOWING element's position" discipline, applied here to a CENTERED grid instead of
# a left-anchored row of groups.
#
# Real measured geometry (every value below is a DIRECT measurement, not a guess):
# button 186x177, shape="custom", CUSTOM mode (NOT theme -- unlike ordinary subsystem
# group buttons, matching DesignIdeasTemplate.md §3's own "uses all custom styling"
# note), `iconposition="top"` (icon above label, not beside it). Landscape: single row,
# centered in the widget's own 1048px canvas (5 real buttons span 1018px, 15px margin
# each side). Portrait: 2 columns, centered in the widget's own 650px canvas, same
# 22px item gap and 208px column step as landscape (confirmed identical), 201px row
# step, a trailing PARTIAL row's items centered as their own smaller row (same
# centering formula, fewer items) -- confirmed real: Source_5 alone in portrait sits
# at left=233, matching a 1-item row's own centered offset almost exactly.
#
# Element ORDER: same real, confirmed-live rule as everywhere else in this module
# (Layer Manager / real click hit-testing keys off component-list order, FIRST =
# FRONTMOST -- see design_ideas_build_subsystem_page's own note) -- confirmed
# directly against the real file's own order: Sync bars, then NoSync bars, then
# Instructions, then the buttons THEMSELVES dead last. Counterintuitive (the buttons
# are the interactive element) but harmless here: the Sync/NoSync bars are a tiny
# 3px-tall strip near the button's own bottom edge, not themselves interactive, so
# sitting in front of just that thin strip doesn't block the button's own real
# clickable area. Reproduced exactly rather than "corrected" -- this project's own
# rule is to match the real file's structure, not to improve on it from a guess.
SOURCE_BUTTON_WIDTH = 186
SOURCE_BUTTON_HEIGHT = 177
SOURCE_GAP = 22  # confirmed: column step (208) - button width (186), same both orientations
SOURCE_COLUMN_STEP = SOURCE_BUTTON_WIDTH + SOURCE_GAP  # 208
SOURCE_LANDSCAPE_TOP = 160
SOURCE_LANDSCAPE_PANEL_WIDTH = 1048  # real Sources - Center.cuiw canvas width

SOURCE_SYNC_WIDTH = 122
SOURCE_SYNC_HEIGHT = 3
SOURCE_SYNC_OFFSET_X = 32  # landscape: from the button's own left (47 - 15)
SOURCE_SYNC_OFFSET_Y = 165  # from the button's own top (325 - 160), both orientations
SOURCE_SYNC_COLOR = "#52a911cc"
SOURCE_NOSYNC_COLOR = "#ed1919b3"

SOURCE_PORTRAIT_COLUMNS = 2
SOURCE_PORTRAIT_PANEL_WIDTH = 650  # real Sources - Center.cuiw portrait canvas width
SOURCE_PORTRAIT_START_Y = 169
SOURCE_PORTRAIT_ROW_STEP = 201
#: A trailing PARTIAL row (fewer than SOURCE_PORTRAIT_COLUMNS items) sits an extra
#: 8px below where the uniform row step alone would predict -- confirmed real (the
#: template's own 5th item, alone in its own row, sits at top=579 vs the 571 a plain
#: `SOURCE_PORTRAIT_START_Y + 2*SOURCE_PORTRAIT_ROW_STEP` would compute) but from only
#: ONE real example, the same "confirmed once, not fully general" caveat this
#: project already applies to the footer's own first-gap quirk.
SOURCE_PORTRAIT_TRAILING_ROW_EXTRA_GAP = 8
SOURCE_PORTRAIT_SYNC_OFFSET_X = 31  # portrait: from the button's own left (157 - 126)

#: Custom-mode palette (NOT theme) -- pressed and selected share the SAME look in the
#: real file (no distinct selected state), text/icon states copied via derive_states'
#: own default "copy unchanged" rule for keys not set explicitly below.
SOURCE_BUTTON_PALETTE: dict[str, str] = {
    "background_color": "rgba(137, 137, 137, 0.55)",
    "border_width": "0px",
    "text_color": "rgba(255, 255, 255, 0.95)",
    "icon_color": "rgba(255, 255, 255, 0.95)",
    "pressed_background_color": "rgba(255, 255, 255, 0.7)",
    "selected_background_color": "rgba(255, 255, 255, 0.7)",
    "pressed_text_color": "rgba(82, 82, 82, 0.9)",
    "selected_text_color": "rgba(82, 82, 82, 0.9)",
    "pressed_icon_color": "rgba(82, 82, 82, 0.9)",
    "selected_icon_color": "rgba(82, 82, 82, 0.9)",
}
SOURCE_ICON_FONT_SIZE = 60


def design_ideas_source_layout_landscape(sources: list[str]) -> list[tuple[str, int, int]]:
    """`(name, x, y)` for each source button, single row, centered in the real
    1048px canvas -- reproduces the real template's own 5-source positions
    (15, 223, 431, 639, 847) exactly. Raises ValueError if `sources` don't
    fit in one row -- landscape MULTI-row wrapping has no real example to
    ground yet (unlike portrait, which has 2 confirmed real rows), so this
    refuses rather than guessing at an unconfirmed wrap rule."""
    n = len(sources)
    if n == 0:
        return []
    total_width = n * SOURCE_BUTTON_WIDTH + (n - 1) * SOURCE_GAP
    if total_width > SOURCE_LANDSCAPE_PANEL_WIDTH:
        raise ValueError(
            f"{n} sources ({total_width}px) don't fit in one landscape row "
            f"({SOURCE_LANDSCAPE_PANEL_WIDTH}px) -- landscape multi-row wrapping "
            f"is not yet grounded against a real file, fewer sources needed"
        )
    start_x = (SOURCE_LANDSCAPE_PANEL_WIDTH - total_width) // 2
    return [
        (name, start_x + i * SOURCE_COLUMN_STEP, SOURCE_LANDSCAPE_TOP)
        for i, name in enumerate(sources)
    ]


def design_ideas_source_layout_portrait(sources: list[str]) -> list[tuple[str, int, int]]:
    """`(name, x, y)` for each source button, wrapped 2 columns per row,
    each row independently centered in the real 650px canvas -- reproduces
    the real template's own 5-source positions exactly (row0 y=169, row1
    y=370, trailing partial row2 y=579 via SOURCE_PORTRAIT_TRAILING_ROW_
    EXTRA_GAP). A row with fewer than SOURCE_PORTRAIT_COLUMNS items (the
    last one, if `sources` isn't a multiple of 2) is centered as its own
    smaller row, not left-aligned under the first column."""
    rows = [
        sources[i:i + SOURCE_PORTRAIT_COLUMNS]
        for i in range(0, len(sources), SOURCE_PORTRAIT_COLUMNS)
    ]
    layout: list[tuple[str, int, int]] = []
    y = SOURCE_PORTRAIT_START_Y
    for ri, row in enumerate(rows):
        if ri > 0:
            y += SOURCE_PORTRAIT_ROW_STEP
            if len(row) < SOURCE_PORTRAIT_COLUMNS:
                y += SOURCE_PORTRAIT_TRAILING_ROW_EXTRA_GAP
        row_width = len(row) * SOURCE_BUTTON_WIDTH + (len(row) - 1) * SOURCE_GAP
        row_x = (SOURCE_PORTRAIT_PANEL_WIDTH - row_width) // 2
        for ci, name in enumerate(row):
            layout.append((name, row_x + ci * SOURCE_COLUMN_STEP, y))
    return layout


def _source_content(
    sdk: UiSdk, *, name: str, x: int, y: int, sync_offset_x: int, icon_class: str,
    icon_library: str, active_font: str, z_index: int, resolution: tuple[int, int] | None,
) -> list[tuple[str, str, Element]]:
    """The 3 real elements for one source: `Source_{name}` button (icon+label,
    custom mode) + `Source_{name}_Sync` (green) + `Source_{name}_NoSync`
    (red) -- both bars identically positioned/sized, toggled by the
    project's own runtime contract (never both visible at once), matching
    the real file exactly. Returned SYNC BARS FIRST (frontmost) then the
    BUTTON LAST (backmost) -- see this section's own module note on why."""
    btn_html, btn_css, btn_element = component.build_component(
        sdk, "ch5-button", component_name=f"Source_{name}", element_id=generate_element_id(),
        x=x, y=y, width=SOURCE_BUTTON_WIDTH, height=SOURCE_BUTTON_HEIGHT, z_index=z_index,
        resolution=resolution, active_font=active_font, label=name,
        icon_class=icon_class, icon_library=icon_library,
        overrides={"labelinnerhtml": name, "iconposition": "top", "customvstheme": "custom"},
    )
    btn_id = dict(btn_element.attributes)["id"]
    btn_css = typography.apply_icon_size(btn_css, btn_id, sdk, "ch5-button", SOURCE_ICON_FONT_SIZE)
    btn_css = palette.apply_palette(
        btn_css, btn_id, sdk, "ch5-button",
        palette.applicable_subset("ch5-button", palette.derive_states(dict(SOURCE_BUTTON_PALETTE))))

    sync_x, sync_y = x + sync_offset_x, y + SOURCE_SYNC_OFFSET_Y
    sync_html, sync_css, sync_element = build_html_div(
        component_name=f"Source_{name}_Sync", element_id=generate_element_id(),
        x=sync_x, y=sync_y, width=SOURCE_SYNC_WIDTH, height=SOURCE_SYNC_HEIGHT,
        z_index=z_index + 10, resolution=resolution, background_color=SOURCE_SYNC_COLOR,
    )
    nosync_html, nosync_css, nosync_element = build_html_div(
        component_name=f"Source_{name}_NoSync", element_id=generate_element_id(),
        x=sync_x, y=sync_y, width=SOURCE_SYNC_WIDTH, height=SOURCE_SYNC_HEIGHT,
        z_index=z_index + 5, resolution=resolution, background_color=SOURCE_NOSYNC_COLOR,
    )
    return [
        (sync_html, sync_css, sync_element),
        (nosync_html, nosync_css, nosync_element),
        (btn_html, btn_css, btn_element),
    ]


def design_ideas_read_sources(sources_path: Path) -> list[str]:
    """Current source display names, in real left-to-right (landscape)
    order, read from a real `Sources - Center.cuiw`'s own catch-all CSS +
    PageAttributes -- never assumed, since the file may already have been
    edited. Self-verifying: replays `design_ideas_source_layout_landscape`
    against the inferred list and raises ValueError if it doesn't reproduce
    the file's own real positions exactly -- same discipline as
    `design_ideas_read_footer_groups`, and for the same reason (a source
    layout that doesn't match this module's model is not safe to write
    blind changes into).

    `Source_{name}_Sync`/`_NoSync` are recognized and excluded by suffix --
    only the real `Source_{name}` BUTTON contributes an entry."""
    _preamble, sections = _read_sections(sources_path)
    by_name = {name: content for name, _h, content in sections}
    css_text = by_name.get("Css", "")
    attrs_text = by_name.get("PageAttributes", "")

    name_by_id: dict[str, str] = {}
    for _s, _e, block in _split_top_components(attrs_text):
        cname, cid = _component_name_and_id(block)
        if cname and cid:
            name_by_id[cid] = cname

    positions = layout.parse_all_position_rules(css_text, layout.CATCH_ALL_QUERY)
    entries: list[tuple[int, str]] = []
    for eid, pos in positions.items():
        cname = name_by_id.get(eid)
        if cname is None or pos["left"] is None or not cname.startswith("Source_"):
            continue
        if cname.endswith("_Sync") or cname.endswith("_NoSync"):
            continue
        entries.append((pos["left"], cname[len("Source_"):]))
    entries.sort(key=lambda e: e[0])
    sources = [name for _x, name in entries]

    replay = {name: x for name, x, _y in design_ideas_source_layout_landscape(sources)}
    for x, name in entries:
        if replay.get(name) != x:
            raise ValueError(
                f"design_ideas_read_sources: inferred sources {sources} do not "
                f"reproduce {sources_path}'s own real position for {name!r} (file has "
                f"{x}px, replaying computes {replay.get(name)}px) -- this file's "
                f"layout doesn't match the expected rhythm; refusing to write changes "
                f"to it blind"
            )
    return sources


def design_ideas_write_sources(
    sources_path: Path,
    sdk: UiSdk,
    new_sources: list[str],
    *,
    icon_classes: dict[str, str] | None = None,
    icon_library: str = "FA Classic Solid",
    active_font: str = DEFAULT_FONT,
) -> dict[str, list[str]]:
    """Rewrite a real `Sources - Center.cuiw` so its `Source_*`/`_Sync`/
    `_NoSync` triplets match `new_sources` -- adding brand-new triplets,
    removing ones no longer present, and repositioning everything else, in
    BOTH landscape and portrait CSS, using `design_ideas_source_layout_
    landscape`/`_portrait`. Diffs against `design_ideas_read_sources`'s OWN
    read of the file's current state, not any assumed default -- safe to
    call again on a file it (or a human) already edited. User's own
    framing, 2026-09-18: "account for 3 objects per source for removal and
    also addition/re-centering/reflow" -- this is that: every add/remove
    handles all 3 real elements together and recomputes every OTHER
    source's position too (the grid re-centers), not just the one being
    touched.

    `icon_classes`: `{name: "fa-solid fa-..."}` for every NEWLY ADDED
    source (required for each one -- there is no default icon to fall back
    to; raises if missing). Not needed for a source that already exists
    (repositioning never touches its icon).

    Explicitly OUT OF SCOPE: the `Instructions` text element's own
    position, and anything about a source's optional `Controls - <name>`
    widget (a separate concern -- see this module's own README notes) --
    neither is touched here.

    A newly ADDED source's 3 elements are appended at the very end of the
    file (its own real DOM/list position, per this module's own front-to-
    back z-order rule -- see design_ideas_build_subsystem_page's note),
    NOT re-inserted into the real file's own role-grouped ordering
    convention (every source's Sync bars together, then every NoSync bar,
    then Instructions, then every button). That grouping is purely
    cosmetic for a new source: its Sync/NoSync bars only ever overlap ITS
    OWN button (confirmed via the real measured geometry above), never
    another source's, so ending up placed after other sources' buttons in
    the list has no visible or functional effect -- documented as a known,
    harmless structural difference from a hand-authored file, not silently
    glossed over.

    Returns `{"added": [...], "removed": [...], "repositioned": [...]}`
    (display names). Marks the project's contract stale on success, same
    as every other structural write in this project.
    """
    icon_classes = icon_classes or {}
    current_sources = design_ideas_read_sources(sources_path)

    preamble, sections = _read_sections(sources_path)
    index_by_name = {name: i for i, (name, _h, _c) in enumerate(sections)}
    html_i, css_i, attrs_i = index_by_name["Html"], index_by_name["Css"], index_by_name["PageAttributes"]
    html_text = sections[html_i][2]
    css_text = sections[css_i][2]
    attrs_text = sections[attrs_i][2]

    id_by_name: dict[str, str] = {}
    for _s, _e, block in _split_top_components(attrs_text):
        cname, cid = _component_name_and_id(block)
        if cname and cid:
            id_by_name[cname] = cid

    old_landscape = {n: x for n, x, _y in design_ideas_source_layout_landscape(current_sources)}
    new_landscape = {n: x for n, x, _y in design_ideas_source_layout_landscape(new_sources)}
    old_portrait = {n: (x, y) for n, x, y in design_ideas_source_layout_portrait(current_sources)}
    new_portrait = {n: (x, y) for n, x, y in design_ideas_source_layout_portrait(new_sources)}

    old_names, new_names = set(old_landscape), set(new_landscape)
    to_remove = old_names - new_names
    to_add = new_names - old_names
    to_reposition = old_names & new_names

    all_queries = _all_media_queries(css_text)
    landscape_extra = [q for q, _s, _e in all_queries if "orientation: landscape" in q]
    portrait_queries = [q for q, _s, _e in all_queries if "orientation: portrait" in q]
    if len(portrait_queries) != 1:
        raise ValueError(
            f"expected exactly one portrait @media block in {sources_path.name}, found "
            f"{len(portrait_queries)} -- refusing to guess which one to write into"
        )
    portrait_query = portrait_queries[0]

    removed: list[str] = []
    added: list[str] = []
    repositioned: list[str] = []

    for name in sorted(to_remove):
        for suffix in ("", "_Sync", "_NoSync"):
            cname = f"Source_{name}{suffix}"
            eid = id_by_name.get(cname)
            if eid is None:
                raise ValueError(f"{cname!r} is in the file's inferred sources but has no element id")
            html_text = _remove_html_element(html_text, eid)
            attrs_text = _remove_toml_component(attrs_text, eid)
            css_text = _remove_css_rules(css_text, eid)
        removed.append(name)

    for name in sorted(to_reposition, key=lambda n: new_landscape[n]):
        new_x = new_landscape[name]
        old_x = old_landscape[name]
        new_py, old_py = new_portrait[name][1], old_portrait[name][1]
        new_px, old_px = new_portrait[name][0], old_portrait[name][0]
        if new_x == old_x and new_px == old_px and new_py == old_py:
            continue
        for suffix, dx in (("", 0), ("_Sync", SOURCE_SYNC_OFFSET_X), ("_NoSync", SOURCE_SYNC_OFFSET_X)):
            cname = f"Source_{name}{suffix}"
            eid = id_by_name.get(cname)
            if eid is None:
                raise ValueError(f"{cname!r} is in the file's inferred sources but has no element id")
            if new_x != old_x:
                css_text, _n = layout.update_element_declarations(
                    css_text, eid, {"left": f"{new_x + dx}px"}, extra_queries=tuple(landscape_extra))
            if new_px != old_px or new_py != old_py:
                # Real bug, found live 2026-09-18 (user screenshot: portrait
                # sync bars rendered at the wrong spot): this wrote the
                # BUTTON's own `top` to the Sync/NoSync bars too, instead of
                # offsetting by SOURCE_SYNC_OFFSET_Y like the ADD path
                # (below) already correctly does -- a real inconsistency
                # between the two code paths, not just a typo in one.
                p_dx = SOURCE_PORTRAIT_SYNC_OFFSET_X if suffix else 0
                p_top = new_py + (SOURCE_SYNC_OFFSET_Y if suffix else 0)
                css_text = _upsert_rule_in_block(
                    css_text, portrait_query, eid, {"left": f"{new_px + p_dx}px", "top": f"{p_top}px"})
        repositioned.append(name)

    existing_positions = layout.parse_all_position_rules(css_text, layout.CATCH_ALL_QUERY)
    z_indices = [p["z_index"] for p in existing_positions.values() if p["z_index"] is not None]
    next_z = (max(z_indices) + 1) if z_indices else 1

    for name in sorted(to_add, key=lambda n: new_landscape[n]):
        icon_class = icon_classes.get(name)
        if not icon_class:
            raise ValueError(
                f"no icon_class given for new source {name!r} -- "
                f"pass icon_classes={{{name!r}: '<fa class>'}}")
        x = new_landscape[name]
        y = SOURCE_LANDSCAPE_TOP
        content = _source_content(
            sdk, name=name, x=x, y=y, sync_offset_x=SOURCE_SYNC_OFFSET_X, icon_class=icon_class,
            icon_library=icon_library, active_font=active_font, z_index=next_z, resolution=None)
        next_z += 10

        html_stripped = html_text.rstrip("\r\n")
        html_trailing = html_text[len(html_stripped):]
        addition_html = "".join(h for h, _c, _e in content)
        html_text = html_stripped + addition_html + html_trailing

        for part_html, part_css, part_element in content:
            catch_all_inner = layout.find_media_block(part_css, layout.CATCH_ALL_QUERY)
            if catch_all_inner is None:
                raise ValueError(f"newly built element for {name!r} has no catch-all CSS block")
            css_text = _insert_into_block(css_text, layout.CATCH_ALL_QUERY, catch_all_inner)

            eid = dict(part_element.attributes)["id"]
            cname = dict(part_element.attributes)["componentName"]
            is_button = cname == f"Source_{name}"
            px, py = new_portrait[name]
            p_left = px if is_button else px + SOURCE_PORTRAIT_SYNC_OFFSET_X
            p_top = py if is_button else py + SOURCE_SYNC_OFFSET_Y
            p_decls = {"left": f"{p_left}px", "top": f"{p_top}px"}
            css_text = _upsert_rule_in_block(css_text, portrait_query, eid, p_decls)

        attrs_stripped = attrs_text.rstrip("\r\n")
        attrs_trailing = attrs_text[len(attrs_stripped):]
        new_blocks = "\n".join(
            "\n".join(part_element.to_toml_lines("Elements.Components"))
            for _h, _c, part_element in content
        )
        attrs_text = attrs_stripped + "\n" + new_blocks + "\n" + attrs_trailing
        added.append(name)

    sections[html_i][2] = html_text
    sections[css_i][2] = css_text
    sections[attrs_i][2] = attrs_text
    _write_sections(sources_path, preamble, sections)
    contracts.mark_project_stale_for(sources_path)

    return {"added": added, "removed": removed, "repositioned": repositioned}


# --- Source Controls -- a source's own optional control-panel widget -----------------
# `Controls - <name>.cuiw` is STRUCTURALLY IDENTICAL to a subsystem popup -- confirmed
# directly, 2026-09-18: `Controls - Template.cuiw` (the real scaffold) has the exact
# same component names/geometry as `Popup - SubsystemTemplate.cuiw` (icon 68x72, title
# left=67 width=333, Group_Container/Group_Title at the same offsets, close at 84x72 --
# already this module's own CLOSE_SIZE_DEVICE, named for exactly this use case).
# design_ideas_build_subsystem_popup(..., device_controls=True) is the SAME builder,
# reused as-is -- no new widget-building code needed here.
#
# What IS new: wiring that widget's reference onto the real Presentation page.
# Confirmed directly against the real `Presentation.cuig`: every `Controls - <name>`
# ref sits at the EXACT SAME position as `Sources - Center`'s own ref in every one of
# the page's 4 real @media blocks (catch-all 168,248,z=99; a landscape-extra block
# that's `display:block` only, a delta; a SECOND landscape-extra block with its OWN
# distinct override, display:none + 116,121; portrait 120,142,display:none) -- they
# overlay exactly, only one visible/interactive at a time via the project's own
# runtime contract, so a new Controls ref's own declarations are copied VERBATIM from
# Sources - Center's real ones in each block (not a shared formula -- the blocks
# genuinely differ from each other), with only the catch-all z-index bumped above it
# (the only block that carries z-index at all) so the widget list front-to-back order
# this module already enforces everywhere else stays correct. Controls refs are
# listed BEFORE Sources - Center in the real file (frontmost, matching every other
# confirmed z-order rule in this module).
SOURCE_CONTROL_REF_ANCHOR = "Sources - Center"


def design_ideas_add_source_control_ref(
    page_path: Path, sdk: UiSdk, control_widget_id: str, control_widget_name: str,
) -> bool:
    """Add a `Controls - <name>` widget's reference to a real Presentation-
    style page (Header-Center-Source pattern), positioned/behaved exactly
    like `Sources - Center`'s own ref -- see this section's own module note
    for why that's the correct real mechanism, not a guess. Idempotent:
    returns False (no-op) if a ref with this widget name is already
    present; True if it was added. Raises ValueError if the page has no
    real `Sources - Center` ref to anchor against (not a Header-Center-
    Source page, or the anchor's own real name has changed).

    Marks the project's contract stale on an actual addition, same as
    every other structural write in this project.
    """
    preamble, sections = _read_sections(page_path)
    index_by_name = {name: i for i, (name, _h, _c) in enumerate(sections)}
    html_i, css_i, attrs_i = index_by_name["Html"], index_by_name["Css"], index_by_name["PageAttributes"]
    html_text = sections[html_i][2]
    css_text = sections[css_i][2]
    attrs_text = sections[attrs_i][2]

    if f'ccid_WidgetName="{control_widget_name}"' in html_text:
        return False

    id_by_name: dict[str, str] = {}
    for _s, _e, block in _split_top_page_elements(attrs_text):
        cname, cid = _component_name_and_id(block)
        if cname and cid:
            id_by_name[cname] = cid
    anchor_id = id_by_name.get(SOURCE_CONTROL_REF_ANCHOR)
    if anchor_id is None:
        raise ValueError(
            f"{page_path} has no real {SOURCE_CONTROL_REF_ANCHOR!r} ref to anchor a "
            f"Controls widget's position/behavior against"
        )

    new_id = generate_element_id()
    ref_html, ref_element = make_widget_reference(sdk, control_widget_id, control_widget_name, element_id=new_id)

    # HTML: insert immediately BEFORE the anchor's own tag (frontmost of the two,
    # matching the real file's own Controls-before-Sources-Center order).
    anchor_needle = f'id="{anchor_id}"'
    anchor_idx = html_text.find(anchor_needle)
    if anchor_idx == -1:
        raise ValueError(f"anchor id {anchor_id!r} not found in {page_path}'s own Html section")
    tag_start = html_text.rfind("<", 0, anchor_idx)
    html_text = html_text[:tag_start] + ref_html + html_text[tag_start:]

    # PageAttributes: insert immediately BEFORE the anchor's own top-level [[Elements]].
    inserted_attrs = False
    for start, _end, block in _split_top_page_elements(attrs_text):
        _cname, cid = _component_name_and_id(block)
        if cid == anchor_id:
            new_block = "\n".join(ref_element.to_toml_lines("Elements")) + "\n"
            attrs_text = attrs_text[:start] + new_block + attrs_text[start:]
            inserted_attrs = True
            break
    if not inserted_attrs:
        raise ValueError(f"anchor id {anchor_id!r} not found in {page_path}'s own PageAttributes section")

    # Css: copy the anchor's own real declarations VERBATIM into every @media block it
    # has one in (see this section's module note -- the blocks genuinely differ from
    # each other, not a shared formula), bumping z-index (only present in catch-all)
    # so the new ref stays frontmost of the two.
    for query, _s, _e in _all_media_queries(css_text):
        span = layout.find_media_block_span(css_text, query)
        if span is None:
            continue
        block_start, block_end = span
        anchor_m = re.search(r"#" + re.escape(anchor_id) + r"\s*\{[^{}]*\}", css_text[block_start:block_end])
        if anchor_m is None:
            continue
        decls_text = re.search(r"\{([^{}]*)\}", anchor_m.group(0)).group(1)
        decl_pairs: list[list[str]] = []
        for decl in decls_text.split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            key, _, value = decl.partition(":")
            decl_pairs.append([key.strip(), value.strip()])
        for pair in decl_pairs:
            if pair[0] == "z-index":
                pair[1] = str(int(pair[1]) + 1)
        new_rule = f"#{new_id}{{" + "; ".join(f"{k}: {v}" for k, v in decl_pairs) + ";}"
        css_text = _insert_into_block(css_text, query, new_rule)

    sections[html_i][2] = html_text
    sections[css_i][2] = css_text
    sections[attrs_i][2] = attrs_text
    _write_sections(page_path, preamble, sections)
    contracts.mark_project_stale_for(page_path)
    return True
