"""FreeCAD workbench entry point for the STL-to-STEP add-on."""

import FreeCADGui as Gui


class Stl2StepWorkbench(Gui.Workbench):
    """Native workbench for STL reconstruction and STEP import."""

    MenuText = "STL to STEP"
    ToolTip = "Reconstruct STL meshes as STEP B-Rep geometry"
    # FreeCAD resolves workbench resources relative to this add-on directory.
    Icon = "resources/stl2step.svg"

    def Initialize(self):
        from stl2step_freecad.command import ConvertCommand

        self._command = ConvertCommand.install()
        self.appendToolbar("STL to STEP", [ConvertCommand.NAME])
        self.appendMenu("STL to STEP", [ConvertCommand.NAME])

    def Deactivated(self):
        command = getattr(self, "_command", None)
        if command:
            command.shutdown()

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(Stl2StepWorkbench())
