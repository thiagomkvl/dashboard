import base64
import os
import streamlit as st

PAGE_TITLE = "Portal Financeiro Executivo"
PAGE_ICON = "🏢"

st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 0. AUTENTICAÇÃO
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False


def _obter_senha_mestre():
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
        return None
    return None


if not st.session_state["autenticado"]:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: "Inter", sans-serif; }
        .stApp { background-color: #f4f6f9; }
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        .login-title { font-size: 24px; font-weight: 800; color: #1e40af; margin-bottom: 5px; text-align: center; }
        .login-subtitle { font-size: 13px; color: #64748b; margin-bottom: 20px; font-weight: 500; text-align: center; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div class='login-title'>Portal Executivo</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='login-subtitle'>S.O.S. Cardio — Insira sua senha para acessar.</div>",
                unsafe_allow_html=
