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
