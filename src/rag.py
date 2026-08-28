"""Recuperação local e resposta RAG opcional com OpenAI/LangChain."""
from __future__ import annotations
import os

SYSTEM="Responda somente com base no contexto. Se a resposta não estiver sustentada, diga que não há informação suficiente. Cite os protocolos utilizados."

def local_answer(question:str,sources:list[dict]) -> dict:
    return {"resposta":"Modo local: foram recuperados os trechos mais semelhantes. Configure OPENAI_API_KEY para gerar uma síntese.","modo":"recuperacao_local","pergunta":question,"fontes":sources}

def answer(question:str,sources:list[dict],model:str="gpt-4.1-mini") -> dict:
    if not os.getenv("OPENAI_API_KEY"): return local_answer(question,sources)
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        prompt=ChatPromptTemplate.from_messages([("system",SYSTEM),("human","Pergunta: {question}\n\nContexto:\n{context}")])
        chain=prompt|ChatOpenAI(model=model,temperature=0)
        context="\n\n".join(f"[Fonte {s.get('protocolo')} p.{s.get('pagina')}] {s.get('conteudo')}" for s in sources)
        response=chain.invoke({"question":question,"context":context})
        return {"resposta":response.content,"modo":"rag","fontes":sources}
    except Exception as exc:
        result=local_answer(question,sources); result["aviso"]=f"Falha no modelo: {type(exc).__name__}"; return result
