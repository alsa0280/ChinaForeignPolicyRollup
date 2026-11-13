# China Foreign Policy Roll-up: n8n prototype

Prototype workflow for Global Affairs Canada. It collects articles from a source registry, deduplicates them, logs source health, uses a local LLM to extract structured claims about 28 tracked opportunities, validates the claims, stores them, and produces a daily change note.

```
sources -> fetch -> documents -> LLM claims -> validate -> events -> current_state -> change note (output/)
```

## Repo layout

| Path | Purpose |
|---|---|
| `n8n/` | Workflow exports: `collection_workflow.json` (main), `setup_tables.json`, `clear_tables.json` |
| `data/source_registry.json` | Sources the workflow reads (`status`: approved / candidate) |
| `data/opportunities.json` | The 28 tracked opportunities; the prompt is built from this |
| `data/samples/` | Sample search results (Brave) |
| `prompts/`, `schemas/` | Kit prompts and the extraction schema (data contract) |
| `output/` | Generated change notes (git-ignored) |
| `tutorials/` | Setup guides (plain text) |
| `docs/` | Client reports and the original starter-kit README |
| `reference/` | The original offline Python/SQLite demo, kept for comparison |

The remaining files in `data/` are the original kit's reference data.

## Run it

Step-by-step guides (Docker, Ollama, n8n, running the workflow) are in `tutorials/`; start with `tutorials/00_START_HERE.txt`. The short version:

1. **Start n8n with the repo mounted** (the workflows read and write `/home/node/.n8n-files`):
   ```
   docker run -it --rm --name n8n -p 5678:5678 \
     -v n8n_data:/home/node/.n8n \
     -v "<path to this repo>:/home/node/.n8n-files" \
     docker.n8n.io/n8nio/n8n
   ```
2. **Start Ollama** on the host and pull the model: `ollama pull qwen2.5:7b`. n8n reaches it at `http://host.docker.internal:11434`. **Note**: a primary objective for the remainder of this project is to find and tune a better model, so that there are more insightful details extracted and fewer errors in the change notes.
3. **Import the three workflows** from `n8n/` (Workflows > Import from file). In the Ollama node, select your Ollama credential.
4. **Create the tables:** run `setup_tables` once. Tables are referenced by name, so no re-selecting is needed.
5. **Run `collection_workflow`.** The change note appears in `output/`.
6. **Reset:** run `clear_tables` to empty all tables (it keeps the tables).

Tables: `documents`, `source_health`, `ai_claims`, `event`, `current_state`.

## Reference demo

The original kit's offline demo still works from the repo root:
```
python reference/pipeline.py --demo --out demo-output
python -m unittest discover -s reference/tests -v
```
