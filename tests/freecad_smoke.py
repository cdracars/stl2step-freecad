"""Headless FreeCAD integration smoke test for the bundled add-on engine."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import FreeCAD as App
import Import


repo = Path(__file__).resolve().parents[1]
stl = Path(r"C:\Users\cdrac\code\stl2step\tests\corpus\S09.stl")
engine = repo / "Stl2StepFreeCAD" / "bin" / "windows-x86_64" / "stl2step.exe"
work = Path(tempfile.mkdtemp(prefix="stl2step-freecad-smoke-", dir=repo / "tests"))
output = work / "S09.step"

try:
    completed = subprocess.run(
        [str(engine), str(stl), "-o", str(output), "--quiet", "--no-verify",
         "--engine", "trueform", "--units", "mm"],
        capture_output=True,
        text=True,
        check=False,
    )
    result_lines = [line for line in completed.stdout.splitlines() if line.startswith("RESULT ")]
    if completed.returncode not in {0, 2} or not result_lines:
        raise RuntimeError(
            f"engine failed: exit={completed.returncode} stderr={completed.stderr!r}"
        )
    result = json.loads(result_lines[-1][len("RESULT "):])
    if not result.get("ok") or not output.is_file():
        raise RuntimeError(f"invalid engine result or missing STEP: {result}")

    document = App.newDocument("Stl2StepSmoke")
    Import.insert(str(output), document.Name)
    document.recompute()
    imported = [obj for obj in document.Objects if obj.TypeId != "App::Origin"]
    if not imported:
        raise RuntimeError("FreeCAD imported no STEP objects")
    print(json.dumps({"result": result, "importedObjects": len(imported)}))
    App.closeDocument(document.Name)
finally:
    shutil.rmtree(work, ignore_errors=True)
