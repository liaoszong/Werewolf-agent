# S0 Gold Game Seed — Werewolf-agent Phase 1

## Status

- Task: S0
- Source type: manually authored virtual game
- Game facts label: `[结构化事件]`
- Author notes label: `[人工 gold sample]`
- Mock data: none
- AI-generated data: none

## Scope

This file defines one logically self-contained 6-player Werewolf game for Phase 1 spike validation.

Role setup is fixed for Phase 1:

| Player | Role | Team |
|---|---|---|
| p1 | werewolf | werewolf |
| p2 | werewolf | werewolf |
| p3 | seer | villager |
| p4 | witch | villager |
| p5 | villager | villager |
| p6 | villager | villager |

## Game Premise

This is a manually authored virtual game. It is not copied from a public video, public transcript, streamer match, or forum record.

The game is intentionally designed to exercise Phase 1 scoring and attribution:

- The seer obtains a correct wolf check but is eliminated on Day 1.
- The witch uses the save potion on Night 1 and poison potion on Night 2.
- The village recovers through deterministic public evidence and eliminates both werewolves.
- The game produces clear turn points for later S3 attribution validation.

Day 2 note for scoring conversion: after Night 2 resolution, the living players are p1, p4, and p6. p1 is a werewolf, while p4 and p6 are the remaining village-team voters. This makes the Day 2 village vote cohesion calculation explicit: the village-team voters are p4 and p6, and both vote for p1.

## Rule Assumptions for This Gold Game

| Rule | Assumption |
|---|---|
| Player count | 6 players |
| Role setup | 2 werewolves, 1 seer, 1 witch, 2 villagers |
| Hunter | Not included |
| Witch save potion | One use per game |
| Witch poison potion | One use per game |
| Witch same-night save and poison | Not used in this game |
| Night death reveal | Public death events are recorded after night resolution |
| Elimination reveal | Eliminated player's role is publicly revealed |
| Win condition | Village wins when all werewolves are eliminated |
| Speech content | Stored as summarized public events, not copied dialogue |

## Event Chain

| event_id | seq | round | phase | type | actor | target | visibility | summary | label |
|---|---:|---:|---|---|---|---|---|---|---|
| g001_e001 | 1 | 0 | setup | role_assignment | system | p1 | specific_player_ids | p1 receives the werewolf role. | [结构化事件] |
| g001_e002 | 2 | 0 | setup | role_assignment | system | p2 | specific_player_ids | p2 receives the werewolf role. | [结构化事件] |
| g001_e003 | 3 | 0 | setup | role_assignment | system | p3 | specific_player_ids | p3 receives the seer role. | [结构化事件] |
| g001_e004 | 4 | 0 | setup | role_assignment | system | p4 | specific_player_ids | p4 receives the witch role. | [结构化事件] |
| g001_e005 | 5 | 0 | setup | role_assignment | system | p5 | specific_player_ids | p5 receives the villager role. | [结构化事件] |
| g001_e006 | 6 | 0 | setup | role_assignment | system | p6 | specific_player_ids | p6 receives the villager role. | [结构化事件] |
| g001_e007 | 7 | 1 | night | werewolf_kill | wolf_team | p5 | werewolf_team | The werewolf team chooses p5 as the kill target. | [结构化事件] |
| g001_e008 | 8 | 1 | night | seer_check | p3 | p1 | seer | p3 checks p1 and receives a werewolf result. | [结构化事件] |
| g001_e009 | 9 | 1 | night | witch_save | p4 | p5 | witch | p4 uses the save potion on p5. | [结构化事件] |
| g001_e010 | 10 | 1 | day | player_speech | p3 | p1 | public | p3 claims useful night information and pushes suspicion toward p1. | [结构化事件] |
| g001_e011 | 11 | 1 | day | player_speech | p1 | p3 | public | p1 challenges p3 and frames p3 as a wolf trying to force an early mis-elimination. | [结构化事件] |
| g001_e012 | 12 | 1 | day | player_speech | p2 | p3 | public | p2 supports p1 and argues that p3's pressure is too aggressive. | [结构化事件] |
| g001_e013 | 13 | 1 | day | player_speech | p4 | p1 | public | p4 notes that p1 and p2 are aligned too quickly but does not reveal witch identity. | [结构化事件] |
| g001_e014 | 14 | 1 | day | player_speech | p5 | p3 | public | p5 says p3's claim lacks enough public evidence and leans toward voting p3. | [结构化事件] |
| g001_e015 | 15 | 1 | day | player_speech | p6 | p1 | public | p6 is uncertain but sees a possible p1 and p2 pairing. | [结构化事件] |
| g001_e016 | 16 | 1 | day | player_vote | p1 | p3 | public | p1 votes for p3. | [结构化事件] |
| g001_e017 | 17 | 1 | day | player_vote | p2 | p3 | public | p2 votes for p3. | [结构化事件] |
| g001_e018 | 18 | 1 | day | player_vote | p3 | p1 | public | p3 votes for p1. | [结构化事件] |
| g001_e019 | 19 | 1 | day | player_vote | p4 | p1 | public | p4 votes for p1. | [结构化事件] |
| g001_e020 | 20 | 1 | day | player_vote | p5 | p3 | public | p5 votes for p3. | [结构化事件] |
| g001_e021 | 21 | 1 | day | player_vote | p6 | p3 | public | p6 votes for p3. | [结构化事件] |
| g001_e022 | 22 | 1 | day | player_eliminated | system | p3 | public | p3 is eliminated by a 4-2 vote. | [结构化事件] |
| g001_e023 | 23 | 1 | day | role_revealed | system | p3 | public | p3 is revealed as the seer. | [结构化事件] |
| g001_e024 | 24 | 2 | night | werewolf_kill | wolf_team | p5 | werewolf_team | The werewolf team again chooses p5 as the kill target. | [结构化事件] |
| g001_e025 | 25 | 2 | night | witch_poison | p4 | p2 | witch | p4 uses the poison potion on p2 after p3's public seer reveal, p2's public Day 1 support for p1, and p2's public vote against p3 make p2's alignment suspicious. | [结构化事件] |
| g001_e026 | 26 | 2 | day | player_died | system | p5 | public | p5 dies from the werewolf night kill. | [结构化事件] |
| g001_e027 | 27 | 2 | day | player_died | system | p2 | public | p2 dies from the witch poison. | [结构化事件] |
| g001_e028 | 28 | 2 | day | role_revealed | system | p5 | public | p5 is revealed as a villager. | [结构化事件] |
| g001_e029 | 29 | 2 | day | role_revealed | system | p2 | public | p2 is revealed as a werewolf. | [结构化事件] |
| g001_e030 | 30 | 2 | day | player_speech | p4 | p1 | public | p4 argues that p1 and p2 formed a coordinated push against the real seer. | [结构化事件] |
| g001_e031 | 31 | 2 | day | player_speech | p1 | p4 | public | p1 argues that p4 is using p2's death to force an easy final vote. | [结构化事件] |
| g001_e032 | 32 | 2 | day | player_speech | p6 | p1 | public | p6 accepts that p2's revealed role makes p1's Day 1 behavior highly suspicious. | [结构化事件] |
| g001_e033 | 33 | 2 | day | player_vote | p1 | p4 | public | p1 votes for p4. | [结构化事件] |
| g001_e034 | 34 | 2 | day | player_vote | p4 | p1 | public | p4 votes for p1. | [结构化事件] |
| g001_e035 | 35 | 2 | day | player_vote | p6 | p1 | public | p6 votes for p1. | [结构化事件] |
| g001_e036 | 36 | 2 | day | player_eliminated | system | p1 | public | p1 is eliminated by a 2-1 vote. | [结构化事件] |
| g001_e037 | 37 | 2 | day | role_revealed | system | p1 | public | p1 is revealed as a werewolf. | [结构化事件] |
| g001_e038 | 38 | 2 | game_end | game_over | system | villager_team | public | The village team wins because all werewolves have been eliminated. | [结构化事件] |

