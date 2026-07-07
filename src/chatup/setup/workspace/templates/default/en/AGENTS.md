# Workspace Agents

`AGENTS.md` is the entry guide when a model enters this workspace.

## Core Principles

- Keep only a small set of control files at workspace root; actual execution should happen inside the target project directory.
- Keep all active work under `projects/`; archive inactive projects into `archive/YYYY-MM-DD/`, where `YYYY-MM-DD` is the date when archiving happens.
- Project structure should stay minimal by default, while naming still allows more flexible grouping.
- `PRD.md` records stable requirements, scope, constraints, and completion criteria; progress details belong in `progress.md`.
- `progress.md` is the continuity log for each task. Update it after each substantive action.
- Archiving should not be decided by scripts alone. Scripts can collect candidates and validate rules, but the final archive index should be reviewed and written into `archive/index.md` by the model.
- If requirements are unclear, ask follow-up questions before execution.

See `projects/README.md` for concrete project structures and naming rules.

## Architecture

```text
Workspace/
  AGENTS.md
  TODO.md
  ARCHIVE.md
  .trash/
  projects/
  discussion/
    MM-DD-<topic>/
      card.md
      Items/
  archive/
    index.md
    YYYY-MM-DD/
  discard/
  core/
  scripts/
  skills/
  public/
```

This workspace is an outer collaboration scaffold around source repositories.

## Current Options

- Enabled options: `projects/`, `discussion/`, `archive/`, `discard/`, `ARCHIVE.md`, `archive/index.md`
- Source repositories go under `core/`
- Workspace maintenance scripts go under `scripts/`
- The workspace root keeps a `.trash/` directory as a low-level safety buffer, not as a main task column; normal task deletion should move to `discard/`
- Imported shared skills go under `skills/`; ChatMemory links the `chatarch`, `common`, and `agents` shared groups by default, and `package-development` / `package-review` are available under `skills/chatarch/`
- Public publish output goes under `public/`
- The directory protocol has two basic item types: Project items and Discussion items. Both are project-like task units in different lifecycle phases. Active Project items go under `projects/`; Discussion items go under `discussion/MM-DD-<topic>/`, include a `card.md` that describes the topic and item-classification logic, and can temporarily absorb other items under `Items/`
- Archived projects go under `archive/YYYY-MM-DD/`, using the date when archiving happens; soft-deleted or no-longer-valuable tasks go under `discard/` instead of being physically deleted

## Workflow

1. Read root `AGENTS.md`, then enter the target project.
2. Identify the repo to change under `core/` and the target project under `projects/`.
3. Create or refine `PRD.md` before execution.
4. Update the current project's `progress.md` after each substantive action.
5. Keep drafts, experiments, and local references inside the current project and place them into the matching subdirectories.
6. Do not write debug temp files into `/tmp`; use the current project's `playground/`.
7. Keep the project root minimal: control files at the root, reports under `reports/`, scripts under `scripts/`.
8. If you use `projects/<topic>/<name>/`, keep `projects/<topic>/` as an index layer with only `README.md`, `.trash/`, and child project directories.
9. Use `MM-DD-...` for new execution tasks by default; Discussion topics use the same prefix.
10. When multiple projects need joint digestion, human correction, routing, or conversion into skill/blog/infra output, create `discussion/MM-DD-<topic>/`, write `card.md` for the topic, absorption goal, and item-classification logic, then move absorbed projects under its `Items/` directory.
11. Move user-deleted or no-longer-valuable tasks to `discard/`; `.trash/` is only a low-level file-operation safety buffer.
12. If a project needs isolated source edits, prefer an on-demand Git worktree from `core/<repo-name>` and remove that worktree when the task is finished. Do not copy the repository.
13. Finish with a report; if archiving happens, update `archive/index.md`.
14. Follow an archive flow of “script candidate collection + model review + `archive/index.md` update”; the procedure lives in root `ARCHIVE.md`.

## Write Rules

| Situation | Write To |
|-----------|----------|
| Any active work unit | `projects/MM-DD-<project-name>/` or `projects/<topic>/MM-DD-<project-name>/` |
| Project item | Must use the `MM-DD-<project-name>` date prefix |
| Inactive old project | `archive/YYYY-MM-DD/<project-name>/`, where `YYYY-MM-DD` is the archive date |
| Tasks that need joint digestion/correction/routing | `discussion/MM-DD-<topic>/`, with its own `card.md` and absorbed tasks under `Items/` |
| Soft-deleted or no-longer-valuable task | `discard/<project-name>/` |
| Archive procedure guide | `ARCHIVE.md` |
| Archived content index | `archive/index.md` |
| Repositories to change | `core/<repo-name>/` |
| Workspace maintenance scripts | `scripts/<name>.py` |

## Conventions

- Stay within the current task boundary unless the task is explicitly expanded.
- State uncertainty explicitly instead of silently assuming.
- Do not scatter standalone scripts or temp files at the workspace root; place durable scripts under `scripts/`.
