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
from datetime import datetime

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
SURFACE = "#ffffff"

ESPACO_ENTRE_BLOCOS = "1.0rem"
AJUSTE_APOS_KPIS = "1.0rem"

ABA_DESPESAS = "Base_Despesas"
ABA_BORDERO = "Fluxo_Despesas_Borderô"
ABA_RECEITA = "Fluxo_Receita"

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

CORES_CAT = [
    AZUL, VERDE, AMBAR, ROXO, LARANJA, CIANO, ROSA, VERMELHO,
    "#0ea5e9", "#84cc16", "#f43f5e", "#a855f7", "#14b8a6", "#eab308",
]

MESES_MAP = {
    "jan": 1, "janeiro": 1,
    "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3, "março": 3,
    "abr": 4, "abril": 4,
    "mai": 5, "maio": 5,
    "jun": 6, "junho": 6,
    "jul": 7, "julho": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "setembro": 9,
    "out": 10, "outubro": 10,
    "nov": 11, "novembro": 11,
    "dez": 12, "dezembro": 12,
}
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

    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: __KPI_GAP__; }
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


def parse_mes_header(h, ano_ref=None):
    """Interpreta cabeçalho de mês (Jan, Janeiro, Jan/25, 01/2025, etc.)."""
    if h is None or (isinstance(h, float) and pd.isna(h)):
        return None
    if isinstance(h, (pd.Timestamp, datetime)):
        return pd.Timestamp(h.year, h.month, 1)
    if isinstance(h, (int, float)) and not isinstance(h, bool):
        n = float(h)
        if 1 <= n <= 12:
            ano = ano_ref or datetime.now().year
            return pd.Timestamp(ano, int(n), 1)
        if 20000 < n < 80000:
            d = pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
            return pd.Timestamp(d.year, d.month, 1)
    t = normalizar(h)
    if not t or t in ("nan", "none", "total", "soma", "geral"):
        return None
    # jan/25, jan-2025, janeiro 2025
    m = re.match(r"^([a-z]{3,9})[\s\-/._]*(\d{2,4})?$", t)
    if m and m.group(1)[:3] in MESES_MAP or (m and m.group(1) in MESES_MAP):
        chave = m.group(1) if m.group(1) in MESES_MAP else m.group(1)[:3]
        mes = MESES_MAP.get(chave) or MESES_MAP.get(m.group(1)[:3])
        if mes:
            ano = ano_ref or datetime.now().year
            if m.group(2):
                ano = int(m.group(2))
                if ano < 100:
                    ano += 2000
            return pd.Timestamp(ano, mes, 1)
    m = re.match(r"^(\d{1,2})[\s\-/._]+(\d{2,4})$", t)
    if m:
        mes = int(m.group(1))
        ano = int(m.group(2))
        if ano < 100:
            ano += 2000
        if 1 <= mes <= 12:
            return pd.Timestamp(ano, mes, 1)
    if t in MESES_MAP:
        return pd.Timestamp(ano_ref or datetime.now().year, MESES_MAP[t], 1)
    if t[:3] in MESES_MAP:
        return pd.Timestamp(ano_ref or datetime.now().year, MESES_MAP[t[:3]], 1)
    return None


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
    idx = ord(letra.upper()) - ord("A")
    if 0 <= idx < len(df.columns):
        return df.columns[idx]
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


def detectar_ano(raw):
    """Tenta achar um ano nas primeiras células da planilha."""
    try:
        for i in range(min(5, len(raw))):
            for j in range(min(8, len(raw.columns))):
                t = normalizar(raw.iloc[i, j])
                m = re.search(r"(20\d{2})", t)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return datetime.now().year


