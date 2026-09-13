# FreeCAD smoke test

Run this against the installed release ZIP, not only a source checkout.

## Setup

- [ ] Start FreeCAD with a blank disposable document.
- [ ] Install the complete release ZIP into the matching user `Mod` directory.
- [ ] Confirm FreeCAD starts without an add-on error notification.
- [ ] Confirm the **STL to STEP** workbench appears after a fresh start.
- [ ] Confirm the archive contains `stl2step.exe` and its runtime DLLs.
- [ ] Prepare one small closed STL and one larger or open-shell STL.

## Happy path

- [ ] Open **STL to STEP Solid** and confirm millimetres and TrueForm defaults.
- [ ] Convert the closed STL and confirm FreeCAD remains responsive.
- [ ] Confirm STEP geometry imports into the starting document.
- [ ] Confirm the completion summary includes document, output path, mode,
      geometry counts, elapsed time, engine version, and warnings.
- [ ] Repeat the command and confirm units and mode are remembered.

## Modes and warnings

- [ ] Convert with Verbatim and confirm the summary identifies Verbatim mode.
- [ ] Convert the open-shell STL and confirm warning text is visible when the
      engine reports a usable result with exit code `2`.
- [ ] Confirm a failed conversion shows a concise error and no partial import.

## Cancellation and recovery

- [ ] Start a conversion large enough to observe the progress dialog.
- [ ] Confirm the dialog shows preparing, reconstructing, and importing phases.
- [ ] Click Cancel and confirm the process stops and FreeCAD remains usable.
- [ ] Confirm cancellation does not hide the source mesh or leave a busy state.
- [ ] If import fails after conversion, confirm the STEP path is shown and the
      retained file can be opened manually.
- [ ] Switch workbenches or close FreeCAD during conversion and confirm no
      orphan engine process remains.

## Clean-install check

- [ ] Test without a source checkout, Python package, PATH change, or separate
      OCCT installation.
- [ ] Record FreeCAD version, Windows version, STL characteristics, mode, and
      elapsed time with any issue report.
