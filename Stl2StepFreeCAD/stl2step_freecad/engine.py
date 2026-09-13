"""Process-isolated adapter for the stl2step CLI."""

from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any


class EngineError(RuntimeError):
    """The converter could not be located or did not produce a usable result."""


def _bundled_relative_path() -> Path:
    machine = platform.machine().lower()
    if os.name == "nt":
        return Path("bin") / "windows-x86_64" / "stl2step.exe"
    if platform.system() == "Darwin":
        architecture = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
        return Path("bin") / f"macos-{architecture}" / "stl2step"
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    return Path("bin") / f"linux-{architecture}" / "stl2step"


def resolve_executable(addon_directory: Path) -> Path:
    configured = os.environ.get("STL2STEP_EXECUTABLE")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        raise EngineError(f"STL2STEP_EXECUTABLE points to a missing file: {candidate}")

    bundled = addon_directory / _bundled_relative_path()
    if bundled.is_file():
        return bundled.resolve()
    discovered = shutil.which("stl2step")
    if discovered:
        return Path(discovered).resolve()
    raise EngineError(
        "Could not find stl2step. Set STL2STEP_EXECUTABLE, put it on PATH, "
        f"or install the platform binary at {bundled}."
    )


def parse_result(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith("RESULT "):
            try:
                result = json.loads(line[len("RESULT "):])
            except json.JSONDecodeError as exc:
                raise EngineError(f"Invalid RESULT JSON: {exc}") from exc
            if not isinstance(result, dict):
                raise EngineError("RESULT payload was not a JSON object")
            return result
    raise EngineError("stl2step did not emit a RESULT line")


def validate_conversion(
    stdout: str,
    stderr: str,
    exit_code: int,
    output_step: Path,
) -> dict[str, Any]:
    """Validate the CLI contract and return its RESULT payload.

    The engine uses exit code 2 for a completed conversion with warnings.
    Exit code 1 (and any other unexpected code) is always a failure, even if
    a partial RESULT line happened to be emitted.
    """
    try:
        result = parse_result(stdout)
    except EngineError as exc:
        detail = stderr.strip() or str(exc)
        raise EngineError(f"stl2step exited {exit_code}: {detail}") from exc

    if exit_code not in {0, 2}:
        detail = result.get("error") or stderr.strip() or "conversion failed"
        raise EngineError(f"stl2step exited {exit_code}: {detail}")
    if not result.get("ok"):
        detail = result.get("error") or stderr.strip() or "conversion failed"
        raise EngineError(f"stl2step exited {exit_code}: {detail}")
    if not output_step.is_file():
        raise EngineError("stl2step reported success but the STEP file is missing")
    return result


def arguments(
    input_stl: Path,
    output_step: Path,
    *,
    units: str,
    mode: str = "trueform",
) -> list[str]:
    if units not in {"mm", "in"}:
        raise ValueError(f"unsupported STL units: {units}")
    if mode not in {"trueform", "verbatim"}:
        raise ValueError(f"unsupported conversion mode: {mode}")
    return [
        str(input_stl), "-o", str(output_step), "--quiet", "--no-verify",
        "--engine", mode, "--units", units,
    ]
