import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from verify_release_archive import verify_archive


COMPLETE = [
    "stl2step-freecad/LICENSE",
    "stl2step-freecad/LICENSE.stl2step",
    "stl2step-freecad/README.md",
    "stl2step-freecad/THIRD_PARTY_NOTICES.md",
    "stl2step-freecad/package.xml",
    "stl2step-freecad/freecad/stl2step/__init__.py",
    "stl2step-freecad/freecad/stl2step/init_gui.py",
    "stl2step-freecad/freecad/stl2step/engine-release.json",
    "stl2step-freecad/freecad/stl2step/bin/windows-x86_64/stl2step.exe",
    "stl2step-freecad/freecad/stl2step/bin/windows-x86_64/TKernel.dll",
]


class ReleaseArchiveTests(unittest.TestCase):
    def build(self, directory, files, contents=lambda name: "test"):
        archive = Path(directory) / "release.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for name in files:
                bundle.writestr(name, contents(name))
        return archive

    def test_accepts_complete_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            verify_archive(self.build(directory, COMPLETE))

    def test_rejects_missing_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                verify_archive(self.build(directory, ["stl2step-freecad/LICENSE"]))

    def test_rejects_legacy_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.build(directory, COMPLETE + ["stl2step-freecad/Stl2StepFreeCAD/InitGui.py"])
            with self.assertRaisesRegex(ValueError, "legacy layout"):
                verify_archive(archive)

    def test_rejects_namespace_init(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.build(directory, COMPLETE + ["stl2step-freecad/freecad/__init__.py"])
            with self.assertRaisesRegex(ValueError, "namespace package"):
                verify_archive(archive)

    def test_rejects_stale_reference_inside_text_file(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.build(
                directory, COMPLETE,
                lambda name: "https://github.com/cdracars/stl2step\n" if name.endswith("README.md") else "test",
            )
            with self.assertRaises(ValueError):
                verify_archive(archive)

    def test_allows_this_repository_url(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.build(
                directory, COMPLETE,
                lambda name: "https://github.com/cdracars/stl2step-freecad" if name.endswith("package.xml") else "test",
            )
            verify_archive(archive)


if __name__ == "__main__":
    unittest.main()
