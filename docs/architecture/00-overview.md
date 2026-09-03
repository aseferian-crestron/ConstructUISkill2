# Architecture Overview — Construct Data File Serialization

Source of truth: `C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor` (UI project files) and
`C:\Git\CCIDE\Crestron.IDE\Components\Solution\Solution.Server` (`.csln`). This document
records only what has been confirmed by reading that source — not inferred from sample
files. Confirmed 2026-09-03 by two Explore passes; a couple of file:line citations below
are as reported by that pass and worth a direct re-read the first time each area is
touched in code, rather than assumed correct from memory.

## Serialization summary

| File | DAO | Sections / format | Library |
|---|---|---|---|
| `.csln` (solution) | `Solution.Server\Dao\SolutionDao.cs` | whole-file JSON, custom `JsonConverter<T>` per model, partial-metadata-first read (reads only `_fileMetadata` first to detect schema version, then the rest) | `System.Text.Json` only — no TOML |
| `.cuip` (project) | `UiEditor.Server\Dao\UiEditorProjectDao.cs` | `{FileMetadata}` (TOML) + `{DeviceResolutionSource}` (JSON array) + `{ProjectAttributes}` (TOML) | Nett 0.15.0 (TOML sections) + `System.Text.Json` (JSON section) |
| `.cuig` (page) / `.cuiw` (widget) | `UiEditor.Server\Dao\UiEditorPageDao.cs` — **same DAO/model class for both**, distinguished only by file extension | `{FileMetadata}` (TOML) + `{Html}` (raw string) + `{Css}` (raw string) + `{PageAttributes}` (TOML, `[[Elements]]` tables) | Nett |
| `.cuia` (image asset) | `UiEditor.Server\Dao\UiEditorAssetDao.cs` | `{FileMetadata}` + `{AssetAttributes}`, same header-split technique | Nett |
| `.cuib` (hard buttons) | `UiEditor.Server\Dao\UiEditorHardButtonDao.cs` | plain indented JSON: `FileMetadata` + `List<HardButtonDto>` (legacy pre-metadata fallback format exists) | `System.Text.Json` |
| `.cuic` (contract/signal) | `UiEditor.Server\Dao\UiEditorContractDao.cs` | indented JSON, `ReferenceHandler.Preserve` | `System.Text.Json` |

**Package reference confirmation:** `Directory.Packages.props:81` →
`<PackageVersion Include="Nett" Version="0.15.0" />`; `UiEditor.Server.csproj:195` →
`<PackageReference Include="Nett" />`. No Newtonsoft/Tomlyn anywhere in the package
manifest — Nett is the one and only TOML library in play, and it is a real TOML
deserializer (not a hand-rolled INI-like parser), confirmed directly in
`UiEditorPageDao.cs`/`UiEditorProjectDao.cs` via `Toml.ReadString<T>()` / `Toml.WriteString(...)`.

## `.cuip` — project file (`UiEditorProjectDao.cs`)

- `Read` (~line 42): regex-based section splitter — `Regex.Match(payloadString, @"(\{)\w+(\})")`
  walks the file on the three headers above.
  - `{FileMetadata}` → `Toml.ReadString<MetadataSource>()`
  - `{DeviceResolutionSource}` → `JsonSerializer.Deserialize<List<DeviceResolutionDto>>()`
    (plain, indented JSON array — NOT TOML, despite sitting between two TOML sections)
  - `{ProjectAttributes}` → `Toml.ReadString<UiEditorSource>(attributeContent)`
- `Write` (~line 139): hand-built `StringBuilder`, sections in the same fixed order.
  `TomlSettings` explicitly ignores the `FileMetadata`/`DeviceResolutionSource` C#
  properties so Nett only ever serializes the flat `Attributes` dictionary for this
  section — confirms `{ProjectAttributes}`'s TOML body maps to a **flat
  `Dictionary<string,string>`**, not a nested object graph.
- Legacy fallback: a payload with no `{FileMetadata}` header is treated as pure
  old-format TOML.

