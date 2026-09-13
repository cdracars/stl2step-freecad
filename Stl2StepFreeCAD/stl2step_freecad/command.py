"""FreeCAD command that converts a selected mesh or external STL."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Import
import Mesh
from PySide import QtCore, QtWidgets

from . import engine


def _addon_directory() -> Path:
    return Path(__file__).resolve().parents[1]


def _decode(data) -> str:
    return bytes(data).decode("utf-8", errors="replace")


def _selected_mesh():
    meshes = [obj for obj in Gui.Selection.getSelection()
              if obj.isDerivedFrom("Mesh::Feature")]
    return meshes[0] if len(meshes) == 1 else None


def _result_summary(result: dict) -> str:
    lines = [
        "The STEP geometry was imported.", "",
        f"Mode: {result.get('mode', 'TrueForm')}",
        f"Triangles: {result.get('triangles', 0)}",
        f"Solids: {result.get('solids', 0)}",
        f"Open shells: {result.get('openShells', 0)}",
        "Faces after reconstruction: "
        f"{result.get('facesAfterSmooth', result.get('facesAfterUnify', 0))}",
        f"Planes recovered: {result.get('smoothPlanes', 0)}",
        f"Cylinders recovered: {result.get('smoothCylinders', 0)}",
        f"Fillets recovered: {result.get('smoothFillets', 0)}",
        f"FreeCAD objects imported: {result.get('importedObjects', 0)}",
        f"Elapsed: {result.get('seconds', 0):.2f}s",
    ]
    warnings = result.get("warnings") or []
    if warnings:
        lines.extend(["", "Warnings:", *[f"- {warning}" for warning in warnings]])
    return "\n".join(lines)


class ConversionProgressDialog(QtWidgets.QDialog):
    """Small non-modal status window for a conversion with unknown duration."""

    def __init__(self, input_stl, mode, on_cancel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("STL to STEP — Converting")
        self.setModal(False)
        self.setMinimumWidth(390)

        layout = QtWidgets.QVBoxLayout(self)
        self._heading = QtWidgets.QLabel("Reconstructing STL geometry")
        self._heading.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(self._heading)

        self._status = QtWidgets.QLabel(
            f"{input_stl.name}  •  {mode.title()} mode"
        )
        layout.addWidget(self._status)

        self._activity = QtWidgets.QLabel("The engine is working")
        layout.addWidget(self._activity)

        self._elapsed = QtWidgets.QLabel("Elapsed: 00:00")
        layout.addWidget(self._elapsed)

        buttons = QtWidgets.QDialogButtonBox()
        self._hide_button = buttons.addButton("Hide", QtWidgets.QDialogButtonBox.AcceptRole)
        self._hide_button.clicked.connect(self.hide)
        self._cancel_button = buttons.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        self._cancel_button.clicked.connect(on_cancel)
        layout.addWidget(buttons)

        self._seconds = 0
        self._dots = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self._seconds += 0.5
        self._activity.setText("The engine is working" + "." * self._dots)
        minutes, seconds = divmod(int(self._seconds), 60)
        self._elapsed.setText(f"Elapsed: {minutes:02d}:{seconds:02d}")

    def set_phase(self, heading, activity):
        self._heading.setText(heading)
        self._activity.setText(activity)
        self._cancel_button.setEnabled(False)

    def set_cancelled(self):
        self._activity.setText("Cancelling…")
        self._cancel_button.setEnabled(False)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def finish(self):
        self._timer.stop()
        self.hide()


class ConversionTaskPanel:
    """Native FreeCAD task panel for one conversion configuration."""

    def __init__(self, command, document, source_mesh):
        self._command = command
        self._document = document
        self._source_mesh = source_mesh
        self.form = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(self.form)
        layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self._path = QtWidgets.QLineEdit()
        self._path.setPlaceholderText("Choose an STL file...")
        self._browse = QtWidgets.QPushButton("Browse...")
        self._browse.clicked.connect(self._choose_file)
        path_row = QtWidgets.QHBoxLayout()
        path_row.addWidget(self._path)
        path_row.addWidget(self._browse)
        layout.addRow("Input STL", path_row)

        self._units = QtWidgets.QComboBox()
        self._units.addItem("Millimetres (mm)", "mm")
        self._units.addItem("Inches (in)", "in")
        layout.addRow("Units", self._units)

        self._mode = QtWidgets.QComboBox()
        self._mode.addItem("TrueForm (recommended)", "trueform")
        self._mode.addItem("Verbatim (preserve facets)", "verbatim")
        layout.addRow("Conversion", self._mode)

        if source_mesh:
            self._path.setText(f"Selected mesh: {source_mesh.Label}")
            self._path.setReadOnly(True)
            self._browse.setEnabled(False)
            self._units.setEnabled(False)

        self.form.setWindowTitle("STL to STEP")

    def _choose_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            Gui.getMainWindow(), "Choose an STL to reconstruct", "", "STL mesh (*.stl)"
        )
        if filename:
            self._path.setText(filename)

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

    def accept(self):
        input_stl = None if self._source_mesh else Path(self._path.text().strip())
        if not self._source_mesh and (not input_stl or not input_stl.is_file()):
            QtWidgets.QMessageBox.warning(self.form, "STL to STEP", "Choose an existing STL file first.")
            return
        units = "mm" if self._source_mesh else self._units.currentData()
        mode = self._mode.currentData()
        if self._command._start_conversion(self._document, self._source_mesh, input_stl, units, mode):
            self._command._panel = None
            Gui.Control.closeDialog()

    def reject(self):
        self._command._panel = None
        Gui.Control.closeDialog()


class ConvertCommand:
    NAME = "Stl2Step_Convert"

    def __init__(self):
        self._process = None
        self._temp_directory = None
        self._output_step = None
        self._document_name = None
        self._source_mesh_name = None
        self._mode = None
        self._cancel_requested = False
        self._progress_dialog = None
        self._panel = None

    def GetResources(self):
        return {
            "Pixmap": str(_addon_directory() / "resources" / "stl2step.svg"),
            "MenuText": "STL to STEP Solid",
            "ToolTip": "Reconstruct a selected mesh or STL as STEP B-Rep geometry.",
        }

    def IsActive(self):
        return self._process is None

    def _hide_progress(self):
        if self._progress_dialog:
            if hasattr(self._progress_dialog, "finish"):
                self._progress_dialog.finish()
            else:
                self._progress_dialog.close()
            self._progress_dialog.deleteLater()
            self._progress_dialog = None
        Gui.getMainWindow().statusBar().clearMessage()

    def _show_progress(self, input_stl, mode):
        try:
            self._progress_dialog = ConversionProgressDialog(
                input_stl, mode, self._cancel_conversion, Gui.getMainWindow()
            )
        except Exception as exc:
            App.Console.PrintError(f"stl2step: status window unavailable: {exc}\n")
            self._progress_dialog = QtWidgets.QProgressDialog(
                f"Converting {input_stl.name} ({mode.title()})...", "Hide", 0, 0,
                Gui.getMainWindow(),
            )
            self._progress_dialog.setWindowTitle("STL to STEP")
            self._progress_dialog.setMinimumDuration(0)
            self._progress_dialog.setAutoClose(False)
            self._progress_dialog.setAutoReset(False)
            self._progress_dialog.canceled.connect(self._cancel_conversion)
        self._progress_dialog.show()
        Gui.getMainWindow().statusBar().showMessage(
            f"STL to STEP: converting {input_stl.name} ({mode.title()})..."
        )

    def _cancel_conversion(self):
        process = self._process
        if process is None:
            return
        self._cancel_requested = True
        if self._progress_dialog and hasattr(self._progress_dialog, "set_cancelled"):
            self._progress_dialog.set_cancelled()
        Gui.getMainWindow().statusBar().showMessage("STL to STEP: cancelling…")
        process.kill()

    def Activated(self):
        if self._process is not None:
            QtWidgets.QMessageBox.information(
                Gui.getMainWindow(), "STL to STEP",
                "A conversion is already in progress. Please wait for it to finish.",
            )
            return
        parent = Gui.getMainWindow()
        document = App.ActiveDocument
        source_mesh = _selected_mesh()
        self._panel = ConversionTaskPanel(self, document, source_mesh)
        Gui.Control.showDialog(self._panel)

    def _start_conversion(self, document, source_mesh, input_stl, units, mode):
        parent = Gui.getMainWindow()
        self._temp_directory = Path(tempfile.mkdtemp(prefix="stl2step-freecad-"))
        if source_mesh:
            input_stl = self._temp_directory / f"{source_mesh.Name}.stl"
            try:
                Mesh.export([source_mesh], str(input_stl))
            except Exception as exc:
                self._cleanup()
                QtWidgets.QMessageBox.critical(parent, "STL to STEP", f"Could not export the selected mesh:\n\n{exc}")
                return False
            units = "mm"
            self._source_mesh_name = source_mesh.Name
        document = document or App.ActiveDocument or App.newDocument("Stl2Step")
        try:
            executable = engine.resolve_executable(_addon_directory())
        except engine.EngineError as exc:
            self._cleanup()
            QtWidgets.QMessageBox.critical(parent, "STL to STEP", str(exc))
            return False
        self._document_name = document.Name
        self._mode = mode
        self._cancel_requested = False
        self._output_step = self._temp_directory / f"{input_stl.stem}.step"
        self._process = QtCore.QProcess(parent)
        self._process.finished.connect(self._finished)
        self._process.setProgram(str(executable))
        self._process.setArguments(
            engine.arguments(input_stl, self._output_step, units=units, mode=mode)
        )
        self._process.start()
        if not self._process.waitForStarted(1000):
            error = self._process.errorString()
            self._process = None
            self._hide_progress()
            self._cleanup()
            QtWidgets.QMessageBox.critical(parent, "STL to STEP", f"Could not start stl2step:\n\n{error}")
            return False
        App.Console.PrintMessage(f"stl2step: converting {input_stl}\n")
        self._show_progress(input_stl, mode)
        return True

    def _finished(self, exit_code, _exit_status):
        parent = Gui.getMainWindow()
        process = self._process
        self._process = None
        if process is None:
            return
        if self._cancel_requested:
            self._hide_progress()
            self._cleanup()
            parent.statusBar().showMessage("STL to STEP: conversion cancelled", 10000)
            QtWidgets.QMessageBox.information(
                parent, "STL to STEP", "The conversion was cancelled. No source mesh was hidden."
            )
            return
        temp_directory = self._temp_directory
        output_step = self._output_step
        stdout = _decode(process.readAllStandardOutput())
        stderr = _decode(process.readAllStandardError()).strip()
        App.Console.PrintMessage(
            f"stl2step: finished with exit code {exit_code}; output={output_step}\n"
        )
        if stderr:
            App.Console.PrintMessage(f"stl2step stderr: {stderr}\n")
        try:
            result = engine.validate_conversion(stdout, stderr, exit_code, output_step)
            if self._progress_dialog and hasattr(self._progress_dialog, "set_phase"):
                self._progress_dialog.set_phase(
                    "Importing STEP geometry", "FreeCAD is opening the generated STEP file…"
                )
            parent.statusBar().showMessage("STL to STEP: importing STEP geometry…")
            try:
                document = App.getDocument(self._document_name)
            except NameError as exc:
                raise engine.EngineError(f"The starting document is no longer open. The STEP remains at {output_step}.") from exc
            object_count = len(document.Objects)
            Import.insert(str(output_step), document.Name)
            document.recompute()
            imported_count = len(document.Objects) - object_count
            if imported_count <= 0:
                raise engine.EngineError(
                    "FreeCAD did not create any objects from the generated STEP file. "
                    f"The STEP remains at {output_step}."
                )
            if self._source_mesh_name:
                source = document.getObject(self._source_mesh_name)
                if source:
                    source.ViewObject.Visibility = False
            Gui.activeDocument().activeView().fitAll()
            result["mode"] = "TrueForm" if self._mode == "trueform" else "Verbatim"
            result["importedObjects"] = imported_count
            QtWidgets.QMessageBox.information(parent, "STL to STEP", _result_summary(result))
            self._hide_progress()
            self._cleanup()
        except Exception as exc:
            App.Console.PrintError(f"stl2step: {exc}\n")
            self._hide_progress()
            parent.statusBar().showMessage(f"STL to STEP failed: {exc}", 15000)
            retained = f"\n\nTemporary files remain at:\n{temp_directory}"
            QtWidgets.QMessageBox.critical(parent, "STL to STEP", f"Could not import the conversion:\n\n{exc}{retained}")

    def _cleanup(self):
        if self._temp_directory:
            shutil.rmtree(self._temp_directory, ignore_errors=True)
        self._temp_directory = self._output_step = self._document_name = self._source_mesh_name = self._mode = None

    @classmethod
    def install(cls):
        Gui.addCommand(cls.NAME, cls())
