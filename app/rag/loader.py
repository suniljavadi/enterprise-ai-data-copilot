from pathlib import Path

_SUPPORTED_EXTENSIONS = {".txt", ".md"}


class DocumentLoadError(ValueError):
    pass


def load_document(path: str | Path) -> tuple[str, dict]:
    file_path = Path(path)
    if file_path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        raise DocumentLoadError(f"Unsupported document type: {file_path.suffix}")
    if not file_path.exists():
        raise DocumentLoadError(f"Document not found: {file_path}")

    text = file_path.read_text(encoding="utf-8", errors="replace")
    metadata = {"document_name": file_path.name, "source": str(file_path)}
    return text, metadata


def list_documents(directory: str | Path) -> list[Path]:
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    return sorted(p for p in dir_path.iterdir() if p.suffix.lower() in _SUPPORTED_EXTENSIONS)
