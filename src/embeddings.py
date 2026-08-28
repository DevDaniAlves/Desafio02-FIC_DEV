"""Geração de embeddings e comparação por cosseno."""
from __future__ import annotations
import numpy as np

class EmbeddingService:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        self.model=SentenceTransformer(model_name)
    def encode(self,texts:list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts,normalize_embeddings=True),dtype=float)

def cosine_scores(query_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query=np.asarray(query_vector,dtype=float).reshape(-1)
    data=np.asarray(matrix,dtype=float)
    qn=np.linalg.norm(query); dn=np.linalg.norm(data,axis=1)
    return (data@query)/np.where(dn*qn==0,1,dn*qn)

def top_k(query:str,texts:list[str],service:EmbeddingService,k:int=5) -> list[tuple[int,float]]:
    if not texts: return []
    vectors=service.encode([query,*texts]); scores=cosine_scores(vectors[0],vectors[1:])
    return [(int(i),float(scores[i])) for i in np.argsort(scores)[::-1][:k]]
