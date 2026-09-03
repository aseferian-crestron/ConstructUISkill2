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
| CH5 component schema (`schema.json`/`schemaaddendum.json`/`component-context.json`) | Mapped (deserialization classes + DAO known), literal file contents of an installed SDK not yet read | 4 | `PageDesigner.Server\Dao\UiSdkDao.cs`, `PageDesigner.Common\Models\Ch5ElementDef.cs`, `GetSdkHandler.cs` |
| Resolutions — `UiEditorResolutionDao.cs` vs. inline `.cuip` `{DeviceResolutionSource}` | Flagged as possibly overlapping/legacy, not resolved | 5 | `UiEditorResolutionDao.cs`, `UiEditorProjectDao.cs` |
| Multi-resolution reflow / orientation-primary rule (spec §9) | Not started | 5 | — |
| Contract generation (`.cuic`) — trigger flow | Mapped | 6 | `Behaviors\ContractGenerationBehavior.cs`, `Services\Contract\ContractGenerationService.cs`, `Dao\UiEditorContractDao.cs` |
| Contract generation — per-component-type signal/join rules | Not deep-dived | 6 | `Services\Contract\ComponentStrategies\*` |
| Themes — project attributes + registration | Mapped | 7 | `ServerThemeAndFontHelper.cs`, `PageDesigner.Server\Commands\Handler\StylingAssets\ThemeAndFontUpdateHandler.cs` |
| Themes — `customvstheme` per-component-type rules | Mapped at a summary level | 7 | `SUpgV1CustomVsThemeUpgradeHandler.cs:528-666` |
| Fonts — project/element attributes + webfont import | Mapped | 8 | `ServerThemeAndFontHelper.cs`, `FontUpgradeHelper.cs`, `ThemeAndFontUpdateHandler.cs:124-166` |
| Assets (`.cuia`) — import + `assetid` linking | Mapped | 9 | `UiEditorAssetDao.cs`, `Helpers\AssetHelper.cs`, `Commands\AssetManagement\Utilities\AssetUtilities.cs` |
| Language files — filename discovery | Mapped | 10 | `LanguageFileDao.cs` |
| Language files — per-file content schema | **Not found** — only filename discovery was traced; the actual JSON shape of a language file's contents is unknown | 10 | `LabelEditor\LabelEditor.Common\Models\LanguageKeyJoin.cs` (candidate, unconfirmed) |
| Hard buttons (`.cuib`) — format + Project→Device→Page cascade | Mapped | 11 | `UiEditorHardButtonDao.cs`, `Helpers\HardButtonHelper.cs`, `Models\HardButtonMapping.cs` |
| "Active project" persisted state (spec §7) | **Resolved** — Construct persists a `.cse` sidecar (`Solution.Common\Constants.cs`: `ExplorerStateFilename`) via `SolutionExplorerState`/`SolutionExplorerStateDto`, but it's Explorer-tree UI bookkeeping (`Id`=project name, `IsOpen`, `Time`) — which project(s) are expanded/last-touched in the IDE's own UI, not a single "the active project" flag. Our skill's own active-project selection (`generator/solution.py::select_active_project`) is a session-scoped concept we own, with no need to read/write `.cse`. | 1 | `Solution.Server\Models\SolutionExplorerState.cs`, `Solution.Common\Models\SolutionExplorerStateDto.cs` |
| Client-side CH5 component instantiation (GrapesJS `ComponentDefinition`) | Mapped at a summary level, not needed unless a UI-editor-level (not file-level) integration is ever in scope | — (not currently planned) | `pd-types\Omni\ComponentDefinition.ts`, `pd-ch5-components\loaders\component.ts`, `pd-metadata-resolver\MetaDataResolver.ts` |

## How to use this index

When a phase starts, update its row's Status to "In progress", do the actual source
read, write `NN-topic.md` (numbered after `01-index.md`, one per topic, named after the
Topic column e.g. `02-ch5-schema.md`), then flip Status to "Done" with a link. Update
this table and `README.md`'s Log in the same turn.
