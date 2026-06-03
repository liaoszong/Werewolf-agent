# G1h Contract Closeout + Route Docs Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align route truth sources after merged G1h work so docs clearly state that G1h is completed, G2a is the next implementation track, and observer server / Qt client / profile editor / leaderboard remain not completed.

**Architecture:** This is a docs-only route closeout. It updates canonical route/status documents and a compact review packet without changing runtime, validators, tests, generated fixtures, demo artifacts, or product behavior.

**Tech Stack:** Markdown docs, GitHub CLI, Git, PowerShell, existing tree hook. No Python runtime changes, no server, no Qt/Web client, no profile editor, no scoring, no generated artifacts.

---

## Execution Mode

User-approved simplification for this execution:

- Work directly on current `main` worktree.
- No PR is required.
- No review packet is required.
- Validation is limited to `git status --short`, `git diff --name-only`, `git diff --check`, and targeted `Select-String` route checks.

## Context Basis

Current facts to preserve:

- GitHub PR #38 merged `feat: add G1h live runtime event spine`.
- Recent main history includes merge commit for G1h and implementation commit `feat: add G1h live runtime event spine`.
- `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md` defines Phase B as route closeout, not new product functionality.
- `README.md`, `docs/PRODUCT_ONE_PAGER.md`, `docs/ROADMAP.md`, and `docs/TASKS.md` may still contain stale wording that treats G1h as current or `next_candidate`.

Phase B must make these three statements true across route docs:

```text
G1h is completed.
G2a is the next implementation track.
Observer server / Qt client / profile editor / leaderboard are not completed.
```

## Scope Summary

Phase B includes:

- Fact collection from GitHub and Git.
- ROADMAP status alignment.
- TASKS status alignment.
- README and PRODUCT_ONE_PAGER status alignment.
- Phase A charter entry link in the route/status docs.
- Verification that no runtime or generated-artifact scope was touched.

Phase B does not include:

- local observer server implementation,
- REST / WebSocket / SSE endpoint design beyond naming G2a as next,
- Qt/QML or Web UI,
- prompt/profile editor,
- match/profile contract implementation,
- visibility contract implementation,
- experiment orchestration,
- leaderboard or scoring work,
- source/test/runtime/validator/generated fixture changes.

## Allowlist

Execution may modify only:

```text
README.md
docs/PRODUCT_ONE_PAGER.md
docs/ROADMAP.md
docs/TASKS.md
docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md
docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.zh.md
.oh-my-harness/tree.md
```

Notes:

- The charter files are allowlisted only for adding a link-target / status note if needed. Do not rewrite Phase A.
- `.oh-my-harness/tree.md` may change only through `node .codex/hooks/tree.mjs --force` if files are created or deleted.
- The active implementation plan file itself is already this file and is not part of Phase B execution changes after plan approval.

Forbidden:

```text
src/**
tests/**
docs/adr/**
docs/harness/plans/** except this plan before execution starts
docs/harness/reviews/**
docs/demo/**
docs/generated-games/**
docs/gold-game/**
docs/semantic-labeling/**
.agents/skills/**
.github/**
```

## Implementation PR Draft

Title:

```text
docs: close out G1h route status
```

Body:

```markdown
## Summary

- Aligns README, PRODUCT_ONE_PAGER, ROADMAP, and TASKS with merged G1h Live Runtime Event Spine facts.
- Marks G1h as completed and G2a Local Observer Server / Protocol Control Plane as the next implementation track.
- Adds the Phase A platform charter as the route/design source for G2a/G2b anti-shrinkage gates.

## Scope

- Docs-only route/status alignment.
- No runtime, server, UI, profile editor, scoring, validator, generated fixture, or demo changes.

## Validation

- `gh pr list --limit 10 --state all`
- `git log --oneline -10`
- `git status --short`
- targeted grep checks for stale G1h next-candidate wording
- targeted grep checks that observer server / Qt client / profile editor / leaderboard are not claimed completed
- `git diff --check`
- changed-file allowlist and forbidden-scope check
```

---

## Task 1: Collect Current Route Facts

**Files:**

- Read: `README.md`
- Read: `docs/PRODUCT_ONE_PAGER.md`
- Read: `docs/ROADMAP.md`
- Read: `docs/TASKS.md`
- Read: `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md`
- Modify: none

- [ ] **Step 1: Confirm working tree state**

Run:

```powershell
git -c safe.directory=G:/Werewolf-agent status --short
```

Expected:

