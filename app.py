"""
Interface Streamlit do Banco Ágil — Sistema de Atendimento Inteligente.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Garantir que o diretório raiz esteja no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from utils.session import BancoAgilSession

# Usa a função interna _html diretamente, contornando o wrapper de deprecação
# que emite "Please replace components.v1.html with st.iframe" a cada render.
_html = st._main._html

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Banco Ágil — Atendimento",
    page_icon="🏦",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS customizado — estilo bancário moderno, sóbrio e elegante
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Toolbar do Streamlit recolhida, aparece no hover */
header[data-testid="stHeader"] {
    opacity: 0 !important;
    transition: opacity 0.3s ease !important;
}
header[data-testid="stHeader"]:hover {
    opacity: 1 !important;
}

/* Evita o escurecimento/flicker durante reruns do Streamlit */
[data-stale="true"], [data-stale="true"] * {
    opacity: 1 !important;
    filter: none !important;
    transition: none !important;
}

/* Esconde o iframe do components.html sem afetar execução */
iframe[height="1"] {
    display: block !important;
    visibility: hidden !important;
    height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
}

/* Reset e base */
html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
}

/* Fundo principal */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1627 50%, #0a1520 100%);
    min-height: 100vh;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1627 0%, #0a1a2e 100%);
    border-right: 1px solid rgba(0, 180, 216, 0.15);
}

section[data-testid="stSidebar"] * {
    color: #e0e8f0 !important;
}

/* Header do chat */
.bank-header {
    background: linear-gradient(90deg, #00b4d8, #0077b6);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 32px rgba(0, 180, 216, 0.25);
}

.bank-header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: white !important;
    margin: 0;
    letter-spacing: -0.5px;
}

.bank-header p {
    color: rgba(255,255,255,0.8) !important;
    margin: 0;
    font-size: 0.85rem;
}

/* Chat container */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 8px 0;
}

/* Mensagens do usuário */
.msg-user {
    background: linear-gradient(135deg, #0077b6, #023e8a);
    color: #ffffff !important;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    max-width: 75%;
    align-self: flex-end;
    margin-left: auto;
    font-size: 0.92rem;
    line-height: 1.5;
    box-shadow: 0 2px 12px rgba(0, 119, 182, 0.3);
}

/* Mensagens do agente */
.msg-agent {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 180, 216, 0.2);
    color: #e0e8f0;
    border-radius: 18px 18px 18px 4px;
    padding: 12px 18px;
    max-width: 80%;
    font-size: 0.92rem;
    line-height: 1.6;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.msg-agent *, .msg-user * {
    background: transparent !important;
    color: inherit !important;
    margin: 0 !important;
}

/* Badge do agente */
.agent-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(0, 180, 216, 0.12);
    border: 1px solid rgba(0, 180, 216, 0.3);
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    color: #00b4d8;
    margin-bottom: 6px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* Card de info do cliente */
.client-card {
    background: linear-gradient(135deg, rgba(0,180,216,0.08), rgba(0,119,182,0.08));
    border: 1px solid rgba(0, 180, 216, 0.25);
    border-radius: 14px;
    padding: 18px;
    margin: 12px 0;
}

.client-card h4 {
    color: #00b4d8 !important;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
}

.client-metric {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 0.85rem;
    color: #a0b4c8 !important;
}

.client-metric span:last-child {
    color: #e0e8f0 !important;
    font-weight: 500;
}

/* Status dot */
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00b4d8;
    display: inline-block;
    animation: pulse 2s infinite;
    margin-right: 6px;
}

@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0,180,216,0.4); }
    50% { opacity: 0.8; box-shadow: 0 0 0 6px rgba(0,180,216,0); }
}

/* Input de texto */
.stTextInput input, .stChatInput textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(0, 180, 216, 0.3) !important;
    border-radius: 12px !important;
    color: #0a1628 !important;
    font-family: 'Sora', sans-serif !important;
}

.stTextInput input:focus, .stChatInput textarea:focus {
    border-color: #00b4d8 !important;
    box-shadow: 0 0 0 2px rgba(0, 180, 216, 0.15) !important;
}

/* Botões */
.stButton button {
    background: linear-gradient(135deg, #0077b6, #023e8a) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.stButton button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(0, 119, 182, 0.4) !important;
}

/* Mensagem de encerramento */
.msg-encerrado {
    background: linear-gradient(135deg, rgba(0,180,216,0.1), rgba(0,119,182,0.1));
    border: 1px solid rgba(0, 180, 216, 0.3);
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
    color: #90caf9;
    font-size: 0.88rem;
    margin-top: 12px;
}

/* Spinner / loading */
.stSpinner {
    color: #00b4d8 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,180,216,0.3); border-radius: 3px; }

/* Remover bordas padrão do Streamlit */
div[data-testid="stChatMessageContent"] {
    background: transparent !important;
}

/* Título da sidebar */
.sidebar-title {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: rgba(160,180,200,0.6) !important;
    margin-bottom: 8px;
}

/* Score bar */
.score-bar-container {
    background: rgba(255,255,255,0.08);
    border-radius: 6px;
    height: 8px;
    margin-top: 4px;
    overflow: hidden;
}

.score-bar-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #0077b6, #00b4d8);
    transition: width 0.6s ease;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Estado da sessão Streamlit
# ---------------------------------------------------------------------------

def init_session():
    if "banco_session" not in st.session_state:
        st.session_state.banco_session = None
    if "historico_chat" not in st.session_state:
        st.session_state.historico_chat = []
    if "iniciado" not in st.session_state:
        st.session_state.iniciado = False


def reset_session():
    st.session_state.banco_session = None
    st.session_state.historico_chat = []
    st.session_state.iniciado = False


init_session()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 10px;">
        <div style="font-size: 3rem;">🏦</div>
        <div style="font-size: 1.2rem; font-weight: 700; color: #00b4d8;">Banco Ágil</div>
        <div style="font-size: 0.75rem; color: rgba(160,180,200,0.7); margin-top: 4px;">
            Atendimento Digital 24h
        </div>
    </div>
    <hr style="border-color: rgba(0,180,216,0.15); margin: 16px 0;">
    """, unsafe_allow_html=True)

    # Info do cliente autenticado
    session: BancoAgilSession = st.session_state.banco_session
    if session and session.autenticado:
        info = session.get_info_cliente()

        agente_labels = {
            "triagem": "🔐 Triagem",
            "credito": "💳 Crédito",
            "entrevista": "📋 Análise Financeira",
            "cambio": "💱 Câmbio",
        }
        agente_label = agente_labels.get(info.get("agente", "triagem"), "Atendimento")

        score = info.get("score", 0)
        score_pct = min(100, int(score / 10))

        st.markdown(f"""
        <div class="client-card">
            <h4>👤 Cliente Autenticado</h4>
            <div class="client-metric">
                <span>Nome</span>
                <span>{info.get('nome', '')}</span>
            </div>
            <div class="client-metric">
                <span>Limite atual</span>
                <span>R$ {info.get('limite', 0):,.2f}</span>
            </div>
            <div class="client-metric" style="border:none;">
                <span>Score</span>
                <span>{score} / 1000</span>
            </div>
            <div class="score-bar-container">
                <div class="score-bar-fill" style="width:{score_pct}%"></div>
            </div>
        </div>

        <div style="margin-top: 12px;">
            <div class="sidebar-title">Agente Ativo</div>
            <div style="font-size: 0.88rem; color: #00b4d8; font-weight: 600;">
                <span class="status-dot"></span>{agente_label}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding: 12px; text-align: center;">
            <div style="font-size: 0.8rem; color: rgba(160,180,200,0.6);">
                🔒 Nenhum cliente autenticado
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(0,180,216,0.15); margin: 16px 0;'>", unsafe_allow_html=True)

    # Botão de nova sessão
    if st.button("🔄 Nova Sessão", use_container_width=True):
        reset_session()
        st.rerun()
      
# ---------------------------------------------------------------------------
# Header principal
# ---------------------------------------------------------------------------

st.markdown("""
<div class="bank-header">
    <div style="font-size: 2.2rem;">🏦</div>
    <div>
        <h1>Banco Ágil</h1>
        <p><span class="status-dot"></span>Assistente Virtual · Atendimento 24 horas</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Iniciar sessão automaticamente
# ---------------------------------------------------------------------------

if not st.session_state.iniciado:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        st.warning(
            "⚠️ Defina a variável de ambiente `GOOGLE_API_KEY` para usar o sistema. "
            "Obtenha sua chave em: https://aistudio.google.com/apikey"
        )
        st.stop()

    with st.spinner("Iniciando atendimento..."):
        try:
            session = BancoAgilSession()
            resposta_inicial = session.iniciar()
            st.session_state.banco_session = session
            st.session_state.historico_chat = [
                {"role": "assistant", "content": resposta_inicial}
            ]
            st.session_state.iniciado = True
        except Exception as e:
            st.error(f"Erro ao iniciar o sistema: {e}")
            st.stop()

# ---------------------------------------------------------------------------
# Exibir histórico do chat
# ---------------------------------------------------------------------------

session: BancoAgilSession = st.session_state.banco_session

agente_icons = {
    "triagem": "🔐",
    "credito": "💳",
    "entrevista": "📋",
    "cambio": "💱",
}

agente_nomes = {
    "triagem": "Triagem",
    "credito": "Crédito",
    "entrevista": "Análise Financeira",
    "cambio": "Câmbio",
}

for msg in st.session_state.historico_chat:
    # Escapa $ para evitar interpretação LaTeX pelo Streamlit
    conteudo = msg['content'].replace('$', '&#36;')
    if msg["role"] == "user":
        st.markdown(f"""
        <div style="display:flex; justify-content:flex-end; margin: 6px 0;">
            <div class="msg-user">{conteudo}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        agente = msg.get("agente", "triagem")
        icon = agente_icons.get(agente, "🤖")
        nome = agente_nomes.get(agente, "Assistente")
        st.markdown(f"""
        <div style="margin: 6px 0;">
            <div class="agent-badge">{icon} {nome}</div>
            <div class="msg-agent">{conteudo}</div>
        </div>
        """, unsafe_allow_html=True)

# Mensagem de encerramento
if session and session.encerrado:
    st.markdown("""
    <div class="msg-encerrado">
        ✅ Atendimento encerrado. Clique em <b>Nova Sessão</b> para iniciar um novo atendimento.
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Input do usuário
# ---------------------------------------------------------------------------

def _processar_e_adicionar(msg: str):
    """Processa uma mensagem e adiciona ao histórico visual."""
    st.session_state.historico_chat.append({"role": "user", "content": msg})
    with st.spinner("Processando..."):
        try:
            resposta = session.processar_mensagem(msg)
            agente_atual = session.agente_atual
        except Exception:
            resposta = "Desculpe, ocorreu um erro. Por favor, tente novamente."
            agente_atual = "triagem"
    st.session_state.historico_chat.append({
        "role": "assistant", "content": resposta, "agente": agente_atual
    })
    st.rerun()


if not (session and session.encerrado):
    # Botões de escolha quando a entrevista de crédito for ofertada
    if session and session.state.get("entrevista_ofertada"):
        st.markdown("""
        <div style="text-align:center; margin: 16px 0 10px;
                    color: rgba(160,180,200,0.65); font-size: 0.78rem;
                    letter-spacing: 1px; text-transform: uppercase;">
            Deseja participar da entrevista de crédito?
        </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅  Sim, quero participar", use_container_width=True, key="btn_sim"):
                _processar_e_adicionar("sim, quero a entrevista de crédito")
        with col2:
            if st.button("❌  Não, obrigado", use_container_width=True, key="btn_nao"):
                _processar_e_adicionar("não, obrigado")
    else:
        user_input = st.chat_input("Digite sua mensagem...")
        if user_input and user_input.strip():
            _processar_e_adicionar(user_input.strip())

# Scroll automático: percorre o DOM do pai para encontrar o container scrollável real
_html("""
<script>
function scrollToBottom() {
    var doc = window.parent.document;
    // Percorre do body para baixo achando o elemento com scrollHeight > clientHeight
    var candidates = doc.querySelectorAll('*');
    var best = null;
    var bestScroll = 0;
    for (var i = 0; i < candidates.length; i++) {
        var el = candidates[i];
        var diff = el.scrollHeight - el.clientHeight;
        if (diff > bestScroll) {
            bestScroll = diff;
            best = el;
        }
    }
    if (best) {
        best.scrollTop = best.scrollHeight;
    } else {
        window.parent.scrollTo(0, 999999);
    }
}
scrollToBottom();
setTimeout(scrollToBottom, 200);
setTimeout(scrollToBottom, 600);
</script>
""", height=1)
