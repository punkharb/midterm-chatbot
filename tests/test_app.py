"""The Streamlit app (SPEC.md §5–§7, ui-rules skill), driven with AppTest. The answer
pipelines are replaced with fakes, so these tests need no Ollama."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import guard
import llm
import preview
import rules

RULES_HEADER = "Rules Guide — answers from the official rules"
PREVIEW_HEADER = "Opponent Preview — in-character demo, not rules"
DISCLAIMER = "Coursework prototype. Not affiliated with Nintendo, The Pokémon Company or Hasbro."
FULL_GAME = "Want to see if they remember your promise? Try it in the full game."


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(rules, "answer_rules", lambda q: ("You get +5 coins [§4.7].", ["§4.7"]))
    monkeypatch.setattr(preview, "preview_reply", lambda persona, scenario, history, message: ("Coins first.", True))
    monkeypatch.setattr(rules, "warm_up", lambda: None)
    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"), default_timeout=30)
    at.run()
    return at


def texts(at: AppTest) -> str:
    parts = [e.value for kind in ("caption", "markdown", "info", "warning", "error", "success") for e in getattr(at, kind)]
    parts += [b.label for b in at.button]
    for msg in at.chat_message:
        parts += [e.value for e in msg.markdown]
    return "\n".join(str(p) for p in parts)


def test_headers_and_disclaimer_are_always_shown(app):
    shown = texts(app)
    assert RULES_HEADER in shown and PREVIEW_HEADER in shown and DISCLAIMER in shown
    assert not app.exception


def test_rules_tab_starts_with_example_questions(app):
    assert "What do I get when I pass Start?" in texts(app)


def test_a_rules_answer_shows_its_sources(app):
    app.chat_input(key="rules_input").set_value("What do I get when I pass Start?").run()
    shown = texts(app)
    assert "You get +5 coins [§4.7]." in shown and "Sources: §4.7" in shown


def test_ollama_errors_are_shown_plainly(app, monkeypatch):
    def down(q):
        raise llm.LLMError("Ollama is not running. Start it, then reload.")

    monkeypatch.setattr(rules, "answer_rules", down)
    app.chat_input(key="rules_input").set_value("Hi").run()
    assert [e.value for e in app.error] == ["Ollama is not running. Start it, then reload."]


def test_a_preview_reply_shows_the_non_binding_banner(app):
    app.chat_input(key="preview_input").set_value("Truce?").run()
    shown = texts(app)
    assert "Coins first." in shown and guard.BANNER in shown


def test_a_too_long_preview_message_is_rejected_and_not_counted(app):
    app.chat_input(key="preview_input").set_value("x" * 300).run()
    assert any("(yours: 300)" in e.value for e in app.warning)
    assert "0 of 6" in texts(app)


def test_the_preview_stops_after_six_messages(app):
    for i in range(preview.LIMIT):
        app.chat_input(key="preview_input").set_value(f"Message {i}").run()
    shown = texts(app)
    assert FULL_GAME in shown and "Preview limit reached. Try it in the full game." in shown
    assert app.chat_input(key="preview_input").disabled


def test_the_end_button_shows_the_full_game_line(app):
    app.button(key="end_preview").click().run()
    assert FULL_GAME in texts(app)


def test_changing_the_scenario_starts_a_new_chat(app):
    app.chat_input(key="preview_input").set_value("Truce?").run()
    app.selectbox(key="scenario").set_value(preview.SCENARIOS[1]["title"]).run()
    assert "Coins first." not in texts(app) and "0 of 6" in texts(app)


def test_openers_and_end_are_disabled_once_the_preview_is_over(app):
    for i in range(preview.LIMIT):
        app.chat_input(key="preview_input").set_value(f"Message {i}").run()
    assert app.button(key="opener_0").disabled and app.button(key="end_preview").disabled


def test_ending_the_preview_disables_the_openers_at_once(app):
    app.button(key="end_preview").click().run()
    assert app.button(key="opener_0").disabled and app.chat_input(key="preview_input").disabled


def test_an_opener_button_sends_its_text(app):
    app.button(key="opener_0").click().run()
    assert preview.SCENARIOS[0]["suggested_openers"][0] in texts(app) and "1 of 6" in texts(app)


def test_the_header_board_is_a_square_loop_with_go_and_gyms_on_the_corners(app):
    import re

    board = next(e.value for e in app.markdown if 'aria-label="The 24-space board"' in str(e.value))
    cells = re.findall(r'title="Space (\d+): (\w+)" style="grid-row:(\d);grid-column:(\d)">(\w+)<', board)
    assert len(cells) == 24
    spots = {(int(r), int(c)) for _, _, r, c, _ in cells}
    assert len(spots) == 24 and all(r in (1, 7) or c in (1, 7) for r, c in spots)  # every edge cell, once
    corners = {int(i): label for i, _, r, c, label in cells if int(r) in (1, 7) and int(c) in (1, 7)}
    assert corners == {0: "GO", 6: "GYM", 12: "GYM", 18: "GYM"}  # Appendix A: Gyms are spaces 6/12/18


def test_the_model_and_rules_are_loaded_when_the_app_starts(monkeypatch):
    calls = []
    monkeypatch.setattr(rules, "warm_up", lambda: calls.append(1))
    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"), default_timeout=30)
    at.run()
    assert calls == [1]


def test_a_warm_up_failure_is_shown_plainly(monkeypatch):
    def down():
        raise llm.LLMError("Ollama is not running. Start it, then reload.")

    monkeypatch.setattr(rules, "warm_up", down)
    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"), default_timeout=30)
    at.run()
    assert [e.value for e in at.error] == ["Ollama is not running. Start it, then reload."]


def test_an_example_question_button_asks_it(app):
    app.button(key="example_0").click().run()
    shown = texts(app)
    assert "What do I get when I pass Start?" in shown and "Sources: §4.7" in shown
