# Architecture Deep-Dive Index

Per-topic status. `00-overview.md` covers the core `.csln`/`.cuip`/`.cuig`/`.cuiw`
serialization mechanics (done). Everything below gets its own `NN-topic.md` doc,
written just-in-time when the phase that needs it starts — not speculatively ahead of
that. "Known" here means confirmed by the two 2026-09-03 Explore passes at a mapping
level (file paths + rough shape); "Deep-dive" means the level of detail actually needed
to write generator code, not yet done for anything except the overview topics.

| Topic | Status | Phase | Key entry points already known |
|---|---|---|---|
| Core file serialization (`.csln`/`.cuip`/`.cuig`/`.cuiw`) | **Done** — see `00-overview.md` | 1 | `SolutionDao.cs`, `UiEditorProjectDao.cs`, `UiEditorPageDao.cs` |
| Solution/project creation (`.csln` write + `.cuip` write, multi-theme/multi-resolution) | **Done** — see `02-project-creation.md` | 2 | `CreateProjectHandler.cs`, `PersistenceHelper.WriteProject`, `AddProjectHandler.cs` |
| `UiEditorProject.cs` (runtime model) ↔ `UiEditorSource.Attributes` mapping | Mapped, not deep-dived | 2 | `Models\UiEditorProject.cs`, `UiEditorProjectDao.cs` |
| `[[Elements]]` nesting rules for widget containers vs. page components | **Done** — see `03-page-widget-creation.md` | 3 | `Models\ElementSource.cs` |
| Create page / create widget / add widget to page | **Done** — see `03-page-widget-creation.md` | 3 | `CreateNewPageHandler.cs`, `CreateNewWidgetHandler.cs`, `AddHtmlViewDependencyHandler.cs`, `PersistenceHelper.CreatePageSource` |
| Page/widget background (color via existing mechanism; image via a pinned ch5-image/ch5-background, reflow-kept at (0,0)+full size) + project-level OverrideThemeColor/ThemePageColor default | **Done**, live-verified 2026-09-11 | 3 | `generator/background.py`, `generator/reflow.py::BACKGROUND_MARKER_ATTR`, `generator/project.py::build_project_attributes`, `ProjectItemThemePageColor.razor.cs` |
| CH5 component schema (`schema.json`/`component-context.json`/`sass-schema.json`) | **Done for Ch5 Button (default config)** — see `04-ch5-schema.md` | 4 | `PageDesigner.Server\Dao\UiSdkDao.cs`, `PageDesigner.Common\Models\Ch5ElementDef.cs`, `GetSdkHandler.cs`, `pd-ch5-components/mixins/common/commonButtonTraitsMixins.ts` |
| Resolutions — `UiEditorResolutionDao.cs` vs. inline `.cuip` `{DeviceResolutionSource}` | **Resolved** — see `05-resolutions.md`: not overlapping, two different concerns (global catalog vs. per-project selection) | 5 | `UiEditorResolutionDao.cs`, `DeviceResolutionDto.cs`, `DisplayOrientation.cs` |
| Device/resolution catalog (74 real entries) + orientation enum semantics | **Confirmed** — see `05-resolutions.md` | 5 | `%APPDATA%\crestron-construct\AppStorage\data\ui\resolution\resolutionData.json`, `InitializeLibraryDeviceResolutionsHandler.cs` |
| Add resolutions to a project | **Done** — catalog AND genuinely custom resolutions, reflow-verified live 2026-09-11 — see `05-resolutions.md` | 5 | `generator/devices.py::to_custom_resolution`, `generator/project.py::add_resolutions_to_project` |
| Multi-resolution reflow / orientation-primary rule (spec §9) | Deliberately deferred (user-scoped) — catalog/orientation confirmed, reflow math for non-primary resolutions not deep-dived | 5 | `05-resolutions.md` |
| Contract generation (`.cuic`) — trigger flow | **Done** — see `06-contracts.md`: we never author a `.cuic`; `ContractIsStale="true"` makes Construct generate it on open | 6 | `Behaviors\ContractGenerationBehavior.cs`, `Services\Contract\ContractGenerationService.cs`, `Dao\UiEditorContractDao.cs` |
| Contract generation — per-component-type signal/join rules | **Done for simple components** — see `06-contracts.md`: signals are SDK data (`component-context.json` `extenderPosition` entries), enabled with the `"Contract Enabled"` sentinel. The per-strategy rules for COMPLEX components (dpad/keypad/button list/widget list/tab button/video switcher/media player) are still not deep-dived | 6 | `Services\Contract\ComponentStrategies\*` |
| Themes — project attributes + registration | Mapped | 7 | `ServerThemeAndFontHelper.cs`, `PageDesigner.Server\Commands\Handler\StylingAssets\ThemeAndFontUpdateHandler.cs` |
| Themes — `customvstheme` per-component-type custom-mode style properties | **Stage 1 (raw properties) + Stage 2 (palette layer, 18/29 real component types — the other 11 confirmed genuinely unstylable) + Stage 3 source #1 (chat-described, single-tag and all-types-at-once) done**, live-verified — Stage 3 sources #2 (reference-project extraction)/#3 (design-doc, deferred) not started | 7 | `generator/style.py`, `generator/palette.py`, `generator/theme_chat.py`, `generator/color_words.py`, `component-context.json`'s `classToVariableMapping`, `customThemeStyleMixins.ts` (client-side runtime, not file-format-relevant) |
| Fonts — project/element attributes + webfont import | Mapped | 8 | `ServerThemeAndFontHelper.cs`, `FontUpgradeHelper.cs`, `ThemeAndFontUpdateHandler.cs:124-166` |
| Assets (`.cuia`) — import + `assetid` linking | **Done for local image import** — see `09-assets.md` (pulled forward out of order to verify Phase 4's image-button variant) | 9 | `UiEditorAssetDao.cs`, `Helpers\AssetHelper.cs`, `Commands\AssetManagement\Utilities\AssetUtilities.cs`, `Handlers\SaveAssetMetadataHandler.cs` |
| Language files — filename discovery + per-file content schema | **Out of scope for now** (user, 2026-09-11: "we can remove the custom language support from this skill for now as well .. i will add that later") — was Mapped (filename discovery)/Not found (content schema), not built | — (deferred) | `LanguageFileDao.cs`, `LabelEditor\LabelEditor.Common\Models\LanguageKeyJoin.cs` (candidate, unconfirmed) |
| Hard buttons (`.cuib`) — format + Project→Device→Page cascade | **Out of scope** (user, 2026-09-11: "not needed in the skill") — was Mapped, not built | — (removed) | `UiEditorHardButtonDao.cs`, `Helpers\HardButtonHelper.cs`, `Models\HardButtonMapping.cs` |
| "Active project" persisted state (spec §7) | **Resolved** — Construct persists a `.cse` sidecar (`Solution.Common\Constants.cs`: `ExplorerStateFilename`) via `SolutionExplorerState`/`SolutionExplorerStateDto`, but it's Explorer-tree UI bookkeeping (`Id`=project name, `IsOpen`, `Time`) — which project(s) are expanded/last-touched in the IDE's own UI, not a single "the active project" flag. Our skill's own active-project selection (`generator/solution.py::select_active_project`) is a session-scoped concept we own, with no need to read/write `.cse`. | 1 | `Solution.Server\Models\SolutionExplorerState.cs`, `Solution.Common\Models\SolutionExplorerStateDto.cs` |
| Client-side CH5 component instantiation (GrapesJS `ComponentDefinition`) | Mapped at a summary level, not needed unless a UI-editor-level (not file-level) integration is ever in scope | — (not currently planned) | `pd-types\Omni\ComponentDefinition.ts`, `pd-ch5-components\loaders\component.ts`, `pd-metadata-resolver\MetaDataResolver.ts` |

## How to use this index

When a phase starts, update its row's Status to "In progress", do the actual source
read, write `NN-topic.md` (numbered after `01-index.md`, one per topic, named after the
Topic column e.g. `02-ch5-schema.md`), then flip Status to "Done" with a link. Update
this table and `README.md`'s Log in the same turn.
