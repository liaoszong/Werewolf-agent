# Text Injection Channels — registry, visibility, and the source-id gap

> **What this is.** Several places append free text directly to a seat's
> `observation_text` *after* the visibility-checked observation is rendered. These
> "injection channels" carry information into the model's prompt that did NOT pass
> through `observation_source_event_ids` / the I4b oracle. This spec is the
> authoritative registry of every such channel, the input each may consume, its
> visibility level, and whether it must carry source ids. Closed out from the
> 2026-06-12 system-view audit item **C3-2 (merged A45-5)**.
>
> **System view.** SYS-B1 (Agent Memory / Context Engineering) × SYS-A4 (Information
> Visibility, I4b oracle) × SYS-C3 (quality defenses). The structural root cause and
> the long-term fix below tie to SYS-A2 (EffectQueue / CapabilityLedger).
>
> **Scope.** Spec only — no renderer byte change, no channel migration in this pass.

---

## 1. Why injection channels exist (the structural root cause)

The visibility oracle is event-sourced: a seat's prompt is built from events it may
see, and `assert_prompt_entitled` / I4b verify every sourcing event id is one that
seat could legitimately see. But some **legitimate** role knowledge has no
seat-visible event to source:

- The wolf kill is emitted with `werewolf_team` visibility, so the witch's
  role-filtered observation never contains tonight's victim — yet the witch
  legitimately must know the victim to satisfy the `target == victim` save rule
  (`augment_witch_observation`, R-04 fix).

Because the oracle cannot express "the witch legally knows the kill target", that
knowledge is forced to **bypass** the event channel and is appended as free text.
The防线 then cannot distinguish a *legitimate* injection from a *leak* injection —
both are invisible to I4b. The negative scan (`tests/test_c3_negative_scan.py`) is
the current compensating control: it runs a guard board and asserts non-witch seats
never receive the witch's victim text or coordination guidance.

---

## 2. Injection point registry

Every channel that writes to `observation_text` outside the rendered observation.
Call sites are in `emergent_engine.py`; renderer methods in `prompt_renderers.py`
(per-version bodies in `prompt_v2/v3/v4.py`).

