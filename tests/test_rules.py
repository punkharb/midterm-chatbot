import rules

RETRIEVED = [
    ({"section": "§4.7", "heading": "4.7 Selling at Start", "text": "4.7 Selling at Start\n\n+5 coins"}, 0.6),
    ({"section": "Appendix A — Items", "heading": "Items", "text": "Items\n\n| Ultra Ball | 3 | +2 |"}, 0.5),
    ({"section": "§4.1", "heading": "4.1 Setup and board", "text": "4.1 Setup\n\n20 coins"}, 0.4),
]


def fake_retrieve(question: str, k: int = 4):
    return RETRIEVED[:k]


def fake_complete(reply: str):
    def complete(system: str, messages: list[dict[str, str]], **options: float) -> str:
        return reply

    return complete


def test_sources_are_the_cited_sections_that_were_retrieved():
    reply = "You get +5 coins [§4.7]. An Ultra Ball costs 3 [Appendix A]. Gyms [§4.4]."
    answer, sources = rules.answer_rules("q", complete=fake_complete(reply), retrieve=fake_retrieve)
    assert answer == reply
    assert sources == ["§4.7", "Appendix A — Items"]  # §4.4 was not retrieved


def test_thai_questions_carry_a_reply_in_thai_reminder():
    sent: list[str] = []

    def complete(system: str, messages: list[dict[str, str]], **options: float) -> str:
        sent.append(messages[-1]["content"])
        return "ok"

    rules.answer_rules("ถ้าไม่มีบอลทำไง", complete=complete, retrieve=fake_retrieve)
    rules.answer_rules("What if I have no Ball?", complete=complete, retrieve=fake_retrieve)
    assert sent[0].startswith("ถ้าไม่มีบอลทำไง") and "ภาษาไทย" in sent[0]
    assert sent[1] == "What if I have no Ball?"


POKEMON = {
    "section": "Appendix A — Pokémon and Abilities",
    "heading": "Pokémon and Abilities",
    "text": "Pokémon and Abilities\n\n| Species | Rarity | Base |\n|---|---|---:|\n"
    "| Gyarados | rare | 20 |\n| Dratini | rare | 26 |",
}
SELLING = {"section": "§4.7", "heading": "4.7 Selling", "text": "4.7 Selling\n\nEverything else uses the Base Sale."}


def answer_with(reply: str, chunks: list[dict[str, str]]) -> tuple[str, list[str]]:
    return rules.answer_rules(
        "q", complete=fake_complete(reply), retrieve=lambda q, k=4: [(c, 0.5) for c in chunks]
    )


def test_a_citation_without_the_claimed_number_points_to_the_row_that_has_it():
    answer, sources = answer_with("Dratini's base sale value is 26 coins [§4.7].", [SELLING, POKEMON])
    assert answer == "Dratini's base sale value is 26 coins [Appendix A — Pokémon and Abilities]."
    assert sources == ["Appendix A — Pokémon and Abilities"]


def test_citations_that_hold_the_number_or_have_no_number_are_kept():
    reply = "Dratini sells for 26 [Appendix A — Pokémon and Abilities]. Base Sale is used [§4.7]."
    assert answer_with(reply, [SELLING, POKEMON]) == (reply, ["Appendix A — Pokémon and Abilities", "§4.7"])
    # a number found nowhere is left for the grounding check (step 3) to reject
    assert answer_with("Dratini sells for 99 [§4.7].", [SELLING, POKEMON])[0] == "Dratini sells for 99 [§4.7]."


def test_a_made_up_number_is_not_given_an_unrelated_source():
    setup = {"section": "§4.1", "heading": "4.1", "text": "4.1\n\n- Starting kit: 20 coins, the class Starter, 5 Poké Balls"}
    for reply in ("An Ultra Ball costs 20 coins [§4.7].", "ดราทินี่ขายได้ 20 เหรียญ [§4.7]"):
        assert answer_with(reply, [setup, SELLING, POKEMON])[0] == reply


def test_a_cited_block_holding_the_numbers_on_separate_lines_is_kept():
    start = {"section": "§4.7", "heading": "4.7", "text": "4.7\n\n- +5 coins\n- `creditedLap` +1"}
    turn = {"section": "§4.2", "heading": "4.2", "text": "4.2\n\n5. collect 5 coins, add 1 to `creditedLap`"}
    reply = "You get +5 coins and `creditedLap` +1 [§4.7]."
    assert answer_with(reply, [start, turn])[0] == reply


def test_citation_matching_handles_lists_and_section_boundaries():
    chunks = [{"section": s, "heading": "", "text": ""} for s in ("§10", "§4.1", "§4.7", "Appendix A — Items")]
    assert rules.cited_sections("[§1]", chunks) == []
    assert rules.cited_sections("[§4.7, §4.1]", chunks) == ["§4.7", "§4.1"]
    assert rules.cited_sections("[Appendix A — Items]", chunks) == ["Appendix A — Items"]
    assert rules.cited_sections("no citation here", chunks) == []


def test_appendix_citations_tolerate_model_variations():
    chunks = [{"section": s, "heading": "", "text": ""} for s in ("Appendix A — Board", "Appendix A — Items", "§4.7")]
    for cite in ("[Appendix A – Items]", "[Appendix A - Items]", "[Appendix A—Items]", "[Appendix A: Items]"):
        assert rules.cited_sections(cite, chunks) == ["Appendix A — Items"], cite
    assert rules.cited_sections("[Appendix A — Items table]", chunks) == ["Appendix A — Items"]
    assert rules.cited_sections("[Appendix A — Items and §4.7]", chunks) == ["Appendix A — Items", "§4.7"]
    # an unknown subheading still counts as citing Appendix A
    assert rules.cited_sections("[Appendix A — Pokémon]", chunks) == ["Appendix A — Board", "Appendix A — Items"]
