# Poke Monopoly Rules Guide

An offline RAG chatbot that answers questions about the rules of **Poke Monopoly**, our class project: a single-player web board game played against AI opponents. Built for the course midterm.

> Status: planning complete, implementation in progress. See [SPEC.md](SPEC.md) §10 for the build order.

## What it does

| Part | What you can do |
| --- | --- |
| **Rules Guide** | Ask about catching, selling at Start, battles, items, classes and edge cases, in Thai or English. Every answer cites the rule section it comes from, e.g. `[§4.7]`. |
| **Opponent Preview** | Chat briefly with one of the game's four AI opponent personalities (Aggressive, Cautious, Greedy, Opportunist) in a prepared scenario. It is a taste of the game's social play: nothing said there changes any game. |

## Guardrails (always on)

1. Every number in a rule answer must appear in the retrieved rule text, with a citation. Answers that fail the check are regenerated once, then withheld.
2. Hidden game information (secret items, event deck order) is never placed in any prompt, so it cannot leak.
3. Prompt-injection attempts are screened before they reach the main prompt. The opponent refuses in character.
4. Deals and promises in the preview are labelled "Chat only, not a contract".
5. Each tab says whether you are talking to the rules guide or to a character.
6. Off-topic questions are declined. Messages are limited to 280 characters.

There is one fixed mode, not AgeWell's three: players need correct rules, and an open mode would mix the game's custom values with real Pokémon facts. See [SPEC.md](SPEC.md) §2.1 and §7.

## How it works

```text
question ─► input guard ─► bge-m3 embedding ─► top-4 rule chunks ─► local LLM ─► output guard ─► answer + sources
            (length,                            (NumPy cosine,       (Typhoon 2.1    (numbers grounded,
             injection)                          score threshold)     Gemma3 4B)      citation present)
```

Everything runs locally through [Ollama](https://ollama.com): no API key and no internet at run time.

| Component | Choice |
| --- | --- |
| UI | Streamlit |
| Chat model | `scb10x/typhoon2.1-gemma3-4b` (Thai-tuned, fits a 4 GB GPU); chosen by a bake-off against `qwen3:4b`, recorded in `evidence/model-bakeoff.md` |
| Embeddings | `bge-m3` (multilingual, so Thai questions match the English rules) |
| Search | In-memory NumPy cosine similarity |
| Knowledge | `knowledge/SPEC-v1.0-PokeMonopoly.md`, the game specification |

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
ollama pull scb10x/typhoon2.1-gemma3-4b
ollama pull bge-m3
```

On macOS or Linux, use `source .venv/bin/activate` and `cp .env.example .env`.

## Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

On a slow machine, set `LLM_MODEL=qwen2.5:3b` in `.env` for a smaller model.

## Test

```bash
pytest -m "not live"
pytest -m live
```

Model bake-off only: `ollama pull qwen3:4b`.

The first command runs fast unit tests of the guardrails without Ollama. The second runs the 16 end-to-end cases from SPEC.md §8, including Thai questions, hidden-information probes and prompt-injection attempts, against the local models.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_MODEL` | `scb10x/typhoon2.1-gemma3-4b` | Ollama chat model |
| `EMBED_MODEL` | `bge-m3` | Ollama embedding model |
| `MODE` | `strict` | Answer mode; only `strict` is implemented |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server |

## Project files

| Path | Purpose |
| --- | --- |
| `SPEC.md` | Full specification: scope, behaviour, guardrails, tests, build order |
| `AGENTS.md`, `CLAUDE.md` | Rules for AI coding agents working on this repository |
| `knowledge/` | The game rules the chatbot answers from |
| `personas/`, `scenarios/` | Opponent Preview content |
| `evidence/` | Screenshots and the model bake-off for submission |

## Disclaimer

Coursework prototype. Not affiliated with Nintendo, The Pokémon Company or Hasbro. Pokémon-inspired names are design references only.