**Model** — `Models\UiEditorSource.cs`:
```
Dictionary<string, string> Attributes        // 1:1 with {ProjectAttributes} keys
UiEditorFileMetadata? FileMetadata
List<DeviceResolutionDto> DeviceResolutionSource
```
`Attributes` key names are defined in `UiEditor.Common\Constants.cs:490-514`
(`ProjectAttributes` static class): `ComponentKey`, `Name`, `ThemeId`, `ProjectThemeIds`,
`ThemePageColor`, `IncludeUnusedAsset`, `OverrideThemeColor`, `DeviceResolutionIds`,
`WebXPanelIPId` ("ipId"), `RoomId` ("roomId"), `SdkId`, `ProjectSchemaVersion`,
`PatchSdkId`, `Id`, `ContractIsStale`, `RuntimeThemeJoin`, `DefaultComponentMode`,
`DefaultFontFamily`, `RuntimeLanguageJoin`, `DefaultLanguageFile`, `ProjectLanguageFiles`.

Note: `Models\UiEditorProject.cs` is a **separate, runtime/in-memory** model
(`ConcurrentDictionary<string,PageDto> Pages`, etc.) — it is not what gets
serialized to disk directly; something maps it to/from `UiEditorSource.Attributes`.
**Not yet traced — flag for Phase 2 (project create/write) deep-dive.**

`{DeviceResolutionSource}` deserializes to `List<DeviceResolutionDto>`
(`UiEditor.Common\Models\DeviceResolutionDto.cs`, extends `DeviceResolutionSpec` with
`ProjectId`, `IsCustom`, `IsSelected`).

## `.cuig` / `.cuiw` — page and widget files (`UiEditorPageDao.cs`)

- `ReadPage` (~line 43): same regex header-splitting, over `{FileMetadata}` / `{Html}` /
  `{Css}` / `{PageAttributes}`, with a `LocateNextHeader`/`IsValidHeader` helper (~line
  320) to avoid false-matching header-looking text that appears *inside* HTML/CSS content.
  - `{FileMetadata}` → `Toml.ReadString<MetadataSource>()`
  - `{Html}` / `{Css}` → raw string, unparsed
  - `{PageAttributes}` → normally `Toml.ReadString<PageSource>()`; for content over
    **70,000 characters** (`safeTomlStringLength`), manually chunks the TOML on
    `[[Elements]]` / `[[Elements.Components]]` boundaries and deserializes each chunk
    separately — a workaround for a **real Nett stack-overflow bug on large strings**
    (bugs cited in-source: CCIDE-8893 / CCID-4274). **This is a hard fact worth designing
    the harness/generator around from day one**: any project with a sufficiently large
    page/widget must be written in a way Nett can still parse back, and our own writer
    should be tested against files that cross this threshold, not just small ones.
  - Legacy fallback (no `{FileMetadata}`): old `[HTML]...[CSS]...[TOML]...` format.
- `WritePage` (~line 284): same manual `StringBuilder` templating, `{PageAttributes}` via
  `Toml.WriteString(page, settings)` with `Css`/`Html`/`FileMetadata` ignored by Nett.

**Model** — `Models\PageSource.cs`:
```
PluginFileMetadata? FileMetadata
string Html
string Css
Dictionary<string, string> Attributes        // {PageAttributes} scalar [Attributes] keys
List<ElementSource> Elements                  // {PageAttributes} [[Elements]] tables
```
`Attributes` key names: `UiEditor.Common\Constants.cs:264-282` (`PageAttributes` class):
`Id`, `Name`, `PageMode`, `TransitionIn/Out/Duration/Delay`, `StartPage`, `PreloadPage`,
`CachePage`, `VisibilityJoin`, `DisplayBackgroundColor`, `BackgroundColor`,
`ComponentName`, `ColorProperty`.