- Shows only known planning/design files from the current docs workflow, or a clean tree.
- If unrelated user changes exist, do not modify those files and record them in the review packet.

- [ ] **Step 2: Confirm recent PR facts**

Run:

```powershell
gh pr list --limit 10 --state all
```

Expected:

- Output includes PR `38` with title `feat: add G1h live runtime event spine` and state `MERGED`.
- Output includes PR `37` with title containing `G1h Live Runtime Event Spine` and state `MERGED`.

- [ ] **Step 3: Confirm recent Git facts**

Run:

```powershell
git -c safe.directory=G:/Werewolf-agent log --oneline -10
```

Expected:

- Output includes merge commit for PR #38.
- Output includes implementation commit `feat: add G1h live runtime event spine`.

- [ ] **Step 4: Confirm G1h implementation files exist**

Run:

```powershell
Test-Path 'src\werewolf_eval\runtime_events.py'
Test-Path 'src\werewolf_eval\run_g1h_fake_runtime.py'
Test-Path 'tests\test_runtime_events.py'
Test-Path 'tests\test_g1h_runtime_spine.py'
```

Expected:

- Each command prints `True`.

- [ ] **Step 5: Locate stale route wording**

Run:

```powershell
Select-String -Path 'README.md','docs\PRODUCT_ONE_PAGER.md','docs\ROADMAP.md','docs\TASKS.md' -Pattern 'G1h|next_candidate|not completed|next implementation candidate|下一候选开发点|observer server|Qt|profile editor|leaderboard' -Context 1,2
```

Expected:

- Shows stale G1h route status in `docs/ROADMAP.md` and `docs/TASKS.md`.
- Shows non-goal wording for observer server / Qt client / profile editor / leaderboard that must remain explicit.

---

## Task 2: Update ROADMAP.md

**Files:**

- Modify: `docs/ROADMAP.md`
- Test: grep checks in Task 6

- [ ] **Step 1: Update Current Main Facts**

Edit `docs/ROADMAP.md` so `## Current Main Facts` lists `G1h Live Runtime Event Spine` under completed items.

Required result:

```markdown
- G1g provider replay HTML report.
- G1h Live Runtime Event Spine.
```

- [ ] **Step 2: Remove G1h from not-completed list**

Edit the `The current main branch has not completed:` list so it no longer includes:

```markdown
- G1h Live Runtime Event Spine.
```

Required remaining not-completed list includes:

```markdown
- Local observer server.
- Qt/QML observer client.
- Web observer client.
- Prompt editor UI.
- Multi-provider arena.
- human-vs-AI UI.
- G4 evaluation platform / real multi-game Leaderboard.
```

- [ ] **Step 3: Mark G1h section completed**

Edit `#### G1h: Live Runtime Event Spine`.

Required status:

```markdown
- Status: `completed`.
```

Keep the role and boundary text focused on event spine. Do not add observer server or client claims.

- [ ] **Step 4: Update G1 foundation sentence**

Replace the stale sentence that says full platform work starts at G1h with wording that G1h is now the completed foundation for G2.

Required meaning:

```text
G1a-G1h are retained as audit foundation, replay foundation, runtime event spine foundation, and log bundle / provider trace / failure audit foundation. Full observer platform work proceeds through G2a because clients must consume a stable event stream through a protocol boundary.
```

- [ ] **Step 5: Update Current Priority**

In the current priority section, replace:

```text
G1g provider replay HTML is now `completed`. The next implementation candidate is G1h Live Runtime Event Spine.
```

with wording that states:

```text
G1h Live Runtime Event Spine is now `completed`. The next implementation candidate is G2a Local Observer Server / Protocol Control Plane.
```

- [ ] **Step 6: Preserve dependency graph**

Keep this dependency route intact:

```text
G1h event spine
  -> G2a Local Observer Server
  -> G2b Qt Observer MVP
  -> G2c God View / Role View
  -> G2d Prompt Configuration MVP
  -> G3 Experiment Profiles / Replay + Live Dual Mode / Multi-provider Arena
  -> G4 Evaluation Platform / real multi-game Leaderboard
```

Do not expand G2a endpoint tasks inside `ROADMAP.md`.

- [ ] **Step 7: Add charter link in document responsibility or route note**

Add one concise reference to:

```markdown
`docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md`
```

Required meaning:

```text
Phase A charter is the route/design source for game-like experience architecture, minimum match/profile contract seed, visibility trust gates, exit demos, and anti-shrinkage gates.
```

Do not make the charter an implementation spec.

