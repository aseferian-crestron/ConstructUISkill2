# Not an automated test -- prepares the real on-disk verification project for the user
# to check in Construct (this project's standing practice, see Phase 5/9).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from project import add_resolutions_to_project  # noqa: E402
from devices import read_catalog, to_project_resolution  # noqa: E402

GEN_TEST_CUIP = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject\GenTestProject.cuip")
catalog = read_catalog()
smaller = to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape"))
smaller["width"], smaller["height"] = 640, 360

warnings = add_resolutions_to_project(GEN_TEST_CUIP, [smaller])
print(f"Added a 640x360 landscape resolution to {GEN_TEST_CUIP}.")
print(f"Warnings: {warnings or '(none)'}")
print("Open the project in Construct, switch to the new resolution, and confirm the "
      "existing button is on-canvas (not clipped) and not overlapping anything.")
