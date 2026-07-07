# Discussion

`discussion/` is for Discussion items that digest, correct, route, or synthesize related work.

## When To Create A Discussion

Create a Discussion when multiple items or materials need joint review, classification, correction, routing, or conversion into skill/blog/infra/archive/discard outcomes:

```text
discussion/MM-DD-<topic>/
  card.md
  PRD.md
  progress.md
  reports/
  Items/
```

## card.md

A Discussion includes its own `card.md`. It explains:

- what topic the Discussion is handling
- why these items are grouped together
- the current judgment
- how materials under `Items/` are classified
- the next action

## Review Flow

1. List the candidate related items.
2. For an item that already has `card.md`, read the card first, then inspect item files as needed.
3. For an item without `card.md`, review `PRD.md`, `progress.md`, reports, and important files, then write a concise card.
4. Write or update the Discussion's own `card.md` with the topic, absorption goal, item groups, current judgment, and next action.
5. Move absorbed items under `Items/` after review confirms they belong together.

## Completion

When the Discussion is complete, handle and clear `Items/`. Items may be archived, discarded, split back into new Projects, or summarized in `progress.md` / reports.
