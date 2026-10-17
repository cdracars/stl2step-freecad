# Changelog

## 0.6.1

- Updated the pinned engine to stl2step 1.5.0. Fillets between planes are now
  recovered as cylinders and hole chamfers or countersinks as cones, and
  hexagonal holes stay planar. Installs that downloaded 1.4.3 are asked once
  to download 1.5.0; release ZIPs bundle it.
- The engine download prompt now says when the new engine replaces an older
  downloaded one.
- Added a Test report issue form, linked from the README, for sharing how the
  add-on worked for you.
- Fixed the weekly engine-pin workflow, which now pins only platforms the
  add-on can install (Windows x64).

## 0.6.0

**Upgrading:** the add-on folder changed from `Stl2StepFreeCAD` to
`stl2step-freecad`. Delete the old `Mod\Stl2StepFreeCAD` folder before
installing; see the README.

- Moved to FreeCAD's namespaced add-on layout (`freecad/stl2step`), with
  `package.xml` at the repository root so the Addon Manager can install it.
- Release ZIPs now contain a single `stl2step-freecad` folder to extract into `Mod`.
- Raised the minimum FreeCAD version to 1.0.
- Added a consent-gated download of the pinned engine when none is installed,
  verified by size, SHA-256, safe unpacking, and engine version before use.
- Moved the engine pin into the add-on as
  `freecad/stl2step/engine-release.json`, with assets keyed by platform.
- Fixed the task panel crashing on FreeCAD builds that use PySide6.
- Switching to the workbench now opens the conversion panel automatically.
- New workbench icon, also shown in the task panel header.
- Imported objects are named after the source STL instead of the STEP writer.
- Warns in the report view if an old `Stl2StepFreeCAD` copy is still installed.

## 0.5.0

- Promoted STL to STEP into a native FreeCAD workbench.
- Added native TrueForm and Verbatim conversion options with remembered settings.
- Added responsive QProcess conversion progress, cancellation, and shutdown handling.
- Added robust engine-result and failure reporting, including retained recovery artifacts.
- Added clean STEP import into the active or a new FreeCAD document.
- Added verified upstream engine vendoring and release-archive smoke tests.

## 0.4.0

- Added verified upstream engine release packaging.
- Added the initial FreeCAD conversion command and engine adapter.
