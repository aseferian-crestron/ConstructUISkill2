# ConstructUISkill2 — Status

This file reflects current status in realtime. It is updated in the same turn as any
work it describes — never batched for later. Newest entries at the top of the Log.

See `docs/ConstructUISkill.md` for the feature spec and
`docs/architecture/` for the source-grounded architecture documentation this project is
built on (see **Approach** below).

## Current phase

**Phase 8 (fonts), global swap slice -- BUILT, applied to the live project, AWAITING
THE USER'S CHECK IN CONSTRUCT.** Scoped with the user to global font-swap only; webfont
IMPORT deferred since no project anywhere on this machine has ever done it, so there is
no real file to verify a `webfonts/` folder's shape against.

`generator/fonts.py::set_project_font(cuip_path, new_font)` rewrites, in one call: the
`.cuip`'s `DefaultFontFamily`, and every `ccid_ActiveFont` attribute + Construct-generated
`font-family` CSS declaration in every `.cuig`/`.cuiw` beside it. Grounded in
`FontUpgradeHelper.cs` (Construct's own font-writing code) and its four literal CSS
selector shapes in `FontSupportConstants` (`UiEditor.Server\Constants.cs:262`), all four
confirmed byte-for-byte against the reference project.

**Verification found two real bugs before the code ever reached a live file, because the
test ran against a COPY of the actual GenTestProject2 harness project rather than a
synthetic fixture** -- the first time in this project a test has used the real live
project as its own oracle rather than the separate `C:\Solutions\ClaudeSamplesComponents` sample:

1. **Attribute-name casing.** Construct's own Html view lowercases attribute names on
   save (`ccid_activefont`); the mirrored PageAttributes TOML preserves the authored
   casing (`ccid_ActiveFont`) -- confirmed with zero exceptions across 12 reference
   files. The first version of the regex was case-sensitive and silently missed every
   Html-view mention on any file that had been through a real Construct save
   (`ComplexContracts.cuig`, built from transplanted real components). Now
   case-insensitive on the key, preserving whichever casing is actually present.
2. **`font-family` quote style.** `layout.py` always writes double quotes with a space;
   `ReflowTest.cuig` -- a real, long-lived file, not something this session wrote fresh
   -- carries single quotes with no space in 21 places. Both are valid CSS and Construct
   evidently accepts either. Now matches `['"]`, preserving whichever quote character was
   actually used rather than normalizing it.

**A related finding, deliberately NOT acted on in this phase:** the generator's own Html
output writes attribute names in their original camelCase (`ccid_ActiveFont`), never
lowercased the way a real Construct save does. This appears functionally harmless (HTML
attribute names are case-insensitive to parsers) and is unconfirmed either way -- flagged
here rather than fixed, since rewriting HTML-casing behavior across every component
builder is a cross-cutting change well outside this phase's scope, and would touch
Phase 4's already user-confirmed-live button code.

Applied to the live `GenTestProject2` (Roboto -> Montserrat; backup taken in the session
scratchpad first). Verified independently before this was written: no file mentions
Roboto anymore, every file still round-trips section-for-section, `.cuip` reads
`DefaultFontFamily = "Montserrat"`. Full 44-file suite green.

**Awaiting the live check:** open `GenTestProject2` in Construct and confirm the project
now shows Montserrat (or its own system fallback, if Montserrat is not installed) rather
than Roboto.

**CONFIRMED IN CONSTRUCT 2026-09-11: all six component pages look good.** Every
component type the generator can build -- 21 types, 38 nested children -- renders
correctly at the size its selection adorner shows. Component generation (flat and
container) is complete and live-verified.

Getting here took four rounds of the user finding sizing bugs by eye, and the reason is
recorded in **Approach** above rather than buried here: the attribute diff against the
reference ran on every test run, the CSS diff did not exist, and prose directives in
this README did not prevent me from shipping without it. `component_css_shape_test.py`
closes that gap and found four more mismatches the moment it was written. The rule is
now mechanical: an automated comparison must cover the dimension that changed before
generated output goes to the user.

**What the sizing model ended up being**, all from published SDK data rather than
inference:

| source | what it decides |
|---|---|
| `defaults.style` | the drop size, and which dimensions a type states -- including the literal `auto` |
| `canResize` | types that cannot be sized at all (animation, segmented/signal gauges) |
| `supportedSizeFormat` | the aspect-locked class (`widthOnly`, `containerWidthOnly`, `handleWidthOnly`, ...) |
| `classToVariableMapping` "idSelector" | the CSS custom properties a component RENDERS from, with its swaptarget/ignore conditions |

Plus two facts no data expresses: `size="custom"` (a Construct mode absent from the
schema's own enum) is what makes an explicit size take effect, and a dpad is locked 1:1
so a non-square request is squared.

**Known limitation, not a bug:** for `height: auto` components the rendered height is
unknowable to the generator, so the showcase packer reserves a 120px guess. Nothing
collided in practice here, but a taller-than-guessed component would overlap what is
below it on a generated page.

Full 43-file suite green.

**`showtickvalues` resolved -- after I first misread the instruction.** "I don't need
you to generate a slider with ticks" means the attribute IS present and turned off, not
that the attribute is dropped. My first pass removed it entirely. The schema default is
`"false"`, so simply emitting it gives exactly what was asked: attribute there, ticks
off. A generated slider is back to 22 attributes with `showtickvalues="false"`.

The reference instance carries no such attribute, so this stays a recorded delta -- but
a deliberate one with a reason, no longer the "unexplained, possibly a defect" it was
listed as before.

**Next / open threads:** (1) themes (7), fonts (8), languages (10), hard buttons (11);
(2) the skill layer; (3) offered but not built -- a `Stop` hook that runs the suite so
the diffs cannot be skipped regardless of what I remember.

**Deferred by the user, not forgotten:** `FALLBACK_MIN_SIZE_PX = 35` gets validated when
we start building live projects, where real pages at real resolutions will exercise it.

**The CSS was never diffed against the reference -- that is why every sizing bug reached
the user.** They asked why they were being sent pages to check when they had supplied a
sample, and they were right: this project's own Approach section says an automated diff
runs before any manual testing in Construct. The attribute diff did. Nothing diffed CSS.

`component_css_shape_test.py` now compares, for all 21 types, which of width/height the
generated rule states and whether each is a pixel value or the literal `auto`, against
the reference instances. **It found four more mismatches immediately** -- including
inside the fix shipped minutes earlier:

- `ch5-keypad`, `ch5-textinput`, `ch5-video`: the reference states `height: auto`. I had
  "fixed" them by OMITTING height, which is not the same thing.
- `ch5-wifi-signal-level-gauge`: the reference states `width: auto; height: auto`; we
  stated nothing.

**And the root cause of the 816px widget list was upstream of all of it.** The showcase
took each type's size from a reference INSTANCE, which has been resized and configured.
`component-context.json`'s `defaults.style` is the drop size and was there all along:
a widget list drops at `200px / auto`, a button list at `510x68`, a slider at `300x30`,
a media player at `800x600`, a toggle at `100px` wide with no height. `defaults.style`
now drives both the emitted shape and the showcase's sizes, outranking the reference.

Two further published fields replaced things I had been inferring: `canResize` (already
in use) and `supportedSizeFormat` (`widthOnly`, `containerWidthOnly`, `widthOnlyNoSize`,
`handleWidthOnly`), which names the aspect-locked class directly.

Full 43-file suite green; all six pages regenerated and their CSS verified against the
reference before this was written.

**Showcase components are FRESH, unconfigured instances again.** The user asked why the
widget list arrived with a widget reference already assigned: it should be added empty.
They are right, and it defeated the purpose -- the question these pages answer is
whether a newly CREATED component matches a newly DROPPED one, and a pre-configured
instance cannot answer it. The override (a widget reference and 3 items, added while
chasing the wrong diagnosis) is gone, and `OVERRIDES` is now deliberately empty with
that reasoning recorded in the file so it is not "helpfully" repopulated later.

The widget list is once again `widgetid=""`, `numberofitems=1`, positioned with no
explicit size -- which is the actual fix, and is independent of whether a widget is
assigned.

`widget_reference_id()` stays in component.py: the `w{GUID}` convention is verified
against the reference project and any real widget list will need it. It is simply not
something the showcase should apply.

**One operational note:** a write to `AllComponents - Media 2.cuig` failed with
`PermissionError` while Construct had it open, so the regeneration silently left that
page stale until retried. Worth remembering when a regenerated page appears not to have
changed -- and worth handling in the harness if this recurs.

Full 42-file suite green; all six pages regenerated.

**Confirmed good in Construct:** Buttons, Keypads, Gauges, Media. **Pending re-check:**
Media 2 and Text.

**Widget list corrected -- and my diagnosis of it was wrong.** I attributed its wrong
size to an empty `widgetid` (nothing referenced, so nothing rendered inside the box).
The user disproved that directly: dropping an EMPTY widget list in Construct gives
something "much smaller than yours", so the initial size was wrong before any widget was
assigned. The empty widgetid was real but beside the point.

The actual cause is the same family as the gauges: a widget list's rendered size is the
widget it references multiplied by its item count -- a small placeholder when it
references nothing -- so it is CONTENT-sized and no explicit box belongs in its CSS.

`CONTENT_SIZED_TAGS` is **transcribed, not derived**, and the code says so: `canResize`
is True for it, and its componentProperties differ from `ch5-button-list`'s only in ways
too incidental to hang a rule on. `ch5-button-list` is the control -- same "no
render-size variables" bucket, but it does lay out to its box and is confirmed good in
Construct -- so the test asserts both behaviours side by side to keep the distinction
honest.

`widget_reference_id()` stays (the `w{GUID}` convention is real and the showcase's list
still points at the project's widget), but its docstring now records that an empty one
is legitimate and was not the bug.

**Sizing rules now, all four:** `canResize: False` or content-sized -> no box;
aspect-locked -> width only; aspect-locked at 1:1 (dpad) -> both, squaring a non-square
request; everything else -> both.

Full 42-file suite green; showcase regenerated.

**Confirmed good in Construct:** Buttons, Keypads, Gauges, Media. **Pending re-check:**
Media 2 (video, video switcher, widget list) and Text (text input).

**Sizing resolved as a CLASS, plus a separate widget-list cause.** The user checked the
remaining pages: Media good; Media 2 wrong on the video switcher, the video and the
widget list. The first two turned out to be the keypad's problem again, and the third a
different problem entirely.

**The class.** Video, video switcher, keypad, toggle and text input are all
ASPECT-LOCKED -- their render-size variables are sourced from a single axis, so height
follows width and an explicit height is a guess. Having had three independent reports
of the same class, the per-type flags are gone and `writes_css_size()` derives it:

1. `canResize: False` (animation, the three gauges) -> no width, no height.
2. Aspect-locked -> width only.
3. Aspect-locked at 1:1 (the dpad) -> both, with a non-square request squared.
4. Everything else -> both.

That derivation reproduces every outcome already confirmed good in Construct (button,
slider, media player, button list, tab button, dpad, the gauges) and fixes the two
reported. **ch5-textinput is fixed by the same rule without waiting for a fourth
report** -- it is in the class, and its variable is preset-named
(`--ch5-textinput--small-width`), which made it suspect already.

**The widget list was NOT a sizing bug.** Its `widgetid` was empty, so it referenced no
widget and rendered nothing inside a box that still sized the adorner. `widgetid` is the
widget's `Id` GUID with a literal "w" in front -- confirmed in the reference, where
`WidgetListReference.cuiw` (`eb72224e-...`) is referenced as `web72224e-...`, the same
`w{GUID}` convention a ch5-template uses for `templateid`. The generator still allows an
empty one (Construct creates them that way, you pick the widget afterwards), but
`widget_reference_id()` builds the reference and the showcase now points its widget list
at the project's own MyWidget with 3 items.

Full 42-file suite green; showcase regenerated.

**Confirmed good in Construct:** Buttons, Keypads, Gauges, Media. **Pending re-check:**
Media 2 (video, video switcher, widget list) and Text (text input, changed by the class
rule above).

**Sizing, third correction: aspect-locked types.** The user found the adorner mismatch
on the keypad while the dpad looked right. Both are aspect-locked -- their rendered size
is driven by a SINGLE axis, which `reflow.py::_is_aspect_locked` already had a test for
-- so their height follows their width and an explicit one is a guess. The dpad only
looked right because the showcase happened to hand it a square; a non-square request
would have rendered a square component inside a rectangular adorner.

- A **keypad** now writes width and no height, like the toggle.
- A **dpad** squares a non-square request: every real instance is square (118x118,
  221x221) and Construct never lets its box go otherwise. reflow.py does the same when
  fitting one to a new resolution.
- Fixed-size detection now reads `componentProperties.canResize`, the SDK's own
  published flag, instead of inferring it from an empty render-size mapping. It names
  exactly the four the user identified (animation, segmented, signal level, wifi) --
  same answer, from the authority rather than a proxy.

**Confirmed good in Construct so far:** Buttons, Keypads (dpad), Gauges. Keypad pending
re-check after this fix.

**The three aspect-locked types not yet looked at are the likely next reports**, since
they are the same class as the keypad: `ch5-textinput`, `ch5-video`, `ch5-video-switcher`
all currently get an explicit height. They were left alone deliberately -- their
reference instances DO carry a height and nothing has shown them broken, so changing
them on suspicion risks breaking what works. `ch5-textinput` is the most suspect: its
render-size variable is `--ch5-textinput--small-width`, preset-named unlike every other
type's, and its reference instance uses `size="small"` with no variable at all.

Full 42-file suite green; showcase regenerated.

**Sizing corrected again, this time for the fixed-size types.** The user checked the
Gauges page and found the same adorner mismatch on the segmented, signal-level and wifi
gauges, adding the fact that settles it: **"signal level and wifi only support fixed
sizes"**.

The first fix over-applied. It set `size="custom"` on every type with a preset `size`
attribute, but a component can only be CSS-resized if the SDK gives it render-size
variables to drive -- and those three have an EMPTY `propertyMapping`. They lay
themselves out from their own attributes (`numberofsegments`, `numberofbars`, the
preset), so `size="custom"` set a preset that does not exist and the explicit
width/height sized an adorner around a component that ignored it. The reference agrees:
the segmented and signal gauges carry **no width or height in CSS at all**.

**The rule is now two conditions, both from SDK data:** a type is custom-sized only if
it has a preset `size` attribute AND `size_css_vars()` yields variables. Everything else
keeps its preset and is positioned without a CSS box (`css_width`/`css_height` on the
profile). That also caught a second over-reach on the way: `ch5-color-chip` HAS
render-size variables but no `size` attribute, so the first version invented one no real
instance carries.

Result: 12 custom-sizable types carry their variables; 9 fixed-size types keep their
preset. The three gauges are positioned and never given a size.

**Both of these were fixes to a fix**, and the pattern is worth naming: the reference
diff cannot see either bug, because the reference instances were never resized, so their
CSS says nothing about what happens when we DO size one. Rendering is the only oracle
for that, which is why the user's screenshots found what 42 green tests did not.

Showcase pages regenerated. Full 42-file suite green.

**Still to check in Construct:** the remaining showcase pages (Text, Media, Media 2) --
Buttons and Keypads already confirmed good.

**Adorner-vs-render size mismatch FIXED -- a regression I introduced, on a bug that had
already been fixed once.** The user opened the showcase pages and found the selection
adorner larger than the component on a toggle and a button, and said this was fixed
before. It was: Phase 4 hit exactly this on ch5-button.

**Why it came back.** A CH5 component does not lay itself out from the plain
`width`/`height` on its `#id` rule -- those size the canvas ADORNER. Its own rendering
reads CSS custom properties, and it only honours an explicit size when `size="custom"`.
`ch5_button.py` does both. `component.py`'s generic `build_component` did neither: it
called `build_position_css` without `extra_vars`, and never overrode `size`. That broke
every type -- including ch5-button, whose ATTRIBUTES delegate to the confirmed builder
but whose CSS came from the generic path. Carrying a fix across a generalisation is
exactly what a reference diff cannot check, because the reference instances were never
resized either.

**The fix is per-type SDK data, not a table.** `size_css_vars()` reads
`component-context.json`'s `classToVariableMapping` "idSelector" entry: a toggle maps
width -> `--ch5-toggle--handle-size-regular`, a dpad -> `--ch5-dpad--regular-size`, a
keypad -> `--ch5-keypad--regular-container-width`, a button width AND height. Both
condition kinds in that data are honoured -- `swaptarget` (a vertical button's width
drives the HEIGHT variable) and `ignore` (a horizontal slider ignores its height
mapping). `size="custom"` is now set for every type with a preset-enum size attribute;
notably "custom" is NOT in the schema's own enum, it is a Construct-level mode, which is
why it cannot be derived and had to come from the real files.

**A toggle also writes no explicit height** (`ComponentProfile.css_height=False`). Its
height follows its handle size, its reference instance carries width only, and an
explicit height is itself an adorner-too-tall bug -- which is what the user's screenshot
showed.

**One earlier note was wrong and is corrected:** the toggle's `size="custom"` had been
recorded as "the user resized this instance". It is not instance state -- it is required
for any explicitly-sized component, which is precisely the bug.

`component_size_vars_test.py` pins all of it, including that the variables appear in
BOTH @media blocks. Showcase pages regenerated. Full 42-file suite green.

**Still awaiting the live check** of the six `AllComponents - *` pages in Construct.

**Showcase pages generated for every component type -- AWAITING THE USER'S CHECK IN
CONSTRUCT.** `harness/build_component_showcase.py` writes six pages into
`GenTestProject2`, carrying all 21 profiled types built entirely by
`generator/component.py`:

| page | components |
|---|---|
| AllComponents - Buttons | tab button, button list, toggle, button (13 nested children) |
| AllComponents - Keypads | keypad, dpad (18 nested children) |
| AllComponents - Gauges | segmented, signal level, wifi signal level, slider |
| AllComponents - Text | colour picker, text input, qrcode, text, datetime, colour chip |
| AllComponents - Media | media player (800x600, fills its page) |
| AllComponents - Media 2 | widget list, video switcher, video, animation (7 children) |

Sizes are taken from each type's reference instance rather than invented, so components
appear at realistic proportions; layout is a shelf pack into the primary 1280x800 that
spills to another page when a row will not fit.

Verified on disk before handing over: every page round-trips byte-identically, all 21
types present, every component inside the 1280x800 panel, zero overlaps, all 38 nested
children written, and the `.cuip` marked stale (by `write_cuig` itself now).

**This is the check the reference diff cannot make.** Matching a Construct-authored
file's attributes is not the same as Construct rendering the result -- the contract work
already showed live checking catching what static diffing does not.

**One more parser bug found while doing it**, same family as the spaced-CSS one: a real
page carries `width:auto` on a component never given an explicit size, and
`parse_position_rules` called `int()` on it and raised -- aborting the parse of EVERY
element in that page, not just the one rule. A non-numeric length now means "not
stated", which is the meaning a missing width already had; a rule with no numeric
POSITION is skipped entirely. Full 41-file suite green.

**Next / open threads:** (1) the live check of these pages; (2) the `showtickvalues`
slider delta, the one difference from the reference not explainable as instance state;
(3) `FALLBACK_MIN_SIZE_PX = 35` validation; (4) themes (7), fonts (8), languages (10),
hard buttons (11); (5) the skill layer.

**Container component types DONE -- every CH5 component type the reference project
contains now generates, parents and nested children alike.** Together with the flat
slice, `generator/component.py` covers all 20 profiled types.

**Where the child definitions come from, and it is two different places:**
- **Counts are SDK data.** A button list's `numberofitems` (10), a tab button's
  `numberofitems` (3), a video switcher's `numberofsources` (5) and `numberofscreens`
  (2) -- each read off the parent's own attributes, and each matching its reference
  instance's child count exactly.
- **The dpad's and keypad's fixed sets are NOT in the SDK.** They are hardcoded in
  `pd-metadata-resolver\MetaDataResolver.ts:103-135`, which pushes literal child tags:
  five dpad buttons (up/down/left/right with `fa-caret-*` icons, centre with none) and
  thirteen keypad buttons (1-9 with their letter groups, 0/+, star, hash, and
  `buttonextra` carrying `fas fa-phone`). Transcribed into `DPAD_KEYS`/`KEYPAD_KEYS`
  with the source cited; the test asserts the shapes still match.

`ch5-subpage-reference-list` turned out NOT to be a container: its only child in the
reference is a textnode, so it builds flat.

**Two defects the reference diff caught**, both of which would have shipped silently:
- **Booleans were written as Python `True`.** `component-context.json` holds real JSON
  booleans for some defaults (`ch5-subpage-reference-list`'s `centeritems`), and `str()`
  turns those into `"True"` -- not what the file or CH5 want. Now normalised.
- **`disabled` was being emitted as a default.** The reference settles it by
  contradiction: the dpad and signal gauge have it, the video switcher does not. It
  records what the user set in the properties panel, so a fresh component never carries
  it (`NEVER_EMIT`).

**`component_container_types_test.py` checks children, not just parents** -- count, each
child's attribute keys, and each child's values. A dpad with four buttons, or a keypad
whose `buttonstar` had the wrong label, would look plausible and behave wrong, so the
count assertion explains what a mismatch means (we read the wrong parent attribute). It
also asserts children reach the Html view and that generated child ids are unique.

Recorded deltas are instance state again, and the notes are self-checking: the keypad's
first TEN children match exactly, while star/hash/extra carry an `id` and an empty
`labelminor` that MetaDataResolver never writes -- Construct assigns those once a child
has been touched.

Full 41-file suite green.

**Next:** the remaining `showtickvalues` slider question (the one delta not explainable
as instance state), `FALLBACK_MIN_SIZE_PX = 35` validation, themes (7), fonts (8),
languages (10), hard buttons (11), and the skill layer. Worth considering soon: nothing
generated by `component.py` has been opened in Construct yet -- the reference diff is a
strong oracle but it is not the same as Construct rendering it.

**Component builders: all 15 flat types now reproduce their reference instance --
key-for-key and value-for-value.** The source read resolved both open questions, and
both answers were things no amount of further inference would have reached.

**1. The sync block is not general.** `ccid_sync_*` was being generated for any tag with
sass-schema sectors, which is 21 of them -- producing 72 attributes on a datetime whose
real instance has 17. In the entire reference project **only `ch5-button` carries a
single sync attribute**. Theme mode is not the gate (a theme-mode button still has 78 of
them); `setSyncData` lives in `commonButtonTraitsMixins`, the button family's own mixin.
`SYNC_TAGS = ("ch5-button",)`, and the test asserts the generator and the reference agree
about which types carry sync, in both directions.

**2. `defaults.attributes` and the trait defaults are BOTH written, not either/or.** The
base layer short-circuited to the context's `defaults.attributes` whenever a tag declared
them. That is exactly backwards for the affected types: a slider declares 10 context
defaults and STILL gets `min`/`max`/`step` from the trait pass, a signal gauge gets
`numberofbars`/`value`. Merging the two sources (context defaults first, winning on
value) took the exact-match count from 3/15 to 15/15.

Two supporting source findings, both from `MetaDataResolver.ts`: `supportsAttribute`
builds a tag's trait set from its own `attributeProperties` UNION `global`'s -- the same
own-then-global pattern the contract lookup needed -- and `:214-229` overrides some
defaults in code rather than reading schema.json (a slider's `min`/`max`/`step` are null
in the schema, hardcoded there).

**`ch5-button` delegates to `ch5_button.py`** rather than going through the generic path:
it already has a builder confirmed attribute-for-attribute in Phase 4, including the
icon/image/checkbox variants the generic path knows nothing about.

**`component_flat_types_test.py` diffs every type against the reference on every run** --
keys and 256 attribute values -- rather than restating expectations by hand. Differences
are recorded per type with a reason and are themselves checked: a recorded delta that
stops being true fails the test, so the notes cannot rot. The recorded ones are
user-typed content (a qrcode's text, a toggle's labels), state flags Construct sets when
the user acts (`demoMode`, `ccid_customSizeSet`, chosen sizes), and the universal `oldID`
-- which every reference instance has because it records a duplicated component's
previous id, and a fresh component has none.

**One suspected defect, recorded not hidden:** we emit `showtickvalues` on a slider from
its non-null schema default and the reference slider does not carry it. The slider mixin
is the likeliest place it is dropped. It is the single delta here that is not explainable
as instance state.

Full 40-file suite green.

**Next:** container types -- ch5-dpad, ch5-keypad, ch5-button-list, ch5-tab-button,
ch5-video-switcher, ch5-subpage-reference-list -- which need a nested-child builder
(`ch5-dpad-button`, `ch5-keypad-button`, individual buttons, sources/screens). They
currently raise `NotImplementedError` rather than emit a childless shell that would look
right and behave wrong. Then: `FALLBACK_MIN_SIZE_PX = 35` validation, themes (7), fonts
(8), languages (10), hard buttons (11), and the skill layer.

**Component builders: pipeline built, layer 1 NOT yet correct -- WIP, do not use.**
`generator/component.py` generalises Phase 4's button into `build_component(sdk, tag,
...)` for the flat (childless) types. Four of its five layers are right; the base
attribute layer reproduces only 3 of 15 types exactly and is the open work.

**What is solid:**
- The layer structure generalises, which was the design bet. Measuring every reference
  component against the button's layers showed the unexplained attributes were almost
  entirely the same common-wiring keys the button hardcoded.
- `PROFILES`: the per-type wiring facts, transcribed from the reference project because
  they are NOT derivable from the SDK -- `ccid_ComponentType` is "Formatted-Text" for
  `ch5-text`, "Widget List" for `ch5-subpage-reference-list`, "Signal Gauge" for
  `ch5-signal-level-gauge`, and which types carry `ccid_ActiveFont`/`ccid_Label` varies.
- Container types raise `NotImplementedError` rather than emitting a childless shell
  that would look right and behave wrong (that is the next slice regardless).
- **`oldID` is correctly NOT emitted**: every reference instance has one, but it is an
  artifact of the user duplicating components, not something a fresh component carries.
- Two source findings: `MetaDataResolver.ts::supportsAttribute` builds a tag's trait set
  from its own `attributeProperties` UNION `global`'s -- the same own-then-global pattern
  the contract lookup needed -- and `MetaDataResolver.ts:214-229` OVERRIDES some defaults
  in code rather than reading schema.json (a slider's `min`/`max`/`step`, which are null
  in the schema). Both are now in the code.

**What is wrong:** the base layer currently short-circuits to
`component-context.json`'s `defaults.attributes` when a tag declares them, and
trait-filters the schema otherwise. Against the reference: `ch5-color-picker`,
`ch5-textinput` and `ch5-video` match exactly; the rest are off. Under-produces on the
slider (no `min`/`max`/`step` -- the short-circuit skips the override path), the signal
and wifi gauges (`numberofbars`, `value`, `minvalue`, `maxvalue`), the toggle
(`labelon`/`labeloff`), the qrcode and datetime. Over-produces `ccid_sync_*` on
`ch5-datetime`, `ch5-text`, `ch5-qrcode` and `ch5-color-chip` -- the sass-schema sectors
are being applied to types whose real instances carry none of them.

**Next step, and it is source work not inference:** read `MetaDataResolver.ts`'s trait
loop properly -- how `defaults.attributes` and the trait set combine (they are clearly
not either/or), and what gates the sync-attribute block per type. Three iterations of
inferring the rule from samples each matched some types and broke others, which is the
signal to stop guessing and read the code.

Full 39-file suite green (component.py has no tests yet -- deliberately, since nothing
about it should be treated as confirmed).

**Writing a page or widget now marks its project's contract stale automatically -- a
real gap the user found by asking the right question.** They noticed Construct gave no
"contract has been updated" toast when the button list's new signal was added, and asked
whether we set the flag for EVERY contract-relevant change (components added or removed,
signals, etc.). Two separate answers came out of checking:

**1. The change did take effect.** `GenTestProject2.cuic` was rewritten 0.4s after the
page write, and `ItemSelected` is present in the generated
`output/.../ComplexContracts/ButtonListTheme.g.cs`. So the missing toast did not mean a
missed update. Worth knowing WHY there was no toast: the notification comes from
`PersistenceHelper.cs:646` (`SaveContract`), on Construct's own in-app save path.
`ContractGenerationBehavior` -- which sets the flag and schedules generation -- is driven
by `SaveProjectCmd`/`ProjectItemUpdatedCmd`, i.e. edits made INSIDE Construct. Our
file-level edits reach it only via the file watcher, and the exact conditions under which
the toast is or is not raised on that path were not traced. **Unverified; do not treat
the toast as the signal that a generated change landed -- check the .cuic timestamp and
the generated output instead.**

**2. The audit found a genuine hole.** `write_cuig` -- the function behind creating a
page, creating a widget, adding a component, and enabling a signal -- never touched the
`.cuip`. Every correct case so far was a caller remembering by hand (both ad-hoc scripts
did it explicitly); nothing enforced it, and a forgotten one ships a project whose
contract does not match its pages, with no symptom until someone opens the Contract
Editor.

`write_cuig` now marks the `.cuip` beside the file it wrote
(`contracts.py::mark_project_stale_for`), deriving the project from the folder rather
than taking it as a parameter -- an optional "also mark the project" argument is exactly
what gets forgotten. Every write marks, including a rewrite: nothing in the written file
distinguishes a renamed component from a no-op, and over-marking costs one regeneration
on next open while under-marking is silent corruption. `mark_project_stale=False` opts
out. A page written where no `.cuip` sits (most of the test suite) is not an error; two
`.cuip`s in one folder raises rather than guessing.

That guard also caught a pre-existing test bug: `reflow_task10_integration_test`'s
"project with no pages" was sitting in the same folder as another project's pages, so
`add_resolutions_to_project` had been globbing those pages -- it was not testing the
zero-page case it claimed to. Given its own folder.

Full 38-file suite green.

**Coverage of the flag now:** new project (`build_project_attributes` defaults it true),
resolutions added (`add_resolutions_to_project`), any page/widget write (`write_cuig`),
and directly via `mark_contract_stale(cuip)`. Component/signal/rename changes all reach
disk through `write_cuig`, so they are covered by construction rather than by discipline.
**Deleting** a page or widget is the one contract-relevant change with no generator path
at all yet -- when one is added it must mark the project too.

**Complex-component contracts VERIFIED IN CONSTRUCT 2026-09-10, with one addition.** The
user checked the generated contract in the actual program: dpad, keypad, tab button and
media player all came out right, so the complex components' own contract strategies DO
honour what the file says -- the open question from the last two entries is closed. The
button list needed one more signal, **"Button Selected"**, which they had missed when
setting up the sample; added to `DEFAULT_SIGNALS` and the page regenerated.

**That signal is only sayable by its DISPLAY name**, which forced a better lookup.
`pd-buttonreceivestateselected` contracts as "ItemSelected" -- a name it shares with
`pd-receivestateselectedbutton` ("List Item Selected") -- so the contract name cannot
pick it out. Names now resolve in three layers: raw attribute, then contract name, then
the name Construct's UI displays. Two layers rather than one merged index, because each
resolves collisions the other has: the button list's and the video switcher's duplicates
are distinguished only by display name, while `ch5-color-chip`'s send/receive halves BOTH
display as "Red Value" and are distinguished only by contract name ("Red Value" vs
"RedValue_fb"). Only `ch5-spinner` is still genuinely ambiguous -- identical in both
layers -- and still raises.

**`REFERENCE_GAPS` records the one place we now deviate from the sample** (the button
list's Button Selected) with the reason. The defaults test still holds every other type
to the reference exactly, and will fail telling us to drop the entry once the sample
catches up.

**Correction earlier in this exchange, user-caught:** the first version of the
verification page also wrote a synthetic non-default signal (`pd-receivestateenable`)
onto all five components as a probe for whether a strategy honours the file. The user saw
"Enable" enabled everywhere and asked where it came from. It was unnecessary as well as
wrong -- an overriding strategy shows up as the contract having more or fewer signals
than the reference specifies, no invented signal required -- and it made the page stop
matching the ground truth it exists to check. Removed; the script now asserts the page
carries exactly the intended set.

Verified on disk after regenerating: TOML `[Elements.Attributes]` and the Html view agree
signal-for-signal on all five components, page round-trips byte-identically, everything
inside the 1280x800 primary, `.cuip` marked stale. Full 37-file suite green.

**Phase 6 (contracts) is complete** -- simple and complex components both confirmed live.
**Next / open threads:** (1) `layout.py::parse_position_rules` only matches compact CSS --
`parse_position_rules("#it8l { left: 124px; ... }")` returns `{}`, so reflowing a
Construct-authored page in the spaced format (as `Component-Widgets-Media Player.cuig`
is) would silently do nothing, no error; verified directly, unfixed; (2) whether
`FALLBACK_MIN_SIZE_PX = 35` holds across more pages and resolutions; (3) the remaining
generator phases -- themes (7), fonts (8), languages (10), hard buttons (11), and the
skill layer; (4) real builders for the complex component types, which is what would let
us stop transplanting.

**Complex-component contracts verified on the canvas; contract listing still to check.** Only the simple path (ch5-button) had ever been opened in Construct,
while dpad, keypad, button list, tab button and media player each go through their own
contract strategy, some of which force signals on regardless of the file
(`DpadStrategy.cs:91`, `KeypadStrategy.cs:94`). We have no generator builders for those
types yet, so the user chose the transplant route: copy each component's
element/html/css out of the reference project and let OUR `contracts.py` write the
signals.

`harness/transplant_reference_components.py` builds
`GenTestProject2/ComplexContracts.cuig` from five reference components and marks the
project stale. Each carries **exactly** the signals the user set on it in the reference
project -- dpad and keypad `Digital Start`, button list `ItemPress`, tab button `_Press`
+ `_Selected`, media player its seven -- so the page is a faithful restatement of their
spec and Construct's contract can be compared against it directly.

**Correction, user-caught:** the first version of this page ALSO wrote a synthetic
non-default signal (`pd-receivestateenable`) onto all five, as a probe for whether a
complex strategy honours the file. The user saw "Enable" enabled everywhere and rightly
asked where it came from. It was unnecessary as well as wrong: a strategy that overrides
the file shows up as the contract having MORE or FEWER signals than the reference
specifies, which needs no invented signal to detect -- and the invented one made the page
stop matching the ground truth it exists to check. Removed; the script now asserts the
page carries exactly the reference's signal set and nothing beyond it.

Verified on disk: page round-trips byte-identically, all 5 elements present, each
component's signals match the reference project exactly in BOTH the TOML
`[Elements.Attributes]` and the Html view, positions present, all inside the 1280x800
primary, no element-id collides with another page, `.cuip` reads `ContractIsStale =
"true"`.

**Also found while using the API for real:** `signal_map`'s friendly-name keys had been
lower-cased by the ambiguity refactor, so `"Enable" in signal_map(...)` was false for
every component. Fixed and pinned. And the reference files are not uniformly formatted --
most are compact CSS, `Component-Widgets-Media Player.cuig` is spaced -- which the
transplant tolerates but reflow does not (see open threads).

**Next / open threads:** (1) **the live check** -- open `GenTestProject2` and compare the
`ComplexContracts` contract against the reference project's signals for those five types;
(2) **`layout.py::parse_position_rules` only matches compact CSS** --
`parse_position_rules("#it8l { left: 124px; ... }")` returns `{}`, so reflowing a
Construct-authored page written in the spaced format would silently do nothing, no error
(verified directly; unfixed, it is reflow rather than contract work); (3) whether
`FALLBACK_MIN_SIZE_PX = 35` holds across more pages and resolutions; (4) the remaining
generator phases -- themes (7), fonts (8), languages (10), hard buttons (11), and the
skill layer; (5) real builders for the complex component types, which is what would let
us stop transplanting.

**Phase 6 corrected against the user's updated reference project — DONE.** The user
confirmed live that Construct generates Press and Selected for the buttons, then went
further and set the intended contract signals on EVERY component in
`C:\Solutions\ClaudeSamples\Components`, noting that some types need none. Checking our
discovery against that ground truth immediately found **two defects in what had just
shipped** — both of which had passed a green suite, because the suite only tested the
model against itself:

1. **Only the component's own `attributeProperties` was read.** Construct reads the
   tag's entry and then falls back to `global`; `JoinNameProviderHelper.cs` says so in
   its own comment, *"search more specific first, then global"*. `ch5-color-picker`
   declares no signal entries at all, so all six signals the user enabled on it were
   unnameable. `ch5-button` went from 5 signals to **10**, gaining `Enable` — which the
   real hand-authored i12 Multicam button has enabled and we previously could not name.
2. **The gate was `extenderPosition`.** That governs the project-level extender, not
   what a component can expose. `ch5-dpad`/`ch5-keypad`'s `sendeventonclickstart`
   ("Digital Start") have none — they are `removeOnContractUse` — yet the user enabled
   them. The gate is now the category prefix (`Send `/`Receive `), because merely having
   a category is far too loose: 179 entries are "Interactions" (`orientation`,
   `customvstheme`, `z-index`) and admitting those offers signals Construct cannot
   generate.

**The standing check that would have caught both**, now a test: walk every component in
the reference project and assert all 95 enabled signals are nameable.

**Attribute placement was also wrong, and the reference settled it.** Signals go LAST,
after the `ccid_sync_*` block — all six reference buttons end with exactly
`sendeventontouch`, `pd-receivestateselected`. The old position (between common wiring
and sync) was flagged in the code as a guess. `phase4_smoke_test`'s exact key-order diff
against the real `Button1` now passes with the default signals present rather than
suppressed, which is a stronger check than before.

**`DEFAULT_SIGNALS` now covers 15 component types**, transcribed from the reference, plus
six the user confirmed should expose none by design (video, video switcher, subpage
reference list, background, datetime, qrcode — each HAS signals available, so "none" is
a decision). The table is not trusted on its own: the test recomputes it from the
reference files every run, so if the user changes a component in Construct the test
reports the difference instead of us drifting.

Also fixed a latent hazard the extraction exposed: three tags have two distinct signals
sharing one friendly name (`ch5-button-list` "ItemSelected", `ch5-spinner` "Selected
Item", `ch5-video-switcher` "_Label"). The old lookup silently kept whichever came last;
ambiguous names now raise and list the attributes to choose between.

Full 37-file suite green. **Next / open threads** (nothing in flight): (1) contract
enablement for the COMPLEX components is still unverified in Construct — dpad, keypad,
button list, tab button, widget list, video switcher and media player each have their own
contract strategy, and some force signals on regardless of the file
(`DpadStrategy.cs:91`, `KeypadStrategy.cs:94`); the defaults are transcribed from the
user's files but no generated complex component has been opened in Construct yet;
(2) whether `FALLBACK_MIN_SIZE_PX = 35` holds across more pages and resolutions; (3) the
remaining generator phases — themes (7), fonts (8), languages (10), hard buttons (11),
and the skill layer.

**Phase 6 (contracts) — DONE, and far smaller than the phase index implied.** The user
corrected the scope up front: we never author a `.cuic`. Construct generates it, and all
we have to leave behind is (1) the signals enabled on each component and (2)
`ContractIsStale = "true"` in the `.cuip`. Both halves confirmed in CCIDE source before
any code was written — `ProjectOpenBehavior.cs:72-99` reads the flag on open, schedules
generation, clears it and saves; `ContractGenerationHelper.cs:1177` shows Construct
writing the `"Contract Enabled"` sentinel itself. Half of it was already built:
`project.py` has written `ContractIsStale="true"` for new projects since Phase 2.

**Enablement turned out to be pure SDK data**, so `generator/contracts.py` hardcodes
nothing per-component: `component-context.json`'s `attributeProperties` entries carrying
an `extenderPosition` ARE the contract-capable signals (the same gate Construct uses in
`CreateProjectComponent`), and their keys already have the storage prefix applied. The
prefix rule itself (`JoinPropertyProvider.cs:151`: state -> `pd-`, event -> bare) is
cross-checked against `schema.json`'s join direction for the whole catalog — 132 signals,
all agreeing — so a future SDK that disagrees fails a test instead of silently writing an
attribute Construct ignores. For `ch5-button` there are exactly five signals: Visibility,
Visibility_fb, Press, Selected, Mode.

**Three findings, each from measurement rather than assumption:**

1. **`component-context.json` outranks `schema.json`.** `ch5-media-player`'s
   `pd-receivestateusemessage` has no schema attribute at all, yet the hand-authored
   reference project writes it as a live signal. The planned hard "raise on disagreement"
   cross-check would have rejected a real signal; it now treats a schema entry as
   corroboration (`ContractSignal.schema_backed`) and the test pins the exception set.
2. **Signal names are not attribute names.** `pd-receivestateshow` contracts as
   "Visibility_fb", not "Visibility"; a slider's `pd-receivestatevalue` is "Lower Touch
   fb", not "Value". Hence resolution by the SDK's own names, with an unknown name raising
   and listing the valid options rather than silently skipping.
3. **Complex components are a separate path.** Dpads, keypads, button/widget lists, tab
   buttons, video switchers and media players each have their own contract strategy, and
   some (`DpadStrategy.cs:91`, `KeypadStrategy.cs:94`) force `ButtonPress` on regardless
   of the file. Phase 6's work is verified for simple components only — flagged in
   `docs/architecture/06-contracts.md` and in the index row.

**A new button now carries Press + Selected by default** (the user's choice), overridable
via `contract_signals=...` and disableable with `()`. `phase4_smoke_test` builds its
reference-comparison button with `()` so it still diffs like-for-like against the real
Button1, which has no signals — and now asserts that premise instead of assuming it.

**Live project updated for verification**: `GenTestProject2/ButtonVariants.cuig`'s three
buttons (IconButton/ImageButton/CheckboxButton) now carry both signals in the TOML *and*
the Html, and the `.cuip` is marked stale. Backup in the session scratchpad as
`GenTestProject2.bak-contracts-20260910-215713`. The edit was a targeted text insertion,
not a regeneration: the harness's byte-identical round-trip proves our section SPLITTER
matches Construct's, not that our TOML writer reproduces a real page.

Full 35-file suite green (4 new: signal discovery, enablement, button wiring,
end-to-end). **PENDING LIVE CHECK**: user opens GenTestProject2 in Construct and confirms
the Contract Editor shows Press and Selected for the three buttons. **Next / open
threads**: (1) that live check; (2) contract enablement for complex components, whenever
one of those component types is built; (3) whether `FALLBACK_MIN_SIZE_PX = 35` holds up
across more pages and resolutions; (4) the remaining generator phases — themes (7), fonts
(8), languages (10), hard buttons (11), and the skill layer.

**Relaxation redesigned as water-fill capping, after the user's own page proved the
first two designs wrong — DONE.** User clarified the intent: 35px is "the minimum allowed
size WHEN you have to shrink", not a target size (correcting a suggestion to raise the
constant to 40/45 to get bigger buttons — that's not what the knob is for; the floor is
clamped to each item's authored size and can only stop shrinking, never grow anything).
Sweeping their real `ReflowTest.cuig` down through smaller panels to prove the floor
actually engages then exposed a genuine defect in the relaxation path, and fixing it
properly took three attempts, each ruled out by measurement rather than argument:

1. **Drop the most demanding rows' floors, honor the rest in full** (the original). At
   400x240 this produced **1px** buttons and a 1px D-pad where no floor at all gave
   16-30px/87px — the rows still frozen at their full floor ate everything and starved
   the relaxed ones.
2. **Scale every floor by one factor.** Fixed the crush, but let a single inflated demand
   dominate: a 40px button sharing a row with a 300px D-pad forces that row to reserve
   263px (a row scales as ONE unit), and scaling 263 down proportionally still leaves it
   huge — ordinary button rows that were easily satisfiable fell from 50px to 26px.
3. **Water-fill capping** (`reflow.py::_cap_floors`, shipped). Both failures are the same
   failure: the expensive demands are exactly the ones asking for a large FRACTION of
   their own row. So bisect for the largest single cap `lambda` such that no row may
   reserve more than `lambda x its own natural height`, trim every floor above it, and
   leave affordable floors completely untouched.

Plus the rule that makes the whole thing safe: **a floor may never make a component
smaller than it would have been with no floor at all.** `_cap_floors` takes `min_cap` =
Tier 3's own uniform scale and refuses any capping below it, so the caller can't fund one
group's floors out of another's. Schema-backed floors (a real Construct limit) are still
held whole while that's affordable; when it isn't, everything degrades together instead of
the D-pad holding 100px while buttons are crushed to pay for it. Capping every floor
always succeeds, since at `lambda = min_cap` the capped total is at most `available`.

**Measured on the real `ReflowTest.cuig` (floor = 35):**

| target | with floors | without floors |
|---|---|---|
| 640x360 | btn 36-68, dpad 198 | btn 36-68, dpad 198 (floor not reached) |
| 480x272 | **btn 35-40, dpad 116** | btn 27-51, dpad 147 (floor engages, D-pad donates) |
| 400x240 | btn 16-30, dpad 88 | btn 16-30, dpad 87 (degraded to no-floor, gracefully) |
| 320x240 | btn 10-20, dpad 58 | btn 10-19, dpad 56 (never worse) |

New tests pin the invariant that the first design violated: a 30-point sweep over target
heights on a realistic shape asserting the smallest component is never smaller than the
no-floor result, plus a proportional bound on the deliberately pathological E2E fixture.
Full 31-file suite green.

**CONFIRMED IN CONSTRUCT 2026-09-10**: user opened the regenerated `GenTestProject2` and
reported the TSW-570 (640x360) layout looks correct -- closing out the chain of pending
live checks from the last three entries (aspect-lock/size-var fix, column-aware + wrap
compaction, and now minimum-size floors). The on-disk result is idempotent under the
final code: buttons 36px, Up/Down 68px, D-pad 198px, 21 elements, zero overlaps, inside
640x360. **Next / open threads** (nothing in flight): (1) whether
`FALLBACK_MIN_SIZE_PX = 35` still holds up across more pages and resolutions -- on this
page the floor isn't even reached at 640x360, it engages from ~480x272 down; (2) the
generator phases after reflow (contracts, themes, fonts, languages, hard buttons, skill
layer) per the original plan.

**Floor raised to 35px + the real page actually regenerated + a real source-selection
bug fixed to make that possible — DONE.** User re-checked `ReflowTest.cuig` in Construct,
still saw 28px buttons, and asked for a 35px minimum "which should force the dpad to be
made smaller". Two things were true: the 28px really was stale output (the file had never
been rewritten — the previous session verified on a COPY), and refreshing it for real was
blocked by a bug worth fixing on its own.

**`reflow_file` treated a non-empty source device block as the complete source layout.**
A device block is an OVERRIDE of the catch-all, not a replacement — Construct only restates
a rule where it differs. `ReflowTest.cuig`'s 1280x800 block holds exactly ONE rule (the
D-pad's `left`/`top`, byte-identical to the catch-all's), so reflowing from it produced a
one-element target block and silently dropped the other twenty: the exact "components
absent at the new resolution" failure this feature exists to prevent. Fixed as the
element-level counterpart of what `_fill_missing_size` already does at field level — every
catch-all element the device block doesn't mention is inherited into the source, catch-all
order first for determinism, with the block's own restated rule still winning for the
element it names. New regression test `reflow_source_block_union_test.py` covers both
halves (all three elements carried over; the restated one keeps its override).

**`FALLBACK_MIN_SIZE_PX` 30 -> 35** (one test fixture's target height retuned, since its
derived row floor no longer fit). Full 31-file suite green.

**Real files regenerated** (`mode="full_refit"`, SDK wired in; backup taken first, in the
session scratchpad as `GenTestProject2.bak-20260910-180206`): `ReflowTest.cuig` 21 -> 21
elements, source/menu buttons **28 -> 36px**, Up/Down **54 -> 68px**, D-pad **228 ->
198px**, zero overlaps, zero elements under their floor, max right 639 / bottom 358 within
640x360. `ButtonVariants.cuig` and `MyWidget.cuiw` unchanged (already fit).

**Worth knowing before tuning further: at 35 the floor never actually binds on this page.**
The uniform Tier 3 factor already lands the buttons at 36, so the D-pad's 228 -> 198 comes
from the column/compaction wrap fixes, not from the minimum. Swept the constant against the
real file to find where it does bite: 40 -> buttons 40px / D-pad 184; 45 -> buttons 42px /
D-pad 176; 50, 55, 60 -> unchanged at 42/176. It saturates because 42px is the buttons'
own authored height and the floor is deliberately shrink-only (clamped to each item's own
size, so it never grows a component past what the user drew) — once every button row sits
at its natural size, the D-pad simply takes the remainder (344 - 4*42 = 176). **Next**:
user re-checks TSW-570 in Construct and says whether to go to 40/45 for bigger buttons.

**Reflow: minimum-size floors for Tier 3 — DONE, implemented + verified against the
real files; one real finding the user should know about.** User reviewed the min-size
design spec (`docs/superpowers/specs/2026-09-10-reflow-min-size-design.md`, written at
the end of the previous session after real buttons came out 28px tall at TSW-570) and
asked to build it. Went spec -> plan (`docs/superpowers/plans/2026-09-10-reflow-min-size.md`)
-> inline TDD execution, five tasks, one commit each. Tier 3 now takes an optional
per-item floor: `fit_axis(min_sizes=...)` runs a flexbox-style iterative
freeze-and-redistribute (freeze whoever falls through their own floor at the current
uniform scale, reserve exactly that floor, recompute the scale for everyone still free,
repeat to convergence), while `min_sizes=None` — every legacy caller — runs the original
one-shot formula verbatim. That two-path split is load-bearing and now pinned by tests: at
`target_dim=10` the legacy branch's independent 1px floors span 11px (its documented,
deliberate overshoot) where the dict branch always packs to exactly `target_dim`. Floors
come from two sources: the SDK's own `minSizes` schema (`ch5-dpad` 100px, `ch5-keypad`
210px — real Construct-enforced limits) and `FALLBACK_MIN_SIZE_PX = 30` for the types
Crestron publishes nothing for (`ch5-button`, `ch5-slider`).

**Three corrections to the spec, all evidence-backed** (the spec was written from the
dpad/keypad entries alone): (1) `minSizes` values are NOT uniformly `"Npx"` strings —
`ch5-qrcode`'s is the unit-less `"160"` and `ch5-video-switcher`'s is a raw JSON **int**,
so the spec's `int(v.rstrip("px"))` would have raised `AttributeError`; (2) three tags
publish their own `minHeight` (`ch5-tab-button` is 110 wide / 68 tall), so the lookup is
per-axis with `minWidth` as the height fallback rather than `minWidth` for both; (3) every
floor is clamped to the item's own current size, keeping Tier 3 shrink-only — without it an
element already below its type's minimum would be "frozen" LARGER than it started.

**The X and Y axes turned out not to be symmetric, which the spec had assumed.** A row can
only ever reach X-axis Tier 3 with ONE column, because `wrap_rows`' peel loop exits only
when the remainder passes `_columns_fit` (Tier 2 compaction alone suffices) or when a
single unpeelable column is left — verified directly and now pinned by an assertion. So
freeze-and-redistribute never engages on X; there the floor only converts "silently emit a
component narrower than its own technical minimum" into an `AxisFitError`, which needs a
target narrower than the component's own floor (210px for a keypad) and so no real device
reaches it. The Y axis (`stack_rows`, no wrap tier) is where floors actually change
layouts.

**Deviation from the spec's error handling, forced by an existing test.**
`reflow_aspect_lock_dpad_test.py` immediately caught the spec's plain `AxisFitError`
doing real damage: a Y floor is DERIVED, not technical — keeping a 40px button at its own
30px minimum forces its whole 300px row to stay 225px tall — so a crowded stack can demand
more than `target_height` even when every individual component is satisfiable, and the
error made `_fit_group` skip the ENTIRE device block. That turns a legibility problem into
missing components, the exact failure `reflow_file` exists to prevent. `stack_rows` now
relaxes instead: it gives up SOFT (fallback) floors before schema-backed ones — a
`ch5-dpad` under 100px isn't just ugly, Construct doesn't support it — largest floor first
so the fewest rows are sacrificed, and warns how many rows lost their floor. A relaxed row
lays out exactly as it does today, so this can never be worse than current behavior.

**Verified against the real `GenTestProject2` (on a copy, the real files were NOT
touched):** `ReflowTest.cuig` reflows to all 21 elements, zero overlaps, inside 640x360,
zero elements under their own floor. **The finding worth knowing: the 28px buttons still
sitting in that file are stale output.** Re-running *today's* code produces 36px even with
floors disabled — the reported symptom was already fixed by the same-day column-aware +
compaction-aware wrap work, and the file just still holds the pre-fix block. So the floors
changed nothing on that page; they're a safety net, and the E2E test uses two fixtures that
genuinely exercise them instead (a tall unconstrained `ch5-image` donating height so
buttons hold 30px: 29px -> 30px; and an over-crowded page where relaxation takes
components at a usable size from 0 to 15 while the dpad holds its 100px schema floor).
5 new test files, full 30-file suite green with every pre-existing test unchanged except
`reflow_aspect_lock_dpad_test.py`, which now expects the one relaxation warning (its layout
assertions are untouched and still pass).

**Also spotted, NOT fixed (needs its own decision):** `reflow_file` treats a non-empty
source device block as the complete source, rather than the catch-all overridden by that
block. `ReflowTest.cuig`'s 1280x800 block holds exactly ONE rule (Construct only restates
a device rule when it differs from the catch-all), so a plain re-run from 1280x800 would
reflow ONE element and drop the other 20. That's why the verification above deleted that
block on its copy to source from the 21-element catch-all. **Next**: user decides whether
to (a) have the real project refreshed so TSW-570 can be re-checked in Construct — worth
doing, since the file's current block predates two rounds of fixes — and (b) whether the
source-block/catch-all union above is the next thing to fix.

**Reflow: column-aware row fitting + compaction-aware wrap decisions — DONE, verified
against the real TSW-570 (640x360) block.** User's next question after the D-pad/
missing-var fixes: "why do the Up/Down buttons move to a second row — there's certainly
room to have them in the same row." Investigated and found a genuinely deeper gap:
`detect_rows` correctly groups a D-pad with two Up/Down button pairs into one row (the
D-pad's height Y-overlaps both pairs), but the row's own X-fitting had no concept that
`iha5b0`/`i4rvpkl` (Up/Down, sharing the exact same source `left=292`) don't compete for
horizontal space — they're a vertical stack. Went through the full brainstorm -> spec ->
plan process (`docs/superpowers/specs/2026-09-10-reflow-columns-design.md`,
`docs/superpowers/plans/2026-09-10-reflow-columns.md`) given this touches the row/wrap
model and its overlap-safety proof, per the user's explicit choice of the general
"sub-column" approach over a narrower patch. Built `detect_columns` (the X-axis
transpose of `detect_rows`, grouping a row's members by source X-range overlap) and
wired `wrap_rows`/`_fit_group`'s X-loop to fit/peel whole columns instead of individual
elements — a stacked pair now always travels together. **Self-caught a second, deeper
bug while re-verifying**: my own spec's hand-trace claimed compaction alone would fit
the real D-pad row with no wrap needed, but the actual re-run still split it — because
`wrap_rows` decides whether to peel using the row's RAW (uncompacted) span vs.
target_width, never checking whether Tier 2 compaction alone (the very next tier, tried
immediately after wrap) would have sufficed on its own. Fixed with the same floor
formula Tier 3 already uses (`sum(widths) + (n-1)*min_gap <= target_width`), applied one
tier earlier before committing to a peel. Together, both fixes eliminate an entire
unnecessary Y-stacking slot on the real page, which is what had been forcing every other
row to compress harder than necessary. 4 new regression tests (one per fix, including
a hand-traced reproduction of the exact reported shape); full 19-file suite passes with
zero regressions (confirmed during planning that every existing wrap_rows test case's
outcome is unchanged under the new compaction-feasibility check — only genuinely-fits-
after-compaction cases like this one behave differently). Re-verified against the real
files: both Up/Down pairs still share their `left` position; source-row button height
improved from 21px to 28px, D-pad from 166px to 228px (both real, measurable
improvements, not just "no worse"); 21 elements, zero overlaps, everything within the
640x360 canvas, zero CSS-var/box mismatches anywhere in the block. **Next**: user to
re-check TSW-570 in Construct.

**Reflow bug fix (superseded above) — a resized button's adorner showed the correct new size, but the
button rendered much bigger — DONE.** Same session as the D-pad/aspect-lock work below,
found immediately after by the user re-checking TSW-570 in Construct: a "Source 2"
button's selection adorner correctly showed 21px height, but the button itself rendered
far larger. Root cause: the size-var fix from the D-pad bug only *recomputed* CSS vars
that already existed in an element's source `extra_vars` — it never *added* a missing
one. A real `size="regular"` button (confirmed: `--ch5-button--regular-width/height`
only ever appears once a button has actually been custom-resized in Construct) has NO
such vars in its source CSS at all, so when reflow forces it to `size="custom"` (see
below), Construct has nothing telling it to constrain the internal render to the new
size — it falls back to a larger default while the outer box (and the adorner) correctly
reflects what reflow computed. Fixed: `_fit_group` now `extra_vars.update(size_vars)`
unconditionally after the per-var loop, synthesizing the vars fresh whenever missing,
not just updating ones that happened to already be there. New regression test
(`reflow_missing_size_vars_test.py`) replicates the exact shape (a plain `size="regular"`
button with empty source `extra_vars`) and asserts the vars are present and match the
final box exactly. Full 16-file suite passes. Re-ran against the real files: zero
width/height/var mismatches across the entire TSW-570 block (programmatically checked
every element, not just the one the user spotted) — "Source 2" now has
`--ch5-button--regular-width: 84px`/`-height: 21px`, matching its box exactly. **Not yet
addressed** (user's next-flagged issue, needs the same brainstorm-first rigor as other
reflow algorithm changes since it touches the wrap model): the wrap tier always drops
peeled/overflow elements onto a brand-new row below rather than considering unused
width beside an already-tall sibling row (e.g. the D-pad's row) — user's hypothesis,
plausible but unconfirmed, is that fixing this would reduce how hard the Y-axis needs to
compress everything else, which is what drove some buttons down to an illegibly-small
21px in the first place (a texture/overlap symptom, not a true box overlap — confirmed
separately: wrapped sub-rows have a clean 4px gap, not a collision). **Next**: user to
re-check TSW-570 in Construct for the adorner/render-size fix, then decide whether to
proceed with the wrap-placement redesign.

**Reflow: SDK-schema-driven size scaling + aspect-lock reconciliation + size="custom"
forcing — DONE, verified against the real `GenTestProject2` at TSW-570 (640x360), the
smallest/most stressful resolution added yet.** After the centering fix (below), the
user added TSW-760 and TSW-570 to `GenTestProject2` and hit two new real bugs at 640x360
(small enough to force genuine wrap + compaction + scaling together for the first time):
(1) a `ch5-dpad` sharing a row with other content visibly overlapped its neighbors in
Construct even though the computed box math was provably non-overlapping — traced to
`_fit_group`'s extra_vars scaling only recognizing CSS var names containing the literal
substrings "width"/"height"; `--ch5-dpad--regular-size` (the D-pad's actual rendered-size
var, confirmed via the SDK's `classToVariableMapping` schema to be sourced from `width`)
matches neither, so it stayed at its original unscaled value regardless of what the box
computed — the box was safe, the RENDER wasn't; (2) a wrapped second line of real
(user-authored, not generator-authored) buttons ran off-canvas because those buttons had
`size="regular"`, which ignores explicit CSS and renders at a fixed preset size — the
same bug this generator's own element-creation code already works around at creation
time, just never applied by reflow. The user pushed back on an initial fix proposal
(schema-driven var scaling alone) by asking me to actually test it against the real
D-pad shape first — correctly caught that it was incomplete: X and Y are fit completely
independently, so even with the var wired to the *correct* schema-mapped axis, that
axis's own scale factor could still be 1.0 (unchanged) while the OTHER axis did all the
shrinking, leaving the var (and the real render) unscaled regardless. Real fix, verified
against a genuine resized D-pad in the reference project
(`C:\Solutions\ClaudeSamples\Components\Component - Keypad - DPad.cuig`, id `ixo7`:
width/height/var are always numerically identical, confirming the component is
fundamentally square): after both axes fit independently, any element the SDK schema
marks single-axis-sourced (`_is_aspect_locked`) gets width=height=`min(fitted_width,
fitted_height)` — shrinking only, so it can't introduce a new overlap. Built (all in
`generator/reflow.py`, gated behind an optional `sdk` param so every existing caller/test
that doesn't pass one keeps today's exact legacy behavior unchanged): `_component_size_css_vars`
(generalizes `ch5_button.py::button_size_css_vars` to any component type via the same
schema, recomputing size vars from the FINAL reconciled width/height instead of
ratio-scaling — strictly more robust, no compounding rounding difference between two
methods), `_is_aspect_locked`, `_tag_index` + `_force_custom_size` (reflow's first-ever
edits to `{Html}`/`[[Elements]]` TOML, not just `{Css}` — forces `size="custom"` on any
element actually resized that's currently `"regular"`, leaves repositioned-only elements
and already-`"custom"` elements untouched). `project.py::add_resolutions_to_project` now
loads the project's own installed SDK (from its `SdkId` attribute) and passes it through,
non-fatally (a project whose SDK can't be loaded still gets reflowed with legacy
behavior, flagged with a warning, never aborted). Two new regression tests hand-verify
both fixes against realistic shapes (`reflow_aspect_lock_dpad_test.py`:
a D-pad forced non-square by asymmetric X/Y scaling now reconciles to square, var
matches, zero overlaps; `reflow_force_custom_size_test.py`: a resized `"regular"` button
becomes `"custom"` in both Html and TOML, an already-`"custom"` resized button is a
no-op, a merely-repositioned `"regular"` button is left untouched). Full existing suite
(15 files) still passes with zero regressions. Re-ran the TSW-570 reflow against the
real files: D-pad now 166x166 (was 332x166, non-square), zero overlaps, everything
within the 640x360 canvas; the real Menu-row buttons that got genuinely resized are now
`size="custom"` in both Html and TOML. **Next**: user to re-check `ReflowTest.cuig` at
TSW-570 in Construct.

**Reflow: preserve centering (superseded above) — DONE, verified against the real
`ReflowTest.cuig`.** After
the width/height-fallback fix (below) got the portrait layout showing all 21 elements
on-canvas and non-overlapping, the user caught a subtler issue: the "Source" and "Menu"
button rows were centered in the 1280px landscape source (left margin 265px, right margin
266px) but came out flush against the portrait target's right edge (52px left, 0px right)
— none of `fit_axis`'s three tiers ever center a result; Tier 1 leaves an already-fitting
group at its original absolute position (meaningless once the canvas width changed), and
Tiers 2/3 both pack from a fixed left/top anchor. `stack_rows` reuses `fit_axis` for the Y
axis, so the row-stack had the identical gap (leaving ~600px of empty space below the
content in the 1280px-tall portrait canvas). Went through the full brainstorming → spec →
plan process given this touches the algorithm's core overlap-safety argument: design spec
at `docs/superpowers/specs/2026-09-10-reflow-centering-design.md`, implementation plan at
`docs/superpowers/plans/2026-09-10-reflow-centering.md` (5 tasks, executed inline).
**Design, approved by the user via 3 targeted questions**: (1) only recenter a row/stack
that was ALREADY centered in the source (detected via `abs(left_margin - right_margin) <=
max(4, round(0.01 * source_dim))`), not force-center everything; (2) evaluated per row
independently, not as one whole-page decision; (3) applied to both X and Y axes. The
trickiest piece: a row that `wrap_rows` splits into sub-rows has no meaningful "was IT
centered" answer of its own (it's a subset of a once-centered row) — resolved (user's
choice) by always centering a wrap-split fragment row, like a fresh flex-wrap line.
**Built**: `fit_axis` gained `source_dim`/`center` params and a final uniform-shift
`_center_result` step (safe by the same argument as Tier 1's existing translate — a
uniform shift of an already-non-overlapping group can't introduce a new overlap);
`wrap_rows` now tags each output row as a fragment (from a split) or untouched, so
`_fit_group` knows which centering rule to apply; `stack_rows` gained `source_height` for
the Y-axis case (a single whole-stack decision, no fragment concept). Every task's numeric
test case was hand-traced during planning before being written down. Verified: full
existing suite (13 files, phases 2-5 + every reflow task) passes with zero regressions —
confirmed during planning that none of the existing tests' synthetic fixtures are
accidentally centered within tolerance, so none needed adjusting except
`reflow_task5_wrap_rows_test.py`'s assertions (updated for `wrap_rows`'s new return
shape, an intentional, expected change). Re-ran the portrait reflow against the real
`ButtonVariants.cuig`/`ReflowTest.cuig`/`MyWidget.cuiw`: the 8-item and 2-item button rows
that were centered in the source now come back with byte-identical left/right margins in
the portrait target (26px/26px and 55px/55px respectively, was 52px/0px before this fix);
all 21 elements still present, zero pairwise overlaps, everything on-canvas. **Next**:
user to re-check `ReflowTest.cuig`'s portrait layout in Construct.

**Reflow bug fix (superseded above) — device-specific blocks that omit width/height (real Construct-authored
pages routinely do this) were silently dropping elements; fixed, verified against the
user's real `ReflowTest.cuig`.** After adding TSW-770 + TST-1080 (Portrait) to
`GenTestProject2` (see the `{DeviceResolutionSource}` fix below for that step), the user
opened the project in Construct and reported the portrait layout was broken — most
components weren't reflowed at all, several overflowing off the right edge of the canvas.
Root cause: `layout.py::parse_position_rules` required a `width` declaration to accept an
element's rule, but a real page authored directly in Construct (not by this generator,
`ReflowTest.cuig`) only restates `width`/`height`/`z-index` in a device-specific block when
they DIFFER from the catch-all block's value — most of its 21 elements had never been
resized, so their landscape-block rule was just `left:Npx;top:Npx;position:absolute;`. 18
of 21 elements were silently dropped from the source set as a result; reflow only ever fit
the 3 elements whose device rule happened to redundantly restate their size. This
generator's own output always restates the full property set, which is why 9+ prior tasks
of reflow work never exercised this path — every test (and every generator-authored
sample) had the shape the bug needed to hide behind, the same class of blind spot as the
per-element-`@media`-block bug found in the original reflow closeout. Fixed:
`parse_position_rules` now only requires `left`/`top` (width/height/z_index come back as
`None` when absent); new `reflow.py::_fill_missing_size` fills any `None` width/height/
z_index/extra_vars from the catch-all block's own value for that element id, dropping
(with a warning, not a crash) the rare element still missing size after that. New
regression test `reflow_partial_device_block_regression_test.py` (a hand-built page
mirroring the real shape: one element with a fully-restated device rule, two with only
left/top/position, one of *those* also carrying a catch-all-only `extra_vars` entry — the
test's first run caught a second gap, `extra_vars` not being merged the same way
width/height are, fixed in the same pass). Re-ran the portrait reflow against the real
`ButtonVariants.cuig`/`ReflowTest.cuig`/`MyWidget.cuiw` with `mode="full_refit"` (not
`add_resolutions_to_project` again, which would have duplicated the already-added
resolution id) — verified programmatically: all 21 of `ReflowTest.cuig`'s elements now
present in the portrait block, zero pairwise overlaps, everything fits the 800×1280 canvas
(max right exactly 800px). Full existing suite (phases 2-5, reflow tasks 9-10) still
passes clean. **Next**: user to re-check `ReflowTest.cuig`'s portrait layout in Construct.

**Phase 5 bug fix, corrected version — `{DeviceResolutionSource}` should never contain a
catalog-sourced resolution at all; the field-level "fix" earlier today was still wrong.**
Full arc: user was live-testing resolution add + reflow in `GenTestProject`'s Resolution
Manager and caught that an added resolution (TSW-570) looked wrong/duplicated. A first fix
pass (see superseded entry below) treated this as a field-value bug (`IsCustom`/
`resolutionType`/`resolutionName` mismatched vs. real sample files) and made
`to_project_resolution` write those fields into `{DeviceResolutionSource}` to match ~62
sampled real entries. The user then discovered the REAL root cause while fixing their own
environment: their machine's `resolutionData.user.json` (this machine's saved custom
resolutions) had an actual invalid duplicate resolution literally named "TSW-1070" —
colliding with the real catalog device name, which Construct is supposed to prevent but
evidently didn't always enforce — and that corruption had leaked into the reference sample
project (`C:\Solutions\ClaudeSamples\Components`) too. After the user cleaned both up,
`Components.cuip`'s `{DeviceResolutionSource}` became `[]` while `DeviceResolutionIds`
kept its one real id — direct proof the two aren't meant to be kept in lockstep the way
this module assumed. Traced this to source and confirmed definitively:
`PersistenceHelper.cs`'s `WriteProject`/`SaveProject` only ever assign
`uiProject.CustomDeviceResolutions` to `projectSource.DeviceResolutionSource` — catalog
picks are represented purely by id in `DeviceResolutionIds`, resolved against the global
catalog at runtime (`ResolutionHelper.cs::GenerateDeviceResolutionDto`); on load,
`OpenProjectHandlerHelper.cs` copies `{DeviceResolutionSource}` verbatim into
`CustomDeviceResolutions`, which the Resolution Manager renders as a second,
separately-removable list — exactly the duplicate/deletable row the user saw. So the
morning's field-level fix was solving the wrong problem: the real bug was ever writing a
catalog resolution into `{DeviceResolutionSource}` at all. Rewrote
`generator/devices.py::to_project_resolution` (no longer touches `IsCustom`/
`resolutionType`/`resolutionName` — the dict is now purely an id/width/height/orientation
carrier for `DeviceResolutionIds` + reflow math) and
`generator/project.py::build_project_attributes`/`add_resolutions_to_project` (catalog
resolutions only ever extend `DeviceResolutionIds`; `{DeviceResolutionSource}` is read and
written back untouched; `add_resolutions_to_project`'s reflow source-resolution lookup now
resolves existing ids against the global catalog, since it can no longer assume
`{DeviceResolutionSource}` holds every existing resolution). Also added macOS support to
`default_app_storage_path()` in both `devices.py` and `sdk.py` (confirmed via
`EnvironmentUtility.cs`: `~/Library/Application Support/crestron-construct/AppStorage`,
not the more commonly-documented `~/.config`), per the user's ask. Regenerated the
already-broken `GenTestProject2.cuip` in place (same Id, `{DeviceResolutionSource}` now
correctly `[]`) — flagged one unrelated, NOT fixed side-observation: the rewrite reset
`ThemePageColor` to `""` (the generator's long-standing, un-investigated default) where
real Construct-managed files (including this one, before the rewrite) show `"#ffffff"`;
out of scope for this fix, not touched further. `docs/architecture/05-resolutions.md`
updated with a correction section citing the exact source. **Not yet done**: this
module still has no "create a genuinely custom resolution" builder — when one is added,
it should validate that the resolution's name doesn't collide with a standard catalog
device name (the exact rule Construct itself is supposed to, but evidently doesn't always,
enforce). User is still mid-way through re-testing reflow in Construct; next step is
waiting on their signal to add resolutions to whichever project they're now using.

**Phase 5 bug fix (SUPERSEDED, see above — this fix was incomplete/wrong) —
`to_project_resolution`'s catalog->project field mapping was wrong.** User was
live-testing resolution add + reflow together in `GenTestProject` (Construct's Resolution
Manager) and caught that a resolution added by `add_resolutions_to_project` (TSW-570)
looked wrong/"custom" compared to the project's original TSW-1070 entry. Root cause,
confirmed against 62 real `DeviceResolutionSource` entries across 30+ human-authored
projects under `C:\Solutions` (not just the one reference project): Construct does NOT
copy a catalog entry's `IsCustom`/`resolutionType`/`resolutionName` verbatim into a
project. Fixed in `generator/devices.py::to_project_resolution` (hardcoded
`IsCustom: True`/`resolutionType: "generic"`). **This survey's ground truth turned out to
be contaminated** — see the superseding entry above for why, and the actual fix.

**Phase 5 continuation (superseded above) — multi-resolution reflow DONE, visually confirmed in
Construct.** All 10 tasks plus a final whole-branch review's fix wave are complete
and merged to `master` (29 commits). The final review caught the most severe bug in
the whole plan: the real generator emits one `@media` block PER ELEMENT even when
several elements share the identical query (`build_position_css` is called once per
element), so the reflow subsystem's single-match block lookup silently found and
reflowed only the FIRST element on any real multi-element page — the exact
"components absent" failure this feature exists to prevent, undetected through 9
tasks of review because every test (including the integration suite) hand-authored a
single combined block, a shape the generator never produces. Fixed with plural
`find_media_block_spans`/`parse_all_position_rules` in `generator/layout.py` and a
consolidating write path in `reflow_file`; verified against the real
`C:\Solutions\ClaudeGenTest\GenTestProject` (`ButtonVariants.cuig`'s 3 buttons all
correctly found and fit, was 1 before the fix) and now **visually confirmed by the
user in Construct** — all 3 buttons render on-canvas and non-overlapping at the
TSW-570 resolution. Also fixed in the same final-review pass: non-deterministic rule
ordering (iterated hash-randomized sets instead of the already-deterministic source
dicts), a missing fallback to the `99999px` catch-all block when a page predates the
project's first resolution, and two documentation overclaims. One known limitation
documented, not fixed, then re-assessed as lower-risk after the user corrected the
model's assumption about typical workflow: Construct projects are authored top-down
(largest resolution = primary, created first; smaller ones added and adapted down
afterward, never the reverse) — that's also the cascade-safe order, so the risk case
(a LARGER resolution added to a project that already has a smaller one) is contrary
to normal usage, not an everyday concern — see `docs/architecture/10-reflow.md`'s
"Known limitation" note. Full history in
`docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md` and
`docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (both kept as
an accurate corrected record, not left stale after the fix rounds). **Next**: another
component type, Trigger 2's skill-layer wiring (the mode-choice prompt when adding
elements to an already-multi-resolution page — `reflow_file`'s `mode` parameter is
the mechanism, not yet wired to the skill layer), or user's direction.

**Phase 5 continuation (superseded above) — multi-resolution reflow BUILT AND VERIFIED end-to-end
(both triggers' underlying mechanism, including row-wrap).** All 10 tasks of
`docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md` complete.
`generator/reflow.py` (`fit_axis`, `detect_rows`, `wrap_rows`, `stack_rows`,
`find_new_elements`, `check_overlaps`, `pick_primary`, `choose_source_resolution`,
`reflow_file`) plus new CSS helpers in `generator/layout.py` are wired into
`generator/project.py::add_resolutions_to_project` (Task 10), which now calls
`reflow_file` for every `*.cuig`/`*.cuiw` in a project's folder each time a resolution
is added, and returns the aggregated list of any reflow warnings (return type changed
from `None` to `list[str]`, additive). End-to-end scenario tests
(`generator/_test_output/reflow_task10_integration_test.py`) cover an edge-placed
element landing on-canvas after a smaller resolution is added, the
orientation-bootstrap case, a genuine row-wrap scenario (a 4-button single row split
across two lines on a much narrower resolution — hand-verified: rows split to
`[b0,b1]`/`[b2,b3]`, tops `20`/`114`, no element scaled, no pairwise overlap), and
zero regression when a project has no pages/widgets yet. Task 10 also found and fixed
a real bug exercising real catalog data end-to-end for the first time: a real `.cuip`'s
`{DeviceResolutionSource}` stores `width`/`height` as `"Npx"` strings (confirmed
against `Components.cuip`), but `reflow.py`/`layout.py` do plain arithmetic on those
fields — every earlier task's unit tests only used plain-int synthetic resolutions, so
this never surfaced until Task 10 called `devices.py::to_project_resolution` for real.
Fixed with new `project.py::_numeric_dim`/`_numeric_resolution`, applied only to the
copies fed into the reflow subsystem — the `.cuip` on disk still gets the real string
form. All 15 smoke/task tests pass (zero regressions). Manual Construct verification
prepared against the existing `C:\Solutions\ClaudeGenTest\GenTestProject` (a second,
640x360 landscape resolution added; setup script reported no warnings) —
**visual confirmation in Construct is still pending the user opening the project.**
Trigger 2 (the skill prompting `pin_existing`/`full_refit` when new elements are added
to an already-multi-resolution page) remains explicitly NOT built — a skill-layer
conversational step, not generator code; `reflow_file`'s `mode` parameter is the
mechanism a future skill call would choose between. See
`docs/architecture/10-reflow.md`'s "Algorithm and integration summary" section.
**Next**: user confirms the manual Construct check, then another component type,
Trigger 2's skill-layer wiring, or user's direction.

**Phase 5 continuation (superseded above) — multi-resolution reflow: row-wrap design
approved, NEW 10-task implementation plan written, ready to build.** Superseding the
entry directly below: the new plan lives at
`docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md` (the 2026-09-08 plan is
now stale/superseded, kept for history only). Tasks 1-3 and 7-8 carry over from the old
plan unchanged (portrait media query, CSS parse/build helpers, `fit_axis`,
`find_new_elements`/`check_overlaps`, `pick_primary`/`choose_source_resolution`) since
the core per-axis fitter's own behavior didn't change. Three new tasks implement the
row-wrap mechanism itself: Task 4 `detect_rows` (Y-overlap row grouping), Task 5
`wrap_rows` (the X-axis wrap tier — peel-and-recurse row splitting, hand-verified
against the spec), Task 6 `stack_rows` (Y-axis row-stacking). Tasks 9-10 (`reflow_file`,
integration) route through the new row/wrap/stack pipeline instead of a flat per-axis
`fit_axis` call, and Task 10 adds a genuine row-wrap end-to-end scenario (a 4-button row
split across two lines on a much narrower resolution, confirming no element gets scaled
and no pair overlaps). While translating the design into concrete code, found and fixed
a real spec gap: two rows produced by splitting the same original row share the exact
source `top` (splitting doesn't move anything vertically), so naively stacking them by
raw `min(top)` would tie sibling rows and overlap them — fixed with a pre-stacked
anchor, folded back into the design spec before Task 6 was written against it. Plan
self-review passed (full spec coverage, one placeholder-adjacent issue found and fixed
in Task 2's own test scaffolding, every function signature confirmed used consistently
across tasks). **Next**: user has been offered the execution-approach choice
(Subagent-Driven vs. Inline) — awaiting answer.

**Phase 5 continuation (superseded above) — multi-resolution reflow design REVISED
AGAIN (X axis gains a row-wrap tier), approved, implementation plan is now STALE and
needs to be rewritten.**
User revisited the design before answering the execution-approach question from the
prior session, pointing out the algorithm was pinned to pure per-axis scaling and
should behave like a real responsive layout — when horizontal space is tight but
vertical space is available, elements should wrap onto new rows below rather than only
ever compact/scale in place. Worked through the shape via clarifying questions: rows
are inferred from source elements' Y-overlap (not authored explicitly), the new wrap
tier sits between move and compact/scale (`move -> wrap -> compact -> scale` on X),
wrapping is row-only (no symmetric column-wrap for height-constrained cases), and
wrapping preserves source row groupings — only an overflowing row splits, trailing
elements peel onto a new row directly below it, rather than a full greedy re-pack that
could merge/reorder rows. The Y axis keeps its original 3-tier fallback but now
operates on the row list (as pseudo-items) instead of individual elements, so rows
stack top-to-bottom the same way elements used to. The "no new overlaps within the
fitted group" proof still holds without new 2D collision checks: same-row elements
stay disjoint on X (unchanged argument), different-row elements stay disjoint on Y
since each row's Y-extent is self-contained and rows themselves never overlap. Full
rewrite at `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`
(Scope, Algorithm, Components, Error handling, and Testing sections all updated; new
`detect_rows`/`wrap_rows`/`stack_rows` components added to `generator/reflow.py`'s
planned shape). **The previously-written 7-task implementation plan
(`docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`) was written against
the old per-axis-only algorithm and is now stale — it has NOT been rewritten yet.**
**Next**: get the user's review/sign-off on the revised spec (asked, awaiting answer),
then invoke writing-plans to redo the implementation plan, then get the
execution-approach answer (Subagent-Driven vs. Inline) that was never answered last
session either.

**Phase 5 continuation (superseded above) — multi-resolution reflow IMPLEMENTATION
PLAN WRITTEN, ready to build.** 7-task TDD plan at
`docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`, source-grounded like
every prior phase: confirmed the previously-unconfirmed portrait media-query formula by
reading `C:\Git\CCIDE`'s `breakpoint.ts::createRawQuery` directly and cross-checking two
real portrait `.cuiw` sample files elsewhere in that repo (`(orientation: portrait) and
(max-height: {H+1}px) and (max-width: {W+1}px), (orientation: portrait) and (max-height:
{H-1}px)` — same `±1px` shape as the already-confirmed landscape formula, just leading
with height instead of width), closing a gap flagged unconfirmed since Phase 4. Tasks:
(1) `orientation_media_query` + doc writeup, (2) CSS block parse/find/build helpers in
`layout.py`, (3) `fit_axis` (the 3-tier algorithm itself, unit-tested per tier plus the
insufficient-room edge case, with direct pairwise AABB checks proving no overlap across
a range of target sizes), (4) `find_new_elements`/`check_overlaps`, (5)
`pick_primary`/`choose_source_resolution`, (6) `reflow_file` tying both modes together
against a hand-built minimal file, (7) wiring into `add_resolutions_to_project` plus
end-to-end scenarios (an edge-placed element landing on-canvas, the
orientation-bootstrap case, zero regression on projects with no pages yet) and manual
Construct verification against the existing `GenTestProject`. Trigger 2 (the skill
prompting for `pin_existing`/`full_refit` when adding elements to an existing
multi-resolution page) is explicitly noted as NOT built by this plan — it's a
skill-layer conversational step that calls the same `reflow_file` this plan builds, not
new generator code. **RESUME POINT (session paused 2026-09-08, picking up next
session):** user was offered the execution choice (Subagent-Driven vs. Inline, per the
writing-plans skill's handoff) and hasn't answered yet — ask that question first, don't
re-derive it. No implementation code has been written yet; the plan file is the only
new artifact. **Next**: get the execution-approach answer, then start Task 1.

**Phase 5 continuation — multi-resolution reflow design spec REVISED AGAIN (reflow
generalized into a standalone, repeatable operation with two fit modes), approved,
ready for an implementation plan.** User pointed out UI work isn't a one-time event —
new controls get added to existing pages long after resolutions are set up (e.g. Apple
TV controls today, Cable box controls next week), and every resolution besides the one
they're authored against needs the same "missing block" fix reflow already solves for
newly-added resolutions. Reflow is now a standalone `reflow_file` operation with two
callers: `add_resolutions_to_project` (target starts empty) and a new skill-level
trigger when new elements are added to an already-multi-resolution page (target already
has content) — the skill asks the user which of two modes to use: `pin_existing`
(default — leave existing controls alone, fit only the new ones; the new elements are
guaranteed not to overlap each other but only best-effort/flagged against pre-existing
pinned elements, since real 2D obstacle avoidance was explicitly ruled out of scope) or
`full_refit` (recompute everything from the source resolution, discarding whatever was
in the target — same full overlap-safety guarantee as the original single-shot design).
Adding a brand-new resolution turns out to be `pin_existing` with zero pinned elements —
no special-casing needed, one mechanism covers both triggers. The still-approved 3-tier
per-axis fit math (move, then compact whitespace to a 4px floor, then scale down) is
unchanged from the previous revision; see
`docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` for the full,
current design. **Next**: write the implementation plan and build it.

**Phase 9 (assets) pulled forward — local image import DONE, confirmed live in
Construct.** User caught that the Phase 4 image-button variant couldn't actually be
verified without a real asset behind it. Built `generator/assets.py`, confirmed exactly
against the real `CrimsonSilk.cuia`/`.jpg` (which is also the exact asset the reference
project's own image-type button already references), wired it into the on-disk
verification project, and the user confirmed the image now renders correctly on the
button in Construct. See `docs/architecture/09-assets.md`. Phase 4's button work (plain +
icon + image + checkbox variants) is now fully closed out end-to-end. **Next**: back to
Phase 5 (full reflow) or another component type, per user direction.

**Phase 5 — resolutions: catalog + add-resolutions-to-a-project DONE.** User chose the
smaller first slice over bundling in full reflow math. Confirmed the real
device/resolution catalog (74 entries, `resolutionData.json`), resolved both
previously-flagged open questions (catalog-vs-per-project-selection, orientation enum
semantics), corrected an unconfirmed guess in `project.py`'s own example (no real
"TSW-1070 Portrait" catalog entry exists — TSW-1070 is landscape-only hardware), and built
`generator/devices.py` + `generator/project.py::add_resolutions_to_project`. See
`docs/architecture/05-resolutions.md`. **Next**: full multi-resolution reflow (deliberately
deferred, bigger/separate slice), another component type, or user's direction.

**Phase 4 — add a CH5 component: button DONE (plain + icon + image + checkbox
variants).** A freshly-created "Ch5 Button" matches real Construct-authored buttons
exactly for the plain and icon configurations, and produces a clean (intentionally
edit-history-free) result for image; checkbox is sanity-checked only since no real sample
exists to confirm against. All schema-driven from the installed SDK's
`component-context.json` + `sass-schema.json` (see `docs/architecture/04-ch5-schema.md`).
**Next**: multi-mode/advanced buttons, another component type, or Phase 5 (resolutions),
per the user's direction.

## Approach

This is a from-scratch rebuild of the Construct UI project generator (previous attempt:
`C:\ClaudeProjects\ConstructUISkill`, kept as-is, not reused). The key change: file-format
rules are being confirmed by reading Construct's own source
(`C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor`), not inferred from sample files by
trial and error. Every phase is proven against a known-good reference project
(`C:\Solutions\ClaudeSamples\Components`) with an automated diff (`harness/compare.py`)
before any manual testing inside Construct itself.

**This directive was violated for the whole of the component-sizing work (2026-09-10/11)
and prose did not prevent it.** The attribute diff ran on every test run; nothing diffed
the generated CSS, so four sizing bugs in a row reached the user, who found each by eye
across several rounds. Writing the rule down twice -- here and in the user's own notes --
changed nothing. What changed it was a TEST: `component_css_shape_test.py`, which found
four more mismatches the moment it existed, including ones inside the fix that had just
shipped.

So the rule is mechanical, not aspirational: **before generated output goes to the user,
an automated comparison must cover the dimension that changed** -- attributes, CSS,
children, file structure. If no such comparison exists, write it first; it is 60 lines.
A live check in Construct is only for what a diff structurally cannot see (does it
RENDER correctly), never a substitute for the diff.

## Log

- 2026-09-10: **Reflow: column-aware row fitting + compaction-aware wrap decisions --
  DONE, verified against real TSW-570.** User asked why Up/Down buttons still moved to
  a second row when "there's certainly room." Found `detect_rows` correctly groups a
  D-pad with two button pairs into one row (Y-overlap via the D-pad's height), but
  X-fitting had no concept that a pair sharing the same source `left` doesn't compete
  for horizontal space. Went through brainstorm -> spec -> plan (user chose the general
  "sub-column" approach); built `detect_columns` (X-axis transpose of `detect_rows`)
  and wired `wrap_rows`/`_fit_group` to fit/peel columns, not elements. Self-caught a
  second bug re-verifying: `wrap_rows` decided to peel using the row's RAW span, never
  checking whether Tier 2 compaction alone would have sufficed -- fixed with Tier 3's
  own floor formula, applied one tier earlier. Together: an entire unnecessary
  Y-stacking slot eliminated on the real page. 4 new tests, full 19-file suite passes.
  Re-verified: pairs still share `left`; button height improved 21px->28px, D-pad
  166px->228px; 21 elements, zero overlaps, zero var mismatches. See Current phase
  above for the full writeup.
- 2026-09-10: **Reflow: missing size-var bug (adorner right, button rendered bigger) --
  DONE.** User re-checked TSW-570 in Construct right after the D-pad/aspect-lock fix and
  caught it immediately: a resized button's adorner showed the new smaller size, but the
  actual render stayed big. The size-var fix only recomputed vars ALREADY present in an
  element's extra_vars -- a plain size="regular" button (the common case for anything
  not yet hand-resized) has none at all, so forcing it to size="custom" left Construct
  with nothing to constrain the render, even though the box CSS was correct. Fixed with
  an unconditional `extra_vars.update(size_vars)` so the vars get synthesized fresh when
  missing. New test `reflow_missing_size_vars_test.py`; full 16-file suite passes;
  re-verified zero width/height/var mismatches across the entire real TSW-570 block. See
  Current phase above -- also flags the user's next question (wrap-placement/Up-Down
  beside the D-pad) as not yet addressed, pending a decision on scope.
- 2026-09-10: **Reflow: SDK-schema-driven size scaling + aspect-lock + size="custom"
  forcing -- DONE, verified against real GenTestProject2 at TSW-570 (640x360).** User
  added TSW-760 then TSW-570 and hit two real bugs at the smallest resolution yet: a
  ch5-dpad visibly overlapped neighbors in Construct despite non-overlapping box math
  (its `--ch5-dpad--regular-size` var, schema-confirmed sourced from width, wasn't
  recognized by the old substring-based scaling and stayed unscaled); a wrapped real
  button ran off-canvas because `size="regular"` ignores explicit CSS entirely. User
  caught that my first fix proposal (schema-driven var scaling alone) was incomplete
  by asking me to test it first -- X/Y are fit independently, so the var's mapped axis
  could still have scale 1.0 while the OTHER axis did the shrinking. Real fix,
  confirmed against a genuine resized D-pad in the reference project (width=height=var
  always, confirming it's fundamentally square): after independent X/Y fitting, force
  width=height=min(...) for any SDK-schema-flagged single-axis component (shrink-only,
  can't introduce overlap). Built `_component_size_css_vars`/`_is_aspect_locked` (SDK
  schema-driven, generalizes ch5_button.py's existing button-only helper) and
  `_tag_index`/`_force_custom_size` (reflow's first edits to Html/TOML, not just Css) in
  reflow.py, gated behind an optional `sdk` param so every existing caller/test is
  unaffected; `add_resolutions_to_project` now loads the project's own SDK and passes
  it through, non-fatally. 2 new regression tests, full 15-file suite passes. Re-ran
  against the real files: D-pad now 166x166 (was 332x166), zero overlaps, resized real
  buttons now size="custom" in both Html and TOML. See Current phase above.
- 2026-09-10: **Reflow: preserve centering -- DONE, verified against the real
  ReflowTest.cuig.** User caught that a button row centered in the 1280px landscape
  source came out flush against the portrait target's edge instead of staying centered
  (none of fit_axis's 3 tiers ever center a result; stack_rows' Y axis had the same
  gap). Went through brainstorming -> spec
  (`docs/superpowers/specs/2026-09-10-reflow-centering-design.md`) -> plan
  (`docs/superpowers/plans/2026-09-10-reflow-centering.md`, 5 tasks) given this touches
  the algorithm's overlap-safety argument. User's approved design: only recenter a
  row/stack that was already centered in the source (tolerance `max(4, 1%)`), decided
  per row independently, applied to both axes; a wrap-split fragment row always centers
  (no meaningful "was it centered" answer of its own). Built: `fit_axis` gained
  `source_dim`/`center` + a final uniform-shift step; `wrap_rows` tags fragment vs.
  untouched rows; `stack_rows` gained `source_height`. Full existing suite passes with
  zero regressions (verified during planning no fixture was accidentally centered,
  except `reflow_task5_wrap_rows_test.py`'s assertions, intentionally updated for the
  new return shape). Re-ran against the real files: previously-centered rows now come
  back with byte-identical left/right margins (26/26, 55/55 -- was 52/0), all 21
  elements present, zero overlaps. See Current phase above for the full writeup.
- 2026-09-10: **Reflow: device-specific blocks omitting width/height were silently
  dropping elements -- found and fixed after the user's real `ReflowTest.cuig` reflowed
  broken (most components not moved, several overflowing off-canvas) for TST-1080
  Portrait.** Root cause: `layout.py::parse_position_rules` required `width` to accept a
  rule; a real Construct-authored device block only restates width/height/z-index when
  they differ from the catch-all's value, so 18 of `ReflowTest.cuig`'s 21 elements (whose
  device rule was just `left/top/position`) were silently dropped. This generator's own
  output always restates the full set, so no prior task/test ever exercised the omitted
  case. Fixed: `parse_position_rules` now only requires left/top; new
  `reflow.py::_fill_missing_size` fills missing width/height/z_index/extra_vars from the
  catch-all block per element (the new regression test's first run also caught extra_vars
  not being merged, fixed in the same pass). Re-ran the portrait reflow against the real
  files with `mode="full_refit"`; verified programmatically (all 21 elements present, zero
  pairwise overlaps, fits the 800x1280 canvas). See Current phase above for the full
  writeup.
- 2026-09-10: **`{DeviceResolutionSource}` architecture bug found and fixed (supersedes
  the same-day field-level fix below, which was still wrong).** User fixed their own
  corrupted environment (an invalid custom resolution named "TSW-1070", colliding with
  the real device, in `resolutionData.user.json`, which had leaked into the reference
  sample project too) and, watching `Components.cuip`'s `{DeviceResolutionSource}` become
  `[]` after cleanup while `DeviceResolutionIds` stayed populated, that was the tell that
  this module's whole model was backwards. Traced to source
  (`PersistenceHelper.cs::WriteProject`/`SaveProject`): `{DeviceResolutionSource}` only
  ever persists genuinely custom resolutions, never catalog picks — confirmed via a
  `Grep` across `C:\Git\CCIDE` landing on the exact two-line assignment. Rewrote
  `generator/devices.py::to_project_resolution` and
  `generator/project.py::build_project_attributes`/`add_resolutions_to_project`
  accordingly; `phase5_smoke_test.py`'s regression check rewritten to assert
  `{DeviceResolutionSource}` stays `[]` for catalog-only adds (the opposite of what it
  asserted a few hours earlier). Also added macOS support to `default_app_storage_path()`
  in `devices.py`/`sdk.py` at the user's request, grounded in `EnvironmentUtility.cs`.
  Regenerated the real `GenTestProject2.cuip` on disk to match (same Id, now-empty
  `{DeviceResolutionSource}`). Full test suite (phases 2-4, reflow task 10, phase 5) still
  passes clean. See Current phase above for the full writeup, including one flagged-but-
  not-fixed side observation (`ThemePageColor` default).
- 2026-09-10: **`to_project_resolution` catalog->project field bug "fixed" (SUPERSEDED —
  wrong fix, see entry above).** User caught it live-testing in `GenTestProject`; root
  cause was believed to be `IsCustom`/`resolutionType`/`resolutionName` field mismatches,
  "confirmed" against 62 real `DeviceResolutionSource` entries scraped from 30+
  human-authored `.cuip` files under `C:\Solutions`. That survey's ground truth turned out
  to be contaminated by the same machine-level corruption described above — the real bug
  was structural, not field-level. Left in the log for an honest record of how this was
  actually debugged (two passes, not one).
- 2026-09-09: **Correction: Construct projects are authored top-down, not
  smallest-first.** User corrected an assumption in the just-written "known
  limitation" note (cascade ordering risk when resolutions are added out of size
  order): Construct projects work like desktop-first responsive web design — the
  largest resolution is always created first and is the primary; smaller resolutions
  are added afterward and adapted down from it, never the reverse. This is also the
  cascade-safe order (a later-added smaller resolution's block lands later in the
  file, correctly overriding the primary at smaller viewports), so the risk case
  documented (a larger resolution added after an existing smaller one) is contrary to
  normal usage, not an everyday concern as the original note implied. Reworded the
  known-limitation note in `docs/architecture/10-reflow.md` and this file's Current
  phase section to reflect the corrected understanding — the limitation itself is
  still real and still unfixed, just lower-priority than first stated.
- 2026-09-09: **Multi-resolution reflow — CLOSED OUT: final whole-branch review's
  Critical bug fixed and visually confirmed in Construct.** The final review (after
  all 10 tasks individually passed) found the real generator emits one `@media` block
  PER ELEMENT even when several elements share the identical query
  (`build_position_css` runs once per element), but `layout.py`'s `find_media_block`
  only ever finds the FIRST such block — silently reflowing only one element on any
  real multi-element page, zero warnings. Confirmed against the real
  `ButtonVariants.cuig` (3 buttons, 3 separate `99999px` blocks, not one combined
  block) before ruling; every task's tests had hand-authored the combined-block shape
  for convenience, which is why 9 tasks of review missed it. Fixed with plural
  `find_media_block_spans`/`parse_all_position_rules` (find every matching block) and
  a consolidating write path (replace the first matching target span, delete the
  rest); also fixed in the same pass: non-deterministic rule ordering (was iterating
  hash-randomized sets), a missing `99999px` catch-all fallback for pages that
  predate a project's first resolution, and two documentation overclaims. Independently
  verified via standalone scratch scripts before writing the fix into the design spec
  and plan, then via a scoped re-review (adversarial splice stress test, 4 different
  `PYTHONHASHSEED` values) after the fix landed — clean, no new breakage. One known
  limitation documented but not fixed: resolutions added out of ascending size order
  can invert the CSS cascade (latent, unreached by any test or the real project — see
  `docs/architecture/10-reflow.md`). User then opened `GenTestProject` in Construct,
  switched to the newly-added TSW-570 resolution, and confirmed all 3 buttons on
  `ButtonVariants.cuig` render on-canvas and non-overlapping — the one remaining
  unconfirmed item from Task 10, now closed. **Next**: another component type,
  Trigger 2's skill-layer wiring, or user's direction.
- 2026-09-09: **Multi-resolution reflow — Task 10 (final task) DONE: wired into
  `add_resolutions_to_project`, end-to-end scenarios including row-wrap, doc
  writeup.** `add_resolutions_to_project` now calls `reflow.reflow_file` for every
  `*.cuig`/`*.cuiw` in a project's folder, once per newly-added resolution, using
  `choose_source_resolution` to pick which existing resolution to fit from
  (same-orientation primary, or the other orientation's primary for the bootstrap
  case); return type changed from `None` to `list[str]` of aggregated reflow warnings
  (additive, existing callers unaffected). New
  `generator/_test_output/reflow_task10_integration_test.py` covers 4 scenarios: an
  edge-placed element landing on-canvas after a smaller resolution is added, the
  orientation-bootstrap case, a genuine row-wrap scenario (4-button single row onto a
  much narrower resolution — hand-traced to confirm the algorithm's own output before
  trusting the test's assertions: rows split `[b0,b1]`/`[b2,b3]`, tops land at `20`/
  `114`, all 4 buttons stay their original 150x90 size, zero pairwise overlaps), and a
  zero-pages regression check. Found and fixed a real bug while wiring real catalog
  data through the pipeline end-to-end for the first time (every earlier task's unit
  tests used hand-built plain-int resolution dicts, never the real catalog shape): a
  real `.cuip`'s `{DeviceResolutionSource}` stores `width`/`height` as `"Npx"` strings
  (confirmed against `Components.cuip`), but `reflow.py`/`layout.py` do plain
  arithmetic on those fields (`width + 1`, `pick_primary`'s width comparison) and
  crashed with a `TypeError`. Fixed at the `add_resolutions_to_project` wiring
  boundary — new `_numeric_dim`/`_numeric_resolution` coerce width/height to `int`
  only for the copies fed into the reflow subsystem, leaving what's written to the
  `.cuip` on disk in the real, confirmed string form. All 15 smoke/task tests pass
  (zero regressions). Manual verification prepared against the real
  `C:\Solutions\ClaudeGenTest\GenTestProject` (a 640x360 landscape resolution added
  via the reflow path; setup script printed no warnings) — visual confirmation in
  Construct itself is still pending the user opening the project, not yet claimed as
  confirmed. `docs/architecture/10-reflow.md` updated with the algorithm/integration
  summary and this bug's writeup. This closes out the 10-task multi-resolution reflow
  plan in full.
- 2026-09-09: **Multi-resolution reflow — X axis redesigned with a row-wrap tier
  (`move -> wrap -> compact -> scale`), via the brainstorming skill.** User asked to
  revisit the reflow logic before answering the still-outstanding execution-approach
  question, objecting that the design was "pinned to a pure horizontal space" — pure
  per-axis scaling/compaction, never letting elements use available vertical room by
  moving below other elements. Classified as an architectural revision (changes an
  already-approved design's core algorithm, reopens a line explicitly marked
  out-of-scope). Resolved via one-at-a-time clarifying questions: rows are inferred
  from source Y-overlap (not authored explicitly); the wrap tier is inserted between
  move and compact (wrap preferred over shrinking); row-wrap only, no symmetric
  column-wrap; and wrapping splits only overflowing source rows (trailing elements
  peel onto a new row below), rather than a full greedy re-pack that could merge or
  reorder rows. Y axis keeps its original 3-tier fallback (move/compact/scale)
  unchanged in kind, but now operates on the row list as pseudo-items instead of
  individual elements. Reworked the "no new overlaps" proof to cover the new
  structure: same-row elements stay disjoint on X (original argument, unchanged
  wording only), different-row elements stay disjoint on Y since each row's Y-extent
  is self-contained and rows themselves never overlap — no new 2D collision detection
  needed. Rewrote Scope, Algorithm, Components, Error handling, and Testing sections
  of `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` in place
  (same file, per this project's established revision pattern); self-review caught and
  fixed two stale "3-tier fit"/pre-wrap-tier-order wording spots left over from the
  previous revision. Committed (`fde5733`). **The existing 7-task implementation plan
  was written against the old algorithm and is now stale — not yet rewritten.**
  **Next**: user reviews the revised spec, then re-run writing-plans for a fresh
  implementation plan, then get the still-unanswered execution-approach choice.
- 2026-09-08: **Multi-resolution reflow — implementation plan written** (7 TDD tasks,
  `docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`), following the
  writing-plans skill against the now-approved spec. Before writing it, did the source
  research the spec's scenarios actually require but didn't yet have: the portrait
  media-query formula, unconfirmed project-wide since Phase 4 (flagged in `layout.py`'s
  own docstring and `04-ch5-schema.md`). Found and read `C:\Git\CCIDE`'s
  `breakpoint.ts::createRawQuery` directly (the real client-side source that generates
  these breakpoints) and cross-checked it against two real portrait `.cuiw` files
  elsewhere in that repo (`Bug_CCIDE_5225_Widget2.cuiw`/`Widget5.cuiw`, both a
  1024x1322 portrait resolution) — source and samples agree exactly, closing the gap
  rather than letting the plan bake in a guess. Also worked out concrete tier-2/tier-3
  math not fully nailed down in the spec's prose: whitespace compaction is a linear
  interpolation from each gap's original size toward the 4px floor (weighted by how
  much reduction is still needed), and tier-3 scaling reserves room for the mandatory
  `(n-1)*4px` floor gaps before computing the shared scale factor, then repacks at
  exactly 4px rather than edge-to-edge. Plan self-review passed: full spec coverage
  (every Components-section function has a task), no placeholders, and a
  cross-checked-against-the-actual-codebase pass confirming `Element`'s dataclass
  defaults, `write_cuig`'s signature, and `harness.compare`'s section-index ordering
  all match what the plan's own test code assumes. **Next**: execute the plan.
- 2026-09-08: **Multi-resolution reflow — generalized from a one-shot,
  resolution-add-only operation into a standalone `reflow_file` callable any time a
  resolution's block is missing elements that exist elsewhere in the file.** User
  pushed back on the spec's implicit assumption that reflow only ever happens at the
  moment a resolution is added — real projects gain new controls on existing pages long
  after resolutions are set up, and those controls hit the identical "other resolutions
  have no CSS rule for this element" gap. Resolved two design forks via clarifying
  questions: (1) when new controls are added to a page that already has fitted content
  in other resolutions, the user wants to be **prompted** each time (not a fixed
  policy) — leave the existing controls alone and fit just the new ones, or re-fit the
  whole page — so `reflow_file` gained a `mode` parameter (`pin_existing` default vs.
  `full_refit`) instead of one hardcoded behavior; (2) in `pin_existing` mode, new
  elements are only guaranteed not to overlap *each other* — guaranteeing they avoid
  the pinned pre-existing elements too would need real 2D obstacle-avoidance placement,
  which the user agreed to explicitly rule out of scope in favor of a best-effort fit
  plus a flagged warning (`check_overlaps`) for manual nudging in Construct. New
  components added to the spec: `find_new_elements` (id-set diff between source and
  target blocks) and `check_overlaps` (pairwise AABB check for the warning surface);
  `reflow_file` now returns a `ReflowResult` carrying `warnings` instead of assuming a
  silently-clean result. `add_resolutions_to_project` (Trigger 1) turns out to be the
  degenerate case of `pin_existing` with zero pinned elements, so it needed no special
  casing — one mechanism now covers both the resolution-add trigger and the new
  add-elements-to-an-existing-multi-resolution-page trigger. Full rewrite at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (Problem,
  Scope, Algorithm, Integration, Components, Error handling, and Testing sections all
  updated). **Next**: user reviews the rewritten spec, then the implementation plan.
- 2026-09-08: **Multi-resolution reflow — fit-strategy redesigned to a 3-tier fallback
  (move, then compact whitespace, then scale), at the user's direction.** The
  just-approved spec (previous entry below) always scaled first and only repositioned
  as a last-resort clamp; the user asked for the opposite priority — try repositioning
  first, then reducing whitespace, and only scale down if neither works. Clarified two
  ambiguities before rewriting: (1) the "move" tier must be collision-aware, not
  independent per-element clamping — resolved by proving that rigid group translation
  (tier 1) plus order-preserving, never-negative-gap compaction (tiers 2/3) can never
  introduce a new overlap, since two elements non-overlapping in the source are always
  disjoint on at least one axis and that disjointness survives any monotonic shrink; (2)
  whitespace reduction preserves element order (no bin-packing/rearrangement) and the
  final scale is one uniform factor per axis, both per the user's explicit choice. User
  then set the minimum gap floor at 4px, applied through both tier 2 (compaction) and
  tier 3 (scale-down reserves `(n-1)*4px` for mandatory gaps before scaling the
  remainder) rather than allowing gaps to reach 0. Spec rewritten in place at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (Algorithm,
  Components, Error handling, and Testing sections all updated; new insufficient-room
  edge case documented for when even 4px floor gaps don't fit the element count).
  **Next**: user reviews the rewritten spec, then the implementation plan.
- 2026-09-08: **Multi-resolution reflow — design spec written and approved.** Covers the
  gap left by Phase 5's first slice: `add_resolutions_to_project` updates the `.cuip`'s
  resolution list but does nothing to existing pages'/widgets' component
  positions/sizes, so content near the edge of an original canvas can land off-canvas on
  a newly-added smaller/differently-oriented resolution. Design: parse each file's
  `99999px` catch-all CSS block (the confirmed single source of truth for current
  position/size) into per-element `{left, top, width, height, extra_vars}`, scale
  per-axis from a chosen source resolution (same-orientation primary, or the other
  orientation's primary for the bootstrap case), then clamp any still-off-canvas element
  by repositioning only (never resizing). Emits one new `@media` block per newly-added
  resolution; the existing catch-all block is untouched. New components planned:
  `layout.py::parse_position_rules`/`build_reflow_block` (extending, not replacing, the
  existing single-element device-block logic) and a new `generator/reflow.py`
  (`reflow_file`, `pick_primary`, `choose_source_resolution`), wired into
  `add_resolutions_to_project`. Explicitly out of scope: resolution removal,
  shrink-to-fit, and reflowing hand-authored non-generator CSS. Full spec at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`. **Next**: write
  the implementation plan.
- 2026-09-08: **Phase 9 (assets) pulled forward — local image import DONE.** User was
  checking the image-button variant in the generated project and pointed out it couldn't
  really be called verified without an actual image asset imported and referenced —
  correctly identified that no asset-import code existed yet (it's Phase 9, unstarted).
  Found the real reference project's image-type button already references a specific real
  asset (`C:\Solutions\ClaudeSamples\Components\assets\CrimsonSilk.cuia`/`.jpg`, Id
  `498f8b9e-eade-4d9d-9475-49bb03d4324b`) — about as strong a ground truth as this project
  has had. Confirmed the `.cuia` format (`{FileMetadata}` + `{AssetAttributes}`, the
  latter a plain `Dictionary<string,string>` whose real key-insertion order — Id, Name,
  SourceUri, AspectRatio, AssetSourceType, Username, Password — was found in
  `SaveAssetMetadataHandler.cs`, confirmed 7/7 against the real file), that
  `MinimumProjectApp=""` for assets specifically (not a typo, a genuinely different
  default than every other file type), and that `AspectRatio` (`width/height` as a
  double) computed independently in Python via Pillow matches C#'s ImageSharp-computed
  value byte-for-byte (`1.588550983899821`) for the real file. Also confirmed no new code
  was needed to reference an asset from a button — `ch5_button.py`'s existing `asset_id`
  param already does the right thing (the real button has no static `iconurl` attribute at
  all; Construct resolves it dynamically from `assetid`). Built `generator/assets.py`
  (`import_asset`), verified via `phase9_assets_smoke_test.py` (imports the real
  CrimsonSilk.jpg, diffs the generated `.cuia` against the real one — exact match) plus a
  new dependency on Pillow. Imported the same real asset into the on-disk verification
  project and rewired `ButtonVariants.cuig`'s image button to use it, for the user to
  check in Construct. Full writeup in `docs/architecture/09-assets.md`.
- 2026-09-08: **Phase 5 — device/resolution catalog + add-resolutions-to-a-project DONE.**
  User asked whether the rest of the components or resolutions should come first;
  recommended resolutions first since `generator/layout.py` (built in Phase 4) is now a
  shared foundation every future component will call, and doing Phase 5 while only one
  component type exists avoids rework across many later. User agreed, then chose the
  smaller "catalog + add resolution" slice over bundling in full reflow math when asked.
  Research resolved both Phase 2-flagged open questions: (1) `UiEditorResolutionDao.cs`
  vs. inline `.cuip` `{DeviceResolutionSource}` are NOT overlapping — the DAO reads a
  global, not-per-project catalog file, the `.cuip` section stores which catalog entries a
  project has selected; (2) `DisplayOrientation` enum confirmed
  (`None=0,Landscape=1,Portrait=2,Both=3`), serialized as int inside `.cuip` but as a
  string in the global catalog file (two different JSON contexts for the same enum).
  Found the real catalog on disk (`%APPDATA%\crestron-construct\AppStorage\data\ui\
  resolution\resolutionData.json`, 74 entries) and confirmed/corrected a previously
  fabricated example in `project.py`'s own `__main__` block: no "TSW-1070 Portrait" exists
  in the real catalog (TSW-1070 is landscape-only hardware); TST-1080 genuinely supports
  both orientations and is used instead. Built `generator/devices.py` (catalog reader —
  found and worked around a real collision: this machine's own custom-resolutions file has
  a personal entry also named "TSW-1070", so `include_custom` defaults to False; also
  normalizes an orientation int-vs-string inconsistency between the two catalog files) and
  `generator/project.py::read_cuip`/`add_resolutions_to_project` (extends an existing
  project's resolutions, handles both the "already has resolutions" and "starts with zero"
  cases, the latter correctly inserting `DeviceResolutionIds` at the confirmed key
  position rather than just appending). Factored `override_attr` out of `ch5_button.py`
  into `toml_util.py` since `project.py` needed the identical operation. All verified via
  `generator/_test_output/phase5_smoke_test.py` (harness round-trip + structural checks;
  no real multi-resolution `.cuip` exists in the reference project to diff against, so
  verified against `build_project_attributes`' own confirmed shape instead, same standard
  used for Phase 2). Full writeup in `docs/architecture/05-resolutions.md`. Full
  multi-resolution reflow (the actual CSS math for non-primary resolutions) deliberately
  NOT built this slice — flagged as a separate, bigger follow-up.
- 2026-09-08: **`--ch5-button--regular-{width,height}` CSS var bug found and fixed.** User
  checked again after the `size="custom"` fix and the adorner still mismatched the actual
  button, asking directly: "are you 100% sure the CSS values match the property grid or
  vice versa and the TOML as well? check the sample project to be sure." Re-verified —
  property grid/CSS/TOML DID all agree; the remaining issue was that `ch5-button`'s own
  shadow-DOM rendering reads its visual size from CSS custom properties, not the plain
  outer `width`/`height` the adorner uses. Found the exact mechanism in
  `component-context.json`'s `classToVariableMapping` "idSelector" entry (already read
  once for the sync-attribute work, but this entry unused until now): `width` ->
  `--ch5-button--regular-width`, `height` -> `--ch5-button--regular-height` (swapped for
  vertical orientation, unconfirmed — no vertical button in the reference project). New
  `ch5_button.py::button_size_css_vars` derives these from that schema entry; wired into
  `layout.py::build_position_css`'s new `extra_vars` param, written in both `@media`
  blocks. Verified value-for-value against real ButtonWithIcon (190x58 ->
  `--ch5-button--regular-width: 190px`/`-height: 58px`, exact match). Rebuilt
  `MainPage.cuig`/`ButtonVariants.cuig` again for the user to re-check. Full writeup in
  `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **`size="custom"` bug found and fixed.** User checked the CSS fix in
  Construct and caught a follow-on bug: the canvas selection adorner was visibly larger
  than the button's actual rendered size. Cause: `size="regular"` (the raw SDK default,
  used verbatim until now) renders the button at its theme's fixed preset dimensions,
  ignoring whatever explicit width/height CSS is written — didn't show up in the earlier
  "112/112 exact match" claim only because Button1's chosen size (84x42) happened to equal
  that preset exactly. Fixed at the user's direction: `size` is now always forced to
  `"custom"` in `ch5_button.py::build_default_button_attributes` (`ccid_lastSizeSelected`
  left untouched, a separate "restore" bookkeeping field, confirmed distinct from `size`
  in the real file's own resized instances) — also consistent with every real button
  instance in the reference file that had actually been resized. Smoke test's plain-button
  comparison updated to exclude `size` from the exact-match assertion (documented as
  intentional). Rebuilt `MainPage.cuig`/`ButtonVariants.cuig` again for the user to
  re-check. Full writeup in `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **Position/size CSS bug found and fixed.** User checked the icon/checkbox
  button variants in Construct and reported "size can never be auto, even when you are
  using a fixed size" — the Properties panel showed Left/Top/Width/Height as "auto" for
  every generated button. Root cause: `build_default_button_element` never wrote any
  `{Css}` rule at all, only `[[Elements]]` TOML attributes — position/size lives entirely
  in CSS. Fixed with new `generator/layout.py::build_position_css`, confirmed against real
  Button1's CSS rule in `Component - Button.cuig` (two `@media` blocks: 99999px catch-all
  + device-specific landscape breakpoint; theme-selector child rule sourced from the SDK's
  own `componentProperties.customThemeRequiredSelectors`, schema-driven not hardcoded).
  While fixing this, **also found and fixed a related Phase 3 gap**: widget's default CSS
  (`page.py::default_widget_html_css`) always used a hardcoded 2560x1440 "no devices yet"
  fallback breakpoint, flagged unconfirmed at the time — now confirmed wrong by direct
  inspection of a real widget in a project WITH a device defined (`Widget.cuiw`, which
  contains a button): it uses the real device breakpoint, not the fallback. Both now share
  one confirmed formula (`layout.py::landscape_media_query`, matched against two
  independent real files at two different widths/heights). `x`/`y`/`width`/`height`/
  `z_index`/`resolution` are now required parameters on `build_default_button_element`
  (matches the widget function's existing "explicit size, no invented default"
  precedent). All Phase 3/4 smoke tests updated with position-CSS regression checks (`"auto"
  not in css`). Rebuilt `MyWidget.cuiw`/`MainPage.cuig`/`ButtonVariants.cuig` in the real
  on-disk verification project with correct CSS for the user to re-check. Full writeup in
  `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **Phase 4 — button icon/image/checkbox variants added.** User confirmed the
  plain button looked correct on the canvas in Construct, then asked to cover the
  variants. Turned out nearly free once the sync-attribute derivation existed:
  `build_sync_attributes` already selects sectors purely from `showWhen` matching on
  current attribute values, so a variant is just different input values, not new logic.
  **Icon** (`icon_class`/`icon_library` params): exact match against the real
  "ButtonWithIcon" instance, excluding 2 confirmed UI-state artifacts (`oldID`,
  `ccid_customSizeSet`) and 1 independent `size` customization. **Image**
  (`image_icon_type="imageasset"`): found and deliberately did NOT reproduce a real
  discrepancy — the reference file's image-type button also carries a stale, unused Icon
  sync sector (16 keys), traced to `setSyncData`'s "only add, never remove" attribute
  guard combined with that specific instance's edit history (authored as icon-type, later
  switched to image-type); a single fresh "add as image button" would never produce that,
  so the generator emits the clean result instead (sanity-checked: exactly 16 new
  `imagesector` keys). **Checkbox** (`checkbox_show=True`): same mechanism, but no real
  checkbox-enabled button exists anywhere in the reference project, so this one is
  sanity-checked only, not confirmed — flagged as needing a real reference file the same
  way the user added one for background-color in Phase 3, if/when it matters. All 4
  configurations round-trip clean in `generator/_test_output/phase4_smoke_test.py`.
  `docs/architecture/04-ch5-schema.md` updated with the full derivation writeup.
- 2026-09-08: **Phase 4 (add a CH5 component) — "Ch5 Button", default configuration,
  DONE.** User asked "if you do not address the 90 additional attributes how can I fully
  test component integration?" after an initial pass found a real button carries ~112
  attributes from 3 different sources, not 1 — pushed the research further rather than
  shipping a partial slice. Findings: `schema.json` (the ch5-button web component's own 60
  runtime attributes) is NOT what a freshly-dropped button's `[Elements.Attributes]` looks
  like; `component-context.json`'s `ch5-button.defaults.attributes` (24 keys) IS the real
  base payload (confirmed order-for-order against a real button); the ~80
  `ccid_sync_{state}_{sector}sector_{property}` "Advanced Style Manager" attributes are
  generated by **client-side TypeScript**
  (`pd-ch5-components/mixins/common/commonButtonTraitsMixins.ts::setSyncData`, real source
  present in `C:\Git\CCIDE`, not compiled/obfuscated) — traced the exact algorithm and
  found its authoritative data source is `sass-schema.json`'s per-tag sector list (NOT
  `component-context.json`'s `classToVariableMapping`, which has a different, over-broad
  property shape). Built `generator/sdk.py` (locates and reads an installed SDK's
  `schema.json`/`component-context.json`/`sass-schema.json` from
  `%APPDATA%\crestron-construct\AppStorage\data\ui\sdk\<version>\data\`) and
  `generator/ch5_button.py` (`build_default_button_element` /
  `build_sync_attributes` — the sync-attribute derivation is written generically off
  `sass-schema.json`'s shape, not button-specific, so should carry over to other component
  types). Verified: `generator/_test_output/phase4_smoke_test.py` — page-with-button
  round-trips byte-identical, AND the generated button's 112 attributes match a real
  Construct-authored plain button (`Component - Button.cuig`'s "Button1", id `i9nb`)
  **exactly** — same 112 keys in the same order, 0 value mismatches. Written up in
  `docs/architecture/04-ch5-schema.md` (includes the full derivation + flagged gaps: only
  the plain/default button variant is covered, not icon/image/checkbox/advanced-mode
  buttons; common wiring keys' universality across component types is unconfirmed beyond
  button). `01-index.md` updated. Also generated one into the real on-disk verification
  project (`C:\Solutions\ClaudeGenTest\GenTestProject\MainPage.cuig`) for the user to
  check in Construct.
- 2026-09-08: **End-to-end manual verification project generated in Construct's own
  Solutions folder**, at the user's request, to sanity-check Phases 1-3 outside the
  harness before starting Phase 4: `C:\Solutions\ClaudeGenTest\ClaudeGenTest.csln` ->
  project `GenTestProject` (CH5:2.18.0 SDK, light theme, TSW-1070 landscape resolution,
  matching real `Components.cuip` values) -> page `MainPage.cuig` (start page) -> widget
  `MyWidget.cuiw` (400x300) added to the page via the real `<ch5-template>` reference.
  Every step passed `harness/compare.py`'s round-trip check. User confirmed it looks good
  after opening in Construct. User also asked about adding multiple landscape/portrait
  resolutions to a project; deferred to Phase 5 (device catalog / orientation semantics
  are explicitly out of scope until then) at the user's direction, rather than guessing at
  unconfirmed device dimensions.
- 2026-09-03: **Background color verification against user-added reference files.**
  User added `Page with Bkd Color.cuig` / `Widget with Bkd Color.cuiw` to
  `C:\Solutions\ClaudeSamples\Components` specifically to test this. Confirmed
  `DisplayBackgroundColor`/`BackgroundColor` attribute placement was already correct
  (matches source exactly, no fix needed) — but the test **did** catch a real bug:
  `generator/page.py::default_widget_html_css`'s root `widgetContainer` element was
  missing `Name=""`/`Status=""`/`Content=""`/`Draggable=False`/`Copyable=False`, all of
  which `CreateNewWidgetHandler.cs`'s real payload sets explicitly (not null) — fixed
  and now matches the real file's element field-for-field. Also resolved (partially) an
  open question: even with a background color set, a page's `{Html}`/`{Css}` stay
  completely empty — the previously-unexplained `#<id>{background-color:#ffffff;}` rule
  seen on other pages is confirmed **unrelated** to this feature (still don't know what
  it is, but now know it's not this). One new open, non-blocking flag: the widget's
  color value has 8 hex digits (`#1900ffff`) vs. the page's 6 (`#ff0000`) — an alpha
  channel is suspected but its byte order (`RRGGBBAA` vs `AARRGGBB`) is unconfirmed;
  doesn't matter for the generator since color strings are passed through verbatim,
  never interpreted. All of this is now permanent regression coverage in
  `generator/_test_output/phase3_smoke_test.py`, not just a one-off check. Written up
  in `docs/architecture/03-page-widget-creation.md`.
- 2026-09-03: **Phase 3 (create page / create widget / add widget to page) complete.**
  Source-grounded in `PersistenceHelper.CreatePageSource` (two overloads: page vs.
  widget — confirmed the widget overload's 4-key `{PageAttributes}` order matches the
  real `Widget.cuiw` exactly), `CreateNewPageHandler.cs` (brand-new page = zero
  elements, empty Html/Css), `CreateNewWidgetHandler.cs` (brand-new widget's default
  `<div id="...">` + sizing CSS + bare `widgetContainer` element), and
  `AddHtmlViewDependencyHandler.cs` (the page→widget dependency graph is in-memory
  bookkeeping only — the actual persisted proof of "widget added to page" is the
  `<ch5-template>` element itself, confirmed attribute-for-attribute against the real
  `Widget on Page.cuig`, including `templateid = "w" + widget's own Id`). Derived —
  not guessed — the `[[Elements]]` nesting/blank-line rule directly from
  `ElementSource.cs`'s field declaration order: this **structurally explains** v1's
  empirically-discovered "BUG #2" (a widget container's own trailing
  `[Elements.Attributes]` landing after all its children's blocks) as a natural
  consequence of `Components` being declared before `Attributes`, rather than a
  special case to patch around. Built `generator/elements.py` (`Element` +
  `to_toml_lines`), `generator/page.py` (page/widget attribute builders, widget-default
  HTML/CSS, `make_widget_reference`, `write_cuig`). **Found and fixed a real bug while
  building a nested-element test**: the TOML string escaper only handled `\`/`"`, not
  control characters — a raw embedded newline (as in a real `Content = "\n..."` value)
  produced invalid TOML that `tomllib` refused to parse. Fixed by centralizing escaping
  in a new `generator/toml_util.py`, now imported by every writer instead of each
  module keeping its own copy. Verified: empty page/widget both round-trip and match
  real reference-file attribute order exactly; add-widget-to-page's `Ch5 Template`
  element matches the real file's `Type`/`Attributes` key set exactly; a synthetic
  3-level nested tree (`widgetContainer → Button → textnode`) proves the nesting +
  blank-line + escaping rules generally, not just against the one sample file. Written
  up in `docs/architecture/03-page-widget-creation.md`; `01-index.md` updated.
  Remaining known gap (flagged, not blocking): exactly when/how the `widget-container`
  CSS class + checkerboard background get added to a widget after its bare creation
  payload is untraced.
- 2026-09-03: **Phase 2 (create solution / create project) complete.** Source-grounded
  in `UiEditor.Server\Helpers\PersistenceHelper.cs::WriteProject` (exact ordered
  `{ProjectAttributes}` key list + omission rules), `CreateProjectHandler.cs` (defaults:
  SDK auto-detect, theme color, component mode, schema version), and
  `Solution.Server\Dao\SolutionDao.cs`/`AddProjectHandler.cs` for `.csln`. Built
  `generator/project.py` (`build_project_attributes` + `write_cuip`) and
  `generator/solution.py` additions (`write_solution`, `create_solution`,
  `add_project_to_solution`). **User caught a gap**: project creation must support
  *multiple* themes and *multiple* device resolutions selected at once, not just one of
  each — reworked `build_project_attributes` to take `themes: list[str]` (+
  `default_theme`) and `resolutions: list[dict]`, correctly producing comma-joined
  `ProjectThemeIds`/`DeviceResolutionIds` and a multi-entry `{DeviceResolutionSource}`
  JSON array. Verified programmatically (not eyeballed): generated `.cuip`'s
  `{ProjectAttributes}` key **order** matches
  `C:\Solutions\ClaudeSamples\Components\Components.cuip` exactly (17/17 keys), and
  `{DeviceResolutionSource}` entry key set matches exactly. Generated `.csln`'s
  structure matches `ClaudeSamples.csln` exactly (top-level, `_fileMetadata`,
  `_solution`, `_projects[0]` keys). Full end-to-end smoke test
  (`generator/_test_output/phase2_smoke_test.py`: create solution → create project with
  2 themes + 1 resolution → add to solution → re-read and confirm correct folder
  resolution) passed. Also resolved the Phase 1 "active project persisted state" open
  question while reading `CreateSolutionHandler.cs`: Construct has a `.cse` sidecar
  file, but it's Explorer-tree open/closed UI bookkeeping, not a single "active
  project" flag — our own `select_active_project` remains the right owner of that
  concept for this skill. Written up in
  `docs/architecture/02-project-creation.md`; `01-index.md` updated. Remaining known
  gap (flagged, not blocking): the device catalog and `orientation` enum semantics
  are unconfirmed — deferred to Phase 5.
- 2026-09-03: **Phase 1 (Foundation) complete.** Built `harness/compare.py`: a
  section-header splitter for `.cuip`/`.cuig`/`.cuiw`/`.cuia` based on the exact
  header-per-line convention confirmed in every known-good file examined (not yet
  stress-tested against Construct's more permissive in-content header scan — see the
  file's own docstring). Round-trip identity (parse -> reassemble -> byte-compare)
  verified **byte-for-byte across every file** in three real projects: all of
  `C:\Solutions\ClaudeSamples\Components` (23 `.cuig`, 2 `.cuiw`, 1 `.cuip`, 1 `.cuia`),
  all of `C:\Solutions\ClaudeSamples\ClaudeCustomModeProject` (4 `.cuig`, 1 `.cuiw`,
  1 `.cuip`), and all 36 files of v1's
  `ConstructUISkill\samples\CrestronDesignIdeas\BasicTemplate_v1_0_2` — including
  several files well over 400,000 characters, far past the 70,000-char threshold where
  Construct's own `UiEditorPageDao` has to work around a real Nett TOML
  stack-overflow bug (see `docs/architecture/00-overview.md`). Also built
  `generator/solution.py` (`.csln` JSON reader + `select_active_project`, spec §7):
  verified against `C:\Solutions\ClaudeSamples\ClaudeSamples.csln` — correctly resolves
  a named project to its real folder, and correctly refuses to guess when a solution
  has multiple projects and none was named.
- 2026-09-03: Planning session completed and approved. Folder structure created
  (`docs/architecture/`, `harness/`, `generator/`, `skills/`). Two source-code research
  passes over `C:\Git\CCIDE` confirmed the serialization mechanics for `.csln`/`.cuip`/
  `.cuig`/`.cuiw`/`.cuia`/`.cuib`/`.cuic` (DAOs, models, TOML library = Nett 0.15.0,
  JSON via `System.Text.Json`), plus contract generation, CH5 SDK schema
  (`schema.json`/`component-context.json`, machine-readable per-SDK-version), themes,
  fonts, hard buttons, and language files. Findings written to
  `docs/architecture/00-overview.md` and `01-index.md`. Decisions locked: fully
  independent codebase from v1; architecture docs written just-in-time per phase, not
  all upfront; generator language is Python (default, flagged to user given source is
  C#). Full plan on file at `C:\Users\aseferian\.claude\plans\jolly-coalescing-quiche.md`.
