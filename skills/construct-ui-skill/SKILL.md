---
name: construct-ui-skill
description: Create and modify Crestron Construct UI projects (.cuip/.csln) via natural language, built from schema-grounded primitives (generator/*.py in this repo) rather than donor-file cloning. Currently covers copying an existing project (e.g. the Design Ideas template) into a solution as a new project, adding a subsystem popup+page to a Design-Ideas-derived project, and editing that project's real footer menu (add/remove/reflow the Menu_*/DividerGroup* icons in Footer - Main.cuiw, both landscape and portrait). Use whenever the user asks to copy, clone, or modify a Crestron Construct UI project in ways this document covers.
---

# Construct UI Skill (v2)

You are a Crestron Construct UI project generator, working directly against
this repo's own `generator/*.py` modules (not a packaged plugin yet -- see
"Status of this document" below). Every module here is grounded against the
real CH5 SDK schema and/or real, already-authored Construct files -- never
guessed. Where this document names a real measured constant (a pixel
position, a color, a gap), it came from reading an actual file, not from
inventing a plausible-looking value.

## Status of this document

This is a v2 REBUILD of an earlier, more complete skill (the currently-
installed `crestron-construct-skills` plugin, `C:\Users\<user>\.claude\
plugins\marketplaces\crestron-construct-skills\skills\construct-ui-skill\
SKILL.md`) that worked by cloning donor skeleton files. v2 replaces that
donor-cloning mechanism with schema-grounded, from-scratch construction --
but v2's own capability surface is still narrower than v1's. **Only follow
the sections below; do not assume any v1 capability not restated here
exists in v2 yet** (no base "generate a brand-new project from scratch" CLI,
no source-control widgets, no global modals, no branding/background-image
swap, no `--validate` equivalent). When a user asks for something v1 could
do that isn't in this document, say so plainly and either fall back to the
v1 plugin (if genuinely equivalent) or treat it as a real gap to build next,
per this project's own README.md "not yet built" notes -- never silently
improvise a mechanism this document doesn't already describe.

## Running generator code

This repo's `generator/` modules are plain Python, imported directly --
there is no CLI wrapper yet (unlike v1's `generate-project.py`). Run via the
Bash tool:

```python
import sys
sys.path.insert(0, r"C:\ClaudeProjects\ConstructUISkill2\generator")
sys.path.insert(0, r"C:\ClaudeProjects\ConstructUISkill2\harness")
import sdk as sdk_module
ui_sdk = sdk_module.read_sdk("2.18.0")
```

Always verify a write with `compare.round_trip_check(path)` (from
`harness/compare.py`) before treating it as done -- every deliverable in
this repo's own README.md was confirmed this way, not assumed correct
because it didn't raise.

---

## Step 0: Detect Context

Same real, confirmed environment behavior as v1: when working inside an
open solution, the working directory (or a path the user gives you) is the
solution's own folder -- a project's `.cuip` lives one level below it, in
its own subfolder.

**0a. Find the solution.** Look for exactly one `*.csln` in the relevant
directory. Read it with `solution.py::read_solution`:
```python
from pathlib import Path
from solution import read_solution
sol = read_solution(Path(r"<path>\Solution.csln"))
print(sol.name, [p.name for p in sol.projects])
```

**0b. Determine which project the user means.** If the request already
names one of `sol.projects`, use it directly. If the solution has no
projects yet, or the user wants a NEW one, go to **Copying an Existing
Project** below. Otherwise ask via `AskUserQuestion` which project, listing
every real name from `sol.projects`.

**0c. Determine Design Ideas template status.** Gate every Design-Ideas-
specific step (everything in **Adding a Subsystem** below) on this check --
don't infer it from how the project was created:
```python
from design_ideas_subsystem import design_ideas_learn_project_shared
try:
    shared = design_ideas_learn_project_shared(PROJECT_DIR)
    IS_DESIGN_IDEAS_TEMPLATE = True
except ValueError:
    IS_DESIGN_IDEAS_TEMPLATE = False
```
(This differs from v1's file-grep check -- v2 confirms it the same way it
confirms everything else: by successfully reading the project's own real
shared-widget structure, not a marker string.)

**Staying on a project:** once resolved, it stays active for the rest of
the conversation -- don't re-ask or re-run Step 0 unless the user
explicitly wants a different project or solution.

---

## Copying an Existing Project

This is v2's equivalent of v1's "Running the Cloner" / "Add Existing
Project as a Copy" -- and it's the REAL mechanism, not an approximation:
traced directly through Construct's own source (`AddProjectCopyEffect.cs` →
`AddProjectCopyHandler.cs` → `ProjectSaveAsHandler.cs`,
`uiEditorProject.DeepCopy(newGuids: true)`) and reproduced at the file
level -- every page/widget/asset in the copy gets a fresh GUID, every
cross-reference updated consistently, exactly like Construct's own real
"Add Existing Project as a Copy."

