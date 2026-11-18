import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import textwrap

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA & IDENTIDADE VISUAL (WHITE MODE)
# ==============================================================================
st.set_page_config(
    page_title="Adiantamentos Pagos 2026 · Visão Executiva",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def render_html(html_str: str):
    """Renderiza blocos HTML sem problemas de indentação no Markdown do Streamlit."""
    st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

# CSS Customizado - Identidade Visual White / Corporativa
render_html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #f4f6f9;
        color: #1e293b;
    }

    .stApp {
        background-color: #f4f6f9;
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
    }

    /* Cabeçalho */
    .exec-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 18px;
        padding-bottom: 12px;
        border-bottom: 1px solid #e2e8f0;
    }
    .exec-title {
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.5px;
        margin: 0;
        line-height: 1.2;
    }
    .exec-subtitle {
        font-size: 12.5px;
        color: #64748b;
        margin-top: 4px;
    }

    /* Cards Superiores (KPIs) */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        height: 100%;
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        margin-bottom: 6px;
    }
    .kpi-val {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1.15;
        margin-bottom: 6px;
    }
    .kpi-sub {
        font-size: 11.5px;
        color: #64748b;
        font-weight: 500;
    }
    .c-blue { color: #2563eb; }
    .c-green { color: #16a34a; }
    .c-red { color: #dc2626; }
    .c-amber { color: #d97706; }

    /* Containers de Seção */
    .panel-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        margin-bottom: 14px;
        height: 100%;
    }
    .panel-title {
        font-size: 13.5px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Barra de Composição */
    .comp-bar-wrap {
        width: 100%;
        height: 14px;
        background-color: #e2e8f0;
        border-radius: 999px;
        overflow: hidden;
        display: flex;
        margin: 8px 0 10px 0;
    }
    .comp-seg-green {
        background-color: #16a34a;
        height: 100%;
        transition: width 0.4s ease;
    }
    .comp-seg-red {
        background-color: #dc2626;
        height: 100%;
        transition: width 0.4s ease;
    }
    .comp-legend {
        display: flex;
        gap: 20px;
        font-size: 12px;
        color: #475569;
        font-weight: 500;
    }
    .dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 2px;
        margin-right: 6px;
    }

    /* Barras Horizontais Customizadas (Top 12, Criticidade, Aging) */
    .bar-row {
        display: flex;
        align-items: center;
        margin-bottom: 7px;
        font-size: 11.5px;
        gap: 8px;
    }
    .bar-name {
        width: 44%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #334155;
        font-weight: 500;
    }
    .bar-track {
        flex: 1;
        height: 8px;
        background-color: #f1f5f9;
        border-radius: 999px;
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        border-radius: 999px;
    }
    .bar-metric {
        min-width: 82px;
        text-align: right;
        font-weight: 700;
        color: #0f172a;
        font-variant-numeric: tabular-nums;
    }
    .bar-extra {
        min-width: 115px;
        text-align: right;
        font-size: 11px;
        color: #64748b;
        font-variant-numeric: tabular-nums;
    }

    /* Badges de Criticidade */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 10.5px;
        font-weight: 700;
        text-align: center;
        min-width: 68px;
    }
    .badge-critico {
        background-color: #fee2e2;
        color: #b91c1c;
        border: 1px solid #fecaca;
    }
    .badge-atencao {
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
    }
    .badge-monitorar {
        background-color: #dbeafe;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }

    /* Lista de Conclusões */
    .conclusoes-list {
        margin: 0;
        padding-left: 18px;
        color: #334155;
        font-size: 12.5px;
        line-height: 1.65;
    }
    .conclusoes-list li {
        margin-bottom: 7px;
    }

    /* Tabelas Executivas */
    .table-scroll {
        max-height: 540px;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }
    .exec-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11.5px;
        background: #ffffff;
    }
    .exec-table thead th {
        position: sticky;
        top: 0;
        background-color: #f8fafc;
        color: #475569;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 10px;
        letter-spacing: 0.4px;
        padding: 9px 10px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
        z-index: 1;
    }
    .exec-table thead th.num, .exec-table tbody td.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .exec-table thead th.ctr, .exec-table tbody td.ctr {
        text-align: center;
    }
    .exec-table tbody td {
        padding: 7.5px 10px;
        border-bottom: 1px solid #f1f5f9;
        color: #1e293b;
    }
    .exec-table tbody tr:hover {
        background-color: #f8fafc;
    }
    .td-bold {
        font-weight: 700;
        color: #0f172a;
    }
    .td-muted {
        color: #64748b;
        max-width: 180px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Legenda de Regras */
    .rules-note {
        margin-top: 14px;
        padding-top: 10px;
        border-top: 1px dashed #e2e8f0;
        font-size: 11px;
        color: #64748b;
        line-height: 1.55;
    }

    /* Rodapé */
    .exec-footer {
        margin-top: 16px;
        font-size: 11px;
        color: #94a3b8;
        text-align: left;
    }
</style>
""")

# ==============================================================================
# 2. FUNÇÕES DE FORMATAÇÃO E CARREGAMENTO DE DADOS (GOOGLE SHEETS / BASE_ADT)
# ==============================================================================
def fmt_brl(val: float, decimais: int = 0) -> str:
    if pd.isna(val):
        val = 0.0
    s = f"{val:,.{decimais}f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_int(val: int) -> str:
    return f"{int(val):,}".replace(",", ".")

def fmt_pct(val: float, decimais: int = 1) -> str:
    return f"{val:.{decimais}f}%".replace(".", ",")

def fmt_mi(val: float) -> str:
    return f"R$ {val / 1_000_000:.2f} mi".replace(".", ",")

@st.cache_data(ttl=300)
def carregar_base_sheets(sheet_id: str, aba: str = "Base_ADT") -> pd.DataFrame:
    """
    Tenta carregar a aba Base_ADT do Google Sheets via Service Account (st.secrets)
    ou via URL pública GViz CSV.
    """
    # 1. Tentativa via gspread (Service Account configurada no Streamlit)
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        if "gcp_service_account" in st.secrets:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )
            gc = gspread.authorize(creds)
            ws = gc.open_by_key(sheet_id).worksheet(aba)
            data = ws.get_all_records()
            return pd.DataFrame(data)
    except Exception:
        pass

    # 2. Fallback via URL de exportação CSV do Google Sheets (caso planilha esteja compartilhada)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
    return pd.read_csv(url)

def limpar_moeda(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce").fillna(0.0)
    s = (
        serie.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )
    # Trata formato brasileiro (1.234,56) vs americano (1234.56)
    has_comma = s.str.contains(",", na=False)
    s_br = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(np.where(has_comma, s_br, s), errors="coerce").fillna(0.0)

def preparar_dados(df_raw: pd.DataFrame, data_corte: pd.Timestamp) -> pd.DataFrame:
    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Padronização de colunas essenciais
    df["Valor"] = limpar_moeda(df["Valor"])
    df["Saldo"] = limpar_moeda(df["Saldo"])
    df["Baixado"] = (df["Valor"] - df["Saldo"]).clip(lower=0.0)

    df["Data inclusão"] = pd.to_datetime(df["Data inclusão"], dayfirst=True, errors="coerce")
    df["Data baixa"] = pd.to_datetime(df["Data baixa"], dayfirst=True, errors="coerce")

    df["Pessoa física/jurídica"] = df["Pessoa física/jurídica"].fillna("Não Informado").astype(str).str.strip()
    df["Banco"] = df["Banco"].fillna("Não Informado").astype(str).str.strip()
    df["Observação"] = df["Observação"].fillna("").astype(str).str.strip()
    df["Estabelecimento"] = df["Estabelecimento"].fillna("SOS Cardio").astype(str).str.strip()

    # Dias desde a inclusão até a data de referência
    df["Dias"] = (data_corte - df["Data inclusão"]).dt.days.fillna(0).astype(int)
    df["Dias"] = df["Dias"].clip(lower=0)

    # Mês/Ano da inclusão
    meses_pt = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }
    df["Mes_Num"] = df["Data inclusão"].dt.month
    df["Ano"] = df["Data inclusão"].dt.year
    df["Mes_Nome"] = df["Mes_Num"].map(meses_pt).fillna("N/D")
    df["Mes_Ano"] = df["Mes_Nome"] + "/" + df["Ano"].fillna(2026).astype(int).astype(str).str[-2:]

    return df

def classificar_criticidade(saldo_forn: float, max_dias_forn: int) -> str:
    """
    Regras idênticas à referência executiva:
    - Crítico: saldo >= R$ 100 mil, ou >= R$ 20 mil com adiantamento há mais de 90 dias
    - Atenção: saldo >= R$ 20 mil, ou >= R$ 5 mil com mais de 90 dias
    - Monitorar: demais fornecedores com saldo
    """
    if saldo_forn >= 100_000 or (saldo_forn >= 20_000 and max_dias_forn > 90):
        return "Crítico"
    elif saldo_forn >= 20_000 or (saldo_forn >= 5_000 and max_dias_forn > 90):
        return "Atenção"
    else:
        return "Monitorar"

# ==============================================================================
# 3. BARRA LATERAL (CONEXÃO E FILTROS INTERATIVOS)
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Fonte de Dados & Filtros")

    # ID padrão da planilha Base_Saldo (aba Base_ADT)
    SHEET_ID_PADRAO = "1J_UpsTsTHK_rIE48MlwwCSZjGgMVdR19N3YTAXLRIZ4"
    ABA_PADRAO = "Base_ADT"

    arquivo_upload = st.file_uploader(
        "Upload alternativo (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        help="Opcional: se não enviar arquivo, o painel consome automaticamente a aba Base_ADT do Google Sheets."
    )

    if st.button("🔄 Atualizar Dados do Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

# Carregamento dos dados
df_bruto = None
nome_fonte = "Google Sheets · Aba Base_ADT"

if arquivo_upload is not None:
    nome_fonte = f"Arquivo {arquivo_upload.name}"
    if arquivo_upload.name.endswith(".csv"):
        df_bruto = pd.read_csv(arquivo_upload)
    else:
        xls = pd.ExcelFile(arquivo_upload)
        aba_usar = ABA_PADRAO if ABA_PADRAO in xls.sheet_names else xls.sheet_names[0]
        df_bruto = pd.read_excel(arquivo_upload, sheet_name=aba_usar)
else:
    try:
        df_bruto = carregar_base_sheets(SHEET_ID_PADRAO, ABA_PADRAO)
    except Exception as e:
        st.error(
            f"Não foi possível conectar automaticamente à aba **{ABA_PADRAO}** no Google Sheets. "
            f"Verifique as credenciais `gcp_service_account` em `st.secrets` ou faça upload da planilha na barra lateral.\n\nDetalhe: `{e}`"
        )
        st.stop()

# Data de posição padrão (18/11/2026 conforme base, ou selecionável no filtro)
with st.sidebar:
    data_ref = st.date_input(
        "Data de Posição (Corte Aging)",
        value=datetime(2026, 11, 18).date(),
        format="DD/MM/YYYY"
    )

df = preparar_dados(df_bruto, pd.to_datetime(data_ref))

# ==============================================================================
# 4. FILTROS INTERATIVOS NA SIDEBAR
# ==============================================================================
with st.sidebar:
    # Filtro de Mês
    meses_disponiveis = (
        df[["Mes_Num", "Mes_Nome"]]
        .dropna()
        .drop_duplicates()
        .sort_values("Mes_Num")
    )
    lista_meses = meses_disponiveis["Mes_Nome"].tolist()
    meses_sel = st.multiselect(
        "Mês de Inclusão",
        options=lista_meses,
        default=lista_meses,
        placeholder="Todos os meses"
    )

    # Filtro de Fornecedor
    lista_fornecedores = sorted(df["Pessoa física/jurídica"].unique().tolist())
    fornecedores_sel = st.multiselect(
        "Fornecedor",
        options=lista_fornecedores,
        default=[],
        placeholder="Todos os fornecedores"
    )

    # Filtro de Banco
    lista_bancos = sorted(df["Banco"].unique().tolist())
    bancos_sel = st.multiselect(
        "Banco",
        options=lista_bancos,
        default=[],
        placeholder="Todos os bancos"
    )

    # Filtro de Criticidade
    criticidades_sel = st.multiselect(
        "Criticidade do Fornecedor",
        options=["Crítico", "Atenção", "Monitorar"],
        default=[],
        placeholder="Todas as criticidades"
    )

    # Filtro de Status de Saldo
    status_saldo = st.radio(
        "Exibir Adiantamentos",
        options=["Todos (Baixados + Em aberto)", "Somente Em Aberto (Saldo > 0)", "Somente Já Baixados"],
        index=0
    )

# Aplicação dos Filtros
df_filt = df.copy()

if meses_sel:
    df_filt = df_filt[df_filt["Mes_Nome"].isin(meses_sel)]

if fornecedores_sel:
    df_filt = df_filt[df_filt["Pessoa física/jurídica"].isin(fornecedores_sel)]

if bancos_sel:
    df_filt = df_filt[df_filt["Banco"].isin(bancos_sel)]

if status_saldo == "Somente Em Aberto (Saldo > 0)":
    df_filt = df_filt[df_filt["Saldo"] > 0]
elif status_saldo == "Somente Já Baixados":
    df_filt = df_filt[df_filt["Saldo"] == 0]

# Agrupamento por fornecedor (para classificar criticidade e filtrar se solicitado)
df_aberto_pre = df_filt[df_filt["Saldo"] > 0].copy()
forn_grp = (
    df_aberto_pre.groupby("Pessoa física/jurídica", as_index=False)
    .agg(
        Saldo_Aberto=("Saldo", "sum"),
        Qtd_Itens=("Adiantamento", "count"),
        Max_Dias=("Dias", "max")
    )
)
if not forn_grp.empty:
    forn_grp["Criticidade"] = forn_grp.apply(
        lambda r: classificar_criticidade(r["Saldo_Aberto"], r["Max_Dias"]), axis=1
    )
else:
    forn_grp["Criticidade"] = pd.Series(dtype=str)

if criticidades_sel:
    forns_crit = forn_grp[forn_grp["Criticidade"].isin(criticidades_sel)]["Pessoa física/jurídica"].tolist()
    df_filt = df_filt[df_filt["Pessoa física/jurídica"].isin(forns_crit)]
    forn_grp = forn_grp[forn_grp["Criticidade"].isin(criticidades_sel)].copy()

# Recálculo final pós-filtros
df_aberto = df_filt[df_filt["Saldo"] > 0].copy()

total_adiantado = df_filt["Valor"].sum()
total_baixado = df_filt["Baixado"].sum()
total_aberto = df_filt["Saldo"].sum()

qtd_total_adt = len(df_filt)
qtd_forn_total = df_filt["Pessoa física/jurídica"].nunique()
qtd_adt_aberto = len(df_aberto)
qtd_forn_saldo = len(forn_grp)

pct_baixado = (total_baixado / total_adiantado * 100) if total_adiantado > 0 else 0.0
pct_aberto = (total_aberto / total_adiantado * 100) if total_adiantado > 0 else 0.0

df_90 = df_aberto[df_aberto["Dias"] > 90]
saldo_90 = df_90["Saldo"].sum()
qtd_90 = len(df_90)

# Top 5 e Top 10 concentração
forn_sorted = forn_grp.sort_values("Saldo_Aberto", ascending=False).reset_index(drop=True)
top5_pct = (forn_sorted.head(5)["Saldo_Aberto"].sum() / total_aberto * 100) if total_aberto > 0 else 0.0
top10_pct = (forn_sorted.head(10)["Saldo_Aberto"].sum() / total_aberto * 100) if total_aberto > 0 else 0.0

#Texto do período selecionado
meses_completos = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
}
if not df_filt["Mes_Num"].dropna().empty:
    m_min = int(df_filt["Mes_Num"].min())
    m_max = int(df_filt["Mes_Num"].max())
    ano_ref = int(df_filt["Ano"].max())
    periodo_txt = (
        f"{meses_completos[m_min].capitalize()} a {meses_completos[m_max]} de {ano_ref}"
        if m_min != m_max else f"{meses_completos[m_min].capitalize()} de {ano_ref}"
    )
else:
    periodo_txt = "Período selecionado"

data_ref_str = data_ref.strftime("%d/%m/%Y")

# ==============================================================================
# 5. CABEÇALHO EXECUTIVO
# ==============================================================================
render_html(f"""
<div class="exec-header">
    <div>
        <h1 class="exec-title">Adiantamentos Pagos 2026 · Visão Executiva</h1>
        <div class="exec-subtitle">
            Posição em {data_ref_str} · {periodo_txt} · Valores em reais (R$)
        </div>
    </div>
</div>
""")

# ==============================================================================
# 6. LINHA 1: 5 KPIs PRINCIPAIS
# ==============================================================================
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    render_html(f"""
    <div class="kpi-card">
        <div class="kpi-label">TOTAL ADIANTADO</div>
        <div class="kpi-val c-blue">{fmt_brl(total_adiantado)}</div>
        <div class="kpi-sub">{fmt_int(qtd_total_adt)} adiantamentos · {fmt_int(qtd_forn_total)} fornecedores</div>
    </div>
    """)

with k2:
    render_html(f"""
    <div class="kpi-card">
        <div class="kpi-label">JÁ BAIXADO</div>
        <div class="kpi-val c-green">{fmt_brl(total_baixado)}</div>
        <div class="kpi-sub">{fmt_pct(pct_baixado)} do total adiantado</div>
    </div>
    """)

with k3:
    render_html(f"""
    <div class="kpi-card">
        <div class="kpi-label">EM ABERTO (SALDO)</div>
        <div class="kpi-val c-red">{fmt_brl(total_aberto)}</div>
        <div class="kpi-sub">{fmt_pct(pct_aberto)} do total · {fmt_int(qtd_adt_aberto)} adiantamentos</div>
    </div>
    """)

with k4:
    render_html(f"""
    <div class="kpi-card">
        <div class="kpi-label">FORNECEDORES COM SALDO</div>
        <div class="kpi-val c-amber">{fmt_int(qtd_forn_saldo)}</div>
        <div class="kpi-sub">Top 5 = {fmt_pct(top5_pct, 0)} do saldo · Top 10 = {fmt_pct(top10_pct, 1)}</div>
    </div>
    """)

with k5:
    render_html(f"""
    <div class="kpi-card">
        <div class="kpi-label">SALDO COM MAIS DE 90 DIAS</div>
        <div class="kpi-val c-red">{fmt_brl(saldo_90)}</div>
        <div class="kpi-sub">{fmt_int(qtd_90)} adiantamentos sem baixa</div>
    </div>
    """)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ==============================================================================
# 7. LINHA 2: COMPOSIÇÃO DO TOTAL ADIANTADO (BARRA SEGMENTADA)
# ==============================================================================
render_html(f"""
<div class="panel-box">
    <div class="panel-title">Composição do total adiantado: baixado × em aberto</div>
    <div class="comp-bar-wrap">
        <div class="comp-seg-green" style="width: {pct_baixado:.2f}%;"></div>
        <div class="comp-seg-red" style="width: {pct_aberto:.2f}%;"></div>
    </div>
    <div class="comp-legend">
        <div><span class="dot" style="background:#16a34a;"></span>Baixado {fmt_brl(total_baixado)} ({fmt_pct(pct_baixado)})</div>
        <div><span class="dot" style="background:#dc2626;"></span>Em aberto {fmt_brl(total_aberto)} ({fmt_pct(pct_aberto)})</div>
    </div>
</div>
""")

# ==============================================================================
# 8. LINHA 3: TOP 12 CRÍTICOS | CLASSIFICAÇÃO CRITICIDADE | ENVELHECIMENTO (AGING)
# ==============================================================================
col_top12, col_crit, col_aging = st.columns([1.15, 0.95, 1.0])

cor_crit_map = {
    "Crítico": "#dc2626",
    "Atenção": "#f59e0b",
    "Monitorar": "#2563eb"
}

# --- Painel 3A: Fornecedores mais críticos (Top 12) ---
with col_top12:
    top12 = forn_sorted.head(12)
    max_val_top12 = top12["Saldo_Aberto"].max() if not top12.empty else 1.0

    linhas_top12 = ""
    for idx, r in top12.iterrows():
        pct_bar = (r["Saldo_Aberto"] / max_val_top12 * 100) if max_val_top12 > 0 else 0
        cor_b = cor_crit_map.get(r["Criticidade"], "#2563eb")
        linhas_top12 += f"""
        <div class="bar-row">
            <div class="bar-name" title="{r['Pessoa física/jurídica']}">{idx + 1}. {r['Pessoa física/jurídica']}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct_bar:.1f}%; background:{cor_b};"></div>
            </div>
            <div class="bar-metric">{fmt_brl(r['Saldo_Aberto'])}</div>
        </div>
        """

    if not linhas_top12:
        linhas_top12 = "<div style='color:#64748b; font-size:12px;'>Nenhum fornecedor com saldo em aberto no filtro atual.</div>"

    render_html(f"""
    <div class="panel-box">
        <div class="panel-title">Fornecedores mais críticos: saldo em aberto (maior → menor)</div>
        {linhas_top12}
    </div>
    """)

# --- Painel 3B: Classificação de criticidade ---
with col_crit:
    linhas_crit = ""
    for cat, badge_cls, bar_hex in [
        ("Crítico", "badge-critico", "#dc2626"),
        ("Atenção", "badge-atencao", "#f59e0b"),
        ("Monitorar", "badge-monitorar", "#2563eb"),
    ]:
        sub_c = forn_sorted[forn_sorted["Criticidade"] == cat]
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

    render_html(f"""
    <div class="panel-box">
        <div class="panel-title">Classificação de criticidade</div>
        {linhas_crit}
        <div class="rules-note">
            <div><span class="dot" style="background:#dc2626;"></span><b>Crítico:</b> saldo ≥ R$ 100 mil, ou ≥ R$ 20 mil com adiantamento há mais de 90 dias</div>
            <div><span class="dot" style="background:#f59e0b;"></span><b>Atenção:</b> saldo ≥ R$ 20 mil, ou ≥ R$ 5 mil com mais de 90 dias</div>
            <div><span class="dot" style="background:#2563eb;"></span><b>Monitorar:</b> demais fornecedores com saldo</div>
        </div>
    </div>
    """)

# --- Painel 3C: Envelhecimento do saldo em aberto (Aging) ---
with col_aging:
    faixas = [
        ("0–30 dias", 0, 30, "#2563eb"),
        ("31–60", 31, 60, "#2563eb"),
        ("61–90", 61, 90, "#f59e0b"),
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
            <div style="width: 68px; font-weight: 600; color: #334155;">{label}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct_a:.1f}%; background:{cor_f};"></div>
            </div>
            <div class="bar-metric" style="min-width:85px;">{fmt_brl(val_a)}</div>
            <div class="bar-extra" style="min-width:65px;">{fmt_int(qtd_a)} itens</div>
        </div>
        """

    render_html(f"""
    <div class="panel-box">
        <div class="panel-title">Envelhecimento do saldo em aberto (dias desde a inclusão)</div>
        {linhas_aging}
    </div>
    """)

# ==============================================================================
# 9. LINHA 4: EVOLUÇÃO MENSAL (GRÁFICO EMPILHADO) + PRINCIPAIS CONCLUSÕES
# ==============================================================================
col_evol, col_conc = st.columns([1.0, 1.85])

with col_evol:
    render_html('<div class="panel-box" style="padding-bottom:8px;"><div class="panel-title">Evolução mensal: valor adiantado, baixado e em aberto</div>')

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
            marker_color="#16a34a",
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
            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=10.5, color="#475569", family="Inter"),
                fixedrange=True
            ),
            yaxis=dict(
                showgrid=False,
                showticklabels=False,
                range=[0, max_y if max_y > 0 else 1],
                fixedrange=True
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.28,
                xanchor="left",
                x=0,
                font=dict(size=10.5, color="#475569", family="Inter")
            ),
            bargap=0.25
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Sem dados mensais para o filtro selecionado.")

    render_html("</div>")

