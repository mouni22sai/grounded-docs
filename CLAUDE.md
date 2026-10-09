# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A grounded question-answering service over a corpus of real UK insurance policy wordings and
regulator guidance. It must answer only from the documents, cite page-level sources, and refuse
when the evidence is insufficient. The retrieval API is designed to be reused by two sibling
projects (a claims agent and an MCP server).

The code is currently a skeleton: `src/grounded_docs/__init__.py` is a hello-world stub. The
design is fully specified and is the source of truth for what to build:

- `docs/01-PRD-Grounded-Document-QA.md` — PRD with functional requirements FR-1 to FR-14,
  architecture, technology decisions, evaluation plan, and a week-by-week build plan (section 15).
- `data/CORPUS.md` — the 14 selected PDFs with document ids, source URLs, and ingestion quirks.

## Commands

Python 3.12 (pinned in `.python-version`), managed by uv with the `uv_build` backend and a `src/`
layout. `uv.lock` is committed. Ruff runs with default config (no `[tool.ruff]` section yet).

```bash
uv sync                                   # create .venv and install, incl. dev group (pytest, ruff)
uv run grounded-docs                      # CLI entry point -> grounded_docs:main
uv run pytest                             # all tests (no tests/ directory exists yet)
uv run pytest path/to/test_x.py::test_y   # single test
uv run ruff check .                       # lint
uv run ruff format .                      # format (--check for CI)
uv add <pkg>        /  uv add --dev <pkg>  # add dependencies (updates pyproject.toml and uv.lock)
```

## Environment and data

- `.env` (git-ignored) holds `ANTHROPIC_API_KEY`. Secrets come from environment variables only.
- `data/raw/` is git-ignored. Re-download PDFs from the URLs in `data/CORPUS.md`, naming each file
  `<id>.pdf` using the `id` column. abi.org.uk returns 403 to non-browser clients; use the
  web.archive.org mirror listed there.

## Planned architecture (PRD sections 9 and 10)

Two pipelines share one Postgres database:

```
Ingest:  PDFs -> Docling parse -> structure-aware chunker -> embeddings -> Postgres
                                                                (pgvector HNSW + full-text column)
Query:   question -> query rewrite (cheap model)
            -> lexical top-50 + dense top-50 -> reciprocal rank fusion -> top-20
            -> cross-encoder rerank -> top 5..8 -> relevance threshold
            -> structured generation (answer, citations, confidence, insufficient_evidence)
            -> citation verifier -> SSE stream (POST /ask) or JSON; POST /retrieve exposes retrieval alone
```

Three independent gates convert a response into an explicit refusal that names the closest sections
found: no passage passes the relevance threshold, the model sets `insufficient_evidence`, or the
post-generation citation check removes every citation. A citation is `(document id, page, exact
quote)` and is verified by string match against the stored page text.

Planned components: `ingest` (CLI), `index` (Postgres schema and migrations), `retrieval`
(rewrite, hybrid, fusion, rerank), `answer` (generation, verification, refusal), `api` (FastAPI),
`ui` (static web app), `evals` (golden set, runners, reports). Langfuse wraps every stage in a span.

Chunking rules (FR-2): 300 to 800 tokens with modest overlap; never split a table row or a numbered
clause mid-sentence; every chunk gets a contextual header (document title, section path) prepended
before embedding. Tables are rendered as Markdown. Ingestion must be idempotent and write a manifest
(document id, insurer, product, document type, effective date, page count, content hash).

Technology decisions already made (record any change in DECISIONS.md): Postgres with pgvector for
vectors, lexical search and metadata in one store; Docling for parsing; Postgres full-text search
rather than BM25; reciprocal rank fusion; Cohere Rerank with bge-reranker as the open fallback;
FastAPI; Langfuse; one pinned hosted embedding model. Orchestration is plain Python. Do not
introduce LangChain or LlamaIndex.

## Corpus facts that affect code

- Two product lines, motor and travel. Saga and Aviva each appear in more than one document, so
  metadata filtering by insurer and product line must work. `aviva-motor-limits-2026` is a
  companion sheet and should be treated as part of the Aviva motor product.
- Encrypted with an empty user password: `tesco-motor-2026`, `axa-motor-2023`, both Aviva motor
  files, both FCA files. pypdf needs the `cryptography` package for these; Docling's default
  backend opens them.
