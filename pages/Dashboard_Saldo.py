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

    /* Badges */
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 800; text-align: center; min-width: 68px; }
    .badge-critico { background-color: rgba(220, 38, 38, 0.1); color: #dc2626; border: 1px solid rgba(220, 38, 38, 0.25); }
    .badge-atencao { background-color: rgba(217, 119, 6, 0.1); color: #d97706; border: 1px solid rgba(217, 119, 6, 0.25); }
    .badge-monitorar { background-color: rgba(37, 99, 235, 0.1); color: #2563eb; border: 1px solid rgba(37, 99, 235, 0.25); }

    /* Tabelas */
    .tabela-container {
        overflow: auto; border: 1px solid #e2e8f0; border-radius: 10px;
        background: #ffffff; max-height: 480px; width: 100%;
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
        if isinstance(val, (int, float)):
            return float(val)
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
    df["Fornecedor"] = df["Pessoa física/jurídica"].fillna("Não Informado").astype(str).str.strip()
elif "Fornecedor" not in df.columns:
    df["Fornecedor"] = "Não Informado"

if "Banco" not in df.columns:
