"""Require one increment per commit and synchronized sidebar/backend build versions.

Sequence: 89, 89.1, ... 89.9, 90, 90.1, ... 90.9, 91.
The one-time migration from legacy 89.11 to 90 corrects the previous bad scheme.
"""
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend/app/main.py"
SIDEBAR = ROOT / "frontend/src/components/intel/AccessNavigation.jsx"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9])?\Z")


def following(value):
    assert VERSION.fullmatch(value), f"Invalid preceding build version: {value}"
    major, *minor = value.split(".")
    if not minor:
        return f"{major}.1"
    if minor[0] == "9":
        return f"{int(major) + 1}.0"
    return f"{major}.{int(minor[0]) + 1}"


def read_version(source, pattern, name):
    match = re.search(pattern, source)
    assert match, f"Missing {name} build version"
    value = match.group(1)
    assert VERSION.fullmatch(value), (
        f"Invalid {name} build version {value}; use 90.0, 90.1 ... 90.9, 91.0, not .10"
    )
    return value


def verify():
    backend = BACKEND.read_text(encoding="utf-8")
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    server = read_version(backend, r"'build_version':'([^']+)'", "backend")
    # AccessNavigation intentionally fetches the current backend health version
    # instead of freezing a stale static value in shipped JavaScript.
    if "useState({build_version:null})" in sidebar and "fetch('/api/health'" in sidebar:
        assert "build.build_version" in sidebar, "Sidebar must show fetched backend build"
        client = server
    else:
        client = read_version(sidebar, r"useState\(\{build_version:'([^']+)'", "sidebar")
    assert server == client, f"Build mismatch: backend {server}, sidebar {client}"

    previous = subprocess.run(
        ["git", "show", "HEAD^:backend/app/main.py"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if previous.returncode == 0:
        match = re.search(r"'build_version':'([^']+)'", previous.stdout)
        assert match, "Previous commit missing a build version"
        old = match.group(1)
        if old == "89.11":
            expected = "90"  # One-time repair for the existing invalid version.
        else:
            expected = following(old)
        assert server == expected, (
            f"Each commit must advance exactly one build: {old} -> {expected}; got {server}"
        )
    assert following("89.9") == "90.0"
    assert following("90") == "90.1"
    assert following("90.9") == "91.0"
    assert not VERSION.fullmatch("89.10")
    assert not VERSION.fullmatch("89.11")
    print("Build version OK:", server)


if __name__ == "__main__":
    verify()
