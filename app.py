import streamlit as st
import base64
import os
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Financeiro Executivo", layout="wide", page_icon="🏢")

# ==============================================================================
# 1. FUNÇÃO PARA CARREGAR IMAGENS LOCAIS (BLINDAGEM STREAMLIT)
# ==============================================================================
# Esta função pega a foto do seu painel e converte para código, garantindo que apareça no HTML.
def get_img_b64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            ext = filepath.split('.')[-1]
            return f"data:image/{ext};base64,{b64}"
    else:
        # Se a imagem não for encontrada, exibe um degradê azul corporativo como "placeholder"
        return "linear-gradient(135deg, #eff6ff, #bfdbfe)"

# --- CAMINHOS DAS IMAGENS (Ajuste para o nome das suas fotos) ---
# Crie uma pasta chamada "assets" e coloque as fotos dos dashboards lá dentro.
img_saldos = get_img_b64("assets/preview_saldos.png")
img_dre = get_img_b64("assets/preview_dre.png")
img_fluxo = get_img_b64("assets/preview_fluxo.png")
img_pagar = get_img_b64("assets/preview_pagar.png")
img_varredura = get_img_b64("assets/preview_varredura.png")
img_upload = get_img_b64("assets/preview_upload.png")

# Função auxiliar para renderizar a propriedade "background-image" ou "background"
def bg_style(img_data):
    if img_data.startswith("linear-gradient"):
        return f"background: {img_data};"
    else:
        return f"background-image: url('{img_data}');"


# ==============================================================================
# 2. CUSTOM CSS — ESTILO PORTAL COM THUMBNAILS
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
.main .block-container { max-width: 1100px; padding-top: 3rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }

/* CABEÇALHO DO HUB */
.hub-header { text-align: center; margin-bottom: 40px; }
.hub-header h1 { font-size: 32px; font-weight: 800; color: var(--primary-dark); margin-bottom: 8px; letter-spacing: -0.5px; }
.hub-header p { font-size: 15px; color: var(--text-muted); font-weight: 500; }

/* GRID DE CARTÕES */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 30px;
    padding: 10px;
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

/* Efeito de zoom suave na foto ao passar o mouse */
.hub-card:hover .card-image {
    transform: scale(1.03);
}

/* CONTAINER DA FOTO PARA CORTAR O ZOOM */
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
# 3. CONSTRUÇÃO DO HTML INJETANDO AS FOTOS
# ==============================================================================

html_hub = f"""
<div class="hub-header">
<h1>Portal Financeiro Executivo</h1>
<p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>
</div>
<div class="card-grid">

<a href="Dashboard_Saldo" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_saldos)}"></div></div>
    <div class="card-content">
        <div class="card-title">Dashboard de Saldos</div>
        <div class="card-desc">Visão consolidada de todas as contas bancárias, aplicações e limites de crédito em tempo real.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

<a href="painel_dre" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_dre)}"></div></div>
    <div class="card-content">
        <div class="card-title">DRE Gerencial</div>
        <div class="card-desc">Análise de Receitas, Custos, Margens e Superávit Líquido sob a ótica de competência e performance.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

<a href="painel_fluxo_caixa" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_fluxo)}"></div></div>
    <div class="card-content">
        <div class="card-title">Fluxo de Caixa Analítico</div>
        <div class="card-desc">Mapeamento da origem e destino do dinheiro, geração líquida e taxa de consumo sob a ótica de caixa.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

<a href="painel_pagar" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_pagar)}"></div></div>
    <div class="card-content">
        <div class="card-title">Painel de Pagamentos</div>
        <div class="card-desc">Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e controle de saídas.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

<a href="leitura_varredura" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_varredura)}"></div></div>
    <div class="card-content">
        <div class="card-title">Varredura de Sacado</div>
        <div class="card-desc">Leitura inteligente de arquivos bancários CNAB 240 (DDA) para auditoria e conciliação de pagamentos.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

<a href="upload" target="_self" class="hub-card">
    <div class="image-container"><div class="card-image" style="{bg_style(img_upload)}"></div></div>
    <div class="card-content">
        <div class="card-title">Upload de Bases</div>
        <div class="card-desc">Área dedicada para atualização manual de planilhas, extratos e inserção de novos dados no sistema.</div>
        <div class="card-arrow">➔</div>
    </div>
</a>

</div>
"""

st.markdown(html_hub.replace('\n', ''), unsafe_allow_html=True)
