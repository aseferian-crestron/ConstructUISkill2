"""Phase 2 end-to-end smoke test: create solution -> create project -> add to solution."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from solution import create_solution, add_project_to_solution, read_solution  # noqa: E402
from project import build_project_attributes, write_cuip  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase2Smoke"

sol = create_solution(OUT, "Phase2Smoke")
print(f"created solution: {sol.path}")

project_dir = OUT / "MyRoom"
project_dir.mkdir(parents=True, exist_ok=True)
cuip_path = project_dir / "MyRoom.cuip"

attrs, device_resolution_source = build_project_attributes(
    name="MyRoom",
    sdk_id="CH5:2.18.0",
    themes=["light-theme.css", "dark-theme.css"],
    default_theme="dark-theme.css",
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
    ],
)
write_cuip(cuip_path, attrs, device_resolution_source)
print(f"created project: {cuip_path}")

handle = add_project_to_solution(sol, "MyRoom", cuip_path)
print(f"added project to solution: {handle}")

# --- verification ---
reread = read_solution(sol.path)
assert len(reread.projects) == 1, reread.projects
assert reread.projects[0].name == "MyRoom"
assert reread.projects[0].project_dir(reread.solution_dir) == project_dir.resolve(), (
    reread.projects[0].project_dir(reread.solution_dir), project_dir.resolve()
)
print("solution round-trip: project resolves to correct folder -- OK")

ok = compare.round_trip_check(cuip_path)
assert ok, "cuip round-trip / section-order check failed"

print("\nPHASE 2 SMOKE TEST: ALL CHECKS PASSED")
