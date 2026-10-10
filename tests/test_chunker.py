from grounded_docs.ingest.chunker import Block, chunk_blocks


def test_single_section_becomes_one_chunk_with_header():
    blocks = [
        Block(1, "section_header", "Glass", True),
        Block(
            1,
            "text",
            "We will pay to replace the windscreen. The excess is £115.",
            False,
        ),
    ]

    chunks = chunk_blocks(blocks, "Aviva Motor Limits")

    assert len(chunks) == 1
    assert chunks[0].text == (
        "Aviva Motor Limits > Glass\n\n"
        "We will pay to replace the windscreen. The excess is £115."
    )


def test_each_heading_starts_a_new_chunk():
    blocks = [
        Block(1, "section_header", "A", True),
        Block(1, "text", "Text under A", False),
        Block(1, "section_header", "B", True),
        Block(1, "text", "Text under B", False),
    ]

    chunks = chunk_blocks(blocks, "Document Title")

    assert len(chunks) == 2
    assert chunks[0].text == ("Document Title > A\n\nText under A")
    assert chunks[1].text == ("Document Title > B\n\nText under B")


def test_text_before_first_heading_uses_title_only():
    blocks = [Block(1, "text", "Text with no heading before it", False)]

    chunks = chunk_blocks(blocks, "Document Title")

    assert len(chunks) == 1
    assert chunks[0].text == ("Document Title\n\nText with no heading before it")


def test_heading_with_no_body_produces_no_chunk():
    blocks = [
        Block(1, "section_header", "A", True),
        Block(1, "section_header", "B", True),
        Block(1, "text", "Text under B", False),
    ]

    chunks = chunk_blocks(blocks, "Document Title")

    assert len(chunks) == 1
    assert chunks[0].text == ("Document Title > B\n\nText under B")


def test_chunk_records_page_range_of_its_body():
    blocks = [
        Block(1, "section_header", "A", True),
        Block(1, "text", "Text under A", False),
        Block(2, "text", "Text under A continued...", False),
    ]

    chunks = chunk_blocks(blocks, "Document Title")

    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2


def test_no_blocks_gives_no_chunks():
    blocks = []

    chunks = chunk_blocks(blocks, "Document Title")

    assert len(chunks) == 0
