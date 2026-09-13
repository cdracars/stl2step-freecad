# Contributing

Thanks for helping improve STL to STEP for FreeCAD.

## Before opening an issue

Search existing issues first. For a conversion problem, include:

- FreeCAD version and operating system
- Whether the source was a selected mesh or an external STL
- Units and conversion mode
- Approximate triangle count and conversion time
- Redacted `stl2step:` lines from the FreeCAD Python console
- The retained temporary-directory path, when an error dialog provides one

Do not attach proprietary models or credentials.

## Development

Run the checks from the repository root:

```text
python -m unittest discover -s tests
python -m py_compile Stl2StepFreeCAD\Init.py Stl2StepFreeCAD\InitGui.py Stl2StepFreeCAD\stl2step_freecad\command.py Stl2StepFreeCAD\stl2step_freecad\engine.py
```

If FreeCAD is installed, also run `tests\freecad_smoke.py` with `freecadcmd`.
Use `scripts\bundle-engine.ps1` only when intentionally refreshing the
platform bundle from a validated upstream build.

## Pull requests

Keep changes focused, explain user-visible behavior, and update the README or
tests when behavior changes. Pull requests should pass CI and must not include
unrelated generated files, local paths, or proprietary assets.
