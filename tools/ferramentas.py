"""
Ferramentas compartilhadas entre os agentes do Banco Ágil.
"""

import csv
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from langchain_core.tools import tool

# Paths
BASE_DIR = Path(__file__).parent.parent / "data"
CLIENTES_CSV = BASE_DIR / "clientes.csv"
SCORE_LIMITE_CSV = BASE_DIR / "score_limite.csv"
SOLICITACOES_CSV = BASE_DIR / "solicitacoes_aumento_limite.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalizar_cpf(cpf: str) -> str:
    """Remove formatação do CPF."""
    return re.sub(r"\D", "", cpf)


def _ler_clientes() -> list[dict]:
    with open(CLIENTES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _salvar_clientes(rows: list[dict]) -> None:
    fieldnames = ["cpf", "nome", "data_nascimento", "limite_credito", "score"]
    with open(CLIENTES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Ferramenta: Autenticação
# ---------------------------------------------------------------------------

@tool
def autenticar_cliente(cpf: str, data_nascimento: str) -> dict:
    """
    Autentica o cliente verificando CPF e data de nascimento na base de dados.
    Retorna dados do cliente se autenticado, ou erro caso contrário.
    data_nascimento deve estar no formato YYYY-MM-DD.
    """
    try:
        cpf_limpo = _normalizar_cpf(cpf)
        clientes = _ler_clientes()
        for cliente in clientes:
            cpf_base = _normalizar_cpf(cliente["cpf"])
            if cpf_base == cpf_limpo and cliente["data_nascimento"].strip() == data_nascimento.strip():
                return {
                    "autenticado": True,
                    "cpf": cliente["cpf"],
                    "nome": cliente["nome"],
                    "limite_credito": float(cliente["limite_credito"]),
                    "score": int(cliente["score"]),
                }
        return {"autenticado": False, "erro": "CPF ou data de nascimento incorretos."}
    except Exception as e:
        return {"autenticado": False, "erro": f"Erro ao acessar base de dados: {str(e)}"}


# ---------------------------------------------------------------------------
# Ferramenta: Consulta de Limite
# ---------------------------------------------------------------------------

@tool
def consultar_limite_credito(cpf: str) -> dict:
    """
    Consulta o limite de crédito atual e score do cliente pelo CPF.
    """
    try:
        cpf_limpo = _normalizar_cpf(cpf)
        clientes = _ler_clientes()
        for cliente in clientes:
            if _normalizar_cpf(cliente["cpf"]) == cpf_limpo:
                return {
                    "cpf": cliente["cpf"],
                    "nome": cliente["nome"],
                    "limite_credito": float(cliente["limite_credito"]),
                    "score": int(cliente["score"]),
                }
        return {"erro": "Cliente não encontrado."}
    except Exception as e:
        return {"erro": f"Erro ao acessar base de dados: {str(e)}"}


# ---------------------------------------------------------------------------
# Ferramenta: Solicitar Aumento de Limite
# ---------------------------------------------------------------------------

@tool
def solicitar_aumento_limite(cpf: str, novo_limite: float) -> dict:
    """
    Registra e avalia uma solicitação de aumento de limite de crédito.
    Verifica o score atual do cliente e aprova ou rejeita conforme score_limite.csv.
    """
    try:
        cpf_limpo = _normalizar_cpf(cpf)
        clientes = _ler_clientes()
        cliente_dados = None
        for c in clientes:
            if _normalizar_cpf(c["cpf"]) == cpf_limpo:
                cliente_dados = c
                break

        if not cliente_dados:
            return {"erro": "Cliente não encontrado."}

        limite_atual = float(cliente_dados["limite_credito"])
        score_atual = int(cliente_dados["score"])

        # Verificar score x limite permitido
        limite_permitido = 0.0
        with open(SCORE_LIMITE_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if int(row["score_minimo"]) <= score_atual <= int(row["score_maximo"]):
                    limite_permitido = float(row["limite_maximo"])
                    break

        status = "aprovado" if novo_limite <= limite_permitido else "rejeitado"
        timestamp = datetime.now().isoformat()

        # Registrar no CSV de solicitações
        with open(SOLICITACOES_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["cpf_cliente", "data_hora_solicitacao", "limite_atual",
                            "novo_limite_solicitado", "status_pedido"]
            )
            # Escrever cabeçalho se arquivo vazio
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow({
                "cpf_cliente": cliente_dados["cpf"],
                "data_hora_solicitacao": timestamp,
                "limite_atual": limite_atual,
                "novo_limite_solicitado": novo_limite,
                "status_pedido": status,
            })

        return {
            "status": status,
            "cpf": cliente_dados["cpf"],
            "nome": cliente_dados["nome"],
            "limite_atual": limite_atual,
            "novo_limite_solicitado": novo_limite,
            "score_atual": score_atual,
            "limite_maximo_permitido": limite_permitido,
            "timestamp": timestamp,
        }
    except Exception as e:
        return {"erro": f"Erro ao processar solicitação: {str(e)}"}


# ---------------------------------------------------------------------------
# Ferramenta: Calcular e Atualizar Score
# ---------------------------------------------------------------------------

@tool
def calcular_e_atualizar_score(
    cpf: str,
    renda_mensal: float,
    tipo_emprego: str,
    despesas_mensais: float,
    num_dependentes: int,
    tem_dividas: str,
) -> dict:
    """
    Calcula o novo score de crédito do cliente com base em dados financeiros
    e atualiza a base de dados (clientes.csv).

    Parâmetros:
        cpf: CPF do cliente.
        renda_mensal: Renda mensal em reais.
        tipo_emprego: 'formal', 'autônomo' ou 'desempregado'.
        despesas_mensais: Total de despesas fixas mensais em reais.
        num_dependentes: Número de dependentes (0, 1, 2 ou 3+).
        tem_dividas: 'sim' ou 'não'.
    """
    try:
        peso_renda = 30
        peso_emprego = {"formal": 300, "autônomo": 200, "desempregado": 0}
        peso_dependentes = {0: 100, 1: 80, 2: 60, 3: 30}
        peso_dividas = {"sim": -100, "não": 100}

        emp_key = tipo_emprego.lower().strip()
        emp_score = peso_emprego.get(emp_key, 0)

        dep_key = min(num_dependentes, 3)
        dep_score = peso_dependentes.get(dep_key, 30)

        div_key = tem_dividas.lower().strip()
        div_score = peso_dividas.get(div_key, 0)

        score_raw = (
            (renda_mensal / (despesas_mensais + 1)) * peso_renda
            + emp_score
            + dep_score
            + div_score
        )
        novo_score = max(0, min(1000, int(score_raw)))

        # Atualizar clientes.csv
        cpf_limpo = _normalizar_cpf(cpf)
        clientes = _ler_clientes()
        atualizado = False
        for c in clientes:
            if _normalizar_cpf(c["cpf"]) == cpf_limpo:
                score_antigo = int(c["score"])
                c["score"] = str(novo_score)
                atualizado = True
                break

        if not atualizado:
            return {"erro": "Cliente não encontrado para atualização."}

        _salvar_clientes(clientes)

        return {
            "cpf": cpf,
            "score_anterior": score_antigo,
            "score_novo": novo_score,
            "mensagem": "Score atualizado com sucesso.",
        }
    except Exception as e:
        return {"erro": f"Erro ao calcular score: {str(e)}"}


# ---------------------------------------------------------------------------
# Ferramenta: Cotação de Moeda
# ---------------------------------------------------------------------------

@tool
def consultar_cotacao(moeda: str = "USD") -> dict:
    """
    Consulta a cotação atual de uma moeda em relação ao Real (BRL).
    Moedas suportadas: USD, EUR, GBP, ARS, etc.
    """
    try:
        url = f"https://economia.awesomeapi.com.br/json/last/{moeda}-BRL"
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        key = f"{moeda}BRL"
        if key not in data:
            return {"erro": f"Moeda '{moeda}' não encontrada."}
        info = data[key]
        return {
            "moeda": moeda,
            "nome": info.get("name", moeda),
            "compra": float(info["bid"]),
            "venda": float(info["ask"]),
            "variacao": info.get("pctChange", "N/A"),
            "atualizacao": info.get("create_date", "N/A"),
        }
    except requests.exceptions.RequestException as e:
        return {"erro": f"Falha ao consultar cotação (API indisponível): {str(e)}"}
    except Exception as e:
        return {"erro": f"Erro inesperado: {str(e)}"}


# ---------------------------------------------------------------------------
# Ferramenta: Encerrar Atendimento
# ---------------------------------------------------------------------------

@tool
def encerrar_atendimento() -> dict:
    """
    Encerra o atendimento atual. Deve ser chamada quando o cliente solicitar
    o fim da conversa ou quando o fluxo chegar ao encerramento natural.
    """
    return {"encerrado": True, "mensagem": "Atendimento encerrado com sucesso."}
