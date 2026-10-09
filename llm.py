"""The only module that talks to Ollama (SPEC.md §3)."""

import os
from collections.abc import Callable
from typing import TypeVar

import httpx
import ollama
from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:4b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "")
THINKING_MODEL_PREFIXES = ("qwen3",)  # only these accept think=False

T = TypeVar("T")


class LLMError(Exception):
    """A plain-language problem to show the user."""


def _call(model: str, request: Callable[[ollama.Client], T]) -> T:
    client = ollama.Client(host=OLLAMA_HOST or None)
    try:
        return request(client)
    except (ConnectionError, httpx.TransportError) as e:
        raise LLMError("Ollama is not running. Start it, then reload.") from e
    except ollama.ResponseError as e:
        if e.status_code == 404:
            raise LLMError(f"Model `{model}` is missing. Run `ollama pull {model}`.") from e
        raise LLMError(f"Ollama error: {e.error}") from e


def complete(system: str, messages: list[dict[str, str]], **options: float) -> str:
    extra = {"think": False} if LLM_MODEL.startswith(THINKING_MODEL_PREFIXES) else {}
    response = _call(
        LLM_MODEL,
        lambda c: c.chat(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": system}, *messages],
            options=options,
            **extra,
        ),
    )
    return response.message.content or ""


def embed(texts: list[str]) -> list[list[float]]:
    response = _call(EMBED_MODEL, lambda c: c.embed(model=EMBED_MODEL, input=texts))
    return [list(v) for v in response.embeddings]
