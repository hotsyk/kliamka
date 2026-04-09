"""Smoke tests for built package artifacts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SMOKE_DIR = ROOT / ".tmp" / "packaging-smoke"
MIN_PYTHON = (3, 11)


@pytest.fixture(scope="session")
def built_artifacts() -> tuple[Path, Path]:
    if sys.version_info < MIN_PYTHON:
        pytest.skip("packaging smoke tests require Python 3.11+")

    if shutil.which("uv") is None:
        pytest.skip("uv is required for packaging smoke tests")

    if DIST.exists():
        shutil.rmtree(DIST)

    subprocess.run(
        ["uv", "build", "--python", sys.executable],
        cwd=ROOT,
        check=True,
    )

    wheel = next(DIST.glob("*.whl"), None)
    sdist = next(DIST.glob("*.tar.gz"), None)

    assert wheel is not None, "wheel artifact was not built"
    assert sdist is not None, "sdist artifact was not built"

    smoke_dist = SMOKE_DIR / "dist"
    if smoke_dist.exists():
        shutil.rmtree(smoke_dist)
    smoke_dist.mkdir(parents=True, exist_ok=True)

    wheel_copy = smoke_dist / wheel.name
    sdist_copy = smoke_dist / sdist.name
    shutil.copy2(wheel, wheel_copy)
    shutil.copy2(sdist, sdist_copy)

    return wheel_copy.resolve(), sdist_copy.resolve()


def _python_in(env_dir: Path) -> Path:
    if os.name == "nt":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def _bootstrap_build_backend(python_bin: Path) -> None:
    subprocess.run(
        [
            str(python_bin),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "setuptools>=68.0",
            "wheel",
        ],
        cwd=ROOT,
        check=True,
    )


def _run_packaging_smoke(artifact: Path, env_dir: Path) -> None:
    if env_dir.exists():
        shutil.rmtree(env_dir)

    venv.create(env_dir, with_pip=True)
    python_bin = _python_in(env_dir)

    install_command = [
        str(python_bin),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
    ]

    if artifact.suffixes[-2:] == [".tar", ".gz"]:
        _bootstrap_build_backend(python_bin)
        install_command.extend(["--no-build-isolation", str(artifact)])
    else:
        install_command.append(str(artifact))

    subprocess.run(
        install_command,
        cwd=ROOT,
        check=True,
    )

    subprocess.run(
        [
            str(python_bin),
            "-c",
            (
                "import kliamka; "
                "assert kliamka.__version__ == '0.6.0'; "
                "assert hasattr(kliamka, 'kliamka_cli'); "
                "assert hasattr(kliamka, 'KliamkaArgClass')"
            ),
        ],
        cwd=ROOT,
        check=True,
    )


@pytest.mark.packaging
def test_wheel_installs_and_imports(built_artifacts: tuple[Path, Path]) -> None:
    wheel, _ = built_artifacts
    _run_packaging_smoke(wheel, SMOKE_DIR / "wheel")


@pytest.mark.packaging
def test_sdist_installs_and_imports(built_artifacts: tuple[Path, Path]) -> None:
    _, sdist = built_artifacts
    _run_packaging_smoke(sdist, SMOKE_DIR / "sdist")
