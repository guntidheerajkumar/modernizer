# Legacy .NET Modernization Agent

## Setup
```
python -m venv .venv && .venv\Scripts\activate     # source .venv/bin/activate on mac/linux
pip install -e .
playwright install chromium
set ANTHROPIC_API_KEY=...                           # export on mac/linux
```
Prereqs: git, .NET SDK, and (for legacy projects) MSBuild / VS Build Tools on Windows.

## Run in VS Code
- Terminal: `python -m modernizer modernize` (or `agent modernize`)
- Task: Ctrl+Shift+P -> "Tasks: Run Task" -> "agent: modernize"
- Chat: `/agent modernize` via the Claude Code extension (`.claude/commands/agent.md`)

## Pipeline
1. Ask for GitHub URL or local path; clone/copy into `./workspace` (original is never modified)
2. Build knowledge base `.modernizer/kb/` (static scan + LLM summary per project)
3. Show framework options newer than the detected one; user picks
4. Capture legacy behaviour baseline with Playwright (optional but recommended)
5. Migrate projects leaf-first, one commit each, build + auto-fix loop, skills from `skills/`
6. Generate xUnit characterization tests per project
7. Run Playwright parity tests against the migrated app
8. `MIGRATION_REPORT.md` + open the solution in VS Code

Edit `skills/*.md` to teach the agent your conventions; edit `modernizer/config.py` for targets.
