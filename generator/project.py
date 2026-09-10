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
import re
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from toml_util import toml_str as _toml_str, override_attr  # noqa: F401  (toml_str re-exported for page.py)

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
    is explicit and preserved.

    `themes`: a project can have MULTIPLE themes associated (ProjectThemeIds, comma-list)
    with one active/default (ThemeId) -- confirmed in docs/architecture/00-overview.md.
    Defaults to a single-element list of the component key's default theme.

    `resolutions`: a project can support MULTIPLE device resolutions simultaneously --
    pass a list of dicts shaped like `devices.py::to_project_resolution`'s return value
    (catalog-sourced only -- this module has no "genuinely custom resolution" builder yet).
    Every id goes into `DeviceResolutionIds`. `device_resolution_source` (the returned
    {DeviceResolutionSource} JSON array) is always empty: confirmed directly from
    `PersistenceHelper.cs`'s WriteProject -- that section ONLY ever persists
    `CustomDeviceResolutions`, never catalog-sourced picks (see
    devices.py::to_project_resolution's docstring for the full citation and the real
    corruption this caused when an earlier version got it backwards).
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

    device_resolution_source: list[dict] = []  # see docstring: catalog picks never go here
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


_HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)


def read_cuip(path: Path) -> tuple[list[tuple[str, str]], list[dict], FileMetadata]:
    """Read a .cuip back into the same shapes write_cuip/build_project_attributes use --
    Phase 5 (resolutions): needed to add a resolution to an EXISTING project rather than
    only ever writing one from scratch. Preserves the real `Created` timestamp; the caller
    is expected to still hand a fresh `Modified` via a new FileMetadata if it wants one --
    this just carries the file's own metadata through unchanged by default."""
    raw = path.read_text(encoding="utf-8")
    headers = list(_HEADER_RE.finditer(raw))
    sections: dict[str, str] = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        sections[m.group(1)] = raw[start:end]

    meta = tomllib.loads(sections["FileMetadata"])
    metadata = FileMetadata(
        schema=meta["Schema"], created_by_app_host=meta["CreatedByAppHost"], created=meta["Created"],
        last_modified_by_app_host=meta["LastModifiedByAppHost"], modified=meta["Modified"],
        created_by_project_app=meta["CreatedByProjectApp"], last_modified_by_project_app=meta["LastModifiedByProjectApp"],
        minimum_project_app=meta["MinimumProjectApp"], minimum_app_host=meta["MinimumAppHost"],
    )
    device_resolution_source = json.loads(sections["DeviceResolutionSource"])
    attrs = list(tomllib.loads(sections["ProjectAttributes"])["Attributes"].items())
    return attrs, device_resolution_source, metadata


def _numeric_dim(value: int | str) -> int:
    """A resolution's width/height as stored in {DeviceResolutionSource} may be a plain
    int (hand-built/test resolutions) or the real catalog's confirmed 'Npx' string form
    (devices.py::to_project_resolution -- confirmed against a real .cuip's own
    {DeviceResolutionSource}, e.g. "1280px"). Coerce to int; used only for feeding
    reflow.py's arithmetic, never for what's written back to disk."""
    if isinstance(value, str):
        return int(value[:-2]) if value.endswith("px") else int(value)
    return value


def _numeric_resolution(r: dict) -> dict:
    """Shallow copy of a resolution dict with width/height coerced to int (see
    _numeric_dim) -- everything else (id, orientation, etc.) passed through unchanged."""
    return {**r, "width": _numeric_dim(r["width"]), "height": _numeric_dim(r["height"])}


