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
import palette
import shape
import spacing
import style
import styleguide
import typography
from elements import Element
from page import generate_element_id
from sdk import UiSdk

#: Fraction of the given box's height given to each band, top to bottom.
#: Judgment call (not a Construct spec) -- verified against this module's own
#: test to fit without overflow at a real modal card's content-area scale.
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
    presets_id = dict(presets_element.attributes)["id"]
    # Styleguide §6 "Tile (single-select grid)" row: surface/divider/muted
    # icon normal state, amber border + amber-dim fill + amber icon/text when
    # selected -- Camera Presets is exactly this "single-select tile group"
    # (§5 of the layout spec itself).
    presets_css = palette.apply_palette(
        presets_css, presets_id, sdk, "ch5-button-list",
        palette.applicable_subset("ch5-button-list", palette.derive_states({
            "background_color": styleguide.SURFACE,
            "border_color": styleguide.DIVIDER,
            "border_width": "1px",
            "border_style": "solid",
            "text_color": styleguide.TEXT_MUTED,
            "icon_color": styleguide.TEXT_MUTED,
            "selected_background_color": styleguide.ACCENT_AMBER_DIM,
            "selected_border_color": styleguide.ACCENT_AMBER,
            "selected_text_color": styleguide.ACCENT_AMBER,
            "selected_icon_color": styleguide.ACCENT_AMBER,
        })),
    )
    presets_css = typography.apply_font_size(presets_css, presets_id, sdk, "ch5-button-list", styleguide.TILE_FONT_SIZE)
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
    # Zoom row height is styleguide §5's real "btn-group button" measurement
    # (37px), not the generic touch-target floor.
    zoom_row_height = styleguide.BTN_GROUP_HEIGHT
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
    dpad_id = dict(dpad_element.attributes)["id"]
    # No dedicated dpad row in styleguide §6 -- a neutral surface-alt/primary-
    # text treatment (the doc's own generic "not otherwise colored control"
    # look, e.g. the dropdown menu panel) rather than leaving it fully
    # unstyled, a judgment call like every other unspeced choice in this
    # module.
    dpad_css = palette.apply_palette(
        dpad_css, dpad_id, sdk, "ch5-dpad",
        palette.applicable_subset("ch5-dpad", palette.derive_states({
            "background_color": styleguide.SURFACE_ALT,
            "text_color": styleguide.TEXT_PRIMARY,
        })),
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
    # Styleguide §6 "Outlined/secondary button (Cancel, No)" row -- Zoom
    # Out/In are momentary secondary actions, not the primary in-call/
    # confirmation treatment.
    zoom_palette = palette.applicable_subset("ch5-button", palette.derive_states({
        "background_color": styleguide.SURFACE_ALT,
        "border_color": styleguide.DIVIDER,
        "border_width": "1px",
        "border_style": "solid",
        "text_color": styleguide.TEXT_PRIMARY,
        "icon_color": styleguide.TEXT_PRIMARY,
    }))
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
        zoom_id = dict(zoom_element.attributes)["id"]
        zoom_html, zoom_css = shape.apply_radius_px(
            zoom_html, zoom_css, zoom_id, sdk, "ch5-button", styleguide.BTN_GROUP_RADIUS)
        zoom_css = palette.apply_palette(zoom_css, zoom_id, sdk, "ch5-button", zoom_palette)
        zoom_css = typography.apply_font_size(zoom_css, zoom_id, sdk, "ch5-button", styleguide.BTN_GROUP_FONT_SIZE)
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
    power_id = dict(power_element.attributes)["id"]
    # Styleguide §6 "Toggle switch" row: "amber for device power... match the
    # token to what the switch represents" -- camera power is exactly that
    # case. Track/knob geometry (42x24 track, 18x18 knob) isn't wired here:
    # ch5-toggle's box width/height drives layout position, not the
    # component's own internal track/knob render size, which this project's
    # style mechanism doesn't expose a property for (confirmed absent from
    # palette.py's _TOGGLE_PALETTE -- label/icon color only, no fill/size).
    power_css = palette.apply_palette(
        power_css, power_id, sdk, "ch5-toggle",
        palette.applicable_subset("ch5-toggle", palette.derive_states({
            "text_color": styleguide.TEXT_PRIMARY,
            "icon_color": styleguide.ACCENT_AMBER,
        })),
    )
    elements.append(power_element)
    html_parts.append(power_html)
    css_parts.append(power_css)

    return "".join(html_parts), "".join(css_parts), elements
