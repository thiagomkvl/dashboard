import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Financeiro Executivo", layout="wide", page_icon="🏢")

# ==============================================================================
# 1. CUSTOM CSS — ESTILO HUB / PORTAL (POWER BI STYLE)
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
    --shadow-sm: 0 2px 8px rgba(30, 64, 175, 0.04);
    --shadow-md: 0 8px 16px rgba(30, 64, 175, 0.1);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 1000px; padding-top: 3rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }

/* CABEÇALHO DO HUB */
.hub-header { text-align: center; margin-bottom: 40px; }
.hub-header h1 { font-size: 32px; font-weight: 800; color: var(--primary-dark); margin-bottom: 8px; letter-spacing: -0.5px; }
.hub-header p { font-size: 15px; color: var(--text-muted); font-weight: 500; }

/* GRID DE CARTÕES */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 25px;
    padding: 10px;
}

/* ESTILO DO CARTÃO CLICÁVEL */
.hub-card {
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 25px 20px;
    text-decoration: none;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    box-shadow: var(--shadow-sm);
    transition: all 0.3s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.hub-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--primary);
    transform: scaleX(0);
    transition: transform 0.3s ease;
    transform-origin: left;
}

.hub-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-md);
    border-color: #bfdbfe;
}

.hub-card:hover::before {
    transform: scaleX(1);
}

.card-icon {
    width: 54px;
    height: 54px;
    background-color: #eff6ff;
    color: var(--primary);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    margin-bottom: 16px;
    font-weight: bold;
}

.card-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--primary-dark);
    margin-bottom: 8px;
}

.card-desc {
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.5;
    font-weight: 500;
}

.card-arrow {
    position: absolute;
    bottom: 20px;
    right: 20px;
    color: #cbd5e1;
    font-size: 16px;
    transition: color 0.3s ease;
}

.hub-card:hover .card-arrow {
    color: var(--primary);
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ==============================================================================
# 2. CONSTRUÇÃO DO HTML (BLINDADO CONTRA QUEBRAS DO STREAMLIT)
# ==============================================================================
# Juntamos as tags para garantir que o motor Markdown não interprete como código

html_hub = """
<div class="hub-header">
<h1>Portal Financeiro Executivo</h1>
<p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>
</div>
<div class="card-grid">
<a href="Dashboard_Saldo" target="_self" class="hub-card"><div class="card-icon">🏦</div><div class="card-title">Dashboard de Saldos</div><div class="card-desc">Visão consolidada de todas as contas bancárias, aplicações e limites de crédito em tempo real.</div><div class="card-arrow">➔</div></a>
<a href="painel_dre" target="_self" class="hub-card"><div class="card-icon">📊</div><div class="card-title">DRE Gerencial</div><div class="card-desc">Análise de Receitas, Custos, Margens e Superávit Líquido sob a ótica de competência e performance.</div><div class="card-arrow">➔</div></a>
<a href="painel_fluxo_caixa" target="_self" class="hub-card"><div class="card-icon">💸</div><div class="card-title">Fluxo de Caixa Analítico</div><div class="card-desc">Mapeamento da origem e destino do dinheiro, geração líquida e taxa de consumo sob a ótica de caixa.</div><div class="card-arrow">➔</div></a>
<a href="painel_pagar" target="_self" class="hub-card"><div class="card-icon">📉</div><div class="card-title">Painel de Pagamentos</div><div class="card-desc">Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e controle de saídas.</div><div class="card-arrow">➔</div></a>
<a href="leitura_varredura" target="_self" class="hub-card"><div class="card-icon">🧾</div><div class="card-title">Varredura de Sacado</div><div class="card-desc">Leitura inteligente de arquivos bancários CNAB 240 (DDA) para auditoria e conciliação de pagamentos.</div><div class="card-arrow">➔</div></a>
<a href="upload" target="_self" class="hub-card"><div class="card-icon">☁️</div><div class="card-title">Upload de Bases</div><div class="card-desc">Área dedicada para atualização manual de planilhas, extratos e inserção de novos dados no sistema.</div><div class="card-arrow">➔</div></a>
</div>
"""

st.markdown(html_hub, unsafe_allow_html=True)