with col_conc:
    # Cálculo dinâmico dos insights executivos
    top3_df = forn_sorted.head(3)
    top3_soma = top3_df["Saldo_Aberto"].sum()
    top3_pct = (top3_soma / total_aberto * 100) if total_aberto > 0 else 0.0
    nomes_top3 = ", ".join([n.split()[0] for n in top3_df["Pessoa física/jurídica"].tolist()]) if not top3_df.empty else "—"

    crit_df = forn_sorted[forn_sorted["Criticidade"] == "Crítico"]
    qtd_crit = len(crit_df)
    soma_crit = crit_df["Saldo_Aberto"].sum()
    pct_crit = (soma_crit / total_aberto * 100) if total_aberto > 0 else 0.0

    render_html(f"""
    <div class="panel-box">
        <div class="panel-title">Principais conclusões</div>
        <ul class="conclusoes-list">
            <li>
                Do total adiantado de <b>{fmt_mi(total_adiantado)}</b>, <b>{fmt_pct(pct_baixado)}</b> já foi baixado.
                Restam <b>{fmt_mi(total_aberto)}</b> ({fmt_pct(pct_aberto)}) em {fmt_int(qtd_adt_aberto)} adiantamentos.
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
    """)

# ==============================================================================
# 10. LINHA 5: TABELAS DETALHADAS (TOP 20 FORNECEDORES & 15 MAIORES ITENS)
# ==============================================================================
col_t1, col_t2 = st.columns([1.0, 1.05])