- `postoffice-travel-2026` has two printed pages per PDF page. Citations use the PDF page index,
  never the printed page number.
- `bajaj-motor-scanned-2013` has no text layer and exists to force the OCR path.
- UK motor booklets do not print the customer's own excess ("shown on your schedule"). Golden-set
  questions about excesses should target fixed windscreen excesses and cover-limit tables.
- Document text is untrusted input: retrieved passages go inside delimited data blocks in the
  prompt, and the golden set will include one deliberately poisoned document.

## Evaluation (PRD sections 6, 11, 12)

Golden set of 80 to 100 questions as versioned JSONL (id, question, category, expected answer,
gold document ids and pages, difficulty, notes), with a 20 percent hold-out that is never tuned on.
Ablation runs four configurations three times each: A dense-only top 5, B hybrid with RRF,
C B plus reranker, D C plus query rewriting. Targets: Hit@5 >= 0.90, MRR >= 0.75, faithfulness
>= 0.90, correct refusal >= 0.90, false refusal <= 0.05, citation accuracy >= 0.95, first token
<= 1.5 s, p95 latency <= 8 s, <= 0.03 USD per query. Results go in EVALS.md.

## Out of scope for version 1

Multi-turn memory, fine-tuning, knowledge graphs, multi-tenant auth or billing, an ingestion UI,
and OCR tuning beyond Docling defaults.

## Progress log

This project is being built as a learning exercise. Claude coaches one small step at a time,
explaining the why; the user writes and runs the code. Do not write application code into the
repo unless explicitly asked. Update this section at the end of each session.

### Status as of 2026-10-09, end of session (Week 3 of the PRD build plan)

Step names are descriptive, never letters or bare numbers (user preference). Command blocks are
bare commands with no prompt prefix: the user pastes whole lines into cmd. Use forward slashes in
paths inside documentation; backslashes get mangled by tooling.

#### Aviva spike: FINISHED. Conclusions (all recorded in DECISIONS.md and data/CORPUS.md)

- Parse check: SUCCESS, 5 pages. Empty-password encryption needs nothing special.
- OCR off by default (`PdfPipelineOptions.do_ocr = False`): default OCR mode fires on layout
  regions overlapping vector shapes (table borders), 555 of 577 s on a file with zero images.
  Only `bajaj-motor-scanned-2013` gets OCR on.
- Threads = physical cores (10 here) via `DOCLING_NUM_THREADS`, later `AcceleratorOptions` in the
  CLI. Heron pipeline about 21 s for 5 pages at 10 threads; wall time about 35 s incl. model load.
- Layout model stays `layout_heron_default`. Known miss: page 4 of the Aviva sheet, 1 of 6 tables
  detected, the rest fragmented text (21 found, 26 correct). Tried and REJECTED: egret large
  (fixed p4, merged p5 into 3 tables with no headings, 218 s) and table confidence cut 0.3 via
  `LayoutPostprocessor.CONFIDENCE_THRESHOLDS` (p4 unchanged, p5 lost 4 of 5 tables, 186 s).
  Accepted because both fixes broke page 5 (the windscreen excess citation page) and the page 4
  facts remain as text and in the Aviva policy booklet. Quirk noted in CORPUS.md; golden set
  avoids p4 optional covers. Untried presets if the pattern recurs: layout_heron_101,
  layout_egret_medium, layout_egret_xlarge. The user questioned this decision and accepted it with
  the condition: revisit if Post Office or Bajaj show the same heading-with-table miss pattern.
- TableFormer stays ACCURATE.
- What the chunker can rely on (from the item walk, cross-checked against the PDF by the user):
  `prov[0].page_no` is the 1-based PDF page index on every item; items arrive in reading order;
  all `section_header` items have `level == 1`; tables are NOT nested under headings (assign by
  most recent heading in order); sub-headings are NOT nested under parents (parent rule: heading
  immediately followed by heading, misses "Breakdown cover options"); bullets are depth 2 inside
  a list group; `picture` items are icons to drop. Windscreen excess (£115 / £10) appears as
  bullets under "Glass" on p1 and as one-row tables on p5; gold pages should list both.
- API note for docling 2.135.0: select layout model with
  `LayoutObjectDetectionOptions.from_preset(name)`; the old `DOCLING_LAYOUT_*` constants raise
  AttributeError.