| # | Channel | Call site | Input consumed | Visibility of input | Carries source ids? |
|---|---|---|---|---|---|
| 1 | `augment_witch_observation` | `_resolve_witch` (`emergent_engine.py:788`) | tonight's wolf `victim` | witch's own legal knowledge (kill is `werewolf_team`-visible; witch entitled by save rule) | **No** (exempt — see §3) |
| 2 | `witch_obs_suffix` (v4 = `render_witch_coord_suffix`) | `_resolve_witch` (`:789`) | public board composition (`board_card` has-guard flag) + witch's own state (`victim`, `save_used`) | witch-private static guidance; **never** the guard's target/aliveness (prompt_v4 §3 gate) | **No** (static + own-state; see §3) |
| 3 | `speech_obs_suffix` (v3 = `render_claim_digest`) | `_resolve_speech` (`:895`) | cross-round claim ledger (scribe digest of **public** `player_speech`) | public (derived only from public speeches) | **No** (public-only; see §3) |
| 4 | `action_obs_suffix` (v3 = `render_vote_scaffold`) | day vote (`:541`) | claim ledger (same public source as #3) | public | **No** (public-only; see §3) |
| 5 | `render_scribe_input` (scribe request body) | `_run_scribe` (`:957`) | THIS round's public `player_speech` summaries | public; numbered so claims can reference source by index | source ids empty by construction (scribe is not a player; `observation_source_event_ids: []`) |
| 6 | `HUNTER_SHOT_OBSERVATION_SUFFIX` | `_resolve_hunter_shot` (`:1032`) | none (static string) | public static | **No** (constant text, no data) |

Note: channels 3/4/5 funnel only **public** speech through the scribe; channel 1 is
the one carrying genuinely role-private (but legal) knowledge; channels 2/6 are
static or own-state guidance. The leak-relevant channel is #1 (and #2's gate).

---

## 3. Source-id requirement, temporary exemptions, and machine-check compensation

**Requirement (target state).** Any memory/knowledge injected into a prompt SHOULD
flow through an id-bearing, visibility-checked event so I4b can verify it — the
安全网 spec's rule "任何记忆注入必须带 source ids 过 I4b". Under the current
mechanism, none of channels 1–6 can satisfy this (the oracle has no event to point
at), so the rule is **vacuously true** for them today.

**Temporary exemptions (current state, allowed until the §4 migration):**

| Channel | Exemption rationale | Compensating machine check |
|---|---|---|
| 1 `augment_witch_observation` | witch's legal kill-target knowledge has no witch-visible source event | `tests/test_c3_negative_scan.py` — non-witch seats never see victim text |
| 2 `witch_obs_suffix` | static guidance + own-state; 3-condition gate proven byte-equal off-arm | `test_c3_negative_scan.py` (coord guidance absent on non-witch seats) + prompt_v4 golden canaries |
| 3/4 claim digest / vote scaffold | derived solely from **public** speeches | scribe input is public by construction; ledger never ingests private events |
| 5 `render_scribe_input` | scribe is a non-player scaffold over public speeches | `observation_source_event_ids` is `[]`; scribe output is non-adjudicating |
| 6 hunter suffix | constant string, no data | golden byte-lock on the action prompt |

**Hard rule for new channels:** a NEW injection channel that would carry
**role-private** data (anything beyond public events + the actor's own state) is NOT
allowed under exemption — it must either (a) source a real visible event id, or
(b) ship with a dedicated negative-scan test proving no other seat receives it, and
be registered here. The drift sentinel
(`tests/test_injection_registry_sentinel.py`) fails if a new channel appears
unregistered.

---

## 4. Long-term plan — migrate legal role knowledge onto an id-bearing channel

The durable fix removes the bypass, not just scans it:

1. **Emit a witch-visible "kill notice" event.** When the night kill resolves, emit
   an event whose visibility entitles the witch (a new role-scoped visibility, the
   same pattern guard protect already uses). The witch's observation then sources
   the victim from a real event id → channel #1 disappears and I4b covers it.
2. **Model coordination/guidance as state, not text.** Channel #2's guidance is
   static; once the witch sources the victim from an event, the guidance can be part
   of the rendered action contract (versioned bytes) rather than a post-hoc append.
3. **EffectQueue / CapabilityLedger boundary (SYS-A2).** This migration is the same
   seam as the witch potion ledger (②b) and the EffectQueue: "what a role legally
   knows / may do" becomes data on the runtime state + visible events, consumed by
   the renderer through the normal (id-bearing) observation path. Injection channels
   are an interim measure that EffectQueue/ledger work should retire. Until then,
   §3's exemptions + scans hold the line.

This is a design direction, not a committed task; it lands when the EffectQueue /
ledger work (SYS-A2) is scheduled. No engine change is made here.

---

## 5. Review checklist — adding or changing an injection channel

Before merging any change that appends to `observation_text` outside the rendered
observation:

- [ ] **Registered:** the channel is in §2's table (name, call site, input,
      visibility, source-id status). The drift sentinel enforces this.
- [ ] **Visibility classified:** the input is exactly one of {public events,
      actor's own state, static text}. If it is role-private data, STOP — it needs a
      real visible event id (see §4), not an exemption.
- [ ] **Negative scan:** if the input is role-private-but-legal, a test proves no
      other seat ever receives it (extend `test_c3_negative_scan.py`).
- [ ] **Prompt bytes:** any change to renderer-emitted text goes through
      `guarding-prompt-bytes` (bump or coexisting version + golden + ledger). A new
      static suffix is model-visible bytes.
- [ ] **No private leak into the scribe:** scribe input must remain public speeches
      only (channels 3/4/5 depend on this).
- [ ] **Spec updated:** this file's §2 table and (if exempt) §3 table are updated in
      the same change.

---

## References

- Audit: 2026-06-12 system-view audit §C3-2 (合并 A45-5).
- Negative scan: `tests/test_c3_negative_scan.py`.
- Drift sentinel: `tests/test_injection_registry_sentinel.py`.
- Visibility oracle: `src/werewolf_eval/invariants/` (I4b), `role_visibility.py`.
- Safety-net spec: `docs/superpowers/specs/2026-06-09-p2a-invariant-safety-net-design.md`.
