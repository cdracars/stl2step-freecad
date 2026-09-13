# STL to STEP Solid for FreeCAD

This is the starter integration for the `stl2step` engine. It runs the engine
outside FreeCAD and imports the generated STEP B-Rep into the active document.

Copy or link `Stl2StepFreeCAD` into FreeCAD's user `Mod` directory. The engine
is resolved from `STL2STEP_EXECUTABLE`, the bundled platform path, or `PATH`.

The workbench accepts one selected `Mesh::Feature` or an external STL through a
single native task panel. The panel controls units and conversion mode, then
the engine runs asynchronously while FreeCAD remains responsive. The STEP is
imported into the starting FreeCAD document, and a selected source mesh is
hidden only after successful import. TrueForm is recommended for analytic
surface recovery; Verbatim preserves the original facets. The result is direct B-Rep geometry;
it does not recreate sketches, constraints, dimensions, or feature history.

## Install

Copy `Stl2StepFreeCAD` into FreeCAD's user `Mod` directory and restart FreeCAD.
Switch to the **STL to STEP** workbench, then run **STL to STEP Solid** from its
menu or toolbar. This workbench is intentionally small; the resulting geometry
can then be used in Part. For
development, set `STL2STEP_EXECUTABLE` to a locally built engine; otherwise the
add-in searches its platform bundle and then `PATH`.

If conversion or import fails, the temporary directory is intentionally kept
and shown in the error dialog so the generated STEP and diagnostics can be
recovered.

## Tests

The engine contract tests run without FreeCAD:

```text
python -m unittest discover -s tests
```
