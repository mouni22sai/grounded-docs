from dataclasses import dataclass

import tiktoken

# Proxy tokenizer until the embedding model is pinned (see DECISIONS.md). Loaded once per process.
_ENCODING = tiktoken.get_encoding("cl100k_base")


@dataclass(frozen=True, slots=True)
class Block:
    """One Docling item, flattened. The chunker's only input type."""

    page: int
    label: str
    text: str
    is_heading: bool


@dataclass(frozen=True, slots=True)
class Chunk:
    """One unit of text to embed and retrieve. Header already prepended."""

    text: str
    page_start: int
    page_end: int


def count_tokens(text: str) -> int:
    """Number of cl100k_base tokens in text.

    Document text is untrusted, so strings that spell a special token such as
    <|endoftext|> are counted as ordinary text instead of raising.
    """
    return len(_ENCODING.encode(text, disallowed_special=()))


def _build_header(title: str, heading: str | None) -> str:
    return title if heading is None else f"{title} > {heading}"


def _piece_text(header: str, body: list[Block]) -> str:
    """The exact string a piece would be embedded as: header, blank line, body."""
    return header + "\n\n" + "\n".join(b.text for b in body)


def _make_chunk(header: str, body: list[Block]) -> Chunk:
    pages = [b.page for b in body]
    return Chunk(
        text=_piece_text(header, body), page_start=min(pages), page_end=max(pages)
    )


def _close_section(
    title: str, heading: str | None, body: list[Block], max_tokens: int
) -> list[Chunk]:
    """Turn a finished section into zero or more Chunks, splitting only between blocks.

    Body blocks are packed greedily in order. A block joins the current piece if the
    piece stays within max_tokens with it; otherwise the piece is emitted and a new
    one starts with that block. A block too large on its own is kept whole.
    """
    if not body:
        return []
    header = _build_header(title, heading)
    chunks: list[Chunk] = []
    piece: list[Block] = []

    for block in body:
        if piece and count_tokens(_piece_text(header, [*piece, block])) > max_tokens:
            chunks.append(_make_chunk(header, piece))
            piece = []
        piece.append(block)

    chunks.append(_make_chunk(header, piece))
    return chunks


def chunk_blocks(blocks: list[Block], title: str, max_tokens: int = 800) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading: str | None = None
    body: list[Block] = []

    for block in blocks:
        if block.is_heading:
            chunks.extend(_close_section(title, heading, body, max_tokens))
            heading = block.text
            body = []
        else:
            body.append(block)

    chunks.extend(_close_section(title, heading, body, max_tokens))
    return chunks