**Always ask for the source project's location explicitly -- never assume
or hardcode a path** for a general "copy this project" request (a specific
path like `C:\Solutions\CrestronDesignIdeas\BasicTemplate_v1_0_2` is this
machine's own, not a constant to bake into code).

**Exception: when the user specifically says "the Design Ideas template"**
(by that name, not an arbitrary project) -- check Construct's own real
Sample Projects folder FIRST, before asking. Grounded directly in
`C:\Git\CCIDE\Crestron.IDE\AppHost\Crestron.IDE\Common\Utils\
EnvironmentUtility.cs` (`CreateInternalAppEnvironment`) and `Common\
Constants.cs` (`ApplicationName = "Crestron Construct"`): Construct's own
per-user content folder is `<Documents>/Crestron/Crestron Construct`
(`Environment.SpecialFolder.MyDocuments` + `"Crestron"` + the app name,
identical join logic on both platforms -- only how the OS resolves
`MyDocuments` differs).

**Do NOT compute `<Documents>` as a naive path join (`~/Documents` or
`Path.home() / "Documents"`) -- confirmed a real bug live, 2026-09-18: this
user's actual Documents folder is OneDrive-redirected
(`C:\Users\<user>\OneDrive - <org>\Documents`), which a naive join silently
misses (no error, just checks the wrong, non-existent-content folder and
wrongly concludes "not found").** Ask the OS for its real answer instead,
the same way Construct's own C# does via `Environment.GetFolderPath`:
- **Windows** -- shell out to PowerShell rather than guess in Python:
  ```powershell
  [Environment]::GetFolderPath('MyDocuments')
  ```
- **macOS** -- `Path.home() / "Documents"` is the normal case (no
  general-purpose redirection API the way Windows has KFM), but treat it as
  a starting assumption, not a guarantee -- if nothing is found there AND
  the user says they know they have it, ask rather than conclude it doesn't
  exist.

Then join `Crestron/Crestron Construct/SampleProjects` onto whatever that
real path is, and look inside for a project folder whose name suggests the
Design Ideas template (e.g. containing "DesignIdeas" or "BasicTemplate",
case-insensitive). CONFIRM it with the user before using it -- same "never
silently apply a guess" discipline this document uses everywhere else, not
an auto-pick.

**If nothing is found there, ask for the path directly, exactly like the
general case below** -- don't guess further or search anywhere else.

Ask, in order:
1. "What's the full path to the project you want to copy?" → `SOURCE_PROJECT_DIR`
   (skip this if the Sample Projects check above already found and confirmed
   a match; verify it contains a `.cuip` before continuing either way).
2. "Should this go into a new solution, or an existing one?"
   - **New solution:** ask for a name and a folder path, then
     `solution.create_solution(dest_dir, name)`.
   - **Existing solution:** ask for the `.csln` path, `solution.read_solution(...)`.
3. "What should the new project be named?" → `NEW_PROJECT_NAME` (must not
   already exist in the target solution -- `solution.find_project(name)`).

Then:
```python
from project_copy import copy_project_as
from solution import add_project_to_solution

new_cuip = copy_project_as(SOURCE_PROJECT_DIR, dest_solution.solution_dir, NEW_PROJECT_NAME)
add_project_to_solution(dest_solution, NEW_PROJECT_NAME, new_cuip)
```

`copy_project_as` raises `FileNotFoundError` if the source has no `.cuip`,
`FileExistsError` if the destination project name is already taken --
report either plainly and ask what to do, don't retry blindly.

**After copying, verify before reporting success** (this repo's own
discipline, not optional): spot-check a few round-trips and confirm no
source GUID leaked into the copy:
```python
import compare
for p in list(new_cuip.parent.glob("*.cuig"))[:3]:
    assert compare.round_trip_check(p)
```
Report the new project's location and that it's registered in the target
solution. Remind the user to open the `.csln` in Construct to see it live.

---

## Adding a Subsystem (Design Ideas projects only)

Gate on `IS_DESIGN_IDEAS_TEMPLATE` from Step 0c. **This workflow is
PARTIAL -- say so up front if the user asks for the whole thing in one
request.** What's done and real-file-tested:

- Building the popup content widget -- header (icon + title + close) + N
  groups, each either a plain list of theme-mode control buttons, a D-pad
  cross (`design_ideas_dpad_group()`), a scrollable contract-driven list
  (`design_ideas_button_list_group(num_items)`), or a numeric keypad
  (`design_ideas_keypad_group(display=...)`) -- plus an optional
  `message=` for a warning/alert-dialog shape (header + message + Close,
  `groups=[]`). See `generator/design_ideas_subsystem.py`'s own module
  docstring and each group-marker's docstring for exactly what's real vs. a
  documented judgment call.
- Building the page that hosts it (Background image + CenterDIV backdrop +
  Header/Footer/Volume widget refs, learned from the project's own existing
  pages + the new popup ref).
- The footer icon-group reflow MATH for both landscape and portrait (exact,
  proven against the real template's own measured positions).
- Writing that reflow into a real `Footer - Main.cuiw` -- add/remove/
  reposition the actual `Menu_*`/`DividerGroup*` HTML+CSS+TOML, verified
  round-trip-identical against real copied-template files (see "Editing the
  Footer Menu" below).

What's still NOT done: wiring the new popup's `Visibility=Contract` toggle to
the new footer button's press signal (the actual show/hide link between
them) -- do that step manually in Construct's own Contract Editor for now,
and say so plainly when reporting a subsystem as added. The "-More" secondary
popup shape (a second, linked popup for overflow controls) is also not built
yet -- flag it if the user specifically asks for one.

Ask, per subsystem, IN ORDER:
1. "What controls does [name] need? Group them if there's more than one
   logical set." → ordered `(group_title, [button_labels])` list -- or one of
   the D-pad/button-list/keypad group markers above for a non-button-list
   group.
2. **"Should [name]'s footer icon go in an existing group, or a new one?"**
   -- ALWAYS ask this explicitly, never silently append to whatever group
   seems closest; read the footer's real current groups first
   (`design_ideas_read_footer_groups`, see below) so the options you offer
   are real, not guessed. A 5th group needs the user to combine two existing
   ones instead (see the "5th group is refused" note below).
3. "What icon should represent [name]?" (suggest a Font Awesome class,
   confirm rather than silently picking one) -- this SAME `icon_class`/
   `icon_library` also goes on the footer button (see "Icon/library
   consistency" below).

To determine the popup's own SIZE and general layout for a NEW subsystem
(panel_width/panel_height, header proportions, group frame geometry), read
the real `Popup - SubsystemTemplate.cuiw` in the Design Ideas project
first (same folder as the other real `Popup - *.cuiw` files) rather than
guessing -- it's Construct's own generic starting scaffold for exactly this
shape, and `design_ideas_subsystem.py`'s own constants (TITLE_WIDTH,
GROUP_TITLE_TOP, GROUP_WIDTH, GROUP_TOP, ...) are already grounded against
it. If a project-specific value looks like it might differ (an unusual
`panel_width`, a custom close-button size), re-check against that real file
rather than assuming the existing constants still apply.

**Build the popup WIDGET first, then the PAGE that references it** --
`design_ideas_build_subsystem_page` needs the popup's own `widget_id`, so
this order isn't optional; see the code below.

```python
from design_ideas_subsystem import (
    design_ideas_learn_project_shared, design_ideas_build_subsystem_popup,
    design_ideas_build_subsystem_page, design_ideas_read_footer_groups,
    design_ideas_write_footer_groups,
    # only the group shapes this subsystem actually needs:
    design_ideas_dpad_group, design_ideas_button_list_group, design_ideas_keypad_group,
)
from page import write_cuig
import compare

shared = design_ideas_learn_project_shared(PROJECT_DIR)

# Read the footer's REAL current groups BEFORE asking the user "existing group
# or new one?" -- the options offered must be real, not guessed.
footer_path = PROJECT_DIR / "Footer - Main.cuiw"
current_footer_groups = design_ideas_read_footer_groups(footer_path)

widget_id, w_attrs, w_html, w_css, w_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name=f"Popup - {NAME}", title=NAME, icon_class=ICON_CLASS,
    groups=GROUPS, panel_width=1048, panel_height=590,
)
popup_path = PROJECT_DIR / f"Popup - {NAME}.cuiw"
write_cuig(popup_path, w_attrs, html=w_html, css=w_css, elements=w_elements)
assert compare.round_trip_check(popup_path)

p_attrs, p_html, p_css, p_elements = design_ideas_build_subsystem_page(
    ui_sdk, page_name=NAME, project_shared=shared,
    popup_widget_id=widget_id, popup_widget_name=f"Popup - {NAME}",
)
page_path = PROJECT_DIR / f"{NAME}.cuig"
write_cuig(page_path, p_attrs, html=p_html, css=p_css, elements=p_elements)
assert compare.round_trip_check(page_path)

# Wire the footer: NAME goes into whichever group the user picked in step 2
# above (existing group name, or a brand-new one) -- reuse current_footer_
# groups read earlier, never re-read-and-assume it's still unchanged if any
# time has passed, and never assume FOOTER_DEFAULT_GROUPS.
new_groups = [...]  # current_footer_groups with NAME inserted into the user's chosen group
report = design_ideas_write_footer_groups(
    footer_path, ui_sdk, new_groups, icon_classes={NAME: ICON_CLASS}, icon_library=ICON_LIBRARY)
assert compare.round_trip_check(footer_path)
# report == {"added": [...], "removed": [...], "removed_pages": [...],
#            "repositioned": [...], "overflow": [...]}
# -- surface `overflow` to the user verbatim if non-empty (Privacy_Mute never
# reflows, so a very full footer can genuinely collide with it). Adding NAME
# never removes anything, so removed/removed_pages should be empty here.
```

**A 5th reflow-managed group is refused** (`ValueError`, not silent
corruption): `design_ideas_footer_layout` would need to name an internal
divider "DividerGroup4", which is already the real template's OWN name for
Privacy_Mute's separate, permanently-fixed divider. 4 groups is this
mechanism's real ceiling right now -- if the user needs a 5th, say so and ask
them to combine two existing groups instead of guessing around it.

---

---

## Editing the Footer Menu directly (Design Ideas projects only)

For a request that's ONLY about the footer's menu icons -- removing a
subsystem the user doesn't want, or reordering/regrouping existing ones --
without building a new subsystem popup+page. Gate on
`IS_DESIGN_IDEAS_TEMPLATE` same as above.

```python
from design_ideas_subsystem import design_ideas_read_footer_groups, design_ideas_write_footer_groups
import compare

footer_path = PROJECT_DIR / "Footer - Main.cuiw"
current_groups = design_ideas_read_footer_groups(footer_path)  # e.g. [["Power"], ["Lights","Shades"], ...]
new_groups = [...]  # current_groups edited per the user's request
report = design_ideas_write_footer_groups(footer_path, ui_sdk, new_groups)
assert compare.round_trip_check(footer_path)
```

`design_ideas_read_footer_groups` self-verifies against the file's own real
measured positions and raises if they don't match its assumed rhythm --
treat that as a real "this footer doesn't fit the expected model" finding to
report, not something to retry or work around.

**Removing a subsystem deletes its own page (`X.cuig`) but leaves its popup
widget (`Popup - X.cuiw`, and any "- More" secondary popup) on disk** -- the
user's own explicit instruction (2026-09-17): keeping the widget means the
subsystem can be re-added later without rebuilding its popup content from
scratch. This happens automatically as part of `design_ideas_write_footer_
groups` for every removed button (`delete_pages=True`, the default) -- pass
`delete_pages=False` for a purely cosmetic footer edit that should leave
every page file alone. Not every subsystem has its own page in the real
template (VideoCall does not) -- a missing page is a silent no-op, not an
error; check `report["removed_pages"]` (a subset of `report["removed"]`) to
see which ones actually had a page to delete. Report deletions to the user
plainly, and remind them the widget is still there if they want it back.

**Privacy_Mute is never touched or reflowed**, in either orientation, by
design -- a request to reposition or restyle it needs a different, dedicated
mechanism this document doesn't cover yet.

---

## Editing Presentation Sources (Design Ideas projects only)

Gate on `IS_DESIGN_IDEAS_TEMPLATE`. Adds/removes source-selection buttons on
the real `Sources - Center.cuiw`. Each source is 3 real elements (`Source_
<name>` button + `Source_<name>_Sync` green bar + `Source_<name>_NoSync`
red bar) -- adding or removing a source always means all 3 together, and
every OTHER source's position is recomputed too (the grid re-centers).

```python
from design_ideas_subsystem import design_ideas_read_sources, design_ideas_write_sources

sources_path = PROJECT_DIR / "Sources - Center.cuiw"
current_sources = design_ideas_read_sources(sources_path)
new_sources = [...]  # current_sources with the requested name added/removed
report = design_ideas_write_sources(
    sources_path, ui_sdk, new_sources, icon_classes={NAME: ICON_CLASS})
assert compare.round_trip_check(sources_path)
# report == {"added": [...], "removed": [...], "repositioned": [...]}
```

`icon_classes` is REQUIRED for every newly added source (no default icon --
suggest a Font Awesome class, confirm rather than silently picking one, same
rule as everywhere else in this document). Landscape is a SINGLE ROW,
centered -- a set of sources that doesn't fit in the widget's own 1048px
width raises `ValueError` rather than guessing at a wrap rule (landscape
multi-row wrapping has no real reference file to ground yet -- say so
plainly if a request needs more sources than fit). Portrait wraps 2 per
row and IS grounded (real reference confirmed).

**Adding a new source: ALWAYS ask whether it needs a control panel** --
never assume either way, and never skip this question even if the user's
request sounds complete without it (e.g. "add a Roku source" -- still
ask). If yes, see "Source Controls" below; build and wire the `Controls -
<name>` widget as part of the SAME request, don't treat it as a follow-up
someone has to remember to ask for separately.

Explicitly out of scope: the `Instructions` text element's own position
(never moved).

---

## Source Controls (a source's own optional control panel)

Gate on `IS_DESIGN_IDEAS_TEMPLATE`. `Controls - <name>.cuiw` is
STRUCTURALLY IDENTICAL to a subsystem popup (confirmed directly against
the real `Controls - Template.cuiw`/`Popup - SubsystemTemplate.cuiw` --
same geometry) -- reuse `design_ideas_build_subsystem_popup(...,
device_controls=True)` for the widget itself, no separate builder. What's
new here is wiring that widget's reference onto the real Presentation
page.

```python
from design_ideas_subsystem import (
    design_ideas_build_subsystem_popup, design_ideas_add_source_control_ref,
)
from page import write_cuig
import compare

widget_id, w_attrs, w_html, w_css, w_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name=f"Controls - {SOURCE_NAME}", title=SOURCE_NAME, icon_class=ICON_CLASS,
    groups=GROUPS, panel_width=1048, panel_height=590, device_controls=True,
)
widget_path = PROJECT_DIR / f"Controls - {SOURCE_NAME}.cuiw"
write_cuig(widget_path, w_attrs, html=w_html, css=w_css, elements=w_elements)
assert compare.round_trip_check(widget_path)

presentation_path = PROJECT_DIR / "Presentation.cuig"  # confirm the real page name first
design_ideas_add_source_control_ref(presentation_path, ui_sdk, widget_id, f"Controls - {SOURCE_NAME}")
assert compare.round_trip_check(presentation_path)
```

`design_ideas_add_source_control_ref` positions the new ref EXACTLY where
`Sources - Center`'s own ref sits (both overlay; the project's own
runtime contract shows only the currently-selected source's Controls
widget) and lists it BEFORE `Sources - Center` (frontmost, same real
z-order rule as everywhere else in this document). Idempotent -- a no-op
if a ref with that widget name is already present. Raises `ValueError` if
the page has no real `Sources - Center` ref to anchor against (not a
Header-Center-Source style page).

**Reuse-before-build**: if the project already has a matching
`Controls - <name>.cuiw` (e.g. re-adding a source that was removed
earlier -- removing a subsystem/source never deletes its own widget
file), reuse it and just re-add the page ref -- don't rebuild it from
scratch.

---

## Icon/library consistency (carried over from v1, still applies)

A subsystem's footer-button icon and its popup-header icon must match
exactly -- there's no mechanism linking them, so pass the same
`icon_class`/`icon_library` to both when the footer-wiring piece exists.
`icon_library` is almost always `"FA Classic Solid"`; use `"FA Brands"` only
for an actual brand logo icon.

---

## Verifying work

Every write in this repo gets `compare.round_trip_check`'d before being
reported as done -- this document inherits that rule, not optional polish.
If a round-trip check fails, that's a real bug to investigate, not
something to retry or silently ignore.
