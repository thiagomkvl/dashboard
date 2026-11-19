import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import textwrap

try:
    st.set_page_config(
        page_title="Adiantamentos Pagos 2026 · Visão Executiva",
        layout="wide",
        page_icon="📊",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

import streamlit.components.v1 as components

try:
    from database import conectar_sheets
except Exception as _err:
    _erro_import_db = str(_err)
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {_erro_import_db}")
        return None

# ==============================================================================
# PALETA — tema claro / clean (igual ao Dash de Saldo)
# ==============================================================================
AZUL, VERDE, AMBAR, VERMELHO = "#2563eb", "#059669", "#d97706", "#dc2626"
ROXO, CIANO = "#7c3aed", "#0891b2"
TXT, MUTED, BORDA = "#0f172a", "#64748b", "#e2e8f0"
BG, SURFACE = "#f8fafc", "#ffffff"

css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #f8fafc !important; color: #0f172a; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1.4rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: 1.0rem; }
    [data-testid="stMarkdownContainer"] { color: #0f172a; }
    [data-testid="stCaptionContainer"] { color: #64748b !important; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stWidgetLabel"] p { color: #64748b !important; font-size: 12px; font-weight: 600; }
    div[role="radiogroup"] label p { color: #0f172a !important; font-size: 12px; }
    .side-sec {
        font-size: 10px; font-weight: 800; letter-spacing: 1px;
        color: #64748b; text-transform: uppercase; margin: 6px 0 -2px;
    }

    /* Widgets claros */
    [data-baseweb="select"] > div,
    [data-testid="stDateInput"] > div > div {
        background: #ffffff !important;
        border-color: #e2e8f0 !important;
        color: #0f172a !important;
    }
    [data-baseweb="select"] span, [data-baseweb="select"] input { color: #0f172a !important; }
    [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #ffffff !important; }
    li[role="option"] { color: #0f172a !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background: #f1f5f9 !important; }

    /* Cabeçalho */
    .top {
        display: flex; justify-content: space-between; align-items: center; gap: 16px;
        padding-bottom: 12px; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0;
    }
    .top h1 {
        margin: 0; font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: 0.3px;
    }
    .top p { margin: 2px 0 0; font-size: 13px; color: #64748b; }

    /* KPIs */
    .kpi {
        padding: 12px 14px; border-radius: 12px; min-height: 96px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .kpi.green { border-left: 3px solid #059669; }
    .kpi.red { border-left: 3px solid #dc2626; }
    .kpi.amber { border-left: 3px solid #d97706; }
    .kpi.blue { border-left: 3px solid #2563eb; }
    .kpi-t {
        font-size: 10px; font-weight: 800; letter-spacing: 0.4px;
        text-transform: uppercase; color: #64748b;
    }
    .kpi-v {
        font-size: 20px; font-weight: 800; color: #0f172a;
        margin: 8px 0 4px; font-variant-numeric: tabular-nums; white-space: nowrap;
    }
    .kpi-sub { font-size: 11px; color: #64748b; font-weight: 600; }

    /* Seções */
    .section-title {
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #0f172a; margin: 10px 0 8px; padding-left: 10px;
        border-left: 3px solid #2563eb;
        display: flex; align-items: center; gap: 8px;
    }
    .section-title span {
        font-size: 10px; font-weight: 600; text-transform: none;
        letter-spacing: 0.2px; color: #64748b; margin-left: auto;
    }

    /* Barra de Composição */
    .comp-bar-wrap {
        width: 100%; height: 14px; background-color: #e2e8f0;
        border-radius: 999px; overflow: hidden; display: flex; margin: 8px 0 10px 0;
    }
    .comp-seg-green { background-color: #059669; height: 100%; }
    .comp-seg-red { background-color: #dc2626; height: 100%; }
    .comp-legend { display: flex; gap: 20px; font-size: 11.5px; color: #475569; font-weight: 600; }
    .dot { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; }

    /* Cards de Painel */
    .panel-box {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 14px 16px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        margin-bottom: 12px; height: 100%;
    }
    .panel-title {
        font-size: 12px; font-weight: 800; color: #0f172a; text-transform: uppercase;
        letter-spacing: 0.4px; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;
    }

    /* Barras Horizontais */
    .bar-row { display: flex; align-items: center; margin-bottom: 7px; font-size: 11px; gap: 8px; }
    .bar-name { width: 44%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #334155; font-weight: 600; }
    .bar-track { flex: 1; height: 8px; background-color: #f1f5f9; border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 999px; }
    .bar-metric { min-width: 82px; text-align: right; font-weight: 800; color: #0f172a; font-variant-numeric: tabular-nums; }
    .bar-extra { min-width: 115px; text-align: right; font-size: 10.5px; color: #64748b; font-variant-numeric: tabular-nums; }

    /* Badges */
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 800; text-align: center; min-width: 68px; }
    .badge-critico { background-color: rgba(220, 38, 38, 0.1); color: #dc2626; border: 1px solid rgba(220, 38, 38, 0.25); }
    .badge-atencao { background-color: rgba(217, 119, 6, 0.1); color: #d97706; border: 1px solid rgba(217, 119, 6, 0.25); }
    .badge-monitorar { background-color: rgba(37, 99, 235, 0.1); color: #2563eb; border: 1px solid rgba(37, 99, 235, 0.25); }

    /* Lista de Conclusões */
    .conclusoes-list {
        margin: 0; padding-left: 18px; color: #334155;
        font-size: 12px; line-height: 1.65;
    }
    .conclusoes-list li { margin-bottom: 6px; }

    /* Legenda de Regras */
    .rules-note {
        margin-top: 12px; padding-top: 8px; border-top: 1px dashed #e2e8f0;
        font-size: 10.5px; color: #64748b; line-height: 1.5;
    }

    /* Tabelas */
    .tabela-container {
        overflow: auto; border: 1px solid #e2e8f0; border-radius: 10px;
        background: #ffffff; max-height: 520px; width: 100%;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }
    .tabela-financeira { width: 100%; border-collapse: collapse; margin: 0; font-size: 11px; color: #0f172a; }
    .tabela-financeira th {
        background: #f8fafc; color: #64748b; font-size: 10px; font-weight: 700; text-align: left;
        padding: 9px 10px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase;
        position: sticky; top: 0; z-index: 2; white-space: nowrap;
    }
    .tabela-financeira td {
        padding: 7px 10px; border-bottom: 1px solid #f1f5f9; font-size: 11px; font-weight: 600;
        color: #334155; white-space: nowrap; font-variant-numeric: tabular-nums;
    }
    .tabela-financeira tbody tr:hover td { background: #f8fafc; }
    .td-bold { font-weight: 800; color: #0f172a; }
    .td-muted { color: #64748b; max-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .exec-footer { margin-top: 14px; font-size: 11px; color: #64748b; }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# CARREGAMENTO DOS DADOS DA ABA Base_ADT
# ==============================================================================
ABA_ADT = "Base_ADT"

@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados_adt():
    conn = conectar_sheets()
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet=ABA_ADT, ttl=0)
        return df
    except Exception as e:
        st.error(f"⚠️ Erro ao ler a aba '{ABA_ADT}' do Google Sheets: {e}")
        return pd.DataFrame()

df_bruto = carregar_dados_adt()

if df_bruto.empty:
    st.warning(f"A aba **{ABA_ADT}** está vazia ou não foi encontrada na planilha conectada. Verifique o Google Sheets.")
    st.stop()

# ==============================================================================
# TRATAMENTO E LIMPEZA DOS DADOS
# ==============================================================================
def limpa_valor(val):
    try:
        if isinstance(val, (int, float, np.integer, np.floating)):
            return float(val) if not pd.isna(val) else 0.0
        if pd.isna(val) or str(val).strip() in ["", "-", "nan", "NaN", "None"]:
            return 0.0
        s = str(val).strip().replace('R$', '').strip()
        if '.' in s and ',' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except Exception:
        return 0.0

def limpa_texto_filtro(valor, padrao="Não Informado"):
    if pd.isna(valor):
        return padrao
    texto = str(valor).strip()
    if texto.lower() in {"", "nan", "none", "null"}:
        return padrao
    if isinstance(valor, (int, float, np.integer, np.floating)) and float(valor).is_integer():
        texto = str(int(valor))
    return texto

df = df_bruto.copy()
df.columns = [str(c).strip() for c in df.columns]

if "Valor" in df.columns:
    df["Valor"] = df["Valor"].apply(limpa_valor)
else:
    df["Valor"] = 0.0

if "Saldo" in df.columns:
    df["Saldo"] = df["Saldo"].apply(limpa_valor)
else:
    df["Saldo"] = df["Valor"]

df["Baixado"] = (df["Valor"] - df["Saldo"]).clip(lower=0.0)

if "Data inclusão" in df.columns:
    df["Data inclusão"] = pd.to_datetime(df["Data inclusão"], dayfirst=True, errors="coerce")
else:
    df["Data inclusão"] = pd.NaT

if "Pessoa física/jurídica" in df.columns:
    df["Fornecedor"] = df["Pessoa física/jurídica"].apply(limpa_texto_filtro)
elif "Fornecedor" in df.columns:
    df["Fornecedor"] = df["Fornecedor"].apply(limpa_texto_filtro)
else:
    df["Fornecedor"] = "Não Informado"

if "Banco" not in df.columns:
    df["Banco"] = "Não Informado"
else:
    df["Banco"] = df["Banco"].apply(limpa_texto_filtro)

if "Observação" not in df.columns:
    df["Observação"] = ""
else:
    df["Observação"] = df["Observação"].fillna("").astype(str).str.strip()

if "Estabelecimento" not in df.columns:
    df["Estabelecimento"] = "SOS Cardio"
else:
    df["Estabelecimento"] = df["Estabelecimento"].apply(lambda x: limpa_texto_filtro(x, "SOS Cardio"))

if "Adiantamento" not in df.columns:
    df["Adiantamento"] = np.arange(1, len(df) + 1)

data_ref = datetime(2026, 11, 18).date()
df["Dias"] = (pd.to_datetime(data_ref) - df["Data inclusão"]).dt.days.fillna(0).astype(int).clip(lower=0)

meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
df["Mes_Num"] = df["Data inclusão"].dt.month
df["Ano"] = df["Data inclusão"].dt.year
df["Mes_Nome"] = df["Mes_Num"].map(meses_pt).fillna("N/D")

# ==============================================================================
# SIDEBAR - FILTROS
# ==============================================================================
with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros de Adiantamentos</div>", unsafe_allow_html=True)

    lista_meses = [m for m in ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"] if m in df["Mes_Nome"].unique()]
    meses_sel = st.multiselect("Mês de Inclusão", options=lista_meses, default=[])

    lista_fornecedores = sorted(df["Fornecedor"].dropna().astype(str).unique().tolist(), key=str.casefold)
    fornecedores_sel = st.multiselect("Fornecedor", options=lista_fornecedores, default=[])

    lista_bancos = sorted(df["Banco"].dropna().astype(str).unique().tolist(), key=str.casefold)
    bancos_sel = st.multiselect("Banco", options=lista_bancos, default=[])

    status_saldo = st.radio("Filtrar por Status", options=["Todos", "Somente Em Aberto (Saldo > 0)", "Somente Baixados"])

df_filt = df.copy()
if meses_sel:
    df_filt = df_filt[df_filt["Mes_Nome"].isin(meses_sel)]
if fornecedores_sel:
    df_filt = df_filt[df_filt["Fornecedor"].isin(fornecedores_sel)]
if bancos_sel:
    df_filt = df_filt[df_filt["Banco"].isin(bancos_sel)]

if status_saldo == "Somente Em Aberto (Saldo > 0)":
    df_filt = df_filt[df_filt["Saldo"] > 0]
elif status_saldo == "Somente Baixados":
    df_filt = df_filt[df_filt["Saldo"] == 0]

# ==============================================================================
# CÁLCULOS E INDICADORES
# ==============================================================================
total_adiantado = df_filt["Valor"].sum()
total_baixado = df_filt["Baixado"].sum()
total_aberto = df_filt["Saldo"].sum()

qtd_total = len(df_filt)
qtd_forn = df_filt["Fornecedor"].nunique()
qtd_aberto = len(df_filt[df_filt["Saldo"] > 0])

pct_baixado = (total_baixado / total_adiantado * 100) if total_adiantado > 0 else 0.0
pct_aberto = (total_aberto / total_adiantado * 100) if total_adiantado > 0 else 0.0

df_aberto = df_filt[df_filt["Saldo"] > 0].copy()
forn_grp = df_aberto.groupby("Fornecedor", as_index=False).agg(
    Saldo_Aberto=("Saldo", "sum"),
    Qtd_Itens=("Valor", "count"),
    Max_Dias=("Dias", "max")
).sort_values("Saldo_Aberto", ascending=False).reset_index(drop=True)

def classificar_criticidade(saldo, dias):
    if saldo >= 100_000 or (saldo >= 20_000 and dias > 90):
        return "Crítico"
    elif saldo >= 20_000 or (saldo >= 5_000 and dias > 90):
        return "Atenção"
    else:
        return "Monitorar"

if not forn_grp.empty:
    forn_grp["Criticidade"] = forn_grp.apply(lambda r: classificar_criticidade(r["Saldo_Aberto"], r["Max_Dias"]), axis=1)
else:
    forn_grp["Criticidade"] = pd.Series(dtype=str)

top5_pct = (forn_grp.head(5)["Saldo_Aberto"].sum() / total_aberto * 100) if total_aberto > 0 else 0.0
top10_pct = (forn_grp.head(10)["Saldo_Aberto"].sum() / total_aberto * 100) if total_aberto > 0 else 0.0
qtd_forn_saldo = len(forn_grp)

df_90 = df_aberto[df_aberto["Dias"] > 90]
saldo_90 = df_90["Saldo"].sum()
qtd_90 = len(df_90)

def fmt_brl(val, decimais=0):
    if pd.isna(val):
        val = 0.0
    s = f"{val:,.{decimais}f}"
    return "R$ " + s.replace(',', 'X').replace('.', ',').replace('X', '.')

def fmt_int(val):
    return f"{int(val):,}".replace(',', '.')

def fmt_pct(val, decimais=1):
    return f"{val:.{decimais}f}%".replace('.', ',')

def fmt_mi(val):
    return f"R$ {val / 1_000_000:.2f} mi".replace('.', ',')

meses_completos = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
}
if not df_filt["Mes_Num"].dropna().empty:
    m_min = int(df_filt["Mes_Num"].min())
    m_max = int(df_filt["Mes_Num"].max())
    ano_val = df_filt["Ano"].dropna().max()
    ano_ref = int(ano_val) if pd.notna(ano_val) else 2026
    periodo_txt = (
        f"{meses_completos[m_min].capitalize()} a {meses_completos[m_max]} de {ano_ref}"
        if m_min != m_max else f"{meses_completos[m_min].capitalize()} de {ano_ref}"
    )
else:
    periodo_txt = "Janeiro a novembro de 2026"

# ==============================================================================
# CABEÇALHO
# ==============================================================================
st.markdown(f"""
<div class="top">
    <div>
        <h1>Adiantamentos Pagos 2026 · Visão Executiva</h1>
        <p>Posição em {data_ref.strftime("%d/%m/%Y")} · {periodo_txt} · Valores em reais (R$)</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# KPIS (5 colunas)
# ==============================================================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="kpi blue"><div class="kpi-t">Total Adiantado</div><div class="kpi-v">{fmt_brl(total_adiantado)}</div><div class="kpi-sub">{fmt_int(qtd_total)} adiantamentos · {fmt_int(qtd_forn)} fornecedores</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi green"><div class="kpi-t">Já Baixado</div><div class="kpi-v">{fmt_brl(total_baixado)}</div><div class="kpi-sub">{fmt_pct(pct_baixado)} do total adiantado</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi red"><div class="kpi-t">Em Aberto (Saldo)</div><div class="kpi-v">{fmt_brl(total_aberto)}</div><div class="kpi-sub">{fmt_pct(pct_aberto)} do total · {fmt_int(qtd_aberto)} adiantamentos</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi amber"><div class="kpi-t">Fornecedores com Saldo</div><div class="kpi-v">{fmt_int(qtd_forn_saldo)}</div><div class="kpi-sub">Top 5 = {fmt_pct(top5_pct, 0)} do saldo · Top 10 = {fmt_pct(top10_pct)}</div></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="kpi red"><div class="kpi-t">Saldo com Mais de 90 Dias</div><div class="kpi-v">{fmt_brl(saldo_90)}</div><div class="kpi-sub">{fmt_int(qtd_90)} adiantamentos sem baixa</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ==============================================================================
# BARRA DE COMPOSIÇÃO
# ==============================================================================
st.markdown(f"""
<div class="panel-box">
    <div class="panel-title">Composição do total adiantado: baixado × em aberto</div>
    <div class="comp-bar-wrap">
        <div class="comp-seg-green" style="width: {pct_baixado:.2f}%;"></div>
        <div class="comp-seg-red" style="width: {pct_aberto:.2f}%;"></div>
    </div>
    <div class="comp-legend">
        <div><span class="dot" style="background:#059669;"></span>Baixado {fmt_brl(total_baixado)} ({fmt_pct(pct_baixado)})</div>
        <div><span class="dot" style="background:#dc2626;"></span>Em aberto {fmt_brl(total_aberto)} ({fmt_pct(pct_aberto)})</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# LINHA 3: TOP 12 CRÍTICOS | CLASSIFICAÇÃO CRITICIDADE | ENVELHECIMENTO (AGING)
# ==============================================================================
col_top12, col_crit, col_aging = st.columns([1.15, 0.95, 1.0])

cor_crit_map = {
    "Crítico": "#dc2626",
    "Atenção": "#d97706",
    "Monitorar": "#2563eb"
}

with col_top12:
    top12 = forn_grp.head(12)
    max_val_top12 = top12["Saldo_Aberto"].max() if not top12.empty else 1.0
    linhas_top12 = ""
    for idx, r in top12.iterrows():
        pct_bar = (r["Saldo_Aberto"] / max_val_top12 * 100) if max_val_top12 > 0 else 0
        cor_b = cor_crit_map.get(r["Criticidade"], "#2563eb")
        linhas_top12 += f"""
        <div class="bar-row">
            <div class="bar-name" title="{r['Fornecedor']}">{idx + 1}. {r['Fornecedor']}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct_bar:.1f}%; background:{cor_b};"></div>
            </div>
            <div class="bar-metric">{fmt_brl(r['Saldo_Aberto'])}</div>
        </div>
        """
    if not linhas_top12:
        linhas_top12 = "<div style='color:#64748b; font-size:12px;'>Nenhum fornecedor com saldo em aberto no filtro atual.</div>"

    st.markdown(f"""
    <div class="panel-box">
        <div class="panel-title">Fornecedores mais críticos: saldo em aberto (maior → menor)</div>
        {linhas_top12}
    </div>
    """, unsafe_allow_html=True)

with col_crit:
    linhas_crit = ""
    for cat, badge_cls, bar_hex in [
        ("Crítico", "badge-critico", "#dc2626"),
        ("Atenção", "badge-atencao", "#d97706"),
        ("Monitorar", "badge-monitorar", "#2563eb"),
    ]:
        sub_c = forn_grp[forn_grp["Criticidade"] == cat]
        val_c = sub_c["Saldo_Aberto"].sum()
        qtd_c = len(sub_c)
        pct_c = (val_c / total_aberto * 100) if total_aberto > 0 else 0.0
        linhas_crit += f"""
        <div class="bar-row" style="margin-bottom: 12px;">
            <div style="width: 74px;"><span class="badge {badge_cls}">{cat}</span></div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct_c:.1f}%; background:{bar_hex};"></div>
            </div>
            <div class="bar-metric" style="min-width:92px;">{fmt_brl(val_c)}</div>
            <div class="bar-extra">{fmt_int(qtd_c)} forn. · {fmt_pct(pct_c)}</div>
        </div>
        """

    st.markdown(f"""
    <div class="panel-box">
        <div class="panel-title">Classificação de criticidade</div>
        {linhas_crit}
        <div class="rules-note">
            <div><span class="dot" style="background:#dc2626;"></span><b>Crítico:</b> saldo ≥ R$ 100 mil, ou ≥ R$ 20 mil com adiantamento há mais de 90 dias</div>
            <div><span class="dot" style="background:#d97706;"></span><b>Atenção:</b> saldo ≥ R$ 20 mil, ou ≥ R$ 5 mil com mais de 90 dias</div>
            <div><span class="dot" style="background:#2563eb;"></span><b>Monitorar:</b> demais fornecedores com saldo</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_aging:
    faixas = [
        ("0–30 dias", 0, 30, "#2563eb"),
        ("31–60", 31, 60, "#2563eb"),
        ("61–90", 61, 90, "#d97706"),
        ("91–180", 91, 180, "#dc2626"),
        (">180 dias", 181, 999999, "#991b1b"),
    ]
    aging_dados = []
    for label, d_min, d_max, cor_f in faixas:
        sub_a = df_aberto[(df_aberto["Dias"] >= d_min) & (df_aberto["Dias"] <= d_max)]
        aging_dados.append((label, sub_a["Saldo"].sum(), len(sub_a), cor_f))

    max_aging = max([x[1] for x in aging_dados]) if aging_dados else 1.0
    max_aging = max_aging if max_aging > 0 else 1.0

    linhas_aging = ""
    for label, val_a, qtd_a, cor_f in aging_dados:
        pct_a = (val_a / max_aging * 100)
        linhas_aging += f"""
        <div class="bar-row" style="margin-bottom: 12px;">
            <div style="width: 68px; font-weight: 700; color: #334155;">{label}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct_a:.1f}%; background:{cor_f};"></div>
            </div>
            <div class="bar-metric" style="min-width:85px;">{fmt_brl(val_a)}</div>
            <div class="bar-extra" style="min-width:65px;">{fmt_int(qtd_a)} itens</div>
        </div>
        """

    st.markdown(f"""
    <div class="panel-box">
        <div class="panel-title">Envelhecimento do saldo em aberto (dias desde a inclusão)</div>
        {linhas_aging}
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# LINHA 4: EVOLUÇÃO MENSAL + PRINCIPAIS CONCLUSÕES
# ==============================================================================
col_evol, col_conc = st.columns([1.0, 1.85])

with col_evol:
    st.markdown('<div class="panel-box" style="padding-bottom:8px;"><div class="panel-title">Evolução mensal: valor adiantado, baixado e em aberto</div>', unsafe_allow_html=True)

    mensal = (
        df_filt.dropna(subset=["Mes_Num"])
        .groupby(["Mes_Num", "Mes_Nome"], as_index=False)
        .agg(
            Valor=("Valor", "sum"),
            Baixado=("Baixado", "sum"),
            Saldo=("Saldo", "sum")
        )
        .sort_values("Mes_Num")
    )

    if not mensal.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Baixado",
            x=mensal["Mes_Nome"],
            y=mensal["Baixado"] / 1_000_000,
            marker_color="#059669",
            hovertemplate="<b>%{x}</b><br>Baixado: R$ %{y:.2f} mi<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            name="Em aberto (por mês de inclusão)",
            x=mensal["Mes_Nome"],
            y=mensal["Saldo"] / 1_000_000,
            marker_color="#dc2626",
            text=[f"{v/1_000_000:.1f}".replace(".", ",") for v in mensal["Valor"]],
            textposition="outside",
            textfont=dict(size=10, color="#475569", family="Inter"),
            hovertemplate="<b>%{x}</b><br>Em aberto: R$ %{y:.2f} mi<extra></extra>"
        ))
        max_y = (mensal["Valor"].max() / 1_000_000) * 1.18
        fig.update_layout(
            barmode="stack",
            height=225,
            margin=dict(l=6, r=6, t=12, b=6),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickfont=dict(size=10.5, color="#475569", family="Inter"), fixedrange=True),
            yaxis=dict(showgrid=False, showticklabels=False, range=[0, max_y if max_y > 0 else 1], fixedrange=True),
            legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="left", x=0, font=dict(size=10.5, color="#475569", family="Inter")),
            bargap=0.25
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Sem dados mensais para o filtro selecionado.")

    st.markdown("</div>", unsafe_allow_html=True)

with col_conc:
    top3_df = forn_grp.head(3)
    top3_soma = top3_df["Saldo_Aberto"].sum()
    top3_pct = (top3_soma / total_aberto * 100) if total_aberto > 0 else 0.0
    nomes_top3 = ", ".join([n.split()[0] for n in top3_df["Fornecedor"].tolist()]) if not top3_df.empty else "—"

    crit_df = forn_grp[forn_grp["Criticidade"] == "Crítico"]
    qtd_crit = len(crit_df)
    soma_crit = crit_df["Saldo_Aberto"].sum()
    pct_crit = (soma_crit / total_aberto * 100) if total_aberto > 0 else 0.0

    st.markdown(f"""
    <div class="panel-box">
        <div class="panel-title">Principais conclusões</div>
        <ul class="conclusoes-list">
            <li>
                Do total adiantado de <b>{fmt_mi(total_adiantado)}</b>, <b>{fmt_pct(pct_baixado)}</b> já foi baixado.
                Restam <b>{fmt_mi(total_aberto)}</b> ({fmt_pct(pct_aberto)}) em {fmt_int(qtd_aberto)} adiantamentos.
            </li>
            <li>
                O saldo é muito concentrado: os 3 maiores fornecedores ({nomes_top3}) somam <b>{fmt_pct(top3_pct)}</b> do saldo;
                os 5 maiores, <b>{fmt_pct(top5_pct, 0)}</b>.
            </li>
            <li>
                <b>{fmt_int(qtd_crit)} fornecedores críticos</b> concentram <b>{fmt_mi(soma_crit)}</b> ({fmt_pct(pct_crit)} do saldo)
                e devem ser priorizados na cobrança de NF/regularização.
            </li>
            <li>
                <b>{fmt_brl(saldo_90)}</b> estão sem baixa há mais de 90 dias ({fmt_int(qtd_90)} adiantamentos):
                risco de envelhecimento e de dificuldade de regularização.
            </li>
            <li>
                Boa parte do saldo é recente (adiantamentos dos últimos meses), o que pode refletir ciclo normal de entrega/NF, mas exige acompanhamento de prazo.
            </li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# LINHA 5: TABELAS DETALHADAS (TOP 20 FORNECEDORES & 15 MAIORES ITENS)
# ==============================================================================
col_t1, col_t2 = st.columns([1.0, 1.05])

with col_t1:
    st.markdown('<div class="panel-box"><div class="panel-title">Top 20 fornecedores com saldo em aberto</div>', unsafe_allow_html=True)
    if not forn_grp.empty:
        html_t1 = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>Fornecedor</th><th style="text-align:right">Saldo em aberto</th><th style="text-align:right">% do saldo</th><th style="text-align:right">Itens</th><th style="text-align:right">Mais antigo (dias)</th><th style="text-align:center">Criticidade</th></tr></thead><tbody>'
        for idx, r in forn_grp.head(20).iterrows():
            pct_s = (r["Saldo_Aberto"] / total_aberto * 100) if total_aberto > 0 else 0.0
            pct_s_str = f"{pct_s:.0f}%" if pct_s >= 5.5 else f"{pct_s:.1f}%".replace(".", ",")
            c_cls = "badge-critico" if r["Criticidade"] == "Crítico" else ("badge-atencao" if r["Criticidade"] == "Atenção" else "badge-monitorar")
            html_t1 += f'<tr><td>{idx+1}</td><td class="td-bold">{r["Fornecedor"]}</td><td style="text-align:right" class="td-bold">{fmt_brl(r["Saldo_Aberto"])}</td><td style="text-align:right">{pct_s_str}</td><td style="text-align:right">{fmt_int(r["Qtd_Itens"])}</td><td style="text-align:right">{fmt_int(r["Max_Dias"])}</td><td style="text-align:center"><span class="badge {c_cls}">{r["Criticidade"]}</span></td></tr>'
        html_t1 += '</tbody></table></div>'
        st.markdown(html_t1, unsafe_allow_html=True)
    else:
        st.info("Nenhum registro encontrado.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_t2:
    st.markdown('<div class="panel-box"><div class="panel-title">15 maiores adiantamentos em aberto (por item)</div>', unsafe_allow_html=True)
    top15 = df_aberto.sort_values("Saldo", ascending=False).head(15)
    if not top15.empty:
        html_t2 = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>Adiant.</th><th>Fornecedor</th><th style="text-align:center">Inclusão</th><th style="text-align:right">Valor</th><th style="text-align:right">Saldo</th><th style="text-align:right">Dias</th><th>Observação</th></tr></thead><tbody>'
        for _, r in top15.iterrows():
            dt_inc = r["Data inclusão"].strftime("%d/%m/%Y") if pd.notna(r["Data inclusão"]) else "—"
            adt_val = r["Adiantamento"]
            try:
                adt_id = str(int(float(adt_val))) if pd.notna(adt_val) and str(adt_val).strip() != "" else "—"
            except Exception:
                adt_id = str(adt_val) if pd.notna(adt_val) else "—"
            html_t2 += f'<tr><td class="td-bold">{adt_id}</td><td class="td-bold" style="max-width:185px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{r["Fornecedor"]}">{r["Fornecedor"]}</td><td style="text-align:center">{dt_inc}</td><td style="text-align:right">{fmt_brl(r["Valor"])}</td><td style="text-align:right" class="td-bold">{fmt_brl(r["Saldo"])}</td><td style="text-align:right">{fmt_int(r["Dias"])}</td><td class="td-muted" title="{r["Observação"]}">{r["Observação"]}</td></tr>'
        html_t2 += '</tbody></table></div>'
        st.markdown(html_t2, unsafe_allow_html=True)
    else:
        st.info("Nenhum registro encontrado.")
    st.markdown('</div>', unsafe_allow_html=True)

estab_nome = df_filt["Estabelecimento"].iloc[0] if not df_filt.empty else "SOS Cardio"
st.markdown(f"""
<div class="exec-footer">
    Fonte: aba {ABA_ADT} ({fmt_int(qtd_total)} adiantamentos, Estabelecimento {estab_nome}).
    Baixado = Valor − Saldo. Em aberto = Saldo. Idade calculada até {data_ref.strftime("%d/%m/%Y")}.
</div>
""", unsafe_allow_html=True)
