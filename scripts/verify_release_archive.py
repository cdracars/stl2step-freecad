"""Validate the contents of a packaged FreeCAD add-on archive."""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path


def verify_archive(archive: Path, addon_dir: str = "stl2step-freecad") -> None:
    prefix = addon_dir.rstrip("/") + "/"
    package = f"{prefix}freecad/stl2step/"
    stale_fork = re.compile(r"cdracars/stl2step(?:[/'\"\s]|$)")
    with zipfile.ZipFile(archive) as bundle:
        names = {name.replace("\\", "/") for name in bundle.namelist()}
        required = {
            f"{prefix}LICENSE",
            f"{prefix}LICENSE.stl2step",
            f"{prefix}README.md",
            f"{prefix}THIRD_PARTY_NOTICES.md",
            f"{prefix}package.xml",
            f"{package}__init__.py",
            f"{package}init_gui.py",
            f"{package}engine-release.json",
            f"{package}bin/windows-x86_64/stl2step.exe",
        }
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"archive is missing required files: {', '.join(missing)}")
        if f"{prefix}freecad/__init__.py" in names:
            raise ValueError("archive must not contain freecad/__init__.py; it is a namespace package")
        legacy = sorted(
            name for name in names
            if name.endswith(("/Init.py", "/InitGui.py")) or "/Stl2StepFreeCAD/" in f"/{name}"
        )
        if legacy:
            raise ValueError(f"archive contains legacy layout files: {', '.join(legacy)}")
        dlls = [name for name in names if name.startswith(f"{package}bin/windows-x86_64/") and name.lower().endswith(".dll")]
        if not dlls:
            raise ValueError("archive contains no engine runtime DLLs")
        if any(stale_fork.search(name.lower()) or "engine-pin.json" in name.lower() for name in names):
            raise ValueError("archive contains a stale fork or legacy engine pin reference")
        text_files = (
            name for name in bundle.namelist()
            if name.lower().endswith((".json", ".md", ".txt", ".xml"))
        )
        for name in text_files:
            contents = bundle.read(name).decode("utf-8", errors="replace").lower()
            if stale_fork.search(contents) or "engine-pin.json" in contents:
                raise ValueError(f"archive file contains a stale fork or legacy engine pin reference: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--addon-dir", default="stl2step-freecad")
    args = parser.parse_args()
    verify_archive(args.archive, args.addon_dir)
    print(f"Validated release archive: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