def melt_matriz(raw, col_label_idx, header_row_idx, start_col_idx, tipo, ano_ref=None):
    """
    Converte matriz (rótulo em coluna fixa + meses nas colunas) em formato longo.
    header_row_idx / col indices são 0-based no DataFrame lido.
    """
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["Ref", "Categoria", "Valor", "Tipo"])

    ano = ano_ref or detectar_ano(raw)
    df = raw.copy()
    df.columns = [str(c).strip() if c is not None else f"col_{i}" for i, c in enumerate(df.columns)]

    # Se a primeira linha ainda não for header de mês, usa a linha indicada como header
    if header_row_idx > 0 and header_row_idx < len(df):
        novos = list(df.iloc[header_row_idx].values)
        # mantém nome da coluna de rótulo
        if col_label_idx < len(novos):
            novos[col_label_idx] = df.columns[col_label_idx] if col_label_idx < len(df.columns) else "Categoria"
        df.columns = [str(x).strip() if pd.notna(x) else f"col_{i}" for i, x in enumerate(novos)]
        df = df.iloc[header_row_idx + 1:].reset_index(drop=True)

    col_label = df.columns[col_label_idx] if col_label_idx < len(df.columns) else df.columns[0]

    # Mapeia colunas de mês a partir de start_col_idx
    mapa_mes = {}
    for j, c in enumerate(df.columns):
        if j < start_col_idx:
            continue
        ref = parse_mes_header(c, ano)
        if ref is not None:
            mapa_mes[c] = ref

    # Fallback: se não achou meses no header, tenta posições C..N como Jan..Dez
    if not mapa_mes and len(df.columns) > start_col_idx:
        for k, j in enumerate(range(start_col_idx, min(start_col_idx + 12, len(df.columns)))):
            mapa_mes[df.columns[j]] = pd.Timestamp(ano, k + 1, 1)

    if not mapa_mes:
        return pd.DataFrame(columns=["Ref", "Categoria", "Valor", "Tipo"])

    partes = []
    for c, ref in mapa_mes.items():
        tmp = pd.DataFrame({
            "Categoria": df[col_label].fillna("").astype(str).str.strip(),
            "Valor": df[c].apply(limpa_valor),
            "Ref": ref,
            "Tipo": tipo,
        })
        partes.append(tmp)

    out = pd.concat(partes, ignore_index=True)
    out = out[out["Categoria"].map(normalizar).isin(["", "nan", "none", "total", "total geral", "soma"]) == False]
    out = out[out["Valor"].abs() > 0.005].copy()
    return out[["Ref", "Categoria", "Valor", "Tipo"]]


