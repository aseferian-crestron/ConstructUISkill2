# Boardroom Panel — Tabbed Layout Spec

Implementation handoff for the boardroom control panel's tabbed shell — a different navigation pattern from the bento panel covered in the earlier Boardroom Panel (Bento) spec. Where the bento spec describes an at-a-glance status grid, this spec describes an interactive control surface: a splash landing screen, a persistent header with tab navigation, per-tab center content, a persistent footer utility bar, and three modal overlays reachable from that footer.

**This spec is intentionally framework-agnostic.** An HTML/CSS mockup was used to review the design with the stakeholder; that markup is not the implementation target. Everything below describes required structure and behavior — component selection (which CH5 components satisfy each requirement) is left to whoever implements this against the real CH5 component library and Construct data-file format.

This panel shares its visual design system (colors, type, the coral "live/urgent" accent) with the residential and boardroom bento panels — see those specs for the full token table. Anything not restated here should be assumed identical.

## Generic Specifications
While the below specification defines actual controls and dialogs, the tabbed layout is generic that should follow this pattern:

### Splash Page
This layout will always have a splash page that can support "What do you want to do" with selections like "Presentation", "Enter Video Call", "Enter Audio Call", "Audio-Only" .. the user should be asked if they want anything on the Splash page.

### Header
Header should support two rows. The top row is the room name on the left with the date/time directly underneath the room name.

The bottom row can contain systems modes is the user specifies: System Power (always included by default), Presentation, Video Call, Audio Call

The company logo should span both rows and be anchored to the right side of the header.

### Footer
The footer will contain sub-system controls. I.E. Environment (Lights, Shades, HVAC), Security, Cameras, Audio. It can also contain Privacy Mute and room volume.

The controls will always open a full screen modal dialog.

### Center Content
The center content area will show controls based on the system mode selected.

---

## 1. Screen inventory

| Screen | Type | Reached from |
|---|---|---|
| Splash | Full-screen landing | App wake / idle timeout |
| Power | Tab (confirmation only) | Header tab |
| Video Call | Tab | Header tab, or Splash → "Join Video Call" |
| Audio Call | Tab | Header tab, or Splash → "Join Audio Call" |
| Environment | Modal | Footer → "Environment", or Splash → "Start Presentation" |
| Audio (mic levels) | Modal | Footer → "Audio" |
| Camera | Modal | Footer → "Camera" |

The header and footer are **persistent chrome**: visible on every tab, not part of any individual tab's content. Modals overlay whatever tab is currently showing underneath and don't change which tab is active.

---

## 2. Splash screen

- Full-screen, shown before the main panel — the room's landing state, not one of the tabs.
- Content: room name (small, above the headline), a large headline reading **"What would you like to do?"**, and a small set of large action tiles (currently three: Start Presentation, Join Video Call, Join Audio Call).
- Each tile is a direct shortcut into the main panel: Join Video Call → Video Call tab, Join Audio Call → Audio Call tab, Start Presentation → opens the Environment modal directly (since starting a presentation is really "set the room up," not a tab of its own).
- Tapping any tile transitions away from Splash into the main panel (header + tabs + footer) with the relevant destination already active.

## 3. Header

- Room identity line: room name plus a live status indicator (e.g. "In call · 24 min") reflecting current call state — same status concept as the boardroom bento panel's header dot.
- Tab bar directly below: **Power, Video Call, Audio Call**. Exactly one tab active at a time; switching tabs swaps the center content only — header and footer stay fixed.
- Lighting and shades are deliberately **not** tabs — they live in the Environment modal instead (see §5). Don't reintroduce them as tabs.

## 4. Tabs (center content)

### Power
The entire tab is a single confirmation, not a dashboard:
- A short question: **"Shutdown System?"**
- One line of consequence text (what shutting down actually powers off — display, audio, connected devices).
- Two actions: **Yes** (destructive — proceeds with shutdown) and **No** (dismisses, no action). No other controls belong on this tab.

### Video Call
- Live call status: platform, participant count, elapsed time, current screen-share source.
- A small set of in-call actions: toggle camera, toggle mic mute, end call. These should be visually distinct from ordinary settings controls — this is the "something is happening right now" surface, so lean on the coral accent here same as the bento panel's call state.
- When idle (no call), this tab should show a clear idle state rather than empty controls — e.g. "No active video call" plus a way to start one, mirroring how Audio Call's idle state works today.

