"""
.csln solution reader + active-project selection (spec section 7).

Confirmed against C:\\Git\\CCIDE\\Crestron.IDE\\Components\\Solution\\Solution.Server
(SolutionDao.cs, Solution.cs, ProjectHandleDto.cs) and directly against
C:\\Solutions\\ClaudeSamples\\ClaudeSamples.csln — see docs/architecture/00-overview.md.

.csln is plain JSON (System.Text.Json, no TOML/header-splitting):
  { "_fileMetadata": {...}, "_solution": { "_name": ..., "_projects": [
        { "_name": ..., "_filename": <path relative to the .csln's own folder>,
          "_datetime": ... }, ... ] } }

The project<->solution link is by name + relative path, NOT GUID -- a project's own
GUID lives only inside its .cuip and is never stored in the .csln.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ProjectHandle:
    name: str
    relative_path: str  # as stored in the .csln, forward-slash separated
    datetime: str

    def project_dir(self, solution_dir: Path) -> Path:
        """Folder containing this project's .cuip (and everything else for the project)."""
        return (solution_dir / self.relative_path).resolve().parent


@dataclass
class Solution:
    path: Path
    name: str
    projects: list[ProjectHandle]

    @property
    def solution_dir(self) -> Path:
        return self.path.resolve().parent

    def find_project(self, name: str) -> ProjectHandle | None:
        for p in self.projects:
            if p.name == name:
                return p
        return None


def read_solution(csln_path: Path) -> Solution:
    data = json.loads(csln_path.read_text(encoding="utf-8"))
    sol = data["_solution"]
    projects = [
        ProjectHandle(
            name=p["_name"],
            relative_path=p["_filename"],
            datetime=p.get("_datetime", ""),
        )
        for p in sol.get("_projects", [])
    ]
    return Solution(path=csln_path, name=sol["_name"], projects=projects)


def select_active_project(csln_path: Path, project_name: str | None) -> tuple[Solution, ProjectHandle]:
    """Spec section 7: resolve which project in a solution is the active working context.

    If project_name is None and the solution has exactly one project, that project is
    selected automatically. Otherwise the caller must supply a name -- the skill layer
    (not this function) is responsible for prompting the user with the exact names
    found here when project_name is not given and more than one project exists.
    """
    solution = read_solution(csln_path)
    if project_name is None:
        if len(solution.projects) == 1:
            return solution, solution.projects[0]
        names = ", ".join(p.name for p in solution.projects)
        raise ValueError(
            f"Solution '{solution.name}' has {len(solution.projects)} projects "
            f"({names}) -- a project name must be specified."
        )
    handle = solution.find_project(project_name)
    if handle is None:
        names = ", ".join(p.name for p in solution.projects)
        raise ValueError(f"No project named '{project_name}' in solution '{solution.name}'. Known projects: {names}")
    return solution, handle


def _dotnet_o_datetime(dt: datetime) -> str:
    """.NET round-trip ('O') DateTime format, matching System.Text.Json's default --
    e.g. '2026-07-23T15:34:57.9628659-04:00'. Confirmed against a real .csln
    (C:\\Solutions\\ClaudeSamples\\ClaudeSamples.csln). Python only carries microsecond
    (6-digit) precision vs .NET's 100ns ticks (7-digit); padded with a trailing zero --
    harmless, since this is a JSON string field re-parsed by System.Text.Json's DateTime
    parser, not something our own splitter/round-trip logic depends on byte-for-byte.
    """
    base = dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "0"  # pad micro- to tick-ish precision
    off = dt.strftime("%z")
    return f"{base}{off[:3]}:{off[3:]}" if off else base + "Z"


def write_solution(csln_path: Path, name: str, projects: list[ProjectHandle], now: datetime | None = None) -> None:
    """Write a .csln matching SolutionDao.Write's JSON shape (Solution.Server\\Dao\\SolutionDao.cs,
    Models\\SolutionFileContent.cs, Models\\Solution.cs) -- confirmed directly against
    C:\\Solutions\\ClaudeSamples\\ClaudeSamples.csln's real structure/keys.
    """
    now = now or datetime.now().astimezone()
    doc = {
        "_fileMetadata": {
            "_schema": "1.0.0.0",
            "_createdByAppHost": "2.1501.15.0",
            "_created": _dotnet_o_datetime(now),
            "_lastModifiedByAppHost": "2.1501.15.0",
            "_minimumAppHost": "2.901.0",
            "_modified": _dotnet_o_datetime(now),
        },
        "_solution": {
            "_name": name,
            "_projects": [
                {"_name": p.name, "_filename": p.relative_path, "_datetime": p.datetime or _dotnet_o_datetime(now)}
                for p in projects
            ],
        },
    }
    csln_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def create_solution(solution_dir: Path, name: str) -> Solution:
    """Smallest possible write path: a brand-new solution with zero projects yet.
    Mirrors CreateSolutionHandler.cs's no-ProjectOptions branch (a solution can be
    created standalone, with project(s) added afterward via add_project_to_solution).
    """
    solution_dir.mkdir(parents=True, exist_ok=True)
    csln_path = solution_dir / f"{name}.csln"
    write_solution(csln_path, name, [])
    return Solution(path=csln_path, name=name, projects=[])


def add_project_to_solution(solution: Solution, project_name: str, project_cuip_path: Path) -> ProjectHandle:
    """Mirrors AddProjectHandler.cs: relative path computed from the solution's own
    folder, forward-slash separated ('ForceSingleForwardSlashInPath'). Appends the new
    project handle and rewrites the .csln with every existing project handle preserved.
    """
    rel = Path(project_cuip_path).resolve().relative_to(solution.solution_dir).as_posix()
    handle = ProjectHandle(name=project_name, relative_path=rel, datetime=_dotnet_o_datetime(datetime.now().astimezone()))
    solution.projects.append(handle)
    write_solution(solution.path, solution.name, solution.projects)
    return handle


if __name__ == "__main__":
    import sys

    csln = Path(sys.argv[1])
    wanted = sys.argv[2] if len(sys.argv) > 2 else None
    solution, active = select_active_project(csln, wanted)
    print(f"Solution: {solution.name}  ({len(solution.projects)} project(s))")
    for p in solution.projects:
        marker = " <-- active" if p is active else ""
        print(f"  - {p.name}: {p.relative_path} -> {p.project_dir(solution.solution_dir)}{marker}")
