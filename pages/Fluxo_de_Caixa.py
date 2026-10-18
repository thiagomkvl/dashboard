import streamlit as st

try:
    st.set_page_config(
        page_title="Fluxo de Caixa",
        layout="wide",
        page_icon="💵",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

import re
import textwrap
import unicodedata
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go

try:
    from database import conectar_sheets
except Exception as _err:
    _erro_import_db = str(_err)

    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {_erro_import_db}")
        return None

# ==============================================================================
# PALETA — tema claro / clean
# ==============================================================================
AZUL, VERDE, AMBAR, VERMELHO = "#2563eb", "#059669", "#d97706", "#dc2626"
ROXO, LARANJA, CIANO, ROSA = "#7c3aed", "#ea580c", "#0891b2", "#e11d48"
TXT, MUTED, BORDA = "#0f172a", "#64748b", "#e2e8f0"
SURFACE, BG = "#ffffff", "#f8fafc"

ESPACO_ENTRE_BLOCOS = "1.0rem"
AJUSTE_APOS_KPIS = "1.0rem"

ABA_DESPESAS = "Base_Despesas"
ABA_TITULOS = "Base_Titulos"

# Transações de Base_Despesas permitidas (coluna D = Transação FCx)
TRANSACOES_DESPESAS = {
    "despesas administrativas",
    "despesas financeiras",
    "despesas judiciais",
    "devolucao adiantamento particular",
    "honorarios medicos",
    "iptu",
    "outras despesas",
    "parcelamento impostos",
    "pessoal",
    "pmts",
}

# Filtro de Base_Titulos (coluna Q = Transação Borderô)
TRANSACAO_BORDERO = "bx bordero - banco"

CORES_CAT = [
    AZUL, VERDE, AMBAR, ROXO, LARANJA, CIANO, ROSA, VERMELHO,
    "#0ea5e9", "#84cc16", "#f43f5e", "#a855f7", "#14b8a6", "#eab308",
]

MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# ==============================================================================
# CSS
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #f8fafc !important; color: #0f172a; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1.4rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: __GAP__; }
    [data-testid="stMarkdownContainer"] { color: #0f172a; }

    [data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stWidgetLabel"] p { color: #64748b !important; font-size: 12px; font-weight: 600; }
    .side-sec {
        font-size: 10px; font-weight: 800; letter-spacing: 1px;
        color: #64748b; text-transform: uppercase; margin: 6px 0 -2px;
    }
    .side-card {
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 10px 12px; margin-top: 8px;
    }
    .side-card small { display: block; color: #64748b; font-size: 11px; }
    .side-card b { color: #0f172a; font-size: 13px; }

    [data-baseweb="select"] > div {
        background: #ffffff !important; border-color: #e2e8f0 !important; color: #0f172a !important;
    }
    [data-baseweb="select"] span, [data-baseweb="select"] input { color: #0f172a !important; }
    [data-baseweb="select"] svg { fill: #64748b; }
    [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #ffffff !important; }
    li[role="option"] { color: #0f172a !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background: #f1f5f9 !important; }
    span[data-baseweb="tag"] { background: #2563eb !important; color: #fff !important; }

    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-weight: 700 !important; padding: 0.55rem 1rem !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover { filter: brightness(1.06); color: #fff !important; }

    .top {
        display: flex; justify-content: space-between; align-items: center; gap: 16px;
        padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px solid #e2e8f0;
    }
    .top h1 { margin: 0; font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: 0.3px; }
    .top p { margin: 2px 0 0; font-size: 13px; color: #64748b; }
    .pills { display: flex; gap: 10px; flex-wrap: wrap; }
    .pill {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 6px 14px; min-width: 120px;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04);
    }
    .pill small { display: block; font-size: 10px; color: #64748b; }
    .pill b { font-size: 13px; color: #0f172a; white-space: nowrap; }

    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: __KPI_GAP__; }
    .kpi {
        padding: 12px 14px; border-radius: 12px; min-height: 96px;
        background: #ffffff; border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(15,23,42,0.05);
        border-left: 3px solid #2563eb;
    }
    .kpi.green { border-left-color: #059669; }
    .kpi.amber { border-left-color: #d97706; }
    .kpi.red { border-left-color: #dc2626; }
    .kpi.purple { border-left-color: #7c3aed; }
    .kpi-t {
        font-size: 10px; font-weight: 800; letter-spacing: 0.4px;
        text-transform: uppercase; color: #64748b; line-height: 1.25;
    }
    .kpi-v {
        font-size: 18px; font-weight: 800; color: #0f172a; margin: 8px 0 4px;
        letter-spacing: -0.3px; font-variant-numeric: tabular-nums; white-space: nowrap;
    }
    .kpi-sub { font-size: 11px; color: #64748b; font-weight: 600; }
    .kpi-sub.up { color: #059669; }
    .kpi-sub.down { color: #dc2626; }

    .section-title {
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #0f172a; margin: 16px 0 10px; padding-left: 10px; border-left: 3px solid #2563eb;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff; border: 1px solid #e2e8f0 !important; border-radius: 12px;
        box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    }
    .card-title {
        display: flex; align-items: center; justify-content: space-between;
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #0f172a; margin: 2px 0 6px;
    }
    .card-title span { font-size: 10px; font-weight: 600; text-transform: none; color: #64748b; letter-spacing: 0.2px; }

    .tbl-wrap {
        overflow: auto; max-height: 420px; border-radius: 10px;
        border: 1px solid #e2e8f0; background: #ffffff;
    }
    .tbl { width: 100%; border-collapse: collapse; font-size: 12px; color: #334155; }
    .tbl th {
        position: sticky; top: 0; z-index: 2; background: #f8fafc; color: #64748b;
        font-weight: 700; font-size: 11px; text-align: left; padding: 8px 10px;
        border-bottom: 1px solid #e2e8f0; white-space: nowrap; text-transform: uppercase;
    }
    .tbl td {
        padding: 8px 10px; border-bottom: 1px solid #f1f5f9; white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }
    .tbl tbody tr:hover td { background: #f8fafc; }
    .tbl tr.tot td {
        font-weight: 800; color: #0f172a; background: #f1f5f9;
        border-top: 1px solid #e2e8f0;
    }
    .tbl .mut { color: #94a3b8; }
    .dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 8px; vertical-align: middle;
    }
    .bar {
        height: 8px; min-width: 80px; background: #f1f5f9;
        border-radius: 4px; overflow: hidden;
    }
    .bar span { display: block; height: 100%; border-radius: 4px; }
    .tbl-wrap::-webkit-scrollbar { height: 6px; width: 6px; }
    .tbl-wrap::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 6px; }
    .vazio { color: #64748b; font-size: 12px; padding: 28px 8px; text-align: center; }
    .leg {
        display: grid; grid-template-columns: 12px 1fr 56px 80px; gap: 8px;
        align-items: center; font-size: 11.5px; padding: 3px 0; color: #334155;
    }
    .leg i { width: 9px; height: 9px; border-radius: 50%; display: block; }
    .leg em { font-style: normal; color: #64748b; }
    .leg b { color: #0f172a; font-weight: 700; }
    .origem-tag {
        display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 8px;
        border-radius: 999px; letter-spacing: 0.2px;
    }
    .origem-desp { background: rgba(37,99,235,0.10); color: #1d4ed8; }
    .origem-bord { background: rgba(124,58,237,0.10); color: #6d28d9; }
</style>
"""
st.markdown(
    textwrap.dedent(css).replace("__GAP__", ESPACO_ENTRE_BLOCOS).replace("__KPI_GAP__", AJUSTE_APOS_KPIS),
    unsafe_allow_html=True,
)

# ==============================================================================
# HELPERS
# ==============================================================================
def normalizar(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return ""
    s = unicodedata.normalize("NFKD", str(txt)).encode("ASCII", "ignore").decode("utf-8")
    return s.lower().strip()


def limpa_valor(v):
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        s = str(v).strip().replace("R$", "").replace(" ", "")
        if s in ("", "-", "nan", "None", "NaN"):
            return 0.0
        neg = (s.startswith("(") and s.endswith(")")) or s.startswith("-")
        s = s.strip("()-")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
            s = s.replace(".", "")
        r = float(s)
        return -r if neg else r
    except Exception:
        return 0.0


def parse_data(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return pd.NaT
    if isinstance(v, (pd.Timestamp, datetime)):
        return pd.Timestamp(v).normalize()
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        n = float(v)
        if 20000 < n < 80000:
            return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)).normalize()
    try:
        return pd.to_datetime(v, dayfirst=True, errors="coerce").normalize()
    except Exception:
        return pd.NaT


def _br(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(v, casas=2):
    return "R$ " + _br(v, casas)


def moeda_curta(v):
    a = abs(v)
    if a >= 1e9:
        return f"R$ {_br(v / 1e9, 1)}Bi"
    if a >= 1e6:
        return f"R$ {_br(v / 1e6, 1)}M"
    if a >= 1e3:
        return f"R$ {_br(v / 1e3, 1)}K"
    return f"R$ {_br(v, 0)}"


def pct(v):
    return f"{_br(v, 1)}%"


def div(a, b):
    return a / b if b else 0.0


def rot_mes(ts):
    return f"{MESES_ABREV[ts.month - 1]}/{str(ts.year)[2:]}"


def col_por_letra(df, letra):
    """Retorna a coluna pela letra Excel (A=0). Aceita se o header for a letra."""
    idx = ord(letra.upper()) - ord("A")
    if 0 <= idx < len(df.columns):
        return df.columns[idx]
    # fallback: header normalizado igual à letra
    for c in df.columns:
        if normalizar(c) == letra.lower():
            return c
    return None


def col_por_nomes(df, nomes):
    mapa = {normalizar(c): c for c in df.columns}
    for n in nomes:
        if normalizar(n) in mapa:
            return mapa[normalizar(n)]
    return None


def barra(w, cor):
    w = max(0.0, min(100.0, float(w)))
    return f"<div class='bar'><span style='width:{w:.1f}%;background:{cor}'></span></div>"


def tabela(heads, rows, total=None, altura=380):
    th = "".join(f"<th>{h}</th>" for h in heads)
    tb = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    if total:
        tb += "<tr class='tot'>" + "".join(f"<td>{c}</td>" for c in total) + "</tr>"
    return (
        f"<div class='tbl-wrap' style='max-height:{altura}px'>"
        f"<table class='tbl'><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>"
    )


def vazio_html(msg="Sem dados no período"):
    return f"<div class='vazio'>{msg}</div>"


def layout_fig(fig, h=300, legenda=True):
    fig.update_layout(
        height=h,
        margin=dict(l=0, r=0, t=28 if legenda else 6, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=11, color=MUTED),
        separators=",.",
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11, color=TXT)),
        hoverlabel=dict(bgcolor=SURFACE, font_color=TXT, bordercolor=BORDA),
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDA, tickfont=dict(size=10, color=MUTED))
    fig.update_yaxes(
        gridcolor="rgba(148,163,184,0.25)", zeroline=False,
        tickprefix="R$ ", tickformat=".2s", tickfont=dict(size=10, color=MUTED),
    )
    return fig


def cor_cat(nome, mapa):
    if nome not in mapa:
        mapa[nome] = CORES_CAT[len(mapa) % len(CORES_CAT)]
    return mapa[nome]


# ==============================================================================
# CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60, show_spinner="Carregando fluxo de caixa…")
def carregar_fluxo():
    """
    Unifica:
      - Base_Despesas (transações listadas) → Data, Classificação, Transação, Valor
      - Base_Titulos (Bx Borderô - Banco)   → Data Baixa, Conta contábil, Valor Pago
    """
    vazio = pd.DataFrame(columns=[
        "Data", "Ref", "Classificação", "Transação", "Valor", "Origem",
    ])
    avisos = []
    conn = conectar_sheets()
    if conn is None:
        return vazio, ["Conexão com o Google Sheets indisponível."]

    partes = []

    # ---- Base_Despesas ----
    try:
        raw_d = conn.read(worksheet=ABA_DESPESAS, ttl=0)
    except Exception as e:
        raw_d = None
        avisos.append(f"Aba '{ABA_DESPESAS}': {e}")

    if raw_d is not None and not raw_d.empty:
        df = raw_d.copy()
        # Preferência por letra (B, D, E, F); fallback por nome
        c_data = col_por_letra(df, "B") or col_por_nomes(df, ["Data", "Data Lançamento", "Dt"])
        c_trans = col_por_letra(df, "D") or col_por_nomes(df, ["Transação FCx", "Transacao FCx", "Transação", "Transacao"])
        c_clas = col_por_letra(df, "E") or col_por_nomes(df, ["Classificação FCx", "Classificacao FCx", "Classificação", "Classificacao"])
        c_val = col_por_letra(df, "F") or col_por_nomes(df, ["Vl Débito", "Vl Debito", "Valor Débito", "Valor Debito", "Débito", "Debito", "Valor"])

        if not all([c_data, c_trans, c_clas, c_val]):
            avisos.append(
                f"Aba '{ABA_DESPESAS}': colunas esperadas não encontradas "
                f"(Data/B, Transação FCx/D, Classificação FCx/E, Vl Débito/F)."
            )
        else:
            tmp = pd.DataFrame({
                "Data": df[c_data].apply(parse_data),
                "Transação": df[c_trans].fillna("").astype(str).str.strip(),
                "Classificação": df[c_clas].fillna("(Sem classificação)").astype(str).str.strip(),
                "Valor": df[c_val].apply(limpa_valor),
            })
            tmp["Transação_n"] = tmp["Transação"].map(normalizar)
            tmp = tmp[tmp["Transação_n"].isin(TRANSACOES_DESPESAS)].copy()
            tmp = tmp[tmp["Data"].notna() & (tmp["Valor"].abs() > 0.005)]
            if not tmp.empty:
                tmp["Origem"] = "Despesas"
                tmp["Ref"] = tmp["Data"].apply(lambda d: pd.Timestamp(d.year, d.month, 1))
                partes.append(tmp[["Data", "Ref", "Classificação", "Transação", "Valor", "Origem"]])
            else:
                avisos.append(f"Aba '{ABA_DESPESAS}': nenhuma linha nas transações filtradas.")
    else:
        if raw_d is None or (hasattr(raw_d, "empty") and raw_d.empty):
            avisos.append(f"Aba '{ABA_DESPESAS}' vazia ou indisponível.")

    # ---- Base_Titulos (Bx Borderô - Banco) ----
    try:
        raw_t = conn.read(worksheet=ABA_TITULOS, ttl=0)
    except Exception as e:
        raw_t = None
        avisos.append(f"Aba '{ABA_TITULOS}': {e}")

    if raw_t is not None and not raw_t.empty:
        df = raw_t.copy()
        c_data = col_por_letra(df, "D") or col_por_nomes(df, ["Data Baixa", "Dt Baixa", "Data da Baixa", "Data"])
        c_clas = col_por_letra(df, "I") or col_por_nomes(df, [
            "Conta contábil", "Conta contabil", "Classificação FCx", "Classificacao FCx", "Conta Contábil",
        ])
        c_val = col_por_letra(df, "W") or col_por_nomes(df, ["Vl Pago", "Valor Pago", "Valor", "Vl. Pago"])
        c_bord = col_por_letra(df, "Q") or col_por_nomes(df, [
            "Transação Borderô", "Transacao Bordero", "Transação Bordero", "Transacao Borderô",
            "Transação Borderô", "Bordero",
        ])

        if not all([c_data, c_clas, c_val, c_bord]):
            avisos.append(
                f"Aba '{ABA_TITULOS}': colunas esperadas não encontradas "
                f"(Data Baixa/D, Conta contábil/I, Transação Borderô/Q, Vl Pago/W)."
            )
        else:
            tmp = pd.DataFrame({
                "Data": df[c_data].apply(parse_data),
                "Classificação": df[c_clas].fillna("(Sem classificação)").astype(str).str.strip(),
                "Transação": df[c_bord].fillna("").astype(str).str.strip(),
                "Valor": df[c_val].apply(limpa_valor),
            })
            tmp["Transação_n"] = tmp["Transação"].map(normalizar)
            tmp = tmp[tmp["Transação_n"] == TRANSACAO_BORDERO].copy()
            tmp = tmp[tmp["Data"].notna() & (tmp["Valor"].abs() > 0.005)]
            if not tmp.empty:
                # Padroniza rótulo da transação
                tmp["Transação"] = "Bx Borderô - Banco"
                tmp["Origem"] = "Borderô"
                tmp["Ref"] = tmp["Data"].apply(lambda d: pd.Timestamp(d.year, d.month, 1))
                partes.append(tmp[["Data", "Ref", "Classificação", "Transação", "Valor", "Origem"]])
            else:
                avisos.append(f"Aba '{ABA_TITULOS}': nenhuma linha com 'Bx Borderô - Banco'.")
    else:
        if raw_t is None or (hasattr(raw_t, "empty") and raw_t.empty):
            avisos.append(f"Aba '{ABA_TITULOS}' vazia ou indisponível.")

    if not partes:
        return vazio, avisos or ["Nenhum lançamento encontrado nas bases."]

    base = pd.concat(partes, ignore_index=True)
    base["Classificação"] = base["Classificação"].replace({"": "(Sem classificação)", "nan": "(Sem classificação)"})
    base = base.sort_values("Data").reset_index(drop=True)
    return base, avisos


base, avisos = carregar_fluxo()

if base.empty:
    for a in avisos:
        st.warning(a)
    st.warning("⚠️ Nenhum dado de fluxo de caixa disponível.")
    st.stop()

# ==============================================================================
# SIDEBAR — FILTROS
# ==============================================================================
datas = base["Data"].dropna()
d_min, d_max = datas.min().date(), datas.max().date()

with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)

    periodo = st.date_input(
        "Período",
        value=(d_min, d_max),
        min_value=d_min,
        max_value=d_max,
    )
    if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
        dt_ini, dt_fim = periodo[0], periodo[1]
    else:
        dt_ini, dt_fim = d_min, d_max
    if dt_ini > dt_fim:
        dt_ini, dt_fim = dt_fim, dt_ini

    origens_all = sorted(base["Origem"].unique().tolist())
    origem_sel = st.multiselect("Origem", origens_all, default=origens_all, placeholder="Todas")

    classes_all = sorted(base["Classificação"].unique().tolist())
    class_sel = st.multiselect("Classificação FCx", classes_all, placeholder="Todas")

    trans_all = sorted(base["Transação"].unique().tolist())
    trans_sel = st.multiselect("Transação", trans_all, placeholder="Todas")

    if st.button("↻ Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Aplica filtros
mask = (base["Data"] >= pd.Timestamp(dt_ini)) & (base["Data"] <= pd.Timestamp(dt_fim))
df = base[mask].copy()
if origem_sel:
    df = df[df["Origem"].isin(origem_sel)]
if class_sel:
    df = df[df["Classificação"].isin(class_sel)]
if trans_sel:
    df = df[df["Transação"].isin(trans_sel)]

# Período anterior (mesmo nº de dias) para comparativo
n_dias = (pd.Timestamp(dt_fim) - pd.Timestamp(dt_ini)).days + 1
prev_fim = pd.Timestamp(dt_ini) - pd.Timedelta(days=1)
prev_ini = prev_fim - pd.Timedelta(days=n_dias - 1)
df_prev = base[(base["Data"] >= prev_ini) & (base["Data"] <= prev_fim)].copy()
if origem_sel:
    df_prev = df_prev[df_prev["Origem"].isin(origem_sel)]
if class_sel:
    df_prev = df_prev[df_prev["Classificação"].isin(class_sel)]
if trans_sel:
    df_prev = df_prev[df_prev["Transação"].isin(trans_sel)]

# ==============================================================================
# MÉTRICAS
# ==============================================================================
total = float(df["Valor"].sum())
total_prev = float(df_prev["Valor"].sum())
delta_pct = ((total / total_prev) - 1) * 100 if total_prev else (100.0 if total else 0.0)

tot_desp = float(df.loc[df["Origem"] == "Despesas", "Valor"].sum())
tot_bord = float(df.loc[df["Origem"] == "Borderô", "Valor"].sum())
n_lanc = len(df)
n_class = df["Classificação"].nunique()

media_dia = total / n_dias if n_dias else 0.0

# Top classificação
if not df.empty:
    top_class = df.groupby("Classificação")["Valor"].sum().sort_values(ascending=False)
    top_nome = top_class.index[0]
    top_val = float(top_class.iloc[0])
else:
    top_nome, top_val = "—", 0.0

mapa_cores = {}

txt_per = f"{dt_ini:%d/%m/%Y} – {dt_fim:%d/%m/%Y}"
txt_orig = "Todas" if not origem_sel or set(origem_sel) == set(origens_all) else (
    origem_sel[0] if len(origem_sel) == 1 else f"{len(origem_sel)} selecionadas"
)

# ==============================================================================
# CABEÇALHO + KPIs
# ==============================================================================
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>FLUXO DE CAIXA · SAÍDAS OPERACIONAIS</h1>
            <p>Despesas (Base_Despesas) + Pagamentos Borderô (Base_Titulos)</p>
        </div>
        <div class='pills'>
            <div class='pill'><small>Período</small><b>{txt_per}</b></div>
            <div class='pill'><small>Origem</small><b>{txt_orig}</b></div>
            <div class='pill'><small>Lançamentos</small><b>{n_lanc:,}</b></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
for a in avisos:
    st.warning(a)

if total_prev:
    cls_d = "down" if delta_pct > 0 else "up"  # saída ↑ = pior (vermelho)
    seta = "↑" if delta_pct >= 0 else "↓"
    sub_delta = f"<div class='kpi-sub {cls_d}'>{seta} {pct(abs(delta_pct))} vs período anterior</div>"
else:
    sub_delta = "<div class='kpi-sub'>sem período anterior comparável</div>"

kpi_html = f"""
<div class='kpi-grid'>
    <div class='kpi red'>
        <div class='kpi-t'>Total de saídas</div>
        <div class='kpi-v'>{moeda(total)}</div>
        {sub_delta}
    </div>
    <div class='kpi'>
        <div class='kpi-t'>Despesas (Base_Despesas)</div>
        <div class='kpi-v'>{moeda(tot_desp)}</div>
        <div class='kpi-sub'><b>{pct(div(tot_desp, total)*100)}</b> do total</div>
    </div>
    <div class='kpi purple'>
        <div class='kpi-t'>Borderô (Base_Titulos)</div>
        <div class='kpi-v'>{moeda(tot_bord)}</div>
        <div class='kpi-sub'><b>{pct(div(tot_bord, total)*100)}</b> do total</div>
    </div>
    <div class='kpi amber'>
        <div class='kpi-t'>Média diária</div>
        <div class='kpi-v'>{moeda(media_dia)}</div>
        <div class='kpi-sub'>{n_dias} dia(s) no período</div>
    </div>
    <div class='kpi green'>
        <div class='kpi-t'>Maior classificação</div>
        <div class='kpi-v' style='font-size:15px'>{top_nome[:28]}{'…' if len(top_nome)>28 else ''}</div>
        <div class='kpi-sub'>{moeda_curta(top_val)} · {pct(div(top_val, total)*100)}</div>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# ==============================================================================
# LINHA 1 — Evolução + Composição
# ==============================================================================
c1, c2 = st.columns([1.55, 1.0], gap="small")

with c1:
    st.markdown(
        "<div class='section-title' style='margin-top:4px'>Evolução mensal das saídas</div>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.markdown(vazio_html(), unsafe_allow_html=True)
    else:
        por_mes = df.groupby("Ref")["Valor"].sum().sort_index()
        por_mes_d = df[df["Origem"] == "Despesas"].groupby("Ref")["Valor"].sum().reindex(por_mes.index, fill_value=0)
        por_mes_b = df[df["Origem"] == "Borderô"].groupby("Ref")["Valor"].sum().reindex(por_mes.index, fill_value=0)
        x_lab = [rot_mes(m) for m in por_mes.index]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_lab, y=por_mes_d.values, name="Despesas",
            marker_color=AZUL, hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Despesas</extra>",
        ))
        fig.add_trace(go.Bar(
            x=x_lab, y=por_mes_b.values, name="Borderô",
            marker_color=ROXO, hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Borderô</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=x_lab, y=por_mes.values, name="Total",
            mode="lines+markers",
            line=dict(color=VERMELHO, width=2.5), marker=dict(size=7),
            hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Total</extra>",
        ))
        fig.update_layout(barmode="stack", bargap=0.3)
        st.plotly_chart(layout_fig(fig, 300), use_container_width=True, config={"displayModeBar": False})

with c2:
    st.markdown(
        "<div class='section-title' style='margin-top:4px'>Composição por classificação</div>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.markdown(vazio_html(), unsafe_allow_html=True)
    else:
        g = df.groupby("Classificação")["Valor"].sum().sort_values(ascending=False)
        # Agrupa cauda pequena em "Outros" para legibilidade
        if len(g) > 8:
            top = g.head(7)
            outros = g.iloc[7:].sum()
            g = pd.concat([top, pd.Series({"Outros": outros})])
        labels = g.index.tolist()
        cores = [cor_cat(x, mapa_cores) for x in labels]
        fig = go.Figure(go.Pie(
            labels=labels, values=g.values, hole=0.62, sort=False, textinfo="none",
            marker=dict(colors=cores, line=dict(color="#ffffff", width=2)),
            hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        ))
        fig.update_layout(annotations=[dict(
            text=f"<b style='color:#0f172a'>{moeda_curta(total)}</b>"
                 f"<br><span style='font-size:10px;color:#64748b'>Total</span>",
            showarrow=False, font=dict(size=13),
        )])
        st.plotly_chart(layout_fig(fig, 180, False), use_container_width=True, config={"displayModeBar": False})
        leg = "".join(
            f"<div class='leg'><i style='background:{cor_cat(x, mapa_cores)}'></i>"
            f"<span>{x}</span><em>{pct(div(g[x], total)*100)}</em>"
            f"<b>{moeda_curta(g[x])}</b></div>"
            for x in labels
        )
        st.markdown(leg, unsafe_allow_html=True)

# ==============================================================================
# LINHA 2 — Tabelas analíticas
# ==============================================================================
st.markdown("<div class='section-title'>Ranking por classificação FCx</div>", unsafe_allow_html=True)

if df.empty:
    st.markdown(vazio_html(), unsafe_allow_html=True)
else:
    rank = (
        df.groupby("Classificação")
        .agg(Valor=("Valor", "sum"), Qtd=("Valor", "count"))
        .sort_values("Valor", ascending=False)
    )
    rank["%"] = rank["Valor"] / total * 100
    mx = rank["Valor"].max()
    rows = []
    for i, (nome, r) in enumerate(rank.iterrows(), 1):
        rows.append([
            f"<span class='mut'>{i}</span>",
            f"<span class='dot' style='background:{cor_cat(nome, mapa_cores)}'></span>{nome}",
            moeda(r["Valor"]),
            int(r["Qtd"]),
            barra(div(r["Valor"], mx) * 100, cor_cat(nome, mapa_cores)),
            pct(r["%"]),
        ])
    total_row = ["", "TOTAL", moeda(total), int(rank["Qtd"].sum()), "", "100,0%"]
    st.markdown(
        tabela(["#", "Classificação", "Valor", "Qtd", "", "%"], rows, total_row, altura=360),
        unsafe_allow_html=True,
    )

# Matriz Classificação × Mês
st.markdown("<div class='section-title'>Classificação × mês</div>", unsafe_allow_html=True)

if df.empty:
    st.markdown(vazio_html(), unsafe_allow_html=True)
else:
    mat = df.pivot_table(
        index="Classificação", columns="Ref", values="Valor",
        aggfunc="sum", fill_value=0.0,
    )
    refs = sorted(mat.columns)
    mat = mat.reindex(columns=refs, fill_value=0.0)
    mat["__total__"] = mat.sum(axis=1)
    mat = mat.sort_values("__total__", ascending=False)
    x_lab = [rot_mes(m) for m in refs]

    rows = []
    for nome, r in mat.iterrows():
        rows.append(
            [f"<span class='dot' style='background:{cor_cat(nome, mapa_cores)}'></span>{nome}"]
            + [moeda(r[m]) if abs(r[m]) > 0.005 else "—" for m in refs]
            + [f"<b>{moeda(r['__total__'])}</b>"]
        )
    tot_cols = [moeda(mat[m].sum()) for m in refs] + [moeda(mat["__total__"].sum())]
    total_row = ["TOTAL"] + tot_cols
    st.markdown(
        tabela(["Classificação"] + x_lab + ["Total"], rows, total_row, altura=400),
        unsafe_allow_html=True,
    )

# Por origem / transação
l1, l2 = st.columns(2, gap="small")

with l1:
    st.markdown("<div class='section-title' style='margin-top:4px'>Por origem</div>", unsafe_allow_html=True)
    if df.empty:
        st.markdown(vazio_html(), unsafe_allow_html=True)
    else:
        g = df.groupby("Origem").agg(Valor=("Valor", "sum"), Qtd=("Valor", "count")).sort_values("Valor", ascending=False)
        rows = []
        for nome, r in g.iterrows():
            tag = "origem-desp" if nome == "Despesas" else "origem-bord"
            rows.append([
                f"<span class='origem-tag {tag}'>{nome}</span>",
                moeda(r["Valor"]),
                int(r["Qtd"]),
                pct(div(r["Valor"], total) * 100),
            ])
        st.markdown(
            tabela(["Origem", "Valor", "Qtd", "%"], rows, ["TOTAL", moeda(total), int(g["Qtd"].sum()), "100,0%"], 260),
            unsafe_allow_html=True,
        )

with l2:
    st.markdown("<div class='section-title' style='margin-top:4px'>Por transação</div>", unsafe_allow_html=True)
    if df.empty:
        st.markdown(vazio_html(), unsafe_allow_html=True)
    else:
        g = df.groupby("Transação").agg(Valor=("Valor", "sum"), Qtd=("Valor", "count")).sort_values("Valor", ascending=False)
        mx = g["Valor"].max()
        rows = []
        for i, (nome, r) in enumerate(g.iterrows(), 1):
            rows.append([
                f"<span class='mut'>{i}</span>",
                nome,
                moeda(r["Valor"]),
                barra(div(r["Valor"], mx) * 100, AZUL),
                pct(div(r["Valor"], total) * 100),
            ])
        st.markdown(
            tabela(["#", "Transação", "Valor", "", "%"], rows, None, 260),
            unsafe_allow_html=True,
        )

# Detalhamento diário / lançamentos
st.markdown("<div class='section-title'>Detalhamento de lançamentos</div>", unsafe_allow_html=True)

if df.empty:
    st.markdown(vazio_html(), unsafe_allow_html=True)
else:
    det = df.sort_values("Data", ascending=False).head(500)
    rows = []
    for _, r in det.iterrows():
        tag = "origem-desp" if r["Origem"] == "Despesas" else "origem-bord"
        rows.append([
            r["Data"].strftime("%d/%m/%Y"),
            f"<span class='origem-tag {tag}'>{r['Origem']}</span>",
            r["Transação"],
            r["Classificação"],
            moeda(r["Valor"]),
        ])
    st.markdown(
        tabela(["Data", "Origem", "Transação", "Classificação", "Valor"], rows, None, 440),
        unsafe_allow_html=True,
    )
    if len(df) > 500:
        st.caption(f"Exibindo os 500 lançamentos mais recentes de {len(df):,} no período.")

# ==============================================================================
# RODAPÉ SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown(
        f"<div class='side-card'><small>Período selecionado</small><b>{txt_per}</b></div>"
        f"<div class='side-card'><small>Total filtrado</small><b>{moeda(total)}</b></div>"
        f"<div class='side-card'><small>Última atualização</small><b>{datetime.now():%d/%m/%Y %H:%M}</b></div>",
        unsafe_allow_html=True,
    )
