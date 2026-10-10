# Story 03: Chunker slice 3, splitting inside an oversize block

Status: issued 2026-10-10, not started. Begins once Story 02 is committed. The user writes the
code, tests and the DECISIONS.md entry; Claude reviews against the acceptance criteria below.

## Story

As the ingestion CLI, I want a single block whose text alone exceeds the token limit to come back
as several chunks, cut only between table rows or at sentence ends, each still carrying the section
header and the block's page, so that no table row or sentence is ever cut in the middle and the
only chunks still over the limit are single rows or sentences that cannot be made smaller.

## Why now

Slice 2 enforces the 800-token upper bound between blocks and keeps an oversize block whole. That
was accepted as a temporary violation. The corpus makes it a real one: Docling renders a table as
one block, and cover-limit tables run to twenty or more rows of Markdown, while general exclusions
and claims conditions arrive as single paragraphs of many sentences. Those are exactly the passages
the golden set will cite, so they must come back as chunks that embed well and quote cleanly.

FR-2 says "never split a table row or a numbered clause mid-sentence". That rule is about where a
cut inside a block may land, so it only becomes testable once we cut inside blocks. This slice is
that cut.

## Background: what an oversize block looks like

A table block's text is Markdown. The first line is the header row, the second is the separator
row made of pipes and dashes, and every line after that is one data row. A row is one line, so
"never split a row" means "cut only at line breaks, and never inside the first two lines". The two
head lines must be repeated at the top of every piece, otherwise a piece of rows has no column
names and cannot be read on its own.

A text block is a paragraph. A sentence ends with a full stop, exclamation mark or question mark
followed by whitespace. "Never mid-sentence" means "cut only at those positions". Numbered clauses
("1. We will pay...") are sentences too, so cutting at sentence ends already satisfies the FR-2
clause rule. Preferring a cut at the start of a clause over a cut at an inner sentence end is a
later refinement, to be made only if the corpus shows it matters.

Abbreviations such as "e.g." or "No." produce a false sentence end. That is harmless here: a false
boundary is only an extra place where a cut is allowed, and a cut there still leaves whole words on
both sides. The DECISIONS.md entry records this trade-off.

## Contract

**Signatures unchanged.** `chunk_blocks(blocks, title, max_tokens=800)` and `count_tokens(text)`
keep their signatures. No new dependency: sentence boundaries come from the standard library `re`.

**When a block is split.** Only when header plus that single block exceeds `max_tokens`. A block
that fits is never touched, so slice 1 and slice 2 behaviour is unchanged for every existing test.

**Table blocks.** A block whose label is `table` or `document_index`. Split its text into lines.
The first two lines are the table head and are repeated at the top of every piece. Data rows are
packed greedily in order: a row joins the current piece if the piece text (section header, blank
line, head lines, rows so far, this row, joined by newlines) stays within `max_tokens`. A table
with fewer than three lines has no data rows to split and is kept whole.

**Text blocks.** Any other label. Split the text into sentences at whitespace that follows `.`,
`!` or `?`. Sentences are packed greedily in order and joined by a single space. Whitespace between
sentences therefore normalises to one space; nothing else about the text changes.

**Oversize units.** A single row or sentence that is larger than `max_tokens` on its own, header
included, forms a piece by itself and is kept whole. This is the slice 2 rule applied one level
down. It is the only way a chunk can still exceed the limit after this slice.

**Pieces are not merged with neighbours.** When the packing loop meets an oversize block it emits
the piece in progress, then emits every piece of the split block as its own Chunk, then starts a
fresh piece with the next block. A split piece never shares a Chunk with a neighbouring block.

**Header and pages.** Every piece of a split block carries the same section header as the rest of
the section, and has `page_start` and `page_end` both equal to the block's page.

## Acceptance criteria

Each criterion is one test unless it says otherwise.

1. **An oversize text block splits at sentence ends.** Given heading A and one body block of four
   sentences, with `max_tokens` equal to `count_tokens` of the header plus the first two sentences
   joined by a space, the result is two Chunks. The first body is sentences 1 and 2, the second is
   sentences 3 and 4, both joined by a single space. Both have header `title > A`.
   (`test_oversize_text_block_splits_at_sentence_ends`)
