# Not an automated test -- prepares the real on-disk verification project for the user
# to check in Construct (this project's standing practice, see Phase 5/9).
#
# CORRECTED 2026-09-09 (task review): the original version overrode a TST-1080 catalog
# entry's width/height fields directly (`smaller["width"], smaller["height"] = 640,
# 360`), leaving its `widthMedia`/`heightMedia`/`resolutionId`/`resolutionName` fields
# still saying 1280x800 -- an internally inconsistent resolution entry Construct never
# authors, and confirmed (by opening the real file after running the original version)
# to leave Construct's own resolution-switcher UI still showing 1280x800, so the
# reflowed 641px-breakpoint block would never actually be exercised -- the plan's only
# real-world check couldn't show anything either way. Fixed by using a genuine catalog
# entry (TSW-570, a real 640x360 landscape device, confirmed present in the catalog)
# instead of hand-overriding fields on an unrelated entry -- every field stays
# self-consistent because it all comes from one real catalog row.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from project import add_resolutions_to_project  # noqa: E402
from devices import read_catalog, to_project_resolution  # noqa: E402

GEN_TEST_CUIP = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject\GenTestProject.cuip")
catalog = read_catalog()
smaller = to_project_resolution(catalog.by_id_name("TSW-570", orientation="landscape"))

warnings = add_resolutions_to_project(GEN_TEST_CUIP, [smaller])
print(f"Added a TSW-570 (640x360 landscape) resolution to {GEN_TEST_CUIP}.")
print(f"Warnings: {warnings or '(none)'}")
print("Open the project in Construct, switch to the new resolution, and confirm the "
      "existing button is on-canvas (not clipped) and not overlapping anything.")
