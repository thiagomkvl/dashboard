import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE Gerencial Executivo", layout="wide", page_icon="📈")

# ==============================================================================
# CUSTOM CSS — IDENTIDADE EXECUTIVA
# ==============================================================================
# Nota: O CSS está compactado à esquerda para evitar que o Streamlit o leia como bloco de código
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f2f5f9;
    --surface: #ffffff;
    --primary-dark: #002b66;
    --primary: #2970d4;
    --success: #02b05c;
    --danger: #fc4e51;
    --text-main: #1a2332;
    --text-muted: #6b7785;
    --border: #d2dbe3;
    --shadow: 0 4px 10px rgba(0, 43, 102, 0.05);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 1.5rem; }
header[data-testid="stHeader"] { display: none !important; }

/* CABEÇALHO AZUL MARINHO */
.top-header { background: var(--primary-dark); color: #fff; padding: 12px 25px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.top-header .title-box h1 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 0.5px; }
.top-header .title-box p { margin: 0; font-size: 11px; font-weight: 400; color: #a4c2f4; letter-spacing: 0.5px; }
.top-header .filters { display: flex; gap: 20px; align-items: center; }
.filter-item { display: flex; flex-direction: column; }
.filter-item label { font-size: 9px; font-weight: 600; color: #a4c2f4; margin-bottom: 2px; }
.filter-item .val { background: #fff; color: var(--primary-dark); padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; min-width: 100px; display: flex; justify-content: space-between; }
.update-badge { background: rgba(255,255,255,0.1); padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; gap: 8px; border: 1px solid rgba(255,255,255,0.2); }
.update-badge div { display: flex; flex-direction: column; }
.update-badge span { font-size: 8px; color: #a4c2f4; text-transform: uppercase;}
.update-badge b { font-size: 11px; font-weight: 700; }

/* KPI CARDS */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 20px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; position: relative; box-shadow: var(--shadow); display: flex; flex-direction: column; justify-content: center; }
.kpi-card::after { content: ""; position: absolute; bottom: 12px; left: 20px; right: 20px; height: 5px; border-radius: 3px; }
.kpi-card.c-blue::after { background: var(--primary); }
.kpi-card.c-green::after { background: var(--success); }
.kpi-content { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.kpi-icon { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.kpi-card.c-blue .kpi-icon { background: #e8f0fe; color: var(--primary); }
.kpi-card.c-green .kpi-icon { background: #e6f6ee; color: var(--success); }
.kpi-text { flex: 1; }
.kpi-title { font-size: 11px; font-weight: 700; color: var(--primary-dark); text-transform: uppercase; margin-bottom: 2px; }
.kpi-val { font-size: 22px; font-weight: 800; color: var(--text-main); letter-spacing: -0.5px; line-height: 1.1; }
.kpi-meta { font-size: 10px; color: var(--text-muted); margin-bottom: 2px; }
.kpi-var { font-size: 11px; font-weight: 700; }
.var-up { color: var(--success); }
.var-down { color: var(--danger); }

/* GRÁFICOS CONTAINERS */
.chart-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 15px 15px 5px 15px; box-shadow: var(--shadow); height: 100%; }
.chart-title { font-size: 15px; font-weight: 800; color: var(--primary-dark); margin-bottom: 2px; }
.chart-subtitle { font-size: 11px; color: var(--primary); font-weight: 500; margin-bottom: 15px; }

/* TABELAS E ANÁLISE GERENCIAL */
.bottom-grid { display: grid; grid-template-columns: 2.5fr 1fr; gap: 15px; margin-top: 20px; }
.table-container { background: var(--surface); border: 1px solid var(--primary-dark); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); }
.table-header { background: var(--primary-dark); color: #fff; padding: 10px 15px; display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 700; }
.dre-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.dre-table th { background: var(--primary); color: #fff; font-weight: 600; text-align: right; padding: 8px 10px; border-left: 1px solid rgba(255,255,255,0.2); }
.dre-table th:first-child { text-align: left; border-left: none; }
.dre-table td { padding: 8px 10px; text-align: right; border-bottom: 1px solid var(--border); font-weight: 600; color: var(--text-main); }
.dre-table td:first-child { text-align: left; }
.dre-table tr:nth-child(even) td { background-color: #f8fafc; }
.row-highlight td { font-weight: 800; background-color: #eef2f6 !important; color: var(--primary-dark); }

/* Box Análise Gerencial */
.insights-container { background: var(--surface); border: 1px solid var(--primary-dark); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); }
.insight-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px 15px; border-bottom: 1px solid var(--border); }
.insight-item:last-child { border-bottom: none; }
.insight-icon { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; font-weight:bold; }
.i-green { background: #e6f6ee; color: var(--success); }
.i-blue { background: #e8f0fe; color: var(--primary); }
.insight-text h4 { margin: 0 0 2px 0; font-size: 11px; font-weight: 700; color: var(--primary-dark); }
.insight-text p { margin: 0; font-size: 10px; color: var(--text-muted); line-height: 1.3; }
</style>
""", unsafe_allow_html=True)

# Função para garantir que o HTML seja injetado limpo sem quebrar no Streamlit
def injetar_html(codigo_html):
    st.markdown(codigo_html.replace('\n', ''), unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÕES UTILITÁRIAS
# ==============================================================================
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

def limpa_valor(valor):
    try:
        if pd.isna(valor): return 0.0
        v = str(valor).replace('R$', '').strip()
        if '.' in v and ',' in v: v = v.replace('.', '').replace(',', '.')
        elif ',' in v: v = v.replace(',', '.')
        return float(v)
    except: return 0.0

def formata_num(valor):
    if pd.isna(valor) or valor == 0: return "-"
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_kpi(valor):
    if pd.isna(valor): return "0"
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_pct(valor):
    if pd.isna(valor) or valor == 0: return "0%"
    return f"{valor:.1f}%".replace('.', ',')

def calc_var(atual, anterior):
    if anterior == 0: return 0
    return ((atual - anterior) / abs(anterior)) * 100

# ==============================================================================
# 2. MAPEAMENTO DRE CLÁSSICA
# ==============================================================================
def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "CASACARESC", "CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "CAPESAUDE", "SIM SAÚDE"]
    if any(c in conta for c in convênios) or "PARTICULAR" in conta or "CARTÃO" in conta: 
        return "Receita Bruta", "Receitas Operacionais", conta

    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "INSS", "HONORÁRIOS", "MÉDICO", "FORNECEDORES", "CUSTO", "MEDICAMENTOS", "OPME"]): 
        return "CPV / CSP", "Custos Variáveis e Serviços", conta
        
    if any(c in conta for c in ["IMPOSTOS", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): 
        return "Deduções", "Impostos Correntes", conta
        
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "INTERNET", "CONTABILIDADE"]): 
        return "OPEX", "Despesas Operacionais Fixas", conta
    
    if any(c in conta for c in ["JUROS", "TARIFAS", "PMT", "FINANCEIRAS", "APLICAÇÕES", "RENDIMENTO", "RESGATE", "OBRAS"]): 
        return "Depreciação e Outros", "Movimentações Financeiras", conta
    
    return "Depreciação e Outros", "Outros", conta

# ==============================================================================
# 3. CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def preparar_dados_dre():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()

    try:
        df = conn.read(worksheet="Extratos_Bancos", ttl=0)
        col_data = df.columns[1]
        col_deb = df.columns[4] if len(df.columns) > 4 else df.columns[-3]
        col_cred = df.columns[5] if len(df.columns) > 5 else df.columns[-2]
        col_conta = df.columns[8] if len(df.columns) > 8 else df.columns[-1]

        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Débito'] = df[col_deb].apply(limpa_valor)
        df['Crédito'] = df[col_cred].apply(limpa_valor)
        df['Valor Líquido'] = df['Crédito'] - df['Débito']
        df['Mês_Ano'] = df['Data'].dt.to_period('M')

        df['Macro'], df['Subgrupo'], df['Conta'] = zip(*df[col_conta].apply(classificar_conta))
        return df[df['Data'].notna()]
    except Exception as e:
        st.error(f"Erro ao gerar DRE: {e}")
        return pd.DataFrame()

df_base = preparar_dados_dre()
if df_base.empty: st.stop()

meses_disponiveis = sorted(df_base['Mês_Ano'].unique())
mes_atual = meses_disponiveis[-1]
mes_anterior = meses_disponiveis[-2] if len(meses_disponiveis) > 1 else mes_atual

meses_str = [str(m) for m in meses_disponiveis]

def get_val(macro, mes):
    return df_base[(df_base['Macro'] == macro) & (df_base['Mês_Ano'] == mes)]['Valor Líquido'].sum()

# ==============================================================================
# 4. MOTOR DRE (MÊS ATUAL E ANTERIOR)
# ==============================================================================
rec_bruta = get_val("Receita Bruta", mes_atual)
deducoes = get_val("Deduções", mes_atual)
rec_liq = rec_bruta + deducoes
cpv = get_val("CPV / CSP", mes_atual)
lucro_bruto = rec_liq + cpv
opex = get_val("OPEX", mes_atual)
ebitda = lucro_bruto + opex
outros = get_val("Depreciação e Outros", mes_atual)
lucro_liq = ebitda + outros

ant_rec_bruta = get_val("Receita Bruta", mes_anterior)
ant_deducoes = get_val("Deduções", mes_anterior)
ant_rec_liq = ant_rec_bruta + ant_deducoes
ant_cpv = get_val("CPV / CSP", mes_anterior)
ant_lucro_bruto = ant_rec_liq + ant_cpv
ant_opex = get_val("OPEX", mes_anterior)
ant_ebitda = ant_lucro_bruto + ant_opex
ant_outros = get_val("Depreciação e Outros", mes_anterior)
ant_lucro_liq = ant_ebitda + ant_outros

mg_bruta = (lucro_bruto / rec_bruta * 100) if rec_bruta else 0
mg_ebitda = (ebitda / rec_bruta * 100) if rec_bruta else 0
ant_mg_bruta = (ant_lucro_bruto / ant_rec_bruta * 100) if ant_rec_bruta else 0
ant_mg_ebitda = (ant_ebitda / ant_rec_bruta * 100) if ant_rec_bruta else 0


# ==============================================================================
# 5. CONFIGURAÇÃO VISUAL / METAS
# ==============================================================================
# As metas ficam centralizadas aqui. Se ainda não houver orçamento/meta cadastrado,
# o dashboard mantém o valor realizado e sinaliza "Meta não cadastrada", sem inventar dados.
METAS = {
    "Receita Bruta": None,
    "Margem Bruta": None,
    "EBITDA": None,
    "Margem EBITDA": None,
    "Lucro Líquido": None,
}

data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
nome_mes_atual = pd.Period(mes_atual).strftime('%B/%Y').capitalize()

def var_vs_meta(atual, meta):
    if meta is None or meta == 0:
        return None
    return ((atual - meta) / abs(meta)) * 100

def meta_texto(valor, percentual=False):
    if valor is None:
        return "Meta não cadastrada"
    return formata_pct(valor) if percentual else f"R$ {formata_kpi(valor)}"

def sinal_var(valor):
    if valor is None:
        return "—"
    return ("▲ " if valor >= 0 else "▼ ") + f"{abs(valor):.1f}%"

# ==============================================================================
# 6. CSS — REPRODUÇÃO DO DASHBOARD DA IMAGEM
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --navy:#073b8f;
    --navy-dark:#062d73;
    --blue:#1769d2;
    --green:#08ad61;
    --red:#f04444;
    --text:#12224a;
    --muted:#61708b;
    --bg:#f5f8fc;
    --border:#c9d9ed;
}
html,body,[class*="css"] { font-family:"Inter",Arial,sans-serif; color:var(--text); }
.stApp { background:var(--bg); }
.main .block-container { max-width:100%; padding:.55rem 1.05rem 1.2rem; }
header[data-testid="stHeader"] { display:none !important; }
div[data-testid="stToolbar"] { display:none !important; }

.exec-header {
    background:linear-gradient(90deg,#062d73,#073b8f 65%,#06357d);
    min-height:92px;
    padding:15px 24px;
    margin:-.55rem -1.05rem 14px;
    color:#fff;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:20px;
    box-shadow:0 4px 14px rgba(7,59,143,.16);
}
.brand { display:flex; align-items:center; gap:12px; min-width:260px; }
.brand-mark {
    width:52px;height:52px;border-radius:16px;background:#ff2338;
    display:flex;align-items:center;justify-content:center;
    color:#fff;font-size:28px;font-weight:800;
}
.brand-name { font-size:23px;line-height:1;font-weight:800;letter-spacing:-.5px; }
.brand-sub { font-size:9px;letter-spacing:5px;margin-top:6px; }
.report-title h1 { margin:0;font-size:27px;line-height:1.05;font-weight:800; }
.report-title p { margin:5px 0 0;color:#bcd1f5;font-size:12px; }
.header-controls { display:flex;align-items:center;gap:20px; }
.filter-item { display:flex;flex-direction:column;gap:4px; }
.filter-item label { color:#d4e2fa;font-size:10px;font-weight:700; }
.fake-select {
    min-width:145px;height:32px;padding:7px 10px;border-radius:5px;
    background:#fff;color:#183b75;font-size:11px;font-weight:700;
    display:flex;justify-content:space-between;align-items:center;
}
.update-card {
    min-width:190px;background:rgba(255,255,255,.08);
    border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:9px 12px;
    display:flex;align-items:center;gap:9px;
}
.update-icon { font-size:20px; }
.update-card small { display:block;color:#bcd1f5;font-size:9px;margin-bottom:2px; }
.update-card strong { font-size:11px; }

.kpi-row { display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:14px; }
.kpi-card {
    position:relative;min-height:135px;padding:16px 16px 17px;background:#fff;
    border:1px solid #bcd0ea;border-radius:11px;
    box-shadow:0 2px 8px rgba(31,68,120,.06);overflow:hidden;
}
.kpi-content { display:flex;align-items:center;gap:11px; }
.kpi-icon {
    width:54px;height:54px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-size:24px;flex:0 0 54px;
}
.kpi-blue .kpi-icon { background:#e2f0ff;color:#1468d8; }
.kpi-green .kpi-icon { background:#d8f8e7;color:#08a95d; }
.kpi-title { font-size:13px;font-weight:800;color:#102e69;text-transform:uppercase;margin-bottom:5px; }
.kpi-val { font-size:25px;font-weight:800;color:#111d40;line-height:1.05;letter-spacing:-.8px; }
.kpi-meta { margin:9px 0 2px 65px;color:#163979;font-size:10px; }
.kpi-var { margin-left:65px;font-size:10px;font-weight:800; }
.kpi-up { color:#08a95d; }.kpi-down { color:#f04444; }
.kpi-track {
    position:absolute;left:16px;right:16px;bottom:10px;height:7px;
    border-radius:5px;background:#dbe9f8;overflow:hidden;
}
.kpi-fill { height:100%;border-radius:5px;background:#0ab568; }

.visual-grid { display:grid;grid-template-columns:1.72fr .92fr;gap:14px;margin-bottom:14px; }
.chart-card {
    background:#fff;border:1px solid #bcd0ea;border-radius:11px;
    box-shadow:0 2px 8px rgba(31,68,120,.05);padding:11px 15px 3px;
}
.chart-title { color:#0c3b89;font-size:18px;font-weight:800;margin-bottom:1px; }
.chart-subtitle { color:#1769d2;font-size:11px;margin-bottom:1px; }

.bottom-grid { display:grid;grid-template-columns:2.75fr .95fr;gap:14px;align-items:stretch; }
.table-container,.insights-container {
    background:#fff;border:1px solid #bcd0ea;border-radius:11px;
    overflow:hidden;box-shadow:0 2px 8px rgba(31,68,120,.05);
}
.section-header {
    height:47px;background:linear-gradient(90deg,#06317c,#10499c);
    color:#fff;padding:0 16px;display:flex;align-items:center;gap:11px;
    font-size:18px;font-weight:800;
}
.section-icon { font-size:22px; }
.dre-table { width:100%;border-collapse:collapse;table-layout:fixed;font-size:11px; }
.dre-table th {
    background:#1354ad;color:#fff;font-weight:700;text-align:center;
    padding:8px;line-height:1.15;border-right:1px solid rgba(255,255,255,.22);
}
.dre-table th:first-child { text-align:left;width:28%; }
.dre-table td {
    padding:7px 9px;border-bottom:1px solid #d8e1ec;color:#162440;
    font-weight:600;text-align:center;
}
.dre-table td:first-child { text-align:left;font-weight:650; }
.dre-table tr:nth-child(even) td { background:#f7f9fc; }
.dre-table .strong-row td { background:#dcecff !important;font-weight:800;color:#092f72; }
.dre-table .negative { color:#f04444; }.dre-table .positive { color:#08a95d; }

.insight-item {
    display:flex;align-items:flex-start;gap:11px;padding:11px 14px;
    border-bottom:1px solid #dbe3ee;
}
.insight-item:last-child { border-bottom:0; }
.insight-icon {
    width:34px;height:34px;flex:0 0 34px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;font-size:16px;
}
.insight-green { background:#dcfaeb;color:#08a95d; }
.insight-blue { background:#e4f0ff;color:#1769d2; }
.insight-text h4 { margin:1px 0 3px;color:#142e68;font-size:12px;font-weight:800; }
.insight-text p { margin:0;color:#53627a;font-size:10px;line-height:1.32; }

.js-plotly-plot .plotly .modebar { display:none !important; }

@media (max-width:1100px) {
    .exec-header { flex-wrap:wrap; }
    .header-controls { width:100%;justify-content:flex-end; }
    .kpi-row { grid-template-columns:repeat(3,1fr); }
    .visual-grid,.bottom-grid { grid-template-columns:1fr; }
}
@media (max-width:700px) {
    .main .block-container { padding:.4rem .55rem 1rem; }
    .exec-header { margin:-.4rem -.55rem 12px;padding:12px; }
    .report-title h1 { font-size:20px; }
    .header-controls { display:none; }
    .kpi-row { grid-template-columns:1fr; }
    .dre-table { font-size:9px; }
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 7. CABEÇALHO
# ==============================================================================
header_html = f"""
<div class="exec-header">
    <div class="brand">
        <div class="brand-mark">♥</div>
        <div>
            <div class="brand-name">SOS CARDIO</div>
            <div class="brand-sub">HOSPITAL</div>
        </div>
    </div>
    <div class="report-title">
        <h1>DRE GERENCIAL EXECUTIVO</h1>
        <p>Análise de Resultados • Performance • Tomada de Decisão</p>
    </div>
    <div class="header-controls">
        <div class="filter-item">
            <label>Período</label>
            <div class="fake-select">{nome_mes_atual}<span>⌄</span></div>
        </div>
        <div class="filter-item">
            <label>Unidade</label>
            <div class="fake-select">Todas<span>⌄</span></div>
        </div>
        <div class="filter-item">
            <label>Centro de Custo</label>
            <div class="fake-select">Todos<span>⌄</span></div>
        </div>
        <div class="update-card">
            <div class="update-icon">▣</div>
            <div><small>Última Atualização</small><strong>{data_hoje}</strong></div>
        </div>
    </div>
</div>
"""
injetar_html(header_html)

# ==============================================================================
# 8. KPI CARDS
# ==============================================================================
kpi_data = [
    ("Receita Bruta", rec_bruta, False, "blue", "▣"),
    ("Margem Bruta", mg_bruta, True, "green", "%"),
    ("EBITDA", ebitda, False, "green", "▥"),
    ("Margem EBITDA", mg_ebitda, True, "green", "↗"),
    ("Lucro Líquido", lucro_liq, False, "blue", "$"),
]

kpi_parts = ['<div class="kpi-row">']
for nome, atual, percentual, tone, icon in kpi_data:
    meta = METAS.get(nome)
    variacao = var_vs_meta(atual, meta)

    valor_display = formata_pct(atual) if percentual else f"R$ {formata_kpi(atual)}"
    meta_display = meta_texto(meta, percentual)

    if variacao is None:
        variacao_html = '<div class="kpi-var" style="color:#718096;">— Meta não cadastrada</div>'
        fill = 72
    else:
        classe = "kpi-up" if variacao >= 0 else "kpi-down"
        variacao_html = f'<div class="kpi-var {classe}">{sinal_var(variacao)} vs. Meta</div>'
        fill = max(8, min(100, (atual / meta) * 100 if meta else 8))

    kpi_parts.append(f"""
    <div class="kpi-card kpi-{tone}">
        <div class="kpi-content">
            <div class="kpi-icon">{icon}</div>
            <div>
                <div class="kpi-title">{nome}</div>
                <div class="kpi-val">{valor_display}</div>
            </div>
        </div>
        <div class="kpi-meta">Meta: {meta_display}</div>
        {variacao_html}
        <div class="kpi-track"><div class="kpi-fill" style="width:{fill:.0f}%;"></div></div>
    </div>
    """)
kpi_parts.append("</div>")
injetar_html("".join(kpi_parts))

# ==============================================================================
# 9. VISUAIS — CASCATA + TENDÊNCIA
# ==============================================================================
injetar_html('<div class="visual-grid">')

# WATERFALL
injetar_html("""
<div class="chart-card">
    <div class="chart-title">Decomposição do Resultado</div>
    <div class="chart-subtitle">Como a Receita Bruta se transforma em Lucro Líquido</div>
""")

x_water = [
    "Receita<br>Bruta","Deduções","Receita<br>Líquida","CPV / CSP",
    "Lucro<br>Bruto","OPEX","EBITDA","Depreciação<br>e Outros","Lucro<br>Líquido"
]
y_water = [rec_bruta,deducoes,rec_liq,cpv,lucro_bruto,opex,ebitda,outros,lucro_liq]
medidas = ["relative","relative","total","relative","total","relative","total","relative","total"]
textos = [f"R$ {formata_num(v)}" if v >= 0 else f"-R$ {formata_num(abs(v))}" for v in y_water]

fig_w = go.Figure(go.Waterfall(
    x=x_water,y=y_water,measure=medidas,text=textos,textposition="outside",
    textfont=dict(color="#0b347c",size=10,family="Inter"),
    connector=dict(line=dict(color="#aab6c6",width=1,dash="dot")),
    increasing=dict(marker=dict(color="#0b3d91")),
    decreasing=dict(marker=dict(color="#f04444")),
    totals=dict(marker=dict(color="#0b3d91"))
))
fig_w.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False,tickfont=dict(size=9,color="#1b2b49")),
    yaxis=dict(showgrid=True,gridcolor="#e3eaf3",tickfont=dict(size=9,color="#4d5d73"),zeroline=False),
    margin=dict(t=26,b=22,l=12,r=8),height=286
)
st.plotly_chart(fig_w,use_container_width=True,config={"displayModeBar":False})
injetar_html("</div>")

# TENDÊNCIA
injetar_html("""
<div class="chart-card">
    <div class="chart-title">Tendência Mensal</div>
    <div class="chart-subtitle">Evolução dos Principais Indicadores</div>
""")

ultimos = meses_str[-6:]
hist_meses = [pd.Period(m).strftime("%b").capitalize() for m in ultimos]
hist_rec = [get_val("Receita Bruta",m) for m in ultimos]
hist_ebitda = [
    get_val("Receita Bruta",m)+get_val("Deduções",m)+get_val("CPV / CSP",m)+get_val("OPEX",m)
    for m in ultimos
]
hist_lucro_bruto = [
    get_val("Receita Bruta",m)+get_val("Deduções",m)+get_val("CPV / CSP",m)
    for m in ultimos
]
hist_mg_bruta = [(lb/r*100) if r else 0 for lb,r in zip(hist_lucro_bruto,hist_rec)]

fig_c = make_subplots(specs=[[{"secondary_y":True}]])
fig_c.add_trace(
    go.Bar(x=hist_meses,y=hist_rec,name="Receita Bruta (Realizado)",marker_color="#0b3d91"),
    secondary_y=False
)
fig_c.add_trace(
    go.Bar(x=hist_meses,y=hist_ebitda,name="EBITDA (Realizado)",marker_color="#65a3f5"),
    secondary_y=False
)
fig_c.add_trace(
    go.Scatter(
        x=hist_meses,y=hist_mg_bruta,name="Margem Bruta % (Realizado)",
        mode="lines+markers",line=dict(color="#f04444",width=3),marker=dict(size=6)
    ),
    secondary_y=True
)

if METAS.get("Margem Bruta") is not None:
    fig_c.add_trace(
        go.Scatter(
            x=hist_meses,y=[METAS["Margem Bruta"]]*len(hist_meses),
            name="Margem Bruta % (Meta)",mode="lines",
            line=dict(color="#214f98",width=2,dash="dash")
        ),
        secondary_y=True
    )

fig_c.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False,tickfont=dict(size=9)),
    yaxis=dict(showgrid=True,gridcolor="#e3eaf3",tickfont=dict(size=9),zeroline=False),
    yaxis2=dict(showgrid=False,range=[0,max(60,max(hist_mg_bruta+[METAS.get("Margem Bruta") or 0])+5)],tickfont=dict(size=9)),
    legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="center",x=.5,font=dict(size=8)),
    margin=dict(t=30,b=20,l=4,r=4),height=286,barmode="group"
)
st.plotly_chart(fig_c,use_container_width=True,config={"displayModeBar":False})
injetar_html("</div>")
injetar_html("</div>")

# ==============================================================================
# 10. MATRIZ DRE + ANÁLISE GERENCIAL
# ==============================================================================
injetar_html('<div class="bottom-grid">')

html_tabela = f"""
<div class="table-container">
    <div class="section-header"><span class="section-icon">▤</span><span>Matriz DRE Gerencial</span></div>
    <table class="dre-table">
        <thead>
            <tr>
                <th>Descrição</th>
                <th>Realizado<br>{nome_mes_atual}<br>(R$)</th>
                <th>Orçado<br>{nome_mes_atual}<br>(R$)</th>
                <th>Var. %<br>(Act vs Bud)</th>
                <th>AV %<br>(Receita Líq.)</th>
                <th>AH %<br>vs. Ano Anterior</th>
            </tr>
        </thead>
        <tbody>
"""

def get_val_ano_anterior(macro, mes):
    try:
        alvo = pd.Period(mes, freq="M") - 12
        return get_val(macro,str(alvo))
    except Exception:
        return 0

linhas_dre = [
    ("Receita Bruta",rec_bruta,"Receita Bruta",False),
    ("Deduções da Receita",deducoes,"Deduções",False),
    ("Receita Líquida",rec_liq,None,True),
    ("Custo dos Serviços (CPV/CSP)",cpv,"CPV / CSP",False),
    ("Lucro Bruto",lucro_bruto,None,True),
    ("Despesas Operacionais (OPEX)",opex,"OPEX",False),
    ("EBITDA",ebitda,None,True),
    ("Depreciação e Amortização",outros,"Depreciação e Outros",False),
    ("Lucro Líquido",lucro_liq,None,True),
]
base_av = rec_liq if rec_liq != 0 else 1

for nome,val_at,macro_ah,destaque in linhas_dre:
    meta = METAS.get(nome)
    var_pct = var_vs_meta(val_at,meta)

    if macro_ah:
        val_ly = get_val_ano_anterior(macro_ah,str(mes_atual))
    else:
        ly_rec = get_val_ano_anterior("Receita Bruta",str(mes_atual))
        ly_ded = get_val_ano_anterior("Deduções",str(mes_atual))
        ly_cpv = get_val_ano_anterior("CPV / CSP",str(mes_atual))
        ly_opex = get_val_ano_anterior("OPEX",str(mes_atual))
        ly_outros = get_val_ano_anterior("Depreciação e Outros",str(mes_atual))
        if nome == "Receita Líquida":
            val_ly = ly_rec+ly_ded
        elif nome == "Lucro Bruto":
            val_ly = ly_rec+ly_ded+ly_cpv
        elif nome == "EBITDA":
            val_ly = ly_rec+ly_ded+ly_cpv+ly_opex
        else:
            val_ly = ly_rec+ly_ded+ly_cpv+ly_opex+ly_outros

    ah_pct = calc_var(abs(val_at),abs(val_ly)) if val_ly else None
    av_pct = (val_at/base_av)*100

    if var_pct is None:
        var_html="—";var_class=""
    else:
        custo=any(x in nome for x in ["Custo","Deduções","Despesas","Depreciação"])
        positivo=var_pct>=0
        if custo: positivo=not positivo
        var_class="positive" if positivo else "negative"
        var_html=f"{'+' if var_pct>=0 else ''}{var_pct:.1f}%"

    ah_html="—" if ah_pct is None else f"{'+' if ah_pct>=0 else ''}{ah_pct:.1f}%"
    ah_class="positive" if ah_pct is not None and ah_pct>=0 else "negative" if ah_pct is not None else ""
    valor_html=f"({formata_num(abs(val_at))})" if val_at<0 else formata_num(val_at)
    classe="strong-row" if destaque else ""

    html_tabela += f"""
        <tr class="{classe}">
            <td>{nome}</td>
            <td>{valor_html}</td>
            <td>—</td>
            <td class="{var_class}">{var_html}</td>
            <td>{av_pct:.1f}%</td>
            <td class="{ah_class}">{ah_html}</td>
        </tr>
    """

html_tabela += "</tbody></table></div>"
injetar_html(html_tabela)

txt_rec="acima" if rec_bruta>=ant_rec_bruta else "abaixo"
txt_lucro="em destaque" if lucro_liq>=ant_lucro_liq else "em atenção"
var_rec_mom=calc_var(rec_bruta,ant_rec_bruta)
var_lucro_mom=calc_var(lucro_liq,ant_lucro_liq)

html_insights=f"""
<div class="insights-container">
    <div class="section-header"><span class="section-icon">◉</span><span>Análise Gerencial</span></div>

    <div class="insight-item">
        <div class="insight-icon insight-green">▥</div>
        <div class="insight-text">
            <h4>Receita Bruta {txt_rec} do mês anterior</h4>
            <p>{var_rec_mom:+.1f}% vs. mês anterior, indicando o ritmo de crescimento das operações.</p>
        </div>
    </div>

    <div class="insight-item">
        <div class="insight-icon insight-green">%</div>
        <div class="insight-text">
            <h4>Margens em evolução</h4>
            <p>Margem Bruta de {mg_bruta:.1f}% e Margem EBITDA de {mg_ebitda:.1f}%, refletindo a eficiência operacional.</p>
        </div>
    </div>

    <div class="insight-item">
        <div class="insight-icon insight-green">$</div>
        <div class="insight-text">
            <h4>Lucro Líquido {txt_lucro}</h4>
            <p>Resultado de R$ {formata_kpi(lucro_liq)}, com variação de {var_lucro_mom:+.1f}% vs. último mês.</p>
        </div>
    </div>

    <div class="insight-item">
        <div class="insight-icon insight-blue">⌕</div>
        <div class="insight-text">
            <h4>Foco para o próximo período</h4>
            <p>Manter disciplina de custos, acompanhar CPV/CSP e preservar a evolução das margens.</p>
        </div>
    </div>
</div>
"""
injetar_html(html_insights)
injetar_html("</div>")
