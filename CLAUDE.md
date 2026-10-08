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
