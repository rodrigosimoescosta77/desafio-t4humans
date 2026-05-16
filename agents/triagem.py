from agents.common import _build_agent_node
from utils.state import BancoAgilState


def triagem_node(state: BancoAgilState) -> dict:
    return _build_agent_node("triagem")(state)
