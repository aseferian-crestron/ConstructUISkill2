# Home Panel — Bento Layout Spec

Implementation handoff for the residential control panel bento UI. Two workflows are supported, switchable via a tab control; both read from the same underlying room/subsystem state, just grouped differently. Sizing is **content-driven**, not hand-placed — see the sizing algorithm below.

A working HTML/CSS/JS reference implementation was prototyped and is described in full here so it can be ported into Construct data files. Adjust field/key names to match the actual Construct schema — the structure below is a proposal, not a fixed contract.

---

## 1. Two workflows

### A. Room view (`by-room`)
- One box per physical room.
- Each box lists that room's active subsystems: lights, climate, current source, shades.
- Default/landing view — matches how a person thinks about their house ("what's going on in the living room?").

### B. System view (`by-system`)
- One box per subsystem: Lighting, Climate, Shades, Audio & Source, Security.
- Each box lists the rooms/zones that subsystem currently touches, with per-zone values.
- Secondary/control-center view — for tasks like "turn off every light" or comparing thermostat zones across the house.

Both views render from the same state; only the grouping (by room vs. by subsystem) differs. The UI should expose a simple toggle (two-button switcher) between them, defaulting to `by-room`.

---

## 2. Data model

Proposed shape — one record per room, one per subsystem. Each room's subsystem entries and each subsystem's zone entries should be **omitted when not applicable** (e.g. a room with no audio source just has no `source` field) — the row count driven by present fields is what drives box sizing (see §4).

```jsonc
{
  "rooms": [
    {
      "id": "living-room",
      "name": "Living Room",
      "occupied": true,
      "subsystems": {
        "lights":  { "state": "on",  "level": 70 },              // level 0-100, omit if off/n-a
        "climate": { "mode": "cool", "setpoint_f": 71 },
        "source":  { "device": "Sonos", "label": "Living Rm" },
        "shades":  { "state": "half_open" }                       // open | half_open | closed
      }
    },
    {
      "id": "kitchen",
      "name": "Kitchen",
      "occupied": false,
      "subsystems": {
        "lights": { "state": "off" }
      }
    }
  ],

  "systems": [
    {
      "id": "lighting",
      "name": "Lighting",
      "summary": "3 of 6 rooms on",
      "zones": [
        { "room_id": "living-room", "state": "on", "level": 70 },
        { "room_id": "office",      "state": "on", "level": 90 },
        { "room_id": "patio",       "state": "on", "level": 100 }
      ],
      "idle_rooms": ["kitchen", "bedroom", "bathroom"]            // rendered as small pills, not full rows
    },
    {
      "id": "climate",
      "name": "Climate",
      "summary": "2 zones cooling · 1 heating",
      "zones": [
        { "room_id": "living-room", "setpoint_f": 71, "mode": "cool",    "note": null },
        { "room_id": "office",      "setpoint_f": 70, "mode": "cool",    "note": null },
        { "room_id": "bedroom",     "setpoint_f": 68, "mode": "heat",    "note": "scheduled 9pm" }
      ]
    },
    {
      "id": "shades",
      "name": "Shades",
      "summary": "2 open · 1 closed",
      "zones": [
        { "room_id": "living-room", "state": "half_open" },
        { "room_id": "office",      "state": "open" },
        { "room_id": "bedroom",     "state": "closed" }
      ]
    },
    {
      "id": "audio",
      "name": "Audio & Source",
      "summary": "Playing in 1 room",
      "zones": [
        { "room_id": "living-room", "device": "Sonos" },
        { "room_id": "office",      "device": "Apple TV" }
      ]
    },
    {
      "id": "security",
      "name": "Security",
      "summary": "Armed · Home",
      "zones": [
        { "label": "Front door", "state": "locked" },
        { "label": "Back door",  "state": "locked" },
        { "label": "Garage",     "state": "unlocked" }
      ]
    }
  ]
}
```

---

## 3. Box anatomy

Every box (room or system) shares the same chrome:

```
┌────────────────────────────┐
│ Title                  ● dot│  ← box-head: name + status dot (occupied/active)
│ Subtitle                    │     subtitle = occupancy or one-line summary
├────────────────────────────┤
│ label ............... value │  ← one row per present data point
│ label ............... value │     (room view: sys-row; system view: zone-row)
│ ...                          │
└────────────────────────────┘
```

