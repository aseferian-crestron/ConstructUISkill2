"""
.cuip (project file) writer -- Phase 2: create solution / create project.

Grounded directly in C:\\Git\\CCIDE source, not inferred from samples:

  - UiEditor.Server\\Commands\\Solution\\CreateProjectHandler.cs  (defaults applied when
    a project is created: ComponentKey, SdkId auto-detect, ThemePageColor, RuntimeThemeJoin/
    RuntimeLanguageJoin, DefaultComponentMode, DefaultFontFamily, ProjectSchemaVersion)
  - UiEditor.Server\\Helpers\\PersistenceHelper.cs, WriteProject() (~line 38) -- the EXACT
    ordered list of {ProjectAttributes} keys written to disk, including which keys are
    conditionally omitted when empty/default. This module's ATTRIBUTE key order below is
    a direct transcription of that method, confirmed 2026-09-03 to match the real key
    ORDER found in C:\\Solutions\\ClaudeSamples\\Components\\Components.cuip exactly.
  - UiEditor.Common\\Constants.cs: ProjectSchemaVersion=13 (UiEditor.Server\\Constants.cs:321),
    DefaultThemeLanguageJoin="0", DefaultFont="Roboto", DefaultIpId="03",
    ComponentKey "UiEditor" (UI project) vs "ZoomRoomControl" (Zoom project) -- spec's
    "Zoom or UI project?" question maps directly to this attribute.

See docs/architecture/02-project-creation.md for the narrative writeup.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from toml_util import toml_str as _toml_str  # noqa: F401  (re-exported for page.py)

# --- confirmed constants (UiEditor.Common\Constants.cs) -------------------------------

COMPONENT_KEY_UI = "UiEditor"          # UiProjectConstants.ComponentKey (via UiEditorConstants.ServiceKey)
COMPONENT_KEY_ZOOM = "ZoomRoomControl"  # ZoomProjectConstants.ComponentKey

DEFAULT_THEME_LANGUAGE_JOIN = "0"       # UiEditorConstants.DefaultThemeLanguageJoin
DEFAULT_FONT = "Roboto"                 # PageElementAttributes.DefaultFont
PROJECT_DEFAULT_FONT_FAMILY = {COMPONENT_KEY_UI: "Roboto", COMPONENT_KEY_ZOOM: "Inter"}
PROJECT_DEFAULT_THEME = {COMPONENT_KEY_UI: "light-theme.css", COMPONENT_KEY_ZOOM: "zoom-light-theme.css"}
DEFAULT_IP_ID = "03"                    # UiEditorConstants.DefaultIpId
CURRENT_PROJECT_SCHEMA_VERSION = 13     # UiEditor.Server\Constants.cs


def _toml_datetime(dt: datetime) -> str:
    """Nett's observed local-datetime-with-offset format: 'YYYY-MM-DD HH:MM:SS.ffffff+HH:MM'."""
    s = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    off = dt.strftime("%z")  # e.g. -0400
    if off:
        s += f"{off[:3]}:{off[3:]}"
    return s


