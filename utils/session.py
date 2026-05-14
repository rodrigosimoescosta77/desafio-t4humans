"""
Gerenciador de sessão do Banco Ágil.
Mantém o estado da conversa e coordena as transições entre agentes.
"""

import re
from typing import Optional
from langchain_core.messages import HumanMessage

from agents.graph import banco_graph
from utils.state import BancoAgilState


class BancoAgilSession:
    """Gerencia uma sessão de atendimento completa."""

    # Palavras-chave para detecção de intenção
    _KEYWORDS_CREDITO = [
        "crédito", "credito", "limite", "aumento", "aumentar", "cartão", "cartao"
    ]
    _KEYWORDS_CAMBIO = [
        "câmbio", "cambio", "cotação", "cotacao", "dólar", "dolar", "euro",
        "moeda", "libra", "dólares"
    ]
    _KEYWORDS_ENTREVISTA = [
        "entrevista", "score", "pontuação", "pontuacao", "análise financeira"
    ]

    def __init__(self):
        self.state: BancoAgilState = {
            "messages": [],
            "autenticado": False,
            "tentativas_auth": 0,
            "cpf_cliente": None,
            "nome_cliente": None,
            "limite_credito": None,
            "score_cliente": None,
            "agente_atual": "triagem",
            "encerrado": False,
            "entrevista_concluida": False,
        }
        self._iniciado = False

    @property
    def encerrado(self) -> bool:
        return self.state.get("encerrado", False)

    @property
    def autenticado(self) -> bool:
        return self.state.get("autenticado", False)

    @property
    def agente_atual(self) -> str:
        return self.state.get("agente_atual", "triagem")

    def _detectar_intencao(self, texto: str) -> Optional[str]:
        """Detecta a intenção do cliente e retorna o agente adequado."""
        texto_lower = texto.lower()
        if any(k in texto_lower for k in self._KEYWORDS_CAMBIO):
            return "cambio"
        if any(k in texto_lower for k in self._KEYWORDS_CREDITO):
            return "credito"
        if any(k in texto_lower for k in self._KEYWORDS_ENTREVISTA):
            return "entrevista"
        return None

    def _atualizar_agente_por_intencao(self, texto: str):
        """Atualiza o agente atual baseado na intenção detectada na mensagem."""
        if self.autenticado and self.agente_atual == "triagem":
            intencao = self._detectar_intencao(texto)
            if intencao:
                self.state["agente_atual"] = intencao

    def _verificar_redirecionamento_pos_entrevista(self):
        """Redireciona para crédito após conclusão da entrevista."""
        if self.state.get("entrevista_concluida") and self.agente_atual == "entrevista":
            self.state["agente_atual"] = "credito"
            self.state["entrevista_concluida"] = False

    def processar_mensagem(self, mensagem: str) -> str:
        """
        Processa uma mensagem do usuário e retorna a resposta do agente.
        
        Returns:
            Texto da resposta do agente.
        """
        if self.encerrado:
            return "O atendimento foi encerrado. Por favor, inicie uma nova conversa."

        # Detectar intenção antes de adicionar mensagem
        self._atualizar_agente_por_intencao(mensagem)

        # Adicionar mensagem do usuário ao estado
        human_msg = HumanMessage(content=mensagem)
        self.state["messages"].append(human_msg)

        # Invocar o grafo
        try:
            novo_estado = banco_graph.invoke(self.state)
            self.state.update(novo_estado)
        except Exception as e:
            self.state["messages"].pop()  # Remove mensagem problemática
            return f"Desculpe, ocorreu um erro interno. Por favor, tente novamente. (Erro: {str(e)})"

        # Verificar redirecionamento pós-entrevista
        self._verificar_redirecionamento_pos_entrevista()

        # Extrair última resposta do assistente
        resposta = self._extrair_ultima_resposta()
        return resposta

    def _extrair_ultima_resposta(self) -> str:
        """Extrai o texto da última mensagem do assistente."""
        msgs = self.state.get("messages", [])
        for msg in reversed(msgs):
            if hasattr(msg, "content") and not isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str) and content.strip():
                    return content
                elif isinstance(content, list):
                    textos = [
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    ]
                    texto = " ".join(t for t in textos if t.strip())
                    if texto:
                        return texto
        return "Desculpe, não consegui processar sua solicitação. Poderia repetir?"

    def iniciar(self) -> str:
        """Inicia o atendimento com a saudação do agente de triagem."""
        if not self._iniciado:
            self._iniciado = True
            return self.processar_mensagem("iniciar atendimento")
        return ""

    def get_info_cliente(self) -> dict:
        """Retorna informações do cliente autenticado para exibição na UI."""
        if not self.autenticado:
            return {}
        return {
            "nome": self.state.get("nome_cliente", ""),
            "cpf": self.state.get("cpf_cliente", ""),
            "limite": self.state.get("limite_credito", 0),
            "score": self.state.get("score_cliente", 0),
            "agente": self.agente_atual,
        }
