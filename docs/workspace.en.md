# Workspace Scaffold

`chatup workspace` initializes the ChatArch human-AI collaboration workspace. The workspace is not the source repository itself; it is the outer structure that holds source repos, task records, shared skills, scripts, and publishable artifacts.

## Basic Command

```bash
chatup workspace default ~/Playground
```

Common options:

```bash
chatup workspace default ~/Playground --language zh
chatup workspace default ~/Playground --with-memory --memory-source https://github.com/ChatArch/ChatMemory.git
chatup workspace default ~/Playground --dry-run
```

## Generated Structure

A typical workspace looks like this:

```text
Playground/
  AGENTS.md
  TODO.md
  ARCHIVE.md
  .trash/
  projects/
  archive/
  core/
  scripts/
  skills/
  public/
```

## Directory Responsibilities

| Path | Responsibility |
|---|---|
| `projects/` | Active work units. Each task should have `PRD.md` and `progress.md`. |
| `archive/` | Archived tasks, usually grouped by date. |
| `core/` | Source repositories that the workspace modifies or references. |
| `scripts/` | Workspace-level maintenance scripts. |
| `skills/` | Shared skill entry points, usually sourced from ChatMemory. |
| `public/` | Published artifacts or local service outputs. |
| `.trash/` | Soft-delete buffer. |

## Working Convention

- Create or confirm a project before stateful implementation, research, or publishing work.
- Keep task progress in `progress.md`; keep stable scope and boundaries in `PRD.md`.
- Put experiments and raw outputs under the task's `playground/`, not `/tmp`.
- Move files into the nearest `.trash/` before deleting or replacing them.

## Relationship to Source Repositories

ChatUp recommends keeping source repositories under `core/`, for example:

```text
Playground/core/ChatUp
Playground/core/ChatMemory
Playground/core/ChatGH
```

Task records remain under `projects/`. This keeps PRs, tests, and source changes in repositories while process notes, reports, and temporary outputs stay in the outer workspace.
