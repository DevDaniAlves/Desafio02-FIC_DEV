"""Entrada de linha de comando."""
from __future__ import annotations
import argparse
from pathlib import Path
from .config import load_config
from .pipeline import process_all
from .indexer import build_index, semantic_query
from .rag import answer
from .database import (
    create_session_factory,
    session_scope,
    resolve_db_url,
    delete_by_protocol,
)


def main():
    parser = argparse.ArgumentParser(description="Processa e consulta os atendimentos")
    parser.add_argument("--indexar", action="store_true")
    parser.add_argument("--pergunta")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--recriar-banco",
        action="store_true",
        help="Apaga e recria as tabelas SQLite antes de processar",
    )
    parser.add_argument(
        "--excluir-protocolo",
        metavar="PROTOCOLO",
        help="Remove o atendimento (e os chunks) do protocolo informado e encerra",
    )
    args = parser.parse_args()
    cfg = load_config()

    if args.excluir_protocolo:
        factory = create_session_factory(
            resolve_db_url(Path(cfg["_root"]), cfg["banco"]["url"])
        )
        with session_scope(factory) as session:
            removed = delete_by_protocol(session, args.excluir_protocolo)
        print(
            f"Protocolo {args.excluir_protocolo} excluído"
            if removed
            else f"Protocolo {args.excluir_protocolo} não encontrado"
        )
        return

    df = process_all(cfg, recreate=args.recriar_banco)
    print(f"Registros encontrados: {len(df)}")
    if args.indexar:
        print(f"Chunks indexados: {build_index(cfg)}")
    if args.pergunta:
        sources = semantic_query(cfg, args.pergunta, args.top_k)
        print(answer(args.pergunta, sources))


if __name__ == "__main__":
    main()
