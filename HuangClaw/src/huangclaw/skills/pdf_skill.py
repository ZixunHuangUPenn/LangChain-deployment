from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from huangclaw.config import Settings, get_settings
from huangclaw.llm import build_embeddings


@dataclass(frozen=True)
class IngestStats:
    pdf_count: int
    page_count: int
    chunk_count: int
    collection_name: str
    chroma_dir: Path


@dataclass(frozen=True)
class RagHit:
    text: str
    source: str
    page: int
    chunk_index: int
    distance: float | None

    def format(self) -> str:
        distance = "" if self.distance is None else f" distance={self.distance:.4f}"
        return f"[{self.source} p.{self.page} chunk {self.chunk_index}{distance}]\n{self.text}"


class PdfSkill:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = chromadb.PersistentClient(path=str(self.settings.chroma_dir))

    def _collection(self):
        return self.client.get_or_create_collection(
            name=self.settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.settings.collection_name)
        except Exception:
            return

    def ingest(
        self,
        docs_dir: str | Path | None = None,
        *,
        reset: bool = False,
        chunk_size: int = 1200,
        chunk_overlap: int = 180,
        batch_size: int = 64,
    ) -> IngestStats:
        docs_path = Path(docs_dir).resolve() if docs_dir else self.settings.docs_dir.resolve()
        if not docs_path.exists():
            raise FileNotFoundError(f"PDF docs directory does not exist: {docs_path}")

        if reset:
            self.reset()

        collection = self._collection()
        embeddings = build_embeddings(self.settings)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

        pdf_paths = sorted(docs_path.rglob("*.pdf"))
        page_count = 0
        chunk_count = 0

        batch_ids: list[str] = []
        batch_texts: list[str] = []
        batch_metadata: list[dict[str, Any]] = []

        for pdf_path in pdf_paths:
            for page_number, page_text in self._extract_pdf_pages(pdf_path):
                page_count += 1
                chunks = splitter.split_text(page_text)
                for chunk_index, chunk in enumerate(chunks):
                    normalized = chunk.strip()
                    if not normalized:
                        continue
                    metadata = {
                        "source": str(pdf_path.relative_to(docs_path)),
                        "file_name": pdf_path.name,
                        "page": page_number,
                        "chunk_index": chunk_index,
                    }
                    batch_ids.append(self._chunk_id(pdf_path, page_number, chunk_index, normalized))
                    batch_texts.append(normalized)
                    batch_metadata.append(metadata)
                    chunk_count += 1

                    if len(batch_texts) >= batch_size:
                        self._upsert_batch(collection, embeddings, batch_ids, batch_texts, batch_metadata)
                        batch_ids, batch_texts, batch_metadata = [], [], []

        if batch_texts:
            self._upsert_batch(collection, embeddings, batch_ids, batch_texts, batch_metadata)

        return IngestStats(
            pdf_count=len(pdf_paths),
            page_count=page_count,
            chunk_count=chunk_count,
            collection_name=self.settings.collection_name,
            chroma_dir=self.settings.chroma_dir,
        )

    def query(self, question: str, *, k: int = 5) -> list[RagHit]:
        if not question.strip():
            return []

        collection = self._collection()
        embeddings = build_embeddings(self.settings)
        query_embedding = embeddings.embed_query(question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, min(k, 20)),
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        hits: list[RagHit] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            metadata = metadata or {}
            hits.append(
                RagHit(
                    text=document,
                    source=str(metadata.get("source", "unknown")),
                    page=int(metadata.get("page", 0)),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    distance=float(distance) if distance is not None else None,
                )
            )
        return hits

    def _extract_pdf_pages(self, pdf_path: Path) -> Iterable[tuple[int, str]]:
        reader = PdfReader(str(pdf_path))
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                yield index, text

    def _upsert_batch(
        self,
        collection,
        embeddings,
        ids: list[str],
        texts: list[str],
        metadata: list[dict[str, Any]],
    ) -> None:
        vectors = embeddings.embed_documents(texts)
        collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadata)

    def _chunk_id(self, pdf_path: Path, page: int, chunk_index: int, text: str) -> str:
        digest = hashlib.sha256(f"{pdf_path}|{page}|{chunk_index}|{text}".encode("utf-8")).hexdigest()
        return digest[:32]
