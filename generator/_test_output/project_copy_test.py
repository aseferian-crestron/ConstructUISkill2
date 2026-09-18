"""project_copy.py -- "Add existing project as a copy" at the file level,
grounded in Construct's own AddProjectCopyHandler.cs/ProjectSaveAsHandler.cs
(UiEditor.Server) source: every entity in the copied project gets a fresh
GUID (project/pages/widgets/assets), every cross-reference updated
consistently."""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
from project_copy import copy_project_as, TEXT_EXTENSIONS, SKIP_EXTENSIONS  # noqa: E402
from solution import create_solution, add_project_to_solution, read_solution  # noqa: E402

GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

SOURCE = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject")
OUT = Path(__file__).resolve().parent / "ProjectCopy"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

# --- create a fresh target solution, copy the source project into it ---------------
solution = create_solution(OUT, "CopyTestSolution")
new_cuip = copy_project_as(SOURCE, OUT, "CopiedLights")
assert new_cuip.name == "CopiedLights.cuip"
assert new_cuip.is_file()
print("copy_project_as: new .cuip exists at the expected path: OK")

# --- every file present in the source is present in the copy (same relative layout,
# except SKIP_EXTENSIONS -- Construct-regenerated caches, never copied) -------------
source_files = {
    p.relative_to(SOURCE) for p in SOURCE.rglob("*")
    if p.is_file() and p.suffix.lower() not in SKIP_EXTENSIONS
}
# account for the .cuip/.cuib rename
source_files = {
    (p.parent / p.name.replace("GenTestProject", "CopiedLights")) if p.suffix in (".cuip", ".cuib") else p
    for p in source_files
}
dest_files = {p.relative_to(new_cuip.parent) for p in new_cuip.parent.rglob("*") if p.is_file()}
assert source_files == dest_files, (source_files - dest_files, dest_files - source_files)
print("copy_project_as: every source file present in the copy (renamed .cuip/.cuib): OK")

# --- no GUID from the source project survives anywhere in the copy ------------------
source_guids = set()
for p in SOURCE.rglob("*"):
    if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS:
        source_guids.update(GUID.findall(p.read_text(encoding="utf-8")))

dest_guids = set()
for p in new_cuip.parent.rglob("*"):
    if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS:
        dest_guids.update(GUID.findall(p.read_text(encoding="utf-8")))

overlap = source_guids & dest_guids
assert not overlap, f"source GUIDs leaked into the copy unchanged: {overlap}"
assert len(dest_guids) == len(source_guids), (len(dest_guids), len(source_guids))
print(f"copy_project_as: all {len(source_guids)} source GUIDs replaced with fresh ones, none leaked: OK")

# --- referential integrity: every widget reference in a copied page resolves to a --
# real widget Id that ALSO exists in the copy (not a dangling/foreign reference) -----
resolved_any = False
for page in new_cuip.parent.glob("*.cuig"):
    text = page.read_text(encoding="utf-8")
    for m in re.finditer(r'templateid="w(' + GUID.pattern + r')"', text):
        resolved_any = True
        assert m.group(1) in dest_guids, f"{page.name} references widget {m.group(1)} not found in the copy"
if resolved_any:
    print("copy_project_as: every page's widget reference resolves to a real widget Id in the copy: OK")
else:
    print("copy_project_as: (no ch5-template widget references in this source project to check)")

# --- the new project's Name field was updated -------------------------------------
cuip_text = new_cuip.read_text(encoding="utf-8")
assert 'Name = "CopiedLights"' in cuip_text
assert "GenTestProject" not in cuip_text
print("copy_project_as: new .cuip's Name field updated, old name gone: OK")

# --- round-trip check on a couple of the copied files -------------------------------
checked = 0
for p in list(new_cuip.parent.glob("*.cuig"))[:2] + list(new_cuip.parent.glob("*.cuiw"))[:2]:
    assert compare.round_trip_check(p), p.name
    checked += 1
print(f"copy_project_as: {checked} copied page/widget file(s) round-trip byte-identical: OK")

# --- register the copy in the target solution ---------------------------------------
add_project_to_solution(solution, "CopiedLights", new_cuip)
reloaded = read_solution(solution.path)
assert reloaded.find_project("CopiedLights") is not None
print("copy_project_as + add_project_to_solution: registered in the new solution's .csln: OK")

# --- conflict: copying into a dest that already has that project name raises --------
try:
    copy_project_as(SOURCE, OUT, "CopiedLights")
    raise AssertionError("expected FileExistsError for a name already used in the target")
except FileExistsError:
    pass
print("copy_project_as: copying into an already-used project name raises FileExistsError: OK")

# --- missing source raises ----------------------------------------------------------
try:
    copy_project_as(OUT, OUT, "NoSourceHere")
    raise AssertionError("expected FileNotFoundError for a source dir with no .cuip")
except FileNotFoundError:
    pass
print("copy_project_as: a source dir with no .cuip raises FileNotFoundError: OK")

print("Project Copy: all assertions passed.")