### Audio Call
- When idle: status text ("No active audio call") plus a dial pad for placing a call.
- When in a call: status line plus an end-call action. (A live audio call sharing screen space with a dial pad doesn't make sense — show one or the other based on state, not both.)

## 5. Modals (Environment, Audio, Camera)

All three share one interaction pattern — implement this once as a reusable modal/overlay requirement, not three separate ones:

- Presented as a **centered, modal overlay** over whatever tab is currently active — not a bottom sheet, not a new tab, not a full navigation away from the current screen.
- A title identifying the modal (Environment / Audio / Camera) and an explicit close control.
- Also dismissible by tapping outside the modal's content area (the backdrop).
- Opening one of these modals does not change which header tab is active underneath.

### Environment modal
Groups **lights and shades together** — this was previously two separate tabs and has been deliberately merged into one modal with two sections:
- **Lights**: per-zone level controls (e.g. Front Wall, Table, Perimeter), each showing a current percentage and adjustable level. A few quick-level presets (Full / Dim / Off) below the zone list.
- **Shades**: per-zone position controls (e.g. Window Wall, Side Wall), each with Raise / Stop / Lower actions and a current-position label.

### Audio modal
Per-microphone controls for **5 microphones** (currently: Podium, Table Mic 1–4). Each mic gets its own row with:
- A level control (current level, adjustable).
- An individual mute toggle, visually distinct (coral) when muted, with the level label switching to something like "Muted" instead of a percentage while muted.
This is a different concern from the footer's Privacy Mute and volume Mute — those are room-wide; this modal is per-microphone control for someone who needs to balance individual mics.

### Camera modal
Three sections:
- **Presets**: a small single-select set (Wide / Speaker Track / Presenter) — only one active at a time.
- **Position**: a directional pad (up / down / left / right, plus a center "home/reset" control) for pan/tilt, and separate Zoom In / Zoom Out actions.
- **Power**: a single on/off toggle for the camera itself.

## 6. Footer (persistent utility bar)

Three-part layout, present and identical on every tab:

- **Left**: navigation buttons that open the three modals — **Environment**, **Audio**, **Camera** — in that order. These are navigation actions, not stateful toggles; they don't themselves carry an on/off visual state.
- **Center**: **Privacy Mute** — a single stateful toggle (visually distinct when active) that mutes camera/mic for privacy. This is deliberately centered for prominence/easy reach, separate from the per-microphone controls in the Audio modal.
- **Right**: a **volume control** (current level, adjustable) paired with a dedicated **Mute** button — a stateful toggle distinct from Privacy Mute. Volume mute silences room audio output; Privacy Mute affects the room's outgoing call presence (mic/camera). Keep these two mute concepts visually and functionally separate even though both live in the footer.

## 7. Visual design intent

Reuses the shared token set from the bento specs in full (background/surface/text roles, amber = on/active, sky = reserved for climate/comfort if ever reintroduced, sage = secure/safe state, coral = live/urgent/call-related). No new tokens are needed for this layout — the same coral used for an active call in the bento panel should be reused here for: the header's live-call status indicator, in-call action emphasis on the Video Call tab, and the muted state on individual Audio-modal mics and the footer's mute toggles.

Typography, radii, and card/surface treatment should match the bento panels as well — the intent is that someone moving between the bento overview and this tabbed control surface reads them as one product, not two.

## 8. Open questions for the CH5/Construct implementation

- Which CH5 components best satisfy: (a) a top-aligned tab bar bound to a content-swap region, (b) a centered modal/overlay with backdrop-dismiss, (c) a directional pad control (PTZ), (d) a per-row slider-plus-toggle combination (mic rows, light zones), (e) a single-select tile group (camera presets, quick light levels).
- Confirm the idle/active state logic for Video Call and Audio Call tabs — is this driven purely by call-platform signals, or does Construct need a combined "any call active" signal to drive the header's live-status indicator too?
- Confirm real device/zone counts and names (mic count, light zone count, shade zone count, camera preset list) — the 5 mics, 3 light zones, 2 shade zones, and 3 camera presets here are the stakeholder-reviewed placeholders, not confirmed final counts.
- Confirm what "Shutdown System" actually powers off at the device level, so the Power tab's consequence text and the Yes action's actual signal list match reality.
- Confirm whether Privacy Mute and the footer volume Mute should have any interaction with each other (e.g. does Privacy Mute also imply volume mute, or are they fully independent).
- Confirm whether the Splash screen's action set should be data-driven (varies by room capability) or is a fixed three-tile set for every room of this type.
