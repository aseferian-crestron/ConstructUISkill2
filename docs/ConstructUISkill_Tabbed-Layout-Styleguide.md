# Construct UI — Component Styleguide (1280×800 target viewport)

This is the shared sizing and interaction-state reference for both tabbed panels (Boardroom and Residential). It exists because the two layout specs were written without concrete default styling — no dimensions, radii, font sizes, or button states — which left too much for whoever implements this to guess. Both tabbed specs should be read together with this document; where a tabbed spec's own "visual design" section gives a number, this document is the source it should match.

**All pixel values below were measured directly from the reviewed mockups rendered at exactly 1280×800**, not estimated. If the CH5 target viewport ends up being a different resolution, these values need to be re-derived (most are expressed as either fixed px or rem-equivalent font sizes, so scaling rules should be agreed before assuming they hold at another resolution).

Base font stack: one primary UI typeface (Manrope in the mockups) at a 16px root size; a monospaced face reserved only for numeric/state readouts (temperatures, percentages, timers, lock states). If CH5 can't cleanly apply per-element font family, drop the monospace distinction and use the primary typeface everywhere rather than approximating it.

---

## 1. Design tokens (color)

| Role | Dark | Light | Use |
|---|---|---|---|
| Background | `#12151a` | `#eef0f3` | page/screen background |
| Surface (card/panel) | `#1c2128` | `#ffffff` | card, modal sheet, dropdown menu background |
| Surface — alt/nested | `#232933` | `#f5f6f8` | row/chip/track background inside a surface |
| Surface — raised | `#282f39` | `#ffffff` | selected segment inside a switcher (e.g. active dropdown item hover) |
| Divider | `#333a45` | `#dde1e7` | borders, hairlines |
| Text — primary | `#edeff2` | `#171a1f` | titles, values |
| Text — muted | `#8b93a1` | `#5b6472` | labels, subtitles |
| Text — faint | `#5c6472` | `#9098a3` | off/idle/disabled-leaning text |
| Accent — amber | `#e8a33d` | same | on/active state (lights, active dot, primary transport action) |
| Accent — amber, dim | `#4a3a24` | `#fbe8c9` | amber accent's own tinted background (e.g. active tile fill) |
| Accent — sky | `#5fa8d3` | same | climate/comfort readouts |
| Accent — sky, dim | `#23394a` | `#dcedf7` | sky accent's tinted background |
| Accent — sage | `#6fb88a` | same | secure/safe/closed-safely state (locks, shades closed) |
| Accent — sage, dim | `#253a2e` | `#dcf0e3` | sage accent's tinted background |
| Accent — coral | `#d97757` | same | live/urgent/in-progress state (active call, shutdown action, muted mic) |
| Accent — coral, dim | `#4a2c22` | `#fbe0d5` | coral accent's tinted background |

A token's "dim" variant is that token's own color desaturated into a background fill — e.g. an amber-active tile uses amber-dim as its background and full amber as its text/icon/border, never a different hue.

---

## 2. Header

| Property | Value |
|---|---|
| Full header height — **with** a tab row (Boardroom) | **99px** |
| Full header height — **no** tab row (Residential) | **62px** |
| Identity/controls row height (both) | **~60px** (58–61px measured) |
| Row padding | `14px 20px 10px` |
| Row internal gap | `16px` (Boardroom) / `14px` (Residential) |
| Border | 1px solid divider, bottom edge only |

