# Skill: functionality guardrails (always applied)
You are migrating a legacy .NET application. The migrated app MUST behave identically.

Rules:
1. Never remove, stub, or comment out functionality to make the build pass.
2. Preserve public APIs, namespaces, routes/URLs, HTTP verbs, response shapes, status codes,
   config keys, connection-string names, DB schema, and error messages.
3. Prefer the smallest change that compiles. No refactors, renames, or style changes.
4. If a library has no equivalent, choose the closest drop-in replacement, keep the same
   behaviour, and record it in MIGRATION_NOTES.md (what, why, risk).
5. If behaviour might differ and you cannot prove otherwise, keep the old behaviour and add a
   `// MIGRATION-REVIEW:` comment plus a MIGRATION_NOTES.md entry.
6. Never touch files outside the repo. Never print or store secret values from config.
7. Use the KB in .modernizer/kb/ for context before editing.