# --- Tabela Esquerda: Top 20 fornecedores com saldo em aberto ---
with col_t1:
    top20 = forn_sorted.head(20)
    rows_t1 = ""
    for idx, r in top20.iterrows():
        pct_s = (r["Saldo_Aberto"] / total_aberto * 100) if total_aberto > 0 else 0.0
        pct_s_str = f"{pct_s:.0f}%" if pct_s >= 5.5 else f"{pct_s:.1f}%".replace(".", ",")
        crit = r["Criticidade"]
        b_cls = "badge-critico" if crit == "Crítico" else ("badge-atencao" if crit == "Atenção" else "badge-monitorar")
        rows_t1 += f"""
        <tr>
            <td class="ctr">{idx + 1}</td>
            <td class="td-bold">{r['Pessoa física/jurídica']}</td>
            <td class="num td-bold">{fmt_brl(r['Saldo_Aberto'])}</td>
            <td class="num">{pct_s_str}</td>
            <td class="num">{fmt_int(r['Qtd_Itens'])}</td>
            <td class="num">{fmt_int(r['Max_Dias'])}</td>
            <td class="ctr"><span class="badge {b_cls}">{crit}</span></td>
        </tr>
        """

    if not rows_t1:
        rows_t1 = '<tr><td colspan="7" class="ctr" style="padding:18px; color:#64748b;">Sem registros em aberto.</td></tr>'

    render_html(f"""
    <div class="panel-box">
        <div class="panel-title">Top 20 fornecedores com saldo em aberto</div>
        <div class="table-scroll">
            <table class="exec-table">
                <thead>
                    <tr>
                        <th class="ctr">#</th>
                        <th>Fornecedor</th>
                        <th class="num">Saldo em aberto</th>
                        <th class="num">% do saldo</th>
                        <th class="num">Itens</th>
                        <th class="num">Mais antigo (dias)</th>
                        <th class="ctr">Criticidade</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_t1}
                </tbody>
            </table>
        </div>
    </div>
    """)

