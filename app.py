import streamlit as st
import base64
import os
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Financeiro Executivo", layout="wide", page_icon="🏢")

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
    .login-container {
        max-width: 400px;
        margin: 80px auto;
        padding: 40px;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 25px rgba(30, 64, 175, 0.08);
        text-align: center;
    }
    .login-title { font-size: 22px; font-weight: 800; color: #1e40af; margin-bottom: 8px; }
    .login-subtitle { font-size: 13px; color: #64748b; margin-bottom: 25px; font-weight: 500; }
    </style>
    """
    st.markdown(textwrap.dedent(css_login), unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
        with st.form("form_login_portal"):
            st.markdown("<div class='login-title'>🏢 Portal Executivo</div>", unsafe_allow_html=True)
            st.markdown("<div class='login-subtitle'>Insira sua senha corporativa para acessar.</div>", unsafe_allow_html=True)
            
            senha_digitada = st.text_input("Senha de Acesso", type="password", placeholder="Digite a senha...")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            botao_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if botao_entrar:
                SENHA_MESTRE = "S@SCARDIO2k26"
                
                if senha_digitada == SENHA_MESTRE:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Senha incorreta. Tente novamente.")
    st.stop()  # Interrompe a execução para não carregar o portal se não estiver logado

# ==============================================================================
# 1. FUNÇÃO PARA CARREGAR IMAGENS LOCAIS (BLINDAGEM STREAMLIT)
# ==============================================================================
def get_img_b64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            ext = filepath.split('.')[-1]
            return f"data:image/{ext};base64,{b64}"
    else:
        return "linear-gradient(135deg, #eff6ff, #bfdbfe)"

# --- CAMINHOS DAS IMAGENS ---
img_saldos = get_img_b64("assets/preview_saldos.png")
img_fluxo = get_img_b64("assets/preview_fluxo.png")
img_pagar = get_img_b64("assets/preview_pagar.png")

def bg_style(img_data):
    if img_data.startswith("linear-gradient"):
        return f"background: {img_data};"
    else:
        return f"background-image: url('{img_data}');"


# ==============================================================================
# 2. CUSTOM CSS — ESTILO PORTAL COM THUMBNAILS E LOGOUT
# ==============================================================================
css = """
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
    --shadow-md: 0 10px 20px rgba(30, 64, 175, 0.12);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 1100px; padding-top: 2rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }

/* CABEÇALHO DO HUB E BOTÃO DE SAIR */
.hub-top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid var(--border); padding-bottom: 15px; }
.hub-header h1 { font-size: 28px; font-weight: 800; color: var(--primary-dark); margin: 0 0 4px 0; letter-spacing: -0.5px; }
.hub-header p { font-size: 14px; color: var(--text-muted); font-weight: 500; margin: 0; }

/* GRID DE CARTÕES */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 30px;
    padding: 10px 0;
}

/* ESTILO DO CARTÃO CLICÁVEL */
.hub-card {
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    text-decoration: none;
    display: flex;
    flex-direction: column;
    box-shadow: var(--shadow-sm);
    transition: all 0.3s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.hub-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-md);
    border-color: #bfdbfe;
}

/* ÁREA DA FOTO (PREVIEW) */
.card-image {
    width: 100%;
    height: 160px;
    background-size: cover;
    background-position: top left;
    background-repeat: no-repeat;
    border-bottom: 1px solid var(--border);
    transition: transform 0.5s ease;
}

.hub-card:hover .card-image {
    transform: scale(1.03);
}

.image-container {
    width: 100%;
    height: 160px;
    overflow: hidden;
    border-radius: 12px 12px 0 0;
}

/* ÁREA DE TEXTO DO CARTÃO */
.card-content {
    padding: 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
}

.card-title {
    font-size: 16px;
    font-weight: 800;
    color: var(--primary-dark);
    margin-bottom: 8px;
}

.card-desc {
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.5;
    font-weight: 500;
    margin-bottom: 10px;
}

.card-arrow {
    margin-top: auto;
    align-self: flex-end;
    color: #cbd5e1;
    font-size: 16px;
    font-weight: bold;
    transition: color 0.3s ease;
}

.hub-card:hover .card-arrow {
    color: var(--primary);
}
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 3. CONSTRUÇÃO DO PORTAL (COM BOTÃO DE LOGOUT DISCRETO)
# ==============================================================================
col_title, col_logout = st.columns([4, 1])
with col_title:
    st.markdown("""
    <div class="hub-header">
        <h1>Portal Financeiro Executivo</h1>
        <p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>
    </div>
    """, unsafe_allow_html=True)

with col_logout:
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    if st.button("🔒 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

html_hub = f"""
<div class="card-grid">

<a href="/Dashboard_Saldo" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_saldos)}"></div></div>
    <div class="card-content">
        <div class="card-title">Dashboard de Saldos</div>
        <div class="card-desc">Visão consolidada de todas as contas bancárias, aplicações e limites de crédito em tempo real.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

<a href="/painel_fluxo_caixa" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_fluxo)}"></div></div>
    <div class="card-content">
        <div class="card-title">Fluxo de Caixa Analítico</div>
        <div class="card-desc">Mapeamento da origem e destino do dinheiro, geração líquida e taxa de consumo sob a ótica de caixa.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

<a href="/painel_pagar" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_pagar)}"></div></div>
    <div class="card-content">
        <div class="card-title">Painel de Pagamentos</div>
        <div class="card-desc">Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e controle de saídas.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

</div>
"""

st.markdown(html_hub.replace('\n', ''), unsafe_allow_html=True)

# ==============================================================================
# 4. CONFIGURAÇÃO DE NAVEGAÇÃO DE PÁGINAS (ST.NAVIGATION)
# ==============================================================================
paginas = [
    st.Page("pages/Dashboard_Saldo.py", title="Dashboard de Saldos", icon="📊"),
    st.Page("pages/painel_fluxo_caixa.py", title="Fluxo de Caixa Analítico", icon="💰"),
    st.Page("pages/painel_pagar.py", title="Painel de Pagamentos", icon="📄")
]

pg = st.navigation(paginas, position="hidden")
pg.run()