# ==============================================================================
# CARGA
# ==============================================================================
@st.cache_data(ttl=60, show_spinner="Carregando fluxo de caixa…")
def carregar_fluxo():
    """
    Saídas:
      - Base_Despesas (transações filtradas) → agregado por mês e classificação
      - Fluxo_Despesas_Borderô → matriz Conta Contábil × mês
    Entradas:
      - Fluxo_Receita → matriz Origem Receita × mês
    """
    cols = ["Ref", "Categoria", "Valor", "Tipo", "Grupo"]
    vazio = pd.DataFrame(columns=cols)
    avisos = []
    conn = conectar_sheets()
    if conn is None:
        return vazio, ["Conexão com o Google Sheets indisponível."]

    partes = []

    # ---- Base_Despesas (saídas por classificação) ----
    try:
        raw_d = conn.read(worksheet=ABA_DESPESAS, ttl=0)
    except Exception as e:
        raw_d = None
        avisos.append(f"Não foi possível ler despesas operacionais: {e}")

    if raw_d is not None and not raw_d.empty:
        df = raw_d.copy()
        c_data = col_por_letra(df, "B") or col_por_nomes(df, ["Data", "Data Lançamento", "Dt"])
        c_trans = col_por_letra(df, "D") or col_por_nomes(df, ["Transação FCx", "Transacao FCx", "Transação", "Transacao"])
        c_clas = col_por_letra(df, "E") or col_por_nomes(df, ["Classificação FCx", "Classificacao FCx", "Classificação", "Classificacao"])
        c_val = col_por_letra(df, "F") or col_por_nomes(df, ["Vl Débito", "Vl Debito", "Valor Débito", "Valor Debito", "Débito", "Debito", "Valor"])

        if all([c_data, c_trans, c_clas, c_val]):
            tmp = pd.DataFrame({
                "Data": df[c_data].apply(parse_data),
                "Transação": df[c_trans].fillna("").astype(str).str.strip(),
                "Categoria": df[c_clas].fillna("(Sem classificação)").astype(str).str.strip(),
                "Valor": df[c_val].apply(limpa_valor),
            })
            tmp = tmp[tmp["Transação"].map(normalizar).isin(TRANSACOES_DESPESAS)]
            tmp = tmp[tmp["Data"].notna() & (tmp["Valor"].abs() > 0.005)]
            if not tmp.empty:
                tmp["Ref"] = tmp["Data"].apply(lambda d: pd.Timestamp(d.year, d.month, 1))
                g = tmp.groupby(["Ref", "Categoria"], as_index=False)["Valor"].sum()
                g["Tipo"] = "Saída"
                g["Grupo"] = "Despesas"
                partes.append(g[cols])
        else:
            avisos.append("Despesas operacionais: estrutura de colunas não reconhecida.")

    # ---- Fluxo_Despesas_Borderô (matriz) ----
    # Col B = Conta Contábil; linha 3 (idx 2) = meses a partir da col C (idx 2)
    try:
        raw_b = conn.read(worksheet=ABA_BORDERO, ttl=0)
    except Exception as e:
        raw_b = None
        avisos.append(f"Não foi possível ler borderô de despesas: {e}")

    if raw_b is not None and not raw_b.empty:
        # header na linha 3 → index 2; rótulo col B → index 1; meses desde col C → index 2
        mb = melt_matriz(raw_b, col_label_idx=1, header_row_idx=2, start_col_idx=2, tipo="Saída")
        if mb.empty:
            # tenta header já na primeira linha
            mb = melt_matriz(raw_b, col_label_idx=1, header_row_idx=0, start_col_idx=2, tipo="Saída")
        if not mb.empty:
            mb["Grupo"] = "Borderô"
            partes.append(mb.rename(columns={})[list(mb.columns) + (["Grupo"] if "Grupo" not in mb.columns else [])])
            # garante colunas
            mb = mb.copy()
            mb["Grupo"] = "Borderô"
            partes[-1] = mb[["Ref", "Categoria", "Valor", "Tipo", "Grupo"]]
        else:
            avisos.append("Borderô de despesas: nenhum valor mensal encontrado.")

    # ---- Fluxo_Receita (matriz) ----
    # Col A = Origem Receita; linha 2 (idx 1) = meses a partir da col B (idx 1)
    try:
        raw_r = conn.read(worksheet=ABA_RECEITA, ttl=0)
    except Exception as e:
        raw_r = None
        avisos.append(f"Não foi possível ler receitas: {e}")

    if raw_r is not None and not raw_r.empty:
        mr = melt_matriz(raw_r, col_label_idx=0, header_row_idx=1, start_col_idx=1, tipo="Entrada")
        if mr.empty:
            mr = melt_matriz(raw_r, col_label_idx=0, header_row_idx=0, start_col_idx=1, tipo="Entrada")
        if not mr.empty:
            mr = mr.copy()
            mr["Grupo"] = "Receita"
            partes.append(mr[["Ref", "Categoria", "Valor", "Tipo", "Grupo"]])
        else:
            avisos.append("Receitas: nenhum valor mensal encontrado.")

    if not partes:
        return vazio, avisos or ["Nenhum lançamento encontrado."]

    base = pd.concat(partes, ignore_index=True)
    base["Categoria"] = base["Categoria"].replace({"": "(Sem classificação)", "nan": "(Sem classificação)"})
    base = base.groupby(["Ref", "Categoria", "Tipo", "Grupo"], as_index=False)["Valor"].sum()
    base = base.sort_values(["Ref", "Tipo", "Categoria"]).reset_index(drop=True)
    return base, avisos


base, avisos = carregar_fluxo()

if base.empty:
    for a in avisos:
        st.warning(a)
    st.warning("⚠️ Nenhum dado de fluxo de caixa disponível.")
    st.stop()

# ==============================================================================
# SIDEBAR
# ==============================================================================
meses_all = sorted(base["Ref"].unique())
rot = {m: rot_mes(m) for m in meses_all}

