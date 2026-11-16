"""Build/test helpers. Legacy (non SDK-style) projects need msbuild; the rest use dotnet."""
import shutil
import subprocess
from pathlib import Path


def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)


def build(repo: Path, target: str) -> tuple[bool, str]:
    p = repo / target
    sdk = 'Sdk="' in p.read_text(errors="ignore") if p.suffix.endswith("proj") else True
    if not sdk:
        ms = shutil.which("msbuild") or shutil.which("MSBuild.exe")
        if not ms:
            return False, "msbuild not found. Legacy projects must be built on Windows with VS Build Tools."
        return _run([ms, str(p), "/restore", "/v:m", "/nologo"], repo)
    if not shutil.which("dotnet"):
        return False, "dotnet SDK not found on PATH."
    return _run(["dotnet", "build", str(p), "-nologo", "-v", "q"], repo)


def test(repo: Path, target: str):
    if not shutil.which("dotnet"):
        return False, "dotnet SDK not found."
    return _run(["dotnet", "test", target, "-nologo", "-v", "q"], repo)
