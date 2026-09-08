# Multi-resolution reflow — design spec

Date: 2026-09-08
Status: approved by user, ready for implementation plan

## Problem

Construct projects are pixel-adaptive per resolution, not responsive: every component's
position and size is a fixed number of CSS pixels within one resolution's own `@media`
breakpoint (confirmed throughout Phases 3-4). When a project that only has, say, a
1280×800 landscape resolution gains a second, smaller or differently-oriented resolution
(a smaller landscape panel, or a portrait resolution added to a landscape-only project),
nothing about the existing pages/widgets adapts automatically — a component placed near
the right or bottom edge of the original canvas can end up positioned off the new,
smaller canvas entirely. Today `generator/project.py::add_resolutions_to_project`
(Phase 5, first slice) only updates the `.cuip`'s resolution list; it does nothing to the
pages/widgets that already exist. This design covers making that automatic and correct.

## Scope

**In scope:**
- Reflowing existing pages' and widgets' component positions/sizes when
  `add_resolutions_to_project` adds one or more new resolutions.
- Both landscape→landscape (or portrait→portrait) reflow (scale from that orientation's
  own existing primary) and the orientation-bootstrap case (first resolution ever added
  in an orientation the project didn't have yet — scale from the *other* orientation's
  primary).
- Both `.cuig` (pages) and `.cuiw` (widgets) — same CSS shape, same reflow logic.

**Out of scope (this design):**
- Resolution *removal* — needs no reflow math, just deleting that resolution's `@media`
  block.
- Shrink-to-fit — the off-canvas correction pass only ever repositions (clamps), never
  resizes a component, even if it doesn't fit after clamping to the top-left corner.
- Reflowing hand-authored/non-generator CSS (e.g. the reference project's own
  `Component - Button.cuig`, which has complex, manually-edited rules). Reflow only
  understands the flat, one-`#id{...}`-rule-per-component shape this generator itself
  produces (`layout.py::build_position_css`'s output).
- Re-reflowing on every edit (e.g. after a user moves a component in Construct) — this
  design only covers the moment a resolution is *added*.

## Data model

Position/size is CSS-only (never TOML — confirmed in Phase 4). A page/widget's
`{Css}` `99999px` catch-all block is the single source of truth for "where is
everything right now," because a resolution's own dedicated `@media` block always
mirrors the catch-all block's values exactly at creation time (confirmed against real
Button1 and `Widget.cuiw`). Reflow parses that block back into:

```python
{element_id: {"left": int, "top": int, "width": int, "height": int,
              "z_index": int | None, "extra_vars": {css_var_name: int}}}
```

`extra_vars` covers component-specific size-mirroring custom properties (e.g.
`--ch5-button--regular-width`/`-height`, see Phase 4) — scaled identically to the
`width`/`height` they mirror, carried through unset (default → unset) otherwise.

Only the flat `#id{ prop: value; ... }` top-level rules are parsed; nested/child
selectors (e.g. the `.ch5-button :not(i):not(svg)` theme font-family rule) are left
alone — they carry no position data and don't need scaling.

## Algorithm

Given a page/widget's parsed catch-all elements, a **source** resolution (width×height)
and a **target** (the newly-added resolution, width×height):

1. `scale_x = target_width / source_width`, `scale_y = target_height / source_height`.
2. For each element: `new_left = round(left * scale_x)`, `new_top = round(top * scale_y)`,
   `new_width = round(width * scale_x)`, `new_height = round(height * scale_y)` (and each
   `extra_vars` entry scaled by whichever axis its own property — width or height —
   corresponds to).
3. Off-canvas clamp: if `new_left + new_width > target_width`, set
   `new_left = max(0, target_width - new_width)`; symmetric for `new_top`/`new_height`
   against `target_height`. This never changes `new_width`/`new_height` — a component
   wider/taller than the entire target canvas still overflows on the right/bottom after
   clamping to 0, which is the accepted last resort.
4. Emit one new `@media {landscape_media_query(target_width, target_height)}` block
   (reusing `layout.py::landscape_media_query`) containing one `#id{...}` rule per
   element with the corrected values — the SAME per-element rule shape
   `layout.py::build_position_css` already produces for the device-specific block, just
   generalized to emit N elements in one pass instead of being called once per
   newly-created element. The existing `99999px` catch-all block is never touched.

