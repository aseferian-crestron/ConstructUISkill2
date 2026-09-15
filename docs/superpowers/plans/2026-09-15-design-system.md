# Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `docs/ConstructUISkill_DesignSystem.md`'s 9-section policy (color, type,
spacing, states, shape, density, layout patterns, cross-resolution consistency, and
"how the skill applies defaults") into real generator code, so the skill can produce a
professional, consistent touch-panel UI when a user gives no design direction, not just
when they hand it exact values.

**Architecture:** Small, focused modules extending the existing per-concern split
(`palette.py` for color, a new `spacing.py` for §4, etc.), reusing the two mechanisms
already proven for writing styling into `.cuig`/`.cuiw` files: `style.py::set_component_style`
(the Stage-1 real-schema-catalog writer) and `layout.py::update_element_declarations`
(catch-all + primary-resolution-block rule). §1's Layout Patterns is the one genuinely
new piece — no header/footer/menu-widget-building orchestration exists yet — everything
else is a policy layer on top of already-built plumbing.

**Scope note (writing-plans Scope Check):** these 9 sections are not one subsystem —
color, typography, spacing, layout orchestration, and density are independently
shippable. This single document sequences all of them as phases (mirroring the design
doc's own §1–§9 structure) rather than splitting into separate plan files, since that
structure already IS the subsystem boundary. **Only Phase 1 is detailed to
step-by-step TDD code below.** Phases 2–8 are scoped as concrete tasks (real files,
function signatures, and what's confirmed vs. still needs a `C:\Git\CCIDE` source
check) but not fully written — matching this project's own established convention
(`docs/architecture/01-index.md`: "written just-in-time when the phase that needs it
starts, not speculatively ahead of that"). Detail the next phase the same way Phase 1
is detailed here, immediately before starting it.

**Tech Stack:** Python 3, no new dependencies. Test convention: standalone scripts
under `generator/_test_output/`, run directly with `python <file>.py` (no pytest; a
test passes when it prints its OK lines and exits 0 — see any existing `*_test.py` in
that folder, e.g. `global_widget_test.py`, for the exact house style: module docstring
citing what's confirmed vs. a policy call, plain `assert`, a print per assertion
group, a final "all assertions passed" line).

**Spec:** `docs/ConstructUISkill_DesignSystem.md` (the design-system policy this plan
implements) + `docs/ConstructUISkill.md` (the base feature spec, §5's hard
requirements) + `README.md`'s Log for current generator state.

## Global Constraints

- **Source-grounded, not inferred**, per this project's core approach (see `README.md`'s
  2026-09-03 entry): before writing any code that claims a Construct file-format fact
  (a new stylable CSS var, a new attribute, a new selector shape), confirm it against
  `C:\Git\CCIDE` source or a real reference project, the same way `page.py`'s
  `is_global` parameter was confirmed against `WidgetDto.cs`/`SubpageTemplate.json`/
  `GlobalSubpageConverter.cs` before being written. A task below marked **NEEDS SOURCE
  CHECK** must not be implemented until that check happens — it is not a placeholder to
  skip, it is the task's actual first step.
- **Pure policy is exempt from source-grounding.** Some of this plan (spacing scale,
  touch-target minimum, density ceilings, color-role derivation) is the skill's own
  design judgment, not a Construct fact — nothing to confirm against source for those,
  same precedent as `palette.py::derive_states`' pressed/selected lightness deltas.
- **README.md's Log gets an entry in the same turn as any completed task** — this
  project's own hard rule (`README.md` line 3-4), not unique to this plan.
- **Every task's test is a standalone script under `generator/_test_output/`**, following
  the Tech Stack section above. `generator/_test_output/` is gitignored except the
  `*_test.py` scripts themselves (`.gitignore`, fixed 2026-09-15) — running a test will
  create output files that do NOT need `git add`.
- **Backward compatibility:** every new parameter on an existing function defaults to
  today's exact behavior (see `page.py::default_widget_html_css`'s `is_global: bool =
  False` precedent) — no existing test in `generator/_test_output/` may change behavior
  because of this plan unless a task explicitly says so.

---

## Phase 1: Foundation — Spacing/Touch-Target Scale (§4) + Contrast Check (§2)

Two prerequisite-free, pure-policy pieces every later phase (layout placement, color
roles) will call into. No Construct source-grounding needed — see Global Constraints.

### Task 1: `generator/spacing.py` — spacing unit + touch-target floor

**Files:**
- Create: `generator/spacing.py`
- Test: `generator/_test_output/spacing_test.py` (new)

