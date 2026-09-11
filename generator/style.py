"""
Custom-mode component styling ("theme my projects" -- Phase 7 territory, entered from
the custom-mode-CSS angle rather than the theme-file angle). Stage 1 of a staged build
(core mechanism now; a palette layer and style-value sources -- chat description,
reference-project extraction, design-doc/image -- are later stages, see README's
Current phase log).

Source-grounded via the SAME `classToVariableMapping` schema already used by
component.py::size_css_vars for component sizing -- confirmed (2026-09-11) to be a
UNIVERSAL mechanism across every CH5 component type checked (ch5-button, ch5-toggle,
ch5-slider, ch5-dpad, ch5-textinput, ch5-tab-button, ch5-button-list, ch5-keypad,
ch5-animation all expose `propertyPattern.customVsThemeHandler ==
"customThemeSize-pattern"` and non-idSelector classToVariableMapping entries with real
style properties), NOT button-specific as an earlier reading of this generator's own
component.py::PROFILES (`vstheme="theme"` default for most types) suggested. Whatever a
component's *current* customvstheme mode is, set_component_style always writes real
values as CSS custom properties on the element's own `#id{}` rule -- the SAME `--ch5-*`
var mechanism already proven correct for width/height -- so it never depends on/needs to
resolve that historical default question.

Stage 1 scope, approved by the user 2026-09-11 after they corrected an unnecessary
request for a hand-styled reference project ("why do you need a sample since... every
component drops on the canvas in custom mode and Construct exposes the CSS properties
of every component, dont you just need to create a map... i shouldnt have to model
anything"): only properties with a real `targetProperty` (a `--ch5-{tag}--...` CSS
custom property) are covered here -- this is the real theming set already confirmed for
ch5-button alone: background/border color+width+style, label color/font-size/
font-weight/text-decoration/letter-spacing, icon color/font-size/margins. Properties
with NO `targetProperty` (e.g. ch5-text's border-radius corners) need a different,
nested-selector placement (see layout.py's `theme_selectors`/`customThemeRequiredSelectors`
precedent, already used for font-family) -- deliberately deferred as a named follow-up,
not guessed at.
"""
from __future__ import annotations

import re

import layout
from sdk import UiSdk

CATCH_ALL_QUERY = "(max-width: 99999px)"


def style_property_catalog(sdk: UiSdk, tag_name: str) -> list[dict]:
    """Every stylable property this tag's real SDK schema exposes with a
    `targetProperty` (Stage 1 scope -- see module docstring), straight off
    `component-context.json`'s `classToVariableMapping`, no per-tag modeling.
    `width`/`height` are excluded -- those are component.py::size_css_vars' own
    sizing concern, not a styling one, even though they can appear in the same
    "idSelector" entry as some of these (confirmed on ch5-text: idSelector mixes
    persist:true width/height with persist:false style properties in one list).

    Each entry: `class_name` (the real selector this property is scoped to, e.g.
    ".ch5-button--default .ch5-button--label" -- informational/for a caller
    building a friendly catalog UI; Stage 1 never writes to this selector
    directly, only to the element's own `#id` rule via `target_property`),
    `source_property` (the real CSS property name, e.g. "background-color"),
    `target_property` (the `--ch5-*` custom property to write instead),
    `sector_prefix` (Construct's own property-grid section label, e.g.
    "Appearance_"/"Label_"/"Icon_"), `condition` (raw and unresolved -- see
    resolve_target_property)."""
    mapping = sdk.component_context.get(tag_name, {}).get("classToVariableMapping") or []
    catalog: list[dict] = []
    for entry in mapping:
        class_name = entry.get("className")
        for prop in entry.get("propertyMapping", []):
            target = prop.get("targetProperty")
            source = prop.get("sourceProperty")
            if target is None or source in ("width", "height"):
                continue
            catalog.append({
                "class_name": class_name,
                "source_property": source,
                "target_property": target,
                "sector_prefix": prop.get("sectorPrefix"),
                "condition": prop.get("condition", []),
            })
    return catalog


def resolve_target_property(entry: dict, attributes: dict[str, str]) -> str:
    """Apply `entry`'s condition(s) (same `swaptarget`/`ignore` shape as
    component.py::size_css_vars -- e.g. a button's icon margin swapping sides for
    an RTL trait) against the component's own current attributes, returning the
    real `--ch5-*` custom property name to write. Raises `ValueError` if a
    matching condition says `ignore` -- this property genuinely does not apply
    given the component's current attributes, so silently writing it anyway
    would be a var nothing ever reads."""
    target = entry["target_property"]
    for condition in entry.get("condition", []):
        if attributes.get(condition.get("property")) != condition.get("value"):
            continue
        action = condition.get("action")
        if action == "swaptarget":
            target = condition.get("alternateTargetProperty", target)
        elif action == "ignore":
            raise ValueError(
                f"{entry['source_property']!r} on {entry['class_name']!r} is ignored "
                "for this component's current attributes"
            )
    return target


