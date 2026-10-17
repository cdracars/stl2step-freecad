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
python -m py_compile freecad\stl2step\__init__.py freecad\stl2step\init_gui.py freecad\stl2step\command.py freecad\stl2step\engine.py freecad\stl2step\engine_install.py
```

If FreeCAD is installed, also run `tests\freecad_smoke.py` with `freecadcmd`.
Use `scripts\bundle-engine.ps1` only when intentionally refreshing the
platform bundle from a validated upstream build.

## Pull requests

Open pull requests against `develop`, the default branch. Keep changes
focused, explain user-visible behavior, and update the README or tests when
behavior changes. Pull requests should pass CI and must not include unrelated
generated files, local paths, or proprietary assets.

## Branches and releases

- `develop` is where work lands. Feature and fix branches start from it and
  merge back into it.
- `main` holds released versions only. The FreeCAD Addon Manager installs from
  `main` (`package.xml` names it in `<url type="repository" branch="main">`), so
  anything merged there reaches users.
- The weekly engine-update workflow opens its pull request against `develop`.

To release:

1. On `develop`, bump `<version>` and `<date>` in `package.xml` and move the
   `CHANGELOG.md` entries under the new version. The Addon Manager compares
   these to offer updates, so bump them on every release.
2. Open a pull request from `develop` into `main` and merge it once CI passes.
3. Publish a GitHub release tagged `v<version>` targeting `main`. CI attaches
   the verified `stl2step-freecad-v<version>.zip`; check that it's there.
