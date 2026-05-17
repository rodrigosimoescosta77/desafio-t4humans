from langchain_core.messages import AIMessage, HumanMessage

from agents.common import _build_agent_node
from agents.credito_helpers import (
    extrair_valor,
    is_aumento_request,
    processar_solicitacao_aumento,
)
from utils.state import BancoAgilState

_PALAVRAS_PEDIDO_VALOR = ("limite", "valor", "quanto", "qual", "deseja", "gostaria")


def _agente_perguntou_valor(messages: list) -> bool:
    """Verifica se a última mensagem do assistente pediu um valor de limite."""
    for msg in reversed(messages[:-1]):
        if isinstance(msg, AIMessage) and isinstance(msg.content, str):
            txt = msg.content.lower()
            return any(p in txt for p in _PALAVRAS_PEDIDO_VALOR)
    return False


def credito_node(state: BancoAgilState) -> dict:
    last_msg = state["messages"][-1] if state["messages"] else None
    cpf = state.get("cpf_cliente", "")

    if isinstance(last_msg, HumanMessage) and cpf:
        txt = last_msg.content.lower()
        valor = None

        if is_aumento_request(txt):
            valor = extrair_valor(last_msg.content)
        elif _agente_perguntou_valor(state["messages"]):
            valor = extrair_valor(last_msg.content)

        if valor:
            resposta = processar_solicitacao_aumento(state, valor)
            if resposta is not None:
                return resposta

    return _build_agent_node("credito")(state)
