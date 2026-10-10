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

### Status as of 2026-10-10, end of session (Week 3 of the PRD build plan)

Step names are descriptive, never letters or bare numbers (user preference). Command blocks are
bare commands with no prompt prefix: the user pastes whole lines into cmd. Use forward slashes in
paths inside documentation; backslashes get mangled by tooling.

#### Docling spike: FINISHED and committed (0a4ef7d)

All three checks done (Aviva limits sheet, Post Office page 3, Bajaj with OCR). The decisions and
their evidence live in DECISIONS.md (six dated entries, 2026-10-08 and 2026-10-09) and the
per-file quirks in data/CORPUS.md; do not re-derive them. What was decided:

- OCR off by default; on only for `bajaj-motor-scanned-2013` (about 95 s per page, 668 s total).
- Threads = physical cores (10 here); one `DocumentConverter` per process.
- Layout model `layout_heron_default`, TableFormer ACCURATE. Known accepted miss: Aviva limits
  sheet page 4, 1 of 6 tables. Egret large and a lower table threshold both broke page 5 and were
  rejected. Post Office and Bajaj did not reproduce the pattern, so the decision stands.
- Full corpus pass estimate 45-90 min plus 11 min OCR (566 PDF pages). TableFormer FAST is
  deferred until the ingestion CLI measures a real pass.
- The ingestion CLI never prints document text (OCR emits non-cp1252 characters): ids, counts
  and timings only.

What the chunker can rely on (cross-checked against the PDFs by the user):

- `prov[0].page_no` is the 1-based PDF page index on every item. Items arrive in reading order,
  including on the Post Office two-page spreads (four text columns, left printed page complete
  before the right). Printed page numbers are `page_footer` items in the FURNITURE layer; the
  chunker walks BODY only. For Post Office, PDF page = printed page // 2 + 1.
- Sections flow across page boundaries, so "assign each item to the most recent `section_header`
  in order" must carry the heading over a page break.
- All `section_header` items have `level == 1`; tables are NOT nested under headings;
  sub-headings are NOT nested under parents. The parent heuristic (heading immediately followed
  by heading) misses some parents and will see junk: heron labelled the plain line "75% refund"
  as a heading and a numbered heading as a `list_item`. Treat heading labels as hints and keep
  the section path short (nearest one or two headings).
- Bullets are depth 2 inside a list group. `picture` items are icons to drop. `document_index`
  is a TableItem subtype and is kept as a table. A page can have no items (Bajaj page 7).
- Windscreen excess (£115 / £10) appears as bullets under the heading "Glass in your vehicle's
  windscreen, windows or sunroof" on Aviva limits p1 (under the parent heading "What's Covered")
  and as one-row tables on p5; gold pages should list both.
- `scripts/spike_docling.py` (throwaway) takes `<pdf> [page] [--ocr]` and prints
  `p<page> x=<left edge pt> <label> <text[:70]>` for every BODY and FURNITURE item. Time it from
  outside, after `set DOCLING_NUM_THREADS=10` in the cmd window:
  `powershell -NoProfile -Command "Measure-Command { uv run python scripts/spike_docling.py <pdf> [page] [--ocr] | Out-Host } | Select-Object TotalSeconds"`

#### Chunker: IN PROGRESS (slices 1 and 2 committed, Story 03 issued)

Working style: each step is a written user story (story, why, input/output contract, numbered
acceptance criteria that map one-to-one to tests, out of scope, definition of done, hints) in
`docs/stories/`, mirrored as a Trello card. The user writes code and tests and brings the diff
back; Claude reviews against the criteria, then commits and ticks the card. Exception this
session: the user explicitly asked Claude to write `chunker.py` for slice 2, the DECISIONS.md
entry and the slice 2 test fixes. The default stays: no application code from Claude unless asked.

Committed:
- Slice 1 (fa6d69f): `Block(page, label, text, is_heading)`, `Chunk(text, page_start, page_end)`,
  `chunk_blocks` grouping blocks by section with a contextual header; six tests.
- Slice 2 (a676fb6): tiktoken `cl100k_base` proxy loaded once into `_ENCODING`; public
  `count_tokens(text)` passing `disallowed_special=()` so special-token strings in document text
  never raise; `chunk_blocks(blocks, title, max_tokens=800)`; `_close_section` returns
  `list[Chunk]` and packs body blocks greedily with the header counted, via helpers `_piece_text`
  and `_make_chunk`; an oversize single block stays whole; ten tests; DECISIONS.md entry dated
  2026-10-10 (proxy choice, alternatives, swap path). Story 02 card ticked and in Done.

Contract as it stands: header `<title> > <nearest heading>` (bare title before any heading), blank
line, body block texts joined by `\n`, no trailing newline; heading text never in the body; two
public functions, helpers underscored; the ingestion CLI calls the chunker once per document with
all its blocks (sections cross page boundaries; overlap needs the previous chunk). The 300-token
lower bound is deferred until the ingestion CLI reports the real chunk-size distribution.

