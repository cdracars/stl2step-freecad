# Changelog

## Unreleased

- Added a consent-gated download of the pinned engine when none is installed,
  verified by size, SHA-256, safe unpacking, and engine version before use.
- Moved the engine pin into the add-on as
  `stl2step_freecad/engine-release.json`, with assets keyed by platform.
- Fixed the task panel crashing on FreeCAD builds that use PySide6.
- Switching to the workbench now opens the conversion panel automatically.

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
