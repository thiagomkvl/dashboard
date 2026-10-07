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
# 0. LÓGICA DE AUTENTICAÇÃO E CONTROLE DE SESSÃO
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Tela de Login (Caso o usuário não esteja autenticado)
if not st.session_state.autenticado:
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

            with st.form("form_login_portal"):
                senha_digitada = st.text_input(
                    "Senha de Acesso",
                    type="password",
                    placeholder="Digite a senha...",
                )
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                botao_entrar = st.form_submit_button(
                    "Entrar no Sistema", use_container_width=True
                )

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
                        senha_input = senha_digitada.strip()
                        senha_esperada = str(SENHA_MESTRE).strip()

                        if senha_input == senha_esperada:
                            st.session_state.autenticado = True
                            st.rerun()
                        else:
                            st.error("Senha incorreta. Tente novamente.")

    st.stop()


# ==============================================================================
# 1. MENU CUSTOMIZADO E BOTÃO DE LOGOUT NA SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### 📌 Menu Principal")
    
    # Aqui você define EXATAMENTE o que vai aparecer no menu.
    # O primeiro parâmetro é o caminho real do arquivo, o label é o texto visível.
    st.page_link("app.py", label="🏠 Hub Inicial")
    st.page_link("pages/Dashboard_Saldo.py", label="💰 Dashboard de Saldos")
    st.page_link("pages/painel_fluxo_caixa.py", label="📊 Fluxo de Caixa")
    st.page_link("pages/painel_pagar.py", label="💸 Painel de Pagamentos")
    
    st.markdown("---")
    
    st.markdown("### 👤 Minha Sessão")
    if st.button("🔒 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.markdown("---")


# ==============================================================================
# 2. MÓDULOS E CARDS DO PORTAL
# ==============================================================================
CARD_PREVIEW_PATHS = {
    "saldos": "assets/preview_saldos.png",
    "fluxo": "assets/preview_fluxo.png",
    "pagar": "assets/preview_pagar.png",
}

MODULES = [
    {
        "title": "Dashboard de Saldos",
        "description": (
            "Visão consolidada de todas as contas bancárias, aplicações e limites de "
            "crédito em tempo real."
        ),
        "href": "Dashboard_Saldo",
        "image": CARD_PREVIEW_PATHS["saldos"],
    },
    {
        "title": "Fluxo de Caixa Analítico",
        "description": (
            "Mapeamento da origem e destino do dinheiro, geração líquida e taxa de "
            "consumo sob a ótica de caixa."
        ),
        "href": "painel_fluxo_caixa",
        "image": CARD_PREVIEW_PATHS["fluxo"],
    },
    {
        "title": "Painel de Pagamentos",
        "description": (
            "Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e "
            "controle de saídas."
        ),
        "href": "painel_pagar",
        "image": CARD_PREVIEW_PATHS["pagar"],
    },
]


def get_image_data_url(file_path: str) -> str:
    """Converte uma imagem local em um data URL válido para uso em HTML/CSS."""
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
    """Retorna uma propriedade de background para uso em elementos HTML."""
    if image_data.startswith("linear-gradient"):
        return f"background: {image_data};"
    return fPara fazer isso, vamos utilizar o sistema nativo de navegação introduzido nas versões mais recentes do Streamlit (`st.navigation` e `st.Page`). 

Com essa estrutura, **o Streamlit ignora a leitura automática da pasta `pages/`** e passa a renderizar no menu lateral **apenas** as páginas que você definir explicitamente no código, na ordem e categoria que você quiser. 

Outra vantagem é que transformamos a sua tela inicial (os cards) em uma página raiz oficial (`default=True`), o que evita conflitos e redirecionamentos estranhos.

Aqui está o código do seu `app.py` ajustado e otimizado:

```python
import base64
import os
import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
PAGE_TITLE = "Portal Financeiro Executivo"
PAGE_ICON = "🏢"

# O st.set_page_config SEMPRE deve ser o primeiro comando Streamlit
st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 0. LÓGICA DE AUTENTICAÇÃO E CONTROLE DE SESSÃO
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Tela de Login (Caso o usuário não esteja autenticado)
if not st.session_state.autenticado:
    css_login = """
    <style>
    @import url('[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap)');
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

            with st.form("form_login_portal"):
                senha_digitada = st.text_input(
                    "Senha de Acesso",
                    type="password",
                    placeholder="Digite a senha...",
                )
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                botao_entrar = st.form_submit_button(
                    "Entrar no Sistema", use_container_width=True
                )

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
                        senha_input = senha_digitada.strip()
                        senha_esperada = str(SENHA_MESTRE).strip()

                        if senha_input == senha_esperada:
                            st.session_state.autenticado = True
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
    """Converte uma imagem local em um data URL válido para uso em HTML/CSS."""
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
    """Retorna uma propriedade de background para uso em elementos HTML."""
    if image_data.startswith("linear-gradient"):
        return f"background: {image_data};"
    return f"background-image: url('{image_data}');"

CSS = """
<style>
@import url('[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap)');

:root {
    --bg: #f4f6f9;
    --surface: #ffffff;
    --primary-dark: #1e40af;
    --primary: #3b82f6;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow-sm: 0 4px 10px rgba(30, 64, 175, 0.05);
    --shadow-md: 0 10px 20px rgba(30, 64, 175, 0.12);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 1100px; padding-top: 3rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }

.hub-header { text-align: center; margin-bottom: 40px; }
.hub-header h1 { font-size: 32px; font-weight: 800; color: var(--primary-dark); margin-bottom: 8px; letter-spacing: -0.5px; }
.hub-header p { font-size: 15px; color: var(--text-muted); font-weight: 500; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 30px; padding: 10px; }
.hub-card {
    background-color: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    text-decoration: none; display: flex; flex-direction: column; box-shadow: var(--shadow-sm);
    transition: all 0.3s ease; cursor: pointer; position: relative; overflow: hidden;
}
.hub-card:hover { transform: translateY(-5px); box-shadow: var(--shadow-md); border-color: #bfdbfe; }
.card-image { width: 100%; height: 160px; background-size: cover; background-position: top left; background-repeat: no-repeat; border-bottom: 1px solid var(--border); transition: transform 0.5s ease; }
.hub-card:hover .card-image { transform: scale(1.03); }
.image-container { width: 100%; height: 160px; overflow: hidden; border-radius: 12px 12px 0 0; }
.card-content { padding: 20px; display: flex; flex-direction: column; flex: 1; }
.card-title { font-size: 16px; font-weight: 800; color: var(--primary-dark); margin-bottom: 8px; }
.card-desc { font-size: 12px; color: var(--text-muted); line-height: 1.5; font-weight: 500; margin-bottom: 10px; }
.card-arrow { margin-top: auto; align-self: flex-end; color: #cbd5e1; font-size: 16px; font-weight: bold; transition: color 0.3s ease; }
.hub-card:hover .card-arrow { color: var(--primary); }
</style>
"""

def render_home_page() -> None:
    """Função que renderiza a Home/Hub do Portal."""
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
            f'</div></a>'
        )
        cards_html.append(card)

    cards_joined = "".join(cards_html)
    html_hub = (
        f'<div class="hub-header">'
        f'<h1>{PAGE_TITLE}</h1>'
        f'<p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>'
        f'</div>'
        f'<div class="card-grid">{cards_joined}</div>'
    )

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(html_hub.replace('\n', ' '), unsafe_allow_html=True)


# ==============================================================================
# 2. SISTEMA DE NAVEGAÇÃO EXPLÍCITA (PÁGINAS DEFINIDAS NO CÓDIGO)
# ==============================================================================

# Página Inicial (Chama a função render_home_page definida acima)
page_home = st.Page(
    render_home_page, 
    title="Home do Portal", 
    icon="🏢", 
    default=True
)

# Páginas dos Dashboards (Mapeando explicitamente para os arquivos na pasta pages)
# Nota: O url_path DEVE ser idêntico ao href lá do MODULES para os cards continuarem funcionando.
page_saldos = st.Page("pages/Dashboard_Saldo.py", title="Saldos Bancários", icon="💰", url_path="Dashboard_Saldo")
page_fluxo = st.Page("pages/painel_fluxo_caixa.py", title="Fluxo de Caixa", icon="📉", url_path="painel_fluxo_caixa")
page_pagar = st.Page("pages/painel_pagar.py", title="Contas a Pagar", icon="💸", url_path="painel_pagar")

# Define a estrutura exata do menu lateral que será exibido
nav_structure = {
    "Principal": [page_home],
    "Módulos Operacionais": [page_saldos, page_fluxo, page_pagar]
}

# Inicia a navegação com base na estrutura acima (qualquer outro arquivo na pasta pages será IGNORADO)
pg = st.navigation(nav_structure)


# ==============================================================================
# 3. SIDEBAR GERAL E EXECUÇÃO
# ==============================================================================
with st.sidebar:
    st.markdown("### 👤 Minha Sessão")
    if st.button("🔒 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.markdown("---")

# Comando que de fato exibe a página selecionada
pg.run()
