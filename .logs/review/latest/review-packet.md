# Review Packet

## Metadata
- Base: `main`
- Branch: `feat/g1g-provider-replay-html`
- Generated: `2026-06-02T23:05:28+08:00`
- Packet type: clean manual A档 packet, rebuilt from fresh local verification after `scripts/dev/build_review_packet.py` was restored to `main`.
- Review scope: `git diff main...HEAD` plus direct safety scan of `docs/demo/phase3-g1f-provider-replay.html`.

## Changed Files
Source: `git -c safe.directory=G:/Werewolf-agent diff --name-only main...HEAD`

- `.oh-my-harness/tree.md`
- `docs/demo/phase3-g1f-provider-replay.html`
- `src/werewolf_eval/render_provider_replay.py`
- `tests/test_render_provider_replay.py`

Worktree hygiene note: local scratch paths `.tmp/g1f-deepseek-consensus-smoke/` and `500` are not in `main...HEAD` and must not be submitted. `docs/TASKS.md` is a separate route/status closeout update, outside the renderer implementation allowlist.

## Diff Stat
Command: `git -c safe.directory=G:/Werewolf-agent diff --stat main...HEAD`

```text
 .oh-my-harness/tree.md                      |   7 +-
 docs/demo/phase3-g1f-provider-replay.html   | 159 ++++++++++
 src/werewolf_eval/render_provider_replay.py | 472 ++++++++++++++++++++++++++++
 tests/test_render_provider_replay.py        | 370 ++++++++++++++++++++++
 4 files changed, 1006 insertions(+), 2 deletions(-)
```

## Diff Check
Command: `git -c safe.directory=G:/Werewolf-agent diff --check main...HEAD`

```text
(clean)
```

## Allowed Files Check
ALLOWLIST_CHECK = PASS

Allowed G1g files:
- `.oh-my-harness/tree.md`
- `docs/demo/phase3-g1f-provider-replay.html`
- `src/werewolf_eval/render_provider_replay.py`
- `tests/test_render_provider_replay.py`

`scripts/dev/build_review_packet.py` is not in `main...HEAD`.

## Forbidden Patterns Check
FORBIDDEN_PATTERN_CHECK = PASS
FORBIDDEN_PATTERN_SCAN = PASS

Fresh strict-risk scan over the four changed files found no runtime or rendered-output risk for:
- raw API key / `x-api-key` / `sk-...`
- `Authorization` / `Bearer`
- secret value exposure
- network/API client imports such as `requests`, `httpx`, `aiohttp`, `openai`, `anthropic`, `urllib`
- `socket`, `subprocess`, or `os.environ` usage in the replay renderer

Benign textual self-references were classified as non-risk:
- `.oh-my-harness/tree.md:160` contains the existing directory name `secrets/`, not a committed secret value.
- `tests/test_render_provider_replay.py:258` and `tests/test_render_provider_replay.py:290` assert that `<script` is absent.

## HTML Output Safety Check
HTML_OUTPUT_SAFETY_CHECK = PASS

Target: `docs/demo/phase3-g1f-provider-replay.html`

Direct scan result:
- `script=False`
- `external_http=False`
- `src_attr=False`
- `href_attr=False`
- `css_url=False`
- `authorization=False`
- `bearer=False`
- `api_key=False`
- `secret=False`
- `sk_key=False`

The committed HTML contains no `<script>`, no external resource reference, no raw API key, no `Authorization` header, and no external URL.

## Dependency / Import Diff
- Dependency manifest changes: none.
- Replay renderer imports only `argparse`, `json`, `html.escape`, `pathlib.Path`, and `typing.Any` (`src/werewolf_eval/render_provider_replay.py:3-7`).
- No `engine/`, provider runtime, scoring runtime, dependency manifest, or `.tmp/` file is in `main...HEAD`.

## Test Summary
Environment: PowerShell with `$env:PYTHONPATH='src'`.

### `python -m unittest tests.test_render_provider_replay -v`
Exit: 0 (PASS)

```text
Ran 8 tests in 0.030s

OK
```

### `python -m unittest discover -s tests -v`
Exit: 0 (PASS)

```text
Ran 193 tests in 4.626s

OK
```

### `python -m compileall -q src tests`
Exit: 0 (PASS)

