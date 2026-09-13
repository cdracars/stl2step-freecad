import importlib.util
import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ENGINE_PATH = Path(__file__).parents[1] / "Stl2StepFreeCAD" / "stl2step_freecad" / "engine.py"
SPEC = importlib.util.spec_from_file_location("stl2step_freecad_engine", ENGINE_PATH)
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


class EngineContractTests(unittest.TestCase):
    def test_arguments_default_to_trueform(self):
        args = engine.arguments(Path("part.stl"), Path("part.step"), units="mm")
        self.assertEqual(args[-4:], ["--engine", "trueform", "--units", "mm"])

    def test_arguments_support_verbatim(self):
        args = engine.arguments(Path("part.stl"), Path("part.step"), units="in", mode="verbatim")
        self.assertEqual(args[-4:], ["--engine", "verbatim", "--units", "in"])

    def test_arguments_reject_invalid_options(self):
        with self.assertRaises(ValueError):
            engine.arguments(Path("a"), Path("b"), units="cm")
        with self.assertRaises(ValueError):
            engine.arguments(Path("a"), Path("b"), units="mm", mode="guess")

    def test_parse_result_uses_last_result_line(self):
        result = engine.parse_result(
            "progress\nRESULT {\"ok\":false}\nRESULT " + json.dumps({"ok": True, "solids": 1})
        )
        self.assertEqual(result, {"ok": True, "solids": 1})

    def test_parse_result_rejects_missing_result(self):
        with self.assertRaises(engine.EngineError):
            engine.parse_result("stl2step failed")

    def test_validate_accepts_exit_zero_when_step_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.step"
            output.touch()
            result = engine.validate_conversion(
                'RESULT {"ok":true}', "", 0, output
            )
            self.assertTrue(result["ok"])

    def test_validate_accepts_exit_two_with_warnings(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.step"
            output.touch()
            result = engine.validate_conversion(
                'RESULT {"ok":true,"warnings":["warning"]}', "warning", 2, output
            )
            self.assertEqual(result["warnings"], ["warning"])

    def test_validate_rejects_exit_one_and_includes_stderr(self):
        with self.assertRaisesRegex(engine.EngineError, "bad input"):
            engine.validate_conversion("", "bad input", 1, Path("missing.step"))

    def test_validate_rejects_malformed_result(self):
        with self.assertRaisesRegex(engine.EngineError, "invalid output"):
            engine.validate_conversion("RESULT {not-json}", "invalid output", 1, Path("missing.step"))

    def test_validate_rejects_missing_output(self):
        with self.assertRaisesRegex(engine.EngineError, "STEP file is missing"):
            engine.validate_conversion('RESULT {"ok":true}', "", 0, Path("missing.step"))

    def test_resolve_prefers_configured_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "custom-stl2step"
            executable.touch()
            with mock.patch.dict(os.environ, {"STL2STEP_EXECUTABLE": str(executable)}):
                self.assertEqual(engine.resolve_executable(Path("unused")), executable.resolve())

    def test_resolve_reports_missing_configured_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-stl2step"
            with mock.patch.dict(os.environ, {"STL2STEP_EXECUTABLE": str(missing)}):
                with self.assertRaisesRegex(engine.EngineError, "missing file"):
                    engine.resolve_executable(Path("unused"))


if __name__ == "__main__":
    unittest.main()
