"""
.cuig (page) / .cuiw (widget) writer -- Phase 3: create page / create widget / add
widget to page.

Grounded directly in C:\\Git\\CCIDE source:

  - UiEditor.Server\\Helpers\\PersistenceHelper.cs:
      CreatePageSource(UiEditorProject, PageDto)   (~line 112) -- page {PageAttributes}
        key order: Name, PageMode, Id, StartPage, PreloadPage, CachePage,
        VisibilityJoin, DisplayBackgroundColor, [BackgroundColor if set],
        [TransitionIn/Out/Duration/Delay only if CachePage=true]
      CreatePageSource(UiEditorProject, WidgetDto)  (~line 178) -- widget
        {PageAttributes} key order: Name, PageMode, Id, DisplayBackgroundColor,
        [BackgroundColor if set]. NO StartPage/PreloadPage/CachePage/VisibilityJoin/
        Transition* -- confirmed to match the real Widget.cuiw's [Attributes] table
        exactly (4/4 keys, same order).
  - UiEditor.Server\\Commands\\HtmlViews\\CreateNewPageHandler.cs -- a brand-new page
    has ZERO elements and empty Html/Css (HtmlViewRenderContextDto("", "")).
  - UiEditor.Server\\Commands\\HtmlViews\\CreateNewWidgetHandler.cs -- a brand-new
    widget's default Html is `<div id="{id}"></div>`, default Css is two @media blocks
    sizing that div to the requested width/height at left:0/top:0 (99999 default block +
    one real device query, or a 2560x1440 landscape fallback if the project has no
    devices yet). The corresponding PageElementDto is Type="widgetContainer" with ONLY
    Id + DevicesVisited attributes -- the "widget-container" CSS class / checkerboard
    background seen in a fully-built widget is NOT part of this initial creation payload
    (added later by the design-time UI; not yet traced -- flagged, not blocking).
  - AddHtmlViewDependencyHandler.cs -- "add widget to page" registers a page->widget
    dependency in the in-memory ProjectStructureDto graph, but does NOT itself write the
    <ch5-template> element; that element (the actual on-disk, persisted proof the widget
    is placed on the page) is inserted the same way any component is dropped onto a page.
    Its exact attribute set was confirmed directly against a real sample
    (C:\\Solutions\\ClaudeSamples\\Components\\Widget on Page.cuig) -- see
    make_widget_reference() below. templateid = "w" + the WIDGET's own Id (confirmed:
    templateid="w434e1f2d-..." == Widget.cuiw's own Id "434e1f2d-...").
"""
from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from elements import Element  # noqa: E402
from project import FileMetadata, _toml_str  # reuse the same FileMetadata/TOML helpers


def generate_element_id() -> str:
    """Short id like the ones observed throughout real files (e.g. 'ic0t', 'ia4c',
    'ifm2bfrlv6'): 'i' + a handful of random lowercase alnum characters. The exact
    generation algorithm (Import.ImportHelper.GetStyleId()) hasn't been read -- this
    only needs to be syntactically plausible and unique within a file, not bit-identical
    to Construct's own RNG.
    """
    length = random.randint(3, 10)
    return "i" + "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# --- page / widget {PageAttributes}[Attributes] builders -------------------------------

def build_page_attributes(
    *,
    name: str,
    page_id: str | None = None,
    page_mode: str = "absolute",
    is_start_page: bool = False,
    is_preload_page: bool = True,
    cache_page: bool = False,
    visibility_join: str = "0",
    display_background_color: bool = False,
    background_color: str | None = None,
    transition_in: str = "",
    transition_out: str = "",
    transition_duration: str = "",
    transition_delay: str = "",
) -> list[tuple[str, str]]:
    """PersistenceHelper.CreatePageSource(UiEditorProject, PageDto) -- exact order."""
    page_id = page_id or str(uuid4())
    attrs: list[tuple[str, str]] = [
        ("Name", name),
        ("PageMode", page_mode),
        ("Id", page_id),
        ("StartPage", str(is_start_page)),
        ("PreloadPage", str(is_preload_page)),
        ("CachePage", str(cache_page)),
        ("VisibilityJoin", visibility_join),
        ("DisplayBackgroundColor", str(display_background_color)),
    ]
    if background_color:
        attrs.append(("BackgroundColor", background_color))
    if cache_page:
        attrs.append(("TransitionIn", transition_in))
        attrs.append(("TransitionOut", transition_out))
        attrs.append(("TransitionDuration", transition_duration))
        attrs.append(("TransitionDelay", transition_delay))
    return attrs


