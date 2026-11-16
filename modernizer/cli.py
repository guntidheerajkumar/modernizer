import argparse
import json
import shutil
import subprocess
from pathlib import Path

from rich.prompt import Confirm, IntPrompt, Prompt

from . import scanner, source
from .config import available_targets
from .llm import load_skills, run_agent
from .migrate import run as run_migration
from .ui import Steps, banner, console, table


def enrich_kb(repo: Path, kb: dict):
    """LLM pass: business-level understanding that static parsing can't give."""
    for p in kb["projects"]:
        text = run_agent(
            f"Analyse project `{p['path']}`. Write a concise markdown summary: purpose, main "
            "features/business flows, entry points, external dependencies (DB, services, files), "
            "and behaviours that MUST be preserved in a migration. Read-only; do not edit files.",
            "You are documenting a legacy .NET app for a migration team.", repo,
            max_turns=15, tools=("Read", "Glob", "Grep"))
        (repo / ".modernizer" / "kb" / f"{p['name']}.md").write_text(text)
        console.print(f"  [green]✔[/] KB: {p['name']}")


def main():
    ap = argparse.ArgumentParser(prog="agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("modernize")
    m.add_argument("--source"); m.add_argument("--target"); m.add_argument("--workspace", default="workspace")
    m.add_argument("--stage", choices=["all", "kb", "migrate"], default="all")
    m.add_argument("--url"); m.add_argument("--legacy-cmd"); m.add_argument("--modern-cmd")
    m.add_argument("--no-llm-kb", action="store_true")
    a = ap.parse_args()

    banner()
    ws = Path(a.workspace).resolve()
    state_file = ws / "state.json"

    if a.stage in ("all", "kb"):
        steps = Steps(["Get solution", "Build knowledge base"])
        steps.start()
        src = a.source or Prompt.ask("GitHub URL or local solution path")
        repo = source.prepare(src, ws)
        steps.ok(f"Solution ready at {repo}")
        steps.start()
        kb = scanner.build(repo)
        if not a.no_llm_kb:
            enrich_kb(repo, kb)
        steps.ok(f"KB written to {repo/'.modernizer'/'kb'}")
        table("Projects", ["Name", "Framework", "Type", "LOC", "Risks"],
              [(p["name"], p["tfm"], "web" if p["is_web"] else p["output_type"], p["loc"],
                len(p["risks"])) for p in kb["projects"]])
        state_file.write_text(json.dumps({"repo": str(repo)}))
        source.commit(repo, "Add modernization knowledge base")
    if a.stage == "kb":
        return

    repo = Path(json.loads(state_file.read_text())["repo"])
    kb = json.loads((repo / ".modernizer/kb/kb.json").read_text())
    opts = available_targets(kb["current_tfm"])
    console.print(f"\nCurrent framework: [bold]{kb['current_tfm']}[/]. Migrate to:")
    for i, t in enumerate(opts, 1):
        console.print(f"  {i}. {t.label}  [dim]{t.note}[/]")
    target = next((t for t in opts if t.tfm == a.target), None)
    if not target:
        target = opts[IntPrompt.ask("Choose number", choices=[str(i) for i in range(1, len(opts) + 1)]) - 1]
    if not Confirm.ask(f"Start migration to {target.label}?", default=True):
        return
    opts_ = {"url": a.url or Prompt.ask("App base URL for parity tests (blank to skip)", default=""),
             "legacy_cmd": a.legacy_cmd, "modern_cmd": a.modern_cmd}
    if opts_["url"]:
        opts_["legacy_cmd"] = opts_["legacy_cmd"] or Prompt.ask("Command that starts the LEGACY app")
        opts_["modern_cmd"] = opts_["modern_cmd"] or Prompt.ask("Command that starts the MIGRATED app")
    run_migration(repo, kb, target, opts_)
    if shutil.which("code"):
        subprocess.run(["code", str(repo)])
