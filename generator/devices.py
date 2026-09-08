"""
Real device/resolution catalog reader -- Phase 5 (resolutions).

Source-grounded, not guessed: mirrors generator/sdk.py's AppStorage-reading pattern.

  - `UiEditor.Common\\Constants.cs`: ResolutionPath = "data/ui/resolution",
    ResolutionFile = "resolutionData", CustomResolutionFile = "resolutionData.user"
    (both ".json", `FileExtensions.Data`).
  - `UiEditor.Server\\Commands\\DeviceResolutions\\InitializeLibraryDeviceResolutionsHandler.cs`:
    copies these from the app's bundled resources into AppStoragePath on first run, then
    reads them via `UiEditorResolutionDao.Read` (a plain `List<DeviceResolutionSpec>` JSON
    reader, `JsonStringEnumConverter` registered for the `orientation` enum).
  - `UiEditor.Common\\Models\\DeviceResolutionSpec.cs` / `DisplayOrientation.cs`: the shape
    (id/idName/resolutionId/resolutionName/resolutionType/deviceSpecId/width/height/
    widthMedia/heightMedia/orientation/supportedDevices/displayNameSuffix/componentKeys/
    modes) and the orientation enum (None=0, Landscape=1, Portrait=2, Both=3).

Confirmed against the real file on this machine: 74 entries, including every device
already seen in the reference project (TSW-1070 = id "D-L-TSW1070-1280-0800", matches
generator/project.py's earlier confirmed value exactly) plus phones/tablets/monitors/Zoom
variants. `resolutionName` is a comma-list of every device sharing that exact resolution
(e.g. TSW-1070's real `resolutionName` is "TST-1080 (Landscape), TSW-1070, TSV-1070GV,
TSW-1060, TSW-770, Cisco Navigator - Fullscreen, TSW-880, TSW-1080" -- NOT just "TSW-1070",
correcting an earlier unconfirmed guess used in this project's own project.py smoke example).

See docs/architecture/05-resolutions.md for the full derivation, including the resolved
"UiEditorResolutionDao vs inline .cuip DeviceResolutionSource" and orientation-enum
questions flagged back in Phase 2.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ORIENTATION_ENUM = {"none": 0, "landscape": 1, "portrait": 2, "both": 3}


def default_app_storage_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable not set -- cannot locate Construct's AppStoragePath")
    return Path(appdata) / "crestron-construct" / "AppStorage"


@dataclass
class ResolutionCatalog:
    entries: list[dict]  # raw DeviceResolutionSpec dicts, exactly as read from the JSON files

    def by_id(self, resolution_id: str) -> dict:
        for e in self.entries:
            if e["id"] == resolution_id:
                return e
        raise KeyError(f"No resolution catalog entry with id {resolution_id!r}")

    def by_id_name(self, id_name: str, *, orientation: str | None = None, component_key: str = "UiEditor") -> dict:
        """Look up by the catalog's own device/preset name (e.g. 'TSW-1070', 'iPad Pro 12.9'
        -- note landscape/portrait pairs are two SEPARATE catalog entries sharing the same
        idName, disambiguated by their own '(Landscape)'/'(Portrait)' suffix in some cases,
        or just orientation for device entries like TSW-1070/TST-1080 -- pass `orientation`
        ('landscape'/'portrait') to disambiguate when more than one entry matches.
        Also filters to entries whose `componentKeys` include `component_key` ("UiEditor"
        by default, matching a UI project's own ComponentKey attribute -- see
        generator/project.py) -- confirmed necessary: e.g. plain "TST-1080" without this
        filter matches BOTH the real UI device entry ("TST-1080 (Landscape)") and an
        unrelated Zoom-mode entry that happens to share the bare idName "TST-1080"
        (componentKeys=["ZoomRoomControl"])."""
        matches = [
            e for e in self.entries
            if (e["idName"] == id_name or e["idName"].startswith(id_name + " ("))
            and component_key in e.get("componentKeys", [])
        ]
        if orientation:
            matches = [e for e in matches if e["orientation"] == orientation]
        if not matches:
            raise KeyError(f"No resolution catalog entry named {id_name!r}" + (f" ({orientation})" if orientation else ""))
        if len(matches) > 1:
            names = ", ".join(f"{e['idName']} [{e['orientation']}]" for e in matches)
            raise ValueError(f"{len(matches)} catalog entries match {id_name!r} -- disambiguate with orientation: {names}")
        return matches[0]

    def supports_both_orientations(self, id_name: str) -> bool:
        """True if the catalog has both a landscape and a portrait entry for this device/
        preset name -- e.g. TST-1080 (yes) vs. TSW-1070 (no, landscape-only hardware)."""
        orientations = {e["orientation"] for e in self.entries if e["idName"] == id_name or e["idName"].startswith(id_name + " (")}
        return "landscape" in orientations and "portrait" in orientations


def _normalize_orientation(entries: list[dict]) -> list[dict]:
    """resolutionData.json encodes `orientation` as the DisplayOrientation string
    (JsonStringEnumConverter, registered on UiEditorResolutionDao.Read); resolutionData.
    user.json -- confirmed by reading the real file -- has entries with `orientation` as
    the raw int instead (written by UiEditorResolutionDao.Write, which does NOT register
    that converter). Normalize both to the string form used throughout this module."""
    by_int = {v: k for k, v in ORIENTATION_ENUM.items()}
    out = []
    for e in entries:
        o = e.get("orientation")
        if isinstance(o, int):
            e = {**e, "orientation": by_int[o]}
        out.append(e)
    return out


def read_catalog(app_storage_path: Path | None = None, *, include_custom: bool = False) -> ResolutionCatalog:
    """`include_custom=False` (default) reads only the real, portable, bundled 74-entry
    catalog (resolutionData.json). resolutionData.user.json holds THIS machine's own
    saved custom resolutions -- confirmed to include user-created entries that literally
    collide by name with real catalog entries (e.g. a personal custom resolution also
    named "TSW-1070") -- opt in explicitly (`include_custom=True`) only when the caller
    actually wants this machine's personal saved resolutions, not the portable catalog.
    """
    app_storage_path = app_storage_path or default_app_storage_path()
    res_dir = app_storage_path / "data" / "ui" / "resolution"

    def load(filename: str) -> list[dict]:
        path = res_dir / f"{filename}.json"
        if not path.is_file():
            return []
        return _normalize_orientation(json.loads(path.read_text(encoding="utf-8-sig")))

    entries = load("resolutionData")
    if include_custom:
        entries = entries + load("resolutionData.user")
    return ResolutionCatalog(entries=entries)


def to_project_resolution(entry: dict, *, is_selected: bool = True, is_custom: bool = False) -> dict:
    """Shape a catalog entry into the dict generator/project.py::build_project_attributes
    expects in its `resolutions` list -- i.e. a DeviceResolutionDto minus `ProjectId` (filled
    in by build_project_attributes itself from the project's own Id). `orientation` is
    converted from the catalog's string form to DisplayOrientation's int encoding, matching
    how it's actually serialized inside a .cuip's {DeviceResolutionSource} (confirmed against
    the real Components.cuip: "orientation": 1 for its landscape TSW-1070 entry).
    """
    visited_name = entry["idName"] if not entry.get("displayNameSuffix") else f"{entry['idName']}{entry['displayNameSuffix']}"
    return {
        "IsCustom": is_custom,
        "IsSelected": is_selected,
        "VisitedName": visited_name,
        "id": entry["id"],
        "idName": entry["idName"],
        "resolutionId": entry["resolutionId"],
        "resolutionName": entry["resolutionName"],
        "resolutionType": entry["resolutionType"],
        "deviceSpecId": entry["deviceSpecId"],
        "width": entry["width"],
        "height": entry["height"],
        "widthMedia": entry["widthMedia"],
        "heightMedia": entry["heightMedia"],
        "orientation": ORIENTATION_ENUM[entry["orientation"]],
        "supportedDevices": entry.get("supportedDevices", ""),
        "displayNameSuffix": entry.get("displayNameSuffix", ""),
        "componentKeys": entry.get("componentKeys", []),
        "modes": entry.get("modes", []),
        "IsMode": entry.get("isMode", False),
    }


if __name__ == "__main__":
    catalog = read_catalog()
    print(f"{len(catalog.entries)} catalog entries")
    tsw = catalog.by_id_name("TSW-1070")
    print("TSW-1070:", tsw["id"], tsw["orientation"], tsw["width"], "x", tsw["height"])
    print("TSW-1070 supports both orientations:", catalog.supports_both_orientations("TSW-1070"))
    print("TST-1080 supports both orientations:", catalog.supports_both_orientations("TST-1080"))
    print(to_project_resolution(tsw))
