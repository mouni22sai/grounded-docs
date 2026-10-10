# Decisions

Technology decisions for grounded-docs. The first table is copied from PRD section 10 and is the
starting point. Everything below it is a dated record of what changed during the build and why.
Add an entry whenever a default is overridden, a listed choice is swapped, or an alternative is
tried and rejected.

## Decisions from the PRD (section 10)

| Decision | Chosen | Alternatives considered | Why |
|---|---|---|---|
| Vector store | Postgres with pgvector | Qdrant, Pinecone, Weaviate, Chroma | One database for vectors, lexical search and metadata; the most common default in postings and teams; teaches SQL. Qdrant is the recommended alternative if multi-vector or very large scale is needed. |
| Parsing | Docling | PyMuPDF, Unstructured, LlamaParse | Best open-source table and layout fidelity; on Thoughtworks Radar Trial; no vendor lock-in. |
| Lexical retrieval | Postgres full-text search | Elasticsearch, OpenSearch, rank_bm25 in memory | Zero extra infrastructure; good enough at this corpus size; document the BM25 difference. |
| Fusion | Reciprocal rank fusion | Weighted score fusion | Robust without score calibration. |
| Reranker | Hosted cross-encoder (Cohere Rerank) with an open fallback (bge-reranker) | No reranker, LLM-based reranking | Largest quality gain per unit of complexity; the ablation proves it. |
| Generation model | Current flagship tier with a cheap-tier fallback | Single model | Provider-agnostic design is expected; fallback demonstrates resilience. |
| Embeddings | One hosted embedding model, version pinned | Open model via local inference | Simplicity first; note the swap path here when it is chosen. |
| API framework | FastAPI | Flask, Django, Litestar | Async, typed, SSE support, the de facto standard in postings. |
| Observability | Langfuse | LangSmith, Arize Phoenix | Open source, dominant in downloads, datasets and scores API. |
| Orchestration | Plain Python | LangChain, LlamaIndex | The pipeline is a dozen functions; a framework would hide the prompts and the decisions. |

## Changes during the build

### 2026-10-08: Docling OCR is off by default, on only for scanned documents

**Context.** Docling 2.135.0 (docling-core 2.101.0) with every default on took 577 s of pipeline
time to convert `aviva-motor-limits-2026`, a 5-page A4 sheet with a full text layer and no
embedded images. Docling's own stage profiler attributed 555 s to the `ocr` stage.

**Cause.** The default OCR mode in this version is `pdf_aware_layout_regions`. It sends a layout
region to OCR when the region overlaps any non-text PDF element, and that includes vector shapes,
not just bitmaps. Table borders, cell shading and ruled lines are vector shapes, so every table
region in a text-layer PDF is OCR'd even though the text underneath is already perfect. Every
policy booklet in the corpus has ruled tables, so this would hit 13 of the 14 documents.

**Decision.** `PdfPipelineOptions.do_ocr = False` is the ingestion default. OCR is enabled per
document, and only `bajaj-motor-scanned-2013` needs it (no text layer). The per-document flag
belongs in the corpus manifest, not in code.

**Evidence.** Same file, same machine, warm model cache:

| Configuration | pipeline_total | ocr | layout | table_structure |
|---|---|---|---|---|
| all defaults (OCR on, 4 threads) | 576.6 s | 555.1 s | 37.5 s | 36.7 s |
| OCR off, 4 threads | 33.8 s | not run | 14.1 s | 27.3 s |

**Consequences.** Text-layer PDFs convert about 17x faster with identical text output, since the
text layer is the source either way. The ingestion CLI must carry a per-document OCR switch. If a
future document has a text layer with bitmap-only regions (scanned pages inside a digital PDF),
revisit by trying `OcrMode.LAYOUT_REGIONS` with a bitmap check rather than turning OCR on globally.

### 2026-10-08: Docling inference threads set to the physical core count, not the default 4

**Context.** `AcceleratorOptions.num_threads` defaults to 4. The development machine has 10
physical cores (12 logical).

**Decision.** Set threads to the physical core count. For the spike this was the
`DOCLING_NUM_THREADS` environment variable. The ingestion CLI should set it explicitly through
`AcceleratorOptions(num_threads=...)` so the behaviour does not depend on the shell.