def find_property(catalog: list[dict], class_name: str, source_property: str) -> dict:
    """The one catalog entry for this (class_name, source_property) pair -- these two
    together are the real key, since `source_property` alone repeats across selectors
    (e.g. "color" on both a button's label and its icon)."""
    matches = [e for e in catalog if e["class_name"] == class_name and e["source_property"] == source_property]
    if not matches:
        raise KeyError(f"No Stage-1 (targetProperty-backed) style property {source_property!r} on selector {class_name!r}")
    return matches[0]


def set_html_attribute(html_text: str, element_id: str, attr_name: str, value: str) -> str:
    """Set (replacing if present, inserting if not) `attr_name="value"` on the ONE
    opening tag in `html_text` whose own `id="element_id"` attribute matches --
    never a descendant's, since a literal `id="{element_id}"` substring match can only
    occur where the closing quote immediately follows, and ids are unique per page/
    widget (see docs/ConstructUISkill.md's "hard requirement" on component names/ids).

    Needed for shape="custom" (see module docstring's border-radius note): unlike
    `set_component_style`, which only ever touches an element's CSS, some Stage-1
    style properties are gated by a plain HTML attribute the schema's own enum doesn't
    list as a valid value (`shape`'s real enum is rounded-rectangle/rectangle/tab/
    circle/oval -- "custom" isn't in it, exactly the same undocumented-but-real pattern
    already established for `size="custom"` in component.py::build_component_attributes).
    Writing `shape="custom"` is what actually lets the border-radius CSS custom
    properties (already resolvable via style_property_catalog under the SAME
    `.ch5-button--rounded-rectangle` selector class regardless of shape's literal
    value) take visible effect, rather than being overridden back to the shape
    preset's own fixed default radius.
    """
    # Deliberately NOT a full attribute-grammar regex (tried first, replaced 2026-09-11):
    # a real live page's devicesVisited attribute was found carrying UNESCAPED embedded
    # quotes (`devicesVisited="["TSW-1070, TSW-1070"]"`, vs. the reference project's
    # properly `&quot;`-escaped form) -- a strict `[\w-]+(?:="[^"]*")?` attribute-by-
    # attribute parse silently fails to match the whole tag the moment it hits that
    # attribute, well before ever reaching `id`. Boundary-finding instead: locate the
    # literal `id="element_id"` text, then walk outward to the nearest `<` before it and
    # the nearest `>` after it. Assumes no attribute VALUE between them contains a
    # literal `<`/`>` itself (true of every attribute value seen in real files so far --
    # enum strings, booleans, colors, JSON-ish arrays -- same pragmatic-boundary
    # assumption this project already makes for CSS declarations in layout.py's
    # `_FLAT_RULE_RE`, not a claim of a general HTML parser).
    id_needle = f'id="{element_id}"'
    id_pos = html_text.find(id_needle)
    if id_pos == -1:
        raise KeyError(f"No opening tag with id={element_id!r} found in this Html text")
    tag_start = html_text.rfind("<", 0, id_pos)
    tag_end = html_text.find(">", id_pos)
    if tag_start == -1 or tag_end == -1:
        raise ValueError(f"Could not locate the opening/closing bracket of the tag with id={element_id!r}")
    tag_end += 1  # include the '>' itself
    tag_text = html_text[tag_start:tag_end]

    attr_re = re.compile(r'(\s' + re.escape(attr_name) + r'=")[^"]*(")')
    if attr_re.search(tag_text):
        new_tag_text = attr_re.sub(rf'\g<1>{value}\g<2>', tag_text, count=1)
    else:
        # Insert right after the tag name -- attribute order carries no meaning here.
        name_end = re.match(r"<[\w-]+", tag_text).end()
        new_tag_text = tag_text[:name_end] + f' {attr_name}="{value}"' + tag_text[name_end:]
    return html_text[:tag_start] + new_tag_text + html_text[tag_end:]


def set_component_style(
    css_text: str,
    element_id: str,
    sdk: UiSdk,
    tag_name: str,
    style_values: list[tuple[str, str, str]],
    *,
    attributes: dict[str, str] | None = None,
) -> str:
    """Apply one or more `(class_name, source_property, value)` style values to
    `element_id`'s CSS, resolved against `tag_name`'s real schema. Written into the
    catch-all (99999px) block's own `#id{...}` rule as `--ch5-*` custom properties --
    the same placement already proven for size (component.py::size_css_vars /
    layout.py::build_position_css's `extra_vars`). Style values are not
    resolution-dependent, so unlike size they only ever need writing once, in the
    catch-all; per-resolution device blocks inherit them via normal CSS cascade.

    `value` is the literal CSS value to write (e.g. "#1a2b3c" for a color, "2px" for
    a border-width, "600" for a font-weight, "solid" for a border-style) -- unlike
    size_css_vars this never appends "px" itself, since these properties are not all
    lengths.
    """
    catalog = style_property_catalog(sdk, tag_name)
    resolved_attributes = attributes or {}
    declarations: dict[str, str] = {}
    for class_name, source_property, value in style_values:
        entry = find_property(catalog, class_name, source_property)
        target = resolve_target_property(entry, resolved_attributes)
        declarations[target] = value
    return layout.update_element_declarations(css_text, CATCH_ALL_QUERY, element_id, declarations)
