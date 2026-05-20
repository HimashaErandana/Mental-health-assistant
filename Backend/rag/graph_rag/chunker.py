import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def load_md_files(self, data_dir: str = "rag/data") -> list[Document]:
        documents = []
        data_path = Path(data_dir)

        if not data_path.exists():
            return documents

        for md_file in data_path.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            doc = Document(page_content=content, metadata={"source": str(md_file.name)})
            documents.append(doc)

        return documents

    def load_single_file(self, filepath: str) -> Document:
        file_path = Path(filepath)
        if not file_path.exists():
            return None
        content = file_path.read_text(encoding="utf-8")
        return Document(page_content=content, metadata={"source": file_path.name})

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        return self.splitter.split_documents(documents)