`Models\ElementSource.cs` is the `[[Elements]]` row shape: `Name`, `Type`, `Status`,
`Content`, `Removable`, `Draggable`, `Highlightable`, `Copyable`, `Editable`,
`Selectable`, `Hoverable`, `_InnerText`, `Components: List<ElementSource>` (self-nesting
— this is how a widget container's children become `[[Elements.Components]]`, and a
mode/state child of a `ch5-button` becomes `[[Elements.Components.Components]]`, one
level per nesting depth of actual DOM containment), `Attributes: Dictionary<string,string>`,
`Style: Dictionary<string,string>`, `Classes: List<string>`. **Its own source comment
flags it as "Temporary source class to simplify the TOML transformation... will be
removed when data structures are more defined"** — worth re-checking this hasn't
changed shape before leaning on it heavily.

Confirmed directly against `C:\Solutions\ClaudeSamples\Components\Component - Button.cuig`
(read 2026-09-03): a page-level (not widget-container) component's `[[Elements]]` table
has `Type`/`Editable` only, then a `[Elements.Attributes]` table holding every HTML
attribute of the element (TOML key case matches the attribute name but capitalized
per `PageAttributes`/known aliases — e.g. `componentName` not `componentname`,
`ccid_ActiveFont` not `ccid_activefont`, `devicesVisited` not `devicesvisited` — **the
HTML attribute and the TOML key are NOT always the same casing**, confirm this per-key
before generating). A `ch5-button` with modes nests
`[[Elements.Components]]` (one per `<ch5-button-mode>`) each with its own
`[[Elements.Components.Components]]` (one per `<ch5-button-mode-state>`), matching
`ElementSource.Components`'s self-nesting exactly.

## GUIDs and identity linking

- Project `Id`: `Guid.NewGuid().ToString()` at creation
  (`Commands\Solution\CreateProjectHandler.cs:100`), re-keyed on import
  (`Commands\Solution\ImportProjectArchiveHandler.cs:101`).
- Page/widget `Id`: minted in `Commands\HtmlViews\CreateNewPageHandler.cs:48` /
  `CreateNewWidgetHandler.cs:84`; regenerated on copy/paste
  (`Commands\CopyPaste\PastePagesHandler.cs:153,163`, `PasteWidgetsHandler.cs:136,144`).
- Project↔page/widget link: the project's `Id` is passed as a constructor argument into
  the page/widget DTO — not looked up separately.
- Solution↔project link: **by name (dictionary key) + relative file path, not GUID.**
  `.csln`'s `Solution.ProjectHandleDtos` (keyed by project name) holds
  `ProjectHandleDto { Name, Filename (relative path), Datetime }` — confirmed directly
  against `C:\Solutions\ClaudeSamples\ClaudeSamples.csln`. The project's own GUID lives
  only inside its own `.cuip`; `.csln` never stores it. `AddProjectHandler.cs:59-65`
  computes the relative path via `Path.GetRelativePath(solutionBasePath, projectFilename)`.
- Asset linking: elements reference an asset via the `assetid` HTML attribute; the asset
  itself is defined in a sidecar `.cuia` file under the project's `assets/` folder.
- `.cuic`/contract linking: driven by component **names**, not GUIDs — see
  `01-index.md` for the deferred deep-dive on the exact signal-naming rules.

## `.csln` — solution manifest (separate codebase area)

Handled entirely outside `UiEditor.Server`, in `Solution.Server\Dao\SolutionDao.cs`. Pure
`System.Text.Json`, no header-splitting, no TOML. Confirmed directly against
`ClaudeSamples.csln`: top-level JSON object with `_fileMetadata` and `_solution`, the
latter holding `_name` and `_projects` (array of `{_name, _filename, _datetime}`).
`Solution.cs`'s custom converter (`SolutionSerializer`) silently skips unrecognized keys
(e.g. a deprecated `_explorerStates`), which matters for round-trip fidelity — an extra
key in a hand-authored `.csln` should not break our reader, and our writer should not
need to reproduce keys we don't understand.

**Open question, not yet resolved:** where does "active project" state live, if
anywhere persisted? Not found in `Solution.cs`/`.csln` itself in this pass — possibly
purely a runtime/session concept (`SolutionState`) with no on-disk representation, or
tracked in a separate `.cse`-style file not yet located. Relevant to spec §7's
"active project" behavior — resolve when Phase 1's `.csln` reader is built.
