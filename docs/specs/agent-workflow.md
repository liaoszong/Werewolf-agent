# Agent Workflow Reference

This file is a non-default workflow reference for cloud agents, GitHub connector agents, and agents that cannot use the local harness directly.

Local Codex / Claude Code / OpenCode work should start from:

1. `AGENTS.md`
2. `README.md`
3. Relevant `docs/ROADMAP.md` and `docs/TASKS.md` ranges
4. The active implementation plan or `docs/generated-context/current-task.ctx.md`
5. Exact source/test ranges only when needed

Do not read this file as default context unless the task involves cloud/connector workflow, PR metadata handling, or handoff rules.

## Scope

- Repository: `liaoszong/Werewolf-agent`.
- Product route authority: `docs/ROADMAP.md`.
- Task/dependency authority: `docs/TASKS.md`.
- Root hard policy: `AGENTS.md`.
- Review packet rules: `docs/specs/review-packet-gate.md`.
- Reviewer rules: `docs/specs/review-guidelines.md`.

This file does not override `AGENTS.md`.

## Cloud / Connector Boundary

If the agent cannot patch and validate locally, it may create or update:

- Implementation plans.
- Research notes under `docs/prs/`.
- PR title/body/comments/review comments.
- Documentation that directly supports the plan or handoff.

It must not modify runtime code, tests, scoring, provider adapters, validators, generated fixtures, or historical artifacts unless the user explicitly grants that ability and the active plan allows it.

If the user says "do not modify files", do not create plan files. If the user says "no code changes", plan/doc files are allowed only when the request asks for them.

## Minimal Read Protocol

Use bounded reads. Avoid repeated fetches of the same file or path.

Recommended order:

1. Recent PRs and main commits.
2. `AGENTS.md`.
3. `README.md`.
4. Relevant `docs/ROADMAP.md` lines around the current route.
5. Relevant `docs/TASKS.md` lines around the current candidate task.
6. Active plan context, preferably generated context/index files.
7. `.oh-my-harness/tree.md` only for navigation when directory access is unavailable.
8. Exact source/test ranges only if the plan requires implementation-entry binding.

Do not default-read:

- Historical plans or reviews.
- Demo HTML.
- Generated game JSON.
- Gold-game fixtures.
- `.tmp/**`.
- Review packets unless doing packet review.
- Full validation logs before reading summaries.

## Routing Rules

- Research PR is optional, not mandatory.
- Clear, bounded tasks can go directly to Implementation Plan / Implementation PR.
- Merged PRs and main files are completed delivery facts.
- Open PRs are unresolved context.
- If PR history and `docs/TASKS.md` conflict, state the conflict and check actual files before deciding.
- If a previous Implementation PR is still open, default to review/closeout before starting a later task.

## Review Handoff

Implementation PRs should provide `.logs/review/latest/review-packet.md` before Codex review.

Codex A档 review starts from the packet only and returns exactly one of:

- `PASS`
- `BLOCK`
- `NEED_DEEP_REVIEW`

Without a packet, request packet generation instead of broad repository review. `NEED_DEEP_REVIEW` must name explicit file paths and line ranges for B档.

## Tree Handoff

If a PR adds, deletes, or renames files, refresh `.oh-my-harness/tree.md` with:

```powershell
node .codex/hooks/tree.mjs --force
```

Do not hand-maintain tree output unless the hook is unavailable.

## Handoff Output

Connector/cloud handoff should include:

- Files changed or proposed.
- Bound plan path.
- Scope allowlist.
- Explicit non-goals.
- Validation evidence or validation still needed locally.
- Review packet status when relevant.
