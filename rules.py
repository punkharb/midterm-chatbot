"""Rules Guide: answer a rules question from the game spec (SPEC.md §5)."""

import re
from collections.abc import Callable

import guard
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


_NUMBER = guard.NUMBER  # "d6", "C1" are names, not numbers


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
        entities = guard.entity_names(claim)
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
    """The Rules Guide pipeline (SPEC.md §5, §7): returns the text to show and its sources."""
    if problem := guard.check_input(question):
        return problem, []
    if guard.is_injection(question, complete=complete):
        return guard.RULES_REFUSAL, []
    if hidden := guard.hidden_info_answer(question):
        return hidden
    retrieved = retrieve(question, k=TOP_K)
    if not retrieved or retrieved[0][1] < guard.SCOPE_THRESHOLD:
        return guard.OUT_OF_SCOPE, []
    chunks = [c for c, _ in retrieved]
    system = prompts.rules_system(chunks)
    messages = [{"role": "user", "content": question + (prompts.THAI_REMINDER if _THAI.search(question) else "")}]
    # The retry is a fresh call with a stricter system prompt: as a chat follow-up
    # ("your answer was wrong"), gemma3:4b apologised and dumped unrelated cited text.
    cited: list[str] = []
    for system in (system, system + prompts.STRICTER_REMINDER):
        answer = complete(system, messages, temperature=0)
        if answer.strip().rstrip(".").strip() == "OUT_OF_SCOPE":
            return guard.OUT_OF_SCOPE, []
        answer = repair_citations(answer, chunks)
        sources = cited_sections(answer, chunks)
        if sources and guard.check_numbers(answer, question, chunks):
            return answer, sources
        cited = sources or cited
    if not cited:  # neither attempt cited the rules: they do not cover this question
        return guard.OUT_OF_SCOPE, []
    return guard.UNRELIABLE, cited


def warm_up() -> None:
    """Load the rule index and the chat model before the first question, so the first
    answer does not also pay for loading (about 7 s for gemma3:4b on the dev machine)."""
    rag.retrieve("warm up", k=1)
    llm.complete("Reply with one word.", [{"role": "user", "content": "ok"}], temperature=0)
