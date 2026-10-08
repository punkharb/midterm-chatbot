"""Rules Guide: answer a rules question from the game spec (SPEC.md §5)."""

import re
from collections.abc import Callable

import llm
import prompts
import rag

TOP_K = 4
_THAI = re.compile(r"[\u0e00-\u0e7f]")
_BRACKET = re.compile(r"\[([^\]]+)\]")
_CITATION = re.compile(r"§\d+(?:\.\d+)?|Appendix [A-Z]")


def _matches(cite: str, tail: str, chunks: list[rag.Chunk]) -> list[str]:
    """Sections a single citation refers to. [§4.7] matches '§4.7' (and [§4] matches '§4.7');
    [Appendix A — Items] matches the subsection named in its tail, whatever dash the model
    used, and falls back to every retrieved Appendix A chunk when no subsection is named."""
    if cite.startswith("§"):
        return [c["section"] for c in chunks if c["section"] == cite or c["section"].startswith(cite + ".")]
    appendix = [c["section"] for c in chunks if c["section"] == cite or c["section"].startswith(cite + " — ")]
    named = [s for s in appendix if " — " in s and s.split(" — ", 1)[1].lower() in tail.lower()]
    return named or appendix


def cited_sections(answer: str, chunks: list[rag.Chunk]) -> list[str]:
    """Sections of `chunks` cited in `answer`, in citation order, without duplicates."""
    sources: list[str] = []
    for bracket in _BRACKET.findall(answer):
        cites = list(_CITATION.finditer(bracket))
        for i, m in enumerate(cites):
            end = cites[i + 1].start() if i + 1 < len(cites) else len(bracket)
            for s in _matches(m.group(), bracket[m.end() : end], chunks):
                if s not in sources:
                    sources.append(s)
    return sources


def answer_rules(
    question: str,
    complete: Callable[..., str] = llm.complete,
    retrieve: Callable[..., list[tuple[rag.Chunk, float]]] = rag.retrieve,
) -> tuple[str, list[str]]:
    """Answer from the top retrieved chunks; return the answer and the cited sections."""
    chunks = [c for c, _ in retrieve(question, k=TOP_K)]
    content = question + (prompts.THAI_REMINDER if _THAI.search(question) else "")
    answer = complete(
        prompts.rules_system(chunks), [{"role": "user", "content": content}], temperature=0
    )
    return answer, cited_sections(answer, chunks)
