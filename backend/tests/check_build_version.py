"""Fail CI when a commit omits or mismatches the required sidebar build-version bump."""
import pathlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]
backend = (root / "backend/app/main.py").read_text(encoding="utf-8")
sidebar = (root / "frontend/src/components/intel/AccessNavigation.jsx").read_text(encoding="utf-8")
server = re.search(r"'build_version':'([0-9.]+)'", backend)
client = re.search(r"useState\(\{build_version:'([0-9.]+)'", sidebar)
assert server and client, "Missing server or sidebar build version"
assert server.group(1) == client.group(1), "Backend and sidebar versions differ"
previous = subprocess.run(["git","show","HEAD^:backend/app/main.py"],cwd=root,text=True,capture_output=True,check=False)
if previous.returncode == 0:
    old = re.search(r"'build_version':'([0-9.]+)'", previous.stdout)
    assert old and old.group(1) != server.group(1), "Every commit must bump the build version"
print("Build version OK:",server.group(1))
