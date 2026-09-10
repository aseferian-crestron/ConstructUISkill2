"""Task 3: stack_rows gains source_height -- a vertically-centered source row-stack
comes back centered in target_height instead of pinned to the top."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import stack_rows  # noqa: E402

# Two rows, each one element: row0 top=400 height=50 (ends 450), row1 top=500 height=100
# (ends 600) -> group top=400, bottom=600, top_margin=400, bottom_margin=1000-600=400.
# Centered (diff 0) in a 1000px-tall source.
rows = [["a"], ["b"]]
elements = {"a": {"top": 400, "height": 50}, "b": {"top": 500, "height": 100}}
result = stack_rows(rows, elements, target_height=300, source_height=1000)

# Legacy (no source_height): today's exact edge-anchored behavior, for comparison.
legacy = stack_rows(rows, elements, target_height=300)
assert result != legacy, "a centered source row-stack must come back different from the legacy edge-anchored result"

min_top = min(result["a"]["top"], result["b"]["top"])
max_bottom = max(result["a"]["top"] + result["a"]["height"], result["b"]["top"] + result["b"]["height"])
leftover = 300 - (max_bottom - min_top)
assert min_top == leftover // 2, f"expected centered leftover split, got min_top={min_top}, leftover={leftover}"
print("Vertically-centered source row-stack -> centered result: OK")

# --- No source_height: unchanged legacy behavior (backward-compat regression guard) --
assert stack_rows(rows, elements, target_height=300) == legacy
print("No source_height -> unchanged legacy edge-anchored behavior: OK")

print("\nTASK 3: stack_rows centering -- ALL CHECKS PASSED")
