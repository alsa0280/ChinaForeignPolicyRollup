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
| `models.py` | Data models (`Document`, `Opportunity`, `Claim`) and fixed lists (`Dimension`, `FocusArea`, `Language`, `ClaimType`, `DropReason`) |
| `reference_data.py` | `ReferenceData`: opportunities and source types from `data/` |
| `validation.py` | `ClaimValidator` and `KeyTermMatcher`: checks on model output |
| `credibility.py` | `CredibilityScorer`: source-type base score plus bounded model adjustment |
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

| Module | Status |
|---|---|
| `models.py`, `reference_data.py`, `validation.py`, `credibility.py` | Implemented and tested |
| `config.py`, `llm_client.py`, `processor.py`, `app.py` | Not implemented yet |

## Validation rules

A claim from the model is kept only if all of these hold; otherwise it is dropped
and counted in `claims_dropped` with a reason.

| Check | Reason when it fails |
|---|---|
| Required fields present (`opportunity_id`, `dimension`, `value`, `claim_en`, `locator`, `support_quote`) | `missing_field` |
| `opportunity_id` exists in `data/opportunities.json` | `unknown_opportunity` |
| `dimension` is in the fixed list | `invalid_dimension` |
| `support_quote` appears word for word in the article | `quote_not_in_text` |
| `locator` is `paragraph N` | `bad_locator` |
| The quote (or its English rendering) shares a key term with the opportunity's title or monitor triggers | `unrelated_to_opportunity` |

Other rules: if the quote sits in a different paragraph than the locator says, the
locator is corrected and the correction is noted in `uncertainty` (paragraphs are the
non-empty lines of the text); scores are rounded and clamped to 1-5; an invalid
`event_date`, or one later than `fetched_at`, becomes `null`; a `claim_type` other
than `reported_fact` is stored as `analysis`.

The key-term check is a heuristic: it compares 5-letter word stems and ignores
stopwords and words common to most trade news (agreement, country, investment...).
It removes clearly unrelated claims but does not prove that a claim is correct.

## Test fixtures

`tests/fixtures/documents/` holds documents in the `document` format. `s01_excerpt`
and `s02_excerpt` contain only the sentences quoted in the n8n run of 2026-11-14;
files named `*_synthetic` were written for tests and are not real news. The R001
document is built at test time from `data/samples/R001.txt`.