## Choosing the source resolution

- If the project already has at least one resolution in the *new* resolution's
  orientation, the source is that orientation's own primary (highest width in that
  orientation) — its already-fitted content is the right basis.
- If this is the first resolution ever added in that orientation (a brand-new
  orientation for the project), the source is the *other* orientation's primary instead.
  The per-axis formula above handles the swap correctly on its own (landscape's
  width-axis scale becomes portrait's own width-axis scale, etc.) — no special-cased
  math, just a different source block chosen once per call.
- "Primary" resolution selection (highest width per orientation) reuses
  `generator/devices.py`-shaped resolution dicts already stored in the project's
  `{DeviceResolutionSource}` (read via `project.py::read_cuip`).

## Integration

`add_resolutions_to_project(cuip_path, new_resolutions)` — after writing the updated
`.cuip` (existing behavior, unchanged) — walks every `*.cuig`/`*.cuiw` file in the
project's own folder and, for each *newly-added* resolution, adds a correctly-reflowed
`@media` block to that file (one call per file per new resolution). One user-facing
operation, matching the spec's own wording ("add/remove resolutions and reflow the
project as required") and your explicit choice not to split it into two steps.

## Components (new/changed code)

- **`generator/layout.py`** (extend, don't replace): add `parse_position_rules(css_text)
  -> dict[element_id, ParsedElement]` (the flat-rule parser described above) and
  `build_reflow_block(elements, resolution) -> str` (the N-element `@media` block
  builder, factored so `build_position_css`'s device-block logic can share it for the
  single-element case it already handles).
- **`generator/reflow.py`** (new): `reflow_file(path, source_resolution, target_resolution)
  -> None` — read the file's `{Css}` (and `{PageAttributes}`/`{Html}` — needed to
  re-write the file, but untouched), parse, scale+clamp, append the new block, write
  back. `pick_primary(resolutions, orientation) -> dict | None` and
  `choose_source_resolution(existing_resolutions, new_resolution) -> dict` implement the
  "which resolution do we scale from" rule above, generic over `devices.py`-shaped
  resolution dicts.
- **`generator/project.py::add_resolutions_to_project`** (extend): after the existing
  `.cuip` write, call `reflow.reflow_file` for every `*.cuig`/`*.cuiw` in
  `cuip_path.parent`, once per newly-added resolution.

## Error handling

- A page/widget whose catch-all block doesn't parse cleanly (non-generator CSS, or a
  component with no position rule at all) is skipped with a clear message identifying
  the file and element — never silently dropped, never a hard crash that aborts
  reflowing the *rest* of the project's files.
- Adding a resolution that's already orientation-primary-less on both sides (a
  brand-new project with zero prior resolutions) is not a reflow case at all — nothing
  to scale from, nothing to reflow; `add_resolutions_to_project` already handles the
  "starts with zero resolutions" case for the `.cuip` itself (Phase 5 first slice) and
  reflow simply does nothing when there are no *existing* resolutions to have placed
  content at.

## Testing

- Unit-level: `parse_position_rules` round-trips a known CSS string into the expected
  dict; `build_reflow_block` produces the expected CSS for a known element dict +
  resolution; `choose_source_resolution` picks the right primary for same-orientation vs.
  bootstrap-new-orientation cases.
- Scenario tests (the real point of this feature): build a synthetic page with a
  component deliberately placed near the right/bottom edge of a 1280×800 landscape
  canvas, add a smaller landscape resolution (e.g. 640×360, TSW-570) and confirm the
  component's new coordinates are both scaled AND fully on-canvas; separately add a
  portrait resolution to a landscape-only project and confirm the bootstrap case
  produces sane on-canvas coordinates.
- Round-trip every produced file through `harness/compare.py`, per this project's
  standing verification requirement.
- Manual Construct verification: add a real second (smaller or portrait) resolution to
  the on-disk `C:\Solutions\ClaudeGenTest\GenTestProject` verification project and have
  the user confirm in Construct that switching to the new resolution shows components
  correctly positioned on-canvas, not clipped off the edge.
