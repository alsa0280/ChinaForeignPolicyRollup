# AI processing service (Role 4)

Receives one cleaned article (`document`) from the n8n workflow and returns one
`ai_claims` row. Runs locally with Ollama (`qwen2.5:7b`); no API key is needed.

```
n8n HTTP Request ──POST /process──► ai_processing (port 8000) ──► Ollama (port 11434)
```

## Setup

```powershell
conda activate gac-ai
pip install -r requirements.txt
copy .env.example .env      # optional; defaults work locally
```

## Run the tests

From the repo root:

```powershell
pytest
```

Tests never call Ollama; the model is replaced by a fake client.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where the Ollama server runs |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model used for all tasks |
| `OLLAMA_TIMEOUT_S` | `600` | Seconds to wait for one model answer |
| `MAX_TEXT_CHARS` | `6000` | Longer article text is trimmed and flagged |

## Layout

| Path | Purpose |
|---|---|
| `config.py` | Settings from environment variables |
| `reference_data.py` | Loads `data/opportunities.json` and `data/source_registry.json` |
| `validation.py` | Deterministic checks on model output |
| `credibility.py` | Source-type base score plus bounded model adjustment |
| `language.py` | Rule-based language detection |
| `llm_client.py` | Ollama client |
| `processor.py` | One document in, one `ai_claims` row out |
| `app.py` | FastAPI endpoints `/health` and `/process` |
| `tests/` | Unit tests and fixtures |

Shared files used by this service live in the repo-wide folders:

| Path | Used for |
|---|---|
| `prompts/ai_processing/` | Versioned prompts this service sends to the model (`assess_v1.md`, ...) |
| `prompts/` | Starter-kit prompts the versioned prompts are based on |
| `schemas/` | Data contracts, including the `ai_claims` table (`schemas/tables/ai_claims.txt`) |
| `data/opportunities.json`, `data/source_registry.json` | Opportunity list and source types |

## Status

Structure only. Each module is implemented in its own step, with tests.
