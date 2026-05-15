"""
Grafo principal do sistema multi-agente Banco Ágil.
Orquestra os 4 agentes usando LangGraph com um StateGraph compartilhado.
"""

import os
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from tools.ferramentas import (
    autenticar_cliente,
    calcular_e_atualizar_score,
    consultar_cotacao,
    consultar_limite_credito,
    encerrar_atendimento,
    solicitar_aumento_limite,
)
from utils.state import BancoAgilState

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

def _get_llm():
    api_key = os.getenv("GROQ_API_KEY", "")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=0.2,
    )


# ---------------------------------------------------------------------------
# Ferramentas por agente
# ---------------------------------------------------------------------------

TOOLS_TRIAGEM = [autenticar_cliente, encerrar_atendimento]
TOOLS_CREDITO = [consultar_limite_credito, solicitar_aumento_limite, encerrar_atendimento]
TOOLS_ENTREVISTA = [calcular_e_atualizar_score, encerrar_atendimento]
TOOLS_CAMBIO = [consultar_cotacao, encerrar_atendimento]

ALL_TOOLS = list({t.name: t for t in (
    TOOLS_TRIAGEM + TOOLS_CREDITO + TOOLS_ENTREVISTA + TOOLS_CAMBIO
)}.values())


# ---------------------------------------------------------------------------
# Prompts dos agentes
# ---------------------------------------------------------------------------

PROMPT_TRIAGEM = """Você é o assistente virtual do Banco Ágil, um banco digital moderno e confiável.
Sua função é autenticar o cliente e direcioná-lo ao serviço correto.

FLUXO OBRIGATÓRIO:
1. Cumprimente o cliente de forma calorosa e profissional.
2. Solicite o CPF do cliente.
3. Solicite a data de nascimento (formato DD/MM/AAAA — converta para YYYY-MM-DD ao chamar a ferramenta).
4. Chame a ferramenta `autenticar_cliente` com os dados fornecidos.
5. Se autenticado:
   - Cumprimente pelo nome.
   - Pergunte como pode ajudar.
   - Direcione para o serviço correto conforme a necessidade (crédito, câmbio, etc.).
   - Sinalize a transição atualizando o campo `agente_atual` no estado.
6. Se não autenticado:
   - Informe a falha educadamente.
   - Permita até 2 novas tentativas (total de 3 tentativas).
   - Após 3 falhas, encerre o atendimento com a ferramenta `encerrar_atendimento`.

IMPORTANTE:
- Nunca invente dados de clientes.
- Não atue fora do escopo de triagem e autenticação.
- Se o cliente pedir para encerrar, chame `encerrar_atendimento`.
- O cliente não deve perceber que existem agentes diferentes — mantenha fluidez e continuidade.
"""

PROMPT_CREDITO = """Você é o assistente de crédito do Banco Ágil.
O cliente já foi autenticado. Você tem acesso ao CPF e nome do cliente no contexto da conversa.

RESPONSABILIDADES:
1. Consultar o limite de crédito atual com `consultar_limite_credito`.
2. Processar solicitações de aumento de limite com `solicitar_aumento_limite`.
3. Informar o resultado da análise (aprovado/rejeitado).
4. Se rejeitado: oferecer redirecionamento para a entrevista de crédito para melhorar o score.
5. Encerrar ou redirecionar conforme a necessidade do cliente.

REGRAS:
- Sempre use as ferramentas para consultar dados reais. Nunca invente valores.
- Se o cliente pedir para encerrar, chame `encerrar_atendimento`.
- Mantenha tom profissional, claro e empático.
- O cliente não deve perceber transição entre agentes.
"""

