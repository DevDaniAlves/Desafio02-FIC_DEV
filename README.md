# Arquivo de atendimentos

Desafio 02 do FIC DEV (Python para IA). O sistema lê fichas em PDF, valida, grava no SQLite, indexa no Chroma e responde perguntas pela API e pelo Streamlit.

Há dois modos: `ktop` (caso ou semelhança, só o top-k) e `completo` (frequência e totais na base, pelo campo Problema). Três consultas grátis por IP; depois, login e planos ilustrativos — sem cobrança real.

## Funcionalidades

- Extração direta de PDFs com `pypdf`;
- Encaminhamento de páginas sem texto para Tesseract;
- Regex, normalização, validação e deduplicação;
- SQLite e SQLAlchemy;
- Limpeza textual com NLTK (tokenização, stopwords em português e stemming RSLP);
- Pandas e NumPy na análise (limpeza, filtros, agrupamentos, média/mediana/desvio-padrão), CSV (utf-8-sig), `indicadores.json` e cinco gráficos PNG;
- Chunks com metadados rastreáveis;
- Embeddings locais com `sentence-transformers`;
- Coleção persistente no ChromaDB;
- Recuperação local e RAG opcional com LangChain/OpenAI;
- FastAPI, Streamlit e testes com Pytest.

## Preparação

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

No Windows, use sempre o Python do `.venv` (`.\.venv\Scripts\python.exe -m …`). O `python` global não tem Streamlit nem Chroma.

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
python -m uvicorn src.api:app --reload
python -m streamlit run src/app_streamlit.py
```

A tela é o Streamlit em `http://127.0.0.1:8501`. A porta `8000` é a API (JSON). Teste o `POST /ask` em `http://127.0.0.1:8000/docs`.

A API expõe `GET /health`, `GET /` e `POST /ask` (`pergunta`, `top_k`, `categoria` opcional). Índice vazio devolve HTTP 200 com `modo=sem_fontes`. Falha ao abrir o Chroma ou o modelo de embedding devolve HTTP 503.

O Streamlit consulta essa API: mostra se ela está no ar, filtra por categoria oficial e lista cada fonte como protocolo (`AT-XXX`), documento, página e trecho. Sem fontes, pede para processar e indexar os PDFs.

Há 3 consultas grátis por IP, sem cadastro. Depois é preciso e-mail e senha (e-mail único) e um plano ilustrativo: 7/dia (R$ 49), 15/dia (R$ 99) ou ilimitado (R$ 199). Cartão valida 16 dígitos, validade futura e CVV; PIX mostra um QR estático e o botão “Já paguei”. Não há cobrança real.

A justificativa dos dois modos de consulta e dos planos está em [docs/consultas-e-planos.md](docs/consultas-e-planos.md). O material de apresentação (correções do entregue + diferenciais) está em [pitch/](pitch/).

Antes de buscar, o modelo classifica a pergunta: `ktop` usa só os `top_k` trechos mais semelhantes; `completo` (frequência, totais) conta a base inteira no SQLite pelo campo Problema e na tela lista só o top-k.

Testes:

```bash
pytest
```

## Modo sem chave de modelo

Os embeddings são locais (`sentence-transformers`, MiniLM multilingual). Sem `OPENAI_API_KEY` e sem `GEMINI_API_KEY`, o sistema recupera e apresenta os chunks mais semelhantes com suas fontes. Com uma das chaves, LangChain gera a síntese (`OPENAI_MODEL` ou `GEMINI_MODEL`). Se as duas estiverem preenchidas, `AI_PROVIDER` escolhe `openai` ou `gemini`. Se o índice estiver vazio ou a busca não devolver trechos, a resposta informa que não há informação suficiente e o modelo não é chamado.

## Saídas geradas pelo pipeline

Após `python -m src.main`, o diretório `output/` contém:

- `atendimentos_processados.csv` — base tratada completa (UTF-8 com BOM, adequada ao Excel);
- `indicadores.json` — total de documentos; totais de válidos, incompletos, inválidos e duplicados; média, mediana e desvio-padrão do tempo; recortes por categoria, status, município e método de extração; percentual de OCR;
- `processamento.log` — andamento, falhas de OCR/CEP e cada registro incompleto, inválido ou duplicado;
- cinco gráficos em `graficos/` (PNG, barras horizontais com título, eixo e valores):
  - `atendimentos_categoria.png` — quantidade por categoria (registros válidos);
  - `tempo_medio_categoria.png` — tempo médio, em minutos, por categoria (registros válidos);
  - `atendimentos_status.png` — quantidade por status (registros válidos);
  - `atendimentos_municipio.png` — quantidade por município (registros válidos);
  - `atendimentos_metodo.png` — quantidade por método de extração (base completa).

## Decisões

- Registros repetidos pelo protocolo são classificados como duplicados e não são reinseridos.
- O texto original é preservado; a versão limpa serve para recuperação.
- Erros de OCR são persistidos e não interrompem os outros arquivos.
- A consulta de CEP complementa município e UF no pipeline. Falha da API ou CEP inexistente não interrompe o processamento; chaves e tokens não são registrados em log.
- O CSV `output/atendimentos_processados.csv` traz a base tratada completa (válidos, incompletos, inválidos e duplicados), com classificação e motivos.
- Os recortes analíticos do JSON e os gráficos de categoria, status, município e tempo médio usam só registros válidos. Totais de documentos/classificação, recorte por método de extração e percentual de OCR usam a base inteira.
- Sempre são gerados CSV, `indicadores.json` e os cinco PNGs, inclusive quando não há dados — nesse caso o gráfico exibe “Sem dados para exibir”.
- Cada registro leva o método da página (`extracao_direta` ou `ocr`). `ocr_pendente` é normalizado para `ocr`, para a primeira execução e a reutilização do banco permanecerem comparáveis. O percentual de OCR inclui `ocr`, `misto` e `ocr_pendente`.
- Problemas de validação e duplicidade são gravados em `output/processamento.log`; duplicatas persistidas também geram `warning` no momento da ingestão.

## Chunking e metadados

A divisão usa janela deslizante por **caracteres** (não por tokens), configurável em `embeddings.tamanho_chunk` e `embeddings.sobreposicao`:

- **Tamanho 500**: cabe na janela típica do MiniLM multilingual (~128 tokens) e evita truncar o embedding.
- **Sobreposição 80** (~16%): o final de um trecho reaparece no início do próximo para não perder o contexto na fronteira. A unidade da sobreposição é o caractere, então o trecho seguinte pode começar no meio de uma palavra.
- **Quebra em espaço**: se o limite cair no meio de uma palavra, o corte recua ao último espaço da janela. Palavras maiores que o tamanho ainda são cortadas.
- Cada chunk recebe um identificador único (chave primária), um índice dentro do atendimento e metadados com documento, página, protocolo e categoria. Esses campos vão para o SQLite e para o ChromaDB; a consulta devolve o id do trecho junto da fonte.
- A indexação espelha o banco relacional e remove ids órfãos da coleção vetorial.

## Limitações

- O NLTK aplica stemming RSLP, não lematização plena.
- A extração por regex vale para o formulário deste desafio; outro layout pede outros padrões.
- OCR de PDF digitalizado no Windows exige Tesseract no PATH (ou `TESSERACT_CMD`).
- O pagamento dos planos é ilustrativo.

Justificativa dos modos e dos planos: [docs/consultas-e-planos.md](docs/consultas-e-planos.md). Material de apresentação: [pitch/](pitch/).
