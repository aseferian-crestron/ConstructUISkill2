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
