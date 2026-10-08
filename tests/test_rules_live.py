"""SPEC.md §8 cases 1–5 through answer_rules(). Expected values are literals from
knowledge/SPEC-v1.0-PokeMonopoly.md; LLM wording is never asserted exactly."""

import re

import pytest

import rules

CITATION = re.compile(r"\[[^\]]*\]")
THAI = re.compile(r"[\u0e00-\u0e7f]")


def ask(question: str) -> tuple[str, list[str]]:
    answer, sources = rules.answer_rules(question)
    print(f"\nQ: {question}\nA: {answer}\nSources: {sources}")
    return CITATION.sub("", answer), sources  # so a "§4.3" citation never satisfies a "3" check


@pytest.mark.live
def test_case_1_pass_start():
    answer, sources = ask("What do I get when I pass Start?")
    assert "5" in answer
    assert "Sell Phase" in answer
    assert {"§4.7", "§4.2", "§4.1"} & set(sources)


@pytest.mark.live
def test_case_2_no_ball_thai():
    answer, sources = ask("ถ้าไม่มีบอลแต่เจอโปเกมอนทำไงได้บ้าง")
    assert THAI.search(answer)
    assert "No Ball" in answer  # SPEC §8: catch button greyed with "No Ball"
    assert {"§3.1", "§4.3"} & set(sources)


@pytest.mark.live
def test_case_3_ultra_ball():
    answer, sources = ask("How much does an Ultra Ball cost and what bonus?")
    assert "3" in answer and "+2" in answer
    assert any(s.startswith("Appendix A") for s in sources)


@pytest.mark.live
def test_case_4_dratini_base_sale():
    answer, sources = ask("What is Dratini's base sale value?")
    assert "26" in answer
    assert any(s.startswith("Appendix A") for s in sources)


@pytest.mark.live
def test_case_5_tie_break():
    answer, sources = ask("How does the tie-break work?")
    assert "badge" in answer.lower() and "co-winner" in answer.lower()
    assert "§4.7" in sources
