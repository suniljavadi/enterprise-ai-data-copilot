def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[dict]:
    """Split into overlapping character chunks along paragraph boundaries where possible."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[dict] = []
    buffer = ""

    def flush():
        if buffer.strip():
            chunks.append({"chunk_index": len(chunks), "text": buffer.strip()})

    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= chunk_size:
            buffer = f"{buffer}\n{paragraph}".strip()
        else:
            flush()
            overlap_text = buffer[-chunk_overlap:] if buffer else ""
            buffer = f"{overlap_text}\n{paragraph}".strip()

    flush()
    return chunks
