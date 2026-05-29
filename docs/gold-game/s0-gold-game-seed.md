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
