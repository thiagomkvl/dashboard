import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import textwrap
import io
from datetime import datetime

# ==============================================================================
# 0. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Acompanhamento de Obras",
    layout="wide",
    page_icon="🏗️",
    initial_sidebar_state="expanded",
)

try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# ==============================================================================
# PALETA (mesma identidade do painel de faturamento)
# ==============================================================================
AZUL, VERDE, AMBAR, VERMELHO = "#3b82f6", "#10b981", "#f59e0b", "#ef4444"
ROXO, LARANJA, CIANO, ROSA = "#8b5cf6", "#f97316", "#22d3ee", "#fb7185"
TXT, MUTED, BORDA = "#e6ecf5", "#8fa3c4", "#1c2a47"
BG_APP, BG_CARD, BG_SIDE = "#0a1020", "#0f1a2e", "#0b1326"

ESPACO_ENTRE_BLOCOS = "0.5rem"
AJUSTE_APOS_KPIS = "-0.5rem"

# ==============================================================================
# 1. CUSTOM CSS (IDENTIDADE VISUAL ESCURA)
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #0a1020 !important; color: #e6ecf5; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: __GAP__; }
    [data-testid="stMarkdownContainer"] { color: #e6ecf5; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #0b1326 !important; border-right: 1px solid #1a2744; }
    [data-testid="stWidgetLabel"] p { color: #8fa3c4 !important; font-size: 12px; font-weight: 600; }
    .side-sec { font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #8fa3c4; text-transform: uppercase; margin: 6px 0 -2px; }
    .side-card { background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 10px; padding: 10px 12px; margin-top: 8px; }
    .side-card small { display: block; color: #8fa3c4; font-size: 11px; }
    .side-card b { color: #e6ecf5; font-size: 13px; }

    /* Widgets escuros */
    [data-baseweb="select"] > div { background: #101b32 !important; border-color: #1e2d4d !important; color: #e6ecf5 !important; }
    [data-baseweb="select"] span, [data-baseweb="select"] input { color: #e6ecf5 !important; }
    [data-baseweb="select"] svg { fill: #8fa3c4; }
    [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #101b32 !important; }
    li[role="option"] { color: #e6ecf5 !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background: #1a2a4a !important; }
    span[data-baseweb="tag"] { background: #f97316 !important; color: #fff !important; }
    .stButton > button { background: linear-gradient(135deg, #f97316, #ea580c); color: #fff; border: none; border-radius: 10px; font-weight: 700; padding: 0.55rem 1rem; }
    .stButton > button:hover { filter: brightness(1.1); color: #fff; border: none; }
    [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-weight: 700 !important; height: 36px; font-size: 12px;
    }

    /* Cabeçalho */
    .top { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px solid #1a2744; }
    .top h1 { margin: 0; padding: 0; font-size: 22px; font-weight: 800; letter-spacing: 0.3px; color: #fff; }
    .top p { margin: 2px 0 0; font-size: 13px; color: #8fa3c4; }
    .pills { display: flex; gap: 10px; flex-wrap: wrap; }
    .pill { background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 10px; padding: 6px 14px; min-width: 120px; }
    .pill small { display: block; font-size: 10px; color: #8fa3c4; }
    .pill b { font-size: 13px; color: #fff; white-space: nowrap; }

    /* KPIs */
    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: __KPI_GAP__; }
    .kpi {
        padding: 12px; border-radius: 12px; height: 110px; container-type: inline-size; overflow: hidden;
        background: linear-gradient(135deg, rgba(59,130,246,0.10), #0f1a2e 70%);
        border: 1px solid rgba(59,130,246,0.22);
    }
    .kpi.green { background: linear-gradient(135deg, rgba(16,185,129,0.10), #0f1a2e 70%); border-color: rgba(16,185,129,0.22); }
    .kpi.amber { background: linear-gradient(135deg, rgba(245,158,11,0.10), #0f1a2e 70%); border-color: rgba(245,158,11,0.22); }
    .kpi.purple { background: linear-gradient(135deg, rgba(139,92,246,0.10), #0f1a2e 70%); border-color: rgba(139,92,246,0.22); }
    .kpi-t { font-size: 10px; font-weight: 800; letter-spacing: 0.4px; text-transform: uppercase; line-height: 1.2; min-height: 22px; color: #9db2d3; }
    .kpi-v { font-size: clamp(11px, 11cqw, 18px); font-weight: 800; color: #fff; letter-spacing: -0.3px; white-space: nowrap; margin: 6px 0 3px; font-variant-numeric: tabular-nums; }
    .kpi-sub { font-size: 11px; color: #8fa3c4; font-weight: 600; }
    .kpi-sub.up { color: #34d399; }
    .kpi-sub.down { color: #f87171; }
    .pb { width: 100%; background: #16213a; height: 6px; border-radius: 3px; margin-top: 6px; overflow: hidden; }
    .pb span { display: block; height: 100%; border-radius: 3px; }

    /* Cards / seções */
    [data-testid="stVerticalBlockBorderWrapper"] { background: #0f1a2e; border: 1px solid #1c2a47 !important; border-radius: 12px; }
    .card-title {
        display: flex; align-items: center; justify-content: space-between;
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #fff; margin: 2px 0 8px;
    }
    .card-title span { font-size: 10px; font-weight: 600; letter-spacing: 0.2px; text-transform: none; color: #8fa3c4; }
    .section-title {
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #fff; margin: 18px 0 10px; padding-left: 10px; border-left: 3px solid #3b82f6;
    }

    /* Tabelas unificadas */
    .unified-summary-box {
        background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 12px;
        margin-top: 8px; margin-bottom: 16px; overflow: hidden;
    }
    .unified-table { width: 100%; border-collapse: collapse; font-size: 11px; text-align: center; color: #dbe6f7; }
    .unified-table th {
        background: #0f1a2e; color: #8fa3c4; font-weight: 700; text-transform: uppercase;
        padding: 10px 4px; border-bottom: 1px solid #1c2a47; border-right: 1px solid #16213a;
    }
    .unified-table th:last-child { border-right: none; }
    .unified-table td {
        padding: 10px 4px; border-bottom: 1px solid #16213a; border-right: 1px solid #16213a;
        background: #0f1a2e; font-variant-numeric: tabular-nums;
    }
    .unified-table td:last-child { border-right: none; }
    .row-label {
        text-align: left; padding-left: 14px !important; font-weight: 700; color: #8fa3c4;
        background: #0d1730 !important; width: 170px; border-right: 2px solid #1c2a47 !important;
    }
    .val-real { font-weight: 800; color: #34d399; }
    .val-orc { font-weight: 800; color: #60a5fa; }

    /* Tabelas com drilldown */
    .fases-table-container {
        max-height: 500px; overflow: auto; border: 1px solid #1c2a47; border-radius: 12px;
        background: #0f1a2e;
    }
    .fases-table {
        width: 100%; border-collapse: collapse; font-size: 11px; white-space: nowrap;
        background: #0f1a2e; table-layout: fixed; color: #dbe6f7;
    }
    .fases-table thead { position: sticky; top: 0; z-index: 15; }
    .fases-table th {
        background: #0f1a2e; color: #8fa3c4; font-weight: 700; text-transform: uppercase;
        padding: 12px 10px; border-bottom: 1px solid #1c2a47; text-align: left;
        position: sticky; top: 0; z-index: 15;
    }
    .fases-table td { padding: 10px; border-bottom: 1px solid #16213a; color: #dbe6f7; background: #0f1a2e; }
    .fases-table th:nth-child(1), .fases-table td:nth-child(1) {
        width: 300px; min-width: 300px; max-width: 300px; position: sticky; left: 0; z-index: 10;
        background: #0f1a2e; border-right: 2px solid #1c2a47; overflow: hidden; text-overflow: ellipsis;
    }
    .fases-table th:nth-child(1) { z-index: 20; }
    .fases-table th:nth-child(2), .fases-table td:nth-child(2) { width: 140px; min-width: 140px; max-width: 140px; }
    .fases-table th:nth-child(n+3), .fases-table td:nth-child(n+3) { width: 110px; min-width: 110px; max-width: 110px; }
    .fases-table tr:hover td { background: #13203a; }
    .total-geral-row td {
        font-weight: 900; background: #0d1730 !important; border-top: 1px solid #2a3a5c; color: #fff;
    }

    /* Drilldown */
    .drilldown-label { cursor: pointer; display: flex; align-items: center; margin: 0; width: 100%; height: 100%; color: #e6ecf5; }
    .toggle-checkbox { display: none; }
    .indicator { margin-right: 8px; font-size: 11px; transition: transform 0.2s; display: inline-block; color: #3b82f6; }
    .obra-group .sub-row { display: none; }
    .obra-group:has(.toggle-checkbox:checked) .sub-row { display: table-row; }
    .obra-group:has(.toggle-checkbox:checked) .indicator { transform: rotate(90deg); }
    .orcado-indicator { display: block; font-size: 9px; color: #8fa3c4; margin-top: 3px; font-weight: 600; }

    .fases-table-container::-webkit-scrollbar,
    .unified-summary-box::-webkit-scrollbar { height: 6px; width: 6px; }
    .fases-table-container::-webkit-scrollbar-thumb,
    .unified-summary-box::-webkit-scrollbar-thumb { background: #2a3a5c; border-radius: 6px; }

    hr { border: none !important; border-top: 1px solid #1a2744 !important; margin: 20px 0 !important; }
</style>
"""
st.markdown(
    textwrap.dedent(css).replace("__GAP__", ESPACO_ENTRE_BLOCOS).replace("__KPI_GAP__", AJUSTE_APOS_KPIS),
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
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
    try:
        s = str(m).strip()
        if '.' in s:
            return int(float(s.split('.')[-1]))
        return int(float(s))
    except Exception:
        return 0


def layout_fig(fig, h=280, legenda=True):
    fig.update_layout(
        height=h,
        margin=dict(l=0, r=0, t=30 if legenda else 8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=11, color=MUTED),
        separators=",.",
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11, color="#ffffff")),
        hoverlabel=dict(bgcolor="#101b32", font_color=TXT, bordercolor=BORDA),
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDA, tickfont=dict(size=10, color=MUTED))
    fig.update_yaxes(
        gridcolor="rgba(148,163,184,0.12)", zeroline=False,
        tickprefix="R$ ", tickformat=".2s", tickfont=dict(size=10, color=MUTED),
    )
    return fig


# ==============================================================================
# 3. CARGA DOS DADOS E TRATAMENTO
# ==============================================================================
@st.cache_data(ttl=60, show_spinner="Carregando dados…")
def carregar_dados_obras_detalhado():
    conn = conectar_sheets()
    if not conn:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        # --- ORÇADO ---
        df_orc = conn.read(worksheet="Orçamento_Obra", ttl=0)
        df_orc.columns = [str(c).strip() for c in df_orc.columns]

        map_meses = {
            'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'MARCO': 3,
            'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6, 'JULHO': 7,
            'AGOSTO': 8, 'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12
        }
        meses_existentes = [c for c in df_orc.columns if c.upper() in map_meses]

        col_resumo = next((c for c in df_orc.columns if 'RESUMO' in c.upper() or 'OBRA' in c.upper()), df_orc.columns[0])
        col_item = next((c for c in df_orc.columns if c.upper() in ['CATEGORIA', 'FASE', 'ITEM', 'DESCRIÇÃO', 'DESCRICAO', 'ETAPA', 'SERVIÇO', 'SERVICO', 'DETALHE', 'CONTA']), None)

        df_orc = df_orc[df_orc[col_resumo].astype(str).str.upper().str.strip() != 'TOTAL'].copy()
        df_orc['Obra'] = df_orc[col_resumo].astype(str).str.upper().str.strip()

        if col_item and col_item != col_resumo:
            df_orc['Item'] = df_orc[col_item].fillna('GERAL').astype(str).str.strip().str.upper()
            id_vars = ['Obra', 'Item']
        else:
            outras_cols = [c for c in df_orc.columns if c.upper() not in map_meses and c != col_resumo and c.upper() != 'OBRA']
            if outras_cols:
                df_orc['Item'] = df_orc[outras_cols[0]].fillna('GERAL').astype(str).str.strip().str.upper()
                id_vars = ['Obra', 'Item']
            else:
                df_orc['Item'] = df_orc['Obra']
                id_vars = ['Obra', 'Item']

        df_orc_melt = df_orc.melt(id_vars=id_vars, value_vars=meses_existentes, var_name='Mes_Nome', value_name='Valor_Orcado')
        df_orc_melt['Mes'] = df_orc_melt['Mes_Nome'].str.upper().map(map_meses)
        df_orc_melt['Valor_Orcado'] = df_orc_melt['Valor_Orcado'].apply(limpa_valor)

        # --- FASES DA OBRA ---
        df_fases = pd.DataFrame()
        try:
            df_fases_raw = conn.read(worksheet="Fases_Obra", ttl=0)
            valid_cols = [c for c in df_fases_raw.columns if str(c).strip() and not str(c).strip().lower().startswith('unnamed')]
            df_fases = df_fases_raw[valid_cols].copy()
            df_fases = df_fases.replace(r'^\s*$', pd.NA, regex=True).dropna(axis=1, how='all')

            if not df_fases.empty and len(df_fases.columns) >= 2:
                col_obra_fases = df_fases.columns[0]
                col_tarefa_fases = df_fases.columns[1]
                df_fases['Obra'] = df_fases[col_obra_fases].fillna('').astype(str).str.strip().str.upper()
                df_fases['Fase_Tarefa'] = df_fases[col_tarefa_fases].fillna('').astype(str).str.strip().str.upper()
            elif not df_fases.empty and len(df_fases.columns) == 1:
                df_fases['Obra'] = df_fases[df_fases.columns[0]].fillna('').astype(str).str.strip().str.upper()
                df_fases['Fase_Tarefa'] = "GERAL"
        except Exception:
            df_fases = pd.DataFrame()

        # --- RECURSOS DA OBRA ---
        df_recursos = pd.DataFrame()
        try:
            df_recursos_raw = conn.read(worksheet="Recursos_Obra", ttl=0)
            valid_cols_rec = [c for c in df_recursos_raw.columns if str(c).strip() and not str(c).strip().lower().startswith('unnamed')]
            df_recursos = df_recursos_raw[valid_cols_rec].copy()
        except Exception:
            df_recursos = pd.DataFrame()

        # --- REALIZADO ---
        df_real = conn.read(worksheet="Realizado_Obra", ttl=0)
        df_real['Obra'] = df_real['Categoria'].astype(str).str.upper().str.strip()
        df_real['Mes'] = df_real['MÊS'].apply(extract_month)
        df_real['Valor_Realizado'] = df_real['Valor'].apply(limpa_valor)
        col_forn = next((c for c in df_real.columns if 'forn' in c.lower()), 'Fornecedor')
        col_nf = next((c for c in df_real.columns if 'nf' in c.lower()), 'NF')
        col_data = next((c for c in df_real.columns if 'data' in c.lower()), 'DATA PGTO')
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

# ==============================================================================
# 4. BARRA LATERAL E FILTROS
# ==============================================================================
df_orc_filtrado = df_orcado.copy()
df_real_filtrado = df_realizado.copy()
df_fases_filtrado = df_fases.copy()

with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)
    mes_selecionado = st.selectbox(
        "Mês de Análise (Acumulado)",
        options=["Todos"] + list(range(1, 13)),
        format_func=lambda x: f"Até Mês {x:02d}" if isinstance(x, int) else x,
    )
    obra_selecionada = st.selectbox("Empreendimento / Obra", ["Todas"] + lista_obras)

    if st.button("↻ Limpar filtros", use_container_width=True):
        st.rerun()

    if mes_selecionado != "Todos":
        df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Mes'] <= mes_selecionado]
        df_real_filtrado = df_real_filtrado[df_real_filtrado['Mes'] <= mes_selecionado]
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
    relatorio_bytes = output_excel.getvalue()

    st.download_button(
        label="📥 Baixar Relatório Completo",
        data=relatorio_bytes,
        file_name="relatorio_detalhado_obras.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ==============================================================================
# 5. CÁLCULOS E ANÁLISE (MoM) E BARRA DE PROGRESSO
# ==============================================================================
total_orcado = df_orc_filtrado['Valor_Orcado'].sum()
total_realizado = df_real_filtrado['Valor_Realizado'].sum()
saldo_orcamento = total_orcado - total_realizado
consumo_geral_perc = (total_realizado / total_orcado * 100) if total_orcado > 0 else 0

caixa_inicial_base = 10_000_000.0
if not df_recursos.empty:
    col_rec = next((c for c in df_recursos.columns if 'recurso' in c.lower() or 'alocado' in c.lower()), None)
    if col_rec:
        val_rec = df_recursos[col_rec].apply(limpa_valor).sum()
        if val_rec > 0:
            caixa_inicial_base = val_rec

caixa_disponivel = caixa_inicial_base - total_realizado

mes_atual = int(mes_selecionado) if mes_selecionado != "Todos" else (int(df_realizado['Mes'].max()) if not df_realizado.empty else 0)
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
    mom_str = f"↗ +{mom_pct:.1f}% vs Mês {mes_anterior:02d}"
    mom_cls = "down"
elif mom_pct < 0:
    mom_str = f"↘ {mom_pct:.1f}% vs Mês {mes_anterior:02d}"
    mom_cls = "up"
else:
    mom_str = f"→ 0.0% vs Mês {mes_anterior:02d}"
    mom_cls = ""

pb_width = min(consumo_geral_perc, 100)
pb_color = VERMELHO if consumo_geral_perc > 100 else VERDE
saldo_color = VERMELHO if saldo_orcamento < 0 else "#fff"
caixa_disp_color = VERMELHO if caixa_disponivel < 0 else VERDE

txt_mes = f"Até Mês {mes_selecionado:02d}" if mes_selecionado != "Todos" else "Todos os meses"
txt_obra = obra_selecionada if obra_selecionada != "Todas" else "Todas"

# ==============================================================================
# 6. CABEÇALHO E KPIs
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

kpi_html = f"""
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
        <div class='kpi-sub {mom_cls}'>{mom_str}</div>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# ==============================================================================
# EVOLUÇÃO MENSAL
# ==============================================================================
df_orc_m_base = df_orcado.copy()
df_real_m_base = df_realizado[df_realizado['Mes'] > 0].copy()
if obra_selecionada != "Todas":
    df_orc_m_base = df_orc_m_base[df_orc_m_base['Obra'] == obra_selecionada]
    df_real_m_base = df_real_m_base[df_real_m_base['Obra'] == obra_selecionada]

df_orc_mensal = df_orc_m_base.groupby('Mes')['Valor_Orcado'].sum().reset_index()
df_real_mensal = df_real_m_base.groupby('Mes')['Valor_Realizado'].sum().reset_index()

df_linha = pd.DataFrame({'Mes': range(1, 13)})
df_linha = pd.merge(df_linha, df_orc_mensal, on='Mes', how='left').fillna({'Valor_Orcado': 0.0})
df_linha = pd.merge(df_linha, df_real_mensal, on='Mes', how='left')
df_linha.loc[df_linha['Mes'] > (df_real_m_base['Mes'].max() if not df_real_m_base.empty else 0), 'Valor_Realizado'] = None

meses_nomes = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
               7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
df_linha['Mes_Nome'] = df_linha['Mes'].map(meses_nomes)

st.markdown("<div class='section-title'>Evolução mensal · Orçado vs Realizado</div>", unsafe_allow_html=True)

fig_linha = go.Figure()
fig_linha.add_trace(go.Scatter(
    x=df_linha['Mes_Nome'], y=df_linha['Valor_Orcado'],
    mode='lines+markers', name='Orçado',
    line=dict(color=AZUL, width=2.5), marker=dict(size=7),
    fill='tozeroy', fillcolor='rgba(59,130,246,0.14)',
    hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Orçado</extra>",
))
fig_linha.add_trace(go.Scatter(
    x=df_linha['Mes_Nome'], y=df_linha['Valor_Realizado'],
    mode='lines+markers', name='Realizado',
    line=dict(color=VERDE, width=2.5), marker=dict(size=7),
    fill='tozeroy', fillcolor='rgba(16,185,129,0.18)',
    connectgaps=False,
    hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Realizado</extra>",
))
st.plotly_chart(layout_fig(fig_linha, 260), use_container_width=True, config={'displayModeBar': False})

html_unified = "<div class='unified-summary-box'><table class='unified-table'><thead><tr><th class='row-label'>Mês</th>"
for _, r in df_linha.iterrows():
    html_unified += f"<th>{r['Mes_Nome']}</th>"
html_unified += "</tr></thead><tbody><tr><td class='row-label'>Realizado</td>"
for _, r in df_linha.iterrows():
    val_disp = formatar_moeda_curta(r['Valor_Realizado']) if pd.notna(r['Valor_Realizado']) else '-'
    html_unified += f"<td class='val-real'>{val_disp}</td>"
html_unified += "</tr><tr><td class='row-label'>Orçado</td>"
for _, r in df_linha.iterrows():
    html_unified += f"<td class='val-orc'>{formatar_moeda_curta(r['Valor_Orcado'])}</td>"
html_unified += "</tr></tbody></table></div>"
st.markdown(html_unified, unsafe_allow_html=True)

# ==============================================================================
# GRÁFICOS ANALÍTICOS
# ==============================================================================
col_g1, col_g2 = st.columns(2, gap="small")

with col_g1:
    st.markdown("<div class='section-title' style='margin-top:4px'>Distribuição de custo por obra</div>", unsafe_allow_html=True)
    df_donut = df_real_filtrado.groupby('Obra')['Valor_Realizado'].sum().reset_index()
    if not df_donut.empty:
        cores = [AZUL, VERDE, AMBAR, ROXO, LARANJA, CIANO, ROSA, VERMELHO]
        fig_donut = go.Figure(go.Pie(
            labels=df_donut['Obra'], values=df_donut['Valor_Realizado'],
            hole=0.62, textinfo="none",
            marker=dict(colors=cores[:len(df_donut)], line=dict(color="#0f1a2e", width=2)),
            hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        ))
        total_d = df_donut['Valor_Realizado'].sum()
        fig_donut.update_layout(annotations=[dict(
            text=f"<b>{formatar_moeda_curta(total_d)}</b><br><span style='font-size:10px;color:#8fa3c4'>Total</span>",
            showarrow=False, font=dict(size=13, color="#fff"),
        )])
        st.plotly_chart(layout_fig(fig_donut, 280, True), use_container_width=True, config={'displayModeBar': False})

with col_g2:
    st.markdown("<div class='section-title' style='margin-top:4px'>Consumo de caixa mensal por obra</div>", unsafe_allow_html=True)
    df_stack = df_real_filtrado.groupby(['Mes', 'Obra'])['Valor_Realizado'].sum().reset_index()
    if not df_stack.empty:
        df_stack['Mes_Nome'] = df_stack['Mes'].map(meses_nomes)
        df_stack = df_stack.sort_values('Mes')
        df_stack_tot = df_stack.groupby(['Mes', 'Mes_Nome'])['Valor_Realizado'].sum().reset_index()

        fig_stack = px.bar(
            df_stack, x='Mes_Nome', y='Valor_Realizado', color='Obra',
            color_discrete_sequence=[AZUL, VERDE, AMBAR, ROXO, LARANJA, CIANO, ROSA, VERMELHO],
        )
        fig_stack.add_trace(go.Scatter(
            x=df_stack_tot['Mes_Nome'], y=df_stack_tot['Valor_Realizado'],
            text=df_stack_tot['Valor_Realizado'].apply(formatar_moeda_curta),
            mode='text', textposition='top center', showlegend=False,
            textfont=dict(size=10, color='#e6ecf5', family='Inter'),
        ))
        fig_stack.update_layout(bargap=0.3, xaxis_title=None, yaxis_title=None, showlegend=False)
        st.plotly_chart(layout_fig(fig_stack, 280, False), use_container_width=True, config={'displayModeBar': False})

# ==============================================================================
# 6.1 FLUXO DE CAIXA DA OBRA
# ==============================================================================
st.markdown("<div class='section-title'>Fluxo de caixa · Realizado vs Projetado</div>", unsafe_allow_html=True)

saidas_real_dict = df_real_m_base.groupby('Mes')['Valor_Realizado'].sum().to_dict()
saidas_orc_dict = df_orc_m_base.groupby('Mes')['Valor_Orcado'].sum().to_dict()
max_mes_realizado = df_real_m_base['Mes'].max() if not df_real_m_base.empty else 0

todas_obras_fluxo = set(df_real_m_base['Obra'].unique()) if not df_real_m_base.empty else set()
if not df_orc_m_base.empty:
    todas_obras_fluxo = todas_obras_fluxo.union(set(df_orc_m_base['Obra'].unique()))
obras_fluxo = sorted(list(todas_obras_fluxo))
if obra_selecionada != "Todas":
    obras_fluxo = [obra_selecionada]

real_por_obra_mes = df_real_m_base.groupby(['Mes', 'Obra'])['Valor_Realizado'].sum().to_dict()
orc_por_obra_mes = df_orc_m_base.groupby(['Mes', 'Obra'])['Valor_Orcado'].sum().to_dict()

s_ini_list, saidas_tot_list, s_fim_list = [], [], []
curr_saldo = caixa_inicial_base
for m in range(1, 13):
    s_ini_list.append(curr_saldo)
    saida_m = saidas_real_dict.get(m, 0.0) if m <= max_mes_realizado else saidas_orc_dict.get(m, 0.0)
    saidas_tot_list.append(saida_m)
    curr_saldo = curr_saldo - saida_m
    s_fim_list.append(curr_saldo)

html_fluxo = "<div class='unified-summary-box'><table class='unified-table'><thead><tr><th class='row-label'>Fluxo de Caixa</th>"
for m_num in range(1, 13):
    html_fluxo += f"<th>{meses_nomes[m_num]}</th>"
html_fluxo += "</tr></thead><tbody>"

html_fluxo += "<tr><td class='row-label'>Saldo Inicial</td>"
for val in s_ini_list:
    html_fluxo += f"<td>{formatar_moeda_curta(val)}</td>"
html_fluxo += "</tr>"

html_fluxo += "<tbody class='obra-group'><tr>"
html_fluxo += (
    "<td class='row-label'>"
    "<label class='drilldown-label' style='padding-left:0;'>"
    "<input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> "
    "<b>(-) Saídas Totais</b></label></td>"
)
for val in saidas_tot_list:
    html_fluxo += f"<td style='color:#f87171;font-weight:800'>{formatar_moeda_curta(val)}</td>"
html_fluxo += "</tr>"

for obra_name in obras_fluxo:
    html_fluxo += (
        f"<tr class='sub-row'><td class='row-label' style='padding-left:28px;font-size:10px;"
        f"font-weight:normal;color:#8fa3c4;border-right:2px solid #1c2a47;overflow:hidden;"
        f"text-overflow:ellipsis;white-space:nowrap'>↳ {obra_name}</td>"
    )
    for m_num in range(1, 13):
        v_obra = real_por_obra_mes.get((m_num, obra_name), 0.0) if m_num <= max_mes_realizado else orc_por_obra_mes.get((m_num, obra_name), 0.0)
        v_str = formatar_moeda_curta(v_obra) if v_obra > 0 else "-"
        html_fluxo += f"<td style='text-align:right;font-size:10px;color:#8fa3c4'>{v_str}</td>"
    html_fluxo += "</tr>"
html_fluxo += "</tbody>"

html_fluxo += "<tr><td class='row-label' style='font-weight:800'>(=) Saldo Final</td>"
for m_num, val in enumerate(s_fim_list, start=1):
    css_class = "val-real" if m_num <= max_mes_realizado else "val-orc"
    html_fluxo += f"<td class='{css_class}'><b>{formatar_moeda_curta(val)}</b></td>"
html_fluxo += "</tr></tbody></table></div>"
st.markdown(html_fluxo, unsafe_allow_html=True)

# ==============================================================================
# 7. TABELA DETALHADA DE ORÇAMENTOS POR OBRA
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento do orçamento por obra</div>", unsafe_allow_html=True)

if not df_orc_filtrado.empty:
    df_orc_tab = df_orc_filtrado[df_orc_filtrado['Mes'] > 0].copy()
    if not df_orc_tab.empty:
        pivot_orc = pd.pivot_table(
            df_orc_tab, index='Obra', columns='Mes', values='Valor_Orcado',
            aggfunc='sum', fill_value=0.0,
        )
        for m in range(1, 13):
            if m not in pivot_orc.columns:
                pivot_orc[m] = 0.0
        pivot_orc = pivot_orc[sorted(pivot_orc.columns)]
        pivot_orc['Total_Geral'] = pivot_orc.sum(axis=1)
        pivot_orc = pivot_orc.sort_values(by='Total_Geral', ascending=False)

        html_orc_det = "<div class='fases-table-container'><table class='fases-table'><thead><tr><th>OBRA / FASE DA OBRA</th>"
        html_orc_det += "<th style='text-align:right'>TOTAL ORÇADO</th>"
        for m_num in range(1, 13):
            html_orc_det += f"<th style='text-align:right'>{meses_nomes[m_num].upper()}</th>"
        html_orc_det += "</tr></thead>"

        totais_col_orc = {m: 0.0 for m in range(1, 13)}
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
            html_orc_det += f"<td style='text-align:right;font-weight:800;color:{AZUL}'>{formatar_moeda(tot_obra)}</td>"

            for m_num in range(1, 13):
                val_m = row.get(m_num, 0.0)
                totais_col_orc[m_num] += val_m
                val_str = formatar_moeda(val_m) if val_m > 0 else "-"
                html_orc_det += f"<td style='text-align:right;font-weight:700'>{val_str}</td>"
            html_orc_det += "</tr>"

            if fases_lista:
                num_fases = len(fases_lista)
                for fase_name in fases_lista:
                    html_orc_det += "<tr class='sub-row'>"
                    html_orc_det += (
                        f"<td title='↳ {fase_name}' style='padding-left:30px;font-size:11px;color:#8fa3c4;"
                        f"border-right:2px solid #1c2a47;overflow:hidden;text-overflow:ellipsis;"
                        f"white-space:nowrap'>↳ {fase_name}</td>"
                    )
                    val_sub_total = tot_obra / num_fases if num_fases > 0 else 0
                    html_orc_det += f"<td style='text-align:right;font-size:11px;font-weight:600;color:#8fa3c4'>{formatar_moeda(val_sub_total)}</td>"
                    for m_num in range(1, 13):
                        val_m_sub = row.get(m_num, 0.0) / num_fases if num_fases > 0 else 0
                        v_str_sub = formatar_moeda(val_m_sub) if val_m_sub > 0 else "-"
                        html_orc_det += f"<td style='text-align:right;font-size:11px;color:#8fa3c4'>{v_str_sub}</td>"
                    html_orc_det += "</tr>"
            html_orc_det += "</tbody>"

        html_orc_det += "<tr class='total-geral-row'><td>TOTAL GERAL ORÇADO</td>"
        html_orc_det += f"<td style='text-align:right;font-weight:900;color:{AZUL}'>{formatar_moeda(total_geral_orc)}</td>"
        for m_num in range(1, 13):
            t_col = totais_col_orc[m_num]
            val_col_str = formatar_moeda(t_col) if t_col > 0 else "-"
            html_orc_det += f"<td style='text-align:right;font-weight:900'>{val_col_str}</td>"
        html_orc_det += "</tr></table></div>"
        st.markdown(html_orc_det, unsafe_allow_html=True)

# ==============================================================================
# 8. TABELA DETALHADA DE PAGAMENTOS REALIZADOS
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento de pagamentos realizados</div>", unsafe_allow_html=True)

if not df_real_filtrado.empty:
    df_real_tab = df_real_filtrado[df_real_filtrado['Mes'] > 0].copy()
    df_orc_tab = df_orc_filtrado[df_orc_filtrado['Mes'] > 0].copy() if not df_orc_filtrado.empty else pd.DataFrame()

    if not df_real_tab.empty:
        orc_obra_mes, orc_obra_tot = {}, {}
        orc_mes_tot = {m: 0.0 for m in range(1, 13)}

        if not df_orc_tab.empty:
            df_orc_grp = df_orc_tab.groupby(['Obra', 'Mes'])['Valor_Orcado'].sum().reset_index()
            for _, r in df_orc_grp.iterrows():
                orc_obra_mes[(r['Obra'], r['Mes'])] = r['Valor_Orcado']
                orc_obra_tot[r['Obra']] = orc_obra_tot.get(r['Obra'], 0.0) + r['Valor_Orcado']
                orc_mes_tot[r['Mes']] = orc_mes_tot.get(r['Mes'], 0.0) + r['Valor_Orcado']

        total_orcado_geral = sum(orc_mes_tot.values())

        pivot_real = pd.pivot_table(
            df_real_tab, index='Obra', columns='Mes', values='Valor_Realizado',
            aggfunc='sum', fill_value=0.0,
        )
        for m in range(1, 13):
            if m not in pivot_real.columns:
                pivot_real[m] = 0.0
        pivot_real = pivot_real[sorted(pivot_real.columns)]
        pivot_real['Total_Geral'] = pivot_real.sum(axis=1)
        pivot_real = pivot_real.sort_values(by='Total_Geral', ascending=False)

        html_real_det = "<div class='fases-table-container'><table class='fases-table'><thead><tr><th>OBRA / CATEGORIA</th>"
        html_real_det += "<th style='text-align:right'>TOTAL</th>"
        for m_num in range(1, 13):
            html_real_det += f"<th style='text-align:right'>{meses_nomes[m_num].upper()}</th>"
        html_real_det += "</tr></thead>"

        totais_col_real = {m: 0.0 for m in range(1, 13)}
        totais_geral_real = 0.0

        for obra_name, row in pivot_real.iterrows():
            sub_df = df_real_tab[df_real_tab['Obra'] == obra_name]
            pivot_sub = pd.pivot_table(
                sub_df, index='Fornecedor', columns='Mes', values='Valor_Realizado',
                aggfunc='sum', fill_value=0.0,
            )
            for m in range(1, 13):
                if m not in pivot_sub.columns:
                    pivot_sub[m] = 0.0
            pivot_sub = pivot_sub[sorted(pivot_sub.columns)]
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
                f"<td style='text-align:right'><span style='font-weight:800;color:{cor_tot_obra}'>"
                f"{formatar_moeda(tot_obra_real)}</span>"
                f"<span class='orcado-indicator'>{str_orc_tot_obra}</span></td>"
            )

            for m_num in range(1, 13):
                val_m_real = row.get(m_num, 0.0)
                totais_col_real[m_num] += val_m_real
                val_m_orc = orc_obra_mes.get((obra_name, m_num), 0.0)

                if val_m_real > 0 and val_m_orc > 0:
                    cor_m = VERDE if val_m_real <= val_m_orc else VERMELHO
                else:
                    cor_m = TXT

                val_str = formatar_moeda(val_m_real) if val_m_real > 0 else "-"
                str_orc_m = f"Orç: {formatar_moeda_curta(val_m_orc)}" if val_m_orc > 0 else "Orç: -"
                html_real_det += (
                    f"<td style='text-align:right'><span style='font-weight:800;color:{cor_m}'>{val_str}</span>"
                    f"<span class='orcado-indicator'>{str_orc_m}</span></td>"
                )
            html_real_det += "</tr>"

            for forn_name, sub_row in pivot_sub.iterrows():
                tot_sub_geral = sub_row['Total_Geral']
                html_real_det += "<tr class='sub-row'>"
                html_real_det += (
                    f"<td title='↳ {forn_name}' style='padding-left:30px;font-size:11px;color:#8fa3c4;"
                    f"border-right:2px solid #1c2a47;overflow:hidden;text-overflow:ellipsis;"
                    f"white-space:nowrap'>↳ {forn_name}</td>"
                )
                html_real_det += f"<td style='text-align:right;font-size:11px;font-weight:700'>{formatar_moeda(tot_sub_geral)}</td>"
                for m_num in range(1, 13):
                    v_sub = sub_row.get(m_num, 0.0)
                    v_str_sub = formatar_moeda(v_sub) if v_sub > 0 else "-"
                    html_real_det += f"<td style='text-align:right;font-size:11px;color:#8fa3c4'>{v_str_sub}</td>"
                html_real_det += "</tr>"
            html_real_det += "</tbody>"

        str_orc_tot_geral = f"Orç: {formatar_moeda_curta(total_orcado_geral)}" if total_orcado_geral > 0 else "Orç: -"
        html_real_det += "<tr class='total-geral-row'><td>TOTAL GERAL</td>"
        html_real_det += (
            f"<td style='text-align:right'><span style='font-weight:900'>{formatar_moeda(totais_geral_real)}</span>"
            f"<span class='orcado-indicator'>{str_orc_tot_geral}</span></td>"
        )
        for m_num in range(1, 13):
            t_col_real = totais_col_real[m_num]
            t_col_orc = orc_mes_tot.get(m_num, 0.0)
            str_orc_col = f"Orç: {formatar_moeda_curta(t_col_orc)}" if t_col_orc > 0 else "Orç: -"
            val_col_str = formatar_moeda(t_col_real) if t_col_real > 0 else "-"
            html_real_det += (
                f"<td style='text-align:right'><span style='font-weight:900'>{val_col_str}</span>"
                f"<span class='orcado-indicator'>{str_orc_col}</span></td>"
            )
        html_real_det += "</tr></table></div>"
        st.markdown(html_real_det, unsafe_allow_html=True)

# ==============================================================================
# RODAPÉ SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown(
        f"<div class='side-card'><small>Filtro atual</small><b>{txt_mes} · {txt_obra}</b></div>"
        f"<div class='side-card'><small>Última atualização</small><b>{datetime.now():%d/%m/%Y %H:%M}</b></div>",
        unsafe_allow_html=True,
    )
