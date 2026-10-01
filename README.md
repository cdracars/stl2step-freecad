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

## Install on Windows

1. Download the latest add-on ZIP from the repository's
   [Releases page](https://github.com/cdracars/stl2step-freecad/releases) and
   extract it.
2. Copy the included `Stl2StepFreeCAD` folder into FreeCAD's user `Mod` directory:

   ```text
   %APPDATA%\FreeCAD\v1-1\Mod
   ```

   Use the matching versioned directory for another FreeCAD release.
3. Restart FreeCAD.
4. Select **STL to STEP** in the workbench selector.

The copied folder must contain `InitGui.py`, `package.xml`,
`stl2step_freecad`, `resources`, and `bin\windows-x86_64\stl2step.exe` plus
its DLLs. Do not copy only the Python files. The repository source ZIP is for
development; use a release ZIP for the bundled engine.

## Update an existing installation

1. Close all FreeCAD windows.
2. Download the newest release ZIP from the
   [Releases page](https://github.com/cdracars/stl2step-freecad/releases).
3. Extract it, then replace the existing `Stl2StepFreeCAD` folder in
   `%APPDATA%\FreeCAD\<version>\Mod` with the folder from the release ZIP.
4. Start FreeCAD again and select **STL to STEP** from the workbench selector.

Keep the release folder intact, including `bin\windows-x86_64` and its DLLs.
Do not update by copying individual Python files or by downloading the source
ZIP. Your documents and FreeCAD files are not affected by replacing the
add-on folder.

## Use

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
   `Stl2StepFreeCAD\bin\windows-x86_64\stl2step.exe`.
3. `stl2step` on `PATH`.

For development:

```powershell
$env:STL2STEP_EXECUTABLE = 'C:\path\to\stl2step.exe'
```

## Troubleshooting

- If the workbench is missing, confirm the folder is directly inside `Mod` and
  restart FreeCAD.
- If the engine cannot start, confirm `stl2step.exe` and all DLLs are present
  in `bin\windows-x86_64`, or set `STL2STEP_EXECUTABLE`.
- If conversion or import fails, the error dialog shows a retained temporary
  directory. The FreeCAD Python console reports the engine exit code, output
  path, and stderr.
- A warning may mean that one component stayed faceted while other components
  were reconstructed successfully; the result is still reported explicitly.

## Development

Maintainers should update the add-on by changing the source, running the tests
and syntax checks below, updating `Stl2StepFreeCAD/package.xml` and
`CHANGELOG.md`, and merging to `master`. Publishing a version tag triggers CI
to vendor the pinned upstream engine, validate the complete archive, and attach
the release ZIP. Engine binaries should remain out of Git history.

FreeCAD-independent tests:

```text
python -m unittest discover -s tests
```

Syntax checks:

```text
python -m py_compile Stl2StepFreeCAD\Init.py Stl2StepFreeCAD\InitGui.py Stl2StepFreeCAD\stl2step_freecad\command.py Stl2StepFreeCAD\stl2step_freecad\engine.py
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
newer pinned version and its SHA-256/size are proposed in an automated pull
request. Release packaging downloads the exact pinned upstream ZIP, verifies
it against the upstream manifest, and includes the unchanged engine bundle in
the add-on release ZIP. Engine binaries are intentionally not committed to
this source repository.

## Licensing

The add-on is MIT-licensed; see [LICENSE](LICENSE). The upstream engine's
license is reproduced in [LICENSE.stl2step](LICENSE.stl2step). The bundled OCCT
runtime libraries have separate LGPL-2.1-with-exception terms. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing or
modifying the binary bundle.
