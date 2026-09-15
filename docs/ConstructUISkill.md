# ConstructUISkill.md: Construct project generator

This file will provide details on how the Construct UI generator skill will work. Another skill was started using a different method and was not progressing.

With a new start, we will change the way AI learns about the Construct data files. Instead of grepping existing data files from reference projects, the actual Construct source code will be used to determine how Construct data files are created and updated.

## 1. Construct Source Code Location and Architecture Analysis
The Construct source code is located here: C:\Git\CCIDE. A complete source code architecture should be performed to understand how the various data files (defined below) are created and updated.

## 2. Feature Description
This skill will allow users through natural language, the ability to create and update Crestron Construct UI projects.

Users can provide the location of existing Construct solutions or projects. If a solution folder is provided, the user must state which project in the solution folder they want to work on. The skill must move the active folder to the project folder so work can be performed.

The following information is required in order to create a Construct project. If the user does not provide all of the required information, the skill must prompt for it:

* Project name
* Zoom or UI project
* Will this project be added to an existing solution?
  * If yes, where is the existing solution located?
  * If no, what solution name should be used and where should it be located?
* What user interface devices should be supported?
  * If mobile has been stated, do you need landscape and portrait designs supported?
* What type of theme should ne used?
  * Construct default light/dark?
  * Custom theme file?
  * Theme should be pulled from the supplied design guide
* What should the design be based on?
  * Design ideas basic template?
  * Provided design sample document

If the above information is not provided in the initial prompt, the skill must ask for all of the above information.

* The skill needs to check if Construct is installed and make sure the UI Plugin is installed.
* The skill will need to determine the latest version of the CH5 SDK that is installed since creating a project requires the user to specify the SDK version to use. The skill should auto-select the latest SDK installed.

## 3. Construct UI Project Folders and Files
This section will define the folder and file structures for a Construct UI project.

* All Construct UI projects are children of a solution. A solution can contain multiple UI projects, but each project name must be unique within the solution.
* The solution folder will have the same exact name of the solution.
  * When multiple solutions are contained within a parent folder, the skill will need to enforce unique solution/folder names.
* All UI project files are contained within a sub-folder of the solution's folder. The sub-folder will have the exact name of the project.
  * When multiple projects are contained within a solution folder, the skill will need to enforce unique project/folder names.

Solution Files
* .csln: Main solution data file.

UI Project Files
* .cuip: Main project data file.
* .cuib: Hard button data file. **Out of scope** (user, 2026-09-11: not needed in the skill).
* .cuic: Communication contract file
* .cuig: Page data file.
* .cuiw: Widget data file.

UI Project Image Assets
Project image assets are always in a separate sub-folder "assets" that is located within the project folder.

Within the "assets" folder are two files for each asset:
* image asset file (.png,.jpg,.bmp,.svg,.gif)
* .cuia: Image asset data file

## 4. Construct Project Structure
Construct projects using the CH5 SDK contain pages and widgets. Widgets are a collection of CH5 components that can be used across many pages.

Projects are typically created such that widgets are used for lighting, shades, power options, device controls, audio adjustments, phone, etc. and then those widgets are added to one or more pages in the project.

Due to DOM size guidelines, Construct projects utilize a multi-page design as opposed to a single page with many widgets. I.E. When a footer menu contains buttons for Power, Lights, Shades, Phone, Camera, etc. those selections will open pages. A widget may be developed for each of those types of controls (for ease of management and extensibility), but then the widget would be placed on the page.

## 5. Project Creation
When the skill creates a project, it should utilize a page-based design where a page is generated for each type of requested control.

If the design requires a footer or header be utilized, those objects should be created as widgets and then be added to every page in the project.

Footers commonly contain menu items like: Power Options, Lighting Controls, Shades Controls, Camera Controls, Phone Controls, Video Call Controls, Audio Controls, Privacy Controls, Volume Controls. Those types of controls in the footer are mutually exclusive so that only one can be selected at a time and when one is active, it can be closed by either selecting it again or pressing a close button on the page.

Headers commonly contain items like: Room Name, Time/Date, Branding Logo.

Footers and Headers are always widgets that are added to every page in the project.

Construct projects can support multiple resolutions and orientations per project.

**Page-based project rules** (user, 2026-09-11):
* The project's Override Theme Color must always be enabled and set to black
  (`OverrideThemeColor="True"`, `ThemePageColor="#000000"`) -- without it, the
  default theme color flashes between page flips, which is less pleasing than
  black. See `generator/project.py::build_project_attributes`.
