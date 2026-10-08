import os

import httpx
import ollama
import pytest
from dotenv import load_dotenv

load_dotenv()


def _ollama_up() -> bool:
    # Probe with the ollama client so host parsing (default port, scheme) matches llm.py.
    try:
        ollama.Client(host=os.environ.get("OLLAMA_HOST") or None, timeout=2).list()
        return True
    except (ConnectionError, httpx.HTTPError, ollama.ResponseError):
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    live = [item for item in items if "live" in item.keywords]
    if not live or _ollama_up():
        return
    skip = pytest.mark.skip(reason="Ollama is not reachable")
    for item in live:
        item.add_marker(skip)
