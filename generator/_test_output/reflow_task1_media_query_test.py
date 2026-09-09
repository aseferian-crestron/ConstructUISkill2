"""Task 1: orientation_media_query, confirmed against breakpoint.ts::createRawQuery and
two real portrait sample files (Bug_CCIDE_5225_Widget2.cuiw / Widget5.cuiw)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from layout import orientation_media_query, landscape_media_query  # noqa: E402

# Real confirmed landscape formula, unchanged (existing behavior must not regress).
assert landscape_media_query(1280, 800) == orientation_media_query("landscape", 1280, 800)
assert orientation_media_query("landscape", 1280, 800) == (
    "(orientation: landscape) and (max-width: 1281px) and (max-height: 801px), "
    "(orientation: landscape) and (max-width: 1279px)"
)

# Real confirmed portrait formula (1024x1322, from the two real .cuiw files above).
assert orientation_media_query("portrait", 1024, 1322) == (
    "(orientation: portrait) and (max-height: 1323px) and (max-width: 1025px), "
    "(orientation: portrait) and (max-height: 1321px)"
)

print("TASK 1: orientation_media_query -- landscape unchanged, portrait confirmed. PASSED")
