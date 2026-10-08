from pathlib import Path

import numpy as np

import rag

SPEC_TEXT = Path("knowledge/SPEC-v1.0-PokeMonopoly.md").read_text(encoding="utf-8")


def chunks_with(snippet: str) -> list[dict[str, str]]:
    return [c for c in rag.chunk(SPEC_TEXT) if snippet in c["text"]]


def test_appendix_a_items_table_is_its_own_section():
    [items] = chunks_with("| Ultra Ball | 3 | +2 |")
    assert items["section"] == "Appendix A — Items"
    assert "Dratini" not in items["text"]


def test_section_labels_follow_numbered_headings():
    assert {c["section"] for c in chunks_with("Ties go to badges")} == {"§4.7"}
    assert {c["section"] for c in chunks_with("The deck is shuffled at setup")} == {"§4.6"}
    assert {c["section"] for c in chunks_with("Delivery scope")} == {"§1"}
    assert {c["section"] for c in chunks_with("No Ball")} >= {"§3.1"}


FRUIT_DOC = "## 1. Apples\n\napple apple red\n\n## 2. Pears\n\npear green\n\n## 3. Plums\n\nplum purple\n"


class WordCountEmbed:
    """Fake embedder: one dimension per word in a small vocabulary; counts its calls."""

    VOCAB = ("apple", "pear", "plum", "red", "green", "purple")

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[t.lower().count(w) + 0.01 for w in self.VOCAB] for t in texts]


def test_retrieve_ranks_the_matching_section_first(tmp_path):
    embed = WordCountEmbed()
    index = rag.build_index(FRUIT_DOC, embed=embed, cache_path=tmp_path / "index.npz")
    results = rag.retrieve("which one is green?", k=2, index=index, embed=embed)
    assert [c["section"] for c, _ in results][0] == "§2"
    assert len(results) == 2
    assert results[0][1] > results[1][1]


def test_one_matching_bullet_lifts_its_whole_chunk(tmp_path):
    doc = "## 1. Mixed\n\n- apple apple apple red red\n- pear\n\n## 2. Greens\n\ngreen pear apple red\n"
    embed = WordCountEmbed()
    index = rag.build_index(doc, embed=embed, cache_path=tmp_path / "index.npz")
    [(best, _)] = rag.retrieve("pear", k=1, index=index, embed=embed)
    assert best["section"] == "§1"
    assert "apple apple apple" in best["text"]  # the whole chunk goes to the LLM, not the bullet


def test_retrieve_returns_distinct_chunks(tmp_path):
    embed = WordCountEmbed()
    index = rag.build_index(FRUIT_DOC, embed=embed, cache_path=tmp_path / "index.npz")
    sections = [c["section"] for c, _ in rag.retrieve("apple", k=3, index=index, embed=embed)]
    assert sorted(sections) == ["§1", "§2", "§3"]


def test_index_is_cached_until_the_knowledge_changes(tmp_path):
    embed = WordCountEmbed()
    cache = tmp_path / "index.npz"
    rag.build_index(FRUIT_DOC, embed=embed, cache_path=cache)
    rag.build_index(FRUIT_DOC, embed=embed, cache_path=cache)
    assert embed.calls == 1
    rag.build_index(FRUIT_DOC + "\n## 4. Figs\n\nfig\n", embed=embed, cache_path=cache)
    assert embed.calls == 2


def test_cache_in_an_older_format_is_rebuilt(tmp_path):
    cache = tmp_path / "index.npz"
    np.savez(cache, vectors=np.zeros((1, 6)))  # e.g. written by an earlier version
    embed = WordCountEmbed()
    index = rag.build_index(FRUIT_DOC, embed=embed, cache_path=cache)
    assert embed.calls == 1
    assert rag.retrieve("pear", k=1, index=index, embed=embed)[0][0]["section"] == "§2"


def test_corrupt_cache_is_rebuilt(tmp_path):
    cache = tmp_path / "index.npz"
    cache.write_bytes(b"not a zip file")
    embed = WordCountEmbed()
    rag.build_index(FRUIT_DOC, embed=embed, cache_path=cache)
    assert embed.calls == 1


def test_zero_vectors_never_score_nan(tmp_path):
    def zeros(texts: list[str]) -> list[list[float]]:
        return [[0.0, 0.0] for _ in texts]

    index = rag.build_index(FRUIT_DOC, embed=zeros, cache_path=tmp_path / "index.npz")
    scores = [s for _, s in rag.retrieve("pear", k=3, index=index, embed=zeros)]
    assert all(np.isfinite(scores))


def test_long_section_is_split_but_tables_stay_whole():
    promises = [c for c in rag.chunk(SPEC_TEXT) if c["section"] == "§4.8"]
    assert len(promises) >= 2
    assert all(len(c["text"]) / 4 <= 500 for c in promises)  # ~4 chars per token
    [trust] = [c for c in promises if "| Broken" in c["text"]]
    assert "closed_by_game_end" in trust["text"]
