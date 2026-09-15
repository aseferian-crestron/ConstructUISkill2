import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typography import TYPE_SCALE

assert set(TYPE_SCALE) == {"title", "heading", "body", "label", "caption"}, TYPE_SCALE
# design doc §3's two explicit floors
assert TYPE_SCALE["body"] >= 22, TYPE_SCALE
assert TYPE_SCALE["label"] >= 18, TYPE_SCALE
# "the type scale increasing from there for headings" -- strictly ascending
order = ["caption", "label", "body", "heading", "title"]
sizes = [TYPE_SCALE[role] for role in order]
assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes), TYPE_SCALE
print(f"TYPE_SCALE: 5 roles, strictly ascending, respects both doc floors: {TYPE_SCALE}: OK")

print("Type scale: all assertions passed.")
