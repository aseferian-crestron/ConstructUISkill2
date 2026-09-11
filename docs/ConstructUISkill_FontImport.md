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

In plain terms: must **start with a letter**, then any run of letters/digits/spaces/underscores/hyphens. No leading digit, no leading special character (confirming the original assumption) — and no other punctuation anywhere in the name (periods, ampersands, etc. all fail this too). Additionally, length must be **2–31 characters** (`WebFontConstants.MinLength`/`MaxLength`). The filename must be renamed to satisfy this before import if it doesn't already.

**The font file itself, not just its filename, determines the family name Construct exposes.** `ThemeAndFontUpdateHandler.cs`/`ThemeAndFontLoaderHandler.cs` group discovered files by `Path.GetFileNameWithoutExtension(f)` — i.e. Construct currently trusts the FILENAME as the family name, not the font's internal name table. This module's own `fonts.py::webfont_names()` (built for the "use an existing library font" slice) already relies on exactly that filename convention and is confirmed correct for **discovering already-present fonts**. For **importing a brand-new file**, if the filename does not match the font's actual internal family name, Construct will still expose it under the filename, not the font's "real" name — worth stating explicitly to whoever renames files before import, since a mismatch won't error, it'll just surface under the wrong name.

## 3. Webfont Data File
Confirmed: there is no webfont data/cache file. `ThemeAndFontUpdateHandler.cs` and `ThemeAndFontLoaderHandler.cs` both perform a live directory scan (`GetAllFiles(webFontDirectory)`) — nothing indexes the Webfonts folder between scans.

**CONFIRMED BY LIVE TEST (user, 2026-09-11): the original assumption was right — you have to close and reopen Construct itself** to pick up a new font, not just the project. My source-only trace suggested otherwise (see below) and that inference was wrong; the live test is the authority here, not the trace.

What the trace actually established, and why it was insufficient on its own: `ThemeAndFontLoaderCmd` performs the same live-scan logic and does fire from `OpenProjectHandlerHelper.cs` (*"Font data is populated asynchronously by ThemeAndFontLoaderCmd... via OpenMostRecentSolution"*) and is reachable via a client endpoint (`PageDesigner.Server\EndPoints\PageDesignerEndpoint.cs: GetCommand<ThemeAndFontLoaderCmd>`) — but tracing *that a trigger site exists* is not the same as confirming *it fires, and actually refreshes the font list, when reopening a project inside an already-running Construct instance*. Most likely explanation: that population point is tied to the solution/app launching, or `PageDesignerServerState`'s cached font data survives a project close/reopen within one running server session and is only rebuilt on a fresh process start. Either way: **the skill must tell users to close and reopen Construct**, full stop — not the lighter "reopen the project" this doc suggested for a few hours based on source alone.

## 4. Skill Use
Users need to be able to ask the skill to find, install and apply fonts.

Examples of online free font websites:
* Google Fonts: https://fonts.google.com/
* Fontspace: https://www.fontspace.com/

