# Contracts (`.cuic`) — Phase 6

**We never author a `.cuic`.** Construct generates it, and the whole of our job is to
leave two things in the project files so that it does:

1. the contract-capable signals enabled on each component, and
2. `ContractIsStale = "true"` in the `.cuip`.

That is the entire mechanism. The `.cuic` itself is a large generated artifact (~16 MB on
a real template) whose signal paths carry a join-allocation table; hand-editing it would
mean reconciling join ranges, and nothing requires us to.

Implemented in `generator/contracts.py`. Source references below are to `C:\Git\CCIDE`.

## 1. `ContractIsStale` — the regeneration trigger

`Behaviors\ProjectOpenBehavior.cs:72-99` is the whole story: on project open, if the
project's `ContractIsStale` is false it returns immediately; otherwise it schedules
contract generation, sets the flag back to false and saves the project.

| Where | What |
|---|---|
| `UiEditor.Common\Constants.cs:507` | the attribute name, `"ContractIsStale"` |
| `Models\UiEditorProject.cs:76` | `bool ContractIsStale` |
| `Commands\Solution\OpenProjectHandlerHelper.cs:336-338` | read from the `.cuip` on load, JSON-deserialized |
| `Helpers\PersistenceHelper.cs:96,713` | written back on save |
| `Behaviors\ContractGenerationBehavior.cs:65-77` | Construct sets it true itself when the design changes |

`generator/project.py::build_project_attributes` already writes `"true"` for every
newly-created project, so a fresh project needs nothing extra. For an existing project,
`contracts.py` exposes two entry points sharing one definition:

- `set_contract_stale(attrs)` — for callers already holding the project attribute list
  and about to write it (`add_resolutions_to_project` uses this).
- `mark_contract_stale(cuip_path)` — read/modify/write for callers that are not.
  Preserves every other byte, `FileMetadata` timestamps included: `Modified` belongs to
  whoever actually edited the design.

**Call it after any change the contract is derived from** — signals enabled or disabled,
components added or removed, pages/widgets renamed (object names *are* the contract's
signal names), or a resolution added (reflow moves components).

## 2. Enabling a signal on a component

A join-carrying attribute whose value is the literal `"Contract Enabled"` becomes a
contract signal. Construct writes that exact string itself
(`Helpers\ContractGenerationHelper.cs:1177`).

The consuming path is
`Services\Contract\ComponentStrategies\SimpleComponentStrategy.cs::CreateComponent` →
`ContractGenerationHelper.GetJoinsFromAttributes` (`:1283`), which walks *every* attribute
on the element and creates a join for each one that maps to a join property and has a
non-empty, non-numeric value. Note the sentinel is not strictly required by that code —
a user-typed signal name is the other legitimate case — but `"Contract Enabled"` is the
contract path and the one we write.

Confirmed in a real hand-authored file
(`C:\Solutions\CustomerIssues\i12 Multicam\IV Auto-Switch Set ID.cuig`): a contract-enabled
button carries exactly `pd-receivestateenable`, `sendeventontouch` and
`pd-receivestateselected` set to `"Contract Enabled"`, and no other signal wiring.

### Which attributes, and under what name

Both questions are answered by SDK data, so `contracts.py` hardcodes nothing
per-component:

- **Which:** an attribute that is a join in `schema.json` AND has a signal entry in
  `component-context.json`. A signal entry is one whose `category` starts with `Send ` or
  `Receive ` ("Send Digital Command", "Receive Analog Feedback", ...). The entry is looked
  up on the component's own tag first and then on the shared `global` entry -- exactly
  what `Helpers\JoinNameProviderHelper.cs::GetAttributeContractInfo` does, in its own
  words: *"search more specific first, then global"*.
- **Under what name:** those context keys already carry the storage prefix. The rule
  behind them (`PageDesigner.Server\Providers\JoinPropertyProvider.cs:151`, and the
  client-side twin at `pd-metadata-resolver\MetaDataResolver.ts:201`) is that a
  `direction="state"` join is stored as `pd-<name>`, so the design-time canvas is not
  driven by live CH5 signals, while a `direction="event"` join keeps its bare name.
  Construct strips a leading `pd-` before any schema lookup
  (`JoinPropertyProvider.GetCh5AttributeDef`).

### Two gates that look right and are not

Both of these shipped wrong first, and were caught only when the user set the intended
signals across the reference project and some turned out to be unnameable:

- **`extenderPosition` is not the signal gate.** It is tempting -- `CreateProjectComponent`
  does test `SignalDetails.ExtenderPosition > 0` -- but that governs the project-level
  extender, not what a component can expose. `GetJoinsFromAttributes`, which actually
  turns attributes into joins, needs only a resolvable `SignalDetails`. `ch5-dpad` and
  `ch5-keypad`'s `sendeventonclickstart` ("Digital Start") carry no `extenderPosition`
  at all -- they are marked `removeOnContractUse` -- yet the reference project enables
  them. `ContractSignal.extender_position` is 0 for these; it is an ordering hint, not a
  filter.
