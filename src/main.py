"""Entrada de linha de comando."""
from __future__ import annotations
import argparse
from .config import load_config
from .pipeline import process_all
from .indexer import build_index, semantic_query
from .rag import answer

def main():
    parser=argparse.ArgumentParser(description="Processa e consulta os atendimentos")
    
    parser.add_argument("--indexar",action="store_true"); parser.add_argument("--pergunta"); parser.add_argument("--top-k",type=int,default=5)
    
    args=parser.parse_args(); cfg=load_config()
    
    df=process_all(cfg); print(f"Registros encontrados: {len(df)}")
    
    if args.indexar: print(f"Chunks indexados: {build_index(cfg)}")
    
    if args.pergunta:
        sources=semantic_query(cfg,args.pergunta,args.top_k); print(answer(args.pergunta,sources))

if __name__=="__main__": main()
