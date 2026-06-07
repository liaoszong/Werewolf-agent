# AGENTS.md

Telegraph style. Root hard policy only. Read scoped `AGENTS.md` before subtree work. Skills own workflows; this file owns routing, default context, and forbidden-scope rules.

回答优先使用中文。

## Project Route

- Product direction: client-agnostic live AI Werewolf experiment platform.
- Current route: G1h = Live Runtime Event Spine.
- G1h goal: expose real/fake provider single-game runtime as stable `events.jsonl`, runtime snapshots, prompt manifest, provider lifecycle events, and standard log bundle compatibility.
- G2 starts observer server / Qt client. G1h does not build Qt/QML, Web observer, prompt editor UI, multi-provider arena, leaderboard, or scoring formula changes.
- Canonical route facts: `docs/ROADMAP.md`.
- Task status and candidate dependencies: `docs/TASKS.md`.
- Product entry: `README.md`.

## Default Context

Default reads should be small and current:

1. User request and this file.
2. `README.md`.
3. Relevant `docs/ROADMAP.md` and `docs/TASKS.md` ranges only.
4. Active implementation plan, preferably through `docs/generated-context/current-task.ctx.md`.
5. Exact source/test ranges only when needed.

Do not default-read historical material:

- `docs/GOLD_DEMO.md` and `docs/SPIKES.md`: Phase 1 legacy/archived. Skip unless tracing Phase 1 spike or gold-demo history.
- `docs/EVALUATION_RUBRIC.md`: G4 later-stage reference. Read-on-demand for G1h-G3; default-read for G4 evaluation platform work.
- `docs/CHECKPOINT_TEMPLATE.md`: process template, not default context.
- `docs/harness/plans/**` except the active bound plan.
- `docs/harness/reviews/**`.
- `docs/demo/**`.
- `docs/generated-games/**`.
- `docs/gold-game/**` unless validating a log/fixture contract.
- `docs/semantic-labeling/**` unless working on saved semantic labels.
- `.tmp/**`.
- `.logs/review/latest/review-packet.md` unless explicitly doing packet review.
- Full validation logs; read `.logs/validate/latest/summary.json` first when validation fails.

## Context Budget Gate

Keep the working context small and generated, not bulk-loaded:

- Do not read long plan files in full. Bind the active plan through the generated
  `docs/generated-context/current-task.ctx.md`, produced by `scripts/context/build_plan_index.py`
  and `scripts/context/build_task_context.py`.
- Validate a task brief with `scripts/dev/validate_brief.py` before implementation.
- On validation failure read `.logs/validate/latest/summary.json` first, not the full logs.
- Do not use Repomix as the default context entry.
- Do not introduce Semble, CodeGraph, or codebase-memory MCP unless a later plan explicitly allows it.

## Work Boundaries

- PR-first workflow. Implementation work must bind to an Implementation Plan.
- Plan path convention: `docs/harness/plans/YYYY-MM-DD--<slug>-plan.md`.
- Current GitHub repo: `liaoszong/Werewolf-agent`.
- Do not modify runtime, scoring, provider, validators, generated fixtures, or tests without an active plan explicitly allowing it.
- Do not treat historical HTML replay, generated JSON, or gold-game artifacts as current product direction.
- G1g HTML replay is offline audit output only, not primary UX.
- Research docs and old plans are evidence/history, not default route authority.
- Stable architecture decisions live in `docs/adr/**`.

## Progress Routing

Before deciding the next implementation step:

- Local agent: run `gh pr list --limit 10 --state all` and `git log --oneline -10`.
- Connector/cloud agent: use equivalent GitHub API/connector reads.
- Merged PRs and main files are facts; open PRs are unresolved context.
- If the previous Implementation PR is open, default next step is review/closeout, not new work.
- Then read only the relevant `ROADMAP` / `TASKS` / active-plan ranges.

## Validation

For every change, report:

- `git diff --stat`
- `git diff --name-only`
- Allowlist check against the user request / plan.
- Forbidden-scope check confirming no unintended `src/**`, `tests/**`, `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/adr/**`, historical plans, demo, generated-games, gold-game, `.agents/skills/**`, or `.github/**` changes.
- Relevant tests or a clear reason tests are unnecessary.

Common local test command on PowerShell:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Only run log validators when the change touches log contracts or fixtures.

## Tree

- `.oh-my-harness/tree.md` is navigation only.
- New/delete/rename files: run `node .codex/hooks/tree.mjs --force`.
- Do not hand-edit tree unless hook is unavailable; if unavailable, explain and use equivalent `git ls-files --cached --others --exclude-standard` output.

## Review

- Reviewers read `docs/specs/review-guidelines.md`.
- Packet-first review uses `docs/specs/review-packet-gate.md`.
- No review packet, no broad Codex implementation review unless the user explicitly asks for a full review.

## Maintenance

- Only stable facts belong here.
- Keep this file short. Link volatile details to canonical docs instead of copying them.