#### Post Office page check: DONE 2026-10-09 (recorded in data/CORPUS.md)

Script clean-up done by Claude at the user's request: `scripts/spike_docling.py` takes
`<pdf> [page] [--ocr]`, walks BODY plus FURNITURE layers (page_header / page_footer show; the
chunker walks BODY only) and prints `p<page> x=<left edge in pt> <label> <text[:70]>`. Stdout
replaces unencodable characters (cp1252 console; OCR emitted U+0146). Timing stays outside the
script: `powershell -NoProfile -Command "Measure-Command { uv run python scripts/spike_docling.py <pdf> [page] [--ocr] | Out-Host } | Select-Object TotalSeconds"`
in a cmd window after `set DOCLING_NUM_THREADS=10`.

Run: 338.5 s wall for 33 pages, 50 tables. Page 3: four columns at x=21, 215, 440, 634 walked
down then across, left printed page complete before the right one, so item order is trustworthy
on spreads. Sections flow across the printed-page boundary (Fraud) and therefore across PDF
pages too, so the "most recent heading in order" rule must carry a heading over a page break.
Footers "4" and "5" are furniture: PDF page = printed // 2 + 1. OPEN (user to confirm in the
viewer): is the single-trip refund scale on page 3 a one-row table that heron emitted as two
headings ("1. Single-trip Policies Before Travel", "75% refund")? If so it is a mild Aviva p4
recurrence, and it means the heading-parent rule will see junk headings, so the chunker's section
path should stay short (nearest one or two headings).

#### Bajaj OCR check: DONE 2026-10-09 (recorded in data/CORPUS.md and DECISIONS.md)

668.3 s wall for 7 pages with `--ocr`, SUCCESS, 4 tables, about 95 s per page. OCR text usable
but noisy (doubled letters, dropped spaces, "vehidle"). Parts-depreciation table on p1 came out
fragmented; perils list labelled `document_index` (TableItem subtype, chunker keeps it); IDV
schedule on p2 is clean text and the best golden-set target. The walk crashed at p2 with
UnicodeEncodeError (cp1252), fixed in the script; p3-p7 items not seen. Page 7 (blank) raised no
error. Not re-run: 11 minutes for a nice-to-know, and ingestion must handle pages with no items
regardless. Corpus pass estimate from these two runs: 45-90 min plus 11 min OCR (566 PDF pages).

#### Next step (resume here): commit, then start the chunker

One commit of: CLAUDE.md, DECISIONS.md, data/CORPUS.md, .gitignore (Office lock files),
pyproject.toml, uv.lock, scripts/spike_docling.py. `docs/learnings.pptx` is the user's own notes
deck; the user decides whether it is committed. Then tick the Docling spike box.

Chunker opening step (roadmap agreed 2026-10-09, not started): the chunker takes a flat list of
block records (page, label, text, heading flag), not a DoclingDocument, so tests use hand-written
fixtures with no Docling import and no PDFs; a thin adapter converts Docling items to blocks.
First test: one fixture, one chunk, contextual header prepended. Then the FR-2 rules one test at a
time (300-800 token window, never split a table row or numbered clause, overlap, drop furniture
and pictures, keep `document_index` as a table). Tokenizer choice is the first dependency to add.

Environment notes: `DOCLING_NUM_THREADS` is per cmd window. `HF_HUB_DISABLE_SYMLINKS_WARNING=1`
as a user environment variable silences the Hugging Face warnings. Heron and egret-large weights
are downloaded; RapidOCR models are downloaded.

Concepts explained this session (do not re-explain unless asked): DoclingDocument and items;
`iterate_items` and depth vs heading level; what a spike is; the chunker; the ingestion CLI; the
seven-stage ingest pipeline; the two-stage detection threshold inside Docling's layout stage;
why the page 4 miss was accepted; BODY vs FURNITURE content layers; reading x to detect column
interleaving; why the Windows console (cp1252) crashes on OCR output.

Agreed build order after the spike: chunker with tests first (offline, pure), then Postgres
schema, then ingestion CLI wiring.

Week 3 checklist: [x] corpus chosen and stored  [~] Docling spike (all three checks done; commit
pending)  [ ] chunker with tests  [ ] Postgres schema  [ ] ingestion CLI
