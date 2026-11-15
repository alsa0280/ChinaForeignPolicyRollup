# AI processing service (Role 4)

Receives one cleaned article (`document`) and returns one `ai_claims` row. Runs
locally with Ollama: `qwen2.5:7b` analyses the article and `bge-m3` (multilingual
embeddings) picks the opportunities to consider. No API key is needed.

For the PoC, the service is run on one article: Daniele's R001 sample
(`data/samples/R001.txt`, source `BRAVE-R001-1`).

```
n8n HTTP Request ──POST /process──► ai_processing (port 8000) ──► Ollama (port 11434)
```

## Setup

```powershell
conda activate gac-ai
pip install -r requirements.txt
copy .env.example .env      # optional; defaults work locally
ollama pull qwen2.5:7b
ollama pull bge-m3
```

## Process the shared article

From the repo root, with Ollama running:

```powershell
python -m ai_processing.run_r001
```

It processes Daniele's R001 sample and saves the `ai_claims` row to
`docs/ai_processing/R001_output.json` (about 5-7 minutes on a laptop without a GPU).

## Run the API (for n8n)

From the repo root, with Ollama running:

```powershell
uvicorn ai_processing.app:app --host 0.0.0.0 --port 8000
```

| Endpoint | What it does |
|---|---|
| `GET /health` | Returns `{"status": "ok", "model": ..., "prompt_version": ...}` |
| `POST /process` | Body: one `document` (JSON). Returns the `ai_claims` row. A body without `source_id` gets `422` |

`--host 0.0.0.0` lets n8n, running in Docker, reach the service at
`http://host.docker.internal:8000`. Interactive docs: http://localhost:8000/docs.

## Run the tests

From the repo root:

```powershell
pytest
```

Tests never call Ollama; `tests/fakes.py` provides a fake model.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where the Ollama server runs |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model that analyses the article |
| `OLLAMA_EMBED_MODEL` | `bge-m3` | Multilingual embedding model that picks candidate opportunities |
| `OLLAMA_TIMEOUT_S` | `600` | Seconds to wait for one model answer |
| `OLLAMA_NUM_CTX` | `8192` | Context window (tokens) for prompt + article + answer |
| `MAX_TEXT_CHARS` | `6000` | Longer article text is trimmed and flagged |
| `PROMPT_VERSION` | `assess_v1` | Analysis prompt, from `prompts/ai_processing/` |

## Layout

| File | Purpose |
|---|---|
| `models.py` | Data models (`Document`, `Opportunity`, `Claim`, `LLMAssessment`, `AIClaimsRow`) and fixed lists (`Dimension`, `FocusArea`, `Language`, `ClaimType`, `DropReason`). `python -m ai_processing.models` regenerates the JSON Schema |
| `config.py` | `Settings` (environment variables) and `ReferenceData` (opportunities and source types from `data/`) |
| `llm_client.py` | `OllamaClient`: chat with a JSON answer, and embeddings |
| `ranking.py` | `OpportunityRanker`: picks the opportunities closest in meaning to the article |
| `checks.py` | Rule-based checks: `ClaimValidator`, `KeyTermMatcher`, `CredibilityScorer` |
| `processor.py` | `Processor`: one document in, one `ai_claims` row out |
| `run_r001.py` | Processes the shared article (R001) and saves the output |
| `app.py` | FastAPI endpoints `/health` and `/process`, called by n8n |
| `tests/` | One test file per module, shared fixtures (`conftest.py`) and the fake model (`fakes.py`) |

Shared files in the repo-wide folders:

| Path | Used for |
|---|---|
| `prompts/ai_processing/assess_v1.md` | Prompt sent to the model (versioned; based on `prompts/01_extract.md`) |
| `schemas/ai_processing/llm_output.schema.json` | JSON Schema of the model's answer, sent to Ollama; generated from `models.py` |
| `schemas/tables/ai_claims.txt` | The `ai_claims` table the output row is written to |
| `data/opportunities.json`, `data/source_registry.json` | Opportunity list and source types |

## How one document is processed

1. The text is split into paragraphs (non-empty lines) and cut at `MAX_TEXT_CHARS`,
   keeping whole paragraphs; a cut adds the red flag `text truncated`.
2. Only the 5 opportunities closest in meaning to the article are sent to the model.
   Each paragraph and each opportunity is turned into a vector by `bge-m3`; an
   opportunity's score is its best-matching paragraph, so a Mandarin paragraph can
   match an opportunity described in English. With all 28 opportunities,
   `qwen2.5:7b` mixed up similar IDs. If embeddings fail, all 28 are sent.
3. The model answers in JSON, constrained by the JSON Schema.
4. Claims are validated (rules below). Then two common model mistakes are fixed: an
   `event_date` equal to the publication date becomes `null`, and an English quote
   gets no `support_quote_en`.
5. `focus_area` comes from the working area of the first kept claim's opportunity;
   without claims, the model's choice is used.
6. Credibility is computed and the `ai_claims` row is returned. If the text is empty,
   Ollama fails or the answer cannot be read, the row has `ai_status` `failed`.

## Validation rules

A claim from the model is kept only if all of these hold; otherwise it is dropped and
counted in `claims_dropped`.

| Check | Reason when it fails |
|---|---|
| Required fields present (`opportunity_id`, `dimension`, `value`, `claim_en`, `locator`, `support_quote`) | `missing_field` |
| `opportunity_id` exists in `data/opportunities.json` | `unknown_opportunity` |
| `dimension` is in the fixed list | `invalid_dimension` |
| `support_quote` appears word for word in the article | `quote_not_in_text` |
| `locator` is `paragraph N` | `bad_locator` |
| The quote (or its English rendering) shares a key term with the opportunity's title or monitor triggers | `unrelated_to_opportunity` |

If the quote sits in a different paragraph than the locator says, the locator is
corrected and the correction is noted in `uncertainty`. An invalid `event_date`, or
one later than `fetched_at`, becomes `null`; a `claim_type` other than `reported_fact`
is stored as `analysis`.

Credibility = base score from the source type (`official` 4, `company` 3, `reported` 3,
unknown 2) plus the model's adjustment of -1, 0 or +1, used only with a reason; always
between 1 and 5 and explained in `credibility_reason`.

## Known limitations

- The key-term check is a heuristic. It removed all 9 wrong claims of the n8n run of
  2026-11-14, but a claim that misstates its quote, or one linked only through common
  words such as "additional" or "tariffs", can still pass. A second model pass (the
  starter kit's `prompts/03_verify.md`) was tried and removed: with `qwen2.5:7b` it was
  unreliable. Whether to add a verifier is an open question for the team.
- The model's answers vary between runs (other claims besides the main one change).
- About 5-7 minutes per article on a laptop without a GPU.

## Test fixtures

`tests/fixtures/documents/` holds documents in the `document` format. `s01_excerpt` and
`s02_excerpt` contain only the sentences quoted in the n8n run of 2026-11-14;
`zh_synthetic` was written for tests and is not real news. The R001 document is built
at test time from `data/samples/R001.txt`. `tests/fixtures/llm_responses/` holds model
answers used by the fake model.
