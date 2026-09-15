import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from layout_patterns import choose_layout

# <=5 items -> Header-Content-Footer, the doc's own universal default, audience-neutral
assert choose_layout(3, is_commercial=True, panel_is_landscape=True) == "header-content-footer"
assert choose_layout(5, is_commercial=False, panel_is_landscape=True) == "header-content-footer"
print("choose_layout: <=5 items picks header-content-footer (the safe default), any audience: OK")

# 6-7 items, landscape: commercial -> Tabbed, residential -> Card-Based (design doc §1:
# "Tabbed and Card-Based... skew commercial" / "a list of rooms/areas" reads residential)
assert choose_layout(7, is_commercial=True, panel_is_landscape=True) == "tabbed"
assert choose_layout(7, is_commercial=False, panel_is_landscape=True) == "card-based"
print("choose_layout: 6-7 items landscape splits by audience (commercial=tabbed, residential=card-based): OK")

# 6-7 items, portrait -> Tabbed needs landscape width; Card-Based regardless of audience
assert choose_layout(6, is_commercial=True, panel_is_landscape=False) == "card-based"
assert choose_layout(6, is_commercial=False, panel_is_landscape=False) == "card-based"
print("choose_layout: 6-7 items portrait falls back to card-based for either audience: OK")

# >7 items, landscape -> Left-Side Menu, audience-neutral (the doc doesn't tie it to one)
assert choose_layout(10, is_commercial=True, panel_is_landscape=True) == "left-side-menu"
assert choose_layout(10, is_commercial=False, panel_is_landscape=True) == "left-side-menu"
print("choose_layout: >7 items landscape picks left-side-menu, any audience: OK")

# >7 items, portrait -> Left-Side Menu needs landscape width; falls back to card-based
assert choose_layout(10, is_commercial=True, panel_is_landscape=False) == "card-based"
print("choose_layout: >7 items portrait falls back to card-based: OK")

print("Choose layout: all assertions passed.")