**Evidence.** Same file, OCR off, warm cache:

| Threads | pipeline_total | layout | table_structure |
|---|---|---|---|
| 4 | 33.8 s | 14.1 s | 27.3 s |
| 10 | 21.5 s | 5.9 s | 18.2 s |

Layout scales well because it is one batched forward pass. Accurate TableFormer scales less
because it decodes a table cell by cell, which is inherently sequential.

**Consequences.** About 4 s per page on this machine, so a full pass over the corpus is on the
order of 30 minutes. Acceptable for version 1 given idempotent ingestion skips unchanged files.

### 2026-10-08: TableFormer stays in accurate mode (default kept, noted for review)

**Context.** With OCR off, `table_structure` is the dominant stage at 18 to 27 s per 5 pages.
`TableFormerMode.FAST` exists and would cut this.

**Decision.** Keep `ACCURATE` for now. Cover-limit tables are the primary citation targets for the
golden set, and the Markdown read of the Aviva sheet showed all columns and values intact. Speed is
not yet a problem worth paying accuracy for.

**Revisit when:** the full-corpus ingest exceeds roughly an hour, or if the Post Office booklet
(two printed pages per PDF page) shows table errors that FAST mode would not make worse.

### 2026-10-08: Build one converter per process and loop over files

**Context.** The elapsed time of a single conversion exceeded Docling's own `pipeline_total` by
14 to 71 s. The gap is model loading (layout model and TableFormer weights), which happens lazily
on the first `convert` call and is not covered by the stage profiler. The spread depends on
whether the weights are in the OS disk cache.

**Decision.** The ingestion CLI constructs `DocumentConverter` once and converts all documents in
that process. Never spawn one process per PDF.

### 2026-10-09: Layout model stays on the default heron preset; one known recall miss accepted

**Context.** The item walk over `aviva-motor-limits-2026` showed heron detecting 1 of 6 tables on
page 4. The other five, all optional covers in exactly the same visual style as the 20 tables it
found on pages 1-3 and 5, came out as fragmented `text` items with columns interleaved. Total 21
tables found, 26 correct. Two fixes were tried.

**Experiment 1: `LayoutObjectDetectionOptions.from_preset("layout_egret_large")`.** Found all 6
tables on page 4 but merged page 5 into 3 tables with no section headers at all: the windscreen
excess headings and their one-row tables, the primary citation targets, were absorbed into larger
blobs. Total 24 tables. Wall time 218 s against about 35 s for heron with the same 10 threads.

**Experiment 2: lower the table confidence cut.** Docling filters detections twice: the engine
keeps scores >= 0.3, then `LayoutPostprocessor.CONFIDENCE_THRESHOLDS[TABLE]` (a hard-coded class
constant) keeps >= 0.5. Setting the table cut to 0.3 with heron produced 17 tables: page 4
unchanged, and page 5 lost 4 of its 5 tables. Wall time 186 s, because every extra low-confidence
candidate goes through accurate TableFormer before being merged or discarded.

**Decision.** Keep `layout_heron_default`. Do not override the post-processor constant. Record the
page 4 miss as a corpus quirk in `data/CORPUS.md` and keep golden-set questions off the optional
covers on that page. The Aviva policy booklet covers the same options.

**Why accept rather than keep tuning.** Both fixes traded a page nobody will cite for the page
everyone will. The layout model and its thresholds are tuned as a system, and moving one knob blind
degraded the system. One page of one companion sheet is not worth that, and a 5-6x ingest slowdown
is not either.

**Revisit when:** Docling ships a new default layout model (re-run the spike and compare the table
count, expected 26), or if the other 13 documents show the same miss pattern at scale.

**API note.** In docling 2.135.0 the layout model is selected with
`LayoutObjectDetectionOptions.from_preset(name)` assigned to `PdfPipelineOptions.layout_options`.
The older `DOCLING_LAYOUT_*` constants assigned to `layout_options.model_spec` raise
`AttributeError: 'LayoutModelConfig' object has no attribute 'get_engine_config'`.

### 2026-10-09: Corpus pass estimate revised to 45-90 minutes; OCR for Bajaj only confirmed

