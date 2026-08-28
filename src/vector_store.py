"""Persistência e consulta dos chunks no ChromaDB."""
from __future__ import annotations
from pathlib import Path

class ChromaStore:
    def __init__(self,directory:str|Path,collection:str):
        import chromadb
        self.client=chromadb.PersistentClient(path=str(directory))
        self.collection=self.client.get_or_create_collection(collection,metadata={"hnsw:space":"cosine"})
    def upsert(self,ids:list[str],documents:list[str],metadatas:list[dict],embeddings:list[list[float]]) -> None:
        self.collection.upsert(ids=ids,documents=documents,metadatas=metadatas,embeddings=embeddings)
    def query(self,embedding:list[float],top_k:int=5,where:dict|None=None) -> list[dict]:
        result=self.collection.query(query_embeddings=[embedding],n_results=top_k,where=where)
        rows=[]
        for i,doc in enumerate((result.get("documents") or [[]])[0]):
            rows.append({"conteudo":doc,"metadata":result["metadatas"][0][i],"distancia":result["distances"][0][i],"similaridade":1-float(result["distances"][0][i])})
        return rows
