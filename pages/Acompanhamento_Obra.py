import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import textwrap
import io
from datetime import datetime

try:
    st.set_page_config(
        page_title="Acompanhamento de Obras",
        layout="wide",
        page_icon="🏗️",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# ==============================================================================
# PALETA — tema claro (sem roxo forte)
# ==============================================================================
AZUL, VERDE, AMBAR, VERMELHO = "#2563eb", "#059669", "#2563eb", "#dc2626"
AZUL_CLARO, LARANJA, CIANO, ROSA = "#60a5fa", "#2563eb", "#0891b2", "#059669"
TXT, MUTED, BORDA = "#0f172a", "#64748b", "#e2e8f0"

ESPACO_ENTRE_BLOCOS = "0.75rem"
AJUSTE_APOS_KPIS = "0.75rem"

# Paleta de obras: azuis claros + complementares suaves (sem roxo intenso)
PALETA_OBRAS = ["#2563eb", "#059669", "#0891b2", "#60a5fa", "#34d399", "#93c5fd"]

# ==============================================================================
# CSS — identidade branca + Total sticky
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #f8fafc !important; color: #0f172a; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 0.65rem 1rem 0.7rem; max-width: 100%; }
    div[data-testid="stVerticalBlock"] { gap: __GAP__; }
    [data-testid="stMarkdownContainer"] { color: #0f172a; }

    [data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stWidgetLabel"] p { color: #64748b !important; font-size: 12px; font-weight: 600; }
    .side-sec { font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #64748b; text-transform: uppercase; margin: 6px 0 -2px; }
    .side-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 12px; margin-top: 8px; }
    .side-card small { display: block; color: #64748b; font-size: 11px; }
    .side-card b { color: #0f172a; font-size: 13px; }

    [data-baseweb="select"] > div { background: #ffffff !important; border-color: #e2e8f0 !important; color: #0f172a !important; }
    [data-baseweb="select"] span, [data-baseweb="select"] input { color: #0f172a !important; }
    [data-baseweb="select"] svg { fill: #64748b; }
    [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #ffffff !important; }
    li[role="option"] { color: #0f172a !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background: #f1f5f9 !important; }
    span[data-baseweb="tag"] { background: #2563eb !important; color: #fff !important; }
    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-weight: 700 !important; padding: 0.55rem 1rem !important;
    }
    [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-weight: 700 !important; height: 36px; font-size: 12px;
    }

    .top { display: flex; justify-content: space-between; align-items: center; gap: 16px;
           padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px solid #e2e8f0; }
    .top h1 { margin: 0; font-size: 22px; font-weight: 800; color: #0f172a; }
    .top p { margin: 2px 0 0; font-size: 13px; color: #64748b; }
    .pills { display: flex; gap: 10px; flex-wrap: wrap; }
    .pill { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 6px 14px; min-width: 120px;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04); }
    .pill small { display: block; font-size: 10px; color: #64748b; }
    .pill b { font-size: 13px; color: #0f172a; white-space: nowrap; }

    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: __KPI_GAP__; }
    .kpi { padding: 12px 14px; border-radius: 12px; min-height: 110px; background: #ffffff;
           border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(15,23,42,0.05); border-left: 3px solid #2563eb; }
    .kpi.green { border-left-color: #059669; }
    .kpi.amber { border-left-color: #2563eb; }
    .kpi.purple { border-left-color: #60a5fa; }
    .kpi-t { font-size: 10px; font-weight: 800; letter-spacing: 0.4px; text-transform: uppercase; color: #64748b; min-height: 22px; }
    .kpi-v { font-size: 17px; font-weight: 800; color: #0f172a; margin: 6px 0 3px; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .kpi-sub { font-size: 11px; color: #64748b; font-weight: 600; }
    .kpi-sub.up { color: #059669; }
    .kpi-sub.down { color: #dc2626; }
    .pb { width: 100%; background: #e2e8f0; height: 6px; border-radius: 3px; margin-top: 6px; overflow: hidden; }
    .pb span { display: block; height: 100%; border-radius: 3px; }

    .section-title {
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #0f172a; margin: 18px 0 10px; padding-left: 10px; border-left: 3px solid #2563eb;
    }

    .unified-summary-box {
        max-width: 100%; overflow-x: auto;
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        margin-top: 8px; margin-bottom: 16px; overflow: auto;
        box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    }
    .unified-table { width: 100%; border-collapse: collapse; font-size: 11px; text-align: left; color: #334155; }
    .unified-table th {
        background: #f8fafc; color: #64748b; font-weight: 700; text-transform: uppercase;
        padding: 10px 8px; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #f1f5f9; text-align: left;
    }
    .unified-table th:last-child { border-right: none; }
    .unified-table td {
        color: #334155;
        padding: 10px 8px; border-bottom: 1px solid #f1f5f9; border-right: 1px solid #f1f5f9;
        background: #ffffff; font-variant-numeric: tabular-nums; text-align: left;
    }
    .unified-table td:last-child { border-right: none; }
    /* Coluna Total FIXA à direita */
    .unified-table th.col-total,
    .unified-table td.col-total {
        position: sticky;
        right: 0;
        z-index: 5;
        background: #f1f5f9 !important;
        font-weight: 800;
        border-left: 2px solid #e2e8f0;
        min-width: 90px;
        box-shadow: -4px 0 8px rgba(15,23,42,0.04);
    }
    .unified-table th.col-total { z-index: 6; }
    .row-label {
        text-align: left; padding-left: 14px !important; font-weight: 700; color: #64748b;
        background: #f8fafc !important; width: 170px; border-right: 2px solid #e2e8f0 !important;
        position: sticky; left: 0; z-index: 4;
    }
    .val-real { font-weight: 800; color: #059669; }
    .val-orc { font-weight: 800; color: #2563eb; }

    .fases-table-container {
        width: 100%; max-height: none; height: auto;
        overflow-x: auto; overflow-y: hidden;
        border: 1px solid #e2e8f0; border-radius: 12px;
        background: #ffffff; box-shadow: 0 1px 3px rgba(15,23,42,0.04);
        scrollbar-width: thin; scrollbar-color: #cbd5e1 transparent;
    }
    .fases-table {
        width: 100%; border-collapse: collapse; font-size: 11px; white-space: nowrap;
        background: #ffffff; table-layout: fixed; color: #334155;
    }
    .fases-table thead { position: sticky; top: 0; z-index: 15; }
    .fases-table th {
        background: #f8fafc; color: #64748b; font-weight: 700; text-transform: uppercase;
        padding: 12px 10px; border-bottom: 1px solid #e2e8f0; text-align: left;
        position: sticky; top: 0; z-index: 15;
    }
    .fases-table td {
        color: #111827 !important;
        padding: 10px; border-bottom: 1px solid #f1f5f9; color: #334155;
        background: #ffffff; text-align: left;
    }
    .fases-table th:nth-child(1), .fases-table td:nth-child(1) {
        width: 300px; min-width: 300px; max-width: 300px; position: sticky; left: 0; z-index: 10;
        background: #ffffff; border-right: 2px solid #e2e8f0; overflow: hidden; text-overflow: ellipsis;
    }
    .fases-table th:nth-child(1) { z-index: 20; background: #f8fafc; }
    .fases-table th:nth-child(2), .fases-table td:nth-child(2) { width: 140px; min-width: 140px; max-width: 140px; }
    .fases-table th:nth-child(n+3), .fases-table td:nth-child(n+3) { width: 110px; min-width: 110px; max-width: 110px; }
    .fases-table tr:hover td { background: #f8fafc; }
    .total-geral-row td {
        font-weight: 900; background: #f1f5f9 !important; border-top: 1px solid #e2e8f0; color: #0f172a;
    }

    .drilldown-label { cursor: pointer; display: flex; align-items: center; margin: 0; width: 100%; height: 100%; color: #0f172a; }
    .toggle-checkbox { display: none; }
    .indicator { margin-right: 8px; font-size: 11px; transition: transform 0.2s; display: inline-block; color: #2563eb; }
    .obra-group .sub-row { display: none; }
    .unified-table td.detail-black { color: #111827 !important; }
    .obra-group:has(.toggle-checkbox:checked) .sub-row { display: table-row; }
    .obra-group:has(.toggle-checkbox:checked) .indicator { transform: rotate(90deg); }
    .orcado-indicator { display: block; font-size: 9px; color: #64748b; margin-top: 3px; font-weight: 600; }

    .fases-table-container::-webkit-scrollbar,
    .unified-summary-box::-webkit-scrollbar { height: 6px; width: 6px; }
    .fases-table-container::-webkit-scrollbar-thumb,
    .unified-summary-box::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 6px; }

    hr { border: none !important; border-top: 1px solid #e2e8f0 !important; margin: 20px 0 !important; }
</style>
"""
st.markdown(
    textwrap.dedent(css).replace("__GAP__", ESPACO_ENTRE_BLOCOS).replace("__KPI_GAP__", AJUSTE_APOS_KPIS),
    unsafe_allow_html=True,
)

# ==============================================================================
# HELPERS
# ==============================================================================
def limpa_valor(valor):
    try:
        if pd.isna(valor):
            return 0.0
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return float(valor)
        v_str = str(valor).strip()
        if v_str in ["", "-", "nan", "None", "NaN"]:
            return 0.0
        v_str = v_str.replace("R$", "").replace(" ", "")
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        if "," in v_str:
            v_str = v_str.replace(".", "").replace(",", ".")
        else:
            v_str = v_str.replace(",", "")
        return float(v_str)
    except Exception:
        return 0.0


def formatar_moeda(valor):
    try:
        val = float(valor)
        if val == 0:
            return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "-"


def formatar_moeda_curta(valor):
    try:
        val = float(valor)
        if val == 0 or pd.isna(val):
            return "-"
        if abs(val) >= 1_000_000:
            return f"R$ {val/1_000_000:.1f}M".replace('.', ',')
        if abs(val) >= 1_000:
            return f"R$ {val/1_000:.0f}K".replace('.', ',')
        return f"R$ {val:.0f}"
    except Exception:
        return "-"


def extract_month(m):
    """Extrai o mês de cabeçalhos como JANEIRO, 01/2026, 2026-01 ou Jan-2026."""
    try:
        if pd.isna(m):
            return 0
        s = str(m).strip().lower()
        nomes = {
            'jan': 1, 'janeiro': 1, 'fev': 2, 'fevereiro': 2, 'mar': 3, 'março': 3, 'marco': 3,
            'abr': 4, 'abril': 4, 'mai': 5, 'maio': 5, 'jun': 6, 'junho': 6,
            'jul': 7, 'julho': 7, 'ago': 8, 'agosto': 8, 'set': 9, 'setembro': 9,
            'out': 10, 'outubro': 10, 'nov': 11, 'novembro': 11, 'dez': 12, 'dezembro': 12,
        }
        nome = re.search(r'[a-zç]+', s)
        if nome and nome.group(0)[:3] in nomes:
            return nomes[nome.group(0)[:3]]
        nums = re.findall(r'\d+', s)
        if len(nums) >= 2:
            a, b = int(nums[0]), int(nums[1])
            if a >= 1900 and 1 <= b <= 12:  # YYYY-MM
                return b
            if 1 <= a <= 12 and b >= 1900:  # MM/YYYY
                return a
        if nums:
            n = int(nums[0])
            return n if 1 <= n <= 12 else 0
    except Exception:
        pass
    return 0


def extract_year(value, default=None):
    """Extrai ano de datas, números ou textos como 2027, Jan/27 e 01/2027."""
    try:
        if pd.isna(value) or str(value).strip() in ('', '-', 'nan', 'None'):
            return default
        if isinstance(value, (datetime, pd.Timestamp)):
            return int(value.year)
        if hasattr(value, 'year') and hasattr(value, 'month'):
            return int(value.year)
        texto = str(value)
        anos_4_digitos = re.findall(r'\d{4}', texto)
        if anos_4_digitos:
            ano = int(anos_4_digitos[-1])
            if 1900 <= ano <= 2200:
                return ano
        # Para formatos como Jan/26, considera o último bloco numérico,
        # evitando interpretar o mês 01 de 01/2026 como ano 2001.
        nums_2_digitos = re.findall(r'\d{2}', texto)
        if nums_2_digitos:
            y = int(nums_2_digitos[-1])
            return 2000 + y if y < 70 else 1900 + y
    except Exception:
        pass
    return default


def mapa_cores_obras(lista):
    ordenadas = sorted([str(o) for o in lista if o])
    return {obra: PALETA_OBRAS[i % len(PALETA_OBRAS)] for i, obra in enumerate(ordenadas)}


def layout_fig(fig, h=280, legenda=True):
    fig.update_layout(
        height=h,
        margin=dict(l=0, r=0, t=48 if legenda else 8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=11, color=MUTED),
        separators=",.",
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11, color=TXT), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#ffffff", font_color=TXT, bordercolor=BORDA),
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDA, tickfont=dict(size=10, color=MUTED))
    fig.update_yaxes(
        gridcolor="rgba(148,163,184,0.25)", zeroline=False,
        tickprefix="R$ ", tickformat=".2s", tickfont=dict(size=10, color=MUTED),
    )
    return fig


# ==============================================================================
# CARGA
# ==============================================================================
@st.cache_data(ttl=60, show_spinner="Carregando dados…")
def carregar_dados_obras_detalhado():
    conn = conectar_sheets()
    if not conn:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        df_orc = conn.read(worksheet="Orçamento_Obra", ttl=0)
        df_orc.columns = [str(c).strip() for c in df_orc.columns]

        map_meses = {
            'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'MARCO': 3,
            'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6, 'JULHO': 7,
            'AGOSTO': 8, 'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12
        }
        meses_existentes = [c for c in df_orc.columns if extract_month(c) in range(1, 13)]
        col_resumo = next((c for c in df_orc.columns if 'RESUMO' in c.upper() or 'OBRA' in c.upper()), df_orc.columns[0])
        col_item = next((c for c in df_orc.columns if c.upper() in [
            'CATEGORIA', 'FASE', 'ITEM', 'DESCRIÇÃO', 'DESCRICAO', 'ETAPA', 'SERVIÇO', 'SERVICO', 'DETALHE', 'CONTA'
        ]), None)

        df_orc = df_orc[df_orc[col_resumo].astype(str).str.upper().str.strip() != 'TOTAL'].copy()
        df_orc['Obra'] = df_orc[col_resumo].astype(str).str.upper().str.strip()
        col_ano_orc = next((c for c in df_orc.columns if str(c).strip().upper() in ['ANO', 'ANO ORCAMENTO', 'ANO ORÇAMENTO', 'EXERCICIO', 'EXERCÍCIO']), None)
        # Compatibilidade: linhas antigas sem coluna ANO continuam em 2026.
        df_orc['Ano'] = df_orc[col_ano_orc].apply(lambda x: extract_year(x, 2026)) if col_ano_orc else 2026

        if col_item and col_item != col_resumo:
            df_orc['Item'] = df_orc[col_item].fillna('GERAL').astype(str).str.strip().str.upper()
            id_vars = ['Obra', 'Item', 'Ano']
        else:
            # A aba de resumo por obra não possui coluna de item: não usar Custo R$, %
            # ou qualquer coluna de competência como identificador do lançamento.
            df_orc['Item'] = df_orc['Obra']
            id_vars = ['Obra', 'Item', 'Ano']

        df_orc_melt = df_orc.melt(id_vars=id_vars, value_vars=meses_existentes, var_name='Mes_Nome', value_name='Valor_Orcado')
        df_orc_melt['Mes'] = df_orc_melt['Mes_Nome'].apply(extract_month)
        ano_coluna = pd.to_numeric(df_orc_melt['Ano'], errors='coerce')
        ano_cabecalho = df_orc_melt['Mes_Nome'].apply(lambda x: extract_year(x, None))
        df_orc_melt['Ano'] = ano_cabecalho.where(ano_cabecalho.notna(), ano_coluna)
        df_orc_melt['Ano'] = pd.to_numeric(df_orc_melt['Ano'], errors='coerce').fillna(2026).astype(int)
        nomes_mes_abrev = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
        df_orc_melt['Competencia'] = df_orc_melt['Mes'].map(nomes_mes_abrev) + '-' + df_orc_melt['Ano'].astype(str)
        df_orc_melt['Valor_Orcado'] = df_orc_melt['Valor_Orcado'].apply(limpa_valor)

        df_fases = pd.DataFrame()
        try:
            df_fases_raw = conn.read(worksheet="Fases_Obra", ttl=0)
            valid_cols = [c for c in df_fases_raw.columns if str(c).strip() and not str(c).strip().lower().startswith('unnamed')]
            df_fases = df_fases_raw[valid_cols].copy()
            df_fases = df_fases.replace(r'^\s*$', pd.NA, regex=True).dropna(axis=1, how='all')
            if not df_fases.empty and len(df_fases.columns) >= 2:
                df_fases['Obra'] = df_fases[df_fases.columns[0]].fillna('').astype(str).str.strip().str.upper()
                df_fases['Fase_Tarefa'] = df_fases[df_fases.columns[1]].fillna('').astype(str).str.strip().str.upper()
            elif not df_fases.empty and len(df_fases.columns) == 1:
                df_fases['Obra'] = df_fases[df_fases.columns[0]].fillna('').astype(str).str.strip().str.upper()
                df_fases['Fase_Tarefa'] = "GERAL"
        except Exception:
            df_fases = pd.DataFrame()

        df_recursos = pd.DataFrame()
        try:
            df_recursos_raw = conn.read(worksheet="Recursos_Obra", ttl=0)
            valid_cols_rec = [c for c in df_recursos_raw.columns if str(c).strip() and not str(c).strip().lower().startswith('unnamed')]
            df_recursos = df_recursos_raw[valid_cols_rec].copy()
            # Normaliza as captações pela data efetiva e pelo valor alocado à obra.
            col_data_rec = next((c for c in df_recursos.columns if str(c).strip().lower() in ['data', 'data alocacao', 'data alocação']), None)
            col_valor_rec = next((c for c in df_recursos.columns if 'recurso' in str(c).lower() and 'aloc' in str(c).lower()), None)
            if col_data_rec and col_valor_rec:
                df_recursos['_Data_Alocacao'] = pd.to_datetime(df_recursos[col_data_rec], errors='coerce', dayfirst=True)
                df_recursos['_Valor_Alocado'] = df_recursos[col_valor_rec].apply(limpa_valor)
                df_recursos['_Ano'] = df_recursos['_Data_Alocacao'].dt.year
                df_recursos['_Mes'] = df_recursos['_Data_Alocacao'].dt.month
                df_recursos = df_recursos[df_recursos['_Data_Alocacao'].notna() & (df_recursos['_Valor_Alocado'] != 0)].copy()
            else:
                df_recursos['_Ano'] = pd.Series(dtype='int64')
                df_recursos['_Mes'] = pd.Series(dtype='int64')
                df_recursos['_Valor_Alocado'] = pd.Series(dtype='float64')
        except Exception:
            df_recursos = pd.DataFrame()

        df_real = conn.read(worksheet="Realizado_Obra", ttl=0)
        df_real['Obra'] = df_real['Categoria'].astype(str).str.upper().str.strip()
        col_data = next((c for c in df_real.columns if 'data' in c.lower()), 'DATA PGTO')
        datas_pgto = pd.to_datetime(df_real[col_data], errors='coerce', dayfirst=True)
        df_real['Mes'] = datas_pgto.dt.month
        mes_texto = df_real['MÊS'].apply(extract_month)
        df_real['Mes'] = df_real['Mes'].fillna(mes_texto).fillna(0).astype(int)
        df_real['Ano'] = datas_pgto.dt.year
        ano_texto = df_real['MÊS'].apply(lambda x: extract_year(x, None))
        df_real['Ano'] = df_real['Ano'].fillna(ano_texto)
        # Se a linha antiga não tiver ano na data nem em MÊS, mantém o histórico no ano-base 2026.
        df_real['Ano'] = pd.to_numeric(df_real['Ano'], errors='coerce').fillna(2026).astype(int)
        df_real['Valor_Realizado'] = df_real['Valor'].apply(limpa_valor)
        col_forn = next((c for c in df_real.columns if 'forn' in c.lower()), 'Fornecedor')
        col_nf = next((c for c in df_real.columns if 'nf' in c.lower()), 'NF')
        df_real['Fornecedor'] = df_real[col_forn].fillna('NÃO INFORMADO').astype(str).str.upper()
        df_real['NF'] = df_real[col_nf].fillna('-').astype(str)
        df_real['Data_Pgto'] = df_real[col_data].fillna('-').astype(str).str.replace('00:00:00', '').str.strip()
        return df_orc_melt, df_real, df_fases, df_recursos
    except Exception as e:
        st.error(f"Erro ao processar dados de obras: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


df_orcado, df_realizado, df_fases, df_recursos = carregar_dados_obras_detalhado()
if df_orcado.empty and df_realizado.empty:
    st.warning("Nenhum dado encontrado nas abas do banco de dados.")
    st.stop()

obras_orcadas = df_orcado['Obra'].dropna().astype(str).unique().tolist() if not df_orcado.empty else []
obras_realizadas = df_realizado['Obra'].dropna().astype(str).unique().tolist() if not df_realizado.empty else []
todas_obras = set(obras_orcadas) | set(obras_realizadas)
lista_obras = sorted([o for o in todas_obras if o.strip() not in ['NAN', '0', '', 'DIVERSAS', 'SEGUROS']])
CORES_OBRA = mapa_cores_obras(lista_obras)

# ==============================================================================
# FILTROS
# ==============================================================================
df_orc_filtrado = df_orcado.copy()
df_real_filtrado = df_realizado.copy()
df_fases_filtrado = df_fases.copy()

ano_selecionado = "Todos"
mes_selecionado = "Todos"
with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)
    obra_selecionada = st.selectbox("Empreendimento / Obra", ["Todas"] + lista_obras)
    if st.button("↻ Limpar filtros", use_container_width=True):
        st.rerun()

    if obra_selecionada != "Todas":
        df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Obra'] == obra_selecionada]
        df_real_filtrado = df_real_filtrado[df_real_filtrado['Obra'] == obra_selecionada]
        if not df_fases_filtrado.empty and 'Obra' in df_fases_filtrado.columns:
            df_fases_filtrado = df_fases_filtrado[df_fases_filtrado['Obra'] == obra_selecionada]

    st.markdown("<div class='side-sec' style='margin-top:14px'>Relatórios</div>", unsafe_allow_html=True)
    df_real_detalhe_exp = df_real_filtrado.copy()
    if not df_real_detalhe_exp.empty:
        df_real_detalhe_exp['Valor_Realizado'] = df_real_detalhe_exp['Valor_Realizado'].apply(limpa_valor)
        df_real_detalhe_exp['Fornecedor'] = df_real_detalhe_exp['Fornecedor'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
        df_real_detalhe_exp['NF'] = df_real_detalhe_exp['NF'].fillna('-').astype(str).str.strip()
        df_real_detalhe_exp['Data_Pgto'] = df_real_detalhe_exp['Data_Pgto'].fillna('-').astype(str).str.replace('00:00:00', '', regex=False).str.strip()

    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        if not df_fases_filtrado.empty:
            df_fases_filtrado.to_excel(writer, sheet_name='Fases_Obra', index=False)
        if not df_real_detalhe_exp.empty:
            df_real_detalhe_exp.to_excel(writer, sheet_name='Transacoes_Realizadas', index=False)
        if not df_orc_filtrado.empty:
            df_orc_filtrado.to_excel(writer, sheet_name='Orcado_Mensal', index=False)
        if not df_recursos.empty:
            df_recursos.to_excel(writer, sheet_name='Recursos_Obra', index=False)
    st.download_button(
        label="📥 Baixar Relatório Completo",
        data=output_excel.getvalue(),
        file_name="relatorio_detalhado_obras.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ==============================================================================
# CÁLCULOS
# ==============================================================================
total_orcado = df_orc_filtrado['Valor_Orcado'].sum()
total_realizado = df_real_filtrado['Valor_Realizado'].sum()
saldo_orcamento = total_orcado - total_realizado
consumo_geral_perc = (total_realizado / total_orcado * 100) if total_orcado > 0 else 0

# Total captado continua sendo exibido no KPI; no fluxo, cada captação
# entra somente na competência da sua data (não no saldo inicial).
caixa_inicial_base = float(df_recursos['_Valor_Alocado'].sum()) if not df_recursos.empty and '_Valor_Alocado' in df_recursos.columns else 0.0
if caixa_inicial_base <= 0:
    caixa_inicial_base = 10_000_000.0  # compatibilidade caso a aba não esteja disponível
caixa_disponivel = caixa_inicial_base - total_realizado
df_real_ano = df_realizado.copy()
mes_atual = int(mes_selecionado) if mes_selecionado != "Todos" else (int(df_real_ano['Mes'].max()) if not df_real_ano.empty else 0)
mes_anterior = mes_atual - 1

df_real_mom = df_realizado.copy()
if obra_selecionada != "Todas":
    df_real_mom = df_real_mom[df_real_mom['Obra'] == obra_selecionada]

realizado_atual = df_real_mom[df_real_mom['Mes'] == mes_atual]['Valor_Realizado'].sum()
realizado_anterior = df_real_mom[df_real_mom['Mes'] == mes_anterior]['Valor_Realizado'].sum()
if realizado_anterior > 0:
    mom_pct = ((realizado_atual / realizado_anterior) - 1) * 100
else:
    mom_pct = 100 if realizado_atual > 0 else 0

if mom_pct > 0:
    mom_str, mom_cls = f"↗ +{mom_pct:.1f}% vs Mês {mes_anterior:02d}", "down"
elif mom_pct < 0:
    mom_str, mom_cls = f"↘ {mom_pct:.1f}% vs Mês {mes_anterior:02d}", "up"
else:
    mom_str, mom_cls = f"→ 0.0% vs Mês {mes_anterior:02d}", ""

pb_width = min(consumo_geral_perc, 100)
pb_color = VERMELHO if consumo_geral_perc > 100 else VERDE
saldo_color = VERMELHO if saldo_orcamento < 0 else TXT
caixa_disp_color = VERMELHO if caixa_disponivel < 0 else VERDE
txt_mes = "Todos os anos · Todas as competências"
txt_obra = obra_selecionada if obra_selecionada != "Todas" else "Todas"

# ==============================================================================
# CABEÇALHO + KPIs
# ==============================================================================
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>ACOMPANHAMENTO DE OBRAS</h1>
            <p>Gestão analítica e execução orçamentária</p>
        </div>
        <div class='pills'>
            <div class='pill'><small>Período</small><b>{txt_mes}</b></div>
            <div class='pill'><small>Obra</small><b>{txt_obra}</b></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f"""
<div class='kpi-grid'>
    <div class='kpi'>
        <div class='kpi-t'>Orçamento total</div>
        <div class='kpi-v'>{formatar_moeda(total_orcado)}</div>
        <div class='kpi-sub'>Valor planejado atualizado</div>
    </div>
    <div class='kpi purple'>
        <div class='kpi-t'>Recursos alocados</div>
        <div class='kpi-v'>{formatar_moeda(caixa_inicial_base)}</div>
        <div class='kpi-sub'>Capital alocado inicial</div>
    </div>
    <div class='kpi green'>
        <div class='kpi-t'>Orçamento utilizado</div>
        <div class='kpi-v'>{formatar_moeda(total_realizado)}</div>
        <div class='kpi-sub' style='color:{pb_color}'>{consumo_geral_perc:.1f}% do orçado</div>
        <div class='pb'><span style='width:{pb_width:.1f}%;background:{pb_color}'></span></div>
    </div>
    <div class='kpi amber'>
        <div class='kpi-t'>Orçamento restante</div>
        <div class='kpi-v' style='color:{saldo_color}'>{formatar_moeda(saldo_orcamento)}</div>
        <div class='kpi-sub'>Para finalização da obra</div>
    </div>
    <div class='kpi'>
        <div class='kpi-t'>Caixa disponível</div>
        <div class='kpi-v' style='color:{caixa_disp_color}'>{formatar_moeda(caixa_disponivel)}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# EVOLUÇÃO MENSAL · TODAS AS COMPETÊNCIAS (COM TOTALIZADORES)
# ==============================================================================
df_orc_m_base = df_orcado.copy()
df_real_m_base = df_realizado[df_realizado['Mes'] > 0].copy()
if obra_selecionada != "Todas":
    df_orc_m_base = df_orc_m_base[df_orc_m_base['Obra'] == obra_selecionada]
    df_real_m_base = df_real_m_base[df_real_m_base['Obra'] == obra_selecionada]

meses_nomes = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
               7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
periodos_set = set()
for dfx in (df_orc_m_base, df_real_m_base):
    if not dfx.empty:
        periodos_set.update((int(r.Ano), int(r.Mes)) for r in dfx[['Ano','Mes']].dropna().itertuples(index=False) if int(r.Mes) > 0)
if not df_recursos.empty and {'_Ano', '_Mes'}.issubset(df_recursos.columns):
    periodos_set.update((int(a), int(m)) for a, m in zip(df_recursos['_Ano'].dropna(), df_recursos.loc[df_recursos['_Ano'].notna(), '_Mes']) if int(m) > 0)
periodos = sorted(periodos_set)
if not periodos:
    periodos = [(2026, m) for m in range(1, 13)]
periodos_labels = [f"{meses_nomes[m]}-{a}" for a,m in periodos]
map_periodo = { (a,m): label for (a,m), label in zip(periodos, periodos_labels) }
for dfx in (df_orc_m_base, df_real_m_base):
    if not dfx.empty:
        dfx['Competencia'] = [map_periodo.get((int(a), int(m)), f"{meses_nomes.get(int(m), '?')}-{int(a)}") for a,m in zip(dfx['Ano'], dfx['Mes'])]

df_orc_mensal = df_orc_m_base.groupby('Competencia')['Valor_Orcado'].sum() if not df_orc_m_base.empty else pd.Series(dtype=float)
df_real_mensal = df_real_m_base.groupby('Competencia')['Valor_Realizado'].sum() if not df_real_m_base.empty else pd.Series(dtype=float)
df_linha = pd.DataFrame({'Competencia': periodos_labels})
df_linha['Valor_Orcado'] = df_linha['Competencia'].map(df_orc_mensal).fillna(0.0)
df_linha['Valor_Realizado'] = df_linha['Competencia'].map(df_real_mensal)
# O corte entre realizado e projetado considera somente competências com
# lançamentos efetivamente realizados (valor diferente de zero). Assim, uma
# linha vazia ou uma data inválida não empurra indevidamente a projeção.
if not df_real_m_base.empty:
    _real_validos = df_real_m_base[
        df_real_m_base['Mes'].between(1, 12)
        & (pd.to_numeric(df_real_m_base['Valor_Realizado'], errors='coerce').fillna(0).abs() > 0)
    ].copy()
else:
    _real_validos = pd.DataFrame()
max_periodo_real = max(
    ((int(r.Ano), int(r.Mes)) for r in _real_validos[['Ano', 'Mes']].dropna().itertuples(index=False)),
    default=None,
) if not _real_validos.empty else None
if max_periodo_real:
    df_linha.loc[[p > max_periodo_real for p in periodos], 'Valor_Realizado'] = None
else:
    df_linha['Valor_Realizado'] = None
tot_real_linha = float(df_linha['Valor_Realizado'].fillna(0).sum())
tot_orc_linha = float(df_linha['Valor_Orcado'].fillna(0).sum())

st.markdown("<div class='section-title'>Evolução mensal · Orçado vs Realizado</div>", unsafe_allow_html=True)
st.markdown(f"""
<div style='display:flex;justify-content:flex-end;align-items:center;gap:18px;flex-wrap:wrap;
            margin:-2px 2px 8px;padding:7px 12px;background:#ffffff;border:1px solid #e2e8f0;
            border-radius:8px;font-size:12px;font-weight:700'>
  <span style='color:{AZUL}'>Total orçado: {formatar_moeda(tot_orc_linha)}</span>
  <span style='color:{VERDE}'>Total realizado: {formatar_moeda(tot_real_linha)}</span>
</div>
""", unsafe_allow_html=True)
fig_linha = go.Figure()
fig_linha.add_trace(go.Scatter(x=df_linha['Competencia'], y=df_linha['Valor_Orcado'], mode='lines+markers', name='Orçado', line=dict(color=AZUL, width=2.5), marker=dict(size=6), fill='tozeroy', fillcolor='rgba(37,99,235,0.10)', hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Orçado</extra>"))
fig_linha.add_trace(go.Scatter(x=df_linha['Competencia'], y=df_linha['Valor_Realizado'], mode='lines+markers', name='Realizado', line=dict(color=VERDE, width=2.5), marker=dict(size=6), fill='tozeroy', fillcolor='rgba(5,150,105,0.12)', connectgaps=False, hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Realizado</extra>"))
fig_linha.update_layout(xaxis=dict(type='category', tickangle=-45), margin=dict(l=8,r=8,t=20,b=48))
st.plotly_chart(layout_fig(fig_linha, 300, True), use_container_width=True, config={'displayModeBar': False})

html_unified = "<div class='unified-summary-box'><table class='unified-table'><thead><tr><th class='row-label'>Competência</th>"
for label in periodos_labels: html_unified += f"<th>{label}</th>"
html_unified += "<th class='col-total'>Total</th></tr></thead><tbody>"
html_unified += "<tr><td class='row-label'>Realizado</td>"
for _, r in df_linha.iterrows(): html_unified += f"<td class='val-real'>{formatar_moeda_curta(r['Valor_Realizado']) if pd.notna(r['Valor_Realizado']) else '-'}</td>"
html_unified += f"<td class='col-total val-real'>{formatar_moeda_curta(tot_real_linha)}</td></tr>"
html_unified += "<tr><td class='row-label'>Orçado</td>"
for _, r in df_linha.iterrows(): html_unified += f"<td class='val-orc'>{formatar_moeda_curta(r['Valor_Orcado'])}</td>"
html_unified += f"<td class='col-total val-orc'>{formatar_moeda_curta(tot_orc_linha)}</td></tr></tbody></table></div>"
st.markdown(html_unified, unsafe_allow_html=True)

# ==============================================================================
# GRÁFICOS
# ==============================================================================
col_g1, col_g2 = st.columns(2, gap="small")

with col_g1:
    st.markdown("<div class='section-title' style='margin-top:4px'>Distribuição de custo por obra</div>", unsafe_allow_html=True)
    df_donut = df_real_filtrado.groupby('Obra')['Valor_Realizado'].sum().reset_index().sort_values('Obra')
    if not df_donut.empty:
        cores_donut = [CORES_OBRA.get(o, PALETA_OBRAS[i % len(PALETA_OBRAS)]) for i, o in enumerate(df_donut['Obra'])]
        fig_donut = go.Figure(go.Pie(
            labels=df_donut['Obra'], values=df_donut['Valor_Realizado'],
            hole=0.62, textinfo="none", sort=False,
            marker=dict(colors=cores_donut, line=dict(color="#ffffff", width=2)),
            hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        ))
        total_d = df_donut['Valor_Realizado'].sum()
        fig_donut.update_layout(annotations=[dict(
            text=f"<b>{formatar_moeda_curta(total_d)}</b><br><span style='font-size:10px;color:#64748b'>Total</span>",
            showarrow=False, font=dict(size=13, color=TXT),
        )])
        st.plotly_chart(layout_fig(fig_donut, 300, True), use_container_width=True, config={'displayModeBar': False})

with col_g2:
    st.markdown("<div class='section-title' style='margin-top:4px'>Consumo de caixa mensal por obra</div>", unsafe_allow_html=True)
    df_stack = df_real_filtrado[df_real_filtrado['Mes'] > 0].groupby(['Ano', 'Mes', 'Obra'])['Valor_Realizado'].sum().reset_index()
    if not df_stack.empty:
        df_stack['Mes_Nome'] = [f"{meses_nomes.get(int(m), '?')}-{int(a)}" for a,m in zip(df_stack['Ano'], df_stack['Mes'])]
        df_stack = df_stack.sort_values(['Ano', 'Mes', 'Obra'])
        df_stack_tot = df_stack.groupby(['Ano', 'Mes', 'Mes_Nome'])['Valor_Realizado'].sum().reset_index()
        obras_no_graf = sorted(df_stack['Obra'].unique().tolist())
        fig_stack = px.bar(
            df_stack, x='Mes_Nome', y='Valor_Realizado', color='Obra',
            category_orders={"Obra": obras_no_graf, "Mes_Nome": periodos_labels},
            color_discrete_map=CORES_OBRA,
        )
        fig_stack.add_trace(go.Scatter(
            x=df_stack_tot['Mes_Nome'], y=df_stack_tot['Valor_Realizado'],
            text=df_stack_tot['Valor_Realizado'].apply(formatar_moeda_curta),
            mode='text', textposition='top center', showlegend=False,
            textfont=dict(size=10, color=TXT, family='Inter'),
        ))
        fig_stack.update_layout(bargap=0.3, xaxis_title=None, yaxis_title=None,
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None))
        st.plotly_chart(layout_fig(fig_stack, 300, True), use_container_width=True, config={'displayModeBar': False})

# ==============================================================================
# FLUXO DE CAIXA DA OBRA
# ==============================================================================
st.markdown("<div class='section-title'>Fluxo de caixa · Realizado vs Projetado</div>", unsafe_allow_html=True)

# Fluxo híbrido: competências até o último mês com pagamento registrado
# usam exclusivamente Realizado_Obra; competências posteriores usam
# exclusivamente Orçamento_Obra. Nunca somar realizado + orçamento no mesmo mês.
saidas_real_dict = df_real_m_base.groupby('Competencia')['Valor_Realizado'].sum().to_dict()
saidas_orc_dict = df_orc_m_base.groupby('Competencia')['Valor_Orcado'].sum().to_dict()
max_comp_real = max_periodo_real
if max_comp_real:
    corte_label = f"{meses_nomes[max_comp_real[1]]}-{max_comp_real[0]}"
    st.caption(f"Fluxo calculado com pagamentos realizados até {corte_label}; a partir da competência seguinte, utiliza o orçamento previsto.")
else:
    st.caption("Ainda não há pagamentos realizados válidos; o fluxo utiliza o orçamento previsto em todas as competências.")

todas_obras_fluxo = set(df_real_m_base['Obra'].unique()) if not df_real_m_base.empty else set()
if not df_orc_m_base.empty:
    todas_obras_fluxo = todas_obras_fluxo.union(set(df_orc_m_base['Obra'].unique()))
obras_fluxo = sorted(list(todas_obras_fluxo))
if obra_selecionada != "Todas":
    obras_fluxo = [obra_selecionada]

real_por_obra_mes = df_real_m_base.groupby(['Competencia', 'Obra'])['Valor_Realizado'].sum().to_dict()
orc_por_obra_mes = df_orc_m_base.groupby(['Competencia', 'Obra'])['Valor_Orcado'].sum().to_dict()

s_ini_list, recursos_mes_list, saidas_tot_list, s_fim_list = [], [], [], []
recursos_por_comp = {}
if not df_recursos.empty and {'_Ano', '_Mes', '_Valor_Alocado'}.issubset(df_recursos.columns):
    for _, rr in df_recursos.iterrows():
        if pd.notna(rr['_Ano']) and pd.notna(rr['_Mes']):
            label_rec = f"{meses_nomes[int(rr['_Mes'])]}-{int(rr['_Ano'])}"
            recursos_por_comp[label_rec] = recursos_por_comp.get(label_rec, 0.0) + float(rr['_Valor_Alocado'])

# O saldo começa zerado. As captações entram na competência indicada em Recursos_Obra.
curr_saldo = 0.0
for comp, (ano_p, mes_p) in zip(periodos_labels, periodos):
    s_ini_list.append(curr_saldo)
    recurso_m = recursos_por_comp.get(comp, 0.0)
    recursos_mes_list.append(recurso_m)
    saida_m = saidas_real_dict.get(comp, 0.0) if max_comp_real and (ano_p, mes_p) <= max_comp_real else saidas_orc_dict.get(comp, 0.0)
    saidas_tot_list.append(saida_m)
    curr_saldo += recurso_m - saida_m
    s_fim_list.append(curr_saldo)

# Faixas do cabeçalho: competências já realizadas em verde e futuras projetadas em salmão.
n_real = sum(1 for p in periodos if max_comp_real and p <= max_comp_real)
n_proj = len(periodos_labels) - n_real

html_fluxo = "<div class='unified-summary-box'><table class='unified-table'><thead>"
html_fluxo += "<tr><th class='row-label' rowspan='2'>Fluxo de Caixa</th>"
if n_real:
    html_fluxo += f"<th colspan='{n_real}' style='background:#86efac;color:#065f46;text-align:center;font-weight:800;padding:7px'>REALIZADO</th>"
if n_proj:
    html_fluxo += f"<th colspan='{n_proj}' style='background:#fdba9a;color:#9a3412;text-align:center;font-weight:800;padding:7px'>PROJETADO</th>"
html_fluxo += "</tr><tr>"
for comp in periodos_labels:
    html_fluxo += f"<th>{comp}</th>"
html_fluxo += "</tr></thead><tbody>"

# Saldo inicial preserva a cor de cada fase: verde no realizado e azul no projetado.
html_fluxo += "<tr><td class='row-label'>Saldo Inicial</td>"
for idx, val in enumerate(s_ini_list):
    css = "val-real" if max_comp_real and periodos[idx] <= max_comp_real else "val-orc"
    color = VERMELHO if val < 0 else (VERDE if css == "val-real" else "#2563eb")
    html_fluxo += f"<td class='{css}' style='color:{color};font-weight:700'>{formatar_moeda_curta(val)}</td>"
html_fluxo += "</tr>"

# Captações no mesmo padrão expansível de Saídas Totais.
html_fluxo += "<tbody class='obra-group recurso-group'><tr>"
html_fluxo += (
    "<td class='row-label'><label class='drilldown-label' style='padding-left:0;'>"
    "<input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> "
    "<b>(+) Recursos Alocados</b></label></td>"
)
for val in recursos_mes_list:
    html_fluxo += f"<td style='color:#059669;font-weight:800'>{formatar_moeda_curta(val) if val else '-'}</td>"
html_fluxo += "</tr>"

# Detalhamento de cada captação, preservando produto, contrato, data e valor.
for _, rr in df_recursos.iterrows():
    ano_rec, mes_rec = rr.get('_Ano'), rr.get('_Mes')
    if pd.isna(ano_rec) or pd.isna(mes_rec):
        continue
    comp_rec = f"{meses_nomes[int(mes_rec)]}-{int(ano_rec)}"
    if comp_rec not in periodos_labels:
        continue
    produto_col = next((c for c in df_recursos.columns if 'produto' in str(c).lower()), None)
    contrato_col = next((c for c in df_recursos.columns if 'contrato' in str(c).lower()), None)
    data_rec = rr.get('_Data_Alocacao')
    data_txt = data_rec.strftime('%d/%m/%Y') if pd.notna(data_rec) else '-'
    produto = str(rr.get(produto_col, '-')) if produto_col else '-'
    contrato = str(rr.get(contrato_col, '-')) if contrato_col else '-'
    valor_rec = float(rr.get('_Valor_Alocado', 0) or 0)
    html_fluxo += "<tr class='sub-row recurso-sub-row'>"
    html_fluxo += f"<td class='row-label detail-black' style='padding-left:28px;font-size:10px;font-weight:normal'>↳ {produto} · Contrato {contrato} · {data_txt}</td>"
    for comp in periodos_labels:
        valor_cel = valor_rec if comp == comp_rec else 0
        html_fluxo += f"<td class='detail-black' style='font-size:10px'>{formatar_moeda_curta(valor_cel) if valor_cel else '-'}</td>"
    html_fluxo += "</tr>"
html_fluxo += "</tbody>"

# Saídas: linha principal vermelha; apenas os detalhes expandidos ficam em preto.
html_fluxo += "<tbody class='obra-group'><tr>"
html_fluxo += (
    "<td class='row-label'><label class='drilldown-label' style='padding-left:0;'>"
    "<input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> "
    "<b>(-) Saídas Totais</b></label></td>"
)
for val in saidas_tot_list:
    html_fluxo += f"<td style='color:#dc2626;font-weight:800'>{formatar_moeda_curta(val)}</td>"
html_fluxo += "</tr>"

for obra_name in obras_fluxo:
    html_fluxo += (
        f"<tr class='sub-row'><td class='row-label detail-black' style='padding-left:28px;font-size:10px;"
        f"font-weight:normal'>↳ {obra_name}</td>"
    )
    for comp, (ano_p, mes_p) in zip(periodos_labels, periodos):
        v_obra = real_por_obra_mes.get((comp, obra_name), 0.0) if max_comp_real and (ano_p, mes_p) <= max_comp_real else orc_por_obra_mes.get((comp, obra_name), 0.0)
        html_fluxo += f"<td class='detail-black' style='font-size:10px'>{formatar_moeda_curta(v_obra) if v_obra > 0 else '-'}</td>"
    html_fluxo += "</tr>"
html_fluxo += "</tbody>"

html_fluxo += "<tr><td class='row-label' style='font-weight:800'>(=) Saldo Final</td>"
for idx, val in enumerate(s_fim_list):
    css_class = "val-real" if max_comp_real and periodos[idx] <= max_comp_real else "val-orc"
    color = VERMELHO if val < 0 else (VERDE if css_class == "val-real" else "#2563eb")
    html_fluxo += f"<td class='{css_class}' style='color:{color};font-weight:800'><b>{formatar_moeda_curta(val)}</b></td>"
html_fluxo += "</tr></tbody></table></div>"
st.markdown(html_fluxo, unsafe_allow_html=True)

# ==============================================================================
# DETALHAMENTO ORÇAMENTO (TOTAL ORÇADO em preto)
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento do orçamento por obra</div>", unsafe_allow_html=True)

if not df_orc_filtrado.empty:
    df_orc_tab = df_orc_filtrado[df_orc_filtrado['Mes'] > 0].copy()
    if not df_orc_tab.empty:
        df_orc_tab['Competencia'] = [f"{meses_nomes.get(int(m), '?')}-{int(a)}" for a,m in zip(df_orc_tab['Ano'], df_orc_tab['Mes'])]
        pivot_orc = pd.pivot_table(df_orc_tab, index='Obra', columns='Competencia', values='Valor_Orcado', aggfunc='sum', fill_value=0.0)
        for comp in periodos_labels:
            if comp not in pivot_orc.columns: pivot_orc[comp] = 0.0
        pivot_orc = pivot_orc[periodos_labels]
        pivot_orc['Total_Geral'] = pivot_orc.sum(axis=1)
        pivot_orc = pivot_orc.sort_values(by='Total_Geral', ascending=False)

        html_orc_det = "<div class='fases-table-container'><table class='fases-table'><thead><tr><th>OBRA / FASE DA OBRA</th>"
        html_orc_det += "<th>TOTAL ORÇADO</th>"
        for comp in periodos_labels:
            html_orc_det += f"<th>{comp.upper()}</th>"
        html_orc_det += "</tr></thead>"

        totais_col_orc = {comp: 0.0 for comp in periodos_labels}
        total_geral_orc = 0.0

        for obra_name, row in pivot_orc.iterrows():
            tot_obra = row['Total_Geral']
            total_geral_orc += tot_obra

            fases_lista = []
            if not df_fases.empty and 'Obra' in df_fases.columns and 'Fase_Tarefa' in df_fases.columns:
                sub_fases = df_fases[df_fases['Obra'] == obra_name]
                if not sub_fases.empty:
                    fases_lista = [f for f in sub_fases['Fase_Tarefa'].dropna().unique().tolist() if f and f != 'NAN']
            if not fases_lista:
                sub_df_orc = df_orc_tab[df_orc_tab['Obra'] == obra_name]
                if 'Item' in sub_df_orc.columns:
                    fases_lista = sub_df_orc['Item'].dropna().unique().tolist()

            html_orc_det += "<tbody class='obra-group'><tr>"
            html_orc_det += (
                f"<td><label class='drilldown-label'><input type='checkbox' class='toggle-checkbox'>"
                f"<span class='indicator'>▶</span> <b>{obra_name}</b></label></td>"
            )
            # TOTAL ORÇADO em preto
            html_orc_det += f"<td style='font-weight:800;color:{TXT}'>{formatar_moeda(tot_obra)}</td>"
            for comp in periodos_labels:
                val_m = row.get(comp, 0.0)
                totais_col_orc[comp] += val_m
                html_orc_det += f"<td style='font-weight:700'>{formatar_moeda(val_m) if val_m > 0 else '-'}</td>"
            html_orc_det += "</tr>"

            if fases_lista:
                num_fases = len(fases_lista)
                for fase_name in fases_lista:
                    html_orc_det += "<tr class='sub-row'>"
                    html_orc_det += (
                        f"<td title='↳ {fase_name}' style='padding-left:30px;font-size:11px;color:#64748b;"
                        f"border-right:2px solid #e2e8f0;overflow:hidden;text-overflow:ellipsis;"
                        f"white-space:nowrap'>↳ {fase_name}</td>"
                    )
                    val_sub_total = tot_obra / num_fases if num_fases > 0 else 0
                    html_orc_det += f"<td style='font-size:11px;font-weight:600;color:#64748b'>{formatar_moeda(val_sub_total)}</td>"
                    for comp in periodos_labels:
                        val_m_sub = row.get(comp, 0.0) / num_fases if num_fases > 0 else 0
                        html_orc_det += f"<td style='font-size:11px;color:#64748b'>{formatar_moeda(val_m_sub) if val_m_sub > 0 else '-'}</td>"
                    html_orc_det += "</tr>"
            html_orc_det += "</tbody>"

        html_orc_det += "<tr class='total-geral-row'><td>TOTAL GERAL ORÇADO</td>"
        html_orc_det += f"<td style='font-weight:900;color:{TXT}'>{formatar_moeda(total_geral_orc)}</td>"
        for comp in periodos_labels:
            t_col = totais_col_orc[comp]
            html_orc_det += f"<td style='font-weight:900'>{formatar_moeda(t_col) if t_col > 0 else '-'}</td>"
        html_orc_det += "</tr></table></div>"
        st.markdown(html_orc_det, unsafe_allow_html=True)

# ==============================================================================
# DETALHAMENTO PAGAMENTOS
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento de pagamentos realizados</div>", unsafe_allow_html=True)

if not df_real_filtrado.empty:
    df_real_tab = df_real_filtrado[df_real_filtrado['Mes'] > 0].copy()
    df_real_tab['Competencia'] = [f"{meses_nomes.get(int(m), '?')}-{int(a)}" for a,m in zip(df_real_tab['Ano'], df_real_tab['Mes'])]
    df_orc_tab = df_orc_filtrado[df_orc_filtrado['Mes'] > 0].copy() if not df_orc_filtrado.empty else pd.DataFrame()
    if not df_orc_tab.empty:
        df_orc_tab['Competencia'] = [f"{meses_nomes.get(int(m), '?')}-{int(a)}" for a,m in zip(df_orc_tab['Ano'], df_orc_tab['Mes'])]

    if not df_real_tab.empty:
        orc_obra_mes, orc_obra_tot = {}, {}
        orc_mes_tot = {comp: 0.0 for comp in periodos_labels}
        if not df_orc_tab.empty:
            df_orc_grp = df_orc_tab.groupby(['Obra', 'Competencia'])['Valor_Orcado'].sum().reset_index()
            for _, r in df_orc_grp.iterrows():
                orc_obra_mes[(r['Obra'], r['Competencia'])] = r['Valor_Orcado']
                orc_obra_tot[r['Obra']] = orc_obra_tot.get(r['Obra'], 0.0) + r['Valor_Orcado']
                orc_mes_tot[r['Competencia']] = orc_mes_tot.get(r['Competencia'], 0.0) + r['Valor_Orcado']
        total_orcado_geral = sum(orc_mes_tot.values())

        pivot_real = pd.pivot_table(df_real_tab, index='Obra', columns='Competencia', values='Valor_Realizado', aggfunc='sum', fill_value=0.0)
        for comp in periodos_labels:
            if comp not in pivot_real.columns: pivot_real[comp] = 0.0
        pivot_real = pivot_real[periodos_labels]
        pivot_real['Total_Geral'] = pivot_real.sum(axis=1)
        pivot_real = pivot_real.sort_values(by='Total_Geral', ascending=False)

        html_real_det = "<div class='fases-table-container'><table class='fases-table'><thead><tr><th>OBRA / CATEGORIA</th>"
        html_real_det += "<th>TOTAL</th>"
        for comp in periodos_labels:
            html_real_det += f"<th>{comp.upper()}</th>"
        html_real_det += "</tr></thead>"

        totais_col_real = {comp: 0.0 for comp in periodos_labels}
        totais_geral_real = 0.0

        for obra_name, row in pivot_real.iterrows():
            sub_df = df_real_tab[df_real_tab['Obra'] == obra_name]
            pivot_sub = pd.pivot_table(sub_df, index='Fornecedor', columns='Competencia', values='Valor_Realizado', aggfunc='sum', fill_value=0.0)
            for comp in periodos_labels:
                if comp not in pivot_sub.columns: pivot_sub[comp] = 0.0
            pivot_sub = pivot_sub[periodos_labels]
            pivot_sub['Total_Geral'] = pivot_sub.sum(axis=1)
            pivot_sub = pivot_sub.sort_values(by='Total_Geral', ascending=False)

            tot_obra_real = row['Total_Geral']
            tot_obra_orc = orc_obra_tot.get(obra_name, 0.0)
            totais_geral_real += tot_obra_real
            cor_tot_obra = VERDE if (tot_obra_orc > 0 and tot_obra_real <= tot_obra_orc) else (VERMELHO if tot_obra_orc > 0 else TXT)
            str_orc_tot_obra = f"Orç: {formatar_moeda_curta(tot_obra_orc)}" if tot_obra_orc > 0 else "Orç: -"

            html_real_det += "<tbody class='obra-group'><tr>"
            html_real_det += (
                f"<td><label class='drilldown-label'><input type='checkbox' class='toggle-checkbox'>"
                f"<span class='indicator'>▶</span> <b>{obra_name}</b></label></td>"
            )
            html_real_det += (
                f"<td><span style='font-weight:800;color:{cor_tot_obra}'>{formatar_moeda(tot_obra_real)}</span>"
                f"<span class='orcado-indicator'>{str_orc_tot_obra}</span></td>"
            )
            for comp in periodos_labels:
                val_m_real = row.get(comp, 0.0)
                totais_col_real[comp] += val_m_real
                val_m_orc = orc_obra_mes.get((obra_name, comp), 0.0)
                if val_m_real > 0 and val_m_orc > 0:
                    cor_m = VERDE if val_m_real <= val_m_orc else VERMELHO
                else:
                    cor_m = TXT
                val_str = formatar_moeda(val_m_real) if val_m_real > 0 else "-"
                str_orc_m = f"Orç: {formatar_moeda_curta(val_m_orc)}" if val_m_orc > 0 else "Orç: -"
                html_real_det += (
                    f"<td><span style='font-weight:800;color:{cor_m}'>{val_str}</span>"
                    f"<span class='orcado-indicator'>{str_orc_m}</span></td>"
                )
            html_real_det += "</tr>"

            for forn_name, sub_row in pivot_sub.iterrows():
                tot_sub_geral = sub_row['Total_Geral']
                html_real_det += "<tr class='sub-row'>"
                html_real_det += (
                    f"<td title='↳ {forn_name}' style='padding-left:30px;font-size:11px;color:#64748b;"
                    f"border-right:2px solid #e2e8f0;overflow:hidden;text-overflow:ellipsis;"
                    f"white-space:nowrap'>↳ {forn_name}</td>"
                )
                html_real_det += f"<td style='font-size:11px;font-weight:700'>{formatar_moeda(tot_sub_geral)}</td>"
                for comp in periodos_labels:
                    v_sub = sub_row.get(comp, 0.0)
                    html_real_det += f"<td style='font-size:11px;color:#64748b'>{formatar_moeda(v_sub) if v_sub > 0 else '-'}</td>"
                html_real_det += "</tr>"
            html_real_det += "</tbody>"

        str_orc_tot_geral = f"Orç: {formatar_moeda_curta(total_orcado_geral)}" if total_orcado_geral > 0 else "Orç: -"
        html_real_det += "<tr class='total-geral-row'><td>TOTAL GERAL</td>"
        html_real_det += (
            f"<td><span style='font-weight:900'>{formatar_moeda(totais_geral_real)}</span>"
            f"<span class='orcado-indicator'>{str_orc_tot_geral}</span></td>"
        )
        for comp in periodos_labels:
            t_col_real = totais_col_real[comp]
            t_col_orc = orc_mes_tot.get(comp, 0.0)
            str_orc_col = f"Orç: {formatar_moeda_curta(t_col_orc)}" if t_col_orc > 0 else "Orç: -"
            html_real_det += (
                f"<td><span style='font-weight:900'>{formatar_moeda(t_col_real) if t_col_real > 0 else '-'}</span>"
                f"<span class='orcado-indicator'>{str_orc_col}</span></td>"
            )
        html_real_det += "</tr></table></div>"
        st.markdown(html_real_det, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(
        f"<div class='side-card'><small>Filtro atual</small><b>{txt_mes} · {txt_obra}</b></div>"
        f"<div class='side-card'><small>Última atualização</small><b>{datetime.now():%d/%m/%Y %H:%M}</b></div>",
        unsafe_allow_html=True,
    )
