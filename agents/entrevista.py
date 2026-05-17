from langchain_core.messages import AIMessage, HumanMessage

from agents.common import _build_agent_node, _get_llm
from tools.ferramentas import calcular_e_atualizar_score
from utils.state import BancoAgilState


def entrevista_node(state: BancoAgilState) -> dict:
    result = _build_agent_node("entrevista")(state)

    last_msg = result.get("messages", [None])[-1]
    if not (hasattr(last_msg, "tool_calls") and last_msg.tool_calls):
        return result

    for tc in last_msg.tool_calls:
        if tc["name"] != "calcular_e_atualizar_score":
            continue

        tool_result = calcular_e_atualizar_score.invoke(tc["args"])
        if "erro" in tool_result:
            return result

        score_novo = tool_result["score_novo"]
        score_anterior = tool_result["score_anterior"]
        nome = state.get("nome_cliente", "cliente")
        cpf = state.get("cpf_cliente", "")

        prompt = (
            f"Você é o assistente financeiro do Banco Ágil atendendo {nome}.\n\n"
            f"RESULTADO DO CÁLCULO:\n"
            f"Score anterior: {score_anterior}\n"
            f"Novo score: {score_novo}\n\n"
            f"Tarefa: Informe o novo score ao cliente de forma positiva e encorajadora. "
            f"Em seguida, diga que ele será direcionado para a análise de limite com o novo score. "
            f"Ao final, acrescente a pergunta: 'O que você deseja agora?' "
            f"Seja breve e caloroso. Não mencione agentes, departamentos ou sistemas internos."
        )
        llm = _get_llm()
        resposta = llm.invoke([HumanMessage(content=prompt)])

        return {
            "messages": [last_msg, resposta],
            "agente_atual": "entrevista",
            "encerrado": False,
            "score_cliente": score_novo,
            "entrevista_concluida": True,
        }

    return result
