"""
Construct data-file comparison/round-trip harness.

Phase 1 deliverable (see docs/architecture/00-overview.md and the project plan):
prove that our section-header splitter locates the exact same section boundaries
Construct's own DAOs use, by round-tripping known-good files byte-for-byte.

Section format, confirmed against C:\\Git\\CCIDE source (UiEditorProjectDao.cs /
UiEditorPageDao.cs / UiEditorAssetDao.cs):

  .cuip  -> {FileMetadata} {DeviceResolutionSource} {ProjectAttributes}   (fixed order)
  .cuig  -> {FileMetadata} {Html} {Css} {PageAttributes}                  (fixed order)
  .cuiw  -> same as .cuig (same DAO/model, distinguished only by extension)
  .cuia  -> {FileMetadata} {AssetAttributes}                              (fixed order)

Every known-good sample file observed so far has each header alone on its own line
(e.g. a line that is exactly "{Html}" with nothing else). This splitter assumes that
convention rather than Construct's own more permissive LocateNextHeader/IsValidHeader
regex scan (which additionally guards against a header-looking line appearing inside
raw Html/Css content). ASSUMPTION, not yet stress-tested against an adversarial file --
revisit if a real project ever has literal "{Word}"-only lines inside its Html/Css.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Fixed section order per file type, per the DAOs cited above.
SECTION_ORDER = {
    ".cuip": ["FileMetadata", "DeviceResolutionSource", "ProjectAttributes"],
    ".cuig": ["FileMetadata", "Html", "Css", "PageAttributes"],
    ".cuiw": ["FileMetadata", "Html", "Css", "PageAttributes"],
    ".cuia": ["FileMetadata", "AssetAttributes"],
}

HEADER_LINE_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)


@dataclass
class ParsedFile:
    path: Path
    ext: str
    # ordered list of (header_name, header_line_text, content_text)
    sections: list[tuple[str, str, str]] = field(default_factory=list)
    preamble: str = ""  # anything before the first header (expected empty)

    def reassemble(self) -> str:
        return self.preamble + "".join(header + content for _, header, content in self.sections)


def split_sections(raw: str, ext: str) -> ParsedFile | None:
    """Split raw file text into (header, content) pairs by locating header-only lines."""
    expected = SECTION_ORDER.get(ext)
    if expected is None:
        return None

    matches = list(HEADER_LINE_RE.finditer(raw))
    if not matches:
        return None  # legacy-format file, out of scope for this harness for now

    preamble = raw[: matches[0].start()]
    sections: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        name = m.group(1)
        header_text = m.group(0)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        content = raw[start:end]
        sections.append((name, header_text, content))

    return ParsedFile(path=Path(""), ext=ext, sections=sections, preamble=preamble)


def parse_file(path: Path) -> ParsedFile:
    raw = path.read_text(encoding="utf-8")
    parsed = split_sections(raw, path.suffix.lower())
    if parsed is None:
        raise ValueError(f"{path}: no recognized section headers found (legacy format, or unknown extension)")
    parsed.path = path
    return parsed


def round_trip_check(path: Path) -> bool:
    """Read a known-good file, reassemble it from parsed sections, and byte-diff."""
    raw = path.read_text(encoding="utf-8")
    parsed = parse_file(path)
    rebuilt = parsed.reassemble()

    expected_order = SECTION_ORDER[path.suffix.lower()]
    found_order = [name for name, _, _ in parsed.sections]

    print(f"\n=== {path.name} ===")
    print(f"  sections found : {found_order}")
    print(f"  expected order : {expected_order}")
    order_ok = found_order == expected_order
    print(f"  order matches expected DAO order: {order_ok}")

    if raw == rebuilt:
        print(f"  ROUND-TRIP: OK ({len(raw)} chars, byte-identical)")
        return order_ok
    else:
        print("  ROUND-TRIP: MISMATCH")
        # locate first divergence
        n = min(len(raw), len(rebuilt))
        i = 0
        while i < n and raw[i] == rebuilt[i]:
            i += 1
        print(f"  first divergence at char {i}")
        print(f"  original  context: {raw[max(0, i - 40):i + 40]!r}")
        print(f"  rebuilt   context: {rebuilt[max(0, i - 40):i + 40]!r}")
        return False


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: compare.py <file1> [file2 ...]")
        return 2
    all_ok = True
    for arg in argv:
        p = Path(arg)
        try:
            ok = round_trip_check(p)
        except ValueError as e:
            print(f"\n=== {p.name} ===\n  SKIPPED: {e}")
            ok = False
        all_ok = all_ok and ok
    print("\n" + ("ALL ROUND-TRIPS OK" if all_ok else "ROUND-TRIP FAILURES PRESENT"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
