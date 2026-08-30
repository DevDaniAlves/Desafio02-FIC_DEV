# Prompt para o Gemini gerar os slides (~5 min)

Copie o bloco abaixo e cole no Gemini.

---

Você é redator de pitch técnico. Crie uma apresentação em português do Brasil, Desafio 02 · FIC DEV · Python para IA. Banca / docentes / colegas. Tom honesto, sem hype, sem emoji, sem jargão vazio. Primeira pessoa do plural.

## Tempo e formato

- Duração total: 5 minutos. **9 slides** (pode ser 8; máximo 10).
- 30 a 50 segundos por slide. Título curto + 3 a 5 bullets. Máximo 16 palavras por bullet.
- Entregue: (1) roteiro slide a slide com tempo sugerido e nota do apresentador (2–3 frases); (2) texto pronto para colar.
- Não use a palavra “Init”. Diga “solução de referência” ou “código raiz”.
- Nos slides do Mato Grosso, fonte no rodapé (veículo + mês/ano). Não invente número.

## O que NÃO pode aparecer como “erro que corrigimos”

Isso NÃO estava no código raiz. Foi efeito colateral do que nós adicionamos depois. Se citar, cite só como evolução nossa, nunca como falha do entregue:

- “o modo completo listava 64 fichas”
- classificador ktop/completo, “mais demorado” virando frequência
- Gemini `2.0-flash`, JSON `type/text/signature` do LangChain
- tela branca na porta 8000 (é JSON da API, não bug)
- `chromadb` / `streamlit` “não reconhecido” (ambiente / venv, não o ZIP)

## Roteiro (nessa ordem)

### 1. Capa (~25 s)

Título: “Arquivo de atendimentos: do pipeline ao produto”. Subtítulo: Desafio 02 · FIC DEV. Sem nomes inventados.

### 2. O projeto inicial (~40 s)

O código raiz já era um pipeline completo, não um esboço:

- PDF com `pypdf`; página sem texto → OCR (Tesseract)
- regex, validação, deduplicação, SQLite
- analytics (CSV, indicadores, 3 gráficos)
- embeddings MiniLM + Chroma + RAG LangChain/OpenAI
- FastAPI (`/health`, `/ask`) e Streamlit mínimo

Nota: partimos do entregue. Não reescrevemos o desafio.

### 3. O que o código raiz não resolvia (~50 s)

Só estes pontos — todos lidos no ZIP `solucao_referencia_desafio_final_python_ia`:

1. **`/ask` trata qualquer falha como 503.** `src/api.py` envolve a consulta num `except Exception` e devolve 503. Índice Chroma vazio, embedding que não abre ou coleção ainda não criada: o cliente vê “Consulta indisponível”, não um “ainda não há fontes”.
2. **O RAG chama o modelo mesmo sem fontes.** Em `src/rag.py`, se existe `OPENAI_API_KEY`, `answer()` monta o contexto e invoca o ChatOpenAI. Lista vazia → contexto vazio → gasta cota e o modelo improvisa ou recusa. O código raiz não tem o guarda “sem fontes, não chama o LLM”.
3. **A pergunta que a própria UI sugere não cabe no produto.** O placeholder do Streamlit é “Quais problemas de instalação do Python aparecem com maior frequência?”. O sistema só devolve o `top_k` (padrão 5) e o prompt manda recusar se “não estiver sustentado”. Frequência é censo da base; o raiz só faz busca semântica. Resultado típico: “não há informação suficiente” mesmo com AT-XXX no contexto — ou um ranking inventado em cima de 5 trechos.

Opcional, uma linha no rodapé (não merecem slide próprio): OCR no Windows não está no README (só `apt` no Ubuntu); cliente de CEP existe e não entra no pipeline (`municipio`/`uf` ficam vazios — o próprio README chama isso de decisão).

### 4. O que mudamos em cima do raiz (~40 s)

- Índice vazio: HTTP 200 e `modo=sem_fontes`; o modelo não é chamado.
- Prompt do caso pontual: usar o campo Problema dos protocolos recuperados.
- Dois modos (diferencial, não “correção”): `ktop` = caso/semelhança no top-k; `completo` = frequência na base SQLite, pelo texto exato do Problema.
- Interface: health da API, filtro de categoria, fonte como AT-XXX.
- Síntese também com Gemini (`AI_PROVIDER`), sem depender só da OpenAI.

### 5. Mato Grosso investiu (~40 s)

Dois fatos, não a lista toda:

- Fev/2026: ~R$ 36 mi reprogramados, em especial MTI (R$ 20 mi TIC + R$ 14,2 mi sede). Fonte: Muvuca Popular, fev/2026. São remanejamentos da LOA, não despesa nova.
- Jun–ago/2026: Parque Tecnológico em Várzea Grande (~R$ 25 mi); MTI anuncia 1º data center Tier 3 e CEIA. Fontes: G1 MT, jun/2026; O Cuiabá, ago/2026.

### 6. O caixa também trava — e a ponte (~45 s)

- Nov/2025: contingenciamento de R$ 826,3 mi. Educação R$ 100 mi; Fapemat ~R$ 12,7 mi. Fonte: G1 MT / Primeira Página, nov/2025.
- Não diga “o governo cortou a tecnologia”. Ele contingenciou E reprogramou para a MTI. O ponto é sustentabilidade: tijolo e data center avançam; dado e produto travam quando a arrecadação cai.

Ponte (obrigatória neste slide ou no próximo): o Estado já produz o registro de atendimento. Um pipeline que só “busca trecho” não vira política nem receita. Separar caso (ktop) de censo (completo) e cobrar o censo é uma forma de financiar a camada de dado sem vender a pessoa.

### 7. A ideia (~45 s)

- `ktop`: o que aconteceu no AT-003; uso de balcão. Ex.: “O que aconteceu no protocolo AT-003 e como foi resolvido?”
- `completo`: o que mais aparece, quantos. Conta a base; não pede ao modelo para reagrupar. Ex.: “Quais problemas de instalação do Python aparecem com maior frequência?”
- Cobra-se indicador (tipo, frequência, tempo médio). Nome, e-mail e CEP não entram na mercadoria. Cadastro é só cota.

### 8. Planos (protótipo) (~35 s)

- 3 consultas grátis por IP, sem cadastro.
- Depois e-mail + senha. 7/dia R$ 49 · 15/dia R$ 99 · ilimitado R$ 199.
- Cartão e PIX só ilustram o fluxo. Sem cobrança real.

### 9. Conclusão (~35 s)

- Do raiz: pipeline de pé, mas `/ask` quebrava sem índice, o LLM rodava sem fonte, e a pergunta de frequência da própria tela não tinha caminho.
- De nós: produto com dois modos e tese de financiamento.
- Frase-síntese (mantenha o sentido): “Tijolo e data center o Estado já está comprando. Falta transformar o atendimento em número que se venda sem vender a pessoa.”
- Pode fechar neste slide (obrigado + perguntas). Sem QR nem URL inventada.

## O que não fazer

- Não prometa contrato com o governo nem receita captada.
- Não trate diferencial nosso como bug do ZIP.
- Não exponha chave, e-mail real ou ficha identificável.
- Não invente métrica de acurácia ou número de usuários.

---
