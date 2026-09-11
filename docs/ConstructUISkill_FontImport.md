# ConstructUISkill_FontImport.md: Construct UI Skill Font Import Feature

This file will provide details on how the Construct UI generator skill - Font Import feature will work.

## 1. Webfonts Folder
Font families that can be used in Construct are centrally located in the Webfonts folder. This folder is Windows and macOS specific.

**Location, confirmed from `C:\Git\CCIDE\Crestron.IDE\AppHost\Crestron.IDE\Common\Utils\EnvironmentUtility.cs`:** `<Documents>/Crestron/Crestron Construct/Webfonts` — the same formula on both platforms (both call .NET's `Environment.GetFolderPath(SpecialFolder.MyDocuments)`; only what that call resolves to differs per OS). Confirmed against this machine's real, running install: its own startup log (`AppStorage\Logs\jsonlog_*.json`, `"EnvironmentUtility solutionsPath: ..."`) and the folder's actual on-disk contents both agree.

- **Windows:** `MyDocuments` is *not* simply `%USERPROFILE%\Documents` — it is whatever the registry's `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders\Personal` value says. OneDrive's "back up your Documents folder" rewrites that value; confirmed on this machine, where it resolves to a OneDrive-redirected path (`...\OneDrive - Crestron Electronics\Documents\...`), not the plain profile folder. `generator/fonts.py::documents_path()` reads that registry key directly, falling back to `~/Documents` if it's unreadable.
- **macOS:** `~/Documents` (Apple's `NSDocumentDirectory`, which is what `SpecialFolder.MyDocuments` maps to there — no OneDrive-style redirection concept applies).

**"Everyone" vs "Current User" install — resolved: it does not matter.** No install-scope branching exists anywhere in the webfont path; `webFontDirectory` derives entirely from `SpecialFolder.MyDocuments`, which is inherently per-*user*, not per-install — every user has their own Documents folder regardless of how the app itself was installed. No shared/all-users fallback exists in the font-scanning code (checked for a `CommonAppStoragePath`-style equivalent, the way `resolutionData.json` has one under AppStorage; none exists here). So: the Webfonts folder is always the *currently logged-in user's own*.

  One loose end, not fully resolved: `EnvironmentUtility.cs` carries a comment on `solutionsPath` — *"this is set to the default but can be overridden by user settings file"* — but no code anywhere in the repo actually performs such an override (`SolutionsPath =` and `SetSolutionsPath`/`ChangeSolutionsPath`-style searches turned up nothing beyond the one default-assignment site). Likely stale documentation rather than a live mechanism, but flagged rather than assumed dead.

## 2. Supported File Types
The following web font file types are supported by Construct:

* .eot
* .woff2
* .woff
* .ttf
* .svg

**Filename rule, confirmed and made precise** (`CommonThemeAndFontHelper.cs::InvalidFontCharacter`/`InvalidFontLength`, `PageDesigner.Common\Constants.cs`): the font family name (filename without extension) must match `Constants.AssetNameValidationRegex`:

```
(^[a-zA-Z\s]+[a-zA-Z]|^[a-zA-Z]+[a-zA-Z0-9 _-])[a-zA-Z0-9-_ ]*$
```

In plain terms: must **start with a letter**, then any run of letters/digits/spaces/underscores/hyphens. No leading digit, no leading special character (confirming the original assumption) — and no other punctuation anywhere in the name (periods, ampersands, etc. all fail this too). Additionally, length must be **2–31 characters** (`WebFontConstants.MinLength`/`MaxLength`). The filename must be renamed to satisfy this before import if it doesn't already. Implemented as `fonts.py::validate_font_family_name`/`sanitize_font_family_name`.

**The font file itself, not just its filename, determines the family name Construct exposes.** `ThemeAndFontUpdateHandler.cs`/`ThemeAndFontLoaderHandler.cs` group discovered files by `Path.GetFileNameWithoutExtension(f)` — i.e. Construct currently trusts the FILENAME as the family name, not the font's internal name table. `fonts.py::import_font_file` relies on exactly that: it writes `<family_name><extension>`, discarding any original filename entirely, so the exposed name is always the one that was validated — not whatever name a download or a user's own file happened to carry.

## 3. Webfont Data File
Confirmed: there is no webfont data/cache file. `ThemeAndFontUpdateHandler.cs` and `ThemeAndFontLoaderHandler.cs` both perform a live directory scan (`GetAllFiles(webFontDirectory)`) — nothing indexes the Webfonts folder between scans.

**CONFIRMED BY LIVE TEST (user, 2026-09-11): you have to close and reopen Construct itself** to pick up a new font, not just the project. An earlier source-only trace suggested "reopen the project" might be enough; that inference was wrong, and the live test is the authority here, not the trace.

What the trace actually established, precisely: the rescan is dispatched from exactly one place client-side, `PageDesignerManager.InitializeComponent()` (`PageDesigner.Client\PageDesignerManager.cs:87`, `dispatcher.Dispatch(new ThemeAndFontLoaderAction())`) — a Blazor component **lifecycle** method, not a named "app launch" or "project open" event. Whether reopening a project *within one already-running Construct instance* tears down and rebuilds that component (and so re-fires the scan) isn't something source alone settles — it depends on how the editor host is structured internally. That is exactly the ambiguity the live test resolved: empirically, it does not pick up a new font that way. Only a full close/reopen of Construct does. **The skill must tell users to close and reopen Construct**, full stop.

## 4. Skill Use
Users need to be able to ask the skill to find, install and apply fonts.

Examples of online free font websites:
* Google Fonts: https://fonts.google.com/ — **BUILT** (`generator/google_fonts.py`). Search via `fonts.google.com/metadata/fonts` (keyless, undocumented — the official Developer API needs an API key the user would have to create/manage, chosen against); download the real `.ttf` via the official `fonts.googleapis.com/css2` endpoint. Both verified live: "Roboto Slab" downloads as 101,564 real bytes with valid TrueType magic; a nonexistent family raises clearly rather than returning garbage.
* Fontsource: https://fontsource.org/ — **BUILT** (`generator/fontsource.py`), **restricted to fonts NOT already covered by Google Fonts**. Measured the real catalog: 1,980 of 2,100 entries are `type: "google"` — literal duplicates of the same fonts the Google module already searches. Only the 120 `type: "other"` entries (real, distinctly-licensed fonts — OFL-1.1, Apache-2.0, CC0-1.0) are searched here, per the user's call once that overlap was measured: "if they are duplicates of Google Fonts no reason to add this." Search: `api.fontsource.org/v1/fonts` (keyless). Download: `cdn.jsdelivr.net/fontsource/fonts/<id>@latest/<subset>-<weight>-<style>.ttf` (jsDelivr's public CDN, keyless). Verified live: "Adwaita Sans" downloads as 513,028 real bytes; "Roboto" is correctly refused here as Google-sourced.

