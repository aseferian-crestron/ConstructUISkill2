"""Task 8: pick_primary / choose_source_resolution."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import pick_primary, choose_source_resolution  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402

def res(width, height, orientation):
    return {"id": f"R-{width}x{height}-{orientation}", "width": width, "height": height, "orientation": ORIENTATION_ENUM[orientation]}

tsw = res(1280, 800, "landscape")
tst_l = res(1920, 1200, "landscape")
tst_p = res(1200, 1920, "portrait")

# pick_primary: highest width in the given orientation; None if that orientation is absent.
assert pick_primary([tsw, tst_l], "landscape") == tst_l  # 1920 > 1280
assert pick_primary([tsw, tst_l], "portrait") is None
assert pick_primary([], "landscape") is None
print("pick_primary: OK")

# choose_source_resolution: same-orientation primary when one exists.
new_landscape = res(640, 360, "landscape")
assert choose_source_resolution([tsw, tst_l, tst_p], new_landscape) == tst_l
print("choose_source_resolution (same-orientation primary): OK")

# Bootstrap case: no existing resolution in the new one's orientation -- use the other's primary.
assert choose_source_resolution([tsw, tst_l], res(800, 1280, "portrait")) == tst_l
print("choose_source_resolution (orientation-bootstrap): OK")

# Nothing to reflow from at all.
assert choose_source_resolution([], new_landscape) is None
print("choose_source_resolution (zero existing resolutions): OK")

print("\nTASK 8: pick_primary / choose_source_resolution -- ALL CHECKS PASSED")
