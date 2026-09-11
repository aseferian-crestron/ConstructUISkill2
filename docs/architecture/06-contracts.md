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

- **Which:** `component-context.json`'s per-tag `attributeProperties` entries that carry
  an `extenderPosition`. This matches Construct's own gate in
  `ContractGenerationHelper.CreateProjectComponent` (`SignalDetails.ExtenderPosition > 0`).
  In SDK 2.18.0 that is 28 tags and 157 signals.
- **Under what name:** those keys already carry the storage prefix. The rule behind them
  (`PageDesigner.Server\Providers\JoinPropertyProvider.cs:151`, and the client-side twin
  at `pd-metadata-resolver\MetaDataResolver.ts:201`) is that a `direction="state"` join is
  stored as `pd-<name>`, so the design-time canvas is not driven by live CH5 signals,
  while a `direction="event"` join keeps its bare name. Construct strips a leading `pd-`
  before any schema lookup (`JoinPropertyProvider.GetCh5AttributeDef`).

`contract_signals()` cross-checks every context key against `schema.json`'s own join
direction and raises if they disagree — writing the wrong one would produce an attribute
Construct silently ignores, with an empty contract as the only symptom. All 132
schema-backed signals in SDK 2.18.0 agree.

### Signal names are not attribute names

Each signal's contract name comes from `contractFriendlyName` where present, else
`friendlyName` — *not* from the attribute spelling. Two cases show why this matters:

- `ch5-button`'s `pd-receivestateshow` displays as "Visibility" but contracts as
  **"Visibility_fb"** (its send-side twin `sendeventonshow` is the plain "Visibility").
- `ch5-slider`'s `pd-receivestatevalue` is **"Lower Touch fb"**, not "Value".

`resolve_signals()` therefore accepts either the friendly name or the raw attribute, and
raises listing the valid options rather than silently skipping a name it does not know.

### ch5-button's five signals

| Position | Signal | Attribute | Category |
|---|---|---|---|
| 1 | Visibility | `sendeventonshow` | Send Digital Command |
| 1 | Visibility_fb | `pd-receivestateshow` | Receive Digital Feedback |
| 3 | Press | `sendeventontouch` | Send Digital Command |
| 3 | Selected | `pd-receivestateselected` | Receive Digital Feedback |
| 9 | Mode | `pd-receivestatemode` | Receive Analog Feedback |

Signals sharing an `extenderPosition` are one logical group — `Selected` names `Press` as
its `groupName` — so emission orders the send event ahead of its own feedback.

`DEFAULT_BUTTON_SIGNALS = ("Press", "Selected")`: what a new button gets unless the caller
says otherwise, `()` disabling contracts entirely (the state of a freshly-dropped button
in Construct's own UI). An enabled signal nobody wires still consumes joins from the pool,
so the rest stay opt-in.

## Gotchas found while building this

- **`component-context.json` is authoritative over `schema.json`, not the reverse.**
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

Signals are written between the common wiring (`devicesVisited`) and the `ccid_sync_*`
block. That position is **our choice, not confirmed against a Construct-authored file** —
real samples place signal attributes inconsistently, and order within an element matters
only to our own reference diffing, not to Construct, which reads the block as TOML.
