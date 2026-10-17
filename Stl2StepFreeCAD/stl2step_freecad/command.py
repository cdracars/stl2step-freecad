"""FreeCAD command that converts a selected mesh or external STL."""

from __future__ import annotations

import shutil
import tempfile
import threading
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Import
import Mesh
from PySide import QtCore, QtGui, QtWidgets

from . import engine, engine_install


def _addon_directory() -> Path:
    return Path(__file__).resolve().parents[1]


def _engine_root() -> Path:
    # Outside the add-on folder so Addon Manager updates never touch it.
    return Path(App.getUserAppDataDir()) / "stl2step-engine"


def _downloaded_engine():
    try:
        return engine_install.installed_executable(_engine_root(), engine_install.load_pin())
    except engine_install.InstallError as exc:
        App.Console.PrintWarning(f"stl2step: {exc}\n")
        return None


def _resolve_engine() -> Path:
    return engine.resolve_executable(_addon_directory(), _downloaded_engine())


def _exec(dialog):
    # PySide6 renamed exec_() to exec().
    return (getattr(dialog, "exec", None) or dialog.exec_)()


def _mode_label(mode: str) -> str:
    return "TrueForm" if mode == "trueform" else "Verbatim"


def _megabytes(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"


def _decode(data) -> str:
    return bytes(data).decode("utf-8", errors="replace")


def _button_flags(*buttons) -> int:
    # PySide6 enums are not int()-convertible; they expose .value instead.
    flags = 0
    for button in buttons:
        value = getattr(button, "value", button)
        flags |= value if isinstance(value, int) else int(value)
    return flags


def _selected_mesh():
    meshes = [obj for obj in Gui.Selection.getSelection()
              if obj.isDerivedFrom("Mesh::Feature")]
    return meshes[0] if len(meshes) == 1 else None


def _result_summary(result: dict) -> str:
    def warning_text(warning):
        if warning.startswith("smooth: analytic rebuild reverted"):
            return "One component could not be safely reconstructed analytically, so it was kept faceted."
        return warning

    lines = [
        "The STEP geometry was imported.", "",
        f"Source: {result.get('inputName', 'selected STL')}",
        f"Output document: {result.get('documentName', 'new FreeCAD document')}",
        f"Output STEP: {result.get('stepPath', 'temporary file')}",
        f"Mode: {result.get('mode', 'TrueForm')}",
        "",
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
        f"Engine: {result.get('engineVersion', 'unknown')}",
    ]
    warnings = result.get("warnings") or []
    if warnings:
        lines.extend(["", "Warnings:", *[f"- {warning_text(warning)}" for warning in warnings]])
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
            f"{input_stl.name}  •  {_mode_label(mode)} mode"
        )
        layout.addWidget(self._status)

        self._activity_text = "The engine is working (progress is indeterminate)."
        self._activity = QtWidgets.QLabel(self._activity_text)
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
        self._activity.setText(self._activity_text + "." * self._dots)
        minutes, seconds = divmod(int(self._seconds), 60)
        self._elapsed.setText(f"Elapsed: {minutes:02d}:{seconds:02d}")

    def set_phase(self, heading, activity, allow_cancel=True):
        self._heading.setText(heading)
        self._activity_text = activity
        self._activity.setText(activity)
        self._cancel_button.setEnabled(allow_cancel)

    def set_cancelled(self):
        self._activity_text = "Cancelling…"
        self._activity.setText(self._activity_text)
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
        layout.addRow("STL units", self._units)

        self._mode = QtWidgets.QComboBox()
        self._mode.addItem("TrueForm (recommended)", "trueform")
        self._mode.addItem("Verbatim (preserve facets)", "verbatim")
        layout.addRow("Conversion mode", self._mode)

        settings = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Stl2StepFreeCAD")
        self._units.setCurrentIndex(max(0, self._units.findData(settings.GetString("Units", "mm"))))
        self._mode.setCurrentIndex(max(0, self._mode.findData(settings.GetString("Mode", "trueform"))))

        if source_mesh:
            self._path.setText(f"Selected mesh: {source_mesh.Label}")
            self._path.setReadOnly(True)
            self._browse.setEnabled(False)
            self._units.setEnabled(False)

        self.form.setWindowTitle("STL to STEP")
        # FreeCAD shows the form's window icon in the task panel header.
        self.form.setWindowIcon(QtGui.QIcon(str(_addon_directory() / "resources" / "stl2step.svg")))

    def _choose_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            Gui.getMainWindow(), "Choose an STL to reconstruct", "", "STL mesh (*.stl)"
        )
        if filename:
            self._path.setText(filename)

    def getStandardButtons(self):
        return _button_flags(QtWidgets.QDialogButtonBox.Ok, QtWidgets.QDialogButtonBox.Cancel)

    def accept(self):
        input_stl = None if self._source_mesh else Path(self._path.text().strip())
        if not self._source_mesh and (not input_stl or not input_stl.is_file()):
            QtWidgets.QMessageBox.warning(self.form, "STL to STEP", "Choose an existing STL file first.")
            return
        units = "mm" if self._source_mesh else self._units.currentData()
        mode = self._mode.currentData()
        settings = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Stl2StepFreeCAD")
        if not self._source_mesh:
            settings.SetString("Units", units)
        settings.SetString("Mode", mode)
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
        self._input_name = None
        self._executable = None
        self._source_mesh_name = None
        self._mode = None
        self._cancel_requested = False
        self._shutting_down = False
        self._retained_directories = []
        self._progress_dialog = None
        self._panel = None
        self._download = None

    def GetResources(self):
        return {
            "Pixmap": str(_addon_directory() / "resources" / "stl2step.svg"),
            "MenuText": "STL to STEP Solid",
            "ToolTip": "Reconstruct a selected mesh or STL as STEP B-Rep geometry.",
        }

    def IsActive(self):
        return self._process is None and self._download is None

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
                f"Converting {input_stl.name} ({_mode_label(mode)})...", "Hide", 0, 0,
                Gui.getMainWindow(),
            )
            self._progress_dialog.setWindowTitle("STL to STEP")
            self._progress_dialog.setMinimumDuration(0)
            self._progress_dialog.setAutoClose(False)
            self._progress_dialog.setAutoReset(False)
            self._progress_dialog.canceled.connect(self._cancel_conversion)
        self._progress_dialog.show()
        Gui.getMainWindow().statusBar().showMessage(
            f"STL to STEP: converting {input_stl.name} ({_mode_label(mode)})..."
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

    def shutdown(self):
        """Stop child work when FreeCAD deactivates or unloads the workbench."""
        self._shutting_down = True
        if self._process is not None:
            self._cancel_requested = True
            self._process.kill()
        self._hide_progress()
        self._stop_download()

    def Activated(self):
        self._shutting_down = False
        if self._process is not None or self._download is not None:
            busy = "A conversion" if self._process is not None else "The engine download"
            QtWidgets.QMessageBox.information(
                Gui.getMainWindow(), "STL to STEP",
                f"{busy} is already in progress. Please wait for it to finish.",
            )
            return
        try:
            _resolve_engine()
        except engine.EngineMissing:
            self._offer_engine_download()
            return
        except engine.EngineError as exc:
            QtWidgets.QMessageBox.critical(Gui.getMainWindow(), "STL to STEP", str(exc))
            return
        self._open_panel()

    def open_from_workbench(self):
        """Show the tool when the user switches to this workbench, if it is idle."""
        if self._process is not None or self._download is not None or self._panel is not None:
            return
        if Gui.Control.activeDialog():
            return
        self.Activated()

    def _open_panel(self):
        self._panel = ConversionTaskPanel(self, App.ActiveDocument, _selected_mesh())
        Gui.Control.showDialog(self._panel)

    def _offer_engine_download(self):
        parent = Gui.getMainWindow()
        try:
            pin = engine_install.load_pin()
        except engine_install.InstallError as exc:
            QtWidgets.QMessageBox.critical(parent, "STL to STEP", str(exc))
            return
        repository = pin["upstreamRepository"]
        manual = (
            "To use your own build instead, put stl2step on PATH or set the "
            "STL2STEP_EXECUTABLE environment variable, then restart FreeCAD."
        )
        asset = engine_install.pinned_asset(pin)
        if not asset:
            QtWidgets.QMessageBox.information(
                parent, "STL to STEP",
                "STL to STEP needs the stl2step engine, but no prebuilt engine is "
                f"published for this platform ({engine_install.platform_key()}).\n\n"
                f"Build it from https://github.com/{repository}. {manual}",
            )
            return

        root = _engine_root()
        box = QtWidgets.QMessageBox(parent)
        box.setWindowTitle("STL to STEP — Download engine")
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setText("STL to STEP needs the stl2step engine, which is not installed yet.")
        box.setInformativeText(
            f"Download stl2step {pin['engineVersion']} ({_megabytes(asset['size'])}) from "
            f"the official {repository} release on GitHub?\n\n"
            f"Source: {engine_install.download_url(pin, asset)}\n"
            f"Saved to: {engine_install.install_directory(root, pin)}\n\n"
            "The download is checked against a pinned SHA-256 before it is used. "
            "GitHub receives the request like any download; no other data is sent. "
            "Nothing else is downloaded until the add-on pins a new engine version.\n\n"
            + manual
        )
        download = box.addButton("Download", QtWidgets.QMessageBox.AcceptRole)
        cancel = box.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)
        box.setDefaultButton(download)
        box.setEscapeButton(cancel)
        _exec(box)
        if box.clickedButton() is not download:
            return
        self._start_download(root, pin, asset)

    def _start_download(self, root, pin, asset):
        parent = Gui.getMainWindow()
        progress = QtWidgets.QProgressDialog(
            f"Downloading stl2step {pin['engineVersion']}…", "Cancel", 0, 100, parent
        )
        progress.setWindowTitle("STL to STEP — Downloading engine")
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        # The worker only writes plain values here; the GUI thread polls them.
        state = {"received": 0, "total": int(asset["size"]), "result": None, "error": None, "done": False}

        def work():
            try:
                state["result"] = engine_install.download_and_install(
                    root, pin,
                    version_of=engine.version,
                    progress=lambda received, total: state.update(received=received, total=total),
                    cancelled=cancel_event.is_set,
                )
            except Exception as exc:
                state["error"] = exc
            finally:
                state["done"] = True

        timer = QtCore.QTimer(progress)
        timer.timeout.connect(self._poll_download)
        self._download = {
            "state": state, "cancel": cancel_event, "dialog": progress,
            "timer": timer, "version": pin["engineVersion"],
        }
        progress.show()
        App.Console.PrintMessage(f"stl2step: downloading {engine_install.download_url(pin, asset)}\n")
        threading.Thread(target=work, name="stl2step-engine-download", daemon=True).start()
        timer.start(100)

    def _poll_download(self):
        download = self._download
        if download is None:
            return
        state, dialog = download["state"], download["dialog"]
        received, total = state["received"], max(1, state["total"])
        if received < total:
            dialog.setLabelText(
                f"Downloading stl2step {download['version']}…\n"
                f"{_megabytes(received)} of {_megabytes(total)}"
            )
            dialog.setValue(int(received * 100 / total))
        else:
            dialog.setLabelText("Verifying and installing the engine…")
            dialog.setValue(100)
        if not state["done"]:
            return

        self._stop_download()
        parent = Gui.getMainWindow()
        error = state["error"]
        if isinstance(error, engine_install.InstallCancelled):
            App.Console.PrintMessage("stl2step: engine download cancelled\n")
            return
        if error is not None:
            QtWidgets.QMessageBox.critical(
                parent, "STL to STEP", f"Could not install the stl2step engine:\n\n{error}"
            )
            return
        App.Console.PrintMessage(f"stl2step: installed engine at {state['result']}\n")
        if not self._shutting_down:
            self._open_panel()

    def _stop_download(self):
        download, self._download = self._download, None
        if download is None:
            return
        download["cancel"].set()
        download["timer"].stop()
        download["dialog"].close()
        download["dialog"].deleteLater()

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
            executable = _resolve_engine()
        except engine.EngineError as exc:
            self._cleanup()
            QtWidgets.QMessageBox.critical(parent, "STL to STEP", str(exc))
            return False
        self._document_name = document.Name
        self._input_name = input_stl.name
        self._executable = executable
        self._mode = mode
        self._cancel_requested = False
        self._shutting_down = False
        self._output_step = self._temp_directory / f"{input_stl.stem}.step"
        self._show_progress(input_stl, mode)
        if hasattr(self._progress_dialog, "set_phase"):
            self._progress_dialog.set_phase(
                "Preparing conversion", "Checking the engine and preparing temporary files…"
            )
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
        if hasattr(self._progress_dialog, "set_phase"):
            self._progress_dialog.set_phase(
                "Reconstructing STL geometry",
                "The engine is working (progress is indeterminate).",
            )
        App.Console.PrintMessage(f"stl2step: converting {input_stl}\n")
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
            if self._shutting_down:
                return
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
            result["inputName"] = self._input_name
            try:
                result["engineVersion"] = engine.version(self._executable)
            except Exception:
                result["engineVersion"] = "unknown"
            if self._progress_dialog and hasattr(self._progress_dialog, "set_phase"):
                self._progress_dialog.set_phase(
                    "Importing STEP geometry", "FreeCAD is opening the generated STEP file…", False
                )
            parent.statusBar().showMessage("STL to STEP: importing STEP geometry…")
            try:
                document = App.getDocument(self._document_name)
            except NameError as exc:
                raise engine.EngineError(f"The starting document is no longer open. The STEP remains at {output_step}.") from exc
            existing = {obj.Name for obj in document.Objects}
            Import.insert(str(output_step), document.Name)
            document.recompute()
            imported = [obj for obj in document.Objects if obj.Name not in existing]
            imported_count = len(imported)
            if imported_count <= 0:
                raise engine.EngineError(
                    "FreeCAD did not create any objects from the generated STEP file. "
                    f"The STEP remains at {output_step}."
                )
            label = Path(self._input_name).stem
            if self._source_mesh_name:
                source = document.getObject(self._source_mesh_name)
                if source:
                    label = source.Label
                    source.ViewObject.Visibility = False
            # The STEP header names the part after the writer ("Open CASCADE
            # STEP translator ..."); name it after the source instead.
            imported_names = {obj.Name for obj in imported}
            for obj in imported:
                if not any(parent.Name in imported_names for parent in obj.InList):
                    obj.Label = label
            Gui.activeDocument().activeView().fitAll()
            result["mode"] = _mode_label(self._mode)
            result["importedObjects"] = imported_count
            result["documentName"] = document.Label or document.Name
            result["stepPath"] = str(output_step)
            QtWidgets.QMessageBox.information(parent, "STL to STEP", _result_summary(result))
            self._hide_progress()
            self._cleanup()
            self._cleanup_retained()
        except Exception as exc:
            App.Console.PrintError(f"stl2step: {exc}\n")
            self._hide_progress()
            parent.statusBar().showMessage(f"STL to STEP failed: {exc}", 15000)
            retained = f"\n\nTemporary files remain at:\n{temp_directory}"
            QtWidgets.QMessageBox.critical(parent, "STL to STEP", f"Could not import the conversion:\n\n{exc}{retained}")
            if temp_directory and temp_directory not in self._retained_directories:
                self._retained_directories.append(temp_directory)
            self._temp_directory = self._output_step = self._document_name = self._source_mesh_name = self._mode = self._input_name = self._executable = None

    def _cleanup(self):
        if self._temp_directory:
            shutil.rmtree(self._temp_directory, ignore_errors=True)
        self._temp_directory = self._output_step = self._document_name = self._source_mesh_name = self._mode = self._input_name = self._executable = None

    def _cleanup_retained(self):
        for directory in self._retained_directories:
            shutil.rmtree(directory, ignore_errors=True)
        self._retained_directories = []

    @classmethod
    def install(cls):
        command = cls()
        Gui.addCommand(cls.NAME, command)
        return command
