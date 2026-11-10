import struct
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from sadie.germlines.builders.blast import BlastDBBuilder
from sadie.germlines.scripts.build_internal_data import build_blast_db
from sadie.utility import binaries
from sadie.utility.binaries import BUNDLED_PLATFORMS, bundled_binary, find_binary
from sadie.utility.exception import BinaryNotFoundError

AIRR_BIN_DIR = Path(binaries.__file__).parent.parent / "airr" / "bin"
REFERENCE_BIN_DIR = Path(binaries.__file__).parent.parent / "reference" / "bin"

MACHO_CPU_TYPES = {0x01000007: "x86_64", 0x0100000C: "arm64"}
ELF_MACHINES = {0x3E: "x86_64", 0xB7: "aarch64"}
PE_MACHINES = {0x8664: "x86_64", 0xAA64: "arm64"}
EXPECTED_ARCH = {"darwin": "x86_64", "darwin-arm64": "arm64", "linux": "x86_64", "windows": "x86_64"}


def architecture_from_header(path: Path) -> str:
    head = path.read_bytes()[:1024]
    if head[:4] in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
        return MACHO_CPU_TYPES[struct.unpack("<I", head[4:8])[0]]
    if head[:4] == b"\x7fELF":
        return ELF_MACHINES[struct.unpack("<H", head[18:20])[0]]
    if head[:2] == b"MZ":
        pe_offset = struct.unpack("<I", head[60:64])[0]
        return PE_MACHINES[struct.unpack("<H", head[pe_offset + 4 : pe_offset + 6])[0]]
    raise ValueError(f"{path} is not a Mach-O, ELF or PE executable")


@pytest.fixture
def fake_bin_dir(tmp_path: Path) -> Path:
    for subdir in set(BUNDLED_PLATFORMS.values()):
        (tmp_path / subdir).mkdir()
        (tmp_path / subdir / ("tool.exe" if subdir == "windows" else "tool")).write_text("")
    return tmp_path


@pytest.mark.parametrize(
    ("system", "machine", "expected_subdir"),
    [
        ("darwin", "arm64", "darwin-arm64"),
        ("darwin", "x86_64", "darwin"),
        ("linux", "x86_64", "linux"),
        ("windows", "amd64", "windows"),
        ("windows", "arm64", "windows"),
    ],
)
def test_bundled_binary_picks_directory_for_each_os_and_chipset(fake_bin_dir, system, machine, expected_subdir):
    expected_name = "tool.exe" if system == "windows" else "tool"

    assert bundled_binary("tool", fake_bin_dir, system, machine) == fake_bin_dir / expected_subdir / expected_name


@pytest.mark.parametrize(("system", "machine"), [("linux", "aarch64"), ("darwin", "ppc"), ("freebsd", "x86_64")])
def test_bundled_binary_returns_none_for_unsupported_pair(fake_bin_dir, system, machine):
    assert bundled_binary("tool", fake_bin_dir, system, machine) is None


def test_find_binary_prefers_bundled_over_path(fake_bin_dir, monkeypatch):
    monkeypatch.setattr(binaries, "host_platform", lambda: ("linux", "x86_64"))
    monkeypatch.setattr(binaries.shutil, "which", lambda tool: "/usr/local/bin/tool")

    assert find_binary("tool", fake_bin_dir) == fake_bin_dir / "linux" / "tool"


def test_find_binary_path_first_prefers_path_over_bundled(fake_bin_dir, monkeypatch):
    monkeypatch.setattr(binaries, "host_platform", lambda: ("linux", "x86_64"))
    monkeypatch.setattr(binaries.shutil, "which", lambda tool: "/usr/local/bin/tool")

    assert find_binary("tool", fake_bin_dir, path_first=True) == Path("/usr/local/bin/tool")


def test_find_binary_path_first_falls_back_to_bundled(fake_bin_dir, monkeypatch):
    monkeypatch.setattr(binaries, "host_platform", lambda: ("linux", "x86_64"))
    monkeypatch.setattr(binaries.shutil, "which", lambda tool: None)

    assert find_binary("tool", fake_bin_dir, path_first=True) == fake_bin_dir / "linux" / "tool"


def test_germline_builders_take_makeblastdb_from_path_before_bundle(tmp_path, monkeypatch):
    commands = []
    monkeypatch.setattr(binaries, "host_platform", lambda: ("linux", "x86_64"))
    monkeypatch.setattr(binaries.shutil, "which", lambda tool: "/usr/local/bin/makeblastdb")
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: commands.append(cmd) or SimpleNamespace(stdout=""))

    BlastDBBuilder()._run_makeblastdb(tmp_path / "human_V.fasta", "V")
    build_blast_db(tmp_path / "human_V.fasta", tmp_path / "human_V")

    assert [cmd[0] for cmd in commands] == ["/usr/local/bin/makeblastdb"] * 2


def test_find_binary_falls_back_to_path_for_unsupported_pair(fake_bin_dir, monkeypatch):
    monkeypatch.setattr(binaries, "host_platform", lambda: ("linux", "aarch64"))
    monkeypatch.setattr(binaries.shutil, "which", lambda tool: "/usr/local/bin/tool")

    assert find_binary("tool", fake_bin_dir) == Path("/usr/local/bin/tool")


def test_find_binary_without_bundle_or_path_names_os_and_chipset(fake_bin_dir, monkeypatch):
    monkeypatch.setattr(binaries, "host_platform", lambda: ("linux", "aarch64"))
    monkeypatch.setattr(binaries.shutil, "which", lambda tool: None)

    with pytest.raises(BinaryNotFoundError, match="no tool for linux/aarch64"):
        find_binary("tool", fake_bin_dir)


def test_host_platform_reads_lowercase_system_and_machine(monkeypatch):
    monkeypatch.setattr(binaries.platform, "system", lambda: "Windows")
    monkeypatch.setattr(binaries.platform, "machine", lambda: "AMD64")

    assert binaries.host_platform() == ("windows", "amd64")


@pytest.mark.parametrize(
    "binary",
    sorted(p for bin_dir in (AIRR_BIN_DIR, REFERENCE_BIN_DIR) for p in bin_dir.glob("*/*") if p.suffix != ".txt"),
    ids=lambda p: f"{p.parent.parent.parent.name}/{p.parent.name}/{p.name}",
)
def test_every_bundled_binary_matches_its_directory_architecture(binary):
    assert architecture_from_header(binary) == EXPECTED_ARCH[binary.parent.name]
