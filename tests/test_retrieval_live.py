"""SPEC.md §10 step 1: the top 4 chunks for §8 cases 1–5 hold the answer's section."""

import pytest

import rag

CASES = [
    ("What do I get when I pass Start?", ("§4.7", "§4.2", "§4.1")),
    ("ถ้าไม่มีบอลแต่เจอโปเกมอนทำไงได้บ้าง", ("§3.1", "§4.3")),
    ("How much does an Ultra Ball cost and what bonus?", ("Appendix A — Items",)),
    ("What is Dratini's base sale value?", ("Appendix A — Pokémon and Abilities",)),
    ("How does the tie-break work?", ("§4.7",)),
]


@pytest.mark.live
@pytest.mark.parametrize(("question", "sections"), CASES)
def test_top_chunks_hold_the_answer(question, sections):
    top = rag.retrieve(question, k=4)
    print(question, [(c["section"], round(s, 3)) for c, s in top])
    assert any(c["section"] in sections for c, _ in top)
