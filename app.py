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
# 0. AUTENTICAÇÃO CENTRAL (única no projeto)
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    css_login = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .stApp { background-color: #0a1020; }
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }
    .login-title { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 5px; text-align: center; }
    .login-subtitle { font-size: 13px; color: #8fa3c4; margin-bottom: 20px; font-weight: 500; text-align: center; }
    </style>
    """
    st.markdown(css_login, unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div class='login-title'>🏢 Portal Executivo</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='login-subtitle'>S.O.S. Cardio — Insira sua senha para acessar.</div>",
                unsafe_allow_html=True,
            )
            with st.form("form_login_portal"):
                senha_digitada = st.text_input(
                    "Senha de Acesso",
                    type="password",
                    placeholder="Digite a senha...",
                )
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                botao_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)

                if botao_entrar:
                    SENHA_MESTRE = None
                    try:
                        if "PASSWORD" in st.secrets:
                            SENHA_MESTRE = st.secrets["PASSWORD"]
                        elif "database" in st.secrets and "password" in st.secrets["database"]:
                            SENHA_MESTRE = st.secrets["database"]["password"]
                        elif "auth" in st.secrets and "senha_mestre" in st.secrets["auth"]:
                            SENHA_MESTRE = st.secrets["auth"]["senha_mestre"]
                    except Exception:
                        pass

                    if not SENHA_MESTRE:
                        st.error("⚠️ Nenhuma chave de senha foi encontrada no secrets.toml!")
                    else:
                        if senha_digitada.strip() == str(SENHA_MESTRE).strip():
                            st.session_state.autenticado = True
                            st.rerun()
                        else:
                            st.error("Senha incorreta. Tente novamente.")
    st.stop()  # bloqueia tudo abaixo (hub + páginas) até autenticar


# ==============================================================================
# 1. HUB / HOME
# ==============================================================================
CARD_PREVIEW_PATHS = {
    "saldos": "assets/preview_saldos.png",
    "fluxo": "assets/preview_fluxo.png",
    "pagar": "assets/preview_pagar.png",
    "obra": "assets/preview_obra.png",
    "faturamento": "assets/preview_faturamento.png",
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
    {
        "title": "Despesas com Obras",
        "description": "Acompanhamento orçamentário de obras, realizado vs orçado, fluxo de caixa e fases.",
        "href": "Acompanhamento_Obra",
        "image": CARD_PREVIEW_PATHS["obra"],
    },
    {
        "title": "Análise de Faturamento",
        "description": "Faturamento por convênio, situação das contas, inadimplência e taxa de liquidação.",
        "href": "Análise_Faturamento",
        "image": CARD_PREVIEW_PATHS["faturamento"],
    },
]


def get_image_data_url(file_path: str) -> str:
    fallback = "linear-gradient(135deg, #1e3a5f, #0f1a2e)"
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

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: #e6ecf5; }
.stApp { background-color: #0a1020; }
.main .block-container { max-width: 1100px; padding-top: 3rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stSidebar"] { background: #0b1326 !important; border-right: 1px solid #1a2744; }
.stButton > button {
    background: linear-gradient(135deg, #f97316, #ea580c); color: #fff;
    border: none; border-radius: 10px; font-weight: 700;
}

.hub-header { text-align: center; margin-bottom: 40px; }
.hub-header h1 { font-size: 32px; font-weight: 800; color: #fff; margin-bottom: 8px; letter-spacing: -0.5px; }
.hub-header p { font-size: 15px; color: #8fa3c4; font-weight: 500; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; padding: 10px; }
.hub-card {
    background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 12px;
    text-decoration: none; display: flex; flex-direction: column;
    transition: all 0.3s ease; cursor: pointer; overflow: hidden;
}
.hub-card:hover { transform: translateY(-4px); border-color: #3b82f6; box-shadow: 0 10px 24px rgba(59,130,246,0.15); }
.card-image { width: 100%; height: 150px; background-size: cover; background-position: top left; background-repeat: no-repeat; border-bottom: 1px solid #1c2a47; transition: transform 0.5s ease; }
.hub-card:hover .card-image { transform: scale(1.03); }
.image-container { width: 100%; height: 150px; overflow: hidden; border-radius: 12px 12px 0 0; }
.card-content { padding: 18px; display: flex; flex-direction: column; flex: 1; }
.card-title { font-size: 15px; font-weight: 800; color: #fff; margin-bottom: 8px; }
.card-desc { font-size: 12px; color: #8fa3c4; line-height: 1.5; font-weight: 500; margin-bottom: 10px; }
.card-arrow { margin-top: auto; align-self: flex-end; color: #3b4a6b; font-size: 16px; font-weight: bold; transition: color 0.3s ease; }
.hub-card:hover .card-arrow { color: #3b82f6; }
</style>
"""


def render_home_page() -> None:
    cards_html = []
    for module in MODULES:
        image_data = get_image_data_url(module["image"])
        bg_style = get_background_style(image_data)
        card = (
            f'<a href="{module["href"]}" target="_self" class="hub-card">'
            f'<div class="image-container"><div class="card-image" style="{bg_style}"></div></div>'
            f'<div class="card-content">'
            f'<div class="card-title">{module["title"]}</div>'
            f'<div class="card-desc">{module["description"]}</div>'
            f'<div class="card-arrow">➔</div>'
            f"</div></a>"
        )
        cards_html.append(card)

    html_hub = (
        f'<div class="hub-header">'
        f"<h1>{PAGE_TITLE}</h1>"
        f"<p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>"
        f"</div>"
        f'<div class="card-grid">{"".join(cards_html)}</div>'
    )
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(html_hub.replace("\n", " "), unsafe_allow_html=True)


# ==============================================================================
# 2. NAVEGAÇÃO
# ==============================================================================
page_home = st.Page(render_home_page, title="Home do Portal", icon="🏢", default=True)

page_saldos = st.Page("pages/Dashboard_Saldo.py", title="Saldo Caixa", url_path="Dashboard_Saldo")
page_fluxo = st.Page("pages/painel_fluxo_caixa.py", title="Fluxo de Caixa", url_path="painel_fluxo_caixa")
page_pagar = st.Page("pages/painel_pagar.py", title="Painel de Pagamentos", url_path="painel_pagar")
page_obra = st.Page("pages/Acompanhamento_Obra.py", title="Despesas C/ Obras", url_path="Acompanhamento_Obra")
page_faturamento = st.Page("pages/Análise_Faturamento.py", title="Análise Faturamento", url_path="Análise_Faturamento")

nav_structure = {
    "Principal": [page_home],
    "Módulos Operacionais": [page_saldos, page_fluxo, page_pagar, page_obra, page_faturamento],
}

pg = st.navigation(nav_structure)

# ==============================================================================
# 3. SIDEBAR + EXECUÇÃO
# ==============================================================================
with st.sidebar:
    st.markdown("### 👤 Minha Sessão")
    if st.button("🔒 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.markdown("---")

pg.run()