* A solid background color at the page or widget level uses that page/widget's own
  local background color control (`DisplayBackgroundColor`/`BackgroundColor` in
  `{PageAttributes}`), not a separate mechanism.
* A custom background IMAGE uses an image component at the lowest z-order, at
  (0,0), sized to the full page/widget -- kept there by the reflow logic across
  every resolution the project has, including ones added later. If the project
  also needs the video component, the background component is used instead of the
  image component (an image component conflicts with video). See
  `generator/background.py`.

**Hard requirement**: Any time a common widget is added to all pages, the Global Contract property for the widget must be set true.

**Hard requirement** (user, 2026-09-15): local page-flip programming is not used
for navigation. Instead: every page's Page Visibility Join must be set to
Contract, and every widget added to a page must have its own Visibility
property set to Contract -- the control system, not the panel itself, decides
what's shown. See `generator/page.py::build_page_attributes` (`VisibilityJoin`
defaults to `contracts.CONTRACT_ENABLED`) and `make_widget_reference` (the
`<ch5-template>` widget-reference element always gets its `Visibility`/
`Visibility_fb` signals enabled).

## 6. Communication with Control Systems
Construct project objects (pages, widgets and individual components) can communicate with control systems using something called a "contract signal". The contract signals use the object name to define the actual signal name. I.E. If there is a button on a cable tv control widget and the button has a text label called "Menu", the object name will be called "Menu".

All pages, widgets and components need to have meaningful names and the contract support enabled to make the control system programming easier.

**Hard requirement**: every component's `componentName` must be non-blank, and must be unique among the other components on the same page or widget (the same name reused on a *different* page/widget is fine). Construct enforces this itself — a component with a blank or colliding name can lose its property-grid fields entirely (including custom-mode CSS fields), not just its displayed name. `generate-project.py --validate` checks this automatically and reports it via `blank_component_names`/`duplicate_component_names`; treat either being non-empty as a hard failure.

## 7. Session Context and Active Project Selection

The skill determines its working context from the Claude AI session's current active folder.

* If the active folder contains a Construct solution file (`.csln`), the skill is operating at the solution level.
* When the user asks for changes to be made, they must provide the project name they want the changes made against. The `.csln` file contains the authoritative list of projects associated with the solution, including each project's child folder path — the skill should read this list directly rather than guessing from the folder structure.
* If the user does not provide the name of the project to apply changes to, the skill must ask them to provide it, offering the exact project names found in the `.csln` file.
* Once a project name has been selected, the skill's working folder must be changed to that project's own folder.
* The selected project remains the skill's active context for the rest of the conversation. The user must explicitly ask to move to another project before the skill selects a different one.

## 8. Skill Functions
Markdown files should be created for skill functions, so there is organization and process defined, as well as business rules that can be added over time during development. New markdown files can be created by AI at any time to ensure organization is followed.

The following are a list of functions the skill should provide:

* Ability to create a new solution
* Ability to add a project to a solution
* Ability to create a page
* Ability to create a widget
* Ability to add a widget to a page
* Ability to add Construct resolutions to a project
* Ability to create custom resolutions and use them in a project
* Ability to add/remove resolutions and reflow the project as required.
* Ability to add and use custom them files to a project
* Ability to add and use custom font files to a project
* Ability to add/edit/remove any component in the CH5 SDK to a page or widget. This includes understanding how to add a widget list and a widget reference to the widget list
* Ability to customize the look of all components (using the components CSS properties) when the components are in custom mode
* Ability to globally replace the font family across the entire project
* Ability to provide font family suggestions by searching the internet for free webfonts and then automatically install add them to Construct and globally apply the new font to all components
* Ability to provide a full user interface design that follows industry standards for touch-based interfaces

## 9. Multi-Resolution Reflow
The skill must handle all of the required reflow operations when working with multi-resolution projects. The reflow operations are always based on the orientation-primary: highest landscape resolution and highest portrait resolution.

## 10. Sample Projects and Testing
A Construct sample solution and project are located here: C:\Solutions\ClaudeSamples. The Components project contains a page per component, where each page will contain variations of the component for validation.

* Page names prefixed with "Component" indicate a component sample.
* Page names prefixed with "Widget on Page" indicate a page with a widget sample.
* Page names prefixed with "Widget List" indicate a widget list sample.

Since the goal of this skill is to create & edit Construct data files, AI is responsible for developing a testing harness that compares skill-generated data files against known-valid Construct data files. AI must automatically iterate, compare and fix issues as the skill progresses before any manual testing is to be performed in Construct.








 