**Interfaces:**
- Produces: `SPACING_UNIT: int` (= 8); `MIN_TOUCH_TARGET: int` (= 44); `EDGE_PADDING: int`
  (= 16); `snap_to_spacing(value: int) -> int`; `meets_touch_target(width: int, height:
  int) -> bool`; `enforce_touch_target(width: int, height: int) -> tuple[int, int]`

- [ ] **Step 1: Write the failing test**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spacing import (
    SPACING_UNIT, MIN_TOUCH_TARGET, EDGE_PADDING,
    snap_to_spacing, meets_touch_target, enforce_touch_target,
)

assert SPACING_UNIT == 8
assert MIN_TOUCH_TARGET == 44
assert EDGE_PADDING == 16  # a spacing-scale multiple, per §4's edge/safe-zone rule

assert snap_to_spacing(0) == 0
assert snap_to_spacing(3) == 0
assert snap_to_spacing(4) == 8
assert snap_to_spacing(5) == 8
assert snap_to_spacing(12) == 16
assert snap_to_spacing(20) == 24
print("snap_to_spacing: rounds to nearest 8px multiple: OK")

assert meets_touch_target(44, 44) is True
assert meets_touch_target(60, 44) is True
assert meets_touch_target(43, 44) is False
assert meets_touch_target(44, 43) is False
print("meets_touch_target: both axes checked independently: OK")

assert enforce_touch_target(30, 30) == (44, 44)
assert enforce_touch_target(44, 20) == (44, 44)
assert enforce_touch_target(60, 60) == (60, 60)
assert enforce_touch_target(60, 30) == (60, 44)
print("enforce_touch_target: clamps up to the floor, never shrinks an already-larger axis: OK")

