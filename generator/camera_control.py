"""
Camera subsystem-control composite (subsystem-control tier, per the two-tier
split the user asked for 2026-09-17: this has zero knowledge of Tabbed,
modals, or pages -- it drops into a modal today, a Bento Box popup or a
future layout's own container unchanged, matching modal.py's ContentBuilder
signature: (x, y, width, height, z_index) -> (html, css, list[Element])).

Three bands, top to bottom, per the reference spec's Camera modal section:
Presets (ch5-button-list, single-select tile group) / Position (ch5-dpad,
whose native center/home button covers the "home/reset" requirement, centered
on top of a Zoom Out/Zoom In ch5-button row below it -- zoom is not part of
any dpad in the real SDK schema, and this arrangement matches the
stakeholder-reviewed reference, docs/construct-tabbed-ui-screens-commercial.pdf)
/ Power (ch5-toggle). All 5 component types (ch5-button-list, ch5-dpad,
ch5-button, ch5-toggle) are confirmed real and exposed in Construct
(viewProperties.showOnUI: true) with real reference files already in this
project's sample solution.

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

    # --- Position: square dpad centered on top, Zoom Out/In side by side below ----
    # Layout (dpad above, zoom row below -- not beside it) matches the stakeholder-
    # reviewed reference (docs/construct-tabbed-ui-screens-commercial.pdf, "Camera
    # Modal" page): the §1 UX persona's judgment here is to follow an already-
    # reviewed/approved mockup closely rather than invent a different arrangement,
    # same as it would for any other reference a client has already signed off on.
    zoom_row_height = spacing.MIN_TOUCH_TARGET
    dpad_size = min(position_h - gap - zoom_row_height, inner_width)
    if dpad_size < spacing.MIN_TOUCH_TARGET:
        raise ValueError(
            f"the {position_h}px position band at {inner_width}px wide is too small "
            f"for a dpad plus a Zoom Out/In row below it -- build_camera_control "
            f"needs a bigger box"
        )
    dpad_x = inner_x + (inner_width - dpad_size) // 2
    dpad_html, dpad_css, dpad_element = component.build_component(
        sdk, "ch5-dpad", component_name="Camera Position", element_id=generate_element_id(),
        x=dpad_x, y=y_cursor, width=dpad_size, height=dpad_size, z_index=z_index,
        resolution=resolution, active_font=active_font,
    )
    elements.append(dpad_element)
    html_parts.append(dpad_html)
    css_parts.append(dpad_css)

    zoom_y = y_cursor + dpad_size + gap
    zoom_width = (inner_width - gap) // 2
    if zoom_width < spacing.MIN_TOUCH_TARGET:
        raise ValueError(
            f"a {inner_width}px wide box leaves only {zoom_width}px per zoom button "
            f"side by side -- build_camera_control needs a wider box"
        )
    for label, icon, dx in (
        ("Zoom Out", "fa-solid fa-magnifying-glass-minus", 0),
        ("Zoom In", "fa-solid fa-magnifying-glass-plus", zoom_width + gap),
    ):
        zoom_html, zoom_css, zoom_element = component.build_component(
            sdk, "ch5-button", component_name=label, element_id=generate_element_id(),
            x=inner_x + dx, y=zoom_y, width=zoom_width, height=zoom_row_height, z_index=z_index,
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
