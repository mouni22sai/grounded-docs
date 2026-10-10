# Story 02: Chunker slice 2, token counting and the upper size limit

Status: issued 2026-10-10, not started. Begins once Story 01 is committed. The user writes the
code, tests and the DECISIONS.md entry; Claude reviews against the acceptance criteria below.

## Story

As the ingestion CLI, I want a section whose text is longer than the embedding window to come
back as several chunks, split only between blocks, each still carrying the section header and its
own page range, so that no chunk exceeds the FR-2 upper bound of 800 tokens and every chunk stays
self-describing and citable.

## Why now

Slice 1 emits one chunk per section no matter how long it is. Policy booklets have sections that
run for pages (general exclusions, claims conditions), which would give chunks of several thousand
tokens. Those embed badly, because one vector has to stand for too many ideas, and they are too
long to hand to the answer model as a quoted passage. FR-2 says "target 300 to 800 tokens". To
enforce a limit in tokens we first need a way to count tokens, so this slice adds the project's
first runtime dependency after Docling and records that choice in DECISIONS.md.

## Background: what a token is

Language models do not read characters or words. They read tokens, pieces of text from a fixed
vocabulary, typically a short word or part of a longer one. In English one token is about three
quarters of a word. Counting is done by the tokenizer, not the model, and each model is tied to the
one tokenizer it was trained with. Two models that share a tokenizer see the same sentence as the
same number of tokens. Under a different tokenizer, even one from the same vendor, the same
sentence can come out as a different number of tokens. We have not yet pinned the embedding model
(DECISIONS.md, Embeddings row), so we cannot use its exact tokenizer. We pick one well-known
tokenizer as a proxy, the `cl100k_base` encoding from the `tiktoken` library, and swap it later if
the pinned model needs a different one. A 10 to 20 percent difference between tokenizers does not
matter for a target window.

## Contract

**Dependency.** `tiktoken`, added with `uv add tiktoken` (a runtime dependency, not dev). The
encoding is `cl100k_base`, loaded once when the module is imported, not on every call.

**New public function.** `count_tokens(text: str) -> int` in
`src/grounded_docs/ingest/chunker.py`. Returns the number of `cl100k_base` tokens in `text`.
Document text is untrusted, so strings that look like special tokens, such as `<|endoftext|>`,
must be counted as ordinary text and must never raise.

**Changed signature.** `chunk_blocks(blocks: list[Block], title: str, max_tokens: int = 800)`.
The third parameter is new and has a default, so every existing caller and every slice 1 test
keeps working unchanged.

**Behaviour.** Section grouping and the header format are exactly as in Story 01. Within one
section, body blocks are packed in order into pieces:

- A piece is one Chunk: header, blank line, body. Its size is `count_tokens` of that whole text,
  header included, because that is the string that will be embedded.
- A block joins the current piece if the piece would still be at most `max_tokens` tokens with
  it. Otherwise the current piece is emitted and a new piece starts with this block.
- A block that is on its own larger than `max_tokens` forms a piece by itself and is emitted as
  is. Splitting inside a block is Story 03.
- Every piece from the same section has the same header. Each piece's `page_start` and
  `page_end` come from its own blocks only.
- Block texts are never cut. Reading all pieces of a section in order gives back the section body
  exactly.

## Acceptance criteria

Each criterion is one test unless it says otherwise.

1. **Token counting works.** `count_tokens("")` is 0 and `count_tokens("Hello world")` is 2.
   `count_tokens("<|endoftext|>")` returns a number rather than raising.
   (`test_count_tokens_counts_cl100k_tokens`)
2. **Short sections are untouched.** All six Story 01 tests pass with no edits, because the
   default `max_tokens` of 800 is far above their fixtures. No new test; the existing six are the
   proof.
3. **A long section splits between blocks.** Given heading A and three body blocks, with
   `max_tokens` chosen so the header plus the first two blocks fits and all three do not, the
   result is two Chunks. The first body is block 1 then block 2; the second body is block 3 only.
   Both have header `title > A`. (`test_long_section_splits_between_blocks`)
4. **One oversize block stays whole.** Given one body block whose text alone is larger than
   `max_tokens`, the result is one Chunk containing that block's full text.
   (`test_single_oversize_block_is_kept_whole`)
5. **Each piece has its own page range.** Given heading A on page 1 and body blocks on pages 1,
   2 and 3, with `max_tokens` chosen so only two blocks fit, the first Chunk has `page_start` 1
   and `page_end` 2, the second has `page_start` 3 and `page_end` 3.
   (`test_split_pieces_record_their_own_pages`)

## Out of scope for this slice

Splitting inside a block (table rows, numbered clauses, sentences) is Story 03. Overlap between
neighbouring pieces is Story 04. The lower bound of 300 tokens, which would mean merging small
sections, is deliberately deferred: the ingestion CLI will report the real chunk-size distribution
over the corpus first, and the decision to merge or not will be made on that evidence and recorded
in DECISIONS.md.

## Definition of done

- `uv add tiktoken` has been run; `pyproject.toml` and `uv.lock` both changed.
- DECISIONS.md has a new dated entry under "Changes during the build", in the same shape as the
  existing ones: Context, Decision, Alternatives considered (the Hugging Face `tokenizers` library
  with the eventual embedding model's own tokenizer; a characters-divided-by-four estimate), and
  the swap path (one constant to change once the embedding model is pinned).
- `uv run pytest` reports 10 passed: the six from Story 01 unchanged plus four new.
- `uv run ruff check .` and `uv run ruff format --check .` are both clean.
- Public functions are `chunk_blocks` and `count_tokens` only. Helpers start with an underscore.
- Diff reviewed by Claude against the criteria above, then committed as the second chunker commit.

## Hints, not instructions

- `_close_section` currently returns one Chunk or None. Make it return a `list[Chunk]`, empty
  when there is no body. The caller then uses `extend`, and both `if chunk is not None` checks
  disappear.
- Inside it, keep a list of blocks for the current piece. For each block, build the text the piece
  would have with that block added and count it. If the current piece is not empty and the count
  is over the limit, emit the current piece and start a new one. Emit whatever is left after the
  loop. Counting the whole piece text each time is slower than it needs to be; that is fine at
  this scale.
- For the fixtures in criteria 3 and 5, do not guess token numbers. Build the exact text you
  expect the first Chunk to have, and set `max_tokens` to `count_tokens` of that text. Anything
  larger then overflows by construction.
- Load the encoding into a module-level constant with a leading underscore. The first call
  downloads a vocabulary file of about 2 MB and caches it, so the first test run needs network.
- Look up the `encode` method's parameters in the tiktoken README to see how to stop special
  token strings from raising.