**Context.** The Post Office booklet (33 spread pages, 50 tables) converted in 338.5 s wall time
at 10 threads with OCR off. The scanned Bajaj policy (7 pages) took 668.3 s with OCR on
(RapidOCR defaults, PP-OCRv6 small models on CPU). Both figures include model load. Per printed
page that is 4-5 s without OCR and about 95 s with it.

**Estimate.** The corpus is 566 PDF pages, almost all single printed pages. A full pass is 45 to
90 minutes plus about 11 minutes for Bajaj, so the "roughly an hour" trigger for revisiting
TableFormer FAST mode (2026-10-08 entry above) will probably fire. Decision deferred until the
ingestion CLI measures a real pass: idempotent ingestion makes the first full run the measurement.

**Decision.** OCR on for `bajaj-motor-scanned-2013` only, with Docling's RapidOCR defaults and no
tuning (PRD scope). OCR output is arbitrary Unicode (U+0146 appeared on page 2) and the Windows
console is cp1252, so the ingestion CLI never prints document text; it logs document ids, page
counts, chunk counts and timings, and text goes to Postgres (UTF-8) only. The spike script now
replaces unencodable characters on stdout after this crashed its item walk.

**Consequences.** Bajaj text will carry scan noise (dropped spaces, doubled letters, c/d swaps).
Citation quotes are verified against the stored OCR text, so they stay consistent, but golden-set
questions on this document should target its cleanest passages (the IDV depreciation schedule on
page 2) rather than its tables. Docling labelled one region `document_index`; the chunker treats
that label as a table, not as furniture.

### 2026-10-10: Chunk sizes are counted with tiktoken `cl100k_base` as a proxy tokenizer

**Context.** FR-2 states the chunk size target in tokens, 300 to 800, and chunker slice 2 enforces
the upper bound. A token count only has meaning relative to a tokenizer, and the tokenizer that
matters is the one the embedding model was trained with, because it defines the window a chunk
must fit. The embedding model is not yet pinned (Embeddings row in the PRD table above), so its
tokenizer cannot be used. Something has to count tokens now.

**Decision.** Add `tiktoken` as a runtime dependency and count with its `cl100k_base` encoding,
the vocabulary used by OpenAI's GPT-4 generation and the text-embedding-3 models. The encoding is
loaded once into a module-level constant in `grounded_docs.ingest.chunker` and exposed through one
public function, `count_tokens(text) -> int`. Document text is untrusted, so the call passes
`disallowed_special=()`: a document that happens to contain a special-token string such as
`<|endoftext|>` is counted as ordinary text instead of raising. The piece size that is compared
against the limit is the count of the whole embedded string, contextual header included.

**Alternatives considered.**

- Hugging Face `tokenizers` with the eventual embedding model's own vocabulary. Exact, but the
  model is not chosen, so there is no vocabulary to load yet. This is the likely swap target if the
  pinned model is not an OpenAI one.
- Characters divided by four. No dependency and no download, but the ratio drifts with Markdown
  tables, numbers and OCR noise, all common in this corpus, and the error has no bound. Rejected
  because a real tokenizer costs one small dependency and gives a count that is exact for one
  plausible pinned model and within 10 to 20 percent for the others.

**Swap path.** One constant, `_ENCODING` in `chunker.py`, names the encoding. If the pinned model
is an OpenAI embedding model, nothing changes. If tiktoken ships the pinned model's encoding under
another name, change the string. Otherwise replace the constant and the body of `count_tokens` with
the `tokenizers` equivalent; the rest of the chunker only ever calls `count_tokens`.

**Consequences.** The first call to `tiktoken.get_encoding` downloads a vocabulary file of about
2 MB and caches it under the temp directory, so the first test run on a fresh machine or CI runner
needs network access, or `TIKTOKEN_CACHE_DIR` pointed at a pre-populated folder. The chunker counts
the full candidate piece text every time it considers adding a block, which is quadratic in blocks
per section; acceptable at this corpus size and simple to replace with incremental counting if the
ingestion CLI shows it matters. The 300-token lower bound is deliberately not enforced yet: the
ingestion CLI will report the real chunk-size distribution over the corpus first, and whether to
merge small sections will be decided on that evidence and recorded here.