with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)
    c_a, c_b = st.columns(2)
    ini = c_a.selectbox("De", meses_all, index=0, format_func=rot.get)
    fim = c_b.selectbox("Até", meses_all, index=len(meses_all) - 1, format_func=rot.get)

    grupos_all = sorted(base["Grupo"].unique().tolist())
    grupo_sel = st.multiselect("Grupo", grupos_all, default=grupos_all, placeholder="Todos")

    cats_all = sorted(base["Categoria"].unique().tolist())
    cat_sel = st.multiselect("Classificação / Origem", cats_all, placeholder="Todas")

    if st.button("↻ Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if ini > fim:
    ini, fim = fim, ini
refs_sel = [m for m in meses_all if ini <= m <= fim]
n_ref = len(refs_sel)
i0 = meses_all.index(refs_sel[0]) if refs_sel else 0
refs_prev = meses_all[max(0, i0 - n_ref):i0] if n_ref else []

df = base[base["Ref"].isin(refs_sel)].copy()
if grupo_sel:
    df = df[df["Grupo"].isin(grupo_sel)]
if cat_sel:
    df = df[df["Categoria"].isin(cat_sel)]

df_prev = base[base["Ref"].isin(refs_prev)].copy()
if grupo_sel:
    df_prev = df_prev[df_prev["Grupo"].isin(grupo_sel)]
if cat_sel:
    df_prev = df_prev[df_prev["Categoria"].isin(cat_sel)]

# ==============================================================================
# MÉTRICAS
# ==============================================================================
ent = float(df.loc[df["Tipo"] == "Entrada", "Valor"].sum())
sai = float(df.loc[df["Tipo"] == "Saída", "Valor"].sum())
liq = ent - sai

ent_p = float(df_prev.loc[df_prev["Tipo"] == "Entrada", "Valor"].sum())
sai_p = float(df_prev.loc[df_prev["Tipo"] == "Saída", "Valor"].sum())
liq_p = ent_p - sai_p

def delta_sub(atual, ant, invert=False):
    """invert=True: aumento é ruim (saídas)."""
    if not ant:
        return "<div class='kpi-sub'>sem período anterior</div>"
    v = (atual / ant - 1) * 100
    if invert:
        cls, seta = ("down", "↑") if v >= 0 else ("up", "↓")
    else:
        cls, seta = ("up", "↑") if v >= 0 else ("down", "↓")
    return f"<div class='kpi-sub {cls}'>{seta} {pct(abs(v))} vs período anterior</div>"

mapa_cores = {}
txt_per = f"{rot[refs_sel[0]]} – {rot[refs_sel[-1]]}" if refs_sel else "—"

# ==============================================================================
# CABEÇALHO + KPIs
# ==============================================================================
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>FLUXO DE CAIXA</h1>
            <p>Receitas × saídas operacionais e borderô</p>
        </div>
        <div class='pills'>
            <div class='pill'><small>Período</small><b>{txt_per}</b></div>
            <div class='pill'><small>Resultado</small><b style="color:{'#059669' if liq>=0 else '#dc2626'}">{moeda_curta(liq)}</b></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
for a in avisos:
    st.warning(a)

kpi_html = f"""
<div class='kpi-grid'>
    <div class='kpi green'>
        <div class='kpi-t'>Receitas</div>
        <div class='kpi-v' style='color:{VERDE}'>{moeda(ent)}</div>
        {delta_sub(ent, ent_p, invert=False)}
    </div>
    <div class='kpi red'>
        <div class='kpi-t'>Saídas totais</div>
        <div class='kpi-v' style='color:{VERMELHO}'>{moeda(sai)}</div>
        {delta_sub(sai, sai_p, invert=True)}
    </div>
    <div class='kpi'>
        <div class='kpi-t'>Despesas operacionais</div>
        <div class='kpi-v'>{moeda(float(df.loc[df['Grupo']=='Despesas','Valor'].sum()))}</div>
        <div class='kpi-sub'><b>{pct(div(float(df.loc[df['Grupo']=='Despesas','Valor'].sum()), sai)*100)}</b> das saídas</div>
    </div>
    <div class='kpi {"green" if liq>=0 else "red"}'>
        <div class='kpi-t'>Resultado líquido</div>
        <div class='kpi-v' style='color:{"#059669" if liq>=0 else "#dc2626"}'>{moeda(liq)}</div>
        {delta_sub(liq, liq_p, invert=False) if (ent_p or sai_p) else "<div class='kpi-sub'>receitas − saídas</div>"}
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# ==============================================================================
# GRÁFICOS
# ==============================================================================
c1, c2 = st.columns([1.55, 1.0], gap="small")

with c1:
    st.markdown(
        "<div class='section-title' style='margin-top:4px'>Evolução mensal · Receitas × Saídas</div>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.markdown(vazio_html(), unsafe_allow_html=True)
    else:
        ent_m = df[df["Tipo"] == "Entrada"].groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0)
        sai_m = df[df["Tipo"] == "Saída"].groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0)
        liq_m = ent_m - sai_m
        x_lab = [rot[m] for m in refs_sel]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_lab, y=ent_m.values, name="Receitas",
            marker_color=VERDE, hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Receitas</extra>",
        ))
        fig.add_trace(go.Bar(
            x=x_lab, y=sai_m.values, name="Saídas",
            marker_color=VERMELHO, hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Saídas</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=x_lab, y=liq_m.values, name="Resultado",
            mode="lines+markers",
            line=dict(color=AZUL, width=2.5), marker=dict(size=7),
            hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>Resultado</extra>",
        ))
        fig.update_layout(barmode="group", bargap=0.25)
        st.plotly_chart(layout_fig(fig, 300), use_container_width=True, config={"displayModeBar": False})

with c2:
    st.markdown(
        "<div class='section-title' style='margin-top:4px'>Composição das saídas</div>",
        unsafe_allow_html=True,
    )
    sai_df = df[df["Tipo"] == "Saída"]
    if sai_df.empty:
        st.markdown(vazio_html("Sem saídas no período"), unsafe_allow_html=True)
    else:
        g = sai_df.groupby("Categoria")["Valor"].sum().sort_values(ascending=False)
        if len(g) > 8:
            top = g.head(7)
            g = pd.concat([top, pd.Series({"Outros": g.iloc[7:].sum()})])
        labels = g.index.tolist()
        cores = [cor_cat(x, mapa_cores) for x in labels]
        fig = go.Figure(go.Pie(
            labels=labels, values=g.values, hole=0.62, sort=False, textinfo="none",
            marker=dict(colors=cores, line=dict(color="#ffffff", width=2)),
            hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        ))
        fig.update_layout(annotations=[dict(
            text=f"<b style='color:#0f172a'>{moeda_curta(sai)}</b>"
                 f"<br><span style='font-size:10px;color:#64748b'>Saídas</span>",
            showarrow=False, font=dict(size=13),
        )])
        st.plotly_chart(layout_fig(fig, 180, False), use_container_width=True, config={"displayModeBar": False})
        leg = "".join(
            f"<div class='leg'><i style='background:{cor_cat(x, mapa_cores)}'></i>"
            f"<span>{x}</span><em>{pct(div(g[x], sai)*100)}</em>"
            f"<b>{moeda_curta(g[x])}</b></div>"
            for x in labels
        )
        st.markdown(leg, unsafe_allow_html=True)

# ==============================================================================
# TABELAS
# ==============================================================================
# Ranking saídas por classificação
st.markdown("<div class='section-title'>Ranking de saídas por classificação</div>", unsafe_allow_html=True)
sai_df = df[df["Tipo"] == "Saída"]
if sai_df.empty:
    st.markdown(vazio_html("Sem saídas no período"), unsafe_allow_html=True)
else:
    rank = (
        sai_df.groupby("Categoria")
        .agg(Valor=("Valor", "sum"))
        .sort_values("Valor", ascending=False)
    )
    rank["%"] = rank["Valor"] / sai * 100
    mx = rank["Valor"].max()
    rows = []
    for i, (nome, r) in enumerate(rank.iterrows(), 1):
        rows.append([
            f"<span class='mut'>{i}</span>",
            f"<span class='dot' style='background:{cor_cat(nome, mapa_cores)}'></span>{nome}",
            moeda(r["Valor"]),
            barra(div(r["Valor"], mx) * 100, cor_cat(nome, mapa_cores)),
            pct(r["%"]),
        ])
    st.markdown(
        tabela(["#", "Classificação", "Valor", "", "%"], rows,
               ["", "TOTAL", moeda(sai), "", "100,0%"], 360),
        unsafe_allow_html=True,
    )

# Ranking receitas
st.markdown("<div class='section-title'>Ranking de receitas por origem</div>", unsafe_allow_html=True)
ent_df = df[df["Tipo"] == "Entrada"]
if ent_df.empty:
    st.markdown(vazio_html("Sem receitas no período"), unsafe_allow_html=True)
else:
    rank = (
        ent_df.groupby("Categoria")
        .agg(Valor=("Valor", "sum"))
        .sort_values("Valor", ascending=False)
    )
    rank["%"] = rank["Valor"] / ent * 100 if ent else 0
    mx = rank["Valor"].max()
    rows = []
    for i, (nome, r) in enumerate(rank.iterrows(), 1):
        rows.append([
            f"<span class='mut'>{i}</span>",
            f"<span class='dot' style='background:{cor_cat(nome, mapa_cores)}'></span>{nome}",
            moeda(r["Valor"]),
            barra(div(r["Valor"], mx) * 100, VERDE),
            pct(r["%"]),
        ])
    st.markdown(
        tabela(["#", "Origem da receita", "Valor", "", "%"], rows,
               ["", "TOTAL", moeda(ent), "", "100,0%"], 320),
        unsafe_allow_html=True,
    )

# Matriz classificação × mês (saídas)
st.markdown("<div class='section-title'>Saídas · classificação × mês</div>", unsafe_allow_html=True)
if sai_df.empty:
    st.markdown(vazio_html("Sem saídas no período"), unsafe_allow_html=True)
else:
    mat = sai_df.pivot_table(index="Categoria", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
    mat = mat.reindex(columns=refs_sel, fill_value=0.0)
    mat["__t__"] = mat.sum(axis=1)
    mat = mat.sort_values("__t__", ascending=False)
    x_lab = [rot[m] for m in refs_sel]
    rows = []
    for nome, r in mat.iterrows():
        rows.append(
            [f"<span class='dot' style='background:{cor_cat(nome, mapa_cores)}'></span>{nome}"]
            + [moeda(r[m]) if abs(r[m]) > 0.005 else "—" for m in refs_sel]
            + [f"<b>{moeda(r['__t__'])}</b>"]
        )
    tot = ["TOTAL"] + [moeda(mat[m].sum()) for m in refs_sel] + [moeda(mat["__t__"].sum())]
    st.markdown(tabela(["Classificação"] + x_lab + ["Total"], rows, tot, 400), unsafe_allow_html=True)

# Matriz receita × mês
st.markdown("<div class='section-title'>Receitas · origem × mês</div>", unsafe_allow_html=True)
if ent_df.empty:
    st.markdown(vazio_html("Sem receitas no período"), unsafe_allow_html=True)
else:
    mat = ent_df.pivot_table(index="Categoria", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
    mat = mat.reindex(columns=refs_sel, fill_value=0.0)
    mat["__t__"] = mat.sum(axis=1)
    mat = mat.sort_values("__t__", ascending=False)
    x_lab = [rot[m] for m in refs_sel]
    rows = []
    for nome, r in mat.iterrows():
        rows.append(
            [f"<span class='dot' style='background:{cor_cat(nome, mapa_cores)}'></span>{nome}"]
            + [moeda(r[m]) if abs(r[m]) > 0.005 else "—" for m in refs_sel]
            + [f"<b>{moeda(r['__t__'])}</b>"]
        )
    tot = ["TOTAL"] + [moeda(mat[m].sum()) for m in refs_sel] + [moeda(mat["__t__"].sum())]
    st.markdown(tabela(["Origem"] + x_lab + ["Total"], rows, tot, 360), unsafe_allow_html=True)

# Resumo mensal consolidado
st.markdown("<div class='section-title'>Resumo mensal consolidado</div>", unsafe_allow_html=True)
if df.empty:
    st.markdown(vazio_html(), unsafe_allow_html=True)
else:
    rows = []
    te = ts = tl = 0.0
    for m in refs_sel:
        e = float(df.loc[(df["Ref"] == m) & (df["Tipo"] == "Entrada"), "Valor"].sum())
        s = float(df.loc[(df["Ref"] == m) & (df["Tipo"] == "Saída"), "Valor"].sum())
        l = e - s
        te += e
        ts += s
        tl += l
        cor_l = VERDE if l >= 0 else VERMELHO
        rows.append([
            rot[m],
            f"<span style='color:{VERDE}'>{moeda(e)}</span>",
            f"<span style='color:{VERMELHO}'>{moeda(s)}</span>",
            f"<span style='color:{cor_l};font-weight:800'>{moeda(l)}</span>",
        ])
    cor_tl = VERDE if tl >= 0 else VERMELHO
    st.markdown(
        tabela(
            ["Mês", "Receitas", "Saídas", "Resultado"],
            rows,
            ["TOTAL", moeda(te), moeda(ts),
             f"<span style='color:{cor_tl}'>{moeda(tl)}</span>"],
            320,
        ),
        unsafe_allow_html=True,
    )

# ==============================================================================
# RODAPÉ SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown(
        f"<div class='side-card'><small>Período</small><b>{txt_per}</b></div>"
        f"<div class='side-card'><small>Receitas</small><b style='color:#059669'>{moeda(ent)}</b></div>"
        f"<div class='side-card'><small>Saídas</small><b style='color:#dc2626'>{moeda(sai)}</b></div>"
        f"<div class='side-card'><small>Última atualização</small><b>{datetime.now():%d/%m/%Y %H:%M}</b></div>",
        unsafe_allow_html=True,
    )
