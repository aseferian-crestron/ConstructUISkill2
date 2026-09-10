# Resolutions / multi-resolution reflow (Phase 5)

Status: **Device catalog + add-resolutions-to-a-project DONE.** Full multi-resolution
*reflow* (scaling existing page content to fit a newly-added resolution) is a deliberately
separate, not-yet-started slice — see "Next" at the bottom; the user chose to scope it out
of this first slice given its size.

## CORRECTION (2026-09-10): `{DeviceResolutionSource}` only ever holds CUSTOM resolutions

An earlier version of this slice got the `{DeviceResolutionSource}`/`DeviceResolutionIds`
relationship backwards, and it caused a real corruption the user found and fixed by hand
in Construct: a catalog-sourced resolution (e.g. TSW-1070) was being written into
`{DeviceResolutionSource}` as if it were a project-embedded entry. Confirmed directly from
source (`UiEditor.Server\Helpers\PersistenceHelper.cs`'s `WriteProject`/`SaveProject`,
both identical):

```csharp
// Write Project custom resolutions
if (uiProject.CustomDeviceResolutions is not null)
    projectSource.DeviceResolutionSource = uiProject.CustomDeviceResolutions;
```

`{DeviceResolutionSource}` **only ever persists genuinely custom (non-catalog)
resolutions**. A standard catalog pick is represented *purely* by its id in
`DeviceResolutionIds`; there is no redundant copy of its width/height/etc. in the project
file at all — it's resolved against the global catalog file at runtime every time
(`ResolutionHelper.cs::GenerateDeviceResolutionDto` rebuilds the full in-memory resolution
list from `LibraryDeviceResolutions` + `CustomResolutions` on every Resolution Manager
open, never from the project's own persisted `DeviceResolutionSource`). On load,
`OpenProjectHandlerHelper.cs` copies `project.CustomDeviceResolutions =
projectSource.DeviceResolutionSource` verbatim, and the Resolution Manager renders that as
a **second, separately-removable list** — so a catalog resolution mistakenly written into
`{DeviceResolutionSource}` shows up as a duplicate, deletable "custom" row sitting right
next to its real catalog row. That's exactly the visual the user saw and correctly flagged
as corruption, in both the reference sample project (`C:\Solutions\ClaudeSamples\
Components`) and this project's own generated `GenTestProject`/`GenTestProject2` — this
machine's `resolutionData.user.json` additionally had an actual invalid duplicate custom
entry literally named "TSW-1070" (colliding with the real device name, which Construct is
supposed to — but apparently didn't always — prevent), compounding the confusion.

Fixed in `generator/devices.py::to_project_resolution` (no longer forces `IsCustom`/
`resolutionType`/`resolutionName` at all — the returned dict is used only for
`DeviceResolutionIds` + reflow math, never written into `{DeviceResolutionSource}`) and
`generator/project.py::build_project_attributes`/`add_resolutions_to_project` (catalog
resolutions only ever extend `DeviceResolutionIds`; `{DeviceResolutionSource}` is written
back untouched). This module still has no "add a genuinely custom resolution" builder —
when one is added, it alone should produce `{DeviceResolutionSource}` entries, and should
validate (mirroring a rule Construct itself is supposed to enforce, per the user) that a
custom resolution's name doesn't collide with a standard catalog device's name.

## The two previously-flagged open questions, both resolved

**`UiEditorResolutionDao.cs` vs. the inline `.cuip` `{DeviceResolutionSource}` section**
(flagged in Phase 2): these are simply two different concerns, not overlapping/legacy:
- `UiEditorResolutionDao` reads/writes a **global, not-per-project** JSON file — the
  catalog of every resolution Construct knows about (see below). It's just a plain
  `List<DeviceResolutionSpec>` reader/writer (`UiEditor.Server\Dao\UiEditorResolutionDao.cs`).
- A project's own `.cuip` `{DeviceResolutionSource}` stores which of those catalog entries
  are genuinely CUSTOM (see the correction above — NOT every included entry;
  `DeviceResolutionDto` = `DeviceResolutionSpec` + `ProjectId`/`IsCustom`/`IsSelected`,
  confirmed in `UiEditor.Common\Models\DeviceResolutionDto.cs`).

**`orientation` enum semantics** (flagged in Phase 2): `DisplayOrientation` enum
(`UiEditor.Common\Models\DisplayOrientation.cs`): `None=0, Landscape=1, Portrait=2, Both=3`.
Confirmed against the real `Components.cuip`'s `"orientation": 1` (its one TSW-1070 entry,
landscape). Serialized as the raw int inside a `.cuip`'s `{DeviceResolutionSource}` JSON
(no string-enum converter registered there), but as the string `"landscape"`/`"portrait"`
in the global catalog file (`UiEditorResolutionDao.Read` registers
`JsonStringEnumConverter`) — two different serialization contexts for the same enum,
confirmed by reading both real files.

## The real device/resolution catalog

Global catalog file, confirmed on disk at
`%APPDATA%\crestron-construct\AppStorage\data\ui\resolution\resolutionData.json`
(`UiEditorConstants.ResolutionPath`/`ResolutionFile`, copied from the app's bundled
resources on first run by `InitializeLibraryDeviceResolutionsHandler.cs`) — **74 real
entries**, each a `DeviceResolutionSpec`: `id`, `idName`, `idDesc`, `deviceSpecId`,
`resolutionId`, `resolutionName` (a comma-list of every device sharing that exact
resolution, e.g. TSW-1070's is `"TST-1080 (Landscape), TSW-1070, TSV-1070GV, TSW-1060,
TSW-770, Cisco Navigator - Fullscreen, TSW-880, TSW-1080"` — **not just the one device
name**, correcting an earlier, unconfirmed guess used in `project.py`'s own `__main__`
smoke example), `resolutionType` (`"device"` = a real Crestron/generic touchpanel,
`"generic"` = a phone/tablet/monitor preset), `orientation`, `width`/`height` (the CH5
project's logical CSS px), `widthMedia`/`heightMedia` (usually identical to width/height —
the values `layout.py`'s media-query formula should use), `supportedDevices`,
`componentKeys` (which project type this entry applies to — `["UiEditor"]` for UI
projects, `["ZoomRoomControl"]` for Zoom projects), and optionally `displayNameSuffix` +
`modes` (Zoom-only: alternate in-meeting/idle sub-resolutions, out of scope here).
A second file, `resolutionData.user.json`, holds user-added custom resolutions (empty on
this machine) — read the same way, appended to the same list
(`InitializeLibraryDeviceResolutionsHandler.cs`'s `CustomResolutions`).

**Important correction**: `project.py`'s own `__main__` example previously invented a
"TSW-1070 Portrait" entry (`D-P-TSW1070-0800-1280`) to demonstrate multi-resolution
support — **no such entry exists in the real catalog**. TSW-1070 is landscape-only
hardware (a 10.1" wide-format panel); Construct's own catalog agrees (only one TSW-1070
entry, landscape). Devices that genuinely support both orientations exist in the real
catalog (e.g. `TST-1080` — both `D-L-TST1080-1280-0800` and `D-P-TST1080-0800-1280` are
real entries — plus every generic phone/tablet preset, each listed twice, once per
orientation) — a landscape+portrait *pair* should be built from one of those, not invented.

## "Orientation-primary" (spec §9)

> The reflow operations are always based on the orientation-primary: highest landscape
> resolution and highest portrait resolution.

Not yet deep-dived in source (client-side reflow logic, not yet located) — "highest" is
presumed to mean widest (by `width`/`widthMedia`), matching the already-confirmed pattern
(from earlier `ConstructUISkill` v1 session memory, re-confirmed structurally by
`Component - Button.cuig`'s CSS: the *one* selected landscape resolution's breakpoint gets
identical left/top/width/height values in BOTH the `99999px` catch-all block AND its own
device-specific block — i.e., the primary resolution IS the "default"/catch-all target).
For a project with only one resolution per orientation (today's generator scope), the
primary is simply that resolution — no ambiguity yet. Confirming the actual reflow
math for a *second, non-primary* resolution (what values a non-primary device's own
`@media` block should reflow to) is the open item for whichever slice tackles true
multi-resolution reflow — see "Next" below.

## Built this slice

- **`generator/devices.py`** — reads the real 74-entry catalog (mirroring
  `generator/sdk.py`'s AppStorage-reading pattern). `read_catalog()` defaults to
  `include_custom=False`: the bundled `resolutionData.json` only, NOT
  `resolutionData.user.json` (this machine's own personal saved custom resolutions) —
  confirmed necessary, not just cautious: this machine's custom file contains a
  user-created resolution literally named `"TSW-1070"` that collides with the real device
  entry, which would silently produce wrong/ambiguous lookups if merged in by default.
  Also confirmed and fixed: `resolutionData.user.json`'s entries encode `orientation` as
  a raw int (written by `UiEditorResolutionDao.Write`, which doesn't register
  `JsonStringEnumConverter`) while `resolutionData.json` encodes it as the enum string
  (written by Construct's build process, read via `.Read`, which does) — normalized to one
  form on load. `by_id_name()` also filters to `componentKeys` containing `"UiEditor"` by
  default — confirmed necessary: a bare `"TST-1080"` lookup without this filter matches
  both the real UI device entry (`"TST-1080 (Landscape)"`) and an unrelated Zoom-mode
  entry that happens to share the same bare idName.
- **`generator/project.py::read_cuip` / `add_resolutions_to_project`** — read an existing
  `.cuip` back into the same shapes `build_project_attributes`/`write_cuip` use, then add
  one or more resolutions to it: extends `{DeviceResolutionSource}`, recomputes
  `DeviceResolutionIds` from the merged list (rather than string-concatenating, to keep
  the two always in sync), marks `ContractIsStale=true`, and — for a project that started
  with **zero** resolutions — inserts the `DeviceResolutionIds` key at the correct position
  (right after `DefaultFontFamily`, matching `build_project_attributes`' own confirmed key
  order) rather than just appending it at the end.
- **`toml_util.py::override_attr`** — a tiny "replace one key's value in an ordered
  attribute list, in place" helper, factored out of `ch5_button.py` (which already needed
  it for the `size="custom"` fix) since `project.py` needed the identical operation for
  `DeviceResolutionIds`/`ContractIsStale`.

No real Construct-authored multi-resolution `.cuip` exists in the reference project to
diff against (`Components.cuip` only has the one TSW-1070 resolution) — verified instead
the same way solution/project creation was in Phase 2: the writer's output round-trips
byte-identical through the harness, and its shape structurally matches
`build_project_attributes`' own confirmed key order/`{DeviceResolutionSource}` wiring.

## Next (not started, deliberately scoped out of this slice)

The actual multi-resolution **reflow** math: what CSS a non-primary resolution's own
`@media` block should contain (how existing page content scales/repositions to fit a
resolution added after the fact), and locating the client-side source for the
orientation-primary rule's exact algorithm (not yet found — see the "Orientation-primary"
section above). `generator/layout.py::build_position_css` today only emits CSS for a
single resolution per call; multi-resolution reflow will need to extend it to emit one
correctly-scaled block per selected resolution, which is a bigger, separate slice.