## S1 Conversion Notes

These notes are not separate game events. They exist to keep the later Game Log JSON conversion unambiguous.

### Visible evidence for g001_e025

p4's Night 2 poison decision against p2 must use only information visible to p4 before the poison decision:

| Evidence event_id | Visibility | Why p4 can use it |
|---|---|---|
| g001_e011 | public | p1 publicly attacked p3 on Day 1. |
| g001_e012 | public | p2 publicly supported p1's attack on p3. |
| g001_e017 | public | p2 publicly voted for p3. |
| g001_e023 | public | p3 was publicly revealed as the seer after elimination. |

Suggested future `visible_info_refs` for g001_e025: `g001_e011`, `g001_e012`, `g001_e017`, `g001_e023`.

### Day 2 vote-cohesion note

At the start of the Day 2 vote, p2 and p5 are dead. The living players are p1, p4, and p6.

- Werewolf-team living voter: p1.
- Village-team living voters: p4 and p6.
- p4 votes for p1.
- p6 votes for p1.

For village vote cohesion, the village-team vote distribution is `{p1: 2}` over 2 village-team voters, so the Day 2 village cohesion value is `2 / 2 = 1.0`.

## Completeness Assessment

| Required item | Covered | Evidence event_id | Notes |
|---|---|---|---|
| role assignment | yes | g001_e001-g001_e006 | All 6 players have explicit roles and teams. |
| night actions | yes | g001_e007-g001_e009, g001_e024-g001_e025 | Night 1 and Night 2 actions are explicit. |
| seer check | yes | g001_e008 | The seer checks p1 and receives a werewolf result. |
| witch action | yes | g001_e009, g001_e025 | Save and poison usage are both explicit. |
| day speeches | yes | g001_e010-g001_e015, g001_e030-g001_e032 | Public speech summaries exist for each day. |
| votes | yes | g001_e016-g001_e021, g001_e033-g001_e035 | Every living voter has a target. |
| deaths | yes | g001_e022, g001_e026, g001_e027, g001_e036 | Eliminations and night deaths are explicit. |
| role reveals | yes | g001_e023, g001_e028, g001_e029, g001_e037 | Key revealed roles are explicit. |
| game over | yes | g001_e038 | Winner and end condition are explicit. |
| copyright risk | yes | Copyright / Source Risk Assessment | No external copyrighted match material is used. |