2. **No sentence is ever cut.** For the same fixture, every piece body ends with sentence
   punctuation, and joining the bodies with a single space gives back the original block text.
   (`test_split_text_pieces_rebuild_the_block`)
3. **An oversize table splits between rows and repeats the head.** Given a table block with a
   header row, a separator row and four data rows, with `max_tokens` equal to `count_tokens` of
   the header plus the head plus the first two data rows, the result is two Chunks. Each body
   starts with the two head lines. The first holds rows 1 and 2, the second rows 3 and 4. The data
   rows of all pieces, in order, equal the original data rows.
   (`test_oversize_table_splits_between_rows_with_head_repeated`)
4. **A single oversize sentence is kept whole.** Given one body block that is one long sentence and
   `max_tokens` of 5, the result is one Chunk containing the whole sentence.
   (`test_single_oversize_sentence_is_kept_whole`)
5. **Split pieces are not merged with neighbours.** Given a short block, then an oversize block of
   two sentences, then another short block, with `max_tokens` chosen so that each sentence fits
   alone but the two do not fit together, the result is four Chunks in order: the first short block
   alone, sentence 1 alone, sentence 2 alone, the second short block alone.
   (`test_split_pieces_are_not_merged_with_neighbours`)
6. **Everything that fits is untouched.** All ten Story 01 and Story 02 tests pass with no edits.
   No new test; the existing ten are the proof.

## Out of scope for this slice

Overlap between neighbouring pieces is Story 04. Dropping `picture`, `page_header` and
`page_footer` blocks, the two-level section path, and the heading-across-a-page-break test are
their own stories. Preferring clause starts over inner sentence ends, and handling abbreviations,
wait for corpus evidence. The 300-token lower bound stays deferred until the ingestion CLI reports
the real chunk-size distribution.

## Definition of done

- `uv run pytest` reports 15 passed: the ten existing tests unchanged plus five new.
- `uv run ruff check .` and `uv run ruff format --check .` are both clean, with the formatter run
  as the last step.
- Public functions are still `chunk_blocks` and `count_tokens` only. New helpers start with an
  underscore. No new dependency in `pyproject.toml`.
- DECISIONS.md has a new dated entry under "Changes during the build": sentence boundaries by a
  regular expression rather than a sentence tokenizer library. Alternatives considered: NLTK
  punkt, spaCy, pysbd. Consequences: false boundaries at abbreviations are accepted and why; the
  table head is repeated in every table piece, so the pieces of a table are a little larger than
  the rows alone.
- Diff reviewed by Claude against the criteria above, then committed as the third chunker commit.

## Hints, not instructions

- `text.splitlines()` gives table rows. `re.split(r"(?<=[.!?])\s+", text.strip())` gives
  sentences; the lookbehind keeps the punctuation attached to the sentence before it.
- Both splits are the same greedy loop as `_close_section`, with a different unit (row or
  sentence instead of block), a different joiner (newline or space) and, for tables, two fixed head
  lines in front of every piece. One helper that takes the units, the joiner and the head lines,
  and returns a list of piece bodies, serves both cases. A second helper chooses rows or sentences
  from the block's label and calls it.
- In `_close_section`, test for an oversize block before the existing packing check. If header
  plus block alone exceeds the limit: emit the piece in progress, emit one Chunk per split body
  with `page_start` and `page_end` both set to `block.page`, reset the piece, and move to the next
  block. The existing loop body handles every block that fits.
- For criterion 5, make sentence 1 clearly longer than sentence 2, make the short blocks shorter
  than sentence 2, and set `max_tokens` to `count_tokens` of the header plus sentence 1. Then
  sentence 2 and the second short block would fit together if merging were allowed, so the test
  proves the no-merge rule rather than passing by accident.
- As in slice 2, do not guess token numbers. Build the exact text you expect the first piece to
  have and set `max_tokens` to `count_tokens` of it.