@dataclass
class FileMetadata:
    """Mirrors Models\\MetadataSource.cs / UiEditorFileMetadata.cs (TOML {FileMetadata}).

    Version strings below are a snapshot of THIS machine's installed AppHost/ProjectApp
    versions (read off a real, currently-open Construct project file), not universal
    constants -- Construct reports its own running version at write time. Safe as a
    default; should be re-confirmed if opening in a different Construct install ever
    fails validation on these fields specifically.
    """

    schema: str = "1.0.0.0"
    created_by_app_host: str = "2.1501.15.0"
    created: datetime = field(default_factory=lambda: datetime.now().astimezone())
    last_modified_by_app_host: str = "2.1501.15.0"
    modified: datetime = field(default_factory=lambda: datetime.now().astimezone())
    created_by_project_app: str = "1.4801.18.0"
    last_modified_by_project_app: str = "1.4801.18.0"
    minimum_project_app: str = "1.2600.1"
    minimum_app_host: str = "2.901.0"

    def to_toml(self) -> str:
        lines = [
            f"Schema = {_toml_str(self.schema)}",
            f"CreatedByAppHost = {_toml_str(self.created_by_app_host)}",
            f"Created = {_toml_datetime(self.created)}",
            f"LastModifiedByAppHost = {_toml_str(self.last_modified_by_app_host)}",
            f"Modified = {_toml_datetime(self.modified)}",
            f"CreatedByProjectApp = {_toml_str(self.created_by_project_app)}",
            f"LastModifiedByProjectApp = {_toml_str(self.last_modified_by_project_app)}",
            f"MinimumProjectApp = {_toml_str(self.minimum_project_app)}",
            f"MinimumAppHost = {_toml_str(self.minimum_app_host)}",
        ]
        return "\n".join(lines) + "\n"


def build_project_attributes(
    *,
    name: str,
    project_id: str | None = None,
    component_key: str = COMPONENT_KEY_UI,
    themes: list[str] | None = None,
    default_theme: str | None = None,
    theme_page_color: str = "",
    include_unused_asset: bool = False,
    override_theme_color: bool = False,
    sdk_id: str,
    runtime_theme_join: str = DEFAULT_THEME_LANGUAGE_JOIN,
    runtime_language_join: str = DEFAULT_THEME_LANGUAGE_JOIN,
    default_component_mode: str = "custom",
    default_font_family: str | None = None,
    resolutions: list[dict] | None = None,
    web_x_panel_ip_id: str = DEFAULT_IP_ID,
    room_id: str = "",
    project_schema_version: int = CURRENT_PROJECT_SCHEMA_VERSION,
    default_language_file: str = "",
    project_language_files: str = "",
    contract_is_stale: bool = True,
) -> tuple[list[tuple[str, str]], list[dict]]:
    """Build the {ProjectAttributes} key/value list in PersistenceHelper.WriteProject's
    exact order, including its exact conditional-omission rules (empty/default -> omitted).
    Returns (attrs, device_resolution_source) -- attrs as an ordered list (not a dict) so
    key ORDER -- confirmed load-bearing, since it's what we diff against the real file --
    is explicit and preserved; device_resolution_source is the {DeviceResolutionSource}
    JSON array (each entry gets ProjectId filled in to match this project's Id).

    `themes`: a project can have MULTIPLE themes associated (ProjectThemeIds, comma-list)
    with one active/default (ThemeId) -- confirmed in docs/architecture/00-overview.md.
    Defaults to a single-element list of the component key's default theme.

    `resolutions`: a project can support MULTIPLE device resolutions simultaneously --
    pass a list of already-shaped DeviceResolutionSource-style dicts (see
    `docs/architecture/00-overview.md`'s DeviceResolutionDto shape, confirmed against a
    real sample). This module does NOT yet know the device catalog or orientation-enum
    semantics (deferred to Phase 5 -- resolutions/reflow) -- it only wires whatever
    resolution dicts the caller supplies into DeviceResolutionIds + DeviceResolutionSource
    correctly, including the N>1 case.
    """
    themes = themes or [PROJECT_DEFAULT_THEME.get(component_key, PROJECT_DEFAULT_THEME[COMPONENT_KEY_UI])]
    theme_id = default_theme or themes[0]
    default_font_family = default_font_family or PROJECT_DEFAULT_FONT_FAMILY.get(component_key, DEFAULT_FONT)
    project_id = project_id or str(uuid4())
    resolutions = resolutions or []

    attrs: list[tuple[str, str]] = [
        ("ComponentKey", component_key),
        ("Name", name),
        ("ThemeId", theme_id),
        ("ProjectThemeIds", ",".join(themes)),
        ("ThemePageColor", theme_page_color),
        ("IncludeUnusedAsset", str(include_unused_asset)),
        ("OverrideThemeColor", str(override_theme_color)),
        ("SdkId", sdk_id),
        ("Id", project_id),
        ("RuntimeThemeJoin", runtime_theme_join),
        ("RuntimeLanguageJoin", runtime_language_join),
        ("DefaultComponentMode", default_component_mode),
        ("DefaultFontFamily", default_font_family),
    ]
    if resolutions:
        attrs.append(("DeviceResolutionIds", ",".join(r["id"] for r in resolutions)))
    if web_x_panel_ip_id:
        attrs.append(("ipId", web_x_panel_ip_id))
    if room_id:
        attrs.append(("roomId", room_id))
    if project_schema_version > 1:
        attrs.append(("ProjectSchemaVersion", str(project_schema_version)))
    if default_language_file:
        attrs.append(("DefaultLanguageFile", default_language_file))
    if project_language_files:
        attrs.append(("ProjectLanguageFiles", project_language_files))
    attrs.append(("ContractIsStale", "true" if contract_is_stale else "false"))

    device_resolution_source = [{"ProjectId": project_id, **r} for r in resolutions]
    return attrs, device_resolution_source


