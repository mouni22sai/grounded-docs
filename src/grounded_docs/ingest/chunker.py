from dataclasses import dataclass


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


def _build_header(title: str, heading: str | None) -> str:
    return title if heading is None else f"{title} > {heading}"


def _close_section(title: str, heading: str | None, body: list[Block]) -> Chunk | None:
    """Turn a finished section into a Chunk, or None if it has no body."""
    if not body:
        return None
    pages = [b.page for b in body]
    text = _build_header(title, heading) + "\n\n" + "\n".join(b.text for b in body)
    return Chunk(text=text, page_start=min(pages), page_end=max(pages))


def chunk_blocks(blocks: list[Block], title: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading: str | None = None
    body: list[Block] = []

    for block in blocks:
        if block.is_heading:
            chunk = _close_section(title, heading, body)
            if chunk is not None:
                chunks.append(chunk)
            heading = block.text
            body = []
        else:
            body.append(block)

    chunk = _close_section(title, heading, body)
    if chunk is not None:
        chunks.append(chunk)

    return chunks
