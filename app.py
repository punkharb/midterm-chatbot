"""Poke Monopoly Rules Guide: Streamlit UI (SPEC.md §2, §5–§7; ui-rules skill).
Chat history lives only in st.session_state; nothing is written to disk."""

import streamlit as st

import guard
import llm
import preview
import rules

RULES_HEADER = "Rules Guide — answers from the official rules"
PREVIEW_HEADER = "Opponent Preview — in-character demo, not rules"
DISCLAIMER = "Coursework prototype. Not affiliated with Nintendo, The Pokémon Company or Hasbro."
FULL_GAME = "Want to see if they remember your promise? Try it in the full game."
LIMIT_REACHED = "Preview limit reached. Try it in the full game."
EXAMPLES = (
    "What do I get when I pass Start?",
    "How much does an Ultra Ball cost and what bonus?",
    "ถ้าไม่มีบอลแต่เจอโปเกมอนทำไงได้บ้าง",
)

st.set_page_config(page_title="Poke Monopoly Rules Guide")
state = st.session_state
state.setdefault("rules_chat", [])  # {"role", "text", "sources"?}
state.setdefault("preview_chat", [])  # {"role", "text", "banner"?}
state.setdefault("preview_ended", False)


def queue(key: str) -> None:
    state[key + "_pending"] = state[key]


def show(turn: dict) -> None:
    with st.chat_message(turn["role"]):
        st.markdown(turn["text"])
        if turn.get("sources"):
            st.caption("Sources: " + ", ".join(turn["sources"]))
        if turn.get("banner"):
            st.info(guard.BANNER)


def reset_preview() -> None:
    state.preview_chat, state.preview_ended = [], False


rules_tab, preview_tab = st.tabs(["Rules Guide", "Opponent Preview"])

with rules_tab:
    st.caption(RULES_HEADER)
    question = state.pop("rules_input_pending", None)
    if not state.rules_chat and not question:
        st.markdown("Ask anything about the Poke Monopoly rules. For example:")
        st.markdown("\n".join(f"- {q}" for q in EXAMPLES))
    for turn in state.rules_chat:
        show(turn)
    if question:  # shown at once, answered under a spinner (ui-rules: no blank screens)
        show(user := {"role": "user", "text": question})
        try:
            with st.spinner("Looking it up in the rules…"):
                answer, sources = rules.answer_rules(question)
            state.rules_chat += [user, {"role": "assistant", "text": answer, "sources": sources}]
            show(state.rules_chat[-1])
        except llm.LLMError as e:
            st.error(str(e))
    st.chat_input("Ask about the rules", key="rules_input", on_submit=queue, args=("rules_input",))

with preview_tab:
    st.caption(PREVIEW_HEADER)
    persona = st.selectbox("Personality", sorted(preview.PERSONAS), key="persona", on_change=reset_preview)
    titles = [s["title"] for s in preview.SCENARIOS]
    title = st.selectbox("Scenario", titles, key="scenario", on_change=reset_preview)
    scenario = preview.SCENARIOS[titles.index(title)]
    st.markdown(f"**Situation:** {scenario['public_state']}  \n**They remember:** {scenario['memory']}")

    message = state.pop("preview_input_pending", None)
    for turn in state.preview_chat:
        show(turn)
    count = sum(t["role"] == "user" for t in state.preview_chat)
    if message and count < preview.LIMIT and not state.preview_ended:
        if problem := guard.check_input(message):
            st.warning(problem)
        else:
            history = [{"role": t["role"], "content": t["text"]} for t in state.preview_chat]
            show(user := {"role": "user", "text": message})
            try:
                with st.spinner("Your opponent is thinking…"):
                    reply, banner = preview.preview_reply(persona, scenario, history, message)
                state.preview_chat += [user, {"role": "assistant", "text": reply, "banner": banner}]
                show(state.preview_chat[-1])
            except llm.LLMError as e:
                st.error(str(e))
    # controls are drawn after the message is handled, so they reflect the new count
    count = sum(t["role"] == "user" for t in state.preview_chat)
    done = state.preview_ended or count >= preview.LIMIT
    for i, opener in enumerate(scenario["suggested_openers"]):
        st.button(opener, key=f"opener_{i}", disabled=done, on_click=state.update,
                  kwargs={"preview_input_pending": opener})
    st.button("End preview", key="end_preview", disabled=done, on_click=state.update,
              kwargs={"preview_ended": True})
    if done:
        st.info(FULL_GAME)
        st.caption(LIMIT_REACHED if count >= preview.LIMIT else "Preview ended.")
    else:
        st.caption(f"{count} of {preview.LIMIT} preview messages used")
    st.chat_input(
        LIMIT_REACHED if done else "Say something to your opponent",
        key="preview_input",
        disabled=done,
        on_submit=queue,
        args=("preview_input",),
    )

st.divider()
st.caption(DISCLAIMER)
