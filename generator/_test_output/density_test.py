import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from density import DENSITY_CEILINGS, check_density

# --- breakpoints are ascending, last one covers everything above it --------------------
diagonals = [d for d, _ in DENSITY_CEILINGS]
assert diagonals == sorted(diagonals), DENSITY_CEILINGS
assert diagonals[-1] == float("inf"), "the last breakpoint must cover every larger panel"
ceilings = [c for _, c in DENSITY_CEILINGS]
assert ceilings == sorted(ceilings), "a bigger panel must never have a LOWER ceiling"
print(f"DENSITY_CEILINGS: ascending diagonals, ascending ceilings, unbounded top: {DENSITY_CEILINGS}: OK")

# --- within the ceiling: no warning ------------------------------------------------------
assert check_density(5, 5.0) == []
assert check_density(8, 7.0) == [], "exactly at the ceiling must not warn"
print("check_density: component_count at or under the ceiling returns no warnings: OK")

# --- over the ceiling: one warning, names the actual count/ceiling/panel size ----------
warnings = check_density(10, 5.0)
assert len(warnings) == 1, warnings
assert "10" in warnings[0] and "8" in warnings[0] and "5.0" in warnings[0], warnings[0]
print(f"check_density: over the ceiling returns exactly one warning naming the real numbers: {warnings[0]}: OK")

# --- a bigger panel gets a higher ceiling for the SAME component count -----------------
assert check_density(10, 5.0) != [] and check_density(10, 15.0) == [], \
    "the same component count must be fine on a large panel even if it warns on a small one"
print("check_density: the same component count is judged against the panel's own size: OK")

# --- boundary: a panel just over a breakpoint uses the NEXT tier's ceiling -------------
just_under = check_density(9, 7.0)     # small tier ceiling is 8 -> warns
just_over = check_density(9, 7.01)     # medium tier ceiling is higher -> no warning
assert just_under != [] and just_over == [], (just_under, just_over)
print("check_density: crossing a breakpoint changes which ceiling applies: OK")

print("Density: all assertions passed.")
