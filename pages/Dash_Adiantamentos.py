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
        color: #0f1
