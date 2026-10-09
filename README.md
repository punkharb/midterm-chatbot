# Poke Monopoly Rules Guide

An offline RAG chatbot that answers questions about the rules of **Poke Monopoly**, our class project: a single-player web board game played against AI opponents. Built for the course midterm.

> Status: built (SPEC.md §10 steps 0–6). Measured results and known gaps are in [SPEC.md](SPEC.md) §5–§7 and [`evidence/`](evidence/).

## What it does

| Part | What you can do |
| --- | --- |
| **Rules Guide** | Ask about catching, selling at Start, battles, items, classes and edge cases, in Thai or English. Every answer cites the rule section it comes from, e.g. `[§4.7]`. |
| **Opponent Preview** | Chat briefly with one of the game's four AI opponent personalities (Aggressive, Cautious, Greedy, Opportunist) in a prepared scenario. It is a taste of the game's social play: nothing said there changes any game. |

## Guardrails (always on)

1. Every number in a rule answer must appear in the retrieved rule text, in the row that names what was asked about, with a citation. An answer that fails is regenerated once; if it fails again, the bot says it can't answer reliably and shows the sections.
2. Hidden game information (secret items, event deck order) is never placed in any prompt, so it cannot leak. The plainest questions about it ("What's the next event card?") get a fixed answer that cites the rule making it hidden.
3. Prompt-injection attempts are screened by two yes/no checks before they reach the main prompt. The opponent refuses in character.
4. Deals and promises in the preview are labelled "Chat only, not a contract".
5. Each tab says whether you are talking to the rules guide or to a character.
6. Off-topic questions are declined. Messages are limited to 280 characters.

There is one fixed mode, not AgeWell's three: players need correct rules, and an open mode would mix the game's custom values with real Pokémon facts. See [SPEC.md](SPEC.md) §2.1 and §7.

## How it works

```text
question ─► input guard ─► bge-m3 embedding ─► top-4 rule chunks ─► local LLM ─► output guard ─► answer + sources
            (length,         (small units:       (NumPy cosine,       (gemma3:4b)     (citation repair,
             injection,       rows, items,        score threshold)                     numbers grounded,
             hidden info)     paragraphs)                                              citation present)
```

Everything runs locally through [Ollama](https://ollama.com): no API key and no internet at run time.

| Component | Choice |
| --- | --- |
| UI | Streamlit |
| Chat model | `gemma3:4b` (good Thai, runs on a 4 GB GPU); compared against `qwen2.5:3b`, recorded in `evidence/model-bakeoff.md` |
| Embeddings | `bge-m3` (multilingual, so Thai questions match the English rules) |
| Search | In-memory NumPy cosine similarity |
| Knowledge | `knowledge/SPEC-v1.0-PokeMonopoly.md`, the game specification |

## Results and limits

These numbers were measured on a 4 GB GTX 1650 with `gemma3:4b`; the details are in SPEC.md.

- **SPEC §8 test cases:** 16/16 passed in the bake-off run. An independent re-run passed 15/16, failing on a brittle keyword check ([evidence/model-bakeoff.md](evidence/model-bakeoff.md)).
- **Blind test:** 145 questions, written by a separate agent that never saw the code ([evidence/blind-eval/](evidence/blind-eval/)):
  - 38 of 40 ordinary rules questions were answered;
  - 24 of 30 manipulation attempts were stopped, but 4 got the bot to state something false (e.g. "Ultra Balls are free now");
  - 6 of 25 hidden-information questions got made-up deck contents;
  - 13 of 20 off-topic requests were declined.
- **Known gaps:** the number check works per table row, not per column. Numbers the user types always count as grounded. The Preview's fake-transfer and banner checks are keyword-based. See SPEC §5, §6 and §7.

## Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com/download) running locally
- About 5 GB of disk space for the models; a GPU with 4 GB or more is recommended (CPU-only works but answers take 5–20 s)

## Setup

```bash
git clone <this repository>
cd midterm-chatbot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
ollama pull gemma3:4b
ollama pull bge-m3
```

On macOS or Linux, use `source .venv/bin/activate` and `cp .env.example .env`.

## Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501). The game fonts (Lilita One, Nunito, IBM Plex Sans Thai Looped) load from Google Fonts when online. Offline, the app falls back to system fonts and works the same.

Answers take roughly 5–20 s on a 4 GB GPU, longer on CPU only.

## Test

```bash
pytest -m "not live"
pytest -m live
```

Model bake-off only: `ollama pull qwen2.5:3b`.

The first command runs fast tests without Ollama: guardrails, chunking, citation handling, the Preview logic, and the Streamlit app through Streamlit's AppTest with fake models. The second runs the end-to-end cases from SPEC.md §8 against the local models, including Thai questions, hidden-information probes and prompt-injection attempts, plus retrieval and classifier checks. Live answers vary a little between runs (SPEC §6).

To repeat the blind test: `python evidence/blind-eval/run_blind_eval.py`. The step 3 runs took 2058–2130 s on the dev machine. The script overwrites `evidence/blind-eval/results.json`, so copy that file first to keep the committed results.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_MODEL` | `gemma3:4b` | Ollama chat model |
| `EMBED_MODEL` | `bge-m3` | Ollama embedding model |
| `MODE` | `strict` | Answer mode; only `strict` is implemented |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server |

## Project files

| Path | Purpose |
| --- | --- |
| `SPEC.md` | Full specification: scope, behaviour, guardrails, tests, build order |
| `AGENTS.md`, `CLAUDE.md`, `.claude/skills/` | Rules and skills for AI coding agents working on this repository |
| `app.py`, `style.css`, `.streamlit/config.toml` | Streamlit UI (two tabs) and its game look |
| `rules.py`, `preview.py` | The Rules Guide and Opponent Preview pipelines |
| `guard.py`, `prompts.py` | Guardrails and system prompts |
| `rag.py`, `llm.py` | Retrieval, and the only module that talks to Ollama |
| `knowledge/` | The game rules the chatbot answers from |
| `personas/`, `scenarios/` | Opponent Preview content |
| `evidence/` | Screenshots, the model bake-off and the blind test, for submission |

## Disclaimer

Coursework prototype. Not affiliated with Nintendo, The Pokémon Company or Hasbro. Pokémon-inspired names are design references only.