def write_cuip(
    path: Path,
    attributes: list[tuple[str, str]],
    device_resolution_source: list[dict] | None = None,
    metadata: FileMetadata | None = None,
) -> None:
    metadata = metadata or FileMetadata()
    device_resolution_source = device_resolution_source or []

    parts = [
        "{FileMetadata}\n",
        metadata.to_toml(),
        "\n{DeviceResolutionSource}\n",
        json.dumps(device_resolution_source, indent=2),
        "\n\n{ProjectAttributes}\n\n[Attributes]\n",
    ]
    parts.extend(f"{key} = {_toml_str(value)}\n" for key, value in attributes)
    path.write_text("".join(parts), encoding="utf-8")


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("TestProject.cuip")
    attrs, device_resolution_source = build_project_attributes(
        name="TestProject",
        sdk_id="CH5:2.18.0",
        themes=["light-theme.css", "dark-theme.css"],
        default_theme="light-theme.css",
        resolutions=[
            {
                "IsCustom": True, "IsSelected": True, "VisitedName": "TSW-1070",
                "id": "D-L-TSW1070-1280-0800", "idName": "TSW-1070",
                "resolutionId": "L-1280-800", "resolutionName": "TSW-1070",
                "resolutionType": "generic", "deviceSpecId": "TSW-1070",
                "width": "1280px", "height": "800px", "widthMedia": "1280px",
                "heightMedia": "800px", "orientation": 1, "supportedDevices": "",
                "displayNameSuffix": "", "componentKeys": ["UiEditor"],
                "modes": [], "IsMode": False,
            },
            {
                "IsCustom": True, "IsSelected": True, "VisitedName": "TSW-1070 Portrait",
                "id": "D-P-TSW1070-0800-1280", "idName": "TSW-1070 Portrait",
                "resolutionId": "P-800-1280", "resolutionName": "TSW-1070 Portrait",
                "resolutionType": "generic", "deviceSpecId": "TSW-1070",
                "width": "800px", "height": "1280px", "widthMedia": "800px",
                "heightMedia": "1280px", "orientation": 0, "supportedDevices": "",
                "displayNameSuffix": "", "componentKeys": ["UiEditor"],
                "modes": [], "IsMode": False,
            },
        ],
    )
    write_cuip(out, attrs, device_resolution_source)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    print(f"  themes -> ThemeId/ProjectThemeIds: {[v for k, v in attrs if k in ('ThemeId', 'ProjectThemeIds')]}")
    print(f"  resolutions -> DeviceResolutionIds: {[v for k, v in attrs if k == 'DeviceResolutionIds']}")
    for k, v in attrs:
        print(f"  {k} = {v!r}")
