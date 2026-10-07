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
                unsafe_allow_html=True,
            )
            senha = st.text_input("Senha de Acesso", type="password", key="login_senha")
            if st.button("Entrar no Sistema", use_container_width=True, type="primary"):
                mestra = _obter_senha_mestre()
                if not mestra:
                    st.error("Nenhuma senha encontrada no secrets.toml")
                elif senha.strip() == mestra:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta. Tente novamente.")
    st.stop()


# ==============================================================================
# 1. HOME (somente boas-vindas — navegação só no menu lateral)
# ==============================================================================
def render_home_page() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: "Inter", sans-serif; color: #1e293b; }
        .stApp { background-color: #f4f6f9; }
        .main .block-container { max-width: 900px; padding-top: 3rem; padding-bottom: 2rem; }
        .hub-header { text-align: center; margin-top: 40px; }
        .hub-header h1 { font-size: 28px; font-weight: 800; color: #1e40af; margin: 0 0 10px 0; }
        .hub-header p { font-size: 15px; color: #64748b; margin: 0; line-height: 1.5; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="hub-header">
            <h1>{PAGE_TITLE}</h1>
            <p>Use o menu lateral para acessar os módulos do portal.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 2. NAVEGAÇÃO (menu lateral)
# ==============================================================================
page_home = st.Page(render_home_page, title="Home do Portal", icon=":material/home:", default=True)


def _page(path, title, url_path):
    if os.path.exists(path):
        return st.Page(path, title=title, url_path=url_path)
    return None


pages_ops = []
for path, title, url in [
    ("pages/Dashboard_Saldo.py", "Saldo Caixa", "Dashboard_Saldo"),
    ("pages/painel_fluxo_caixa.py", "Fluxo de Caixa", "painel_fluxo_caixa"),
    ("pages/Acompanhamento_Obra.py", "Despesas C/ Obras", "Acompanhamento_Obra"),
    ("pages/Análise_Faturamento.py", "Análise Faturamento", "Análise_Faturamento"),
    ("pages/painel_pagar.py", "Painel de Pagamentos", "painel_pagar"),
]:
    p = _page(path, title, url)
    if p is not None:
        pages_ops.append(p)

nav = {"Principal": [page_home]}
if pages_ops:
    nav["Módulos Operacionais"] = pages_ops

pg = st.navigation(nav)

with st.sidebar:
    st.markdown("### Minha Sessão")
    if st.button("Sair do Sistema", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()
    st.divider()

try:
    pg.run()
except Exception as e:
    st.error("Erro ao carregar a página:")
    st.exception(e)
