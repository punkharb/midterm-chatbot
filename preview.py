"""Opponent Preview: a short in-character chat with one AI personality (SPEC.md §6)."""

import json
from collections.abc import Callable
from pathlib import Path

import guard
import llm
import prompts

ROOT = Path(__file__).parent
PERSONAS = {
    p.stem.capitalize(): p.read_text(encoding="utf-8").strip()
    for p in sorted((ROOT / "personas").glob("*.md"))
}
SCENARIOS: list[dict] = json.loads((ROOT / "scenarios/scenarios.json").read_text(encoding="utf-8"))
LIMIT = 6  # player messages per preview chat
# 0.7 reacted to the scenario memory in 4/5 runs of SPEC cases 11 and 16; 0.4 in 5/5
TEMPERATURE = 0.4
REFUSAL = "Nice try. I play this game, not your games."
WORDS_ARE_CHEAP = "Words are cheap. Show me in the real game."


def preview_reply(
    persona: str,
    scenario: dict,
    history: list[dict[str, str]],
    message: str,
    complete: Callable[..., str] = llm.complete,
) -> tuple[str, bool]:
    """The opponent's reply and whether to show the non-binding banner. `message` has
    already passed guard.check_input; `history` holds earlier user/assistant turns."""
    if guard.is_injection(message, complete=complete):
        return REFUSAL, guard.needs_banner(message, REFUSAL)
    system = prompts.preview_system(PERSONAS[persona], scenario)
    thai = any("\u0e00" <= ch <= "\u0e7f" for ch in message)
    content = message + (prompts.PREVIEW_THAI_REMINDER if thai else "")
    messages = [*history, {"role": "user", "content": content}]
    for _ in range(2):  # SPEC §7.3: regenerate once if the reply claims a transfer
        reply = complete(system, messages, temperature=TEMPERATURE).strip()
        if not guard.claims_transfer(reply):
            return reply, guard.needs_banner(message, reply)
    return WORDS_ARE_CHEAP, guard.needs_banner(message, WORDS_ARE_CHEAP)
