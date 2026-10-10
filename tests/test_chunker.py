from grounded_docs.ingest.chunker import Block, chunk_blocks, count_tokens


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


def test_count_tokens_counts_cl100k_tokens():
    assert count_tokens("") == 0
    assert count_tokens("Hello world") == 2
    assert isinstance(count_tokens("<|endoftext|>"), int)


def test_long_section_splits_between_blocks():
    blocks = [
        Block(1, "section_header", "A", True),
        Block(1, "text", "Text under A", False),
        Block(1, "text", "More text under A", False),
        Block(1, "text", "Even more text under A", False),
    ]
    # The limit is exactly the size of header + first two blocks, so the third overflows.
    first_piece = "Document Title > A\n\nText under A\nMore text under A"

    chunks = chunk_blocks(
        blocks, "Document Title", max_tokens=count_tokens(first_piece)
    )

    assert len(chunks) == 2
    assert chunks[0].text == first_piece
    assert chunks[1].text == "Document Title > A\n\nEven more text under A"


def test_single_oversize_block_is_kept_whole():
    blocks = [
        Block(1, "section_header", "A", True),
        Block(
            1,
            "text",
            "This is a very long block that exceeds the max tokens limit",
            False,
        ),
    ]

    chunks = chunk_blocks(blocks, "Document Title", 5)

    assert len(chunks) == 1
    assert chunks[0].text == (
        "Document Title > A\n\nThis is a very long block that exceeds the max tokens limit"
    )


def test_split_pieces_record_their_own_pages():
    blocks = [
        Block(1, "section_header", "A", True),
        Block(1, "text", "Text under A which is on Page 1", False),
        Block(2, "text", "Text under A which is on Page 2", False),
        Block(3, "text", "Text under A which is on Page 3", False),
    ]
    first_piece = "Document Title > A\n\nText under A which is on Page 1\nText under A which is on Page 2"

    chunks = chunk_blocks(blocks, "Document Title", count_tokens(first_piece))

    assert len(chunks) == 2
    assert chunks[0].text == first_piece
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2
    assert chunks[1].text == "Document Title > A\n\nText under A which is on Page 3"
    assert chunks[1].page_start == 3
    assert chunks[1].page_end == 3
