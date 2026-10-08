import pytest

import llm


def test_unreachable_ollama_gives_plain_error(monkeypatch):
    monkeypatch.setattr(llm, "OLLAMA_HOST", "http://127.0.0.1:9")
    with pytest.raises(llm.LLMError, match=r"^Ollama is not running\. Start it, then reload\.$"):
        llm.complete("system", [{"role": "user", "content": "hi"}])
    with pytest.raises(llm.LLMError, match=r"^Ollama is not running\. Start it, then reload\.$"):
        llm.embed(["hi"])


@pytest.mark.live
def test_missing_model_tells_user_to_pull_it(monkeypatch):
    monkeypatch.setattr(llm, "LLM_MODEL", "no-such-model:1b")
    with pytest.raises(llm.LLMError, match=r"^Model `no-such-model:1b` is missing\. Run `ollama pull no-such-model:1b`\.$"):
        llm.complete("system", [{"role": "user", "content": "hi"}])


@pytest.mark.live
def test_complete_and_embed_talk_to_ollama():
    reply = llm.complete("Reply with one word.", [{"role": "user", "content": "Say ok"}], temperature=0)
    assert reply.strip()
    vectors = llm.embed(["ลูกเต๋า", "dice"])
    assert len(vectors) == 2 and len(vectors[0]) == len(vectors[1]) > 0
