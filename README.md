# 🏦 Banco Ágil — Sistema Multi-Agente de Atendimento Bancário

Sistema de atendimento ao cliente bancário baseado em múltiplos agentes de IA, construído com **LangGraph** e **Gemini 2.5 Flash (Google AI)**. Cada agente possui escopo definido e responsabilidades claras, operando de forma transparente para o cliente como um único assistente virtual coeso.

---

## 📋 Visão Geral

O **Banco Ágil** é um sistema de atendimento digital inteligente que simula o atendimento bancário moderno por meio de agentes especializados:

- **Autenticação segura** com CPF e data de nascimento contra base CSV
- **Consulta e solicitação de crédito** com análise automatizada de score
- **Entrevista financeira** para recálculo de score de crédito
- **Cotação de câmbio em tempo real** via API externa
- **Interface web** moderna e responsiva com Streamlit

O sistema é construído sobre um **grafo de estados** (LangGraph), onde cada agente é um nó especializado e as transições acontecem de forma condicional e transparente — o cliente jamais percebe a mudança de agente.

---

## 🤖 Modelo de LLM

| Atributo | Valor |
|---|---|
| Provedor | Google AI Studio |
| Modelo | `gemini-2.5-flash` |
| Temperatura | 1.0 |
| Thinking budget | 0 (desabilitado) |
| Biblioteca | `langchain-google-genai` |
| Chave de acesso | `GOOGLE_API_KEY` (em aistudio.google.com) |

> **Nota:** O thinking mode do Gemini 2.5 Flash foi desativado (`thinking_budget=0`) para evitar que o modelo exponha raciocínio interno nas respostas ao cliente.

---

## 🏗 Arquitetura do Sistema

### Visão geral do grafo

O grafo LangGraph utiliza **entrada condicional via `START`**: a cada invocação, o roteador verifica o campo `agente_atual` do estado e direciona para o nó correto — sem passar pela triagem em toda mensagem.

```
[START]
   │
   ▼
[router_principal] ── agente_atual ──►  ┌─────────────┐
                                        │   Triagem   │ ◄── autenticação
                                        │   Crédito   │ ◄── limite, aumento
                                        │  Entrevista │ ◄── score financeiro
                                        │   Câmbio    │ ◄── cotação
                                        └─────────────┘
                                               │
                              ┌────────────────┴──────────────────┐
                    tool_call │                                    │ sem tool_call
                              ▼                                    ▼
                         [tools node]                           [END]
                              │
                    router_pos_tool
                              │
                    retorna ao agente atual
```

### Estrutura de arquivos

```
banco-agil/
├── app.py                              # Interface Streamlit
├── requirements.txt                    # Dependências
├── .env                                # Variáveis de ambiente (não versionado)
│
├── agents/
│   ├── graph.py                        # Grafo LangGraph — nós, arestas e roteadores
│   ├── router.py                       # Roteamento de mensagens e tool handler
│   ├── common.py                       # Fabrica LLM e mapeia prompts / ferramentas
│   ├── prompts.py                      # Prompt templates por agente
│   ├── triagem.py                      # Nó do agente de triagem
│   ├── credito.py                      # Nó do agente de crédito
│   ├── entrevista.py                   # Nó do agente de entrevista
│   ├── cambio.py                       # Nó do agente de câmbio
│   └── credito_helpers.py              # Helpers de detecção e extração para crédito
│
├── tools/
│   └── ferramentas.py                  # Ferramentas dos agentes (@tool LangChain)
│
├── utils/
│   ├── logging_config.py               # Logging centralizado e alertas
│   ├── state.py                        # BancoAgilState — estado compartilhado
│   └── session.py                      # BancoAgilSession — gerenciador de sessão
│
├── logs/                               # Arquivos de log gerados em execução
│   └── banco_agil.log
│
└── data/
    ├── clientes.csv                    # Base de clientes
    ├── score_limite.csv                # Tabela score × limite máximo
    └── solicitacoes_aumento_limite.csv # Registro histórico de solicitações
```

### Modularização de agentes

O projeto usa uma arquitetura de agentes modular, distribuída em três camadas:

