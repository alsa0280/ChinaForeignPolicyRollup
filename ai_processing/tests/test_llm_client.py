"""Tests for llm_client.py. The HTTP transport is replaced, so Ollama is never called."""
import json

import httpx
import pytest

from ai_processing.config import Settings
from ai_processing.llm_client import LLMError, OllamaClient


def client_returning(handler) -> OllamaClient:
    return OllamaClient(Settings(), transport=httpx.MockTransport(handler))


def ollama_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})


def test_sends_structured_request_and_returns_answer():
    sent = {}

    def handler(request):
        sent.update(json.loads(request.content))
        return ollama_reply('{"language": "en"}')

    answer = client_returning(handler).generate_json("system", {"article": "x"}, {"type": "object"})

    assert answer == {"language": "en"}
    assert sent["model"] == "qwen2.5:7b"
    assert sent["stream"] is False
    assert sent["format"] == {"type": "object"}
    assert [m["role"] for m in sent["messages"]] == ["system", "user"]


@pytest.mark.parametrize("content", ["not json", "[1, 2]"])
def test_unusable_answer_raises(content):
    with pytest.raises(LLMError):
        client_returning(lambda request: ollama_reply(content)).generate_json("s", {}, {})


def test_server_error_raises():
    with pytest.raises(LLMError):
        client_returning(lambda request: httpx.Response(500)).generate_json("s", {}, {})


def test_embed_returns_one_vector_per_text():
    def handler(request):
        assert json.loads(request.content)["model"] == "bge-m3"
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    assert client_returning(handler).embed(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]
