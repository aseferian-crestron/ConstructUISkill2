"""Phase 6 task 7: writing a page or widget marks its project's contract stale.

Everything that changes what the contract is derived from has to set ContractIsStale --
components added or removed, signals enabled or disabled, pages/widgets created or
renamed (object names ARE the contract's signal names). Marking it was previously left
to each caller, and write_cuig (the function behind every one of those changes) did not
do it, so correctness depended on whoever called it remembering.
"""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ch5_button import build_default_button_element  # noqa: E402
from page import build_page_attributes, write_cuig  # noqa: E402
from project import build_project_attributes, write_cuip  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "ContractsAutoStale"
OUT.mkdir(parents=True, exist_ok=True)


def stale_flag(cuip: Path) -> str:
    raw = cuip.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    for i, m in enumerate(headers):
        if m.group(1) == "ProjectAttributes":
            end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
            return tomllib.loads(raw[m.end():end])["Attributes"]["ContractIsStale"]
    raise LookupError("no ProjectAttributes")


def fresh_project(name: str) -> Path:
    """A project whose contract Construct has already generated and un-staled, in its own
    folder -- a real project is one .cuip per directory, alongside its pages."""
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    cuip = folder / f"{name}.cuip"
    attrs, resolutions = build_project_attributes(
        name=name, sdk_id="CH5:2.18.0", contract_is_stale=False)
    write_cuip(cuip, attrs, resolutions)
    assert stale_flag(cuip) == "false"
    return cuip


html, css, element = build_default_button_element(
    sdk, component_name="Button1", element_id="i9nb",
    x=40, y=40, width=84, height=42, z_index=1, resolution=(1280, 800))

# --- adding a page to a project marks that project stale ------------------------------
cuip = fresh_project("AutoStale")
write_cuig(cuip.parent / "NewPage.cuig", build_page_attributes(name="NewPage"),
           html=html, css=css, elements=[element])
assert stale_flag(cuip) == "true", \
    "a page carrying a contract-enabled component must leave the project stale"
print("writing a page marks the sibling project stale: OK")

# --- the same for a widget ------------------------------------------------------------
cuip = fresh_project("AutoStaleWidget")
write_cuig(cuip.parent / "NewWidget.cuiw", build_page_attributes(name="NewWidget"),
           html=html, css=css, elements=[element])
assert stale_flag(cuip) == "true", "a widget write must mark the project too"
print("writing a widget marks it too: OK")

# --- rewriting an existing page counts as well ----------------------------------------
# Renaming a component or toggling a signal both arrive as "the page was rewritten";
# there is nothing in the file to distinguish them from a no-op rewrite, so every write
# marks. Over-marking costs one regeneration on next open; under-marking ships a project
# whose contract does not match its pages.
cuip = fresh_project("AutoStaleRewrite")
page = cuip.parent / "Existing.cuig"
write_cuig(page, build_page_attributes(name="Existing"), html=html, css=css, elements=[element])
cuip.write_text(cuip.read_text(encoding="utf-8").replace('"true"', '"false"'), encoding="utf-8")
assert stale_flag(cuip) == "false"
write_cuig(page, build_page_attributes(name="Existing"), html=html, css=css, elements=[element])
assert stale_flag(cuip) == "true", "rewriting an existing page must re-mark"
print("rewriting an existing page re-marks: OK")

# --- a page written outside any project is not an error -------------------------------
# Most of the test suite writes pages into scratch directories with no .cuip beside them.
loose = OUT / "Loose"
loose.mkdir(exist_ok=True)
write_cuig(loose / "Orphan.cuig", build_page_attributes(name="Orphan"),
           html=html, css=css, elements=[element])
print("a page with no project beside it is written without complaint: OK")

# --- opting out is possible but explicit ----------------------------------------------
cuip = fresh_project("AutoStaleOptOut")
write_cuig(cuip.parent / "OptOut.cuig", build_page_attributes(name="OptOut"),
           html=html, css=css, elements=[element], mark_project_stale=False)
assert stale_flag(cuip) == "false", "mark_project_stale=False must leave the flag alone"
print("mark_project_stale=False opts out: OK")

# --- two projects in one folder is ambiguous, and says so ----------------------------
# Not a real project layout, but silently picking one would be the exact failure this
# mechanism exists to prevent.
ambiguous = OUT / "Ambiguous"
ambiguous.mkdir(exist_ok=True)
for project_name in ("One", "Two"):
    attrs, resolutions = build_project_attributes(name=project_name, sdk_id="CH5:2.18.0")
    write_cuip(ambiguous / f"{project_name}.cuip", attrs, resolutions)
try:
    write_cuig(ambiguous / "Page.cuig", build_page_attributes(name="Page"),
               html=html, css=css, elements=[element])
except RuntimeError as e:
    assert "cannot tell which project" in str(e), str(e)
    print("two projects in one folder raises rather than guessing: OK")
else:
    raise AssertionError("an ambiguous project folder must raise")

print("\nAutomatic stale marking: all assertions passed.")