Review lessons from slice 2, apply to future reviews: a test can pass through the wrong rule (a
limit below one block exercised the oversize path, not packing), so check which rule a fixture
really hits; derive `max_tokens` from `count_tokens` of the expected first piece, never a guessed
number; watch for copy-paste index errors (`chunks[0]` repeated where `chunks[1]` was meant);
`isinstance` over `type(...) ==`; run `uv run ruff format .` as the very last step.

#### Next step (resume here): Story 03, splitting inside an oversize block

Story 03 is issued: `docs/stories/03-chunker-slice-3-split-inside-block.md`, Trello card in Today.
Table blocks (`table`, `document_index`) split between rows with the two head lines repeated on
every piece; text blocks split at sentence ends with `re.split(r"(?<=[.!?])\s+", ...)`; a single
oversize row or sentence is kept whole; split pieces are never merged with neighbouring blocks;
`page_start` and `page_end` both equal the block page; no new dependency; six criteria, five new
tests, 15 passed; DECISIONS.md entry (regex over NLTK punkt, spaCy, pysbd; false boundaries at
abbreviations accepted). On resume: ask whether it is ready. If yes, run `uv run pytest` (expect
15 passed), `uv run ruff check .`, `uv run ruff format --check .`, read the diff and the DECISIONS
entry, review against the six criteria, commit as the third chunker commit, tick the card and move
it to Done. If not ready, coach from wherever they are stuck.

Also this session: `docs/tokenizer-explained.pdf` (untracked, user may commit) holds the tokenizer
lesson: what a token is (one vocabulary row, piece plus id), vocabulary and BPE, byte fallback,
model welded to one tokenizer, model families, tiktoken as a ruler on our side. Made from HTML via
headless Edge; recipe in memory. Do not re-explain anything in that PDF, nor why slice 2 splits
only between blocks and what Story 03 adds.

Stories are mirrored as Trello cards (board "grounded-docs q&a"; new stories go in Today, accepted
ones are ticked and moved to Done; credentials in `.env` as TRELLO_API_KEY and TRELLO_TOKEN, never
printed). Trello does not render Markdown tables, so stories use lists, not tables.

Stories queued after slice 3, each as its own file in `docs/stories/`: modest overlap (Story 04);
drop `picture`, `page_header`, `page_footer`; keep `document_index` as a table; two-level section
path (a heading immediately followed by a heading becomes the parent, e.g.
`What's Covered > Glass in your vehicle's windscreen, windows or sunroof`); a test that a heading
carries across a page break; small-section merging decided on corpus evidence. Then the
Docling-to-Block adapter, Postgres schema, ingestion CLI (agreed build order).

Environment notes: `DOCLING_NUM_THREADS` is per cmd window. `HF_HUB_DISABLE_SYMLINKS_WARNING=1`
as a user environment variable silences the Hugging Face warnings. Heron and egret-large weights
are downloaded; RapidOCR models are downloaded. The Windows console is cp1252, so printing OCR
output can crash; the spike script sets `sys.stdout.reconfigure(errors="replace")`.

Concepts explained so far (do not re-explain unless asked): DoclingDocument and items;
`iterate_items` and depth vs heading level; what a spike is; the chunker; the ingestion CLI; the
seven-stage ingest pipeline; the two-stage detection threshold inside Docling's layout stage;
why the page 4 miss was accepted; BODY vs FURNITURE content layers; reading x to detect column
interleaving; why the Windows console (cp1252) crashes on OCR output. Added 2026-10-10: module
vs import package vs distribution package; subpackages need `__init__.py`; src vs flat vs
single-module vs workspace layouts; the import path (`sys.path`) and editable installs;
dataclass, decorator, type hints, frozen and slots; pytest discovery (`tests/test_*.py`,
`test_` functions, assert) and red-green; what a Block is (a Docling item cut down to four facts,
`is_heading` decided by the adapter so heading detection lives in one place); the ingest pipeline
as seven stages (discover, fingerprint, parse, adapt, chunk, embed, store) and who calls the
chunker; structure-aware chunking with contextual headers and why; the list of alternative
chunking strategies (fixed-size, sentence, recursive, page, semantic, parent-child, sliding
window, proposition/agentic, contextual retrieval, late chunking); why a body-less heading
gives no chunk (nothing to cite, retrieval noise, the parent-heading story carries its text); the
three Chunk fields and why a chunk needs two page numbers; what a token is (Story 02 text).

Week 3 checklist: [x] corpus chosen and stored  [x] Docling spike  [~] chunker with tests (slices 1 and 2 committed fa6d69f and a676fb6, slice 3 issued)
[ ] Postgres schema  [ ] ingestion CLI