PROMPT_ENTREVISTA = """Você é o assistente de análise financeira do Banco Ágil.
O cliente deseja melhorar seu score de crédito. Conduza uma entrevista estruturada e respeitosa.

PERGUNTAS OBRIGATÓRIAS (faça uma por vez, de forma conversacional):
1. Qual é a sua renda mensal aproximada? (em R$)
2. Qual é o seu tipo de emprego? (formal com carteira assinada, autônomo/freelancer, ou desempregado)
3. Quais são suas despesas fixas mensais? (aluguel, contas, etc. — em R$)
4. Quantos dependentes você possui? (filhos, cônjuge, etc.)
5. Você possui dívidas ativas no momento? (sim ou não)

APÓS COLETAR TODOS OS DADOS:
- Chame `calcular_e_atualizar_score` com os dados coletados.
- Informe o novo score ao cliente de forma positiva.
- Informe que ele será redirecionado para análise do limite com o novo score.

REGRAS:
- Faça perguntas uma por vez — nunca em lista.
- Seja empático e encorajador.
- Se o cliente pedir para encerrar, chame `encerrar_atendimento`.
- O cliente não deve perceber transição entre agentes.
"""

PROMPT_CAMBIO = """Você é o assistente de câmbio do Banco Ágil.
Sua função é consultar cotações de moedas em tempo real.

RESPONSABILIDADES:
1. Perguntar qual moeda o cliente deseja consultar (se não informado).
2. Usar a ferramenta `consultar_cotacao` com o código da moeda (ex: USD, EUR, GBP, ARS).
3. Apresentar os valores de compra e venda de forma clara.
4. Encerrar com mensagem amigável ou perguntar se deseja outra cotação.

REGRAS:
- Use os códigos corretos: Dólar=USD, Euro=EUR, Libra=GBP, Peso Argentino=ARS.
- Se a API falhar, informe o cliente e sugira tentar novamente mais tarde.
- Se o cliente pedir para encerrar, chame `encerrar_atendimento`.
- O cliente não deve perceber transição entre agentes.
"""

PROMPTS = {
    "triagem": PROMPT_TRIAGEM,
    "credito": PROMPT_CREDITO,
    "entrevista": PROMPT_ENTREVISTA,
    "cambio": PROMPT_CAMBIO,
}

TOOLS_MAP = {
    "triagem": TOOLS_TRIAGEM,
    "credito": TOOLS_CREDITO,
    "entrevista": TOOLS_ENTREVISTA,
    "cambio": TOOLS_CAMBIO,
}


# ---------------------------------------------------------------------------
# Nós do grafo
# ---------------------------------------------------------------------------

def _build_agent_node(agente: str):
    """Cria um nó de agente com LLM + ferramentas específicas."""

    def node(state: BancoAgilState) -> dict:
        llm = _get_llm()
        tools = TOOLS_MAP[agente]
        llm_with_tools = llm.bind_tools(tools)
        system_prompt = PROMPTS[agente]

        # Injetar contexto do cliente autenticado no system prompt
        contexto = ""
        if state.get("autenticado") and state.get("cpf_cliente"):
            contexto = (
                f"\n\nCONTEXTO DO CLIENTE AUTENTICADO:\n"
                f"Nome: {state.get('nome_cliente', 'N/A')}\n"
                f"CPF: {state.get('cpf_cliente', 'N/A')}\n"
                f"Limite atual: R$ {state.get('limite_credito', 0):,.2f}\n"
                f"Score atual: {state.get('score_cliente', 0)}\n"
            )

        messages = [SystemMessage(content=system_prompt + contexto)] + state["messages"]
        response = llm_with_tools.invoke(messages)

        # Detectar encerramento por tool_call
        encerrado = state.get("encerrado", False)
        if hasattr(response, "tool_calls"):
            for tc in response.tool_calls:
                if tc["name"] == "encerrar_atendimento":
                    encerrado = True

        # Detectar redirecionamento para outro agente
        novo_agente = state.get("agente_atual", agente)
        content = response.content if isinstance(response.content, str) else ""

        return {
            "messages": [response],
            "agente_atual": novo_agente,
            "encerrado": encerrado,
        }

    return node


