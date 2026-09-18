"""
Concrete sizing/radii/font/color/interaction-state constants transcribed
directly from docs/ConstructUISkill_Tabbed-Layout-Styleguide.md (1280x800
target viewport) -- the companion doc a separate Claude AI session built
2026-09-17 after the Boardroom Tabbed spec shipped with structure but no real
numbers, which had left every dimension in layout_patterns.py/modal.py/
camera_control.py a locally-invented judgment call instead of the
stakeholder-reviewed mockup's own measurements.

Only the LIGHT theme color column is wired here -- this project's Tabbed
Commercial work has targeted light theme throughout (SPLASH_BACKGROUND_COLOR
and friends in layout_patterns.py predate this module and were already light-
theme hex values pulled from the reviewed PDF); the styleguide doc's dark-
theme column is left for whenever a dark-theme pass is actually scoped.

Values with no direct doc citation (line noted per group below) are this
module's own judgment call to make an already-real number usable as a layout
input (e.g. a text element needs a box HEIGHT, but the doc only gives a font-
size and "line box" description) -- same "judgment call, not a Construct
spec" discipline every other constants module in this project already
follows (spacing.py, shape.py, typography.py).

This module intentionally does NOT define a dark-theme variant, a Residential
variant beyond what the doc marks shared, or the full per-component
Normal/Pressed/Selected table (styleguide §6) -- that table is genuinely
per-component behavior (a filled button's selected state doesn't exist at
all; a tile's selected state is a fill+border+icon change; a tab's is a
border only), not a set of reusable constants, so it's applied directly at
each call site in layout_patterns.py/camera_control.py instead of centralized
here.
"""
from __future__ import annotations

# --- §1 Design tokens (color) -- LIGHT theme column only ----------------------------
BACKGROUND = "#eef0f3"
SURFACE = "#ffffff"
SURFACE_ALT = "#f5f6f8"
DIVIDER = "#dde1e7"
TEXT_PRIMARY = "#171a1f"
TEXT_MUTED = "#5b6472"
TEXT_FAINT = "#9098a3"
ACCENT_AMBER = "#e8a33d"
ACCENT_AMBER_DIM = "#fbe8c9"
ACCENT_SKY = "#5fa8d3"
ACCENT_SKY_DIM = "#dcedf7"
ACCENT_SAGE = "#6fb88a"
ACCENT_SAGE_DIM = "#dcf0e3"
ACCENT_CORAL = "#d97757"
ACCENT_CORAL_DIM = "#fbe0d5"

# --- §2 Header ------------------------------------------------------------------------
HEADER_HEIGHT_WITH_TABS = 99  # Boardroom
HEADER_HEIGHT_NO_TABS = 62  # Residential
IDENTITY_ROW_PADDING_TOP = 14
IDENTITY_ROW_PADDING_X = 20
IDENTITY_ROW_PADDING_BOTTOM = 10
IDENTITY_ROW_GAP_BOARDROOM = 16
ROOM_NAME_FONT_SIZE = 16
ROOM_NAME_LINE_HEIGHT = 18  # "~18px line box" (§2)
DATETIME_FONT_SIZE = 11.5
DATETIME_LINE_HEIGHT = 14  # judgment call: a reasonable box for an 11.5px line, not in the doc
STATUS_DOT_SIZE = 9
STATUS_DOT_HALO = 4

TAB_ROW_HEIGHT = 40
TAB_ROW_PADDING_X = 16
TAB_GAP = 4
TAB_LABEL_FONT_SIZE = 13.76
TAB_ICON_SIZE = 16
TAB_SELECTED_UNDERLINE_WIDTH = 2

LOGO_SIZE = 26
LOGO_RADIUS = 7  # not applied: ch5-image corner-radius stylability is unconfirmed, see shape.py

# --- §3 Center content area -----------------------------------------------------------
CONTENT_PADDING = 20
CONTENT_MAX_WIDTH = 760
CARD_RADIUS = 16
CARD_PADDING = 16
SLIDER_TRACK_HEIGHT = 8
SLIDER_TRACK_RADIUS = 4
SLIDER_HANDLE_SIZE = 16

# --- §4 Footer --------------------------------------------------------------------------
FOOTER_HEIGHT = 62  # both panels
FOOTER_PADDING_Y = 12
FOOTER_PADDING_X = 20
FOOTER_NAV_BUTTON_HEIGHT = 37
FOOTER_NAV_BUTTON_RADIUS = 999
FOOTER_NAV_BUTTON_PADDING_X = 14  # the PILL's own internal padding -- distinct from FOOTER_PADDING_X (the footer row's outer edge padding)
FOOTER_NAV_LABEL_FONT_SIZE = 12.8
FOOTER_ICON_BUTTON_SIZE = 37  # Privacy Mute / Volume Mute, circular
VOLUME_CONTROL_WIDTH = 220
VOLUME_TRACK_WIDTH = 148
VOLUME_TRACK_HEIGHT = 6
VOLUME_TRACK_RADIUS = 3
VOLUME_HANDLE_SIZE = 14

# --- §5 Buttons/tiles/controls used inside modals --------------------------------------
BTN_GROUP_HEIGHT = 37  # Raise/Stop/Lower, Zoom In/Out
BTN_GROUP_RADIUS = 10
BTN_GROUP_FONT_SIZE = 13.12
TILE_WIDTH = 193  # measured 3-up row width
TILE_HEIGHT = 49
TILE_RADIUS = 14
TILE_FONT_SIZE = 13.33
ROUND_BUTTON_BOARDROOM = 56  # in-call actions (camera/mute/end-call)
PTZ_BUTTON_SIZE = 52
PTZ_BUTTON_RADIUS = 14  # rounded square, distinct from circular call-action buttons
TOGGLE_TRACK_WIDTH = 42
TOGGLE_TRACK_HEIGHT = 24
TOGGLE_KNOB_SIZE = 18
MODAL_CLOSE_SIZE = 32
MODAL_MAX_WIDTH = 640
MODAL_MAX_HEIGHT_VH_FRACTION = 0.82
MODAL_RADIUS = 22
MODAL_PADDING_TOP = 18
MODAL_PADDING_X = 20
MODAL_PADDING_BOTTOM = 26
CONFIRM_BUTTON_HEIGHT = 44
CONFIRM_BUTTON_RADIUS = 12
CONFIRM_BUTTON_FONT_SIZE = 14.4

# --- §6 Interaction states --------------------------------------------------------------
#: "pressed = an 8% black (dark theme: 8% white) overlay" (§6) -- this project's
#: derive_states can't apply a real opacity overlay (Stage 1 only exposes flat
#: color custom properties, not layered compositing), so it uses the doc's own
#: named fallback instead: "a discrete color swap using the same 'darken 8%'
#: values ... as fixed colors rather than a computed overlay."
PRESSED_DARKEN_FRACTION = 0.08