## Key Evidence Pointers
- JSON-only input and no live API call: `src/werewolf_eval/render_provider_replay.py:403-419` reads optional logs with `Path(...).read_text(encoding="utf-8")` and `json.loads(...)`; `src/werewolf_eval/render_provider_replay.py:467` prints `live_api=not_called`.
- Escaping: `src/werewolf_eval/render_provider_replay.py:81-85` routes table cell rendering through `html.escape(..., quote=True)`.
- UTF-8 output: `src/werewolf_eval/render_provider_replay.py:429` writes HTML with `encoding="utf-8"`.
- Escaping tests: `tests/test_render_provider_replay.py:244-290` cover unsafe provider content and assert `<script` is absent.
- HTML artifact scan: `docs/demo/phase3-g1f-provider-replay.html` direct scan shows no script, external resources, secret, raw key, or authorization header.

## Evidence Map
| Acceptance | Evidence | Status |
|---|---|---|
| A1:Only allowlisted files changed | `git diff --name-only main...HEAD` lists exactly the four G1g files above; `ALLOWLIST_CHECK=PASS` | PASS |
| A2:Renderer consumes existing JSON logs only, no network/API calls | `render_provider_replay.py:403-419` reads JSON from disk; imports at `:3-7` contain no network/API clients; CLI prints `live_api=not_called` at `:467` | PASS |
| A3:HTML is single-file static output with no JS, no external resources | `HTML_OUTPUT_SAFETY_CHECK=PASS`; direct scan has `script=False`, `external_http=False`, `src_attr=False`, `href_attr=False`, `css_url=False` | PASS |
| A4:All untrusted JSON values escaped via html.escape | `_html()` uses `html.escape(..., quote=True)` at `render_provider_replay.py:81-82`; `_row()` uses `_html()` at `:85`; unsafe provider tests pass | PASS |
| A5:Report includes game, player, timeline, decision, consensus, trace, failure sections | `tests.test_render_provider_replay` 8/8 PASS, including required section coverage | PASS |
| A6:Report labels `[DeepSeek API output]` and boundary statement | Target HTML contains source label and "未发起任何实时 API 调用"; renderer CLI prints `live_api=not_called` | PASS |
| A7:Tests cover context, HTML content, escaping, and CLI output | Targeted replay test suite ran 8 tests and passed | PASS |
| A8:Full unittest and compile check pass | Full unittest ran 193 tests and passed; compileall exit 0 | PASS |
| A9:No dependency/provider/engine/scoring/.tmp changes committed | `main...HEAD` has only the four allowlisted files; no manifest, engine, provider runtime, scoring runtime, or `.tmp/` path | PASS |
| A10:Review packet contains required machine evidence | Includes changed files, diff stat, diff check, allowlist, forbidden scan, HTML safety scan, imports, tests, evidence map, checklist, and risk notes | PASS |
| A11:Forbidden scan differentiates test literals from rendered HTML | Strict-risk scan is PASS; benign test/tree self-references classified separately; rendered HTML safety scan is PASS | PASS |

## Acceptance Checklist
- [x] A1:Only allowlisted files changed
- [x] A2:Renderer consumes existing JSON logs only, no network/API calls
- [x] A3:HTML is single-file static output with no JS, no external resources
- [x] A4:All untrusted JSON values escaped via html.escape
- [x] A5:Report includes game, player, timeline, decision, consensus, trace, failure sections
- [x] A6:Report labels `[DeepSeek API output]` and boundary statement
- [x] A7:Tests cover context, HTML content, escaping, and CLI output
- [x] A8:Full unittest and compile check pass
- [x] A9:No dependency/provider/engine/scoring/.tmp changes committed
- [x] A10:Review packet contains all required machine evidence
- [x] A11:Forbidden scan differentiates test literals from rendered HTML

## Implementer Risk Notes
- Committed HTML is a replay artifact for G1f smoke-test output; it does not call live APIs.
- `.tmp/` exists locally and must remain untracked/out of PR scope.
- `build_review_packet.py` is not part of `main...HEAD` and should remain unchanged for this PR.

## Review Trigger Result
NO_BLOCKING_TRIGGER

- PACKET_TOO_LARGE = NO
- ALLOWLIST_CHECK = PASS
- FORBIDDEN_PATTERN_CHECK = PASS
- HTML_OUTPUT_SAFETY_CHECK = PASS
- TESTS = PASS
