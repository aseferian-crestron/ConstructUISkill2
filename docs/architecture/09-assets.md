# Assets — image import (Phase 9, pulled forward)

Status: **Done for local image file import.** Pulled forward out of order (was originally
planned for after fonts/languages/hard buttons) because the Phase 4 image-type button
variant genuinely couldn't be verified in Construct without a real asset to reference —
the user caught this directly ("i cant call that closed until you add an image asset to
the project and then use that asset in the button").

## Confirmed against a genuinely real, already-in-use reference asset

`C:\Solutions\ClaudeSamples\Components\assets\CrimsonSilk.cuia`/`.jpg` isn't just a sample
— it's the *exact* asset the reference project's image-type button (`Component -
Button.cuig`'s "Button"/ButtonWithImage instance) already references by Id
(`498f8b9e-eade-4d9d-9475-49bb03d4324b`), so this is about as strong a ground truth as this
project has had for anything.

## File format

Same header-split convention as every other Construct file:
`UiEditor.Server\Dao\UiEditorAssetDao.cs` writes `{FileMetadata}` + `{AssetAttributes}`
sections (`{FileMetadata}` via the same `MetadataSource`/`Toml.WriteString` path as pages/
projects — except **`MinimumProjectApp` is `""` for assets specifically**, confirmed
directly against the real file, not a typo — assets go through a different metadata
collection helper, `CollectPluginMetadata`, than `PersistenceHelper.WriteProject`).

`{AssetAttributes}`'s `[Attributes]` table is a `Dictionary<string,string>`
(`AssetSource.Attributes`), so unlike page/project attributes its key order isn't a fixed
model field order — it's whatever order the caller happened to insert keys in. Found the
real caller: `UiEditor.Server\Commands\AssetManagement\Handlers\SaveAssetMetadataHandler.cs`
inserts exactly `Id, Name, SourceUri, AspectRatio, AssetSourceType, Username, Password` (7
keys) — confirmed 7/7 in that exact order against the real `CrimsonSilk.cuia`.

## Import mechanics

`UiEditor.Server\Helpers\AssetHelper.cs::WriteFileBasedAsset`: the image file is copied to
`<project>/assets/<AssetName><original extension>` — note the file is renamed to match the
*asset's* Name, not kept as the original source filename. `SourceUri` is just that
filename (relative, no path) — confirmed: `CrimsonSilk.cuia`'s `SourceUri = "CrimsonSilk.jpg"`.
Folder/extension constants confirmed in `UiEditor.Common\Constants.cs`:
`AssetPath = "assets"`, `AssetFilenameExtension = ".cuia"`.

`AspectRatio` = `image.Width / image.Height` as a double
(`AssetUtilities.cs::GetImageAspectRatio`, using SixLabors.ImageSharp in C#). Confirmed
**exactly** against the real file: `CrimsonSilk.jpg` is 1776×1118px; computing
`1776/1118` in Python produces `"1.588550983899821"` — byte-for-byte identical to the
real `.cuia`'s stored value, string formatting included. Uses Pillow (`PIL.Image`) to read
dimensions — a new dependency for this project, confirmed available in this environment.

## Referencing an imported asset from a component

Confirmed by direct inspection, no new code needed: a component just sets its `assetid`
attribute to the asset's `Id`. The real image-type button instance carries **no**
`iconurl`/`Url` HTML attribute at all — Construct resolves the design-time image URL
dynamically from `assetid`, it isn't baked into the file. `generator/ch5_button.py`'s
existing `asset_id` parameter already does exactly this; no change was needed there.

## Built this slice

- **`generator/assets.py`**: `import_asset(project_dir, name=..., source_image_path=...)`
  — copies the image, computes the aspect ratio, writes the `.cuia`, returns an
  `AssetInfo` (including the asset's `id`, ready to pass straight into
  `ch5_button.py`'s `asset_id`).
- **`generator/_test_output/phase9_assets_smoke_test.py`**: imports the REAL
  `CrimsonSilk.jpg` (using the real asset's own confirmed Id) and diffs the generated
  `.cuia` against the real `CrimsonSilk.cuia` — 7/7 keys, exact values, including the
  independently-computed `AspectRatio`. Also wires the resulting asset into a
  `ch5_button.py` image-variant button and confirms `assetid` matches.
- Imported the same real asset into the on-disk verification project
  (`C:\Solutions\ClaudeGenTest\GenTestProject\assets\CrimsonSilk.cuia`/`.jpg`) and
  rewired `ButtonVariants.cuig`'s image button to reference it, for the user to check
  in Construct.

## Known gaps (flagged, not blocking)

- Only local-file import is covered (`AssetSourceType = "File"`). URL-based assets
  (`CreateWebBasedAsset` in `AssetHelper.cs`) are a different code path, not built.
- Asset rename/delete (`UpdateAssetHandler.cs`/`DeleteAssetHandler.cs`) and the
  dependent-component-update logic (`AssetUtilities.cs::UpdateAssetsInComponentsOfViews`,
  for when an asset already in use gets swapped) are read but not built — out of scope
  until a real request needs them.
