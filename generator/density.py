"""
Design-system information density (ConstructUISkill_DesignSystem.md §7) -- an
advisory/validation layer, not a file-format writer: nothing here touches a
.cuip/.cuig/.cuiw file, so there is no Construct source-grounding needed (same
class of pure policy as spacing.py/palette.py's derived-state deltas).

"One dominant action per screen" and control grouping (§7's other two rules) are
deliberately NOT modeled here as standalone functions -- they are decisions a
layout-pattern builder makes while placing components (e.g. Bento Box's largest
card), not a property checkable after the fact from a bare count. Their real shape
gets decided when Phase 7 (Layout Patterns) starts, not guessed at here (YAGNI --
same precedent as palette.py's module docstring rejecting a premature generic
mechanism in favor of one verified case at a time).
"""
from __future__ import annotations

#: (max_diagonal_in, max_components) breakpoints, ascending by diagonal AND by
#: ceiling -- a panel's diagonal uses the first breakpoint it fits under. "Rule of
#: thumb ceiling... appropriate to the panel's physical size and viewing distance"
#: (design doc §7) -- a judgment call, not a Construct spec. Breakpoints correspond
#: to real market segments: small in-wall (TSW-570/770-class), medium (TSW-1070-
#: class), large tabletop/lobby panels (unbounded top tier).
DENSITY_CEILINGS: list[tuple[float, int]] = [
    (7.0, 8),
    (10.0, 12),
    (float("inf"), 20),
]


def _ceiling_for(panel_diagonal_in: float) -> int:
    for max_diagonal, max_components in DENSITY_CEILINGS:
        if panel_diagonal_in <= max_diagonal:
            return max_components
    return DENSITY_CEILINGS[-1][1]  # unreachable given the inf breakpoint, kept as a safe fallback


def check_density(component_count: int, panel_diagonal_in: float) -> list[str]:
    """Warnings only -- never raises, never writes. Empty list means
    `component_count` is within the density ceiling for a panel this size."""
    ceiling = _ceiling_for(panel_diagonal_in)
    if component_count > ceiling:
        return [
            f"{component_count} components exceeds the density ceiling of {ceiling} "
            f"for a {panel_diagonal_in}\" panel -- consider fewer, larger controls or "
            f"splitting across pages (design doc §7)"
        ]
    return []
