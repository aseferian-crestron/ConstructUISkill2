"""
Page/widget background placement -- user's standing rule, 2026-09-11: "Construct
projects need to be 'page based'... pages and widgets both support local controls
for background colors so those should be used when a color needs to be applied at
the page or widget level. When a custom image needs to be used as a page
background, the rule is you use an image component at the lowest z-order at 0,0 at
the page size... If the user specifies that they need to have the video component
supported in the project, then the image component should not be used and the
background component used instead."

Solid page/widget background COLOR needs no new code here -- `page.py`'s existing
`DisplayBackgroundColor`/`BackgroundColor` `{PageAttributes}` mechanism (Phase 3)
is already the right, established tool for that.

`ch5-image`/`ch5-background` PROFILES entries (component.py) transcribed from real
instances 2026-09-11: `ch5-background` from `C:\\Solutions\\ClaudeSamples\\Components\\
Component - Images - Background.cuig`; `ch5-image` (no instance in that project) from
`C:\\Solutions\\ClaudeSamples\\ClaudeCustomModeProject\\Page1.cuig` -- verified
separately by `background_test.py`, not this project's own component_flat_types_test.py
oracle (see that test's `NO_REFERENCE_IN_THIS_PROJECT`).

The real `ch5-background` instance's own CSS (that reference file) is `width: 100%;
height: 100%; z-index: -99; overflow: hidden; position: absolute; display: block;
left: 0; top: 0` in the catch-all block. Deliberately NOT reproduced verbatim: this
module places the component at PIXEL-exact width/height (matching the primary
resolution's own dimensions) via the SAME `component.py::build_component` /
`layout.py::build_position_css` machinery every other component already uses,
rather than percentages -- found, while building this, that `layout.py::_px()` (the
parser every later reflow call re-reads an existing rule through) can't parse a
percentage value, and `_fill_missing_size` treats that as "no size at all" and
silently DROPS the element from every future resolution add. Pixel-exact values are
functionally identical (full canvas cover, lowest z-order) and round-trip correctly
through the whole existing pipeline. `overflow: hidden` is also not reproduced --
`parse_position_rules`/`build_reflow_block` have no generic non-var declaration slot
to carry a plain property like that across a reflow-rewritten block -- a documented,
deliberate simplification, not an oversight.

`z-index: -99` (BACKGROUND_Z_INDEX below) IS reproduced verbatim from the real file
-- it parses fine (no unit), and matching the real value costs nothing.

`ccid_pageBackground="true"` is a marker THIS module invents and `reflow.py` reads
back (`BACKGROUND_MARKER_ATTR`) to recognize and re-pin the element on every
newly-added resolution -- not a real CH5/Construct attribute, purely internal.
"""
from __future__ import annotations

from pathlib import Path

import compare
import component as component_module
import contracts
import devices
import page as page_module
import reflow
from devices import ORIENTATION_ENUM
from project import _numeric_resolution, read_cuip
from sdk import UiSdk

BACKGROUND_Z_INDEX = -99
BACKGROUND_MARKER = ("ccid_pageBackground", "true")

#: Matches page.py's own no-devices-yet default (CreateNewWidgetHandler.cs's real
#: fallback, see layout.py's module docstring) -- used only if the project genuinely
#: has no resolutions configured at all. `orientation` is the int DisplayOrientation
#: encoding (ORIENTATION_ENUM["landscape"]), matching what pick_primary/reflow_file
#: expect from every OTHER resolution dict, not the string form.
FALLBACK_RESOLUTION = {"width": 2560, "height": 1440, "orientation": ORIENTATION_ENUM["landscape"]}


def choose_background_tag(*, needs_video: bool) -> str:
    """`ch5-background` when the project also needs video support (the user's own
    rule: an image component conflicts with video in that case), `ch5-image`
    otherwise."""
    return "ch5-background" if needs_video else "ch5-image"


