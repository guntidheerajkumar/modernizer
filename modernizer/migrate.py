"""Steps 4-8: migrate project by project, verify, generate tests, report."""
import subprocess
from graphlib import TopologicalSorter
from pathlib import Path

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from . import builder, source, testgen
from .config import Target
from .llm import load_skills, run_agent
from .ui import Steps, console, table

MAX_FIX_ATTEMPTS = 4


def skills_for(target: Target, project: dict) -> str:
    names = ["00-guardrails"]
    if target.kind == "netfx":
        names.append("netfx-retarget")
    else:
        names.append("netfx-to-modern-dotnet")
        if project["is_web"]:
            names.append("aspnet-to-aspnetcore")
    return load_skills(*names)


def order(kb: dict) -> list[dict]:
    by_name = {p["name"]: p for p in kb["projects"]}
    graph = {n: {r for r in p["project_refs"] if r in by_name} for n, p in by_name.items()}
    return [by_name[n] for n in TopologicalSorter(graph).static_order()]   # leaves first


def migrate_project(repo, p, target, kb_hint, ui) -> bool:
    system = skills_for(target, p)
    prompt = (f"Migrate project `{p['name']}` at `{p['path']}` from `{p['tfm']}` to `{target.tfm}`.\n"
              f"Read .modernizer/kb/overview.md first for solution context.\n{kb_hint}\n"
              f"Dependencies already migrated: {p['project_refs'] or 'none'}.\n"
              "Do not change behaviour. Append decisions to MIGRATION_NOTES.md.")
    run_agent(prompt, system, repo)
    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        ok, out = builder.build(repo, p["path"])
        if ok:
            return True
        ui.warn(f"{p['name']}: build failed (fix attempt {attempt}/{MAX_FIX_ATTEMPTS})")
        run_agent(f"Build of `{p['path']}` failed. Fix the errors WITHOUT changing behaviour "
                  f"or deleting functionality.\n\nBuild output (tail):\n{out[-6000:]}", system, repo)
    return False


def run(repo: Path, kb: dict, target: Target, console_opts: dict):
    steps = Steps(["Baseline", "Create migration branch", "Migrate projects",
                   "Build full solution", "Generate unit tests (xUnit)",
                   "Playwright parity verification", "Report"])
    results = {}

    # 1 baseline ---------------------------------------------------------------
    steps.start()
    legacy_cmd, modern_cmd, url = (console_opts.get(k) for k in ("legacy_cmd", "modern_cmd", "url"))
    testgen.write(repo, kb)
    if legacy_cmd and url:
        ok, out = testgen.run(repo, "capture", legacy_cmd, url)
        (steps.ok if ok else steps.warn)("Captured legacy behaviour baseline" if ok else out[-500:])
        source.commit(repo, "Add Playwright parity tests and legacy baseline")
    else:
        steps.warn("No legacy run command/URL provided: skipping behaviour baseline")

    # 2 branch -----------------------------------------------------------------
    steps.start()
    steps.ok(f"Working on branch {source.create_branch(repo, target.tfm)}")

    # 3 migrate ----------------------------------------------------------------
    steps.start(f"→ {target.label}")
    projects = [p for p in order(kb) if not p["is_test"]]
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(),
                  TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn(),
                  console=console) as prog:
        task = prog.add_task("Migrating", total=len(projects))
        for p in projects:
            prog.update(task, description=f"Migrating [cyan]{p['name']}[/]")
            hint = f"Known risks in this project: {p['risks']}" if p["risks"] else ""
            ok = migrate_project(repo, p, target, hint, steps)
            results[p["name"]] = ok
            source.commit(repo, f"Migrate {p['name']} to {target.tfm}" + ("" if ok else " (NEEDS ATTENTION)"))
            (steps.ok if ok else steps.fail)(f"{p['name']}")
            prog.advance(task)

    # 4 build ------------------------------------------------------------------
    steps.start()
    failed = [n for n, ok in results.items() if not ok]
    steps.ok("All projects build") if not failed else steps.fail(f"Needs attention: {', '.join(failed)}")

    # 5 unit tests -------------------------------------------------------------
    steps.start()
    for p in projects:
        run_agent(f"Create an xUnit test project `{p['name']}.Tests` targeting `{target.tfm}` for "
                  f"`{p['path']}`. Characterize EXISTING behaviour (public API, edge cases, "
                  "error paths). Add it to the solution. Then run `dotnet test` and fix test code "
                  "(never production code) until green.",
                  load_skills("00-guardrails", "testing"), repo, max_turns=30)
        steps.ok(f"Tests for {p['name']}")
    source.commit(repo, "Add xUnit unit tests")

    # 6 parity -----------------------------------------------------------------
    steps.start()
    parity = None
    if legacy_cmd and modern_cmd and url:
        parity, out = testgen.run(repo, "compare", modern_cmd, url)
        (steps.ok if parity else steps.fail)("Behaviour matches legacy baseline" if parity else out[-1500:])
    else:
        steps.warn("Skipped (need legacy + modern run commands and URL)")

    # 7 report -----------------------------------------------------------------
    steps.start()
    stat = subprocess.run(["git", "diff", "--stat", "main...HEAD"], cwd=repo,
                          capture_output=True, text=True).stdout
    table("Migration result", ["Project", "Status"],
          [(n, "[green]OK[/]" if ok else "[red]NEEDS ATTENTION[/]") for n, ok in results.items()])
    (repo / "MIGRATION_REPORT.md").write_text(
        f"# Migration report → {target.label}\n\n" +
        "\n".join(f"- {n}: {'OK' if ok else 'NEEDS ATTENTION'}" for n, ok in results.items()) +
        f"\n\nParity check: {parity}\n\n```\n{stat}\n```\n")
    console.print(f"\n[bold green]Done.[/] Solution: {repo}\nReport: {repo/'MIGRATION_REPORT.md'}")
    return results
