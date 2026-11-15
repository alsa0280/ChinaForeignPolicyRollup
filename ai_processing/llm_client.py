"""Client for the local Ollama server (POST /api/chat, structured JSON output).

No API key is used. Tests replace the HTTP transport, so no test calls Ollama.
"""

import json

import httpx

from ai_processing.config import Settings

TEMPERATURE = 0.1


class LLMError(Exception):
    """The model could not be reached or did not return a usable JSON object."""


class OllamaClient:
    def __init__(
        self, settings: Settings, transport: httpx.BaseTransport | None = None
    ):
        self.settings = settings
        self._http = httpx.Client(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_s,
            transport=transport,
        )

    def generate_json(self, system_prompt: str, payload: dict, schema: dict) -> dict:
        """Send the prompt and payload; return the model's answer as a dict."""
        request = {
            "model": self.settings.ollama_model,
            "stream": False,
            "format": schema,
            "options": {
                "temperature": TEMPERATURE,
                "num_ctx": self.settings.ollama_num_ctx,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
        try:
            response = self._http.post("/api/chat", json=request)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LLMError(f"Ollama request failed: {error}") from error

        content = response.json().get("message", {}).get("content", "")
        try:
            answer = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMError("Model answer is not a valid JSON") from error
        if not isinstance(answer, dict):
            raise LLMError("Model answer is not a JSON object")
        return answer

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text, from the embedding model."""
        request = {"model": self.settings.ollama_embed_model, "input": texts}
        try:
            response = self._http.post("/api/embed", json=request)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LLMError(f"Ollama embedding request failed: {error}") from error

        vectors = response.json().get("embeddings", [])
        if len(vectors) != len(texts):
            raise LLMError("Embedding model returned the wrong number of vectors")
        return vectors
