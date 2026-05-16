from agents.common import _build_agent_node
from utils.state import BancoAgilState


def cambio_node(state: BancoAgilState) -> dict:
    return _build_agent_node("cambio")(state)