def add_resolutions_to_project(cuip_path: Path, new_resolutions: list[dict]) -> list[str]:
    """Add one or more catalog-sourced resolution dicts (see generator/devices.py::
    to_project_resolution) to an existing project's .cuip, updating `DeviceResolutionIds`
    and marking `ContractIsStale`.

    `{DeviceResolutionSource}` is read and written back UNCHANGED -- confirmed from source
    (see devices.py::to_project_resolution's docstring) that it only ever holds genuinely
    CUSTOM resolutions, never catalog picks like the ones this function adds. An earlier
    version of this function appended every new resolution to `{DeviceResolutionSource}`
    regardless of source, which is what actually produced a real corrupted-looking project
    (a catalog device appearing twice in Construct's own Resolution Manager -- once as
    itself, once as a phantom deletable "custom" duplicate) that the user found and fixed
    by hand in Construct (2026-09-10). `DeviceResolutionIds` (not `{DeviceResolutionSource}`)
    is the authoritative membership list for a project's resolutions, both catalog and
    custom -- read from there, not from `{DeviceResolutionSource}`.

    Also reflows every existing *.cuig/*.cuiw in the project's folder so each newly-added
    resolution gets a correctly-fitted @media block for whatever elements already exist
    (see generator/reflow.py and docs/superpowers/specs/2026-09-08-multi-resolution-
    reflow-design.md) -- returns the aggregated list of any reflow warnings (e.g. a new
    element flagged as possibly overlapping a pinned one), never raises for them. This
    includes an unhandled I/O failure on any single page/widget file (e.g. Construct
    itself holding the file open) -- ADDED 2026-09-09 (task review): reflow_file only
    guards against parse failures, not OS-level file errors, but the spec's own
    contract ("never a hard crash that aborts reflowing the rest of the project's
    files") applies to every failure class, not just parse ones -- a raised OSError
    here would leave the .cuip write below never happening while some page files had
    already been rewritten, a silently inconsistent project. Wrapped per-file.
    """
    import devices
    import reflow
    import sdk as sdk_module

    attrs, device_resolution_source, metadata = read_cuip(cuip_path)
    project_dir = cuip_path.parent
    warnings: list[str] = []

    # ADDED 2026-09-10 (real D-pad overlap bug -- see reflow.py::_is_aspect_locked's
    # docstring): loading the project's own installed SDK enables schema-driven CSS-var
    # scaling, aspect-lock reconciliation, and size="regular"->"custom" forcing inside
    # reflow_file. Never fatal: a project with an SdkId reflow_file can't resolve (not
    # installed, malformed attribute) still gets its resolution added and pages
    # reflowed with the pre-2026-09-10 legacy behavior, just flagged with a warning
    # rather than aborting the whole operation over an SDK read issue.
    ui_sdk = None
    sdk_id = dict(attrs).get("SdkId")
    if sdk_id and ":" in sdk_id:
        try:
            ui_sdk = sdk_module.read_sdk(sdk_id.split(":", 1)[1])
        except (FileNotFoundError, OSError, KeyError) as e:
            warnings.append(f"Could not load SDK {sdk_id!r} ({e}) -- reflow will use legacy CSS-var scaling")

    existing_ids = [i for i in dict(attrs).get("DeviceResolutionIds", "").split(",") if i]

    # Full width/height/orientation for every resolution already in the project, needed
    # for reflow's choose_source_resolution. Resolve each id against the global catalog
    # first (the common case); fall back to this project's own {DeviceResolutionSource}
    # only for ids the catalog doesn't recognize (a genuinely custom resolution).
    catalog = devices.read_catalog()

    def _resolve(resolution_id: str) -> dict:
        try:
            return devices.to_project_resolution(catalog.by_id(resolution_id))
        except KeyError:
            match = next((e for e in device_resolution_source if e["id"] == resolution_id), None)
            if match is None:
                raise KeyError(
                    f"Resolution id {resolution_id!r} is in DeviceResolutionIds but found "
                    "neither in the global catalog nor in this project's own "
                    "{DeviceResolutionSource}"
                ) from None
            return match

    existing_full = [_resolve(i) for i in existing_ids]

    for r in new_resolutions:
        # Real catalog-sourced resolutions (devices.py::to_project_resolution) carry
        # width/height as the confirmed real-file "Npx" string form (e.g. "1280px"), but
        # reflow.py/layout.py do arithmetic on these values (media-query +-1px formulas,
        # pick_primary's width comparison) and need plain ints. Coerce to int only for the
        # numeric copies fed into the reflow subsystem.
        numeric_existing = [_numeric_resolution(e) for e in existing_full]
        numeric_r = _numeric_resolution(r)
        source = reflow.choose_source_resolution(numeric_existing, numeric_r)
        existing_ids.append(r["id"])
        existing_full.append(r)
        if source is not None:
            page_files = list(project_dir.glob("*.cuig")) + list(project_dir.glob("*.cuiw"))
            for page_path in page_files:
                try:
                    result = reflow.reflow_file(page_path, target_resolution=numeric_r, source_resolution=source, mode="pin_existing", sdk=ui_sdk)
                except OSError as e:
                    warnings.append(f"{page_path.name}: {e} -- skipped")
                    continue
                warnings.extend(result.warnings)

    ids_csv = ",".join(existing_ids)

    keys = [k for k, _ in attrs]
    if "DeviceResolutionIds" in keys:
        override_attr(attrs, "DeviceResolutionIds", ids_csv)
    else:
        attrs.insert(keys.index("DefaultFontFamily") + 1, ("DeviceResolutionIds", ids_csv))
    override_attr(attrs, "ContractIsStale", "true")

    write_cuip(cuip_path, attrs, device_resolution_source, metadata=metadata)
    return warnings


if __name__ == "__main__":
    import sys

    from devices import read_catalog, to_project_resolution

    # NOTE: a prior version of this example fabricated a "TSW-1070 Portrait" resolution
    # that does not exist in the real catalog (TSW-1070 is landscape-only hardware) --
    # see docs/architecture/05-resolutions.md. TST-1080 genuinely supports both
    # orientations, so it's used here instead to demonstrate a real landscape+portrait pair.
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("TestProject.cuip")
    catalog = read_catalog()
    attrs, device_resolution_source = build_project_attributes(
        name="TestProject",
        sdk_id="CH5:2.18.0",
        themes=["light-theme.css", "dark-theme.css"],
        default_theme="light-theme.css",
        resolutions=[
            to_project_resolution(catalog.by_id_name("TSW-1070")),
            to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape")),
            to_project_resolution(catalog.by_id_name("TST-1080", orientation="portrait")),
        ],
    )
    write_cuip(out, attrs, device_resolution_source)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    print(f"  themes -> ThemeId/ProjectThemeIds: {[v for k, v in attrs if k in ('ThemeId', 'ProjectThemeIds')]}")
    print(f"  resolutions -> DeviceResolutionIds: {[v for k, v in attrs if k == 'DeviceResolutionIds']}")
    for k, v in attrs:
        print(f"  {k} = {v!r}")
