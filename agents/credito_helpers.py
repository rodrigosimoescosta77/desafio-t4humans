import re
from langchain_core.messages import HumanMessage

from agents.common import _get_llm
from tools.ferramentas import solicitar_aumento_limite
from utils.state import BancoAgilState

AUMENTO_KEYWORDS = [
    "aumento", "aumentar", "solicitar", "quero mais", "subir",
    "elevar", "limite para", "para r$",
]


def is_aumento_request(texto: str) -> bool:
    texto_lower = texto.lower()
    return any(k in texto_lower for k in AUMENTO_KEYWORDS)


def extrair_valor(texto: str) -> float | None:
    texto_norm = texto.replace(".", "").replace(",", ".")
    matches = re.findall(r"\d+(?:\.\d{1,2})?", texto_norm)
    for m in matches:
        try:
            v = float(m)
            if v > 100:
                return v
        except ValueError:
            continue
    return None


def processar_solicitacao_aumento(state: BancoAgilState, valor: float) -> dict | None:
    cpf = state.get("cpf_cliente", "")
    if not cpf:
        return None

    resultado = solicitar_aumento_limite.invoke({"cpf": cpf, "novo_limite": valor})
    if "erro" in resultado:
        return None

    status = resultado.get("status", "")
    novo_limite_val = resultado.get("novo_limite_solicitado", valor)
    limite_maximo = resultado.get("limite_maximo_permitido", 0)
    nome = state.get("nome_cliente", "cliente")

    if status == "aprovado":
        dados_resultado = (
            f"RESULTADO DO SISTEMA: Solicitação de aumento para "
            f"R$ {novo_limite_val:,.2f} APROVADA."
        )
        instrucao = "Comunique a aprovação de forma positiva e parabenize o cliente."
    else:
        dados_resultado = (
            f"RESULTADO DO SISTEMA: Solicitação de aumento para "
            f"R$ {novo_limite_val:,.2f} REJEITADA. "
            f"Limite máximo permitido pelo score atual: R$ {limite_maximo:,.2f}."
        )
        instrucao = (
            "Informe a rejeição com empatia e explique que o score atual não permite "
            "esse valor. Em seguida, pergunte APENAS: 'Deseja fazer uma entrevista de "
            "crédito para tentar melhorar seu score?' — nada mais."
        )

    prompt = (
        f"Você é o assistente bancário do Banco Ágil atendendo {nome}.\n\n"
        f"{dados_resultado}\n\n"
        f"Tarefa: {instrucao}\n\n"
        f"Regras: Seja cordial e direto. Não mencione agentes, departamentos, "
        f"sistemas internos ou ferramentas. Não faça perguntas adicionais."
    )
    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    updates = {
        "messages": [response],
        "agente_atual": "credito",
        "encerrado": False,
        "entrevista_ofertada": status == "rejeitado",
    }
    if status == "aprovado":
        updates["limite_credito"] = novo_limite_val
    return updates
