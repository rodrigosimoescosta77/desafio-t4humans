"""
Grafo principal do sistema multi-agente Banco Ágil.
Orquestra os 4 agentes usando LangGraph com um StateGraph compartilhado.
"""

from langgraph.graph import END, START, StateGraph

from agents.credito import credito_node
from agents.cambio import cambio_node
from agents.entrevista import entrevista_node
from agents.router import (
    router_principal,
    router_pos_tool,
    router_tool_call,
    tool_node_handler,
)
from agents.triagem import triagem_node
from utils.state import BancoAgilState


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

    # Ponto de entrada condicional — rota para o agente correto com base no agente_atual
    graph.add_conditional_edges(
        START,
        router_principal,
        {
            "triagem": "triagem",
            "credito": "credito",
            "entrevista": "entrevista",
            "cambio": "cambio",
            END: END,
        },
    )

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
