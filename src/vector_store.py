"""Persistência e consulta dos chunks no ChromaDB (RF12)."""
from __future__ import annotations
from pathlib import Path


class ChromaStore:
    def __init__(self, directory: str | Path, collection: str):
        import chromadb

        self.client = chromadb.PersistentClient(path=str(directory))
        self.collection_name = collection
        self.collection = self.client.get_or_create_collection(
            collection, metadata={"hnsw:space": "cosine"}
        )

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        self.collection.upsert(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
        )

    def sync(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Espelha o SQLite: atualiza os ids atuais e remove órfãos."""
        existing = set(self.collection.get()["ids"] or [])
        keep = set(ids)
        stale = list(existing - keep)
        if stale:
            self.collection.delete(ids=stale)
        if ids:
            self.upsert(ids, documents, metadatas, embeddings)

    def query(
        self, embedding: list[float], top_k: int = 5, where: dict | None = None
    ) -> list[dict]:
        count = self.collection.count()
        if count == 0:
            return []
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, count),
            where=where,
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        rows = []
        for i, doc in enumerate(documents):
            rows.append(
                {
                    "id": ids[i] if i < len(ids) else None,
                    "conteudo": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distancia": distances[i],
                    "similaridade": 1 - float(distances[i]),
                }
            )
        return rows
