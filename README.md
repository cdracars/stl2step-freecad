# STL to STEP Solid for FreeCAD

An open-source FreeCAD workbench that converts STL meshes into STEP B-Rep
geometry using the [`stl2step`](https://github.com/BlinkingSun/stl2step)
engine. Select a mesh or choose an STL file, choose the units and reconstruction
mode, and receive editable Part geometry in the active FreeCAD document.

## Features

- Native **STL to STEP** workbench with toolbar and menu command.
- **TrueForm** mode for recovering planes, cylinders, and fillets where the
  mesh supports them.
- **Verbatim** mode for preserving faceted surfaces.
- Asynchronous conversion through FreeCAD/PySide `QProcess`.
- Robust `RESULT` and exit-code handling, including warnings and retained
  recovery files when import fails.
- Source mesh hidden only after a successful STEP import.
- Bundled Windows x64 engine and OCCT runtime libraries.

The output is direct B-Rep geometry. It does not recreate sketches, constraints,
dimensions, or parametric feature history.

For shared behavior and manual validation, see the
[`ENGINE_CONTRACT.md`](ENGINE_CONTRACT.md),
[`docs/SCENARIO_MATRIX.md`](docs/SCENARIO_MATRIX.md), and
[`docs/FREECAD_SMOKE_TEST.md`](docs/FREECAD_SMOKE_TEST.md).

## Install

Requires FreeCAD 1.0 or newer.

### With git (works like the Addon Manager)

Clone the repository into FreeCAD's user `Mod` directory, then restart FreeCAD:

```bash
git clone https://github.com/cdracars/stl2step-freecad "%APPDATA%\FreeCAD\v1-1\Mod\stl2step-freecad"
```

Use the matching versioned directory for another FreeCAD release. A clone does
not include the engine; the first time you run the tool, it offers to download
it (see [Network access](#network-access)).

### From a release ZIP (Windows, works offline)

1. Download the latest `stl2step-freecad-<version>.zip` from the
   [Releases page](https://github.com/cdracars/stl2step-freecad/releases).
2. Extract it so the `stl2step-freecad` folder lands directly in FreeCAD's
   user `Mod` directory, for example `%APPDATA%\FreeCAD\v1-1\Mod\stl2step-freecad`.
3. Restart FreeCAD and select **STL to STEP** in the workbench selector.

The release ZIP bundles the engine in
`freecad\stl2step\bin\windows-x86_64`, so no download is needed. Keep the
folder intact; don't copy only the Python files.

## Update an existing installation

- **Git install:** close FreeCAD, run `git pull` in the add-on folder, then
  start FreeCAD again.
- **Release ZIP:** close FreeCAD, delete `Mod\stl2step-freecad`, extract the
  newest release ZIP in its place, then start FreeCAD again.

Your documents, saved settings, and any downloaded engine are not affected.

### Upgrading from 0.5.x or earlier

Version 0.6.0 moved to FreeCAD's namespaced add-on layout, so the add-on folder
changed from `Stl2StepFreeCAD` to `stl2step-freecad`.

1. Close FreeCAD.
2. Delete the old `%APPDATA%\FreeCAD\<version>\Mod\Stl2StepFreeCAD` folder.
3. Install 0.6.0 using either method above.

If the old folder is still present, FreeCAD's report view shows a warning,
because both copies register the same workbench. Your units and mode settings
carry over.

## Use

Switching to the **STL to STEP** workbench opens the conversion panel
automatically. Run **STL to STEP Solid** from the toolbar or menu to reopen it.

1. For an imported mesh, select exactly one mesh object and run **STL to STEP
   Solid**. The workbench exports the selected mesh to a temporary STL.
2. With no mesh selected, run the command and choose an `.stl` file.
3. Choose input units: **Millimetres** or **Inches**.
4. Choose **TrueForm** or **Verbatim**.
5. Click **OK** and let the asynchronous conversion finish.

The status window shows the input file, mode, activity, and elapsed time. On
success, the STEP is inserted into the starting document and the view is fitted.

## Engine lookup

The adapter resolves the converter in this order:

1. An existing path in `STL2STEP_EXECUTABLE`.
2. The bundled platform directory, currently
   `freecad\stl2step\bin\windows-x86_64\stl2step.exe` (present in release ZIPs).
3. An engine previously downloaded by the add-on (see below).
4. `stl2step` on `PATH`.

If none is found, the add-on offers to download the pinned engine.

For development:

```powershell
$env:STL2STEP_EXECUTABLE = 'C:\path\to\stl2step.exe'
```

## Network access

The add-on makes no network requests at startup or during conversion. The only
connection it ever makes is the engine download below, and only after you agree
to it.

When no engine is found (for example after installing from the Addon Manager,
which does not include the engine binary), running **STL to STEP Solid** asks
before downloading anything. The dialog shows the exact URL, size, and install
location. If you agree:

- The add-on downloads the pinned engine ZIP from the official
  [`BlinkingSun/stl2step`](https://github.com/BlinkingSun/stl2step) GitHub
  release named in
  [`engine-release.json`](freecad/stl2step/engine-release.json),
  currently about 16 MB for Windows x64.
- GitHub receives the request like any browser download. No other data is sent.
- The ZIP must match the pinned size and SHA-256, unpack without unsafe paths,
  and report the pinned version before it is used.
- It is installed in FreeCAD's user data directory under `stl2step-engine`
  (on Windows, `%APPDATA%\FreeCAD\<version>\stl2step-engine`), outside the
  add-on folder. Delete that folder to remove it.

Nothing is downloaded again until a newer add-on release pins a new engine
version. Declining is never remembered; you are asked again next time. Prebuilt
engines are currently published only for Windows x64; on other platforms, build
`stl2step` yourself and use `STL2STEP_EXECUTABLE` or `PATH`.

## Troubleshooting

- If the workbench is missing, confirm the folder is directly inside `Mod` and
  restart FreeCAD.
- If the engine cannot start, confirm `stl2step.exe` and all DLLs are present
  in `bin\windows-x86_64`, or set `STL2STEP_EXECUTABLE`. To force a fresh
  engine download, delete the `stl2step-engine` folder described above.
- If conversion or import fails, the error dialog shows a retained temporary
  directory. The FreeCAD Python console reports the engine exit code, output
  path, and stderr.
- A warning may mean that one component stayed faceted while other components
  were reconstructed successfully; the result is still reported explicitly.

## Development

Maintainers should update the add-on by changing the source, running the tests
and syntax checks below, updating `package.xml` and
`CHANGELOG.md`, and merging to `master`. Publishing a version tag triggers CI
to vendor the pinned upstream engine, validate the complete archive, and attach
the release ZIP. Engine binaries should remain out of Git history.

FreeCAD-independent tests:

```text
python -m unittest discover -s tests
```

Syntax checks:

```text
python -m py_compile freecad\stl2step\__init__.py freecad\stl2step\init_gui.py freecad\stl2step\command.py freecad\stl2step\engine.py freecad\stl2step\engine_install.py
```

With FreeCAD installed, vendor the pinned engine first, then run the real
bundled-engine smoke test:

```text
powershell -ExecutionPolicy Bypass -File scripts\vendor-engine.ps1
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" tests\freecad_smoke.py
```

To vendor the pinned, checksum-verified upstream release:

```powershell
.\scripts\vendor-engine.ps1
```

To copy a local engine build for development only:

```powershell
.\scripts\bundle-engine.ps1 -EngineDirectory 'C:\path\to\engine\bin'
```

## Automated engine updates

GitHub Actions checks the canonical `BlinkingSun/stl2step` releases weekly. A
newer pinned version and its per-platform SHA-256/size are proposed in an
automated pull request that updates
`freecad/stl2step/engine-release.json`. The same pin drives
both the in-app download and release packaging, which downloads the exact
pinned upstream ZIP, verifies it against the upstream manifest, and includes
the unchanged engine bundle in the add-on release ZIP. Engine binaries are intentionally not committed to
this source repository.

## Licensing

The add-on is MIT-licensed; see [LICENSE](LICENSE). The upstream engine's
license is reproduced in [LICENSE.stl2step](LICENSE.stl2step). The bundled OCCT
runtime libraries have separate LGPL-2.1-with-exception terms. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing or
modifying the binary bundle.
