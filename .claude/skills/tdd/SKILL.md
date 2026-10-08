---
name: tdd
description: Test-driven development for this repo. Use before writing any feature, bug fix or behaviour change (guardrails, retrieval, prompts, UI logic), and pass it to every worker.
---

# Test-Driven Development

Adapted from Pun's personal `tdd` skill for this Python/pytest project. TDD is the red → green loop; this skill is what makes the loop produce tests worth keeping.

## What a good test is

Tests verify behaviour through public interfaces, not implementation details. A good test reads like a spec line: "a number not in the retrieved chunks fails the grounding check". It survives refactors because it does not care about internal structure.

See [tests.md](tests.md) for good/bad examples (written in TypeScript; the ideas map 1:1 to pytest) and [mocking.md](mocking.md) for when to mock.

## Seams in this repo

A **seam** is the public boundary you test at. Do not ask the user to confirm seams (standing instruction in `AGENTS.md`); name the seam in one line and proceed.

| Seam | What to test there | Tier |
| --- | --- | --- |
| `guard.*` functions (length, number grounding, citation check, banner keywords, fake-transfer regex, classifier answer parsing) | Pure input → output | Fast |
| `rag.chunk()` / `rag.retrieve()` | Section labels, Appendix A split, top-k contains the expected section | Fast for chunking; live for retrieval (needs embeddings) |
| `answer_rules(question)` | `SPEC.md` §8 rules cases | Live |
| Preview reply function | `SPEC.md` §8 preview cases | Live |

`llm.py` is the system boundary (Ollama). Fast tests that need it pass a fake `complete`/`embed` in; never mock your own modules.

## Anti-patterns

- **Implementation-coupled:** mocks internal collaborators, tests private helpers, or checks through a side channel. Tell: breaks on refactor with no behaviour change.
- **Tautological:** expected value recomputed the way the code does. Expected values come from an independent source: a literal from `knowledge/SPEC-v1.0-PokeMonopoly.md` (e.g. Ultra Ball = 3 coins, +2) or `SPEC.md` §8.
- **Horizontal slicing:** writing all tests first, then all code. Work in vertical slices: one test → one minimal implementation → repeat.
- **Exact LLM wording:** never assert the model's exact sentence. Assert cheap properties: citation present, forbidden number absent, banner shown, language is Thai.

## Rules of the loop

- **Red before green.** Write the failing test, run it, confirm it fails for the intended reason, then write only enough code to pass.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Bugs start with a failing regression test.**
- **Refactoring is not part of the loop.** Do it after green, with tests still passing.
- **Never weaken a test** to make it pass, and never tune a live test to favour a model.