- **Room box header**: room name, occupancy/status subtitle, a status dot (amber if occupied/active, dim gray if empty/idle).
- **System box header**: system name, one-line aggregate summary (e.g. "3 of 6 rooms on").
- **Row content**:
  - Room view: one row per active subsystem (lights, climate, source, shades) — icon + label on the left, value on the right.
  - System view: one row per zone the system touches — zone/room name on the left, its value on the right. Lighting and climate rows also render a thin progress bar under the row for level/percentage.
  - Idle/off rooms in a system box collapse into small pills at the bottom rather than full rows (see Lighting example — "Kitchen off", "Bedroom off").

## 4. Sizing algorithm (the important part)

Boxes are **not** given fixed widths or heights. Both dimensions come from how much data the box actually has to show:

1. **Height**: intrinsic. The box is a flex column with no forced min-height — it's exactly as tall as its header + however many rows it renders. An empty room (one row) is a short tile; a room running four subsystems is proportionally taller.
2. **Width**: computed from a weight equal to the number of visible rows in that box (minimum 1).
   ```
   weight = max(count_of_visible_rows, 1)
   flex-grow = weight
   flex-basis = 150 + weight * 90   // px
   ```
   The container is a `display: flex; flex-wrap: wrap` bento row (not a fixed CSS grid). Boxes with more rows both request more base width (`flex-basis`) and claim more of the leftover space (`flex-grow`), so they end up visibly larger without any manual placement.
3. Recompute weight/size whenever the underlying data changes (a device turns on/off, a row is added or removed) — sizing should always reflect current state, not a cached layout.
4. On narrow viewports (< ~640px), collapse every box to full width, one per row (drop the flex-grow/basis sizing, `flex-basis: 100%`).

This means the visual hierarchy (which rooms/systems look "bigger") is a direct, always-current readout of how much is going on in that space — not something a designer or Claude Code needs to re-tune by hand when the state changes.

## 5. Visual design tokens

Dark theme (primary), with a light-theme token swap.

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | `#12151a` | `#eef0f3` | page background |
| `--panel` | `#1c2128` | `#ffffff` | box background |
| `--panel-alt` | `#232933` | `#f5f6f8` | nested row / pill background |
| `--hairline` | `#333a45` | `#dde1e7` | borders, dividers |
| `--text` | `#edeff2` | `#171a1f` | primary text |
| `--text-muted` | `#8b93a1` | `#5b6472` | labels, subtitles |
| `--text-faint` | `#5c6472` | `#9098a3` | off/idle values |
| `--amber` | `#e8a33d` | same | **on / active** state (lights, active dot) |
| `--sky` | `#5fa8d3` | same | climate values |
| `--sage` | `#6fb88a` | same | locked / safely-closed / cooling states |

Color is functional, not decorative: amber always means "on/active," sky is reserved for climate readouts, sage means a secure/closed-safely state.

**Typography**: Manrope (400/500/600/700/800) for all UI labels and headings. JetBrains Mono for numeric/state readouts only (temperatures, percentages, lock states) — reserved for actual data values to give those a control-panel feel, not used for labels.

**Radii**: boxes `20px`, nested pills/rows `9px`. Gap between boxes: `14px`.

## 6. Interaction

- A pill-style two-button switcher (`By room` / `By system`) toggles which view is visible. Only one view renders at a time; switching is instant (no data refetch, both views read the same state).
- No other interactivity in the current mockup (it's a status display, not yet wired for control actions like tapping a row to toggle a light) — flag if Construct needs tap targets added per row for direct control.

## 7. Open questions for Construct implementation

- Confirm actual field names / schema Construct data files expect — §2 is a proposal to translate from, not a required shape.
- Confirm whether rows should be tappable to control devices directly, or if control happens elsewhere and this panel is read-only status.
- Confirm the room ↔ subsystem id mapping source (so `by-system` zones can resolve back to room display names).
- Confirm light/dark theme handling matches Construct's existing theming approach (this spec assumes CSS custom properties + `prefers-color-scheme`).
