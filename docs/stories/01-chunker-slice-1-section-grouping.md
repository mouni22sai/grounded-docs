# Story 01: Chunker slice 1, section grouping with contextual headers

Status: accepted 2026-10-10. Written by the user, reviewed by Claude against the acceptance
criteria below, and committed as the first chunker commit.

## Story

As the ingestion CLI, I want to hand the chunker every Block of one document and get back one
Chunk per section, each carrying a header that names the document and the section, and the page
range it came from, so that every chunk the system later embeds, retrieves and quotes is
self-describing and citable to a page.

## Why now

This is stage 5 of the ingest pipeline (discover, fingerprint, parse, adapt, chunk, embed, store)
and the first behaviour everything downstream depends on. Grouping by heading is the core of
structure-aware chunking (FR-2). The header is what stops "excess £115" floating free of its
insurer and section. The page range is what makes a page-level citation possible. The size
window, splitting, overlap and table rules all sit on top of this grouping, so it has to be right
first.

## Contract

**Input.** A call `chunk_blocks(blocks, title)` where `blocks` is a `list[Block]` in reading
order for one document, and `title` is the document title string. The list may be empty.
`Block` already exists in `src/grounded_docs/ingest/chunker.py`: a frozen, slotted dataclass with
fields `page: int`, `label: str`, `text: str`, `is_heading: bool`, in that order.

**Output.** A `list[Chunk]`, in the same order as the sections appeared. `Chunk` is a frozen,
slotted dataclass, built the same way as `Block`, with exactly these three fields in this order:

- `text` (str): the header line, a blank line, then the body. Exact format below.
- `page_start` (int): the lowest page number among the body blocks of the section.
- `page_end` (int): the highest page number among the body blocks of the section. It equals
  `page_start` when the whole section sits on one page.

**Text format, exactly.** The header is `title`, a space, `>`, a space, the nearest heading's
text. If no heading has been seen yet, the header is `title` alone with no separator. Then `\n\n`.
Then the body: the `text` of each non-heading block in the section, joined with a single `\n`.
No trailing newline. A heading block's text appears in the header only, never in the body.

Example: title `Aviva Motor Limits`, heading block `Glass`, two body blocks `Alpha` and `Beta`
gives the string `Aviva Motor Limits > Glass\n\nAlpha\nBeta`.

**Behaviour.** Walk the blocks in order. A heading block closes the current section and starts
a new one. Non-heading blocks are added to the current section's body. When the blocks run out,
the last section is closed too. A section is emitted as a Chunk only if it has at least one body
block.

## Acceptance criteria

Each criterion is one test in `tests/test_chunker.py`. Suggested names in brackets.

1. **One section, one chunk.** Given a heading block then one text block, when chunked, the
   result has exactly one Chunk whose text is the header, blank line, body.
   (`test_single_section_becomes_one_chunk_with_header`, already written)
2. **Two sections, two chunks.** Given heading A, text, heading B, text, the result has two
   Chunks in that order: the first with header `title > A` and only the first text in its body,
   the second with header `title > B` and only the second text.
   (`test_each_heading_starts_a_new_chunk`)
3. **Body before any heading.** Given a text block with no heading before it, the result has one
   Chunk whose header is the bare title, no `>`.
   (`test_text_before_first_heading_uses_title_only`)
4. **Empty sections are skipped.** Given heading A immediately followed by heading B, then text,
   the result has exactly one Chunk, with header `title > B`. No chunk for A.
   (`test_heading_with_no_body_produces_no_chunk`)
5. **Page range is recorded.** Given a heading on page 1, text on page 1 and text on page 2 in
   the same section, the Chunk has `page_start == 1` and `page_end == 2`.
   (`test_chunk_records_page_range_of_its_body`)
6. **Empty input.** Given an empty list, the result is an empty list.
   (`test_no_blocks_gives_no_chunks`)

## Out of scope for this slice

The 300 to 800 token window, splitting long sections, overlap, dropping pictures and page
furniture, table rules, and the two-level section path such as `What's Covered > Glass in your
vehicle's windscreen, windows or sunroof`. Each gets its own story later.

## Definition of done

- All six tests exist and `uv run pytest` reports 6 passed.
- `uv run ruff check .` and `uv run ruff format --check .` are both clean.
- `chunk_blocks` is the only public function. Helpers, if any, start with an underscore.
- Diff reviewed by Claude against the criteria above, then committed as the first chunker commit.

## Hints, not instructions

- Criteria 2, 4 and 6 are all about the moment a section closes. A small helper that turns the
  current heading, body list and pages into one Chunk, called both when a new heading arrives and
  once after the loop, keeps that logic in one place.
- Criterion 5 falls out of `min` and `max` over a list of page numbers collected alongside the
  body texts.
- Criterion 3 is an `if` on whether a heading has been seen. Decide what "no heading yet" looks
  like in your variables before you write the format line.
- Write the tests first, watch them fail, then make them pass one at a time, running
  `uv run pytest` after each.