**Room name**: 16px, weight 800, single line, ~18px line box.
**Date/time**: 11.5px (0.72rem), text-faint, monospace, sits directly under the room name with no gap beyond normal line spacing.
**Status dot** (Boardroom's live/occupied indicator next to room name): 9×9px circle, plus a 4px "halo" ring in the dot's dim color (i.e. total visual footprint ~17×17px).

**Tab row** (Boardroom only — Residential has no tabs, which is exactly why its header is 37px shorter):
- Row height: **40px**, padding `0 16px`, gap between tabs `4px`.
- Each tab: auto width (content + padding), **40px tall**, padding `10px 16px 12px`, label 13.76px (0.86rem) weight 600, icon 16×16px.
- Active tab: 2px solid amber underline on the bottom edge only; inactive tabs have a transparent 2px bottom border (reserve the space so text doesn't shift on selection).

**Header-right cluster** (logo, status text, dropdowns, weather, status icons — whichever apply to that panel): all vertically centered in the identity row, `14–16px` gaps between sibling elements.
- Logo mark (Boardroom): 26×26px, radius **7px**, 12.8px weight 800 centered monogram.
- Logo wordmark: 13.12px weight 700.
- Status text (Boardroom, e.g. "In call · 24 min"): 12.48px, text-muted.
- Weather block (Residential): 13.12px weight 600, icon 18×18px, 6px gap between icon and text.
- Status icon (Residential — Heating/Lights/Shades glance icons): **30×30px** circle, 15×15px icon centered, colored per token (heat→sky, lights→amber, shades→sage) using that token's dim shade as the circle fill and full token as the icon color.
- Power icon button (Residential, left of room name): 37×37px circle — see §5 for the icon-button spec this follows.

**Dropdowns** (Residential's Source and Room selectors — same component used for both):
- Trigger button: height **33px**, radius **999px** (full pill), padding `8px 13px`, gap `7px` between icon/label/chevron, label 13.12px weight 600.
- Menu panel: radius **12px**, padding `6px`, min-width ~180px, surface-raised background, 1px divider border, drop shadow.
- Menu item: height **33px**, radius **8px** (so it insets cleanly inside the 6px menu padding), padding `9px 10px`, label 13.44px weight 600. Selected item shows a trailing checkmark in amber and amber text color — see §6 for how selected differs from pressed here.

---

## 3. Center content area

| Property | Value |
|---|---|
| Outer padding | `20px` on all sides |
| Max content width | `760px`, centered (both panels) |
| Section title | 12.48px (0.78rem), weight 700, uppercase, `0.04em` letter-spacing, text-muted; `12px` gap below before content, `26px` gap above when a second section follows the first |
| Card (surface container) | radius **16px**, padding `16px`, 1px divider border |
| Card internal row ("zone" — a light/shade/etc. control row) | padding `14px 0`, ~62px tall including its slider |
| Slider track | height **8px**, radius **4px**; handle is a 16×16px circle, white fill, 2px colored border matching the active value's token |

---

## 4. Footer

| Property | Value |
|---|---|
| Footer height (both panels) | **62px** |
| Padding | `12px 20px` |
| Border | 1px solid divider, top edge only |
| Layout | three flex sections (left / center / right), each `flex: 1`; left content start-aligned, center content centered, right content end-aligned. Residential has no center-section content (Privacy Mute was Boardroom-only and was not carried over) — leave that section empty rather than re-centering left/right into two columns, so both panels' footers share one layout rule. |

**Footer nav button** (opens a modal — Environment/Audio/Camera on Boardroom; Lights/Shades/Security/Cameras/HVAC on Residential): pill shape, height **36–37px**, radius **999px**, padding `9px 14px`, gap `8px` between icon and label, icon 16×16px, label 12.8px weight 600.

**Footer icon-only button** (volume Mute, Privacy Mute): 37×37px circle, radius 50%, icon 17×17px centered.

**Volume control**: total width **220px**, `10px` gap between icon/track/label. Track: width **148px**, height **6px**, radius **3px**; handle 14×14px circle matching the slider handle spec in §3 but in the sky accent (volume's designated color).

---

## 5. Buttons, tiles, and controls used inside modals

| Component | Size | Radius | Font |
|---|---|---|---|
| `btn-group` button (Raise/Stop/Lower, Zoom In/Out) | height **37px**, flexes to fill its row | **10px** | 13.12px weight 600 |
| Tile (scene/preset/quick-level, single-select grid) | min width ~130px, measured **193×49px** in a 3-up row | **14px** | 13.33px |
| Round button (transport controls, PTZ nudge, HVAC stepper) | **52×52px** (Residential transport/stepper/PTZ) or **56×56px** (Boardroom's larger in-call actions: camera/mute/end-call) | 50% (circle) | icon-only, 20×20px icon |
| PTZ direction button (Boardroom camera pad) | **52×52px** | **14px** (rounded square, not circular — distinguishes navigation from the call-action round buttons) | icon-only |
| Toggle switch (device power, door lock) | **42×24px** track, **18×18px** knob | **999px** (track), 50% (knob) | — |
| Modal close button | **32×32px** circle | 50% | 16×16px icon |
| Modal sheet | max-width **640px**, max-height 82vh, radius **22px**, padding `18px 20px 26px` | **22px** | — |
| Confirmation action button (Boardroom Yes/No) | height **44px**, min-width 120px | **12px** | 14.4px weight 700, padding `13px 22px` |
| Stacked power-option button (Residential's three-option list) | height **46px**, full width up to 300px | **12px** | 14.72px weight 700, padding `14px 20px` |
| Now-playing / camera-preview art frame | **64×64px** | **14px** | icon-only placeholder |

---

## 6. Interaction states: Normal, Pressed, Selected

Every interactive control in both panels needs all three states defined — not just a hover. These are distinct concepts and shouldn't be collapsed into one:

- **Normal** — the control's resting appearance, as sized and colored elsewhere in this document.
- **Pressed** — a momentary state while the control is actively being touched/clicked, which reverts the instant contact ends. It communicates "this registered your touch," independent of whether the action changes anything persistent.
- **Selected** — a persistent state that remains after release, because the control now represents the current value/choice/on-off status (an active tab, a toggled-on switch, the currently-chosen tile in a single-select grid, the currently-chosen dropdown item). Selected can itself be pressed (a selected tile still needs a pressed feedback when tapped again), so the two are independent, stackable states, not alternatives.

Default rule, applied consistently across every button/tile/switch/tab type: **pressed = an 8% black (dark theme: 8% white) overlay on top of whatever the control's current background is**, applied instantly with no transition delay on press and released with a ~100ms ease-out on release. This is the same state-layer approach used across most current design systems (an opacity overlay rather than a hue shift), and it composes correctly with Selected automatically — a selected+pressed tile is its selected color with the same 8% overlay on top, no special-cased combination needed.

Per-component specifics:

| Component | Normal | Pressed | Selected |
|---|---|---|---|
| Footer nav button / tab / dropdown trigger | surface-alt background, divider border, muted text | +8% overlay on current background | *(tabs only)* amber bottom border + full-opacity text; footer nav buttons and dropdown triggers have no persistent selected state — they're momentary navigation, not a choice |
| Tile (single-select grid) | surface background, divider border, muted icon | +8% overlay | amber border + amber-dim fill + amber icon/text (this is the state already defined as `.active` in the mockups) |
| Toggle switch | surface-alt track, faint knob | +8% overlay on the track | token-dim track + full token knob position/color (amber for device power, sage for a locked door — match the token to what the switch represents, not a single fixed "on" color) |
| Filled action button (confirmation Yes, Shutdown, primary call action) | solid token color (usually coral) | darken the fill 8% *toward black* rather than overlay-white, since it's already a saturated fill and a light overlay would wash it out; for a coral fill this reads as roughly `#c2684a` | filled buttons in this UI are momentary actions, not toggles — they don't have a selected state |
| Outlined/secondary button (Cancel, No) | surface-alt background, divider border, primary text | +8% overlay | none |
| Dropdown menu item | transparent background, primary text | surface-alt background (the item's own hover/press fill, not a generic overlay, since it's a list row) | amber text + trailing checkmark, background stays transparent so the checkmark alone carries the selected meaning |
| Round button (transport/PTZ/stepper) | surface-alt background, divider border | +8% overlay | *(transport's primary/play button only)* solid amber fill instead of surface-alt — this is a permanent style difference marking it as the primary action in the group, not a press state |

If CH5 exposes native pressed/selected states for its button components (most touch-panel toolkits do), map this table onto those native states directly rather than re-implementing the overlay technique from scratch — the visual target is what matters, not the mechanism. If CH5 has no equivalent to a transient opacity-overlay press state, the fallback is a discrete color swap using the same "darken 8%" values given above as fixed colors rather than a computed overlay.

---

## 7. What's intentionally not specified here

- Animation/transition timing beyond the ~100ms press-release mentioned above (modal open/close, tab-switch fade) — the mockups use a simple 200–250ms ease fade, but this wasn't treated as a hard requirement and can follow whatever CH5's own transition conventions are.
- Exact spacing values for every one-off layout (e.g. the splash screen's tile gap) not called out above — infer from the 8/10/14/16/20px rhythm already established rather than introducing new arbitrary values.
- Any value for a viewport other than 1280×800. If Construct needs this to scale to other panel resolutions, that's a separate design pass, not an extrapolation from these numbers.