---

## Task 3: Update TASKS.md

**Files:**

- Modify: `docs/TASKS.md`
- Test: grep checks in Task 6

- [ ] **Step 1: Update summary paragraph**

Edit the G-track summary paragraph near the start of the task list so it includes G1h as completed and names G2a as the next candidate.

Required meaning:

```text
E1-E4, D1/D2, S4/S5, and G1a-G1h are completed. The next candidate development point is G2a Local Observer Server / Protocol Control Plane.
```

Keep the L1 real multi-game Leaderboard as `G4 evaluation-platform dependent`.

- [ ] **Step 2: Mark G1h completed**

Edit `#### G1h：Live Runtime Event Spine`.

Required status:

```markdown
- 状态：`completed`（plan 文件 `docs/harness/plans/2026-06-03--g1h-live-runtime-event-spine-plan.md`；implementation merged in PR #38）
```

- [ ] **Step 3: Add concrete G1h outputs**

In the G1h section, ensure the output/core-product lines mention:

```text
src/werewolf_eval/runtime_events.py
src/werewolf_eval/run_g1h_fake_runtime.py
tests/test_runtime_events.py
tests/test_g1h_runtime_spine.py
events.jsonl contract
runtime snapshots
prompt manifest
provider lifecycle events
standard log bundle compatibility
```

Do not list generated `.tmp` live smoke artifacts as committed outputs.

- [ ] **Step 4: Add G2a next-candidate entry**

Add a new `#### G2a：Local Observer Server / Protocol Control Plane` entry after G1h or in the next appropriate G2 section.

Required fields:

```markdown
#### G2a：Local Observer Server / Protocol Control Plane

- 状态：`next_candidate`
- 作用：通过本地 client-agnostic protocol 暴露 G1h event spine、run status、snapshots、historical run artifacts，并为后续 Qt/Web observer client 提供协议边界。
- Scope：REST/stream protocol、run/status/artifact/snapshot/event 查询与订阅、minimum match/profile contract seed for default-template launch、visibility trust slices from day one。
- Non-goals：不做 Qt/QML client，不做 Web observer UI，不做完整 prompt/profile editor，不做 multi-provider arena，不做 leaderboard，不改 scoring formula，不改 runtime game behavior。
- 路线依据：`docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md`。
```

- [ ] **Step 5: Keep existing backlog item unchanged**

Do not rename or absorb `Backlog / prerequisite fix candidate：Decision Round Scoring Disambiguation`.

Required meaning:

```text
It remains a planned backlog / prerequisite fix candidate and does not own the G1h stage name.
```

---

## Task 4: Update README.md and PRODUCT_ONE_PAGER.md

**Files:**

- Modify: `README.md`
- Modify: `docs/PRODUCT_ONE_PAGER.md`
- Test: grep checks in Task 6

- [ ] **Step 1: Update README current status**

Edit `README.md` current status so it states that G1h is completed along with G1a-G1g.

Required meaning:

```text
Current main includes G1h Live Runtime Event Spine.
G1a-G1h now form audit/replay/log bundle/provider trace/failure audit/event spine foundation.
G2a Local Observer Server / Protocol Control Plane is the next implementation track.
```

- [ ] **Step 2: Preserve README non-completion warning**

Ensure `README.md` still explicitly says these are not completed:

```text
observer server
Qt/Web client
prompt/profile editor
multi-provider arena
human-vs-AI UI
real multi-game Leaderboard
```

Use wording that does not imply a rich client exists.

- [ ] **Step 3: Add charter to README docs index**

Add a row to the docs index:

```markdown
| [Live Platform Charter](docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md) | `CURRENT` | Phase A 产品路线 + 系统架构宪章：game-like experience、minimum match/profile seed、visibility trust gate、exit demo、anti-shrinkage gates |
```

- [ ] **Step 4: Update PRODUCT_ONE_PAGER G1h section**

Edit `docs/PRODUCT_ONE_PAGER.md` so the G1h heading no longer says current if that implies uncompleted work.

Required heading:

```markdown
## G1h：Live Runtime Event Spine（已完成基础设施）
```

Required meaning:

```text
G1h is completed as runtime infrastructure.
G2 Observer Route is the next stage.
G1h did not build Qt/QML client, Web observer, prompt editor UI, multi-provider arena, leaderboard, or scoring formula changes.
```

- [ ] **Step 5: Add charter link to PRODUCT_ONE_PAGER**

Add one concise reference to the Phase A charter.

Required meaning:

