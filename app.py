import base64
import os
import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
PAGE_TITLE = "Portal Financeiro Executivo"
PAGE_ICON = "🏢"

st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 0. AUTENTICAÇÃO CENTRAL
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False


def _obter_senha_mestre():
    """Lê a senha dos secrets em diferentes formatos possíveis."""
    try:
        if "PASSWORD" in st.secrets:
            return str(st.secrets["PASSWORD"]).strip()
        if "password" in st.secrets:
            return str(st.secrets["password"]).strip()
        if "database" in st.secrets and "password" in st.secrets["database"]:
            return str(st.secrets["database"]["password"]).strip()
        if "auth" in st.secrets and "senha_mestre" in st.secrets["auth"]:
            return str(st.secrets["auth"]["senha_mestre"]).strip()
    except Exception:
        pass
    return None


if not st.session_state["autenticado"]:
    css_login = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .stApp { background-color: #f4f6f9; }
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }
    .login-title { font-size: 24px; font-weight: 800; color: #1e40af; margin-bottom: 5px; text-align: center; }
    .login-subtitle { font-size: 13px; color: #64748b; margin-bottom: 20px; font-weight: 500; text-align: center; }
    </style>
    """
    st.markdown(css_login, unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(
                "<div class='login-title'>🏢 Portal Executivo</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='login-subtitle'>S.O.S. Cardio - Insira sua senha para acessar.</div>",
                unsafe_allow_html=True,
            )

            # Sem st.form: evita problemas de estado em alguns ambientes
            senha_digitada = st.text_input(
                "Senha de Acesso",
                type="password",
                placeholder="Digite a senha...",
                key="login_senha",
            )
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)

            if st.button("Entrar no Sistema", use_container_width=True, type="primary"):
                senha_mestre = _obter_senha_mestre()

                if not senha_mestre:
                    st.error("⚠️ Nenhuma chave de senha foi encontrada no secrets.toml!")
                elif senha_digitada.strip() == senha_mestre:
                    st.session_state["autenticado"] = True
                    # limpa o campo da senha da sessão (opcional)
                    if "login_senha" in st.session_state:
                        del st.session_state["login_senha"]
                    st.rerun()
                else:
                    st.error("Senha incorreta. Tente novamente.")

    st.stop()


# ==============================================================================
# 1. FUNÇÕES DO HUB / HOME PORTAL
# ==============================================================================
CARD_PREVIEW_PATHS = {
    "saldos": "assets/preview_saldos.png",
    "fluxo": "assets/preview_fluxo.png",
    "pagar": "assets/preview_pagar.png",
}

MODULES = [
    {
        "title": "Dashboard de Saldos",
        "description": "Visão consolidada de todas as contas bancárias, aplicações e limites de crédito em tempo real.",
        "href": "Dashboard_Saldo",
        "image": CARD_PREVIEW_PATHS["saldos"],
    },
    {
        "title": "Fluxo de Caixa Analítico",
        "description": "Mapeamento da origem e destino do dinheiro, geração líquida e taxa de consumo sob a ótica de caixa.",
        "href": "painel_fluxo_caixa",
        "image": CARD_PREVIEW_PATHS["fluxo"],
    },
    {
        "title": "Painel de Pagamentos",
        "description": "Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e controle de saídas.",
        "href": "painel_pagar",
        "image": CARD_PREVIEW_PATHS["pagar"],
    },
]


def get_image_data_url(file_path: str) -> str:
    fallback = "linear-gradient(135deg, #eff6ff, #bfdbfe)"
    if not file_path or not os.path.exists(file_path):
        return fallback
    try:
        with open(file_path, "rb") as image_file:
            image_bytes = image_file.read()
    except OSError:
        return fallback
    extension = os.path.splitext(file_path)[1].lower().lstrip(".")
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/{extension};base64,{encoded}"


def get_background_style(image_data: str) -> str:
    if image_data.startswith("linear-gradient"):
        return f"background: {image_data};"
    return f"background-image: url('{image_data}');"


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f4f6f9;
    --surface: #ffffff;
    --primary-dark: #1e40af;
    --primary: #3b82f6;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow-sm: 0 4px 10px rgba(30, 64, 175, 0.05);
    --shadow-md: 0
