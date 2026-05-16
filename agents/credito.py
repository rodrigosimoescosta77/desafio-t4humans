from langchain_core.messages import HumanMessage

from agents.common import _build_agent_node
from agents.credito_helpers import (
    extrair_valor,
    is_aumento_request,
    processar_solicitacao_aumento,
)
from utils.state import BancoAgilState


def credito_node(state: BancoAgilState) -> dict:
    last_msg = state["messages"][-1] if state["messages"] else None
    cpf = state.get("cpf_cliente", "")

    if isinstance(last_msg, HumanMessage) and cpf:
        txt = last_msg.content.lower()
        if is_aumento_request(txt):
            valor = extrair_valor(last_msg.content)
            if valor:
                resposta = processar_solicitacao_aumento(state, valor)
                if resposta is not None:
                    return resposta

    return _build_agent_node("credito")(state)
