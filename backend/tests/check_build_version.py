"""Canonical image release version and UI contract.

Historical releases numbered v175.59/v175.60 but app health was stuck at 173.1.
v175.61 is the one-time alignment; thereafter prebuilt images receive their
version and exact commit through Docker build arguments supplied by Actions.
"""
import pathlib
import re
import subprocess

ROOT=pathlib.Path(__file__).resolve().parents[2]
MAIN=ROOT/"backend/app/main.py"
SHELL=ROOT/"frontend/src/components/intel/Shell.jsx"
NAV=ROOT/"frontend/src/components/intel/AccessNavigation.jsx"
DOCKER=ROOT/"Dockerfile"

def valid(value):
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]?))?",value or ""):
        return False
    major,*minor=map(int,value.split("."))
    return not minor or major>=175 or minor[0]<=9

def following(value):
    assert valid(value),f"Invalid build version: {value}"
    major,*minor=map(int,value.split("."))
    last=minor[0] if minor else 0
    max_minor=99 if major==175 else 9
    return f"{major+1}.0" if last>=max_minor else f"{major}.{last+1}"

def read_version(source):
    match=re.search(r"'build_version':os\.getenv\('BAWASLU_BUILD_VERSION','([^']+)'\)",source)
    if match:return match.group(1)
    match=re.search(r"'build_version':'([^']+)'",source)
    return match.group(1) if match else None

def docker_version(source):
    match=re.search(r"^ARG BAWASLU_BUILD_VERSION=([0-9]+[.][0-9]+)$",source,re.M)
    return match.group(1) if match else None

def verify():
    backend=MAIN.read_text(encoding="utf-8")
    shell=SHELL.read_text(encoding="utf-8")
    sidebar=NAV.read_text(encoding="utf-8")
    version=read_version(backend)
    assert valid(version),f"Invalid backend fallback build: {version}"
    image_version=docker_version(DOCKER.read_text(encoding="utf-8"))
    assert valid(image_version),f"Invalid Dockerfile build version: {image_version}"
    assert version==image_version,f"Backend/Docker version mismatch: {version} vs {image_version}"
    assert "fetch('/api/health'" in shell
    assert "data-build-version={buildInfo.build_version||'unavailable'}" in shell
    assert "<AccessNavigation access={access} user={user} build={buildInfo}/>" in shell
    assert "build?.build_version" in sidebar
    assert "173.1" not in shell and "173.1" not in sidebar
    assert "BAWASLU_BUILD_COMMIT" in backend
    previous_docker=subprocess.run(["git","show","HEAD^:Dockerfile"],
                                   cwd=ROOT,text=True,capture_output=True,check=False)
    previous=subprocess.run(["git","show","HEAD^:backend/app/main.py"],
                           cwd=ROOT,text=True,capture_output=True,check=False)
    if previous.returncode==0:
        old=read_version(previous.stdout)
        assert old and valid(old),f"Invalid previous version: {old}"
        old_image=docker_version(previous_docker.stdout) if previous_docker.returncode==0 else None
        # Dockerfile is the canonical release sequence; a previous release may
        # have failed to update the backend fallback (v186.4 regression).
        baseline=old_image or old
        assert valid(baseline),f"Invalid previous Docker release: {baseline}"
        if version!=baseline:
            if (old,version)==("173.1","175.61"):
                message=subprocess.run(["git","log","-1","--format=%s"],cwd=ROOT,
                                       text=True,capture_output=True,check=True).stdout.strip()
                assert message.startswith("BAWASLU v175.61:"),"Unapproved version reconciliation"
            else:
                assert version==following(baseline),f"Non-sequential build: {baseline} -> {version}"
    assert following("89.9")=="90.0"
    assert following("175.61")=="175.62"
    assert following("175.99")=="176.0"
    assert following("176.9")=="177.0"
    assert following("177.0")=="177.1"
    assert not valid("89.10")
    assert docker_version("ARG BAWASLU_BUILD_VERSION=186.5\n")=="186.5"
    print("Build metadata contract OK:",version)

if __name__=="__main__":
    verify()