def triagem_node(state: BancoAgilState) -> dict:
    base = _build_agent_node("triagem")(state)

    # Extrair dados de autenticação das tool calls na última mensagem
    last_msg = base["messages"][-1]
    return base


def credito_node(state: BancoAgilState) -> dict:
    return _build_agent_node("credito")(state)


def entrevista_node(state: BancoAgilState) -> dict:
    return _build_agent_node("entrevista")(state)


def cambio_node(state: BancoAgilState) -> dict:
    return _build_agent_node("cambio")(state)


def tool_node_handler(state: BancoAgilState) -> dict:
    """Executa as ferramentas e atualiza o estado com resultados de autenticação."""
    tool_node = ToolNode(ALL_TOOLS)
    result = tool_node.invoke(state)

    updates = {}

    # Processar resultados das ferramentas para atualizar estado
    for msg in result.get("messages", []):
        if hasattr(msg, "content"):
            import json
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else {}
            except Exception:
                content = {}

            # Autenticação bem-sucedida
            if content.get("autenticado") is True:
                updates["autenticado"] = True
                updates["cpf_cliente"] = content.get("cpf")
                updates["nome_cliente"] = content.get("nome")
                updates["limite_credito"] = content.get("limite_credito")
                updates["score_cliente"] = content.get("score")

            # Autenticação falhou — incrementar tentativas
            elif content.get("autenticado") is False:
                tentativas = state.get("tentativas_auth", 0) + 1
                updates["tentativas_auth"] = tentativas

            # Encerramento
            if content.get("encerrado") is True:
                updates["encerrado"] = True

            # Score atualizado após entrevista
            if "score_novo" in content:
                updates["score_cliente"] = content["score_novo"]
                updates["entrevista_concluida"] = True

    return {**result, **updates}


# ---------------------------------------------------------------------------
# Roteadores
# ---------------------------------------------------------------------------

def router_principal(state: BancoAgilState) -> Literal[
    "triagem", "credito", "entrevista", "cambio", "__end__"
]:
    """Decide qual agente deve responder com base no estado."""
    if state.get("encerrado"):
        return END

    agente = state.get("agente_atual", "triagem")
    if agente in ("triagem", "credito", "entrevista", "cambio"):
        return agente
    return "triagem"


def router_pos_tool(state: BancoAgilState) -> Literal[
    "triagem", "credito", "entrevista", "cambio", "__end__"
]:
    """Retorna ao agente correto após execução de ferramenta."""
    if state.get("encerrado"):
        return END
    agente = state.get("agente_atual", "triagem")
    return agente if agente in ("triagem", "credito", "entrevista", "cambio") else "triagem"


def router_tool_call(state: BancoAgilState) -> Literal["tools", "__end__"]:
    """Verifica se o agente chamou alguma ferramenta."""
    if state.get("encerrado"):
        return END
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Construção do grafo
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(BancoAgilState)

    # Nós de agentes
    graph.add_node("triagem", triagem_node)
    graph.add_node("credito", credito_node)
    graph.add_node("entrevista", entrevista_node)
    graph.add_node("cambio", cambio_node)
    graph.add_node("tools", tool_node_handler)

    # Ponto de entrada
    graph.set_entry_point("triagem")

    # Arestas condicionais — após cada agente, verificar tool call
    for agente in ("triagem", "credito", "entrevista", "cambio"):
        graph.add_conditional_edges(agente, router_tool_call, {"tools": "tools", END: END})

    # Após execução das ferramentas, retornar ao agente correto
    graph.add_conditional_edges(
        "tools",
        router_pos_tool,
        {
            "triagem": "triagem",
            "credito": "credito",
            "entrevista": "entrevista",
            "cambio": "cambio",
            END: END,
        },
    )

    return graph.compile()


# Instância global do grafo
banco_graph = build_graph()