def build_widget_attributes(
    *,
    name: str,
    widget_id: str | None = None,
    page_mode: str = "absolute",
    display_background_color: bool = False,
    background_color: str | None = None,
) -> list[tuple[str, str]]:
    """PersistenceHelper.CreatePageSource(UiEditorProject, WidgetDto) -- exact order.
    Confirmed to match the real Widget.cuiw's [Attributes] table exactly (4/4 keys).
    """
    widget_id = widget_id or str(uuid4())
    attrs: list[tuple[str, str]] = [
        ("Name", name),
        ("PageMode", page_mode),
        ("Id", widget_id),
        ("DisplayBackgroundColor", str(display_background_color)),
    ]
    if background_color:
        attrs.append(("BackgroundColor", background_color))
    return attrs


def default_widget_html_css(element_id: str, width: int, height: int) -> tuple[str, str, Element]:
    """CreateNewWidgetHandler.cs's default payload for a brand-new, empty widget."""
    html = f'<div id="{element_id}"></div>'
    css = (
        f"@media (max-width: 99999px){{#{element_id}{{width: {width}px;height: {height}px; left: 0; top: 0; position: absolute;}}}}"
        f"@media (orientation: landscape) and (max-width: 2561px) and (max-height: 1441px), (orientation: landscape) and (max-width: 2559px)"
        f"{{#{element_id}{{ width: {width}px; height: {height}px; left: 0; top: 0; position: absolute; }}}}"
    )
    element = Element(
        # CreateNewWidgetHandler.cs's PageElementDto("", "widgetContainer", "", "", null,
        # false, null, false, ...) -- Name/Status/Content/Draggable/Copyable are
        # explicitly set (not null), so ElementSource/Nett DOES emit them (confirmed
        # 2026-09-03 against the real "Widget with Bkd Color.cuiw", which caught this
        # module originally omitting them entirely).
        type="widgetContainer",
        name="",
        status="",
        content="",
        draggable=False,
        copyable=False,
        attributes=[("id", element_id), ("devicesVisited", '["4K Monitor"]')],
    )
    return html, css, element


def make_widget_reference(
    widget_id: str,
    widget_name: str,
    *,
    element_id: str | None = None,
    devices_visited: str = '["TSW-1070, TSW-1070"]',
    transition_duration: str = "1s",
    transition_delay: str = "0s",
) -> tuple[str, Element]:
    """'Add widget to page': the persisted <ch5-template> element -- confirmed
    attribute set/order against C:\\Solutions\\ClaudeSamples\\Components\\Widget on Page.cuig.
    Returns (html_tag, toml_element) so the caller inserts both into the target page.
    """
    element_id = element_id or generate_element_id()
    templateid = f"w{widget_id}"
    attrs: list[tuple[str, str]] = [
        ("transitionduration", transition_duration),
        ("transitiondelay", transition_delay),
        ("templateid", templateid),
        ("id", element_id),
        ("componentName", widget_name),
        ("ccid_ComponentType", "Widget"),
        ("ccid_WidgetName", widget_name),
        ("devicesVisited", devices_visited),
    ]
    html = "<ch5-template " + " ".join(f'{k}="{v}"' for k, v in attrs) + "></ch5-template>"
    element = Element(type="Ch5 Template", attributes=attrs)
    return html, element


# --- .cuig / .cuiw writer (shared format) ----------------------------------------------

def write_cuig(
    path: Path,
    attributes: list[tuple[str, str]],
    html: str = "",
    css: str = "",
    elements: list[Element] | None = None,
    metadata: FileMetadata | None = None,
) -> None:
    metadata = metadata or FileMetadata()
    elements = elements or []

    parts = [
        "{FileMetadata}\n",
        metadata.to_toml(),
        "\n{Html}\n",
        html,
        "\n\n{Css}\n",
        css,
        "\n\n{PageAttributes}\n\n[Attributes]\n",
    ]
    parts.extend(f"{key} = {_toml_str(value)}\n" for key, value in attributes)
    for el in elements:
        parts.append("\n")
        parts.append("\n".join(el.to_toml_lines("Elements")))
        parts.append("\n")
    path.write_text("".join(parts), encoding="utf-8")


def add_widget_reference_to_page(page_html: str, page_elements: list[Element], widget_id: str, widget_name: str) -> tuple[str, list[Element]]:
    """Append a widget reference to an already-loaded page's html/elements (in-memory
    'add widget to page' step -- caller re-writes the page file afterward)."""
    html_tag, element = make_widget_reference(widget_id, widget_name)
    new_html = (page_html + "\n" + html_tag) if page_html else html_tag
    return new_html, [*page_elements, element]
