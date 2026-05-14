# 🏦 Banco Ágil — Sistema Multi-Agente de Atendimento Bancário

Sistema de atendimento ao cliente bancário baseado em múltiplos agentes de IA, construído com **LangGraph** e **Gemini**. Cada agente possui escopo definido e responsabilidades claras, operando de forma transparente para o cliente como um único assistente virtual coeso.

---

## 📋 Visão Geral

O **Banco Ágil** é um sistema de atendimento digital inteligente que simula o atendimento bancário moderno por meio de agentes especializados:

- **Autenticação segura** com CPF e data de nascimento
- **Consulta e solicitação de crédito** com análise automatizada de score
- **Entrevista financeira** para recálculo de score de crédito
- **Cotação de câmbio em tempo real** via API externa
- **Interface web** moderna e responsiva com Streamlit

O sistema é construído sobre um **grafo de estados** (LangGraph), onde cada agente é um nó especializado e as transições acontecem de forma condicional e transparente — o cliente jamais percebe a mudança de agente.

---

## 🏗 Arquitetura do Sistema

### Visão geral do grafo

```
[ENTRADA]
    │
    ▼
[Agente de Triagem] ──autenticado──► [roteamento por intenção]
    │                                         │
    │                              ┌──────────┼──────────┐
    │                              ▼          ▼          ▼
    │                         [Crédito]  [Câmbio]  [Entrevista]
    │                              │                    │
    │                              └────────────────────┘
    │                                        │
    ▼                                        ▼
[Encerramento] ◄──────────────── [encerrar_atendimento()]
```

### Componentes

```
banco_agil/
├── app.py                      # Interface Streamlit
├── requirements.txt            # Requisitos necessários a serem instalados
├── .env.example                # Variáveis de ambiente
│
├── agents/
│   └── graph.py                # Grafo LangGraph — nós, arestas e roteadores
│
├── tools/
│   └── ferramentas.py          # Todas as ferramentas dos agentes (@tool)
│
├── utils/
│   ├── state.py                # BancoAgilState — estado compartilhado
│   └── session.py              # BancoAgilSession — gerenciador de sessão
│
└── data/
    ├── clientes.csv                    # Base de clientes
    ├── score_limite.csv                # Tabela score × limite máximo
    └── solicitacoes_aumento_limite.csv # Registro de solicitações
```

### Fluxo de dados

1. O usuário digita na interface Streamlit
2. `BancoAgilSession.processar_mensagem()` detecta intenção e atualiza o agente ativo
3. `banco_graph.invoke()` executa o nó do agente com o LLM (Gemini)
4. Se o LLM retornar uma tool call, o `ToolNode` executa a ferramenta
5. O resultado volta ao LLM para formulação da resposta final
6. O estado é atualizado (autenticação, score, encerramento, etc.)
7. A resposta é exibida na interface com o badge do agente ativo

---

## 👥 Agentes

### 🔐 Agente de Triagem
- Ponto de entrada obrigatório para todos os atendimentos
- Coleta CPF e data de nascimento
- Autentica contra `clientes.csv`
- Permite até **3 tentativas** antes de encerrar
- Redireciona para o agente adequado após autenticação

**Ferramentas:** `autenticar_cliente`, `encerrar_atendimento`

### 💳 Agente de Crédito
- Consulta limite e score atual
- Processa solicitações de aumento de limite
- Verifica score contra `score_limite.csv`
- Registra solicitação em `solicitacoes_aumento_limite.csv` com status
- Oferece redirecionamento para entrevista em caso de rejeição

**Ferramentas:** `consultar_limite_credito`, `solicitar_aumento_limite`, `encerrar_atendimento`

### 📋 Agente de Entrevista de Crédito
- Conduz entrevista financeira conversacional (5 perguntas, uma por vez)
- Calcula novo score pela fórmula ponderada
- Atualiza `clientes.csv` com o novo score
- Redireciona ao Agente de Crédito para nova análise

**Ferramentas:** `calcular_e_atualizar_score`, `encerrar_atendimento`

**Fórmula de score:**
```python
score = (renda / (despesas + 1)) * 30
      + {"formal": 300, "autônomo": 200, "desempregado": 0}[emprego]
      + {0: 100, 1: 80, 2: 60, 3+: 30}[dependentes]
      + {"sim": -100, "não": 100}[dívidas]
# Resultado clampado entre 0 e 1000
```

