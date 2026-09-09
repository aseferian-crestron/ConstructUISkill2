# Multi-resolution reflow

Source-grounded confirmations for `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`.

## Portrait media-query formula (previously unconfirmed project-wide)

Confirmed by reading `C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor\PageDesigner\PageDesigner.Server\JS\src\pd-utils\src\breakpoint.ts`'s `createRawQuery(devOrientation, devWidth, devHeight)` -- the real client-side TypeScript source that generates these breakpoints (same file/method family as the already-confirmed landscape formula).
Cross-checked against two real portrait sample files elsewhere in the CCIDE repo
(`CrestronConstruct_RIDE\Solutions\MySolution\SolutionCCIDE5225\Bug_CCIDE_5225_Widget2.cuiw` and `...Widget5.cuiw`, both a 1024x1322 portrait resolution) -- source and samples agree exactly:

```
(orientation: portrait) and (max-height: {H+1}px) and (max-width: {W+1}px), (orientation: portrait) and (max-height: {H-1}px)
```

Same `+-1px` shape as the already-confirmed landscape formula, just with height leading
(and being the sole clause in the second alternative) instead of width -- `createRawQuery` branches on orientation only to decide which dimension leads, not on any other logic.
`generator/layout.py::orientation_media_query` implements both branches;
`landscape_media_query` is now a thin wrapper for backward compatibility.