**Camada de orquestração (`agents/`)**
- `agents/graph.py` — monta o grafo LangGraph, registra os nós de agente e define as arestas condicionais.
- `agents/router.py` — isola os três roteadores (`router_principal`, `router_pos_tool`, `router_tool_call`) e o `tool_node_handler`, responsável por executar ferramentas e propagar atualizações de estado (autenticação, score, encerramento, etc.).
- `agents/common.py` — fábrica do LLM (`_get_llm`) e construtor genérico de nós (`_build_agent_node`): monta o prompt de sistema dinâmico com contexto do cliente e vincula as ferramentas corretas a cada agente.
- `agents/prompts.py` — centraliza os system prompts de todos os agentes no dicionário `PROMPTS`, facilitando ajustes sem tocar na lógica.
- `agents/credito_helpers.py` — helpers de detecção e extração para identificar pedidos de aumento de limite nas mensagens do usuário.

**Nós de agente (`agents/`)**
- `agents/triagem.py` — nó de autenticação: valida CPF, autentica o cliente e roteia para o agente adequado.
- `agents/credito.py` — nó de crédito: consulta limite atual e processa solicitações de aumento.
- `agents/entrevista.py` — nó de entrevista financeira: conduz as perguntas e recalcula o score ao final.
- `agents/cambio.py` — nó de câmbio: consulta cotações em tempo real via AwesomeAPI.

**Ferramentas e suporte**
- `tools/ferramentas.py` — todas as ferramentas `@tool` do LangChain disponíveis aos agentes.
- `utils/state.py` — `BancoAgilState` (TypedDict): estado compartilhado entre todos os nós do grafo.
- `utils/session.py` — `BancoAgilSession`: gerencia o ciclo de vida da conversa e detecta intenções por palavras-chave para atualizar `agente_atual`.
- `utils/logging_config.py` — configuração centralizada de logging com alertas opcionais via Slack e e-mail.

Para detalhes internos de cada módulo de agente, consulte `agents/README.md`.

### Logging centralizado e alertas

- `utils/logging_config.py` configura o logger global do projeto.
- Logs são gravados em `logs/banco_agil.log`.
- Mensagens de nível `ERROR` ou superior podem ser enviadas para Slack via `SLACK_WEBHOOK_URL`.
- Alertas de e-mail podem ser enviados se as variáveis SMTP estiverem definidas.

### Fluxo de dados

```
Usuário digita
      │
      ▼
BancoAgilSession.processar_mensagem()
      │
      ├─► Detecta intenção por palavras-chave → atualiza agente_atual
      │
      ▼
banco_graph.invoke(state)
      │
      ├─► router_principal → nó do agente ativo
      │         │
      │         ├─► LLM (Gemini 2.5 Flash) gera resposta ou tool_call
      │         │
      │         └─► [tool_call] → ToolNode executa ferramenta
      │                    │
      │                    └─► tool_node_handler atualiza estado
      │                              (autenticado, score, encerrado, etc.)
      ▼
Resposta extraída → exibida na interface com badge do agente
```

---

## 👥 Descrição dos Agentes

### 🔐 Agente de Triagem
**Objetivo:** Porta de entrada obrigatória. Autentica o cliente e direciona para o agente adequado somente após autenticação bem-sucedida.

**Fluxo:**
1. Saudação inicial
2. Coleta CPF
3. Coleta data de nascimento
4. Chama `autenticar_cliente` → valida contra `clientes.csv`
5. Se autenticado: identifica a necessidade e roteia
6. Se falhar: permite até **3 tentativas** no total; após isso, chama `encerrar_atendimento`

**Ferramentas:** `autenticar_cliente`, `encerrar_atendimento`

---

### 💳 Agente de Crédito
**Objetivo:** Processar consultas e solicitações de limite de crédito.

**Fluxo:**
- Consulta o limite atual via `consultar_limite_credito`
- Ao receber um valor desejado, chama `solicitar_aumento_limite` diretamente em Python (decisão automática por score), e usa o LLM para comunicar o resultado ao cliente
- Se **aprovado**: informa o novo limite disponível
- Se **rejeitado**: informa o limite máximo permitido e oferece redirecionamento para entrevista de crédito via botões na interface

**Ferramentas:** `consultar_limite_credito`, `solicitar_aumento_limite`, `encerrar_atendimento`