def _project_resolutions(cuip_path: Path) -> list[dict]:
    """Every resolution this project currently has, fully resolved (catalog-first,
    falling back to the project's own {DeviceResolutionSource} for custom ids) --
    same resolution logic project.py::add_resolutions_to_project already uses --
    and coerced to plain-int width/height (project.py::_numeric_resolution): both
    to_project_resolution and to_custom_resolution carry the confirmed real-file
    "Npx" string form, but reflow.py's pick_primary/reflow_file do arithmetic
    (max-by-width, media-query formulas) that needs plain ints."""
    attrs, device_resolution_source, _ = read_cuip(cuip_path)
    catalog = devices.read_catalog()
    ids = [i for i in dict(attrs).get("DeviceResolutionIds", "").split(",") if i]

    def _resolve(resolution_id: str) -> dict:
        try:
            return devices.to_project_resolution(catalog.by_id(resolution_id))
        except KeyError:
            return next(e for e in device_resolution_source if e["id"] == resolution_id)

    return [_numeric_resolution(_resolve(i)) for i in ids]


def add_page_background(
    page_path: Path,
    cuip_path: Path,
    sdk: UiSdk,
    *,
    needs_video: bool = False,
    component_name: str = "PageBackground",
    element_id: str | None = None,
) -> list[str]:
    """Place a full-canvas background component (see module docstring for the
    image-vs-background choice) on an EXISTING page/widget: (0,0), the project's
    primary resolution's own size, lowest z-order, and re-pinned into every OTHER
    resolution the project already has via reflow.py's background-forcing (the same
    mechanism a LATER `add_resolutions_to_project` call uses for a resolution added
    after this). Returns any reflow warnings (never raises for them, same convention
    as add_resolutions_to_project/reflow_file).
    """
    tag_name = choose_background_tag(needs_video=needs_video)
    element_id = element_id or page_module.generate_element_id()

    resolutions = _project_resolutions(cuip_path)
    primary = (reflow.pick_primary(resolutions, "landscape")
               or reflow.pick_primary(resolutions, "portrait")
               or FALLBACK_RESOLUTION)

    raw = page_path.read_text(encoding="utf-8")
    parsed = compare.split_sections(raw, page_path.suffix.lower())
    html_before = next(c for n, _, c in parsed.sections if n == "Html")
    css_before = next(c for n, _, c in parsed.sections if n == "Css")
    page_attrs_before = next(c for n, _, c in parsed.sections if n == "PageAttributes")

    html_tag, css_block, element = component_module.build_component(
        sdk, tag_name,
        component_name=component_name, element_id=element_id,
        x=0, y=0, width=primary["width"], height=primary["height"],
        z_index=BACKGROUND_Z_INDEX,
        resolution=(primary["width"], primary["height"]),
        overrides=dict([BACKGROUND_MARKER]),
    )

    # Insert BEFORE the section's own trailing whitespace, not after it -- that
    # trailing text (typically "\n\n") is what separates this section from the next
    # header ("{Css}") in the real file; appending after it (an earlier version of
    # this function's own bug, found via this module's own test) leaves the new tag
    # directly abutting "{Css}" with no newline, so the header no longer starts a
    # physical line and every later section-reading call silently fails to find it.
    stripped_html = html_before.rstrip()
    if stripped_html:
        new_html = stripped_html + "\n" + html_tag + html_before[len(stripped_html):]
    else:
        new_html = html_tag + html_before[len(stripped_html):]
    stripped_css = css_before.rstrip()
    new_css = stripped_css + css_block + css_before[len(stripped_css):]
    new_page_attrs = page_attrs_before + "\n" + "\n".join(element.to_toml_lines("Elements")) + "\n"

    new_sections = []
    for name, header, content in parsed.sections:
        if name == "Html":
            content = new_html
        elif name == "Css":
            content = new_css
        elif name == "PageAttributes":
            content = new_page_attrs
        new_sections.append((name, header, content))
    rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
    page_path.write_text(rebuilt, encoding="utf-8", newline="")
    contracts.mark_project_stale_for(page_path)

    warnings: list[str] = []
    for r in resolutions:
        if r["id"] == primary.get("id"):
            continue
        result = reflow.reflow_file(page_path, target_resolution=r, source_resolution=primary,
                                    mode="pin_existing", sdk=sdk)
        warnings.extend(result.warnings)
    return warnings
