import streamlit as st
import base64
import os
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Financeiro Executivo", layout="wide", page_icon="🏢")

# ==============================================================================
# 1. FUNÇÕES DE NAVEGAÇÃO E IMAGENS (ROTEAMENTO POR NOME DA PÁGINA)
# ==============================================================================
def acessar_painel(nome_arquivo):
    """
    Em vez de lutar contra o caminho das pastas no Linux do Streamlit Cloud,
    nós usamos o recurso do Streamlit de buscar apenas pelo NOME da página.
    Ele acha a página independentemente da subpasta em que ela esteja.
    """
    # Remove o ".py" para extrair o nome puro da página
    nome_sem_py = nome_arquivo.replace(".py", "")
    
    # O Streamlit as vezes converte os sublinhados (_) em espaços no menu invisível
    nome_com_espaco = nome_sem_py.replace("_", " ")
    
    # O roteador tenta chamar o painel apenas pelo nome dele, ignorando pastas
    rotas_tentativas = [
        nome_sem_py,                          # Ex: Dashboard_Saldo
        nome_com_espaco,                      # Ex: Dashboard Saldo
        f"pages/{nome_arquivo}",              # Ex: pages/Dashboard_Saldo.py
        f"dashboard/pages/{nome_arquivo}"     # Ex: dashboard/pages/Dashboard_Saldo.py (O da sua foto)
    ]
    
    for rota in rotas_tentativas:
        try:
            st.switch_page(rota)
            return  # Sucesso! Achou a rota e saiu da função
        except Exception:
            continue  # Falhou, tenta a próxima rota da lista
            
    st.error(f"❌ O servidor não conseguiu rotear para '{nome_arquivo}'.")

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
# 2. CUSTOM CSS — ESTILO DOS CARTÕES (ADAPTADO PARA COMPONENTES NATIVOS)
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

.hub-header h1 { font-size: 28px; font-weight: 800; color: var(--primary-dark); margin: 0 0 4px 0; letter-spacing: -0.5px; }
.hub-header p { font-size: 14px; color: var(--text-muted); font-weight: 500; margin: 0; }

/* ÁREA DA FOTO (PREVIEW) */
.card-image {
    width: 100%;
    height: 160px;
    background-size: cover;
    background-position: top left;
    background-repeat: no-repeat;
    border-bottom: 1px solid var(--border);
    transition: transform 0.5s ease;
    border-radius: 12px 12px 0 0;
}
.image-container {
    width: 100%;
    height: 160px;
    overflow: hidden;
    border-radius: 12px 12px 0 0;
}

/* ÁREA DE TEXTO DO CARTÃO NATIVO */
.card-title {
    font-size: 16px;
    font-weight: 800;
    color: var(--primary-dark);
    margin-bottom: 8px;
    padding: 0 20px;
}
.card-desc {
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.5;
    font-weight: 500;
    margin-bottom: 5px;
    padding: 0 20px;
}

/* Modifica a borda padrão do container do Streamlit para parecer um cartão clicável */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--surface);
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-sm);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    padding: 0px !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-md);
    border-color: #bfdbfe !important;
}

/* Estiliza o botão do Streamlit para parecer a setinha do HTML */
.stButton > button {
    border: none !important;
    background: transparent !important;
    color: #cbd5e1 !important;
    font-weight: bold !important;
    text-align: right !important;
    display: flex !important;
    justify-content: flex-end !important;
    box-shadow: none !important;
    padding-right: 20px !important;
    margin-top: 10px !important;
}
.stButton > button:hover {
    color: var(--primary) !important;
}
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)


# ==============================================================================
# 3. CONSTRUÇÃO DO PORTAL E CARDS DE NAVEGAÇÃO
# ==============================================================================
st.markdown("""
<div class="hub-header">
    <h1>Portal Financeiro Executivo</h1>
    <p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>
</div>
<br>
""", unsafe_allow_html=True)

# Grid de cartões usando as estruturas nativas do Streamlit
c1, c2, c3 = st.columns(3)

with c1:
    with st.container(border=True):
        st.markdown(f'<div class="image-container"><div class="card-image" style="{bg_style(img_saldos)}"></div></div>', unsafe_allow_html=True)
        st.markdown("<div class='card-title' style='margin-top:20px;'>Dashboard de Saldos</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-desc'>Visão consolidada de todas as contas bancárias, aplicações e limites de crédito em tempo real.</div>", unsafe_allow_html=True)
        if st.button("Acessar Painel ➔", key="btn_saldos", use_container_width=True):
            acessar_painel("Dashboard_Saldo.py")

with c2:
    with st.container(border=True):
        st.markdown(f'<div class="image-container"><div class="card-image" style="{bg_style(img_fluxo)}"></div></div>', unsafe_allow_html=True)
        st.markdown("<div class='card-title' style='margin-top:20px;'>Fluxo de Caixa Analítico</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-desc'>Mapeamento da origem e destino do dinheiro, geração líquida e taxa de consumo sob a ótica de caixa.</div>", unsafe_allow_html=True)
        if st.button("Acessar Painel ➔", key="btn_fluxo", use_container_width=True):
            acessar_painel("painel_fluxo_caixa.py")

with c3:
    with st.container(border=True):
        st.markdown(f'<div class="image-container"><div class="card-image" style="{bg_style(img_pagar)}"></div></div>', unsafe_allow_html=True)
        st.markdown("<div class='card-title' style='margin-top:20px;'>Painel de Pagamentos</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-desc'>Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e controle de saídas.</div>", unsafe_allow_html=True)
        if st.button("Acessar Painel ➔", key="btn_pagar", use_container_width=True):
            acessar_painel("painel_pagar.py")
