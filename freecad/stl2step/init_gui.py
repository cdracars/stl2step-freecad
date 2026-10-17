"""FreeCAD workbench entry point for the STL-to-STEP add-on."""

from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

ICON = str(Path(__file__).resolve().parent / "resources" / "icons" / "stl2step.svg")


class Stl2StepWorkbench(Gui.Workbench):
    """Native workbench for STL reconstruction and STEP import."""

    MenuText = "STL to STEP"
    ToolTip = "Reconstruct STL meshes as STEP B-Rep geometry"
    Icon = ICON

    def Initialize(self):
        from freecad.stl2step.command import ConvertCommand

        self._command = ConvertCommand.install()
        self.appendToolbar("STL to STEP", [ConvertCommand.NAME])
        self.appendMenu("STL to STEP", [ConvertCommand.NAME])

    def Activated(self):
        command = getattr(self, "_command", None)
        if command:
            from PySide import QtCore

            # Open the tool once FreeCAD has finished switching workbenches.
            QtCore.QTimer.singleShot(0, command.open_from_workbench)

    def Deactivated(self):
        command = getattr(self, "_command", None)
        if command:
            command.shutdown()

    def GetClassName(self):
        return "Gui::PythonWorkbench"


def _warn_about_legacy_install():
    # Releases up to 0.5.x were copied into Mod/Stl2StepFreeCAD. Both copies
    # register the same workbench and command, so ask the user to remove it.
    legacy = Path(App.getUserAppDataDir()) / "Mod" / "Stl2StepFreeCAD"
    if (legacy / "InitGui.py").is_file():
        App.Console.PrintWarning(
            f"STL to STEP: an older copy of this add-on is still installed at {legacy}. "
            "Close FreeCAD and delete that folder to avoid duplicate commands.\n"
        )


_warn_about_legacy_install()
Gui.addWorkbench(Stl2StepWorkbench())
