"""Step 1: get the solution into an isolated workspace (never touch the original)."""
import re
import shutil
import subprocess
from pathlib import Path

IGNORE = shutil.ignore_patterns("bin", "obj", "packages", "node_modules", ".vs")


def git(repo: Path, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check)


def prepare(src: str, workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    if re.match(r"^(https?://|git@)", src):
        name = re.sub(r"\.git$", "", src.rstrip("/").split("/")[-1])
        dest = workspace / name
        if dest.exists():
            raise SystemExit(f"{dest} already exists; delete it or choose another workspace.")
        subprocess.run(["git", "clone", src, str(dest)], check=True)
        return dest
    p = Path(src).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"Path not found: {p}")
    if p.is_file():
        p = p.parent
    dest = workspace / p.name
    if dest.exists():
        raise SystemExit(f"{dest} already exists; delete it or choose another workspace.")
    shutil.copytree(p, dest, ignore=IGNORE)
    if not (dest / ".git").exists():
        git(dest, "init")
        git(dest, "add", "-A")
        git(dest, "-c", "user.name=modernizer", "-c", "user.email=m@local",
            "commit", "-m", "Baseline snapshot before modernization")
    return dest


def create_branch(repo: Path, target_tfm: str) -> str:
    branch = f"modernize/{target_tfm}"
    git(repo, "checkout", "-B", branch)
    return branch


def commit(repo: Path, msg: str):
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=modernizer", "-c", "user.email=m@local",
        "commit", "-m", msg, "--allow-empty", check=False)
