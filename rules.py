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


_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_ENTITY = re.compile(r"\b[A-Z][a-zé]{2,}")  # capitalised names such as Dratini, Ultra, Ball
_NOT_ENTITIES = {"The", "You", "Your", "When", "If", "This", "That", "They", "There", "Each", "Every"}


def _supports(chunk: rag.Chunk, numbers: list[str], entities: set[str]) -> bool:
    """Some line of the chunk (a table row or a sentence's line) holds every number
    and every entity name of the claim."""
    for line in chunk["text"].lower().splitlines():
        found = set(_NUMBER.findall(line))
        if all(n in found for n in numbers) and all(e in line for e in entities):
            return True
    return False


def repair_citations(answer: str, chunks: list[rag.Chunk]) -> str:
    """Re-point a citation whose block does not hold the numbers of the claim before it to
    the first retrieved block that does. gemma3:4b often cites a block that only explains
    the topic (e.g. §4.7 for a value in an Appendix A table row). Claims whose numbers are
    in no block are left alone for the grounding check."""
    out, last = [], 0
    for m in _BRACKET.finditer(answer):
        claim = _BRACKET.sub("", answer[last : m.start()])
        numbers = _NUMBER.findall(claim)
        cited = set(cited_sections(m.group(), chunks))
        replacement = m.group()
        entities = {w.lower() for w in _ENTITY.findall(claim) if w not in _NOT_ENTITIES}
        if numbers and cited and entities:  # no named entity (e.g. a Thai claim): never re-point
            # keep the citation if its block holds every number anywhere (facts may span lines)
            held = {n for c in chunks if c["section"] in cited for n in _NUMBER.findall(c["text"])}
            if not all(n in held for n in numbers):
                better = next((c for c in chunks if _supports(c, numbers, entities)), None)
                if better:
                    replacement = f"[{better['section']}]"
        out.append(answer[last : m.start()] + replacement)
        last = m.end()
    return "".join(out) + answer[last:]


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
    answer = repair_citations(answer, chunks)
    return answer, cited_sections(answer, chunks)
