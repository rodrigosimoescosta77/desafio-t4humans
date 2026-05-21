import json
from typing import Literal

from langgraph.graph import END
from langgraph.prebuilt import ToolNode

from tools.ferramentas import (
    autenticar_cliente,
    calcular_e_atualizar_score,
    consultar_cotacao,
    consultar_limite_credito,
    encerrar_atendimento,
    solicitar_aumento_limite,
    validar_cpf,
)
from utils.state import BancoAgilState

TOOLS_TRIAGEM = [validar_cpf, autenticar_cliente, encerrar_atendimento]
TOOLS_CREDITO = [consultar_limite_credito, solicitar_aumento_limite, encerrar_atendimento]
TOOLS_ENTREVISTA = [calcular_e_atualizar_score, encerrar_atendimento]
TOOLS_CAMBIO = [consultar_cotacao, encerrar_atendimento]

ALL_TOOLS = list({t.name: t for t in (
    TOOLS_TRIAGEM + TOOLS_CREDITO + TOOLS_ENTREVISTA + TOOLS_CAMBIO
)}.values())


def tool_node_handler(state: BancoAgilState) -> dict:
    """Executa as ferramentas e atualiza o estado com resultados de autenticação."""
    tool_node = ToolNode(ALL_TOOLS)
    result = tool_node.invoke(state)

    updates = {}

    # Mapeia tool_call_id → tool call (nome + args) da última AIMessage
    tool_call_map = {}
    for msg in reversed(state["messages"]):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_call_map[tc["id"]] = tc
            break

    for msg in result.get("messages", []):
        if hasattr(msg, "content"):
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else {}
            except Exception:
                content = {}

            if content.get("autenticado") is True:
                updates["autenticado"] = True
                updates["cpf_cliente"] = content.get("cpf")
                updates["nome_cliente"] = content.get("nome")
                updates["limite_credito"] = content.get("limite_credito")
                updates["score_cliente"] = content.get("score")
            elif content.get("autenticado") is False:
                tentativas = state.get("tentativas_auth", 0) + 1
                updates["tentativas_auth"] = tentativas
            if content.get("valido") is False:
                tentativas_cpf = state.get("tentativas_cpf_invalido", 0) + 1
                updates["tentativas_cpf_invalido"] = tentativas_cpf
            elif content.get("valido") is True:
                tool_call_id = getattr(msg, "tool_call_id", None)
                if tool_call_id and tool_call_id in tool_call_map:
                    cpf = tool_call_map[tool_call_id]["args"].get("cpf", "")
                    if cpf:
                        updates["cpf_validado"] = cpf
            if content.get("status") == "rejeitado" and "novo_limite_solicitado" in content:
                updates["entrevista_ofertada"] = True
                updates["limite_credito"] = content.get("limite_atual", state.get("limite_credito"))
            if content.get("status") == "aprovado" and "novo_limite_solicitado" in content:
                updates["limite_credito"] = content.get("novo_limite_solicitado", state.get("limite_credito"))
            if content.get("encerrado") is True:
                updates["encerrado"] = True
            if "score_novo" in content:
                updates["score_cliente"] = content["score_novo"]
                updates["entrevista_concluida"] = True

    return {**result, **updates}


def router_principal(state: BancoAgilState) -> Literal[
    "triagem", "credito", "entrevista", "cambio", "__end__"
]:
    if state.get("encerrado"):
        return END

    agente = state.get("agente_atual", "triagem")
    if agente in ("triagem", "credito", "entrevista", "cambio"):
        return agente
    return "triagem"


def router_pos_tool(state: BancoAgilState) -> Literal[
    "triagem", "credito", "entrevista", "cambio", "__end__"
]:
    if state.get("encerrado"):
        return END
    agente = state.get("agente_atual", "triagem")
    return agente if agente in ("triagem", "credito", "entrevista", "cambio") else "triagem"


def router_tool_call(state: BancoAgilState) -> Literal["tools", "__end__"]:
    if state.get("encerrado"):
        return END
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return END
