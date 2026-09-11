"""Phase 6 task 4: end-to-end -- a generated project carries everything Construct needs
to produce a contract, read back off disk rather than from the in-memory structures.

What Construct requires is exactly two things (see generator/contracts.py): the signals
enabled on the components, and ContractIsStale="true" on the project. This asserts both
survive the write, and that adding a resolution to an existing project re-marks it (the
reflow moves components, so the previously-generated contract no longer matches).
"""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from ch5_button import build_default_button_element  # noqa: E402
from contracts import CONTRACT_ENABLED  # noqa: E402
from page import build_page_attributes, write_cuig  # noqa: E402
from project import add_resolutions_to_project, build_project_attributes, write_cuip  # noqa: E402
from sdk import read_sdk  # noqa: E402
from devices import read_catalog, to_project_resolution  # noqa: E402
import compare  # noqa: E402

sdk = read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "ContractsE2E"
OUT.mkdir(parents=True, exist_ok=True)


def sections_of(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    out = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        out[m.group(1)] = raw[start:end]
    return out


# --- a project with two buttons: one default, one with extra signals -----------------
buttons = [
    build_default_button_element(
        sdk, component_name="Play", element_id="ip1a",
        x=40, y=40, width=84, height=42, z_index=1, resolution=(1280, 800)),
    build_default_button_element(
        sdk, component_name="Mute", element_id="im2b",
        x=160, y=40, width=84, height=42, z_index=2, resolution=(1280, 800),
        contract_signals=("Press", "Selected", "Visibility_fb")),
]
page_path = OUT / "Controls.cuig"
write_cuig(
    page_path,
    build_page_attributes(name="Controls"),
    html="".join(html for html, _, _ in buttons),
    css="".join(css for _, css, _ in buttons),
    elements=[element for _, _, element in buttons],
)
assert compare.round_trip_check(page_path), "contract-enabled page failed round-trip"

# --- read the signals back OFF DISK ---------------------------------------------------
page = tomllib.loads(sections_of(page_path)["PageAttributes"])
by_name = {e["Attributes"]["componentName"]: e["Attributes"] for e in page["Elements"]}
assert set(by_name) == {"Play", "Mute"}, sorted(by_name)

enabled = {name: {k for k, v in a.items() if v == CONTRACT_ENABLED} for name, a in by_name.items()}
assert enabled["Play"] == {"sendeventontouch", "pd-receivestateselected"}, enabled["Play"]
assert enabled["Mute"] == {
    "sendeventontouch", "pd-receivestateselected", "pd-receivestateshow",
}, enabled["Mute"]
print("signals survive the .cuig write, per-component: OK")

# The same signals reach the HTML view, which is what the page actually renders from --
# an element whose TOML says one thing and whose html says another is a real failure mode.
html_section = sections_of(page_path)["Html"]
assert html_section.count(f'sendeventontouch="{CONTRACT_ENABLED}"') == 2, "both buttons' Press must be in the html"
assert html_section.count(f'pd-receivestateshow="{CONTRACT_ENABLED}"') == 1, "only Mute has Visibility_fb"
print("signals present in the html view too, not just the TOML elements: OK")

# --- the project file tells Construct to regenerate ------------------------------------
cuip = OUT / "ContractsE2E.cuip"
catalog = read_catalog()
resolutions = [to_project_resolution(catalog.by_id_name("TSW-1070"))]
project_attrs, resolution_source = build_project_attributes(
    name="ContractsE2E", sdk_id="CH5:2.18.0", resolutions=resolutions)
write_cuip(cuip, project_attrs, resolution_source)

attrs = tomllib.loads(sections_of(cuip)["ProjectAttributes"])["Attributes"]
assert attrs["ContractIsStale"] == "true", attrs.get("ContractIsStale")
print("a newly-generated project is marked stale, so Construct regenerates on open: OK")

# --- adding a resolution re-marks a project that Construct has since cleared -----------
# Simulate Construct having opened the project and cleared the flag (ProjectOpenBehavior).
text = cuip.read_text(encoding="utf-8").replace('ContractIsStale = "true"', 'ContractIsStale = "false"')
cuip.write_text(text, encoding="utf-8")

add_resolutions_to_project(cuip, [to_project_resolution(catalog.by_id_name("TSW-770"))])
attrs = tomllib.loads(sections_of(cuip)["ProjectAttributes"])["Attributes"]
assert attrs["ContractIsStale"] == "true", \
    "reflowing for a new resolution moves components, so the contract must be re-marked"
print("adding a resolution re-marks an already-generated project stale: OK")

print("\nContract end-to-end: all assertions passed.")
