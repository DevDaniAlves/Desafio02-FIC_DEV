# Solução de referência - desafio final Python para IA

Esta implementação demonstra uma forma de resolver o desafio. Ela não é a única solução correta e não deve ser fornecida aos discentes antes da conclusão da atividade.

## Funcionalidades

- Extração direta de PDFs com `pypdf`;
- Encaminhamento de páginas sem texto para Tesseract;
- Regex, normalização, validação e deduplicação;
- SQLite e SQLAlchemy;
- Limpeza textual, stopwords e lematização leve;
- Pandas, NumPy, CSV, JSON e três gráficos;
- Chunks com metadados rastreáveis;
- Embeddings locais com `sentence-transformers`;
- Coleção persistente no ChromaDB;
- Recuperação local e RAG opcional com LangChain/OpenAI;
- FastAPI, Streamlit e testes com Pytest.

## Preparação

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

No Ubuntu, instale também Poppler e Tesseract:

```bash
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-por
```

## Execução

Pipeline sem indexação vetorial:

```bash
python -m src.main
```

Pipeline e indexação:

```bash
python -m src.main --indexar
```

Consulta por linha de comando:

```bash
python -m src.main --pergunta "Quais problemas mencionam instalação do Python?"
```

API e interface:

```bash
uvicorn src.api:app --reload
streamlit run src/app_streamlit.py
```

Testes:

```bash
pytest
```

## Modo sem chave da OpenAI

Os embeddings são locais. Sem `OPENAI_API_KEY`, o sistema recupera e apresenta os chunks mais semelhantes com suas fontes. Com a chave configurada, LangChain e o modelo definido em `OPENAI_MODEL` produzem uma síntese fundamentada no contexto.

## Decisões de referência

- Registros repetidos pelo protocolo são classificados como duplicados e não são reinseridos.
- O texto original é preservado; a versão limpa serve para recuperação.
- O chunk utiliza 500 caracteres e sobreposição de 80, configuráveis.
- Erros de OCR são persistidos e não interrompem os outros arquivos.
- A API de CEP foi isolada em um cliente tolerante a falhas. Sua chamada pode ser incorporada ao pipeline conforme a política de rede da turma.

## Limitações intencionais

- A lematização leve evita exigir o download de um modelo grande; uma solução com spaCy também é válida.
- A extração por regex foi ajustada ao formulário fornecido. Layouts diferentes exigem novos padrões.
- O histórico Git solicitado na atividade não pode ser representado dentro de um ZIP; o professor deve demonstrá-lo em um repositório de referência ou avaliar o histórico do discente separadamente.

## Uso de IA nesta referência

A solução foi estruturada como material pedagógico e deve ser revisada pelo professor antes da aplicação. O discente continua responsável por explicar e modificar o próprio código durante a verificação de aprendizagem.
