"""Process the shared article (Daniele's R001 sample) and save the output.

Run from the repo root, with Ollama running:
    python -m ai_processing.run_r001

The ai_claims row is written to docs/ai_processing/R001_output.json.
"""
import json
import time
from pathlib import Path

from ai_processing.config import DATA_DIR, REPO_ROOT, ReferenceData, Settings
from ai_processing.models import AIClaimsRow, Document
from ai_processing.processor import Processor

R001_SAMPLE = DATA_DIR / "samples" / "R001.txt"
R001_SOURCE_ID = "BRAVE-R001-1"
OUTPUT_FILE = REPO_ROOT / "docs" / "ai_processing" / "R001_output.json"


def run(settings: Settings, llm, output_file: Path = OUTPUT_FILE) -> AIClaimsRow:
    """Process R001 with the given model client and write the row to output_file."""
    document = Document.from_sample(R001_SAMPLE, R001_SOURCE_ID)
    row = Processor(settings, ReferenceData.from_files(), llm).process(document)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(row.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return row


if __name__ == "__main__":
    from ai_processing.llm_client import OllamaClient

    settings = Settings.from_env()
    print(f"Processing {R001_SAMPLE.name} with {settings.ollama_model} (this can take several minutes)...")
    start = time.time()
    row = run(settings, OllamaClient(settings))
    claims = json.loads(row.claims_json)
    print(f"Done in {time.time() - start:.0f}s: ai_status={row.ai_status}, "
          f"{len(claims)} claim(s) kept, {row.claims_dropped} dropped")
    for claim in claims:
        print(f"  {claim['opportunity_id']} {claim['dimension']}: {claim['value']}")
    if row.ai_error:
        print(f"  error: {row.ai_error}")
    print(f"Saved to {OUTPUT_FILE.relative_to(REPO_ROOT)}")