---

### 📋 Agente de Entrevista de Crédito
**Objetivo:** Conduzir entrevista financeira conversacional para recalcular o score do cliente.

**Perguntas (uma por vez):**
1. Renda mensal aproximada (R$)
2. Tipo de emprego (formal / autônomo / desempregado)
3. Despesas fixas mensais (R$)
4. Número de dependentes
5. Possui dívidas ativas? (sim / não)

Após coletar todos os dados, chama `calcular_e_atualizar_score`, informa o novo score de forma positiva e pergunta ao cliente o que deseja fazer em seguida — sem mencionar redirecionamento ou troca de etapa.

**Fórmula de score:**
```python
score = (renda / (despesas + 1)) * 30
      + {"formal": 300, "autônomo": 200, "desempregado": 0}[emprego]
      + {0: 100, 1: 80, 2: 60, 3+: 30}[dependentes]
      + {"não": 100, "sim": -100}[dívidas]
# Resultado limitado entre 0 e 1000
```

**Ferramentas:** `calcular_e_atualizar_score`, `encerrar_atendimento`

---

### 💱 Agente de Câmbio
**Objetivo:** Consultar cotações de moedas em tempo real.

- Chama `consultar_cotacao` imediatamente ao detectar qualquer menção de moeda
- Apresenta valores de compra e venda
- Suporta: USD, EUR, GBP, ARS e qualquer moeda disponível na AwesomeAPI
- Nunca estima ou inventa valores — apenas reproduz o retorno da API

**Ferramentas:** `consultar_cotacao`, `encerrar_atendimento`

---

## ✅ Funcionalidades Implementadas

- [x] Autenticação com CPF + data de nascimento e controle de até 3 tentativas
- [x] Injeção do contador de tentativas no contexto do agente de triagem
- [x] Consulta de limite de crédito em tempo real (CSV)
- [x] Solicitação de aumento de limite com aprovação/rejeição automática por score
- [x] Registro persistente de solicitações em CSV com timestamp ISO 8601
- [x] Entrevista financeira conversacional com recálculo e atualização de score
- [x] Fluxo completo: crédito → entrevista → crédito com transição transparente (sem indicação de redirecionamento ao cliente)
- [x] Botões "Sim / Não" na interface para aceite ou recusa da entrevista de crédito
- [x] Cotação de câmbio em tempo real via AwesomeAPI
- [x] Encerramento controlado em qualquer momento por qualquer agente
- [x] Roteamento condicional via `START` no grafo (cada mensagem vai direto ao agente certo)
- [x] Interface Streamlit com design bancário moderno (tema escuro)
- [x] Sidebar com dados do cliente autenticado e indicador de agente ativo
- [x] Escape de `$` no front-end para evitar interpretação LaTeX pelo Streamlit
- [x] Transição transparente entre agentes — o cliente interage com um único assistente

---

## 🧪 Desafios enfrentados

As informações detelhadas sobre os desafios encontrados e soluções dadas estão no documento "LICOES_APRENDIDAS.md"

---

## 🛠 Escolhas Técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Framework de agentes | **LangGraph** | Grafo de estados com controle explícito de fluxo e roteamento condicional entre nós |
| LLM | **Gemini 2.5 Flash** | Disponível via Google AI Studio; suporta tool calling; thinking mode desabilitável |
| Entrada do grafo | **`add_conditional_edges(START, ...)`** | Permite rotear diretamente ao agente correto sem passar pela triagem a cada turno |
| Chamada de ferramenta financeira | **Tool calling nativo do LangGraph** | O LLM chama a ferramenta diretamente; o roteador `tools → agente` executa e devolve o resultado ao LLM para que ele formule a resposta final ao cliente |
| Detecção de intenção | **Palavras-chave no `BancoAgilSession`** | Mais previsível e controlável do que deixar o LLM decidir o redirecionamento |
| Estado compartilhado | **`BancoAgilState` (TypedDict)** | Persiste dados entre agentes (CPF, score, agente ativo, flags de controle) |
| API de câmbio | **AwesomeAPI** | Gratuita, sem autenticação, ampla cobertura de pares de moedas |
| Persistência | **CSV** | Requisito do desafio; simples e sem dependências externas |
| Interface | **Streamlit** | Requisito do desafio; rápido para prototipagem com boa UX |
| Contexto dos agentes | **System prompt dinâmico** | Cada agente recebe CPF, nome, limite e score do cliente no prompt — sem repetição no chat |

