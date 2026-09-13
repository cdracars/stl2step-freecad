import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from verify_release_archive import verify_archive


class ReleaseArchiveTests(unittest.TestCase):
    def test_accepts_complete_archive(self):
        files = [
            "LICENSE", "LICENSE.stl2step", "README.md", "THIRD_PARTY_NOTICES.md",
            "config/engine-release.json", "Stl2StepFreeCAD/package.xml",
            "Stl2StepFreeCAD/bin/windows-x86_64/stl2step.exe",
            "Stl2StepFreeCAD/bin/windows-x86_64/TKernel.dll",
        ]
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "release.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for name in files:
                    bundle.writestr(name, "test")
            verify_archive(archive)

    def test_rejects_missing_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "release.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("LICENSE", "test")
            with self.assertRaises(ValueError):
                verify_archive(archive)

    def test_rejects_stale_reference_inside_text_file(self):
        files = [
            "LICENSE", "LICENSE.stl2step", "README.md", "THIRD_PARTY_NOTICES.md",
            "config/engine-release.json", "Stl2StepFreeCAD/package.xml",
            "Stl2StepFreeCAD/bin/windows-x86_64/stl2step.exe",
            "Stl2StepFreeCAD/bin/windows-x86_64/TKernel.dll",
        ]
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "release.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for name in files:
                    bundle.writestr(name, "https://github.com/cdracars/stl2step\n" if name == "README.md" else "test")
            with self.assertRaises(ValueError):
                verify_archive(archive)

    def test_allows_this_repository_url(self):
        files = [
            "LICENSE", "LICENSE.stl2step", "README.md", "THIRD_PARTY_NOTICES.md",
            "config/engine-release.json", "Stl2StepFreeCAD/package.xml",
            "Stl2StepFreeCAD/bin/windows-x86_64/stl2step.exe",
            "Stl2StepFreeCAD/bin/windows-x86_64/TKernel.dll",
        ]
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "release.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for name in files:
                    value = "https://github.com/cdracars/stl2step-freecad" if name.endswith("package.xml") else "test"
                    bundle.writestr(name, value)
            verify_archive(archive)
