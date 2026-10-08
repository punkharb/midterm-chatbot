---
name: rules-map
description: Maps Poke Monopoly rule topics to sections of knowledge/SPEC-v1.0-PokeMonopoly.md. Use when writing test cases or expected answers, checking a citation, tuning chunking, or verifying a fact the bot states.
---

# Rules map

Adapted from the game team's `game-rules` skill. The rules live in `knowledge/SPEC-v1.0-PokeMonopoly.md`, not here. Find the topic, read that section, and take expected values from it as literals. Never edit the knowledge file to make a test pass.

| Topic | Section |
| --- | --- |
| Goal, delivery scope (Quick 2 Laps, 1–3 AIs) | §1 |
| Screens and flow; unspecified situations ("No Ball", empty Shop budget...) | §3, §3.1 |
| Setup, board, starting kit (20 coins, 5 Poké Balls), Start income (+5) | §4.1 |
| Turn order, action budgets, social window | §4.2 |
| Catching and Balls | §4.3 |
| Combat, PvP, Gym, Tired, Battle Reward | §4.4 |
| Encounters, Abilities, evolution, Starters, Rescue Starter | §4.5 |
| Items, Shop, hostile items, slowing effects, Events, deck shuffle | §4.6 |
| Selling at Start, Laps, game end, winner and tie-break | §4.7 |
| Chat (280 chars), Deal Cards, concession budget, `no_attack` promise, trust | §4.8 |
| Personalities (names only; only Greedy is described, in Appendix B) | §5.5 |
| Board layout, classes, species stats, Abilities, evolution, item prices | Appendix A |
| Example AI request (Greedy description) | Appendix B |

Sections §2, §5.1–5.4, §5.6–§12 are about how the game is engineered (Jev, engine, plan). Players rarely ask about them.

## Gotchas

- Appendix A uses bold subheadings (`**Classes**`, `**Pokémon and Abilities**`, `**Evolution**`, `**Items**`), not `###`. Chunking must split on them (`SPEC.md` §4).
- Bold subheadings also appear inside §3, §4.2, §4.6, §4.8 and §8; they stay inside their parent section's chunk.
- Some facts appear in two places (Start income in §4.1, §4.2 step 5 and §4.7). Tests accept any correct section.
- Game values differ from real Pokémon games on purpose (e.g. Gyarados Battle 5, DC 5). The bot must never "correct" them.