- **A tag's own `attributeProperties` is not the whole list.** `ch5-color-picker`
  declares no signal entries whatsoever, and all six signals the reference enables on it
  come from `global`. Reading only the per-tag entry also cost `ch5-button` five of its
  ten signals, including `Enable` -- which a real hand-authored button in
  `C:\Solutions\CustomerIssues\i12 Multicam` has enabled. A global entry applies only
  where the tag's own schema has that join, so colour and animation signals do not leak
  onto components that lack them.

`contract_signals()` cross-checks every context key against `schema.json`'s own join
direction and raises if they disagree — writing the wrong one would produce an attribute
Construct silently ignores, with an empty contract as the only symptom. All 238
schema-backed signals in SDK 2.18.0 agree.

### Signal names are not attribute names

Each signal's contract name comes from `contractFriendlyName` where present, else
`friendlyName` — *not* from the attribute spelling. Two cases show why this matters:

- `ch5-button`'s `pd-receivestateshow` displays as "Visibility" but contracts as
  **"Visibility_fb"** (its send-side twin `sendeventonshow` is the plain "Visibility").
- `ch5-slider`'s `pd-receivestatevalue` is **"Lower Touch fb"**, not "Value".

`resolve_signals()` therefore accepts either the friendly name or the raw attribute, and
raises listing the valid options rather than silently skipping a name it does not know.

### ch5-button's ten signals

| Position | Signal | Attribute | Source |
|---|---|---|---|
| 1 | Visibility | `sendeventonshow` | own |
| 1 | Visibility_fb | `pd-receivestateshow` | own |
| 1 | Indirect Text | `pd-receivestatelabel` | global |
| 1 | Indirect Rich Text | `pd-receivestatescriptlabelhtml` | global |
| 2 | Enable | `pd-receivestateenable` | global |
| 2 | Icon | `pd-receivestateiconclass` | global |
| 3 | Press | `sendeventontouch` | own |
| 3 | Selected | `pd-receivestateselected` | own |
| 6 | Icon URL | `pd-receivestateiconurl` | global |
| 9 | Mode | `pd-receivestatemode` | own |

Signals sharing an `extenderPosition` are one logical group — `Selected` names `Press` as
its `groupName` — so emission orders the send event ahead of its own feedback.

## Defaults per component type

`DEFAULT_SIGNALS` records what a newly-generated component of each type exposes,
transcribed from the user's reference project, where they set the intended signals on
every component by hand (2026-09-10). `contracts_task6_defaults_test.py` recomputes the
table from those files on every run, so the reference stays the ground truth rather than
a one-time copy. For a button that is `("Press", "Selected")`.

Six types deliberately expose none (`NO_SIGNALS_BY_DESIGN`): video, video switcher,
subpage reference list, background, datetime and qrcode. Each of them *has* signals
available -- this is a judgement that a generated instance should not enable any. A type
absent from the table defaults to `()` on the same reasoning: no signals is always a
valid component, whereas guessing puts joins in a contract nobody asked for.

### Naming signals

Three tags have two distinct signals sharing one name (`ch5-button-list`'s
"ItemSelected", `ch5-spinner`'s "Selected Item", `ch5-video-switcher`'s "_Label").
`resolve_signals` raises on those rather than picking one -- picking would silently
enable the wrong signal -- and the raw attribute name always disambiguates.

## Gotchas found while building this

- **`component-context.json` can name a signal `schema.json` does not have.**
  `ch5-media-player`'s `pd-receivestateusemessage` has no `schema.json` attribute at all,
  yet the hand-authored reference project
  (`C:\Solutions\ClaudeSamples\ClaudeCustomModeProject\Page3.cuig`) writes it as a live
  `"Contract Enabled"` signal. A schema entry is corroboration, not a requirement;
  `ContractSignal.schema_backed` records which, and the test pins the exception set so a
  new SDK version changing it is a visible failure rather than a silent one.
- **Not every schema element has a context entry.** The nested sub-element types
  (`ch5-button-list-mode`, `ch5-button-label`, …) are configured through their parent's
  traits and have no signals of their own.
- **`component-context.json`'s `global` entry is not an element.** It holds shared
  attribute metadata; `contract_signals("global")` raises rather than returning signals
  that belong to no component.
- **Complex components do not use this path.** `SimpleComponentStrategy` handles anything
  without `CompilerFlags.IsComplex`; dpads, keypads, button lists, widget lists, tab
  buttons, video switchers and media players each have their own strategy (see
  `Services\Contract\ComponentStrategies\`). Some force signals on regardless of the file
  — `DpadStrategy.cs:91` and `KeypadStrategy.cs:94` set `ButtonPress` to `"Contract
  Enabled"` themselves. Enabling signals on those types is therefore **not** covered by
  Phase 6's button work and needs its own verification when those components are built.
- **`ccid_linkSendReceive` is not contract enablement.** Every component in the reference
  files carries it whether or not any signal is enabled; it is the UI-level link that
  toggles a matching receive when you enable a send
  (`pd-utils\trait-interactions.ts:109,203`).

## Attribute placement

Signals are written **last**, after the `ccid_sync_*` block and any icon keys. Confirmed
against all six real buttons in the reference project, every one of which ends with
exactly `sendeventontouch`, `pd-receivestateselected`. An earlier version placed them
between the common wiring and the sync block, flagged in the code as a guess; it was the
wrong guess, and `phase4_smoke_test`'s exact key-order diff against the real `Button1`
now passes with the default signals present rather than suppressed.
