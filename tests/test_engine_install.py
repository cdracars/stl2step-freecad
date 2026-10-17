import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "freecad" / "stl2step" / "engine_install.py"
SPEC = importlib.util.spec_from_file_location("stl2step_freecad_engine_install", MODULE_PATH)
engine_install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine_install)

KEY = "windows-x64"


def make_archive(entries=None):
    entries = entries or {"stl2step.exe": b"engine", "TKernel.dll": b"runtime"}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for name, data in entries.items():
            bundle.writestr(name, data)
    return buffer.getvalue()


def make_pin(data, *, size=None, sha256=None, version="1.4.3"):
    return {
        "upstreamRepository": "BlinkingSun/stl2step",
        "tag": f"v{version}",
        "engineVersion": version,
        "assets": {
            KEY: {
                "name": f"stl2step-engine-v{version}-windows-x64.zip",
                "sha256": sha256 or hashlib.sha256(data).hexdigest(),
                "size": len(data) if size is None else size,
            }
        },
    }


class FakeOpener:
    def __init__(self, data):
        self.data = data
        self.urls = []

    def __call__(self, request, timeout):
        self.urls.append(request.full_url)
        return io.BytesIO(self.data)


def refuse_network(request, timeout):
    raise AssertionError("unexpected download")


class EngineInstallTests(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name) / "stl2step-engine"

    def tearDown(self):
        self._directory.cleanup()

    def install(self, data, pin, **kwargs):
        kwargs.setdefault("opener", FakeOpener(data))
        kwargs.setdefault("version_of", lambda executable: f"stl2step {pin['engineVersion']}\n")
        return engine_install.download_and_install(self.root, pin, key=KEY, **kwargs)

    def assert_nothing_installed(self, pin):
        self.assertIsNone(engine_install.installed_executable(self.root, pin, KEY))
        leftovers = [path.name for path in self.root.iterdir()] if self.root.exists() else []
        self.assertEqual(leftovers, [])

    def test_installs_verified_engine(self):
        data = make_archive()
        pin = make_pin(data)
        opener = FakeOpener(data)
        progress = []
        executable = self.install(data, pin, opener=opener, progress=lambda r, t: progress.append((r, t)))

        self.assertEqual(executable, self.root / "1.4.3" / "windows-x86_64" / "stl2step.exe")
        self.assertEqual(executable.read_bytes(), b"engine")
        self.assertTrue((executable.parent / "TKernel.dll").is_file())
        self.assertEqual(engine_install.installed_executable(self.root, pin, KEY), executable)
        self.assertEqual(opener.urls, [
            "https://github.com/BlinkingSun/stl2step/releases/download/v1.4.3/"
            "stl2step-engine-v1.4.3-windows-x64.zip"
        ])
        self.assertEqual(progress[-1], (len(data), len(data)))
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["1.4.3"])

    def test_existing_install_skips_download(self):
        data = make_archive()
        pin = make_pin(data)
        first = self.install(data, pin)
        self.assertEqual(self.install(data, pin, opener=refuse_network), first)

    def test_rejects_hash_mismatch(self):
        data = make_archive()
        pin = make_pin(data, sha256="0" * 64)
        with self.assertRaisesRegex(engine_install.InstallError, "SHA-256"):
            self.install(data, pin)
        self.assert_nothing_installed(pin)

    def test_rejects_short_download(self):
        data = make_archive()
        pin = make_pin(data, size=len(data) + 1)
        with self.assertRaisesRegex(engine_install.InstallError, "bytes"):
            self.install(data, pin)
        self.assert_nothing_installed(pin)

    def test_rejects_oversized_download(self):
        data = make_archive()
        pin = make_pin(data, size=len(data) - 1)
        with self.assertRaisesRegex(engine_install.InstallError, "larger"):
            self.install(data, pin)
        self.assert_nothing_installed(pin)

    def test_rejects_path_traversal(self):
        data = make_archive({"stl2step.exe": b"engine", "../escaped.exe": b"evil"})
        pin = make_pin(data)
        with self.assertRaisesRegex(engine_install.InstallError, "unsafe path"):
            self.install(data, pin)
        self.assertFalse((self.root.parent / "escaped.exe").exists())
        self.assert_nothing_installed(pin)

    def test_rejects_archive_without_executable(self):
        data = make_archive({"README.txt": b"no engine"})
        pin = make_pin(data)
        with self.assertRaisesRegex(engine_install.InstallError, "did not contain"):
            self.install(data, pin)
        self.assert_nothing_installed(pin)

    def test_rejects_wrong_engine_version(self):
        data = make_archive()
        pin = make_pin(data)
        with self.assertRaisesRegex(engine_install.InstallError, "expected 'stl2step 1.4.3'"):
            self.install(data, pin, version_of=lambda executable: "stl2step 9.9.9")
        self.assert_nothing_installed(pin)

    def test_reports_engine_that_cannot_run(self):
        data = make_archive()
        pin = make_pin(data)

        def broken(executable):
            raise RuntimeError("exit code 1")

        with self.assertRaisesRegex(engine_install.InstallError, "could not run"):
            self.install(data, pin, version_of=broken)
        self.assert_nothing_installed(pin)

    def test_cancel_leaves_nothing_behind(self):
        data = make_archive()
        pin = make_pin(data)
        with self.assertRaises(engine_install.InstallCancelled):
            self.install(data, pin, cancelled=lambda: True)
        self.assert_nothing_installed(pin)

    def test_network_error_is_reported(self):
        data = make_archive()
        pin = make_pin(data)

        def offline(request, timeout):
            raise OSError("no route to host")

        with self.assertRaisesRegex(engine_install.InstallError, "no route to host"):
            self.install(data, pin, opener=offline)
        self.assert_nothing_installed(pin)

    def test_unsupported_platform_is_reported(self):
        data = make_archive()
        pin = make_pin(data)
        with self.assertRaisesRegex(engine_install.InstallError, "linux-x64"):
            engine_install.download_and_install(
                self.root, pin, key="linux-x64", version_of=str, opener=refuse_network
            )
        self.assertIsNone(engine_install.installed_executable(self.root, pin, "linux-x64"))

    def test_new_version_replaces_old_versions(self):
        old_data = make_archive()
        old_pin = make_pin(old_data, version="1.4.3")
        self.install(old_data, old_pin)
        new_data = make_archive({"stl2step.exe": b"newer engine"})
        new_pin = make_pin(new_data, version="1.5.0")
        executable = self.install(new_data, new_pin)
        self.assertEqual(executable.read_bytes(), b"newer engine")
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["1.5.0"])

    def test_install_without_marker_is_not_trusted(self):
        data = make_archive()
        pin = make_pin(data)
        executable = self.install(data, pin)
        (executable.parent / engine_install.MARKER).unlink()
        self.assertIsNone(engine_install.installed_executable(self.root, pin, KEY))

    def test_install_for_different_hash_is_not_trusted(self):
        data = make_archive()
        pin = make_pin(data)
        self.install(data, pin)
        repinned = make_pin(data, sha256="f" * 64)
        self.assertIsNone(engine_install.installed_executable(self.root, repinned, KEY))

    def test_shipped_pin_is_well_formed(self):
        pin = engine_install.load_pin()
        asset = engine_install.pinned_asset(pin, KEY)
        self.assertIsNotNone(asset)
        self.assertRegex(asset["sha256"], r"^[0-9a-f]{64}$")
        self.assertGreater(int(asset["size"]), 0)
        self.assertTrue(engine_install.download_url(pin, asset).startswith("https://github.com/"))

    def test_load_pin_rejects_incomplete_file(self):
        path = Path(self._directory.name) / "pin.json"
        path.write_text(json.dumps({"tag": "v1"}), encoding="utf-8")
        with self.assertRaisesRegex(engine_install.InstallError, "missing"):
            engine_install.load_pin(path)


if __name__ == "__main__":
    unittest.main()
