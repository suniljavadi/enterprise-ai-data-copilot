from app.rag.chunker import chunk_text


def test_chunks_respect_max_size():
    text = "\n\n".join(f"Paragraph {i} with some content." for i in range(20))
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert all(len(c["text"]) <= 100 + 20 for c in chunks)
    assert len(chunks) > 1


def test_chunk_indices_are_sequential():
    text = "\n\n".join(f"Paragraph {i}." for i in range(5))
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_overlap_must_be_smaller_than_chunk_size():
    try:
        chunk_text("some text", chunk_size=50, chunk_overlap=50)
    except ValueError as exc:
        assert "chunk_overlap" in str(exc)
    else:
        raise AssertionError("Expected ValueError for overlap >= chunk_size")
