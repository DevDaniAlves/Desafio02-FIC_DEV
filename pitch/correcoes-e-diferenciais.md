# Correções do código raiz e diferenciais

Fonte do raiz: ZIP `solucao_referencia_desafio_final_python_ia` (`src/api.py`, `src/rag.py`, `src/app_streamlit.py`).

## O que não é erro do entregue

Não use no pitch como “bug que o código raiz tinha”:

| Item | Por quê |
|---|---|
| Modo completo listava 64 fichas | O raiz não tem modo `completo`. Isso surgiu no nosso código. |
| Classificador “mais demorado” → frequência | Também é nosso. |
| Gemini 2.0 Flash / JSON `type/text/signature` | O raiz só fala OpenAI (`gpt-4.1-mini`). |
| Tela branca em `:8000` | A API devolve JSON. Não é defeito. |
| `chromadb` / `streamlit` no terminal | Pacote no `requirements.txt`; falta ativar o `.venv`. |

## Falhas do produto original

| Onde no ZIP | O que acontecia | O que fizemos |
|---|---|---|
| `src/api.py` — `except Exception` → 503 | Qualquer falha da consulta (índice vazio, Chroma, embedding) vira “Consulta indisponível” | Índice vazio: HTTP 200 e `modo=sem_fontes`. 503 só se o índice/embedding realmente falhar |
| `src/rag.py` — `answer()` | Com `OPENAI_API_KEY`, chama o modelo mesmo se `sources` estiver vazio | Sem fontes, o modelo não é chamado |
| Mesmo `rag.py` + placeholder do Streamlit | A UI sugere pergunta de **frequência**. O raiz só devolve `top_k` e o system prompt manda recusar se “não estiver sustentado” | Censo no SQLite (`completo`); caso pontual no top-k (`ktop`) |

## Limitações possíveis do raiz (não vender como bug corrigido)

- README de OCR só cita Ubuntu (`poppler` + Tesseract). No Windows o digitalizado pede Tesseract no PATH / `TESSERACT_CMD`.
- `cep_client.py` existe; o pipeline grava `municipio` e `uf` como `None`. O README do ZIP diz que isso é decisão, não omissão acidental.
- `nltk` está no `requirements.txt` e não é usado: a limpeza é a lematização leve de `text_processor.py`.
- CSV em `utf-8` (sem BOM): o Excel no Windows pode abrir com acento quebrado.

## Diferenciais (além do enunciado / do ZIP)

| Diferencial | Papel |
|---|---|
| Gemini + `AI_PROVIDER` | Síntese sem depender só da OpenAI |
| `ktop` / `completo` | Caso operacional vs. censo; a pergunta da UI original passa a ter caminho |
| Contagem no código (campo Problema) | Mesma pergunta, mesmo ranking |
| 3 fichas grátis / IP, login, planos | Financiar indicador, não PII |
| Cartão e PIX ilustrativos | Fluxo de assinatura, sem cobrança real |
| Balcão com health, categoria e AT-XXX | Interface usável em cima do Streamlit mínimo do raiz |

Tese dos modos e dos planos: [consultas-e-planos.md](consultas-e-planos.md).
