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

## Install on Windows

1. Download this repository with **Code → Download ZIP** and extract it.
2. Copy the inner `Stl2StepFreeCAD` folder into FreeCAD's user `Mod` directory:

   ```text
   %APPDATA%\FreeCAD\v1-1\Mod
   ```

   Use the matching versioned directory for another FreeCAD release.
3. Restart FreeCAD.
4. Select **STL to STEP** in the workbench selector.

The copied folder must contain `InitGui.py`, `package.xml`,
`stl2step_freecad`, `resources`, and `bin`. Do not copy only the Python files.

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

FreeCAD-independent tests:

```text
python -m unittest discover -s tests
```

Syntax checks:

```text
python -m py_compile Stl2StepFreeCAD\Init.py Stl2StepFreeCAD\InitGui.py Stl2StepFreeCAD\stl2step_freecad\command.py Stl2StepFreeCAD\stl2step_freecad\engine.py
```

With FreeCAD installed, run the real bundled-engine smoke test:

```text
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" tests\freecad_smoke.py
```

To refresh the Windows bundle from a local engine build:

```powershell
.\scripts\bundle-engine.ps1 -EngineDirectory 'C:\path\to\engine\bin'
```

## Automated engine updates

GitHub Actions checks the canonical `BlinkingSun/stl2step` releases weekly. A newer Windows
bundle is downloaded and validated, then proposed in an automated pull request.
The workflow enables squash auto-merge after its checks succeed. Review the
upstream release and binary provenance before changing this policy.

## Licensing

The add-on and engine integration are MIT-licensed; see [LICENSE](LICENSE).
The bundled OCCT runtime libraries have separate LGPL-2.1-with-exception terms.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing or
modifying the binary bundle.
