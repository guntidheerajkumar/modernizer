"""Playwright parity tests: capture legacy behaviour, then compare the migrated app."""
import json
import os
import subprocess
import sys
from pathlib import Path

from .apprunner import running

TEMPLATE = '''import json, os, pathlib, re
import pytest

HERE = pathlib.Path(__file__).parent
ROUTES = json.loads((HERE / "routes.json").read_text())
BASE = os.environ["BASE_URL"].rstrip("/")
MODE = os.environ.get("MODE", "compare")          # capture | compare
BASELINE = pathlib.Path(os.environ.get("BASELINE", HERE / "baseline.json"))
_store = {}


@pytest.fixture(scope="session", autouse=True)
def _baseline():
    base = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    yield base
    if MODE == "capture":
        BASELINE.write_text(json.dumps(_store, indent=2))


def snapshot(page, route):
    resp = page.goto(BASE + route, wait_until="networkidle")
    is_html = bool(resp) and "html" in resp.headers.get("content-type", "")
    return {
        "status": resp.status if resp else None,
        "title": page.title() if is_html else "",
        "text": re.sub(r"\\s+", " ", page.inner_text("body")).strip() if is_html else "",
        "links": page.locator("a").count() if is_html else 0,
        "forms": page.locator("form").count() if is_html else 0,
    }


@pytest.mark.parametrize("route", ROUTES)
def test_route_parity(page, route, _baseline):
    snap = snapshot(page, route)
    if MODE == "capture":
        _store[route] = snap
        return
    assert route in _baseline, f"No baseline captured for {route}"
    assert snap == _baseline[route], f"Behaviour changed on {route}"
'''


def write(repo: Path, kb: dict) -> Path:
    d = repo / "tests" / "e2e"
    d.mkdir(parents=True, exist_ok=True)
    routes = sorted({r for p in kb["projects"] for r in p["routes"] + p["pages"]} | {"/"})
    (d / "routes.json").write_text(json.dumps(routes, indent=2))
    (d / "test_parity.py").write_text(TEMPLATE)
    return d


def run(repo: Path, mode: str, run_cmd: str, url: str) -> tuple[bool, str]:
    env = {**os.environ, "BASE_URL": url, "MODE": mode}
    with running(run_cmd, url, repo):
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/e2e", "-q"],
                           cwd=repo, env=env, capture_output=True, text=True)
    return r.returncode == 0, r.stdout + r.stderr
