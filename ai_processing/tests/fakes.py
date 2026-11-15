"""Fake model used by the tests instead of Ollama."""

# Each topic is one dimension of the fake embedding vector.
TOPICS = [("canola", "油菜籽"), ("lng",), ("potash",)]


class FakeLLM:
    """Stands in for OllamaClient: returns a prepared answer and keeps what it received."""

    def __init__(self, answer=None, error=None, embed_error=None):
        self.answer, self.error, self.embed_error = answer, error, embed_error
        self.payload = None
        self.embed_calls = 0

    def generate_json(self, system_prompt, payload, schema):
        self.payload = payload
        if self.error:
            raise self.error
        return self.answer

    def embed(self, texts):
        """One number per topic: 1 if the text mentions it (in English or Chinese)."""
        self.embed_calls += 1
        if self.embed_error:
            raise self.embed_error
        return [
            [1.0 if any(word in text.lower() for word in words) else 0.0 for words in TOPICS]
            for text in texts
        ]
