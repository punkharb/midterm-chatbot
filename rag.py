"""Load, chunk, embed and retrieve the game spec (SPEC.md §4)."""

import hashlib
import re
import zipfile
from collections.abc import Callable
from functools import cache
from pathlib import Path

import numpy as np

import llm

ROOT = Path(__file__).parent
KNOWLEDGE_PATH = ROOT / "knowledge/SPEC-v1.0-PokeMonopoly.md"
CACHE_PATH = ROOT / ".cache/index.npz"

MAX_TOKENS = 500
OVERLAP_TOKENS = 60
APPENDIX_A_SUBHEADINGS = ("Board", "Classes", "Pokémon and Abilities", "Evolution", "Items")

_HEADING = re.compile(r"^(##|###) (.+)$")
_BOLD_SUBHEADING = re.compile(r"^\*\*(.+)\*\*$")


def _section_label(heading: str, parent: str) -> str:
    """'4.7 Selling…' → '§4.7', '3. User flow…' → '§3', 'Appendix A — …' → 'Appendix A'.
    Unnumbered headings ('Delivery scope') keep their parent's label."""
    if m := re.match(r"(\d+(?:\.\d+)?)\.?\s", heading):
        return "§" + m.group(1)
    if m := re.match(r"(Appendix [A-Z])\b", heading):
        return m.group(1)
    return parent


def _sections(text: str) -> list[tuple[str, str, list[str]]]:
    """Split into (section, heading, body lines) on ##/### and Appendix A bold subheadings."""
    sections: list[tuple[str, str, list[str]]] = [("Intro", "Introduction", [])]
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        section, heading, body = sections[-1]
        m = None if in_fence else _HEADING.match(line)
        if m:
            heading = m.group(2).strip()
            parent = section.split(" — ")[0]
            sections.append((_section_label(heading, parent), heading, []))
            continue
        bold = None if in_fence else _BOLD_SUBHEADING.match(line.strip())
        if bold and section.startswith("Appendix A") and bold.group(1) in APPENDIX_A_SUBHEADINGS:
            sub = bold.group(1)
            sections.append((f"Appendix A — {sub}", sub, []))
            continue
        body.append(line)
    return sections


def _blocks(lines: list[str]) -> list[str]:
    """Paragraphs split on blank lines; a table or code fence is always one block."""
    blocks, current, in_fence = [], [], False
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if current:
                blocks.append("\n".join(current))
            current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _pack(heading: str, blocks: list[str]) -> list[str]:
    """Group blocks into parts of at most MAX_TOKENS; repeat a short last block as overlap.
    A single block over the limit (a big table) stays whole."""
    parts: list[list[str]] = [[]]
    for block in blocks:
        current = parts[-1]
        if current and _tokens("\n\n".join([heading, *current, block])) > MAX_TOKENS:
            overlap = [current[-1]] if _tokens(current[-1]) <= OVERLAP_TOKENS else []
            if _tokens("\n\n".join([heading, *overlap, block])) > MAX_TOKENS:
                overlap = []
            parts.append(overlap)
            current = parts[-1]
        current.append(block)
    return ["\n\n".join([heading, *part]) for part in parts if part]


def _tokens(text: str) -> float:
    return len(text) / 4  # ponytail: ~4 chars per token; swap in a tokenizer if limits matter


def chunk(text: str) -> list[dict[str, str]]:
    """Chunks with `section` (the citation label), `heading` and `text` (heading + body)."""
    return [
        {"section": section, "heading": heading, "text": part}
        for section, heading, body in _sections(text)
        for part in _pack(heading, _blocks(body))
    ]


Chunk = dict[str, str]
Index = tuple[list[Chunk], np.ndarray, np.ndarray]  # chunks, unit vectors, owning chunk per unit
Embed = Callable[[list[str]], list[list[float]]]

EMBED_BATCH = 32  # one call with ~400 texts crashed the Ollama runner
_LIST_ITEM = re.compile(r"^(\d+\.|-) ")


def units(c: Chunk) -> list[str]:
    """Small retrieval units of a chunk: table rows (with the header row), top-level
    list items (with their sub-items) and paragraphs, each prefixed with the heading.
    A chunk is scored by its best unit, but the whole chunk is what the LLM sees."""
    out = []
    for block in _blocks(c["text"].splitlines()[1:]):
        lines = block.splitlines()
        if lines[0].startswith("|") and len(lines) > 2:
            out += [f"{lines[0]}\n{row}" for row in lines[2:]]
        elif _LIST_ITEM.match(lines[0]):
            items: list[list[str]] = []
            for line in lines:
                if _LIST_ITEM.match(line) or not items:
                    items.append([])
                items[-1].append(line)
            out += ["\n".join(item) for item in items]
        else:
            out.append(block)
    return [f"{c['heading']}\n{u}" for u in out] or [c["text"]]


def _unit_rows(vectors: list[list[float]]) -> np.ndarray:
    m = np.asarray(vectors, dtype=np.float32)
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)  # zero vector → 0, not NaN


def _load_cache(cache_path: Path, key: str) -> np.ndarray | None:
    """Cached unit vectors for `key`, or None if missing, stale, old-format or corrupt."""
    try:
        with np.load(cache_path) as cached:
            if {"key", "vectors"} <= set(cached.files) and str(cached["key"]) == key:
                return cached["vectors"]
    except (OSError, ValueError, zipfile.BadZipFile):
        pass  # rebuild below
    return None


def build_index(text: str, embed: Embed = llm.embed, cache_path: Path = CACHE_PATH) -> Index:
    """Chunk and embed `text`; reuse cached vectors while the model and the exact unit texts match."""
    chunks = chunk(text)
    texts, owner = [], []
    for i, c in enumerate(chunks):
        for u in units(c):
            texts.append(u)
            owner.append(i)
    key = hashlib.sha256(
        "\0".join([llm.EMBED_MODEL, str(owner), *texts]).encode()
    ).hexdigest()
    if (vectors := _load_cache(cache_path, key)) is not None:
        return chunks, vectors, np.array(owner)
    vectors = _unit_rows(
        [v for i in range(0, len(texts), EMBED_BATCH) for v in embed(texts[i : i + EMBED_BATCH])]
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache_path, key=np.array(key), vectors=vectors, owner=np.array(owner))
    return chunks, vectors, np.array(owner)


@cache
def _default_index() -> Index:
    return build_index(KNOWLEDGE_PATH.read_text(encoding="utf-8"))


def retrieve(
    question: str, k: int = 4, index: Index | None = None, embed: Embed = llm.embed
) -> list[tuple[Chunk, float]]:
    """Top-k distinct chunks, best first, each scored by the cosine similarity of its best unit."""
    chunks, vectors, owner = index if index is not None else _default_index()
    unit_scores = vectors @ _unit_rows(embed([question]))[0]
    scores = np.full(len(chunks), -np.inf)
    np.maximum.at(scores, owner, unit_scores)
    best = np.argsort(scores)[::-1][:k]
    return [(chunks[i], float(scores[i])) for i in best]
