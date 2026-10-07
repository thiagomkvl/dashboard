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
# 1. HOME
# ==============================================================================
CARD_PREVIEW_PATHS = {
    "saldos": "assets/preview_saldos.png",
    "fluxo": "assets/preview_fluxo.png",
    "pagar": "assets/preview_pagar.png",
}

MODULES = [
    {
        "title": "Dashboard de Saldos",
        "description": "Visão consolidada de contas bancárias, aplicações e limites de crédito.",
        "href": "Dashboard_Saldo",
        "image": CARD_PREVIEW_PATHS["saldos"],
    },
    {
        "title": "Fluxo de Caixa Analítico",
        "description": "Origem e destino do dinheiro, geração líquida e taxa de consumo.",
        "href": "painel_fluxo_caixa",
        "image": CARD_PREVIEW_PATHS["fluxo"],
    },
    {
        "title": "Painel de Pagamentos",
        "description": "Passivos, curva ABC de fornecedores e aging de vencimentos.",
        "href": "painel_pagar",
        "image": CARD_PREVIEW_PATHS["pagar"],
    },
]


def get_image_data_url(file_path: str) -> str:
    fallback = "linear-gradient(135deg, #eff6ff, #bfdbfe)"
    if not file_path or not os.path.exists(file_path):
        return fallback
    try:
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(file_path)[1].lower().lstrip(".") or "png"
        return f"data:image/{ext};base64,{encoded}"
    except OSError:
        return fallback


def render_home_page() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: "Inter", sans-serif; color: #1e293b; }
        .stApp { background-color: #f4f6f9; }
        .main .block-container { max-width: 1100px; padding-top: 2rem; padding-bottom: 2rem; }
        .hub-header { text-align: center; margin-bottom: 32px; }
        .hub-header h1 { font-size: 28px; font-weight: 800; color: #1e40af; margin: 0 0 8px 0; }
        .hub-header p { font-size: 14px; color: #64748b; margin: 0; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
        .hub-card {
            background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
            text-decoration: none; color: inherit; display: block; overflow: hidden;
            box-shadow: 0 4px 10px rgba(30, 64, 175, 0.05);
        }
        .hub-card:hover { border-color: #bfdbfe; box-shadow: 0 10px 20px rgba(30, 64, 175, 0.12); }
        .card-image { width: 100%; height: 140px; background-size: cover; background-position: center; }
        .card-content { padding: 16px 18px 18px; }
        .card-title { font-size: 15px; font-weight: 800; color: #1e40af; margin-bottom: 6px; }
        .card-desc { font-size: 12px; color: #64748b; line-height: 1.45; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="hub-header">
            <h1>{PAGE_TITLE}</h1>
            <p>Selecione um módulo no menu lateral ou nos cards abaixo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cards = []
    for m in MODULES:
        img = get_image_data_url(m["image"])
        bg = f"background-image:url('{img}');" if img.startswith("data:") else f"background:{img};"
        cards.append(
            f'<a class="hub-card" href="{m["href"]}" target="_self">'
            f'<div class="card-image" style="{bg}"></div>'
            f'<div class="card-content">'
            f'<div class="card-title">{m["title"]}</div>'
            f'<div class="card-desc">{m["description"]}</div>'
            f"</div></a>"
        )
    st.markdown(f'<div class="card-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


# ==============================================================================
# 2. NAVEGAÇÃO
# ==============================================================================
page_home = st.Page(render_home_page, title="Home do Portal", icon=":material/home:", default=True)

# Só registra páginas cujo arquivo existe (evita tela branca se faltar algum .py)
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