# --- Tabela Direita: 15 maiores adiantamentos em aberto (por item) ---
with col_t2:
    top15_itens = df_aberto.sort_values("Saldo", ascending=False).head(15)
    rows_t2 = ""
    for _, r in top15_itens.iterrows():
        dt_inc = r["Data inclusão"].strftime("%d/%m/%Y") if pd.notna(r["Data inclusão"]) else "—"
        adt_id = int(r["Adiantamento"]) if pd.notna(r["Adiantamento"]) else "—"
        rows_t2 += f"""
        <tr>
            <td class="td-bold">{adt_id}</td>
            <td style="max-width:190px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{r['Pessoa física/jurídica']}">
                {r['Pessoa física/jurídica']}
            </td>
            <td class="ctr">{dt_inc}</td>
            <td class="num">{fmt_brl(r['Valor'])}</td>
            <td class="num td-bold">{fmt_brl(r['Saldo'])}</td>
            <td class="num">{fmt_int(r['Dias'])}</td>
            <td class="td-muted" title="{r['Observação']}">{r['Observação']}</td>
        </tr>
        """

    if not rows_t2:
        rows_t2 = '<tr><td colspan="7" class="ctr" style="padding:18px; color:#64748b;">Sem adiantamentos em aberto.</td></tr>'

    render_html(f"""
    <div class="panel-box">
        <div class="panel-title">15 maiores adiantamentos em aberto (por item)</div>
        <div class="table-scroll">
            <table class="exec-table">
                <thead>
                    <tr>
                        <th>Adiant.</th>
                        <th>Fornecedor</th>
                        <th class="ctr">Inclusão</th>
                        <th class="num">Valor</th>
                        <th class="num">Saldo</th>
                        <th class="num">Dias</th>
                        <th>Observação</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_t2}
                </tbody>
            </table>
        </div>
    </div>
    """)

# ==============================================================================
# 11. RODAPÉ
# ==============================================================================
estab_nome = df_filt["Estabelecimento"].iloc[0] if not df_filt.empty else "SOS Cardio"
render_html(f"""
<div class="exec-footer">
    Fonte: {nome_fonte} ({fmt_int(qtd_total_adt)} adiantamentos, Estabelecimento {estab_nome}).
    Baixado = Valor − Saldo. Em aberto = Saldo. Idade calculada até {data_ref_str}.
</div>
""")
