"""
Definição do estado compartilhado entre os agentes no grafo LangGraph.
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class BancoAgilState(TypedDict):
    """Estado global compartilhado por todos os agentes do Banco Ágil."""

    # Histórico de mensagens (acumulado automaticamente pelo LangGraph)
    messages: Annotated[list, add_messages]

    # Dados de autenticação
    autenticado: bool
    tentativas_auth: int
    tentativas_cpf_invalido: int
    cpf_cliente: Optional[str]
    nome_cliente: Optional[str]
    limite_credito: Optional[float]
    score_cliente: Optional[int]

    # Controle de fluxo
    agente_atual: str          # "triagem" | "credito" | "entrevista" | "cambio"
    encerrado: bool

    # Contexto da entrevista de crédito
    entrevista_concluida: bool
    entrevista_ofertada: bool     # True após rejeição de limite, aguardando resposta do cliente
