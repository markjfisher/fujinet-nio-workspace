# Workspace backlog

This is the cross-repository work queue for the FujiNet-NIO workspace.

## Rules

- One Markdown file represents one coherent goal or deliverable.
- Keep detailed implementation notes in the repository that owns the code;
  keep this file focused on scope, order, dependencies, and acceptance.
- Use only these statuses: `TODO`, `IN PROGRESS`, `BLOCKED`, and `DONE`.
- A task is `DONE` only when its acceptance criteria are met, tests have been
  run where applicable, and the user has reviewed or accepted the result.
- Do not add speculative ideas to an active task. Create a new backlog item
  instead.
- When the whole goal is complete, move its file to `completed/` rather than
  leaving a long historical checklist in the active backlog.

The backlog is intentionally small: it is a Kanban-style coordination layer,
not a second source tree or a replacement for design documentation.
