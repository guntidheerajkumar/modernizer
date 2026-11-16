"""Thin wrapper around the Claude Agent SDK (file edits + bash happen inside the repo)."""
import asyncio
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def load_skills(*names: str) -> str:
    return "\n\n".join((SKILLS_DIR / f"{n}.md").read_text() for n in names)


async def _run(prompt, system, cwd, tools, max_turns):
    opts = ClaudeAgentOptions(system_prompt=system, cwd=str(cwd), allowed_tools=tools,
                              permission_mode="acceptEdits", max_turns=max_turns)
    chunks = []
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            chunks += [b.text for b in msg.content if isinstance(b, TextBlock)]
    return "\n".join(chunks)


def run_agent(prompt: str, system: str, cwd: Path, max_turns: int = 40,
              tools=("Read", "Write", "Edit", "Glob", "Grep", "Bash")) -> str:
    return asyncio.run(_run(prompt, system, cwd, list(tools), max_turns))