print("Spacing scale: all assertions passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/spacing_test.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'spacing'`

- [ ] **Step 3: Write minimal implementation**

```python
"""
Design-system spacing/sizing scale (ConstructUISkill_DesignSystem.md §4) -- the
skill's own POLICY, not a Construct file-format fact, so there is nothing to confirm
against C:\\Git\\CCIDE here: these are defaults the generator applies when
placing/sizing components, the same way palette.py's derive_states applies a
standard-practice default rather than a schema-derived one.

SPACING_UNIT: every margin, padding, and gap a multiple of this.
MIN_TOUCH_TARGET: Apple HIG's 44pt floor (Material's 48dp is the other common
reference point; 44 is the doc's own default, kept as a single named constant so a
project can override it without touching call sites).
EDGE_PADDING: the minimum margin between the outermost controls and the panel's own
bezel -- one spacing-scale multiple, not an independent value.
"""
from __future__ import annotations

SPACING_UNIT = 8
MIN_TOUCH_TARGET = 44
EDGE_PADDING = SPACING_UNIT * 2


def snap_to_spacing(value: int) -> int:
    """`value` rounded to the nearest multiple of SPACING_UNIT (ties round up).

    Not `round(value / SPACING_UNIT) * SPACING_UNIT`: Python's `round()` is
    round-half-to-even ("banker's rounding"), so that expression sends 4 to 0, not
    8 -- wrong for a spacing scale, where ties should round up like everyday rounding.
    """
    return ((value + SPACING_UNIT // 2) // SPACING_UNIT) * SPACING_UNIT


def meets_touch_target(width: int, height: int) -> bool:
    """Whether a component's full tappable area (not just its visible icon/label)
    meets the minimum touch-target floor on BOTH axes independently."""
    return width >= MIN_TOUCH_TARGET and height >= MIN_TOUCH_TARGET


def enforce_touch_target(width: int, height: int) -> tuple[int, int]:
    """`(width, height)` clamped UP to MIN_TOUCH_TARGET on any axis below it. Never
    shrinks an axis that already meets the floor -- this is a floor, not a fixed
    size."""
    return max(width, MIN_TOUCH_TARGET), max(height, MIN_TOUCH_TARGET)
```

**Deviation from plan (found during execution):** the first draft used
`round(value / SPACING_UNIT) * SPACING_UNIT`, which sent `snap_to_spacing(4)` to `0`
instead of `8` -- Python's `round()` is round-half-to-even. Fixed to
`((value + SPACING_UNIT // 2) // SPACING_UNIT) * SPACING_UNIT` (floor-based
round-half-up). Test step 1 (RED) is unchanged; this only affects the Step 3
implementation shown above, already corrected.

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/spacing_test.py`
Expected: PASS (all four print lines + "Spacing scale: all assertions passed.")

- [ ] **Step 5: Commit**

```bash
git add generator/spacing.py generator/_test_output/spacing_test.py
git commit -m "feat: add design-system spacing unit + touch-target floor (§4)"
```

---

### Task 2: `generator/color_words.py::contrast_ratio` — WCAG 2.1 contrast math

**Files:**
- Modify: `generator/color_words.py` (add after `adjust_lightness`)
- Test: `generator/_test_output/contrast_ratio_test.py` (new)

**Interfaces:**
- Consumes: `color_words._hex_to_rgb(hex_color: str) -> tuple[int, int, int]` (already
  exists, line 76)
- Produces: `contrast_ratio(hex_a: str, hex_b: str) -> float` (order-independent, 1.0–21.0)

- [ ] **Step 1: Write the failing test**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from color_words import contrast_ratio

assert abs(contrast_ratio("#ffffff", "#000000") - 21.0) < 0.01, "white/black must be the maximum 21:1"
assert abs(contrast_ratio("#000000", "#ffffff") - 21.0) < 0.01, "order must not matter"
assert abs(contrast_ratio("#ffffff", "#ffffff") - 1.0) < 0.01, "identical colors must be the minimum 1:1"

# #767676 on white is the textbook "just barely passes AA normal text" gray (~4.54:1)
ratio = contrast_ratio("#767676", "#ffffff")
assert 4.5 <= ratio < 4.6, ratio
print(f"contrast_ratio: known WCAG reference pairs match (white/black=21:1, #767676/white={ratio:.2f}:1): OK")

print("Contrast ratio: all assertions passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/contrast_ratio_test.py`
Expected: FAIL with `ImportError: cannot import name 'contrast_ratio'`

- [ ] **Step 3: Write minimal implementation** (append to `generator/color_words.py`)

```python
def _relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance -- the exact formula behind the 4.5:1/3:1 contrast
    thresholds this module's callers check against (see contrast_ratio)."""
    r, g, b = _hex_to_rgb(hex_color)

    def _channel(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_lin, g_lin, b_lin = _channel(r), _channel(g), _channel(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2.1 contrast ratio between two colors (1:1 minimum, 21:1 maximum),
    order-independent. Design-system §2's contrast rule checks this against 4.5:1
    (normal text) / 3:1 (large text)."""
    l1 = _relative_luminance(hex_a)
    l2 = _relative_luminance(hex_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/contrast_ratio_test.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add generator/color_words.py generator/_test_output/contrast_ratio_test.py
git commit -m "feat: add WCAG contrast_ratio to color_words.py (§2)"
```

---

### Task 3: `generator/palette.py::check_contrast` — apply the rule to a resolved palette

**Files:**
- Modify: `generator/palette.py` (add after `derive_states`)
- Test: `generator/_test_output/palette_contrast_test.py` (new)

**Interfaces:**
- Consumes: `color_words.contrast_ratio(hex_a: str, hex_b: str) -> float` (Task 2)
- Produces: `MIN_CONTRAST_RATIO: float` (= 4.5); `check_contrast(resolved_palette: dict[str,
  str]) -> tuple[bool | None, float | None]`

- [ ] **Step 1: Write the failing test**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from palette import check_contrast

# White text on Cornell Carnelian red -- the real palette from this project's live
# Cornell theming session (README.md, 2026-09-13 entry). Passes AA normal text.
passing = {"background_color": "#B31B1B", "text_color": "#FFFFFF"}
ok, ratio = check_contrast(passing)
assert ok is True and ratio >= 4.5, (ok, ratio)
print(f"check_contrast: white on Cornell Carnelian passes AA normal text ({ratio:.2f}:1): OK")

# Near-white text on white -- a real failure case, must report False with its actual ratio.
failing = {"background_color": "#FFFFFF", "text_color": "#F7F7F7"}
ok2, ratio2 = check_contrast(failing)
assert ok2 is False and ratio2 < 4.5, (ok2, ratio2)
print(f"check_contrast: near-white text on white correctly fails AA ({ratio2:.2f}:1): OK")

# A palette missing either key can't be checked -- must return (None, None) rather
# than raise or silently assume a default color.
incomplete = {"background_color": "#B31B1B"}
assert check_contrast(incomplete) == (None, None)
print("check_contrast: missing background_color or text_color returns (None, None): OK")

print("Palette contrast check: all assertions passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/palette_contrast_test.py`
Expected: FAIL with `ImportError: cannot import name 'check_contrast'`

- [ ] **Step 3: Write minimal implementation** (append to `generator/palette.py`, after
  `derive_states`)

```python
#: WCAG AA normal-text minimum -- design-system §2's contrast rule. (Large-text's 3:1
#: floor is not checked here yet: this project has no notion of "large text" separate
#: from §3's type scale, which is a later phase -- see the plan.)
MIN_CONTRAST_RATIO = 4.5


def check_contrast(resolved_palette: dict[str, str]) -> tuple[bool | None, float | None]:
    """Whether `resolved_palette`'s text_color meets MIN_CONTRAST_RATIO against its own
    background_color (design-system §2's contrast rule). Returns (None, None) if either
    key is missing -- there is nothing to check, not a failure."""
    background = resolved_palette.get("background_color")
    text = resolved_palette.get("text_color")
    if background is None or text is None:
        return None, None
    ratio = color_words.contrast_ratio(background, text)
    return ratio >= MIN_CONTRAST_RATIO, ratio
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/palette_contrast_test.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add generator/palette.py generator/_test_output/palette_contrast_test.py
git commit -m "feat: check text/background contrast against WCAG AA (§2)"
```

---

## Phase 2: Color Roles (§2 continued) — DONE (2026-09-15)

Primary/secondary/accent hierarchy, semantic colors, neutral scale. 2 tasks, 2 commits:

- `color_words.py::adjust_saturation`/`rotate_hue` (same HSL round-trip as
  `adjust_lightness`) + `palette.py::resolve_color_roles(primary, secondary=None,
  accent=None) -> dict[str, str]` — secondary = desaturated primary
  (`SECONDARY_SATURATION_DELTA = -0.45`), accent = a 30° analogous hue shift
  (`ACCENT_HUE_ROTATION_DEGREES = 30`), both explicit judgment calls (documented as
  such, same precedent as `derive_states`), never overriding an explicit value.
- `palette.py::SEMANTIC_COLORS` (success/warning/error/info) + `NEUTRAL_SCALE` (3
  grays) — fixed conventions, folded into one task since neither has real logic.
  `NEUTRAL_SCALE`'s light/mid/dark ordering verified via real WCAG relative
  luminance (`color_words._relative_luminance`), not eyeballed.

No regressions in `palette_test.py`/`contrast_ratio_test.py`/`palette_contrast_test.py`
across either task.

## Phase 3: Interaction States — disabled (§5 continued) — DONE, NOT BUILDABLE (2026-09-15)

Source check run as planned, before writing any code: `style.style_property_catalog`
checked for every currently-mapped type (`ch5-button`, `ch5-toggle`, `ch5-dpad`,
`ch5-signal-level-gauge`, `ch5-slider`) — ZERO `disabled`-scoped entries across all
five, versus dozens for `pressed`/`selected`. A raw search of `ch5-button`'s
`component-context.json` confirms `disabled` appears only as a plain attribute
default, never inside `classToVariableMapping`. **Conclusion: not a gap to fill later,
a real platform limit** — whatever visual change a disabled component gets is baked
into the CH5 component library's own internal styling, not exposed for custom-mode
override. No `derive_disabled_state()` task exists; there is nothing for the
generator to write. `docs/ConstructUISkill_DesignSystem.md` §5 updated to record this
so a future session doesn't re-attempt it.

## Phase 4: Typography Scale (§3) — scoped, not detailed

**NEEDS SOURCE CHECK first:** whether `font-size` is a real `targetProperty`-backed
style for text-bearing types (`ch5-text`, `ch5-button`'s label, etc.) — `style.py`'s
module docstring already flags that some properties have NO `targetProperty` (the
precedent: border-radius corners needed special handling, `style.py:29`). Run
`style.style_property_catalog` per relevant tag before assuming font-size is
stylable via the existing mechanism at all.

- **Task:** confirm font-size stylability per tag.
- **Task:** `typography.py::TYPE_SCALE: dict[str, int]` (title/heading/body/label/
  caption, body defaulting ~22px per the design doc) once confirmed stylable, or a
  documented fallback (e.g. a min-readable-size WARNING rather than a write) if not.

## Phase 5: Elevation & Shape (§6) — scoped, not detailed

Border-radius: LOW risk, reuses the already-confirmed mechanism
(`generator/_test_output/custom_shape_test.py` — 4 CSS vars via
`style.set_component_style`, gated by `shape="custom"`). Shadow/elevation: **NEEDS
SOURCE CHECK** — the design doc itself flags this as uncertain ("a border/
background-contrast substitute where CH5 doesn't support real shadows"); grep
`style_property_catalog` across component types for any shadow/elevation-like
property before assuming one exists.

- **Task:** `shape.py::RADIUS_PRESETS = {"sharp": 0, "subtle": 4, "rounded": 12}` (px,
  applied to all 4 corners via the existing mechanism) — button confirmed; check
  applicability for other stylable types before extending.
- **Task:** confirm whether any shadow/elevation-like `targetProperty` exists at all;
  if not, implement the border/background-contrast substitute via
  `palette.py::apply_palette`, not a new mechanism.

## Phase 6: Information Density & Hierarchy (§7) — scoped, not detailed

Not a file-format writer — an advisory/validation layer the skill runs and reports to
the user, no Construct source-grounding needed.

- **Task:** `density.py::DENSITY_CEILINGS: dict[str, int]` (panel size class → max
  component count) + `check_density(component_count: int, panel_diagonal_in: float) ->
  list[str]` (returns warnings, writes nothing).
- **Task:** "one dominant action per screen" — likely folds directly into Phase 7's
  layout-pattern builders (e.g. Bento Box's largest card) rather than a standalone
  function; decide the real shape when Phase 7 starts rather than guessing a signature
  now (YAGNI — this project's own precedent, e.g. `palette.py`'s module docstring
  explicitly rejecting a premature generic mechanism in favor of building one verified
  case at a time).

## Phase 7: Layout Patterns (§1) — scoped, not detailed

The one genuinely new orchestration layer — no header/footer/menu-widget-building code
exists yet. Start with ONE pattern end-to-end (Header-Content-Footer — "the default,
safest... fallback when no other pattern is a clearly better fit," design doc §1);
the other four patterns follow the same shape once this one is proven, same
incremental precedent as `palette.py`'s "one verified type at a time."

- **Task:** `layout_patterns.py::build_header_widget(...)` /
  `build_footer_widget(...)` — compose `page.py::build_widget_attributes` +
  `page.py::default_widget_html_css(..., is_global=True)` (§5's hard requirement,
  landed 2026-09-15) + `component.py::build_component` calls for child buttons/labels,
  applying Phase 1's `spacing.enforce_touch_target`/`snap_to_spacing` to every child's
  placement.
- **Task:** `layout_patterns.py::choose_layout(item_count: int, is_commercial: bool,
  panel_is_landscape: bool) -> str` — pure decision function implementing §1's
  "Choosing a Layout" order (Residential/Commercial → item count → panel size).
- **Acceptance criterion (§8 Cross-Resolution Consistency):** already-built
  infrastructure (`reflow.py`, `layout.py::update_element_declarations`'s catch-all +
  primary rule) must be exercised by whatever this phase builds at every configured
  resolution, not just the primary one — no new code needed for §8 itself, this is a
  test requirement on Phase 7's own output.

## Phase 8: §9 — How the Skill Applies These Defaults — scoped, not detailed

Capstone; genuinely cannot be detailed until Phases 1–7 exist to call into.

- **Task:** `design_system.py::apply_defaults(project_dir: Path, *, commercial: bool,
  brand_color: str | None = None) -> dict` — when the user gives no/partial design
  direction, resolves color roles (Phase 2), picks a layout (Phase 7's
  `choose_layout`), and applies type/spacing/shape defaults (Phases 1/4/5) project-wide,
  the same "resolve once, apply everywhere" shape `theme_chat.py` already uses for
  chat-described theming.

---

## Self-Review

- **Spec coverage:** §1→Phase 7, §2→Phase 1 (contrast) + Phase 2 (roles), §3→Phase 4,
  §4→Phase 1, §5→already built (states) + Phase 3 (disabled, confirmed not
  buildable), §6→Phase 5, §7→Phase 6,
  §8→already built, acceptance criterion on Phase 7, §9→Phase 8. Every section has a
  task or an explicit "already built, no task needed."
- **Placeholder scan:** Phase 1's 3 tasks contain full real code, no TBD/"add
  appropriate handling"/"similar to Task N" patterns. Phases 2–8 are deliberately
  scoped-not-detailed per the header's Scope note — each still names real files,
  function signatures, and existing precedents to reuse, and flags exactly which
  pieces need a source check before any code is written, rather than leaving a bare
  "implement this" with no shape.
- **Type consistency:** `spacing.enforce_touch_target`'s `(width, height) ->
  tuple[int, int]` is the exact shape Phase 7's task references it by; `color_words
  .contrast_ratio(hex_a, hex_b) -> float` is what `palette.check_contrast` (Task 3)
  and Phase 2's role work both consume.

---

Plan complete and saved to `docs/superpowers/plans/2026-09-15-design-system.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
