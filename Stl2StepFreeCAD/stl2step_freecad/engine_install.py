"""Verified installation of the pinned stl2step engine.

Importing this module never touches the network. The add-on calls
``download_and_install`` only after the user agrees to download the engine.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PIN_FILE = Path(__file__).with_name("engine-release.json")
MARKER = ".stl2step-install.json"
_CHUNK = 64 * 1024
_MAX_EXTRACTED_BYTES = 512 * 1024 * 1024

# Upstream engine-manifest asset keys -> bin/ directory names used by the add-on.
_PLATFORM_DIRECTORIES = {
    "windows-x64": "windows-x86_64",
    "windows-arm64": "windows-arm64",
    "macos-x64": "macos-x86_64",
    "macos-arm64": "macos-arm64",
    "linux-x64": "linux-x86_64",
    "linux-arm64": "linux-arm64",
}


class InstallError(RuntimeError):
    """The engine could not be downloaded, verified, or installed."""


class InstallCancelled(InstallError):
    """The user cancelled the download."""


def load_pin(path: Path = PIN_FILE) -> dict[str, Any]:
    try:
        pin = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"Could not read the engine pin {path}: {exc}") from exc
    for key in ("upstreamRepository", "tag", "engineVersion", "assets"):
        if key not in pin:
            raise InstallError(f"The engine pin {path} is missing '{key}'.")
    return pin


def platform_key() -> str:
    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if os.name == "nt":
        return f"windows-{architecture}"
    if platform.system() == "Darwin":
        return f"macos-{architecture}"
    return f"linux-{architecture}"


def pinned_asset(pin: dict[str, Any], key: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Return the pinned asset for this platform, or None when there is none."""
    return pin["assets"].get(key or platform_key())


def executable_name(key: str) -> str:
    return "stl2step.exe" if key.startswith("windows-") else "stl2step"


def install_directory(root: Path, pin: dict[str, Any], key: Optional[str] = None) -> Path:
    key = key or platform_key()
    return root / pin["engineVersion"] / _PLATFORM_DIRECTORIES.get(key, key)


def download_url(pin: dict[str, Any], asset: dict[str, Any]) -> str:
    return (
        f"https://github.com/{pin['upstreamRepository']}/releases/download/"
        f"{pin['tag']}/{asset['name']}"
    )


def installed_executable(root: Path, pin: dict[str, Any], key: Optional[str] = None) -> Optional[Path]:
    """Return the downloaded engine when a complete, matching install exists."""
    key = key or platform_key()
    asset = pinned_asset(pin, key)
    if not asset:
        return None
    directory = install_directory(root, pin, key)
    executable = directory / executable_name(key)
    try:
        marker = json.loads((directory / MARKER).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if marker.get("sha256") != asset["sha256"].lower() or not executable.is_file():
        return None
    return executable


def download_and_install(
    root: Path,
    pin: dict[str, Any],
    *,
    version_of: Callable[[Path], str],
    progress: Optional[Callable[[int, int], None]] = None,
    cancelled: Optional[Callable[[], bool]] = None,
    opener: Callable[..., Any] = urlopen,
    key: Optional[str] = None,
) -> Path:
    """Download, verify, and install the pinned engine; return its executable.

    The archive must match the pinned size and SHA-256, unpack without unsafe
    paths, and report the pinned version before it is moved into place. A
    marker written last marks the install complete, so an interrupted install
    is never mistaken for a valid one.
    """
    key = key or platform_key()
    asset = pinned_asset(pin, key)
    if not asset:
        raise InstallError(f"No prebuilt stl2step engine is published for {key}.")
    existing = installed_executable(root, pin, key)
    if existing:
        return existing

    url = download_url(pin, asset)
    if urlparse(url).scheme != "https":
        raise InstallError(f"Refusing to download the engine over a non-HTTPS URL: {url}")

    root.mkdir(parents=True, exist_ok=True)
    staging = root / f".staging-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        archive = staging / asset["name"]
        _download(url, archive, asset, progress, cancelled, opener)
        extracted = staging / "engine"
        _extract(archive, extracted)

        executable = extracted / executable_name(key)
        if not executable.is_file():
            raise InstallError(f"The engine archive did not contain {executable.name}.")
        if not key.startswith("windows-"):
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        try:
            reported = version_of(executable).strip()
        except Exception as exc:
            raise InstallError(f"The downloaded engine could not run: {exc}") from exc
        expected = f"stl2step {pin['engineVersion']}"
        if reported != expected:
            raise InstallError(f"The downloaded engine reported '{reported}', expected '{expected}'.")

        target = install_directory(root, pin, key)
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(extracted, target)
        (target / MARKER).write_text(
            json.dumps({"tag": pin["tag"], "sha256": asset["sha256"].lower()}),
            encoding="utf-8",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    _remove_other_versions(root, pin["engineVersion"])
    return target / executable_name(key)


def _download(url, archive, asset, progress, cancelled, opener) -> None:
    expected_size = int(asset["size"])
    digest = hashlib.sha256()
    received = 0
    request = Request(url, headers={"User-Agent": "stl2step-freecad"})
    try:
        # The URL is built from the pin and checked to be HTTPS above.
        with opener(request, timeout=30) as response, archive.open("wb") as handle:  # nosec B310
            while True:
                if cancelled and cancelled():
                    raise InstallCancelled("The engine download was cancelled.")
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                received += len(chunk)
                if received > expected_size:
                    raise InstallError(
                        f"The engine download is larger than the pinned {expected_size} bytes."
                    )
                digest.update(chunk)
                handle.write(chunk)
                if progress:
                    progress(received, expected_size)
    except OSError as exc:
        raise InstallError(f"Could not download the engine from {url}: {exc}") from exc
    if received != expected_size:
        raise InstallError(
            f"The engine download was {received} bytes, expected {expected_size}."
        )
    actual = digest.hexdigest()
    if actual != asset["sha256"].lower():
        raise InstallError(
            f"The engine download failed its SHA-256 check (expected {asset['sha256']}, got {actual})."
        )


def _extract(archive: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            total = 0
            for info in bundle.infolist():
                name = info.filename.replace("\\", "/")
                parts = PurePosixPath(name).parts
                if name.startswith("/") or ":" in name or ".." in parts:
                    raise InstallError(f"The engine archive contains an unsafe path: {info.filename}")
                total += info.file_size
                if total > _MAX_EXTRACTED_BYTES:
                    raise InstallError("The engine archive is unexpectedly large when unpacked.")
            destination.mkdir()
            bundle.extractall(destination)
    except zipfile.BadZipFile as exc:
        raise InstallError(f"The engine download is not a valid ZIP archive: {exc}") from exc


def _remove_other_versions(root: Path, current_version: str) -> None:
    for child in root.iterdir():
        if child.is_dir() and child.name != current_version and not child.name.startswith(".staging-"):
            # Another FreeCAD instance may still be running an old engine.
            shutil.rmtree(child, ignore_errors=True)
