# Solution & Project Creation

Covers Phase 2: creating a `.csln` (solution) and a new, empty `.cuip` (project) —
including a project associating with **multiple themes** and **multiple device
resolutions** at creation time (spec §2's required-info list: devices supported, theme
choice — both are naturally multi-valued, confirmed by the file format itself).

## Source grounding

- `UiEditor.Server\Commands\Solution\CreateProjectHandler.cs` — defaults applied when a
  project is created (SDK auto-detect = latest installed if not specified, `ThemePageColor`
  via `ServerThemeAndFontHelper.GetDefaultThemeColor`, `DefaultComponentMode = "custom"`,
  `RuntimeThemeJoin`/`RuntimeLanguageJoin` default `"0"`, `ProjectSchemaVersion` = current).
- `UiEditor.Server\Helpers\PersistenceHelper.cs`, `WriteProject()` (~line 38) — the
  **exact ordered list** of `{ProjectAttributes}` keys written to a `.cuip`, including
  which keys are conditionally omitted when empty. This is the ground truth
  `generator/project.py::build_project_attributes()` transcribes directly.
- `UiEditor.Common\Constants.cs` — `ComponentKey` values (`"UiEditor"` vs
  `"ZoomRoomControl"`, spec's "Zoom or UI project?"), `ProjectDefaultTheme`,
  `ProjectDefaultFontFamily`, `DefaultIpId = "03"`, `DefaultThemeLanguageJoin = "0"`,
  `CurrentProjectSchemaVersion = 13`.
- `Solution.Server\Dao\SolutionDao.cs` / `Models\Solution.cs` / `ProjectHandleDto.cs` —
  `.csln` JSON shape (`generator/solution.py`).
- `Solution.Server\Commands\Handlers\AddProjectHandler.cs` — relative-path computation
  when a project is added to a solution (`Path.GetRelativePath` from the solution's own
  folder, forward-slash normalized) — mirrored in `add_project_to_solution()`.

## Multi-theme / multi-resolution (confirmed 2026-09-03, prompted by user correction)

- **Themes**: `ThemeId` (the active/default theme) is one value; `ProjectThemeIds` is a
  **comma-separated list of every theme associated with the project** — so per-page/
  per-instance theme overrides can pick from any of them (see `00-overview.md`'s Themes
  entry). `build_project_attributes(themes=[...], default_theme=...)` takes the full
  list and the active one separately; `default_theme` must be a member of `themes`
  (not currently enforced in code — flag for a future validation pass).
- **Resolutions**: `{DeviceResolutionSource}` (JSON, inside `.cuip`) is an **array** —
  a project can support any number of device resolutions simultaneously.
  `DeviceResolutionIds` (a `{ProjectAttributes}` string) is a comma-join of the array's
  `id` values. `build_project_attributes(resolutions=[...])` accepts a list of
  already-shaped resolution dicts and fills in `ProjectId` on each automatically.
  **Not yet resolved** (deferred to Phase 5): the device catalog itself (valid
  `deviceSpecId`/`resolutionId` values, and the `orientation` field's actual enum
  semantics — the demo data in `project.py`'s `__main__` block guesses `1`=landscape/
  `0`=portrait from a single real sample and is explicitly flagged as unconfirmed).

## What's built (`generator/project.py`, `generator/solution.py`)

- `project.build_project_attributes(...)` → `(attrs, device_resolution_source)`,
  attrs as an **ordered** list (key order is load-bearing — it's diffed against real
  files) matching `WriteProject`'s exact order and omission rules.
- `project.write_cuip(path, attrs, device_resolution_source, metadata=None)` — writes a
  complete `.cuip` (`{FileMetadata}` + `{DeviceResolutionSource}` + `{ProjectAttributes}`).
- `solution.create_solution(dir, name)` / `solution.write_solution(...)` /
  `solution.add_project_to_solution(solution, name, cuip_path)` — full `.csln` write path.

## Verification performed

1. **Structural match against the real reference file**: generated `.cuip`'s
   `{ProjectAttributes}` key **order** matches
   `C:\Solutions\ClaudeSamples\Components\Components.cuip` exactly (17/17 keys, same
   order) — parsed with Python's `tomllib`, compared programmatically, not eyeballed.
   Generated `{DeviceResolutionSource}` entry's key **set** matches the real entry's key
   set exactly.
2. **Structural match against the real `.csln`**: generated solution's top-level keys,
   `_fileMetadata` keys, `_solution` keys, and `_projects[0]` keys all match
   `C:\Solutions\ClaudeSamples\ClaudeSamples.csln` exactly.
3. **Round-trip**: `harness/compare.py` confirms the generated `.cuip` splits into the
   correct sections in the correct order and round-trips byte-identically.
4. **End-to-end smoke test** (`generator/_test_output/phase2_smoke_test.py`): create
   solution → create project (2 themes, 1 resolution) → add project to solution →
   re-read the solution and confirm the project resolves to the right folder on disk.
   All assertions passed.

Not yet tested: opening any of this in Construct itself (per the project's own rule —
automated verification first, manual Construct testing only after that's clean). This is
the natural next checkpoint once the user wants to hand-verify in the real app.
