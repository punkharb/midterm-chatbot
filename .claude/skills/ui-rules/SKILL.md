---
name: ui-rules
description: UI house rules for the Streamlit app (Rules Guide and Opponent Preview tabs). Use before building or changing any screen, message, button or banner in app.py.
---

# UI rules

Adapted from the game team's `ui-rules` skill (game spec §3.1). The fixed texts (headers, banner, refusals, disclaimer) are defined in `SPEC.md` §6–§7; use them word for word.

## House rules

- **No blank screens.** There is always a message: a welcome line with example questions before the first chat, a spinner while the model answers, and a plain error when something fails.
- **Say what to change.** Errors tell the user the fix: "Ollama is not running. Start it, then reload." / "Model `X` is missing. Run `ollama pull X`." / "Keep messages under 280 characters (yours: 312)."
- **An unusable control is disabled and says why**, e.g. the Preview input after 6 messages: "Preview limit reached. Try it in the full game."
- **Plain tone, no jokes** in the app's own text. Personas may have character; the app frame does not.
- **Every rule number comes from the knowledge file**, shown with its citation. The UI never computes or rewrites numbers.
- **Always show who is talking:** the tab header ("Rules Guide — answers from the official rules" / "Opponent Preview — in-character demo, not rules") stays visible.
- **Disclaimer footer on every page.**
- Thai and English both work; keep game terms (Ball, Sell Phase, Lap) in English.

## Streamlit notes

- Keep chat history in `st.session_state` only; never write it to disk (`SPEC.md` §7.3 privacy).
- Changing persona or scenario clears that chat and its message count.
- Cache the loaded index with `st.cache_resource` so embeddings are not rebuilt on every rerun.