---

## 🚀 Tutorial de Execução

### Pré-requisitos

- Python 3.11+
- Chave de API gratuita do Google AI Studio: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 1. Clonar o repositório

```bash
git clone https://github.com/rodrigosimoescosta77/desafio-t4humans.git
cd desafio-t4humans/banco-agil
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar a chave de API

Crie o arquivo `.env` na raiz do projeto:

```
GOOGLE_API_KEY=sua_chave_aqui
```

Para ativar alertas de erro, adicione as variáveis opcionais abaixo:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.exemplo.com
SMTP_PORT=587
SMTP_FROM=noreply@bancoagil.local
SMTP_USERNAME=usuario
SMTP_PASSWORD=senha
ALERT_EMAIL_RECIPIENTS=ops@bancoagil.local
```

### 5. Executar a aplicação

```bash
streamlit run app.py
```

Acesse [http://localhost:8501](http://localhost:8501) no navegador.

---

## 🧪 Roteiro de Testes

Use os clientes disponíveis da aplicação:

| Cliente | CPF | Nascimento | Score |
|---|---|---|---|
| Rodrigo Simões Costa | 023.770.814-01 | 04/08/1977 | 750 |
| Renata Muniz de Araujo Pelinca | 024.081.514-90 | 01/12/1977 | 200 |
| Pedro Pelinca Simões | 704.610.094-20 | 31/12/2007 | 420 |
| Manuela Pelinca Simões | 704.610.104-37 | 26/09/2009 | 710 |
| Mariana Pelinca Simões | 154.121.524-90 | 28/07/2012 | 380 |

### Teste 1 — Autenticação e aumento de limite aprovado
1. CPF `023.770.814-01` | Nasc `04/08/1977` (Rodrigo Simões Costa, score 750)
2. Solicite aumento para R$ 8.000,00 → **aprovado**

### Teste 2 — Rejeição e entrevista de crédito
1. CPF `024.081.514-90` | Nasc `01/12/1977` (Renata Muniz de Araujo Pelinca, score 200)
2. Solicite aumento para R$ 15.000,00 → **rejeitado**
3. Clique em **"Sim, quero participar"**
4. Responda a entrevista (renda, emprego, despesas, dependentes, dívidas):
      renda = R$30.000 / 
      emprego = formal / 
      despesas = R$1000 /
      dependentes = 0 /
      dívidas = não 
5. Verifique o novo score calculado → sistema redireciona ao crédito

### Teste 3 — Câmbio
1. Autentique com qualquer cliente
2. Peça a cotação do dólar, euro ou libra

### Teste 4 — Falha de autenticação
1. Digite CPF ou data de nascimento incorretos
2. Verifique o controle de 3 tentativas e encerramento automático

### Teste 5 — Encerramento
1. A qualquer momento, diga "quero encerrar" ou "tchau"

---

## 📁 Estrutura dos Arquivos CSV

### `clientes.csv`
| Campo | Tipo | Descrição |
|---|---|---|
| cpf | string | CPF com formatação |
| nome | string | Nome completo |
| data_nascimento | YYYY-MM-DD | Data de nascimento |
| limite_credito | float | Limite atual em R$ |
| score | int | Score de crédito (0–1000) |

### `score_limite.csv`
| Campo | Tipo | Descrição |
|---|---|---|
| score_minimo | int | Score mínimo da faixa |
| score_maximo | int | Score máximo da faixa |
| limite_maximo | float | Limite máximo permitido em R$ |

### `solicitacoes_aumento_limite.csv`
| Campo | Tipo | Descrição |
|---|---|---|
| cpf_cliente | string | CPF do cliente |
| data_hora_solicitacao | ISO 8601 | Timestamp da solicitação |
| limite_atual | float | Limite no momento da solicitação |
| novo_limite_solicitado | float | Valor solicitado |
| status_pedido | string | `aprovado` ou `rejeitado` |
