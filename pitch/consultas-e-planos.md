# Por que existem ktop, completo e planos

O arquivo de atendimentos serve a dois usos diferentes. Misturá-los na mesma busca gasta cota, mistura recorte com censo e entrega a resposta errada (foi o caso de “mais demorado” cair numa lista de frequência).

## ktop

Pergunta de **caso ou semelhança**: o que aconteceu no AT-003, tickets de *pip não reconhecido*, o problema mais demorado *neste recorte*.

O sistema pega só os `top_k` trechos mais parecidos e o modelo responde com eles. Serve a quem opera o balcão — suporte, pesquisa interna, um protocolo pontual.

Exemplo: *O que aconteceu no protocolo AT-003 e como foi resolvido?*

## completo

Pergunta de **censo**: o que mais aparece, quantos, totais. A conta usa a base inteira e o texto exato do campo Problema, sem o modelo reagrupar. A tela ainda mostra só o top-k, para não listar 64 fichas.

Isso é o produto que interessa a quem não precisa da ficha: o mapa de carências (instalação, senha, venv, rede), não o e-mail do solicitante.

Exemplo: *Quais problemas de instalação do Python aparecem com maior frequência?*

## Por que planos

Estados e órgãos públicos costumam operar com orçamento abaixo do necessário. Pesquisa, dados e modernização de atendimento ficam no fim da fila porque o resultado não é imediato nem fácil de mostrar.

Ao mesmo tempo, informação agregada é cara: empresas e parceiros tecnológicos pagam para saber *quais problemas a sociedade está enfrentando*, não para ler o nome de um aluno.

Os planos (3 fichas grátis por IP; 7/dia, 15/dia ou ilimitado) são a forma de **financiar a infraestrutura** vendendo esse retrato, dentro das quatro linhas da LGPD:

- o que se cobra é indicador (tipo de problema, frequência, tempo médio), não dado pessoal;
- cadastro na ferramenta é só e-mail e senha para controlar cota — não entra na mercadoria;
- a ficha completa (nome, e-mail, CEP) fica no modo operacional (ktop), não no produto vendido.

O pagamento no protótipo é ilustrativo. A tese é a mesma: o Estado deixa de ser só consumidor de software e passa a ter uma receita ligada ao bem que já produz — o registro do atendimento — sem abrir a identidade de quem foi atendido.

## O que não se vende

Não se vende a linha do CSV com solicitante e e-mail. Não se vende recorte que permita reidentificar alguém. Se a pergunta pede um protocolo específico, isso é ktop, uso interno ou autorizado — não o pacote comercial.
