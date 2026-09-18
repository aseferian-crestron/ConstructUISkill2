"""
"Add existing project as a copy" -- the real Construct action a user invokes
to start a new project from an existing one (e.g. the Design Ideas
template), grounded directly in Construct's own source rather than guessed:

  - `Solution.Client\\Store\\Solution\\Effects\\AddProjectCopyEffect.cs` -- the UI
    orchestration (file picker, name-conflict dialog if a project with that
    name already exists in the target solution).
  - `Solution.Server\\Commands\\Handlers\\AddProjectCopyHandler.cs` -- routes to
    the project-TYPE-specific ("facet") copy command; for a UI project
    (`.cuip`) that's...
  - `UiEditor.Server\\Commands\\Solution\\AddProjectCopyHandler.cs` -- opens the
    source project, then delegates to `ProjectSaveAsCmd`.
  - `UiEditor.Server\\Commands\\Solution\\ProjectSaveAsHandler.cs` -- the ACTUAL
    copy: `uiEditorProject.DeepCopy(newGuids: true)` (line ~115) -- every
    entity in the whole project (the project itself, every page, every
    widget, every asset) gets a BRAND NEW GUID, not just the project's own
    top-level Id -- then every page/widget/asset is individually re-saved
    under the new project's folder, plus the `languages` folder is copied
    verbatim.

This module reproduces that whole-project "new GUIDs everywhere, all
references updated consistently" behavior at the FILE level, without a
running Construct server: collect every GUID a file in the source project
DECLARES as its own identity (`Id = "..."` in a `.cuip`/`.cuig`/`.cuiw`/
`.cuia`'s own `[Attributes]`/`[AssetAttributes]` block -- confirmed this is
the only place a GUID is ever declared "owned," e.g. a page's own Id vs. a
`templateid="w<guid>"` widget REFERENCE elsewhere, which is the same raw
GUID substring, not a separately-declared one), map each to a fresh uuid4,
copy the whole project directory to its new location/name, then do a global
old-GUID -> new-GUID text substitution across every text-based Construct
file in the copy (`.cuip`/`.cuib`/`.cuig`/`.cuiw`/`.cuia`) -- this correctly
rewrites both an entity's own declaration AND every place elsewhere in the
project that references it by the same raw GUID string, the same net effect
`DeepCopy(newGuids: true)` + re-saving every page/widget achieves, without
needing to separately understand every reference attribute's name
(`templateid`, `assetid`, ...). Binary asset files (.jpg/.png/.gif/.svg) are
copied byte-for-byte, untouched -- they never carry a GUID themselves, only
their `.cuia` metadata sibling does.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

_GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_OWN_ID_RE = re.compile(r'(?:^|\n)\s*Id\s*=\s*"(' + _GUID + r')"')

#: Construct's own plain-text/TOML/JSON project file types -- GUID
#: substitution is safe and expected in all of these. Everything else found
#: in a project folder (image/font assets) is copied byte-for-byte.
TEXT_EXTENSIONS = {".cuip", ".cuib", ".cuig", ".cuiw", ".cuia"}

#: NOT copied at all -- confirmed via a real, already-performed "Add Existing
#: Project as a Copy" in Construct itself (2026-09-18): the user copied
#: `C:\Solutions\CrestronDesignIdeas\BasicTemplate_v1_0_2` (which carries
#: both, 33MB `.cca` + 17MB `.cuic`) into their `ClaudeGenTest` solution, and
#: the RESULTING copy has NEITHER file -- Construct's own real copy
#: operation leaves them behind. Independently consistent with `.cuic`
#: appearing on `TabbedCommercial` (this project's own generated project)
#: despite this project's generator never writing one -- Construct created
#: it itself on first open. Both read as regenerable caches (`.cuic`: a
#: large JSON index carrying the project's own GUIDs, confirmed by direct
#: sampling -- exactly the kind of derived content that would go stale
#: after a GUID remap and needs no advance handling; `.cca`: a ZIP archive
#: of asset files already present individually as `.cuia` siblings
#: elsewhere in the project), not primary content this module needs to
#: carry forward or GUID-remap.
SKIP_EXTENSIONS = {".cca", ".cuic"}


def _collect_owned_guids(project_dir: Path) -> set[str]:
    """Every GUID any text file in `project_dir` declares as ITS OWN identity
    (an `Id = "..."` field in that file's own `[Attributes]`/
    `[AssetAttributes]` block) -- NOT every GUID-shaped string anywhere,
    which would also catch a REFERENCE to something outside this project (a
    real, if currently unobserved, risk this project's own "verify before
    assuming identical" discipline warns against guessing past)."""
    owned: set[str] = set()
    for path in project_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            text = path.read_text(encoding="utf-8")
            owned.update(m.group(1) for m in _OWN_ID_RE.finditer(text))
    return owned


def copy_project_as(
    source_project_dir: Path, dest_solution_dir: Path, new_project_name: str,
) -> Path:
    """Copy the Construct project at `source_project_dir` into
    `dest_solution_dir` as a brand-new, independent project named
    `new_project_name` -- every page/widget/asset (and the project itself)
    gets a fresh GUID, with every cross-reference updated consistently, the
    same net effect as Construct's own "Add Existing Project as a Copy"
    (see module docstring for the source-grounded mechanism this mirrors).

    Returns the new project's own `.cuip` path -- pass it to
    `solution.py::add_project_to_solution` to register it in the target
    solution. Raises `FileNotFoundError` if `source_project_dir` has no
    `.cuip` (not a real Construct project directory), and `FileExistsError`
    if `dest_solution_dir / new_project_name` already exists (same conflict
    check `AddProjectCopyEffect.cs` makes before ever calling the server).
    """
    source_project_dir = Path(source_project_dir)
    source_cuips = list(source_project_dir.glob("*.cuip"))
    if not source_cuips:
        raise FileNotFoundError(
            f"{source_project_dir} has no .cuip file -- not a Construct project directory"
        )
    source_cuip = source_cuips[0]
    old_project_name = source_cuip.stem

    dest_project_dir = Path(dest_solution_dir) / new_project_name
    if dest_project_dir.exists():
        raise FileExistsError(
            f"{dest_project_dir} already exists -- a project named {new_project_name!r} "
            f"is already present in the target solution folder"
        )

    owned_guids = _collect_owned_guids(source_project_dir)
    guid_map = {old: str(uuid4()) for old in owned_guids}

    def _ignore_skip_extensions(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if Path(n).suffix.lower() in SKIP_EXTENSIONS}

    shutil.copytree(source_project_dir, dest_project_dir, ignore=_ignore_skip_extensions)

    # Rename the project's own .cuip/.cuib to the new name (Construct names
    # these files after the project itself, confirmed against every real
    # project in this project's own reference solutions).
    for ext in (".cuip", ".cuib"):
        old_path = dest_project_dir / f"{old_project_name}{ext}"
        if old_path.is_file():
            old_path.rename(dest_project_dir / f"{new_project_name}{ext}")

    for path in dest_project_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8")
        new_text = text
        for old, new in guid_map.items():
            if old in new_text:
                new_text = new_text.replace(old, new)
        # The project's own Name field -- distinct from its Id, has to be
        # updated separately (a plain string, not a GUID this loop touches).
        if path.name == f"{new_project_name}.cuip":
            new_text = re.sub(
                r'(?:^|\n)Name = "' + re.escape(old_project_name) + r'"',
                lambda m: m.group(0).replace(old_project_name, new_project_name),
                new_text, count=1,
            )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")

    return dest_project_dir / f"{new_project_name}.cuip"
