# Collection Workflow — Integration Test Report

**Project:** CST8516 AI Project 1 — China Foreign Policy Rollup  
**Workflow:** `collection_workflow` (n8n)  
**Test date:** 2026-11-21  
**Status:** Main HTML-processing path passed; other paths remain unverified  
**Report type:** Validation / development progress report

## 1. Objective

Validate that the n8n collection workflow can load registered sources, fetch and extract source material, process AI-generated claims, store results, and produce a daily change note. This was a limited integration test, not a full production run.

## 2. Test environment

- Self-hosted n8n in Docker, accessed through the team instance on port 5679.
- Local Ollama service with `qwen2.5:7b` and `llama3.2:3b` available; the screenshots confirm an Ollama Model node executed, but do not establish which model that node selected.
- Source registry: `/home/node/.n8n-files/data/source_registry.json`.
- Change-note destination: `/home/node/.n8n-files/output/`.
- Test scope: first **2** records from a registry of **56** entries, both using `method: page`.
- Observed execution duration: approximately **10 minutes**.

## 3. Executed workflow

The following processing sequence showed successful execution (green nodes):

1. Manual trigger → Read/Write Files from Disk → Extract from File → Split Out.
2. Limit to 2 items → Switch (`method=page`) → Prepare Fetch → HTTP Request → HTML extraction → Parse Dates.
3. Edit Fields (Success) → Crypto/hash → database checks and document insertion → Read Opportunities → Extract Opportunities → Load Opportunities.
4. Basic LLM Chain with Ollama and Structured Output Parser → Verify AI Claims → Insert AI Claim → Explode Claims → Deduplicate Events → Insert Event.
5. Get row(s) → Determine state_change action → Switch on existing event → Insert `current_state`.
6. Build Change Note → Convert to File → Write Change Note.

The HTTP request returned HTML for both test sources, and the HTML node extracted a title, publication metadata, and text. The final write node reported one text-file output.

## 4. Observed results

| Metric | Observed result |
|---|---:|
| Source registry entries | 56 |
| Test sources selected | 2 |
| HTML/page sources processed | 2 |
| New leads in generated note | 9 |
| Updated leads | 0 |
| Conflicts | 0 |
| `current_state` insert-branch items | 9 |
| Generated change-note file | 1 |
| File size reported by n8n | 6.53 KB |

The generated note is headed **Daily change note**, dated **2026-11-21**, and clearly marked **VALIDATION DRAFT: claims are AI-extracted and unreviewed. Not for distribution.**

### New leads recorded

| ID | Subject | Source |
|---|---|---|
| B01 | Revitalization of the Joint Economic and Trade Commission | S01 |
| B02 | Bilateral trade and investment promotion | S01 |
| B03 | Agrifood cooperation and communication | S01 |
| B04 | Green and sustainable trade | S01 |
| B05 | E-commerce cooperation | S01 |
| P01 | Energy and clean technology cooperation | S02 |
| P03 | Agri-food trade barriers and tariffs | S02 |
| P05 | Public safety and security cooperation | S02 |
| P06 | Cultural exchanges | S02 |

The generated note includes previous-state information, evidence summaries, quotations, source references, and review reminders for each lead. These are **unreviewed AI-extracted claims**, not independently verified findings.

## 5. Paths not exercised

- **RSS processing loop:** The two selected registry entries were page sources; the RSS branch remained grey and was not tested.
- **HTTP error-handling path:** Both tested HTTP requests succeeded; the error branch did not execute.
- **Update existing `current_state`:** The nine items followed the insert path, so the update path was not tested.
- **Full 56-source run:** Not attempted in this test.

Grey nodes on these conditional paths are expected when no input is routed to them; their behavior remains unverified.

## 6. Issues and limitations

1. **Missing evidence dates:** The S01 leads B01–B05 display `Evidence (date unknown)`, even though the HTML extraction stage returned publication metadata. Date propagation or normalization should be reviewed.
2. **Source verification pending:** The generated note explicitly states that the claims are AI-extracted and unreviewed. Source quotations and interpretations require manual validation.
3. **Character encoding:** Earlier preview text showed garbled punctuation in at least one excerpt; inspect encoding and text normalization before distribution.
4. **Performance:** Approximately 10 minutes for the limited two-source run. This is not enough evidence to estimate full-registry runtime reliably.
5. **No regression/idempotency check yet:** A repeat run has not been evaluated to confirm whether unchanged claims are correctly recognized and whether duplicates are avoided.

## 7. Next steps

1. Preserve/export the working n8n workflow and generated test note.
2. Verify the nine claims against their primary sources.
3. Correct missing S01 evidence dates and check character encoding.
4. Test at least one RSS source and one controlled HTTP failure.
5. Test an unchanged repeat run and an update to an existing event.
6. Expand source coverage gradually while monitoring runtime and failures.

## 8. Conclusion

The limited end-to-end integration test **passed for the main HTML/page branch**: two source records were fetched and processed, AI claims and state records were generated, and a 6.53 KB daily change note containing nine new leads was written successfully. The RSS, error, update, and full-registry paths remain outside the verified scope. The output is a validation draft and is not approved for external distribution.
