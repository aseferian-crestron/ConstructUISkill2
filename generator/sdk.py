"""
Installed CH5 UI SDK reader -- Phase 4 (add a CH5 component).

Grounded directly in C:\\Git\\CCIDE source, not inferred from samples:

  - PageDesigner.Common\\Constants.cs: SdkFolder = "data/ui/sdk" (relative to Construct's
    own AppStoragePath), Filenames.Schema = "schema", .SchemaAddendum = "schemaaddendum",
    .ComponentAttributes = "component-context", .SassSchema = "sass-schema",
    .IconData = "icon-library" -- all ".json" (FileExtensions.Data).
  - PageDesigner.Server\\Dao\\UiSdkDao.cs::ReadSdkAsync -- reads exactly these 5 files from
    "<ManifestPath>/<sdkHandle.Location>/data/" for one installed SDK version. A project's
    own SdkId attribute (e.g. "CH5:2.18.0", see generator/project.py) names the version.

Construct's AppStoragePath itself is not read from any config by this module -- it is
resolved the same way `EnvironmentUtility.cs` (`Crestron.IDE\\AppHost\\Crestron.IDE\\
Common\\Utils\\EnvironmentUtility.cs`) does per-OS: `<OS ApplicationData folder>/
crestron-construct/AppStorage`. Confirmed on this (Windows) machine at
"%APPDATA%\\crestron-construct\\AppStorage"; on macOS that same .NET call resolves (per
that file's own code comment) to `~/Library/Application Support`, not the more commonly
documented `~/.config`. This module only ever *reads* these files (never writes/modifies
an installed SDK).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


def default_app_storage_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA environment variable not set -- cannot locate Construct's AppStoragePath")
        base = Path(appdata)
    return base / "crestron-construct" / "AppStorage"


@dataclass
class UiSdk:
    version: str
    schema: dict          # schema.json -> {"ch5Elements": {"elements": [...]}, ...}
    component_context: dict  # component-context.json -> {"<tagName>": {...}, "global": {...}}
    sass_schema: dict     # sass-schema.json -> {"<tagName>": [...]}

    def element_def(self, name: str) -> dict:
        """Look up a Ch5ElementDef by its schema.json 'name' field, e.g. 'Ch5 Button'."""
        for el in self.schema["ch5Elements"]["elements"]:
            if el.get("name") == name:
                return el
        raise KeyError(f"No ch5Elements entry named {name!r} in schema.json")

    def context_for(self, tag_name: str) -> dict:
        """component-context.json's per-tag entry, e.g. 'ch5-button'."""
        return self.component_context[tag_name]

    def sass_sectors_for(self, tag_name: str) -> list[dict]:
        """sass-schema.json's per-tag sector-definition list, e.g. 'ch5-button'."""
        return self.sass_schema.get(tag_name, [])


def sdk_id_to_version(sdk_id: str) -> str:
    """'CH5:2.18.0' (generator/project.py's SdkId attribute format) -> '2.18.0'."""
    return sdk_id.split(":", 1)[1] if ":" in sdk_id else sdk_id


def read_sdk(version: str, app_storage_path: Path | None = None) -> UiSdk:
    app_storage_path = app_storage_path or default_app_storage_path()
    data_dir = app_storage_path / "data" / "ui" / "sdk" / version / "data"
    if not data_dir.is_dir():
        raise FileNotFoundError(f"SDK {version} not found (looked in {data_dir})")

    def load(filename: str) -> dict:
        # utf-8-sig: schema files on this machine carry a BOM (matches .NET's default
        # UTF-8 file writer); plain utf-8 also parses fine with -sig if no BOM present.
        return json.loads((data_dir / f"{filename}.json").read_text(encoding="utf-8-sig"))

    return UiSdk(
        version=version,
        schema=load("schema"),
        component_context=load("component-context"),
        sass_schema=load("sass-schema"),
    )


if __name__ == "__main__":
    import sys

    version = sys.argv[1] if len(sys.argv) > 1 else "2.18.0"
    sdk = read_sdk(version)
    btn = sdk.element_def("Ch5 Button")
    print(f"SDK {sdk.version}: {len(sdk.schema['ch5Elements']['elements'])} ch5Elements")
    print(f"Ch5 Button: tagName={btn['tagName']!r}, {len(btn['attributes'])} schema attributes")
    ctx = sdk.context_for("ch5-button")
    print(f"component-context defaults.attributes: {len(ctx['defaults']['attributes'])} keys")
    sectors = sdk.sass_sectors_for("ch5-button")
    print(f"sass-schema sectors: {len(sectors)}")
