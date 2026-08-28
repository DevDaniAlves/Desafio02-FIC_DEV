"""API HTTP de consulta."""
from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .config import load_config
from .indexer import semantic_query
from .rag import answer

app=FastAPI(title="Atendimentos FIC_DEV",version="1.0.0")
cfg=load_config()

class AskRequest(BaseModel):
    pergunta:str=Field(min_length=3,max_length=500)
    top_k:int=Field(default=5,ge=1,le=20)
    categoria:str|None=None

@app.get("/health")
def health(): return {"status":"ok","modo":"rag" if os.getenv("OPENAI_API_KEY") else "recuperacao_local"}

@app.post("/ask")
def ask(payload:AskRequest):
    try:
        sources=semantic_query(cfg,payload.pergunta,payload.top_k,payload.categoria)
        return answer(payload.pergunta,sources,os.getenv("OPENAI_MODEL","gpt-4.1-mini"))
    except Exception as exc:
        raise HTTPException(status_code=503,detail=f"Consulta indisponível: {type(exc).__name__}") from exc
