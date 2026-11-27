"""Locate bundled NCBI executables (igblastn, makeblastdb) by operating system and chipset."""

import platform
import shutil
from pathlib import Path

from sadie.utility.exception import BinaryNotFoundError

# (platform.system().lower(), platform.machine().lower()) -> subdirectory under a package bin/ dir.
# Pairs not listed here (for example linux/aarch64) have no bundled binary and use PATH.
BUNDLED_PLATFORMS = {
    ("darwin", "arm64"): "darwin-arm64",
    ("darwin", "x86_64"): "darwin",
    ("linux", "x86_64"): "linux",
    ("windows", "amd64"): "windows",
    ("windows", "arm64"): "windows",  # x64 binaries; Windows on ARM runs them under emulation
}


def host_platform() -> tuple[str, str]:
    return platform.system().lower(), platform.machine().lower()


def bundled_binary(tool: str, bin_dir: Path, system: str, machine: str) -> Path | None:
    """Path of the bundled `tool` for the given OS and chipset, or None if sadie ships none."""
    subdir = BUNDLED_PLATFORMS.get((system, machine))
    if subdir is None:
        return None
    exe = bin_dir / subdir / (f"{tool}.exe" if system == "windows" else tool)
    return exe if exe.is_file() else None


def find_binary(tool: str, bin_dir: Path, path_first: bool = False) -> Path:
    """Bundled `tool` for this host, then `tool` on PATH (PATH first if `path_first`), else BinaryNotFoundError."""
    system, machine = host_platform()
    bundled = bundled_binary(tool, bin_dir, system, machine)
    on_path = shutil.which(tool)
    found = (on_path or bundled) if path_first else (bundled or on_path)
    if found:
        return Path(found)
    raise BinaryNotFoundError(tool, system, machine)
