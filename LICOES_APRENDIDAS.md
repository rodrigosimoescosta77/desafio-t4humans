# Lições Aprendidas — Banco Ágil

## 1. Cota da API Google Esgotada
**Problema:** Chave `GOOGLE_API_KEY` atingiu o limite gratuito (`RESOURCE_EXHAUSTED`).  
**Solução:** Criar novo projeto no Google AI Studio para obter uma chave nova e colar crédito para usar a chave.

---

## 2. Modelos de LLM Descontinuados (Groq)
**Problema:** Modelos `llama3-groq-70b`, `mixtral-8x7b` e `llama-3.1-70b` foram removidos da Groq sem aviso prévio.  
**Solução:** Migrar para Gemini 2.5 Flash via `langchain-google-genai`.

---

## 3. LLM Recusando Chamadas de Ferramentas Financeiras
**Problema:** O Gemini 2.5 Flash recusava chamar `solicitar_aumento_limite` por treinamento de segurança — respondia "não consigo atender essa solicitação".  
**Solução:** A lógica de decisão foi movida para Python (chamada direta à ferramenta); o LLM ficou responsável apenas por formatar a resposta ao cliente.

---

## 4. Roteamento Incorreto entre Agentes
**Problema:** O grafo LangGraph sempre iniciava no nó `triagem`, tornando os agentes de crédito, câmbio e entrevista inalcançáveis.  
**Solução:** Substituir `set_entry_point("triagem")` por `add_conditional_edges(START, router_principal)`, roteando dinamicamente com base no campo `agente_atual` do estado.

---

## 5. Campos de Estado `None` Quebrando Formatação
**Problema:** Campos como `limite_credito` inicializados como `None` causavam erro `NoneType.__format__` ao usar f-strings com `:,.2f`.  
**Solução:** Usar o padrão `state.get('campo') or 0` em vez de `state.get('campo', 0)`, que não substitui `None` pelo default.

---

## 6. Falso Positivo na Detecção de Intenção
**Problema:** A frase "entrevista de **crédito**" ativava a keyword `crédito` antes de `entrevista`, impedindo o roteamento para o agente correto.  
**Solução:** Ao estar no agente de crédito, checar keywords de entrevista diretamente, sem passar pelo detector geral de intenção.

---

## 7. Contagem de Tentativas de Autenticação Sem Contexto
**Problema:** O agente de triagem não sabia quantas tentativas falhas já haviam ocorrido, podendo encerrar antes ou depois do limite de 3.  
**Solução:** Injetar o contador `tentativas_auth` no system prompt do agente, com instrução explícita de encerrar ao atingir o limite.

---

## 8. LLM Inventando Fluxo de Agendamento de Entrevista
**Problema:** O agente de crédito, ao oferecer a entrevista, inventava um processo de agendamento inexistente (telefones, horários, etc.).  
**Solução:** Simplificar o prompt para que o agente faça apenas uma pergunta direta ("Deseja fazer a entrevista?") e delegar o redirecionamento ao código.

---

## 9. UX — Texto Ilegível no Chat
**Problema:** Mensagens do usuário exibiam texto azul (`#0077b6`) sobre fundo azul escuro.  
**Solução:** Alterar a cor do texto das mensagens do usuário para branco (`#ffffff`).

---

## 10. Fundo Branco Aparecendo Dentro das Bolhas de Mensagem
**Problema:** O Streamlit envolve o conteúdo renderizado via `unsafe_allow_html` em elementos filhos (`<p>`, `<span>`, `<div>`) com fundo branco padrão, que vazavam para dentro das bolhas estilizadas.  
**Solução:** Adicionar regra CSS com seletor wildcard: `.msg-agent *, .msg-user * { background: transparent !important; color: inherit !important; }` para forçar herança em todos os descendentes.

---

## 11. Símbolo `$` Interpretado como LaTeX pelo Streamlit
**Problema:** O Streamlit interpreta `$valor$` como delimitador de fórmula LaTeX. Respostas do LLM contendo "R$ 25.000,00" perdiam o `$` e o trecho era renderizado em fonte matemática.  
**Solução:** Escapar o símbolo antes de injetar no HTML: `conteudo = msg['content'].replace('$', '&#36;')`.

---

## 12. Aceitação de Entrevista Não Detectada por Texto Livre
**Problema:** Após o agente de crédito oferecer a entrevista, respostas afirmativas do cliente como "tenho interesse" ou "pode ser" não eram reconhecidas, pois não correspondiam às palavras-chave de entrevista. O agente tentava "agendar" algo inexistente.  
**Solução:** Introduzir o campo `entrevista_ofertada` no estado. Quando `True`, qualquer palavra afirmativa ("sim", "quero", "aceito", "interesse", etc.) roteia para o agente de entrevista. Na interface, substituir o campo de texto por botões **"Sim, quero participar"** / **"Não, obrigado"** para eliminar ambiguidade.

---

## 13. Data de Nascimento com Dia e Mês Invertidos no CSV
**Problema:** O cliente Rodrigo Simões Costa não conseguia autenticar mesmo fornecendo os dados corretos. João Silva autenticava normalmente.  
**Causa raiz:** A data no CSV estava como `1977-04-08` (8 de abril), mas o cliente nasceu em 4 de agosto (`1977-08-04`). O LLM converte corretamente `04/08/1977` (DD/MM/AAAA) para `1977-08-04`, que não batia com o CSV. João Silva não apresentava o problema pois seu dia (15) é maior que 12, tornando a conversão DD/MM inequívoca — o que mascarava o bug.  
**Solução:** Corrigir o valor no CSV para `1977-08-04`. Atenção ao popular a base: datas no formato YYYY-MM-DD devem seguir a ordem ano-mês-dia, não ano-dia-mês.

---

## 14. Sistema Aceitava Qualquer Número com 11 Dígitos como CPF
**Problema:** A validação de CPF verificava apenas a quantidade de dígitos. Qualquer sequência de 11 números (ex: `12345678901`, `45611555555555555`) era aceita e avançava para a etapa de data de nascimento.  
**Solução:** Implementar o algoritmo oficial de validação de CPF com dois dígitos verificadores e rejeição de sequências repetidas (ex: `111.111.111-11`). A ferramenta `validar_cpf` foi criada como `@tool` separado, chamada pelo agente de triagem imediatamente após receber o CPF — antes de solicitar a data de nascimento. Tentativas com CPF inválido são contadas em `tentativas_cpf_invalido` no estado; após 3 tentativas, a sessão é encerrada automaticamente.