```text
The charter defines the product-route and system-architecture guardrails for turning the runtime foundation into a game-like, observable, configurable AI-vs-AI Werewolf platform.
```

---

## Task 5: Add Phase A Charter Entry Without Rewriting The Charter

**Files:**

- Modify: `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md` only if a status/link note is needed
- Modify: `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.zh.md` only if the English charter receives the same status/link note
- Test: grep checks in Task 6

- [ ] **Step 1: Decide whether charter needs a status note**

Open the charter headers.

Run:

```powershell
Get-Content -Path 'docs\harness\designs\2026-06-03--live-ai-werewolf-experiment-platform-charter.md' -TotalCount 12
Get-Content -Path 'docs\harness\designs\2026-06-03--live-ai-werewolf-experiment-platform-charter.zh.md' -TotalCount 12
```

Expected:

- Both say `Status: draft` or equivalent.

- [ ] **Step 2: Keep draft status unless user approves promotion**

Do not change charter status from `draft` to `accepted` unless the user explicitly approves that status change.

If user approves promotion during execution, update both files consistently:

```markdown
Status: accepted
```

and:

```markdown
状态：已接受
```

- [ ] **Step 3: Avoid rewriting charter content**

Do not modify Phase A-H content during Phase B unless the change is a direct link/status consistency fix.

The charter must remain a route/design source, not a Phase B implementation spec.

---

## Task 6: Validation And Review Packet

**Files:**

- Create/Modify: `.logs/review/latest/review-packet.md`
- Modify: `.oh-my-harness/tree.md` only through tree hook if needed
- Test: command outputs below

- [ ] **Step 1: Run targeted stale-status grep**

Run:

```powershell
Select-String -Path 'README.md','docs\PRODUCT_ONE_PAGER.md','docs\ROADMAP.md','docs\TASKS.md' -Pattern 'G1h.*next_candidate|next_candidate.*G1h|next implementation candidate is G1h|下一候选开发点是 G1h|has not completed:\s*$|G1h Live Runtime Event Spine\.' -Context 1,2
```

Expected:

- No result claims G1h is still `next_candidate`.
- No result places G1h in the current not-completed list.
- If a broad heading or dependency graph still mentions G1h, it must not imply uncompleted status.

- [ ] **Step 2: Run not-completed capability grep**

Run:

```powershell
Select-String -Path 'README.md','docs\PRODUCT_ONE_PAGER.md','docs\ROADMAP.md','docs\TASKS.md' -Pattern 'observer server|Local Observer Server|Qt/QML|Qt client|Web observer|profile editor|prompt editor|leaderboard|Leaderboard' -Context 1,2
```

Expected:

- Results still state observer server / Qt-Web client / prompt-profile editor / leaderboard are future or not completed.
- No result claims those capabilities are completed.

- [ ] **Step 3: Run diff whitespace check**

Run:

```powershell
git -c safe.directory=G:/Werewolf-agent diff --check
```

Expected:

- No whitespace errors.

- [ ] **Step 4: Run changed-file checks**

Run:

```powershell
git -c safe.directory=G:/Werewolf-agent diff --stat
git -c safe.directory=G:/Werewolf-agent diff --name-only
git -c safe.directory=G:/Werewolf-agent status --short
```

Expected:

- Changed files are within the allowlist.
- No `src/**`, `tests/**`, validators, generated fixtures, demo files, ADRs, historical plans/reviews, `.agents/skills/**`, or `.github/**` changes.

- [ ] **Step 5: Run tree hook if needed**

Run only if files were created, deleted, or renamed:

```powershell
node .codex/hooks/tree.mjs --force
```

Expected:

- `.oh-my-harness/tree.md` reflects created/deleted/renamed files.
- Do not hand-edit `.oh-my-harness/tree.md`.

- [ ] **Step 6: Final reporting checklist**

Final report must include:

```text
git diff --stat
git diff --name-only
allowlist check
forbidden-scope check
tests or reason tests are unnecessary
```

Expected test rationale:

```text
No runtime tests were run because Phase B is docs-only route/status alignment and does not change code, validators, fixtures, or generated artifacts.
```

## Completion Criteria

Phase B is complete only when all are true:

```text
G1h is completed.
G2a is the next implementation track.
Observer server / Qt client / profile editor / leaderboard are not completed.
```

and:

```text
Changed files remain within allowlist.
No runtime, server, UI, scoring, validators, tests, generated fixtures, demos, ADRs, historical reviews, or GitHub workflow files changed.
```
