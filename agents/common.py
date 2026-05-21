import os
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

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
from agents.prompts import PROMPTS


def _get_llm():
    api_key = os.getenv("GOOGLE_API_KEY", "")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=1.0,
        thinking_budget=0,
    )


TOOLS_TRIAGEM = [validar_cpf, autenticar_cliente, encerrar_atendimento]
TOOLS_CREDITO = [consultar_limite_credito, solicitar_aumento_limite, encerrar_atendimento]
TOOLS_ENTREVISTA = [calcular_e_atualizar_score, encerrar_atendimento]
TOOLS_CAMBIO = [consultar_cotacao, encerrar_atendimento]

TOOLS_MAP = {
    "triagem": TOOLS_TRIAGEM,
    "credito": TOOLS_CREDITO,
    "entrevista": TOOLS_ENTREVISTA,
    "cambio": TOOLS_CAMBIO,
}


def _build_agent_node(agente: str):
    def node(state: BancoAgilState) -> dict:
        llm = _get_llm()
        tools = TOOLS_MAP[agente]
        llm_with_tools = llm.bind_tools(tools)
        system_prompt = PROMPTS[agente]

        contexto = ""
        cpf = state.get("cpf_cliente", "")

        if agente == "triagem" and not state.get("autenticado"):
            tentativas_cpf = state.get("tentativas_cpf_invalido", 0)
            if tentativas_cpf > 0:
                restantes_cpf = 3 - tentativas_cpf
                if restantes_cpf <= 0:
                    contexto += (
                        f"\n\nALERTA DO SISTEMA: O cliente informou {tentativas_cpf} CPFs inválidos. "
                        f"Limite de 3 tentativas de CPF atingido — "
                        f"chame IMEDIATAMENTE `encerrar_atendimento` após informar o cliente.\n"
                    )
                else:
                    contexto += (
                        f"\n\nCONTEXTO DE VALIDAÇÃO DE CPF: {tentativas_cpf} CPF(s) inválido(s) "
                        f"informado(s). Restam {restantes_cpf} tentativa(s) antes do encerramento.\n"
                    )

            tentativas = state.get("tentativas_auth", 0)
            if tentativas > 0:
                restantes = 3 - tentativas
                if restantes <= 0:
                    contexto += (
                        f"\n\nALERTA DO SISTEMA — ENCERRAR AGORA: O cliente realizou {tentativas} "
                        f"tentativas de autenticação sem sucesso. Limite esgotado. "
                        f"AÇÃO OBRIGATÓRIA: diga ao cliente que não foi possível confirmar sua identidade "
                        f"e que o atendimento será encerrado por segurança. "
                        f"Em seguida, chame IMEDIATAMENTE `encerrar_atendimento`. "
                        f"NÃO solicite CPF nem data de nascimento novamente.\n"
                    )
                else:
                    contexto += (
                        f"\n\nCONTEXTO DE AUTENTICAÇÃO: {tentativas} chamada(s) a "
                        f"autenticar_cliente falharam. Restam {restantes} tentativa(s). "
                        f"Cada tentativa = uma chamada à ferramenta, não uma mensagem individual.\n"
                    )

            cpf_validado = state.get("cpf_validado", "")
            if cpf_validado and not state.get("autenticado"):
                contexto += (
                    f"\n\nCONTEXTO CPF VALIDADO: O CPF '{cpf_validado}' já passou pela validação matemática. "
                    f"NÃO solicite o CPF novamente. Vá direto ao passo 4: peça apenas a data de nascimento.\n"
                )

        if state.get("autenticado") and cpf:
            contexto += (
                f"\n\nCONTEXTO DO CLIENTE AUTENTICADO:\n"
                f"Nome: {state.get('nome_cliente') or 'N/A'}\n"
                f"CPF: {cpf}\n"
                f"Limite atual: R$ {state.get('limite_credito') or 0:,.2f}\n"
                f"Score atual: {state.get('score_cliente') or 0}\n"
            )
            if agente == "credito":
                contexto += (
                    f"\nEXEMPLO DE USO CORRETO: Se o cliente pedir aumento para R$ 8000, "
                    f"chame solicitar_aumento_limite com cpf='{cpf}' e novo_limite=8000.0\n"
                )

        messages = [SystemMessage(content=system_prompt + contexto)] + state["messages"]
        response = llm_with_tools.invoke(messages)

        encerrado = state.get("encerrado", False)
        if hasattr(response, "tool_calls"):
            for tc in response.tool_calls:
                if tc["name"] == "encerrar_atendimento":
                    encerrado = True

        novo_agente = state.get("agente_atual", agente)
        return {
            "messages": [response],
            "agente_atual": novo_agente,
            "encerrado": encerrado,
        }

    return node
