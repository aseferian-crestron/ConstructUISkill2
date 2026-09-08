"""
.cuia (asset) writer + asset import -- Phase 9 (assets), pulled forward because the
Phase 4 image-button variant can't actually be verified without a real asset to reference.

Grounded directly in C:\\Git\\CCIDE source, not inferred from samples:

  - UiEditor.Common\\Constants.cs: AssetPath = "assets" (folder, relative to the project's
    own folder), AssetFilenameExtension = ".cuia".
  - UiEditor.Server\\Dao\\UiEditorAssetDao.cs: {FileMetadata} + {AssetAttributes} sections
    (same header-split convention as every other Construct file), written via
    `Toml.WriteString(AssetSource)` where `AssetSource.Attributes` is a plain
    `Dictionary<string,string>` -- so its key ORDER is whatever order the caller inserted
    keys in, not a fixed model field order (unlike page/project attributes).
  - UiEditor.Server\\Commands\\AssetManagement\\Handlers\\SaveAssetMetadataHandler.cs: the
    ACTUAL insertion order -- Id, Name, SourceUri, AspectRatio, AssetSourceType, Username,
    Password -- confirmed 7/7 keys in this exact order against the real reference asset
    (C:\\Solutions\\ClaudeSamples\\Components\\assets\\CrimsonSilk.cuia, which is also the
    exact asset the reference project's image-type button already references by Id --
    "498f8b9e-eade-4d9d-9475-49bb03d4324b" -- so this is a genuinely confirmed, not
    inferred, ground truth).
  - UiEditor.Server\\Helpers\\AssetHelper.cs::WriteFileBasedAsset: the image file itself is
    copied to "<project>/assets/<AssetName><original extension>" -- SourceUri is just that
    filename (relative, no path), matching the real file's `SourceUri = "CrimsonSilk.jpg"`.
  - UiEditor.Server\\Commands\\AssetManagement\\Utilities\\AssetUtilities.cs::
    GetImageAspectRatio: `image.Width / image.Height` as a double. Confirmed EXACTLY
    against the real file: CrimsonSilk.jpg is 1776x1118px; 1776/1118 computed in Python
    produces "1.588550983899821" -- byte-for-byte identical to the real .cuia's
    `AspectRatio` value, string formatting included, giving real confidence this
    reproduces C#'s double-to-string formatting for this case (not proven universally).
  - Also confirmed by DIRECT INSPECTION (not needing new code): once an asset exists,
    referencing it from a component is just setting that component's `assetid` attribute
    to the asset's Id -- generator/ch5_button.py's `asset_id` parameter already does this;
    no `iconurl`/`Url` HTML attribute is written statically for a button (confirmed: the
    real image-type button instance has no such attribute at all -- the design-time image
    URL is resolved dynamically from `assetid` by Construct itself, not baked into the
    file).

Real .cuia FileMetadata has `MinimumProjectApp = ""` (empty) -- unlike every other file
type in this project (.cuip/.cuig/.cuiw all have "1.2600.1") -- confirmed directly against
CrimsonSilk.cuia, not a typo. `UiEditorAssetDao.WriteAsset` collects its metadata via a
different helper (`CollectPluginMetadata`) than `PersistenceHelper.WriteProject`, so a
genuinely different default is plausible, not an inconsistency to "fix".

Uses Pillow (PIL) to read image dimensions -- not previously a dependency of this project;
confirmed available in this environment and its output matches C#'s ImageSharp-computed
aspect ratio exactly for the one real file checked (see above).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image

from project import FileMetadata
from toml_util import toml_str as _toml_str

ASSETS_FOLDER = "assets"
ASSET_EXTENSION = ".cuia"


def compute_aspect_ratio(image_path: Path) -> str:
    """Width / Height as a string -- confirmed to match AssetUtilities.GetImageAspectRatio's
    C#-computed value exactly for a real reference file (see module docstring)."""
    with Image.open(image_path) as im:
        width, height = im.size
    return str(width / height)


@dataclass
class AssetInfo:
    id: str
    name: str
    source_uri: str  # filename only, relative to the project's assets/ folder
    aspect_ratio: str
    cuia_path: Path
    image_path: Path


def write_cuia(path: Path, attributes: list[tuple[str, str]], metadata: FileMetadata | None = None) -> None:
    """{FileMetadata} + {AssetAttributes}[Attributes] -- UiEditorAssetDao.WriteAsset's
    exact section shape. `MinimumProjectApp` defaults to "" (confirmed real-file value for
    assets specifically, unlike every other file type) unless the caller overrides it."""
    metadata = metadata or FileMetadata(minimum_project_app="")
    parts = [
        "{FileMetadata}\n",
        metadata.to_toml(),
        "\n{AssetAttributes}\n\n[Attributes]\n",
    ]
    parts.extend(f"{key} = {_toml_str(value)}\n" for key, value in attributes)
    path.write_text("".join(parts), encoding="utf-8")


def import_asset(
    project_dir: Path,
    *,
    name: str,
    source_image_path: Path,
    asset_id: str | None = None,
    username: str = "",
    password: str = "",
) -> AssetInfo:
    """Import a local image file as a new Construct asset: copies it into the project's
    assets/ folder (named after the asset, matching Construct's own WriteFileBasedAsset --
    NOT the original filename) and writes the matching .cuia sidecar. Returns the asset's
    Id, ready to be passed as `asset_id` to generator/ch5_button.py's image-variant builder
    (or any other assetid-bearing component).
    """
    source_image_path = Path(source_image_path)
    asset_id = asset_id or str(uuid4())
    extension = source_image_path.suffix
    filename = f"{name}{extension}"

    assets_dir = project_dir / ASSETS_FOLDER
    assets_dir.mkdir(parents=True, exist_ok=True)
    image_dest = assets_dir / filename
    shutil.copyfile(source_image_path, image_dest)

    aspect_ratio = compute_aspect_ratio(image_dest)
    attrs: list[tuple[str, str]] = [
        ("Id", asset_id),
        ("Name", name),
        ("SourceUri", filename),
        ("AspectRatio", aspect_ratio),
        ("AssetSourceType", "File"),
        ("Username", username),
        ("Password", password),
    ]
    cuia_path = assets_dir / f"{name}{ASSET_EXTENSION}"
    write_cuia(cuia_path, attrs)

    return AssetInfo(id=asset_id, name=name, source_uri=filename, aspect_ratio=aspect_ratio,
                      cuia_path=cuia_path, image_path=image_dest)


if __name__ == "__main__":
    import sys
    import tempfile

    from PIL import Image as _Image

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "AssetTestProject"
        project_dir.mkdir()
        img_path = Path(tmp) / "sample.png"
        _Image.new("RGB", (400, 250), color="crimson").save(img_path)

        info = import_asset(project_dir, name="SampleImage", source_image_path=img_path)
        print(f"asset id: {info.id}")
        print(f"cuia: {info.cuia_path}")
        print(f"image: {info.image_path} (exists: {info.image_path.is_file()})")
        print(f"aspect ratio: {info.aspect_ratio}")
        print(info.cuia_path.read_text(encoding="utf-8"))