### 💱 Agente de Câmbio
- Consulta cotação em tempo real via [AwesomeAPI](https://economia.awesomeapi.com.br)
- Suporta qualquer par de moedas (USD, EUR, GBP, ARS, etc.)
- Trata falhas de API com mensagem amigável

**Ferramentas:** `consultar_cotacao`, `encerrar_atendimento`

---

## ✅ Funcionalidades Implementadas

- [x] Autenticação com CPF + data de nascimento e controle de tentativas
- [x] Consulta de limite de crédito em tempo real (CSV)
- [x] Solicitação de aumento de limite com aprovação/rejeição automática por score
- [x] Registro persistente de solicitações em CSV (com timestamp ISO 8601)
- [x] Entrevista financeira conversacional com recálculo de score
- [x] Atualização do score no CSV após entrevista
- [x] Redirecionamento crédito → entrevista → crédito (fluxo completo)
- [x] Cotação de câmbio em tempo real
- [x] Encerramento controlado em qualquer momento
- [x] Interface Streamlit com design bancário moderno
- [x] Sidebar com dados do cliente autenticado e indicador de agente ativo
- [x] Clientes de teste documentados na interface
- [x] Tratamento de erros em todas as ferramentas (CSV, API, LLM)
- [x] Transição transparente entre agentes (o cliente vê um único assistente)

---

## ⚠️ Desafios Enfrentados

### 1. Gerenciamento de estado entre agentes
**Problema:** O LangGraph gerencia mensagens automaticamente, mas dados como CPF autenticado, score e agente atual precisam persistir entre turnos.  
**Solução:** `BancoAgilState` (TypedDict) com campos explícitos além das `messages`. O `tool_node_handler` extrai os dados das respostas das ferramentas e os propaga para o estado.

### 2. Detecção de transição entre agentes
**Problema:** O LLM decide quando redirecionar, mas o grafo precisa saber qual nó executar.  
**Solução:** Detecção de intenção por palavras-chave no `BancoAgilSession` antes de invocar o grafo, combinada com o campo `agente_atual` no estado.

### 3. Transparência da transição para o cliente
**Problema:** O requisito exige que o cliente não perceba a troca de agentes.  
**Solução:** Cada agente recebe o contexto completo do cliente no system prompt, mantendo a continuidade conversacional. O histórico de mensagens é passado integralmente a cada invocação.

### 4. Atualização do estado após tool calls
**Problema:** O LangGraph executa ferramentas assincronamente; os resultados precisam atualizar o estado global (ex: score novo, autenticação).  
**Solução:** `tool_node_handler` intercepta todos os resultados de ferramentas, parseia o JSON e atualiza os campos relevantes do estado.

### 5. Score clampado e pesos ajustáveis
**Problema:** A fórmula pode produzir valores negativos ou acima de 1000.  
**Solução:** `max(0, min(1000, int(score_raw)))` garante o range correto.

---

## 🛠 Escolhas Técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Framework de agentes | **LangGraph** | Grafo de estados com controle explícito de fluxo — ideal para transições condicionais entre agentes |
| LLM | **Gemini 2.0 Flash** | Free tier generoso, latência baixa, excelente para demos ao vivo |
| API de câmbio | **AwesomeAPI** | Gratuita, sem autenticação, cobertura ampla de pares de moedas |
| Persistência | **CSV** | Requisito do desafio; simples e sem dependências externas |
| Interface | **Streamlit** | Requisito do desafio; rápido para prototipagem com boa UX |
| Injeção de contexto | **System prompt dinâmico** | Garante que cada agente conheça o cliente autenticado sem repetição no chat |

---

## 🚀 Tutorial de Execução

### Pré-requisitos

- Python 3.11+
- Conta Google com acesso ao [Google AI Studio](https://aistudio.google.com/)

### 1. Clonar o repositório

```bash
git clone https://github.com/rodrigosimoescosta77/desafio-t4humans.git
cd desafio-t4humans
```

### 2. Criar ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar a API Key

```bash
# Edite o .env e adicione sua GOOGLE_API_KEY
GOOGLE_API_KEY=AIza***************
```

Ou exporte diretamente:

```bash
export GOOGLE_API_KEY="sua_chave_aqui"  # Linux/Mac
set GOOGLE_API_KEY=sua_chave_aqui       # Windows
```

### 5. Executar a aplicação

```bash
streamlit run app.py
```

Acesse [http://localhost:8501](http://localhost:8501) no navegador.

---

## 🧪 Roteiro de Testes

Use os clientes de exemplo disponíveis na sidebar da aplicação:

### Teste 1 — Fluxo de autenticação e crédito
1. CPF: `123.456.789-00` | Nasc: `15/05/1990` (João Silva, score 650)
2. Solicite consulta de limite → R$ 5.000,00
3. Solicite aumento para R$ 8.000,00 → deve **aprovar** (limite máximo para score 650 = R$ 10.000)
4. Solicite aumento para R$ 25.000,00 → deve **rejeitar**

### Teste 2 — Fluxo de entrevista de crédito
1. Autentique como Carlos Oliveira (CPF: `111.222.333-44`, score 420)
2. Solicite aumento de limite para R$ 5.000,00 → deve rejeitar
3. Aceite a entrevista de crédito
4. Responda: renda R$ 5.000, emprego formal, despesas R$ 1.500, 1 dependente, sem dívidas
5. Verifique o novo score calculado
6. O sistema redirecionará ao crédito automaticamente

### Teste 3 — Câmbio
1. Autentique com qualquer cliente
2. Solicite a cotação do dólar
3. Solicite a cotação do euro

### Teste 4 — Falha de autenticação
1. Digite um CPF inválido
2. Verifique o controle de tentativas (máximo 3)

### Teste 5 — Encerramento
1. A qualquer momento, diga "encerrar" ou "tchau"

---

## 📁 Estrutura dos Arquivos CSV

### `clientes.csv`
| Campo | Tipo | Descrição |
|---|---|---|
| cpf | string | CPF com formatação |
| nome | string | Nome completo |
| data_nascimento | YYYY-MM-DD | Data de nascimento |
| limite_credito | float | Limite atual em R$ |
| score | int | Score de crédito (0-1000) |

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
| status_pedido | string | `pendente`, `aprovado` ou `rejeitado` |
