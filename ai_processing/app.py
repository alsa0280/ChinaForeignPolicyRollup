"""HTTP API called by the n8n HTTP Request node.

GET  /health   service status, model and prompt version
POST /process  one document in, one ai_claims row out

Run from the repo root, with Ollama running:
    uvicorn ai_processing.app:app --host 0.0.0.0 --port 8000

--host 0.0.0.0 lets n8n reach the service from inside Docker
(http://host.docker.internal:8000).
"""

# python library to create API endpoints
# why the API running, open http://localhost:8000/docs in a browser to see the automatic generated API docs
from fastapi import FastAPI

from ai_processing.config import ReferenceData, Settings
from ai_processing.llm_client import OllamaClient
from ai_processing.models import AIClaimsRow, Document
from ai_processing.processor import Processor


def create_app(settings: Settings | None = None, llm=None) -> FastAPI:
    """Build the API, by default Ollama is used."""
    settings = settings or Settings.from_env()
    processor = Processor(
        settings, ReferenceData.from_files(), llm or OllamaClient(settings)
    )
    app = FastAPI(title="GAC AI processing")

    # /health checks that the service is running
    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "model": settings.ollama_model,
            "prompt_version": settings.prompt_version,
        }

    # /process receives the article and returns the ai_claims row
    @app.post("/process")
    def process(document: Document) -> AIClaimsRow:
        return processor.process(document)

    return app


app = create_app()
