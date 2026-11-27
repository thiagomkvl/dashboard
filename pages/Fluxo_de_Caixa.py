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

import os
from io import BytesIO
import re
import textwrap
import time
import unicodedata
import calendar
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
# CONFIG
# ==============================================================================
AZUL, VERDE, AMBAR, VERMELHO = "#2563eb", "#059669", "#d97706", "#dc2626"
ROXO, LARANJA, CIANO, ROSA = "#7c3aed", "#ea580c", "#0891b2", "#e11d48"
TXT, MUTED, BORDA = "#0f172a", "#64748b", "#e2e8f0"

ESPACO_ENTRE_BLOCOS = "0.75rem"
AJUSTE_APOS_KPIS = "0.75rem"
ANO_REF = 2026

ABA_DESPESAS = "Base_Despesas"
ABA_BORDERO = "Fluxo_Despesas_Borderô"
ABA_ADIANT = "Fluxo_Adiantamentos"
ABA_RECEITA = "Fluxo_Receita"
ABA_CLASSIF = "Classificacao_FCx"
ABA_SALDO = "Saldo_FCx"
ABA_SALDO_TASY = "Base_Saldo_FCx_Tasy"
ABA_DEVOL = "FCx_Devolução_Adiantamento"
ABA_DEVOL_ALT = "FCx_Devolucao_Adiantamento"
ABA_OBRA = "FCx_Obra"
ABA_EXTRATOS = "Extratos_Bancos"
INICIO_EXTRATOS = pd.Timestamp(2026, 11, 1)


@st.cache_data(ttl=60, show_spinner=False)
def ler_aba_cacheada(nome_aba):
    """Lê cada aba no máximo uma vez por janela de cache e repete em erros 429."""
    ultimo_erro = None
    for tentativa, espera in enumerate((0, 5, 10, 20, 30)):
        if espera:
            time.sleep(espera)
        try:
            conn = conectar_sheets()
            if conn is None:
                raise RuntimeError("Conexão indisponível com Google Sheets.")
            raw = conn.read(worksheet=nome_aba, ttl=0)
            if raw is None:
                return pd.DataFrame()
            return raw
        except Exception as e:
            ultimo_erro = e
            msg = str(e).lower()
            erro_limite = ("429" in msg or "quota exceeded" in msg or
                           "rate_limit_exceeded" in msg or "resource_exhausted" in msg)
            if not erro_limite or tentativa == 4:
                raise
    raise ultimo_erro


FLUXO_OP = "Fluxo de Caixa Operacional"
FLUXO_INV = "Fluxo de Caixa de Investimentos"
FLUXO_FIN = "Fluxo de Caixa de Financiamento"

CLASSIF_VAR_AP = "Variações de Ativos e Passivos"

TRANSACOES_DESPESAS = {
    "despesas administrativas", "despesas financeiras", "despesas judiciais",
    "devolucao adiantamento particular", "honorarios medicos", "iptu",
    "outras despesas", "parcelamento impostos", "pessoal", "pmts",
    "tributos correntes", "juros fornecedor", "seguros", "iof", "tributos s emprestimos",
}

CORES_CAT = [
    AZUL, VERDE, AMBAR, ROXO, LARANJA, CIANO, ROSA, VERMELHO,
    "#0ea5e9", "#84cc16", "#f43f5e", "#a855f7", "#14b8a6", "#eab308",
]

MESES_MAP = {
    "jan": 1, "janeiro": 1, "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3, "março": 3, "abr": 4, "abril": 4,
    "mai": 5, "maio": 5, "jun": 6, "junho": 6,
    "jul": 7, "julho": 7, "ago": 8, "agosto": 8,
    "set": 9, "setembro": 9, "out": 10, "outubro": 10,
    "nov": 11, "novembro": 11, "dez": 12, "dezembro": 12,
}
MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

SKIP_LABELS = {
    "", "nan", "none", "total", "total geral", "soma", "geral",
    "mes", "mês", "origem", "origem receita",
    "conta contabil", "conta contábil", "classificacao", "classificação",
    "transacao", "transação", "sum de vl debito", "sum de vl débito",
    "adiantamento fornecedores - banco total", "adiantamento fornecedores - banco",
    "receitas", "saidas", "saídas",
}
SKIP_HEADER = {
    "total", "total geral", "soma", "geral", "data - mes", "data - mês",
    "sum de vl debito", "sum de vl débito",
}
SECAO_LABELS = {
    "pmts", "captacoes", "captacao", "alugueis", "aluguéis",
    "outras receitas", "convenio", "convênio", "particular",
    "receitas", "saidas", "saídas",
}

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

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #ffffff !important; border: 1px solid #1d4ed8 !important; border-radius: 10px !important;
        font-weight: 700 !important; padding: 0.5rem 0.9rem !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #334155 !important; border: 1px solid #cbd5e1 !important; border-radius: 10px !important;
        font-weight: 600 !important; padding: 0.5rem 0.9rem !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        border-color: #2563eb !important; color: #1e40af !important;
    }
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] > button {
        background: #0f172a !important;
        color: #ffffff !important; border: none !important; border-radius: 10px !important;
        font-weight: 700 !important; padding: 0.55rem 1rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] > button:hover {
        background: #1e293b !important;
    }

    .top {
        display: flex; justify-content: space-between; align-items: center; gap: 16px;
        padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px solid #e2e8f0;
    }
    .top h1 { margin: 0; font-size: 22px; font-weight: 800; color: #0f172a; }
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
        padding: 12px 14px; border-radius: 12px; min-height: 100px;
        background: #ffffff; border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(15,23,42,0.05);
        border-left: 3px solid #2563eb;
    }
    .kpi.green { border-left-color: #059669; }
    .kpi.red { border-left-color: #dc2626; }
    .kpi.amber { border-left-color: #d97706; }
    .kpi.purple { border-left-color: #7c3aed; }
    .kpi.blue { border-left-color: #2563eb; }
    .kpi-t {
        font-size: 10px; font-weight: 800; letter-spacing: 0.4px;
        text-transform: uppercase; color: #64748b;
    }
    .kpi-v {
        font-size: 18px; font-weight: 800; color: #0f172a; margin: 8px 0 4px;
        font-variant-numeric: tabular-nums; white-space: nowrap;
    }
    .kpi-sub { font-size: 11px; color: #64748b; font-weight: 600; }

    .section-title {
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #0f172a; margin: 16px 0 10px; padding-left: 10px; border-left: 3px solid #2563eb;
    }

    .tbl-wrap {
        overflow-x: auto; overflow-y: visible;
        border-radius: 10px; border: 1px solid #e2e8f0; background: #ffffff;
    }
    .tbl { width: 100%; border-collapse: collapse; font-size: 12px; color: #334155; }
    .tbl th {
        background: #f8fafc; color: #64748b; font-weight: 700; font-size: 11px;
        text-align: left; padding: 8px 10px; border-bottom: 1px solid #e2e8f0;
        white-space: nowrap; text-transform: uppercase;
    }
    .tbl td {
        padding: 8px 10px; border-bottom: 1px solid #f1f5f9; white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }
    .tbl tbody tr:hover td { background: #f8fafc; }
    .tbl tr.tot td {
        font-weight: 800; color: #0f172a; background: #f1f5f9; border-top: 1px solid #e2e8f0;
    }
    .tbl tr.sec td {
        font-weight: 800; color: #0f172a; background: #eef2ff;
        border-top: 1px solid #e2e8f0; text-transform: uppercase; font-size: 11px;
    }
    .tbl tr.caixa-total td {
        font-weight: 800; color: #0f172a; background: #cbd5e1;
        border-top: 2px solid #94a3b8; border-bottom: 1px solid #94a3b8;
        text-transform: uppercase; font-size: 11px;
    }
    .tbl tr.subsec td {
        font-weight: 700; color: #334155; background: #f8fafc; font-size: 11px;
    }
    .tbl tr.res td {
        font-weight: 800; background: #f8fafc; border-top: 2px solid #e2e8f0;
    }
    .tbl tr.saldo td {
        font-weight: 800; background: #ecfdf5; border-top: 2px solid #a7f3d0;
    }
    .tbl tr.sub-row td { background: #fafbfc; color: #64748b; font-size: 11px; }
    .tbl tr.sub-row td:first-child { padding-left: 28px; }
    .dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 8px; vertical-align: middle;
    }
    .drill-label {
        cursor: pointer; display: flex; align-items: center; gap: 6px;
        margin: 0; font-weight: 700; color: #0f172a; user-select: none;
    }
    .toggle-checkbox { display: none; }
    .indicator {
        display: inline-block; font-size: 10px; color: #2563eb;
        transition: transform 0.15s ease; width: 12px;
    }
    .grp .sub-row { display: none; }
    .grp:has(.toggle-checkbox:checked) .sub-row { display: table-row; }
    .grp:has(.toggle-checkbox:checked) .indicator { transform: rotate(90deg); }

    .sec-drill-label {
        cursor: pointer; display: inline-flex; align-items: center; gap: 7px;
        margin: 0; font-weight: 800; color: #0f172a; user-select: none;
    }
    .sec-toggle { display: none; }
    .sec-indicator {
        display: inline-block; font-size: 10px; color: #1e40af;
        transition: transform 0.15s ease; width: 12px;
    }
    .tbl:has(#sec_fco:checked) tr.sec-fco { display: none !important; }
    .tbl:has(#sec_fco:checked) #sec_fco + .sec-indicator { transform: rotate(-90deg); }

    .tbl:has(#sec_fci:checked) tr.sec-fci { display: none !important; }
    .tbl:has(#sec_fci:checked) #sec_fci + .sec-indicator { transform: rotate(-90deg); }

    .tbl:has(#sec_fcf:checked) tr.sec-fcf { display: none !important; }
    .tbl:has(#sec_fcf:checked) #sec_fcf + .sec-indicator { transform: rotate(-90deg); }

    .subsec-drill-label {
        cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
        margin: 0; font-weight: 700; color: #334155; user-select: none;
    }
    .subsec-indicator {
        display: inline-block; font-size: 9px; color: #2563eb;
        transition: transform 0.15s ease; width: 11px;
    }
    .tbl:has(#sub_rec_op:checked) tr.sub-rec-op { display: none !important; }
    .tbl:has(#sub_rec_op:checked) #sub_rec_op + .subsec-indicator { transform: rotate(-90deg); }

    .tbl:has(#sub_custo_op:checked) tr.sub-custo-op { display: none !important; }
    .tbl:has(#sub_custo_op:checked) #sub_custo_op + .subsec-indicator { transform: rotate(-90deg); }

    .tbl:has(#sub_imposto:checked) tr.sub-imposto { display: none !important; }
    .tbl:has(#sub_imposto:checked) #sub_imposto + .subsec-indicator { transform: rotate(-90deg); }

    .tbl:has(#sub_var_ap:checked) tr.sub-var-ap { display: none !important; }
    .tbl:has(#sub_var_ap:checked) #sub_var_ap + .subsec-indicator { transform: rotate(-90deg); }
    .vazio { color: #64748b; font-size: 12px; padding: 28px 8px; text-align: center; }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: #1e40af !important; color: #ffffff !important;
        border: 1px solid #1e40af !important; border-radius: 8px !important;
        font-weight: 700 !important; font-size: 12px !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"] {
        background: #ffffff !important; color: #334155 !important;
        border: 1px solid #cbd5e1 !important; border-radius: 8px !important;
        font-weight: 600 !important; font-size: 12px !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        border-color: #2563eb !important; color: #1e40af !important;
    }
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
    s = s.lower().strip()
    s = re.sub(r"[.\-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalizar_chave(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return ""
    s = unicodedata.normalize("NFKD", str(txt)).encode("ASCII", "ignore").decode("utf-8")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


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
    if h is None or (isinstance(h, float) and pd.isna(h)):
        return None
    if isinstance(h, (pd.Timestamp, datetime)):
        return pd.Timestamp(ano_ref or ANO_REF, h.month, 1)
    if isinstance(h, (int, float)) and not isinstance(h, bool):
        val_f = float(h)
        if 2020 <= val_f <= 2050:
            ano = int(val_f)
            mes = int(round((val_f - ano) * 100))
            if 1 <= mes <= 12:
                return pd.Timestamp(ano, mes, 1)
        if 1 <= val_f <= 12:
            return pd.Timestamp(ano_ref or ANO_REF, int(val_f), 1)
        if 20000 < val_f < 80000:
            d = pd.Timestamp("1899-12-30") + pd.Timedelta(days=val_f)
            return pd.Timestamp(ano_ref or ANO_REF, d.month, 1)
    t = normalizar(h)
    if not t or t in SKIP_HEADER or "total" in t:
        return None
    m = re.match(r"^(\d{4})[.\-_/](\d{1,2})$", t)
    if m:
        ano, mes = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12:
            return pd.Timestamp(ano, mes, 1)
    m = re.match(r"^(\d{4})\s+(\d{1,2})$", t)
    if m:
        ano, mes = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12:
            return pd.Timestamp(ano, mes, 1)
    m = re.match(r"^([a-z]{3,9})(?:\s+(\d{2,4}))?$", t)
    if m:
        chave = m.group(1)
        mes = MESES_MAP.get(chave) or MESES_MAP.get(chave[:3])
        if mes:
            ano = ano_ref or ANO_REF
            if m.group(2):
                ano = int(m.group(2))
                if ano < 100:
                    ano += 2000
            return pd.Timestamp(ano, mes, 1)
    m = re.match(r"^(\d{1,2})\s+(\d{2,4})$", t)
    if m:
        mes, ano = int(m.group(1)), int(m.group(2))
        if ano < 100:
            ano += 2000
        if 1 <= mes <= 12:
            return pd.Timestamp(ano, mes, 1)
    return None


def _br(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(v, casas=2):
    if abs(v) < 0.005:
        return "—"
    return "R$ " + _br(v, casas)


def moeda_curta(v):
    a = abs(v)
    if a < 0.005:
        return "—"
    if a >= 1e6:
        return f"R$ {_br(v / 1e6, 1)}M"
    if a >= 1e3:
        return f"R$ {_br(v / 1e3, 1)}K"
    return f"R$ {_br(v, 0)}"


def rot_mes(ts):
    return f"{MESES_ABREV[ts.month - 1]}/{str(ts.year)[2:]}"


def col_por_letra(df, letra):
    idx = ord(letra.upper()) - ord("A")
    if 0 <= idx < len(df.columns):
        return df.columns[idx]
    return None


def col_por_nomes(df, nomes):
    mapa = {normalizar(c): c for c in df.columns}
    for n in nomes:
        if normalizar(n) in mapa:
            return mapa[normalizar(n)]
    return None


def cor_cat(nome, mapa):
    if nome not in mapa:
        mapa[nome] = CORES_CAT[len(mapa) % len(CORES_CAT)]
    return mapa[nome]


def melt_matriz(raw, col_label_idx, header_row_idx, start_col_idx, tipo, ano_ref=None):
    cols_out = ["Ref", "Dia", "Categoria", "Valor", "Tipo", "Detalhe"]
    if raw is None or raw.empty:
        return pd.DataFrame(columns=cols_out)

    ano = ano_ref or ANO_REF
    col_headers = [str(c) if c is not None else "" for c in raw.columns]
    data = [col_headers] + raw.astype(object).where(pd.notna(raw), None).values.tolist()
    n_rows = len(data)
    n_cols = max((len(r) for r in data), default=0)
    if n_cols == 0:
        return pd.DataFrame(columns=cols_out)

    grid = []
    for r in data:
        row = list(r) + [None] * (n_cols - len(r))
        grid.append(row[:n_cols])

    def montar_mapa_mes(header_row):
        m = {}
        for j in range(start_col_idx, n_cols):
            h = header_row[j] if j < len(header_row) else None
            nt = normalizar(h) if h is not None else ""
            if not nt or "total" in nt or nt in SKIP_HEADER:
                continue
            ref = parse_mes_header(h, ano)
            if ref is not None:
                m[j] = ref
        return m

    def score_header(row):
        return len(montar_mapa_mes(row))

    hr0, best_s = 0, score_header(grid[0])
    for i in range(min(8, n_rows)):
        s = score_header(grid[i])
        if s > best_s:
            hr0, best_s = i, s
    if 0 <= header_row_idx < n_rows:
        s_c = score_header(grid[header_row_idx])
        if s_c >= best_s and s_c >= 2:
            hr0 = header_row_idx

    mapa_atual = montar_mapa_mes(grid[hr0])
    if not mapa_atual:
        return pd.DataFrame(columns=cols_out)

    li = col_label_idx if 0 <= col_label_idx < n_cols else 0
    reg = []

    for i in range(hr0 + 1, n_rows):
        row = grid[i]
        s_local = score_header(row)
        if s_local >= 1:
            cat_test = row[li] if li < len(row) else None
            ncat_test = normalizar(cat_test) if cat_test is not None else ""
            parece_cabecalho = (
                not ncat_test
                or ncat_test in ("mes", "mês")
                or ncat_test in SECAO_LABELS
                or ncat_test in SKIP_LABELS
                or parse_mes_header(cat_test, ano) is not None
            )
            if s_local >= 1 and parece_cabecalho:
                novo = montar_mapa_mes(row)
                if novo:
                    mapa_atual = novo
                continue

        cat = row[li] if li < len(row) else None
        if cat is None or (isinstance(cat, float) and pd.isna(cat)):
            continue
        cat_s = str(cat).strip()
        ncat = normalizar(cat_s)
        if not ncat or ncat in SKIP_LABELS or ncat.startswith("total"):
            continue
        if "adiantamento fornecedores" in ncat and "total" in ncat:
            continue

        tem_valor = any(
            abs(limpa_valor(row[j] if j < len(row) else 0)) > 0.005
            for j in mapa_atual
        )
        if ncat in SECAO_LABELS and not tem_valor:
            continue
        if not tem_valor:
            continue

        for j, ref in mapa_atual.items():
            val = limpa_valor(row[j] if j < len(row) else 0)
            if abs(val) <= 0.005:
                continue
            reg.append({"Ref": ref, "Dia": 1, "Categoria": cat_s, "Valor": val, "Tipo": tipo, "Detalhe": cat_s})

    if not reg:
        return pd.DataFrame(columns=cols_out)
    return pd.DataFrame(reg)[cols_out]


def parse_fcx_obra(raw, ano_ref=None):
    cols_out = ["Ref", "Dia", "Categoria", "Valor", "Tipo", "Grupo", "Detalhe"]
    if raw is None or raw.empty:
        return pd.DataFrame(columns=cols_out)

    ano = ano_ref or ANO_REF
    col_headers = [str(c) if c is not None else "" for c in raw.columns]
    data = [col_headers] + raw.astype(object).where(pd.notna(raw), None).values.tolist()
    n_rows = len(data)
    n_cols = max((len(r) for r in data), default=0)
    if n_cols < 3:
        return pd.DataFrame(columns=cols_out)

    grid = []
    for r in data:
        row = list(r) + [None] * (n_cols - len(r))
        grid.append(row[:n_cols])

    def montar_mapa_mes(header_row):
        m = {}
        for j in range(2, n_cols):
            h = header_row[j] if j < len(header_row) else None
            ref = parse_mes_header(h, ano)
            if ref is not None:
                m[j] = ref
        return m

    hr0, best_s = 0, 0
    for i in range(min(8, n_rows)):
        s = len(montar_mapa_mes(grid[i]))
        if s > best_s:
            hr0, best_s = i, s

    mapa_atual = montar_mapa_mes(grid[hr0])
    if not mapa_atual:
        return pd.DataFrame(columns=cols_out)

    reg = []
    current_obra = ""

    for i in range(hr0 + 1, n_rows):
        row = grid[i]
        col0_val = row[0] if len(row) > 0 else None
        col1_val = row[1] if len(row) > 1 else None

        n_col0 = normalizar(col0_val)
        n_col1 = normalizar(col1_val)

        if "total" in n_col0 or "total" in n_col1:
            continue

        if col0_val is not None and str(col0_val).strip() != "":
            current_obra = str(col0_val).strip()

        conta = col1_val if col1_val is not None else col0_val
        if conta is None or (isinstance(conta, float) and pd.isna(conta)):
            continue
        conta_s = str(conta).strip()
        nconta = normalizar(conta_s)
        if not nconta or nconta in SKIP_LABELS or "total" in nconta:
            continue

        for j, ref in mapa_atual.items():
            val = limpa_valor(row[j] if j < len(row) else 0)
            if abs(val) <= 0.005:
                continue

            # 1. Abatimento proporcional no FCO
            reg.append({
                "Ref": ref,
                "Dia": 1,
                "Categoria": conta_s,
                "Valor": -val,
                "Tipo": "Saída",
                "Grupo": "FCx_Obra (Redução FCO)",
                "Detalhe": conta_s,
            })
            # 2. No FCI, cada Obra assume a sua própria categoria principal (ex: Obra: NOME) e detalha a Conta Contábil
            nome_obra = current_obra if current_obra else "Diversas"
            reg.append({
                "Ref": ref,
                "Dia": 1,
                "Categoria": f"Obra: {nome_obra}",
                "Valor": val,
                "Tipo": "Saída",
                "Grupo": f"FCx_Obra - {nome_obra}",
                "Detalhe": conta_s,
            })

    if not reg:
        return pd.DataFrame(columns=cols_out)
    return pd.DataFrame(reg)


def sinal_devolucao(categoria):
    n = normalizar_chave(categoria)
    if "fornecedor" in n or "salarial" in n:
        return 1.0
    if "paciente" in n or "prontuario" in n:
        return -1.0
    if "devolucao" in n:
        return -1.0
    return 1.0


def eh_linha_devolucao(categoria):
    n = normalizar_chave(categoria)
    return "devolucao" in n and (
        "adiantamento" in n or "prontuario" in n or "fornecedor" in n or "paciente" in n
    )


# ==============================================================================
# SALDO INICIAL
# ==============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def carregar_saldo_inicial(ano_ref=None):
    ano = ano_ref or ANO_REF
    out = {}
    try:
        conn = conectar_sheets()
        if conn is None:
            return out
        raw = ler_aba_cacheada(ABA_SALDO)
    except Exception:
        return out

    if raw is None or raw.empty:
        return out

    col_headers = [str(c) if c is not None else "" for c in raw.columns]
    data = [col_headers] + raw.astype(object).where(pd.notna(raw), None).values.tolist()
    n_rows = len(data)
    n_cols = max((len(r) for r in data), default=0)
    if n_cols == 0:
        return out

    grid = []
    for r in data:
        row = list(r) + [None] * (n_cols - len(r))
        grid.append(row[:n_cols])

    def mapa_mes_linha(row, start_j=0):
        m = {}
        for j in range(start_j, n_cols):
            h = row[j] if j < len(row) else None
            nt = normalizar(h) if h is not None else ""
            if not nt or "total" in nt or nt in SKIP_HEADER:
                continue
            ref = parse_mes_header(h, ano)
            if ref is not None:
                m[j] = ref
        return m

    hr, best = 0, 0
    for i in range(min(6, n_rows)):
        s = max(len(mapa_mes_linha(grid[i], 0)), len(mapa_mes_linha(grid[i], 1)))
        if s > best:
            best, hr = s, i
    if best == 0:
        return out

    mapa = mapa_mes_linha(grid[hr], 0)
    if len(mapa) < best:
        mapa = mapa_mes_linha(grid[hr], 1)
    if not mapa:
        return out

    row_saldo = None
    for i in range(hr + 1, min(hr + 8, n_rows)):
        for j in (0, 1):
            if j >= n_cols:
                continue
            lab = normalizar(grid[i][j])
            if "saldo" in lab and "inicial" in lab:
                row_saldo = i
                break
            if lab in ("saldo inicial", "saldo de caixa", "saldo caixa", "caixa inicial"):
                row_saldo = i
                break
        if row_saldo is not None:
            break

    if row_saldo is None and hr + 1 < n_rows:
        row_saldo = hr + 1
    if row_saldo is None:
        return out

    for j, ref in mapa.items():
        val = limpa_valor(grid[row_saldo][j] if j < len(grid[row_saldo]) else 0)
        out[ref] = float(val)
    return out


@st.cache_data(ttl=60, show_spinner=False)
def carregar_saldos_tasy():
    inicial, final, avisos = {}, {}, []
    try:
        conn = conectar_sheets()
        if conn is None:
            return inicial, final, ["Saldo Tasy: conexão indisponível."]
        raw = ler_aba_cacheada(ABA_SALDO_TASY)
        if raw is None or raw.empty:
            return inicial, final, ["Saldo Tasy: aba vazia."]
        grid = [list(raw.columns)] + raw.astype(object).where(pd.notna(raw), None).values.tolist()
        destino, meses = None, {}
        for row in grid:
            label = normalizar(row[0]) if row else ""
            if label in ("saldo inicial", "saldo final"):
                destino = inicial if label == "saldo inicial" else final
                meses = {}
            elif label == "banco" and destino is not None:
                meses = {j: ref for j, h in enumerate(row[1:], 1)
                         if (ref := parse_mes_header(h, ANO_REF)) is not None}
            elif label == "total geral" and destino is not None:
                for j, ref in meses.items():
                    if j < len(row) and row[j] is not None and str(row[j]).strip():
                        destino[ref] = limpa_valor(row[j])
        if not inicial or not final:
            avisos.append("Saldo Tasy: bloco inicial ou final sem totais reconhecidos.")
    except Exception as e:
        avisos.append(f"Saldo Tasy: não foi possível carregar a referência ({e}).")
    return inicial, final, avisos


def consolidar_devolucoes(base):
    base = base.copy()
    mask = base["Categoria"].apply(eh_linha_devolucao)
    dev = base.loc[mask].copy()
    if dev.empty:
        return base
    def natureza(c):
        n = normalizar_chave(c)
        if "fornecedor" in n:
            return "fornecedor"
        if "salarial" in n:
            return "salarial"
        if "prontuario" in n:
            return "prontuario"
        return "paciente"
    dev["Natureza"] = dev["Categoria"].map(natureza)
    especifica = dev[dev["Grupo"] == "Devolução Adiantamento"]
    meses_paciente = set(especifica.loc[especifica["Natureza"].isin(["paciente", "prontuario"]), "Ref"])
    meses_fornecedor = set(especifica.loc[especifica["Natureza"] == "fornecedor", "Ref"])
    meses_salarial = set(especifica.loc[especifica["Natureza"] == "salarial", "Ref"])
    remover = (dev["Grupo"] != "Devolução Adiantamento") & (
        (dev["Natureza"].isin(["paciente", "prontuario"]) & dev["Ref"].isin(meses_paciente)) |
        ((dev["Natureza"] == "fornecedor") & dev["Ref"].isin(meses_fornecedor)) |
        ((dev["Natureza"] == "salarial") & dev["Ref"].isin(meses_salarial)))
    dev = dev.loc[~remover].copy()
    dev["Valor"] = dev.apply(lambda r: abs(float(r["Valor"])) * sinal_devolucao(r["Categoria"]), axis=1)
    dev["Tipo"] = dev["Categoria"].apply(lambda c: "Entrada" if sinal_devolucao(c) > 0 else "Saída")
    dev["Grupo"] = "Devolução Adiantamento"
    return pd.concat([base.loc[~mask], dev[base.columns]], ignore_index=True)


def montar_serie_saldo(refs, s_variacao, mapa_saldo_ini):
    s_ini = pd.Series(0.0, index=refs, dtype=float)
    s_fim = pd.Series(0.0, index=refs, dtype=float)
    prev_fim = None

    for m in refs:
        if m in mapa_saldo_ini:
            ini = float(mapa_saldo_ini[m])
        elif prev_fim is not None:
            ini = float(prev_fim)
        else:
            ant = [k for k in sorted(mapa_saldo_ini.keys()) if k < m]
            ini = float(mapa_saldo_ini[ant[-1]]) if ant else 0.0

        var = float(s_variacao.get(m, 0.0))
        fim = ini + var
        s_ini[m] = ini
        s_fim[m] = fim
        prev_fim = fim

    return s_ini, s_fim


# ==============================================================================
# DE-PARA
# ==============================================================================
def _mapa_de_dataframe(df_map):
    if df_map is None or df_map.empty:
        return {}
    cols = list(df_map.columns)
    c_desc = c_cls = c_flx = None
    for c in cols:
        n = normalizar(c)
        if n in ("descricao", "descrição", "conta contabil", "conta contábil", "categoria"):
            c_desc = c
        if ("classific" in n) and ("fluxo" not in n):
            c_cls = c
        if "fluxo" in n:
            c_flx = c
    if c_desc is None:
        c_desc = cols[0]
    if c_cls is None and len(cols) > 1:
        c_cls = cols[1]
    if c_flx is None and len(cols) > 2:
        c_flx = cols[2]
    if not c_desc or not c_cls:
        return {}

    out = {}
    for _, r in df_map.iterrows():
        d = str(r[c_desc]).strip() if pd.notna(r[c_desc]) else ""
        c = str(r[c_cls]).strip() if pd.notna(r[c_cls]) else ""
        f = str(r[c_flx]).strip() if (c_flx and pd.notna(r[c_flx])) else ""
        nd = normalizar_chave(d)
        if not nd or nd in SKIP_LABELS:
            continue
        if not c or normalizar(c) in SKIP_LABELS:
            continue
        nf = normalizar(f)
        if "invest" in nf:
            fluxo = FLUXO_INV
        elif "financ" in nf:
            fluxo = FLUXO_FIN
        else:
            fluxo = FLUXO_OP
        out[nd] = (c, fluxo)
    return out


@st.cache_data(ttl=120, show_spinner=False)
def carregar_mapa_classificacao():
    try:
        conn = conectar_sheets()
        if conn is not None:
            try:
                raw = ler_aba_cacheada(ABA_CLASSIF)
                m = _mapa_de_dataframe(raw)
                if m:
                    return m
            except Exception:
                pass
    except Exception:
        pass
    for path in [
        "RegraFCx_Ajustado.xlsx",
        "/home/workdir/attachments/RegraFCx_Ajustado.xlsx",
        "Classificacao_FCx_Concluida.xlsx",
    ]:
        if os.path.isfile(path):
            try:
                m = _mapa_de_dataframe(pd.read_excel(path))
                if m:
                    return m
            except Exception:
                continue
    return {}


def eh_juros(nome):
    return "juros" in normalizar_chave(nome)


def eh_juros_fornecedor(nome):
    n = normalizar_chave(nome)
    return "juros" in n and "fornecedor" in n


def eh_juros_financiamento(nome):
    n = normalizar_chave(nome)
    if "juros" not in n or "fornecedor" in n:
        return False
    return any(x in n for x in (
        "emprestimo", "financiament", "banco", "unicred", "encarg",
        "capital de giro", "cdc", "leasing",
    ))


def eh_amortizacao(nome):
    return "amortiza" in normalizar_chave(nome)


def eh_captacao(nome):
    n = normalizar_chave(nome)
    if not n:
        return False
    if "juros" in n or "amortiza" in n or "encargo" in n:
        return False
    if "captacao" in n or "captacoes" in n:
        return True
    if "emprestimo" in n and (
        "banco" in n or "unicred" in n or "bradesc" in n
        or "itau" in n or "santander" in n or "outros" in n
    ):
        return True
    if n.startswith("emprestimo"):
        return True
    return False


def aplicar_classificacao(categoria, mapa):
    n = normalizar_chave(categoria)
    if not n:
        return "Não classificado", FLUXO_OP, categoria

    if eh_linha_devolucao(categoria):
        return CLASSIF_VAR_AP, FLUXO_OP, categoria

    if n in mapa:
        cls, flx = mapa[n]
        return cls, flx, categoria

    cand = []
    for k, (cls, flx) in mapa.items():
        if len(k) >= 6 and (k in n or n in k):
            cand.append((len(k), cls, flx))
    if cand:
        cand.sort(reverse=True)
        return cand[0][1], cand[0][2], categoria

    if eh_captacao(categoria):
        return "Captações", FLUXO_FIN, categoria
    if eh_amortizacao(categoria):
        return "Amortização de Empréstimos", FLUXO_FIN, categoria
    if eh_juros_fornecedor(categoria):
        return "Juros Fornecedor", FLUXO_OP, categoria
    if eh_juros_financiamento(categoria):
        return "Juros e Encargos Financeiros", FLUXO_FIN, categoria
    if eh_juros(categoria):
        return "Juros Fornecedor", FLUXO_OP, categoria

    return "Não classificado", FLUXO_OP, categoria


def eh_receita_aplicacao(classif, categoria=""):
    """Reconhece a classificação específica e contas de rendimentos abreviadas."""
    cls = normalizar_chave(classif)
    conta = normalizar_chave(categoria)
    classe_aplicacao = "aplic" in cls and "financeir" in cls
    rendimento_conta = (
        any(termo in conta for termo in ("rendimento", "receita"))
        and "aplic" in conta and "financeir" in conta
    )
    return classe_aplicacao or rendimento_conta


def papel_classif(classif, fluxo=""):
    n = normalizar(classif)
    nf = normalizar(fluxo)

    if "variacoes de ativos" in n or "variações de ativos" in n or n == normalizar(CLASSIF_VAR_AP):
        return "var_ap"

    if "invest" in nf:
        # A exceção depende da classificação e do fluxo definidos no de-para.
        # Obras continuam sendo CAPEX, mesmo se o nome contiver esses termos.
        if not n.startswith(("obra:", "obra ")) and eh_receita_aplicacao(classif):
            return "receita_inv"
        return "capex"

    if "financ" in nf:
        if "captac" in n or (
            "emprestimo" in n and "amortiza" not in n and "juros" not in n
        ):
            return "captacao"
        if "amortiza" in n:
            return "amortizacao"
        if "juros" in n:
            return "juros"
        return "outros"

    if any(x in n for x in ("alugue", "convenio", "particular", "outras receitas")):
        return "receita_op"
    if "imposto" in n or "tributo" in n:
        return "imposto"
    if "juros" in n:
        if "fornecedor" in n or "operac" in nf:
            return "custo_op"
        if any(x in n for x in ("emprestimo", "banco", "financiament", "encarg")):
            return "juros"
        return "custo_op"
    if "capex" in n or "investimento" in n:
        return "capex"
    if "captac" in n:
        return "captacao"
    if "amortiza" in n:
        return "amortizacao"
    if any(x in n for x in (
        "pessoal", "honorario", "terceiros", "utilidade", "opme",
        "administrativ", "bancari", "outras despesas", "fornecedor", "seguro", "iof",
    )):
        return "custo_op"
    return "outros"


# ==============================================================================
# CARGA
# ==============================================================================
@st.cache_data(ttl=60, show_spinner="Carregando fluxo de caixa…")
def carregar_fluxo_legado():
    cols = ["Ref", "Dia", "Categoria", "Valor", "Tipo", "Grupo", "Detalhe"]
    vazio = pd.DataFrame(columns=cols)
    avisos = []
    conn = conectar_sheets()
    if conn is None:
        return vazio, ["Conexão indisponível."]
    partes = []

    # Base_Despesas
    try:
        raw_d = ler_aba_cacheada(ABA_DESPESAS)
    except Exception as e:
        raw_d = None
        avisos.append(f"Despesas: {e}")
    if raw_d is not None and not raw_d.empty:
        df = raw_d.copy()
        c_data = col_por_letra(df, "B") or col_por_nomes(df, ["Data"])
        c_trans = col_por_letra(df, "D") or col_por_nomes(df, ["Transação FCx", "Transacao FCx"])
        c_clas = col_por_letra(df, "E") or col_por_nomes(df, ["Classificação FCx", "Classificacao FCx"])
        c_val = col_por_letra(df, "F") or col_por_nomes(df, ["Vl Débito", "Vl Debito", "Valor"])
        if all([c_data, c_trans, c_clas, c_val]):
            tmp = pd.DataFrame({
                "Data": df[c_data].apply(parse_data),
                "Transação": df[c_trans].fillna("").astype(str).str.strip(),
                "Categoria": df[c_clas].fillna("(Sem classificação)").astype(str).str.strip(),
                "Valor": df[c_val].apply(limpa_valor),
            })
            devolucoes = tmp["Transação"].map(eh_linha_devolucao)
            permitidas = tmp["Transação"].map(normalizar).isin(TRANSACOES_DESPESAS)
            tmp.loc[devolucoes, "Categoria"] = tmp.loc[devolucoes, "Transação"]
            tmp = tmp[permitidas | devolucoes]
            tmp = tmp[tmp["Data"].notna() & (tmp["Valor"].abs() > 0.005)]
            if not tmp.empty:
                tmp["Ref"] = tmp["Data"].apply(lambda d: pd.Timestamp(d.year, d.month, 1))
                tmp["Dia"] = tmp["Data"].dt.day.astype(int)
                g = tmp.groupby(["Ref", "Dia", "Categoria"], as_index=False)["Valor"].sum()
                g["Tipo"], g["Grupo"] = "Saída", "Despesas"
                g["Detalhe"] = g["Categoria"]
                partes.append(g[cols])

    # Borderô
    try:
        raw_b = ler_aba_cacheada(ABA_BORDERO)
    except Exception as e:
        raw_b = None
        avisos.append(f"Borderô: {e}")
    if raw_b is not None and not raw_b.empty:
        mb = melt_matriz(raw_b, 1, 0, 2, "Saída", ANO_REF)
        if mb.empty:
            mb = melt_matriz(raw_b, 1, 2, 2, "Saída", ANO_REF)
        if not mb.empty:
            mb = mb.copy()
            mb["Grupo"] = "Borderô"
            partes.append(mb[cols])

    # Adiantamentos
    try:
        raw_a = ler_aba_cacheada(ABA_ADIANT)
    except Exception as e:
        raw_a = None
        avisos.append(f"Adiantamentos: {e}")
    if raw_a is not None and not raw_a.empty:
        ma = melt_matriz(raw_a, 1, 0, 2, "Saída", ANO_REF)
        if ma.empty:
            ma = melt_matriz(raw_a, 1, 1, 2, "Saída", ANO_REF)
        if not ma.empty:
            ma = ma.copy()
            ma["Grupo"] = "Adiantamentos"
            partes.append(ma[cols])

    # Receita
    try:
        raw_r = ler_aba_cacheada(ABA_RECEITA)
    except Exception as e:
        raw_r = None
        avisos.append(f"Receita: {e}")
    if raw_r is not None and not raw_r.empty:
        mr = melt_matriz(raw_r, 0, 0, 1, "Entrada", ANO_REF)
        if mr.empty:
            mr = melt_matriz(raw_r, 0, 1, 1, "Entrada", ANO_REF)
        if not mr.empty:
            mr = mr.copy()
            mr["Grupo"] = "Receita"
            partes.append(mr[cols])

    # Devoluções de adiantamento
    raw_dev = None
    for nome_aba in (ABA_DEVOL, ABA_DEVOL_ALT):
        try:
            raw_dev = ler_aba_cacheada(nome_aba)
            if raw_dev is not None and not raw_dev.empty:
                break
        except Exception:
            raw_dev = None
    if raw_dev is not None and not raw_dev.empty:
        md = melt_matriz(raw_dev, 0, 0, 1, "Entrada", ANO_REF)
        if md.empty:
            md = melt_matriz(raw_dev, 1, 0, 2, "Entrada", ANO_REF)
        if md.empty:
            md = melt_matriz(raw_dev, 0, 1, 1, "Entrada", ANO_REF)
        if md.empty:
            md = melt_matriz(raw_dev, 1, 1, 2, "Entrada", ANO_REF)
        if not md.empty:
            md = md.copy()
            md["Valor"] = md.apply(
                lambda r: abs(float(r["Valor"])) * sinal_devolucao(r["Categoria"]),
                axis=1,
            )
            md["Tipo"] = md["Categoria"].apply(
                lambda c: "Entrada" if sinal_devolucao(c) > 0 else "Saída"
            )
            md["Grupo"] = "Devolução Adiantamento"
            partes.append(md[cols])

    # FCx_Obra
    try:
        raw_obra = ler_aba_cacheada(ABA_OBRA)
    except Exception as e:
        raw_obra = None
        avisos.append(f"FCx_Obra: {e}")
    if raw_obra is not None and not raw_obra.empty:
        mobra = parse_fcx_obra(raw_obra, ANO_REF)
        if not mobra.empty:
            partes.append(mobra[cols])

    if not partes:
        return vazio, avisos or ["Nenhum lançamento."]
    
    base_full = pd.concat(partes, ignore_index=True)
    base_full = consolidar_devolucoes(base_full)
    base_full["Categoria"] = base_full["Categoria"].replace({"": "(Sem classificação)", "nan": "(Sem classificação)"})
    
    if "Dia" not in base_full.columns:
        base_full["Dia"] = 1
    base_full["Dia"] = base_full["Dia"].fillna(1).astype(int)
    base_grouped = base_full.groupby(
        ["Ref", "Dia", "Categoria", "Tipo", "Grupo", "Detalhe"],
        as_index=False
    )["Valor"].sum()
    
    return base_grouped.sort_values(["Ref", "Tipo", "Categoria"]).reset_index(drop=True), avisos



def parse_extratos_bancos(raw):
    """Movimentos bancários a partir do corte; sem cruzar as bases antigas."""
    cols = ["Ref", "Dia", "Categoria", "Valor", "Tipo", "Grupo", "Detalhe"]
    avisos, reg = [], []
    if raw is None or raw.empty:
        return pd.DataFrame(columns=cols), ["Extratos_Bancos: aba vazia."]
    campos = {}
    for campo, letra, nomes in (
        ("data", "B", ["Data"]),
        ("debito", "E", ["Vl Débito", "Vl Debito"]),
        ("credito", "F", ["Vl Crédito", "Vl Credito"]),
        ("categoria", "L", ["SubGrupo", "Sub Grupo"]),
        ("obra", "N", ["Obra"]),
        ("operacional", "K", ["Operacional"]),
    ):
        campos[campo] = col_por_nomes(raw, nomes) or col_por_letra(raw, letra)
    if any(campos[k] is None for k in ("data", "debito", "credito", "categoria", "operacional")):
        raise ValueError("Extratos_Bancos: colunas Data (B), Vl Débito (E), "
                         "Vl Crédito (F), Operacional (K) e SubGrupo (L) obrigatórias.")
    invalidas = sem_categoria = 0
    for _, row in raw.iterrows():
        # Lista positiva: transferências internas, vazios e qualquer outra
        # classificação não entram na base nem nos totais do fluxo.
        if normalizar(row[campos["operacional"]]) not in ("operacional", "operacionais"):
            continue
        debito = abs(limpa_valor(row[campos["debito"]]))
        credito = abs(limpa_valor(row[campos["credito"]]))
        if debito == 0 and credito == 0:
            continue
        data = parse_data(row[campos["data"]])
        if pd.isna(data):
            invalidas += 1
            continue
        if data < INICIO_EXTRATOS:
            continue
        categoria = row[campos["categoria"]]
        categoria = str(categoria).strip() if pd.notna(categoria) else ""
        if not categoria:
            sem_categoria += 1
            categoria = "(Sem classificação)"
        obra = row[campos["obra"]] if campos["obra"] is not None else ""
        obra = str(obra).strip() if pd.notna(obra) else ""
        tem_obra = normalizar(obra) not in ("", "nao", "n", "0", "false", "nenhuma", "sem obra", "na", "n a", "nan", "none", "-")
        for valor, tipo in ((debito, "Saída"), (credito, "Entrada")):
            if valor == 0:
                continue
            reg.append({
                "Ref": data.to_period("M").to_timestamp(),
                "Dia": int(data.day),
                "Categoria": f"Obra: {obra}" if tem_obra else categoria,
                "Valor": valor,
                "Tipo": tipo,
                "Grupo": f"FCx_Obra - {obra}" if tem_obra else "Extratos_Bancos",
                "Detalhe": categoria,
            })
    if invalidas:
        avisos.append(f"Extratos_Bancos: {invalidas} linha(s) com movimento e data inválida; corrigir a coluna B.")
    if sem_categoria:
        avisos.append(f"Extratos_Bancos: {sem_categoria} linha(s) sem SubGrupo (L).")
    return pd.DataFrame(reg, columns=cols), avisos


@st.cache_data(ttl=60, show_spinner="Carregando fluxo de caixa…")
def carregar_fluxo():
    # O processamento legado permanece intacto, inclusive devoluções e obras.
    legado, avisos = carregar_fluxo_legado()
    legado = legado.loc[legado["Ref"] < INICIO_EXTRATOS].copy()
    try:
        extratos, avisos_extratos = parse_extratos_bancos(ler_aba_cacheada(ABA_EXTRATOS))
    except Exception as erro:
        st.error(f"Não foi possível carregar os lançamentos a partir de novembro: {erro}")
        st.stop()
    avisos.extend(avisos_extratos)
    base = pd.concat([legado, extratos], ignore_index=True)
    if base.empty:
        return base, avisos
    return base.sort_values(["Ref", "Tipo", "Categoria"]).reset_index(drop=True), avisos


base, avisos = carregar_fluxo()
mapa_cls = carregar_mapa_classificacao()
mapa_saldo = carregar_saldo_inicial(ANO_REF)
mapa_tasy_ini, mapa_tasy_fim, avisos_tasy = carregar_saldos_tasy()
avisos.extend(avisos_tasy)
mapa_saldo.update(mapa_tasy_ini)

if base.empty:
    for a in avisos:
        st.warning(a)
    st.warning("⚠️ Nenhum dado disponível.")
    st.stop()

base = base.copy()

# Separar lançamentos normais de lançamentos vindos de FCx_Obra
mask_obra = base["Grupo"].str.startswith("FCx_Obra -", na=False)

df_normal = base[~mask_obra].copy()
pares = df_normal["Categoria"].apply(lambda c: aplicar_classificacao(c, mapa_cls))
df_normal["Classif"] = pares.apply(lambda x: x[0])
df_normal["Fluxo"] = pares.apply(lambda x: x[1])

# Cada Obra vira sua própria categoria/linha principal no FCI
df_obra = base[mask_obra].copy()
df_obra["Classif"] = df_obra["Categoria"]
df_obra["Fluxo"] = FLUXO_INV

base = pd.concat([df_normal, df_obra], ignore_index=True)

# Agrupa somente os investimentos de CAPEX; preserva receitas do FCI.
mask_receita_inv = (
    (base["Fluxo"] == FLUXO_INV)
    & ~base["Grupo"].str.startswith("FCx_Obra -", na=False)
    & base.apply(lambda r: eh_receita_aplicacao(r["Classif"], r["Categoria"]), axis=1)
)
# Define o nome antes de agrupar CAPEX e de atribuir o papel/sinal financeiro.
base.loc[mask_receita_inv, "Classif"] = "Aplicações Financeiras"
mask_capex_geral = (
    (~base["Grupo"].str.startswith("FCx_Obra -", na=False))
    & (base["Fluxo"] == FLUXO_INV)
    & ~mask_receita_inv
)
base.loc[mask_capex_geral, "Classif"] = "Investimentos / CAPEX"

base["Papel"] = base.apply(lambda r: papel_classif(r["Classif"], r["Fluxo"]), axis=1)

# As fórmulas existentes subtraem custos/CAPEX e somam receitas/variações.
# Converte a direção bancária para essa convenção apenas no novo período.
mask_extratos = base["Ref"] >= INICIO_EXTRATOS
mask_soma = base["Papel"].isin(["receita_op", "receita_inv", "captacao", "var_ap", "outros"])
mask_entrada = base["Tipo"] == "Entrada"
base.loc[mask_extratos, "Valor"] = base.loc[mask_extratos, "Valor"].abs() * (
    (mask_soma == mask_entrada).loc[mask_extratos].map({True: 1.0, False: -1.0})
)
# Créditos em contas de captação também entram nas fórmulas que filtram Entrada;
# débitos na mesma conta representam a reversão da captação.
base.loc[mask_extratos & (base["Papel"] == "captacao"), "Tipo"] = "Entrada"


from modules.ajustes_fcx import carregar_ajustes, linhas_dashboard, ativos
try:
    conn_ajustes = conectar_sheets()
    if conn_ajustes is None:
        raise RuntimeError("Conexão indisponível para consultar os ajustes aprovados.")
    ledger_ajustes = carregar_ajustes(conn_ajustes)
    base_ajustes = linhas_dashboard(ledger_ajustes)
except Exception as erro_ajustes:
    st.error(f"Não foi possível validar os ajustes aprovados: {erro_ajustes}")
    st.stop()
if not base_ajustes.empty:
    if "Dia" not in base_ajustes.columns:
        base_ajustes = base_ajustes.copy()
        base_ajustes["Dia"] = 1
    base = pd.concat([base, base_ajustes], ignore_index=True)
if "Dia" not in base.columns:
    base["Dia"] = 1
base["Dia"] = base["Dia"].fillna(1).astype(int)

# ==============================================================================
# SIDEBAR
# ==============================================================================
meses_all = sorted(base["Ref"].unique())
rot = {m: rot_mes(m) for m in meses_all}

if "visao_fcx" not in st.session_state:
    st.session_state["visao_fcx"] = "resumida"
if "visao_fcx_ver" not in st.session_state:
    st.session_state["visao_fcx_ver"] = 0

with st.sidebar:
    st.markdown("<div class='side-sec'>Período</div>", unsafe_allow_html=True)
    c_a, c_b = st.columns(2)
    ini = c_a.selectbox("De", meses_all, index=0, format_func=rot.get)
    fim = c_b.selectbox("Até", meses_all, index=len(meses_all) - 1, format_func=rot.get)

    st.markdown("<div class='side-sec' style='margin-top:12px;'>Visão</div>", unsafe_allow_html=True)
    if st.button(
        "Visão Resumida",
        key="btn_visao_resumida",
        type="primary" if st.session_state["visao_fcx"] == "resumida" else "secondary",
        use_container_width=True,
    ):
        st.session_state["visao_fcx"] = "resumida"
        st.session_state["visao_fcx_ver"] += 1
        st.rerun()
    if st.button(
        "Visão Analítica",
        key="btn_visao_analitica",
        type="primary" if st.session_state["visao_fcx"] == "analitica" else "secondary",
        use_container_width=True,
    ):
        st.session_state["visao_fcx"] = "analitica"
        st.session_state["visao_fcx_ver"] += 1
        st.rerun()

grupo_sel = []

if ini > fim:
    ini, fim = fim, ini
refs_sel = [m for m in meses_all if ini <= m <= fim]
df = base[base["Ref"].isin(refs_sel)].copy()
if grupo_sel:
    df = df[df["Grupo"].isin(grupo_sel)]

df_captacao = df[(df["Papel"] == "captacao") & (df["Tipo"] == "Entrada")].copy()
df_juros = df[df["Papel"] == "juros"].copy()
df_amort = df[df["Papel"] == "amortizacao"].copy()
df_var_ap = df[df["Papel"] == "var_ap"].copy()

# ==============================================================================
# FÓRMULAS
# ==============================================================================
def total_papel(d, papel, tipo=None):
    m = d["Papel"] == papel
    if tipo:
        m = m & (d["Tipo"] == tipo)
    return float(d.loc[m, "Valor"].sum())


rec_op = total_papel(df, "receita_op")
custo_op = total_papel(df, "custo_op")
impostos = total_papel(df, "imposto")
var_ap = total_papel(df, "var_ap")
capex = total_papel(df, "capex")
rec_inv = total_papel(df, "receita_inv")
amort = total_papel(df, "amortizacao")
juros = total_papel(df, "juros")
captacao = total_papel(df, "captacao", tipo="Entrada")

fco = rec_op - custo_op - impostos + var_ap
fci = rec_inv - capex
fcf = captacao - amort - juros
variacao = fco + fci + fcf

mapa_cores = {}
txt_per = f"{rot[refs_sel[0]]} – {rot[refs_sel[-1]]}" if refs_sel else "—"
x_lab = [rot[m] for m in refs_sel]

# ==============================================================================
# UI
# ==============================================================================
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>FLUXO DE CAIXA</h1>
            <p>Visão gerencial · FCO · FCI · FCF · Saldo de caixa · {ANO_REF}</p>
        </div>
        <div class='pills'>
            <div class='pill'><small>Período</small><b>{txt_per}</b></div>
            <div class='pill'><small>Variação líquida</small>
                <b style="color:{'#059669' if variacao>=0 else '#dc2626'}">{moeda_curta(variacao)}</b></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
for a in avisos:
    st.warning(a)
if not mapa_saldo:
    st.info("ℹ️ Aba **Saldo_FCx** sem saldo inicial detectado — o saldo começará em zero e rolará pela variação.")


def serie(d, papel, sinal=1.0, tipo=None):
    x = d[d["Papel"] == papel]
    if tipo:
        x = x[x["Tipo"] == tipo]
    s = x.groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0.0)
    return s * sinal


s_rec = serie(df, "receita_op")
s_cus = serie(df, "custo_op")
s_imp = serie(df, "imposto")
s_vap = serie(df, "var_ap")
s_fco = s_rec - s_cus - s_imp + s_vap
s_cap = serie(df, "capex")
s_rec_inv = serie(df, "receita_inv")
s_fci = s_rec_inv - s_cap
s_cpt = serie(df, "captacao", tipo="Entrada")
s_amo = serie(df, "amortizacao")
s_jur = serie(df, "juros")
s_fcf = s_cpt - s_amo - s_jur
s_var = s_fco + s_fci + s_fcf

refs_calculo = list(pd.date_range(min(meses_all), max(refs_sel), freq="MS")) if refs_sel else []
s_var_completo = (base.assign(_sinal=base.apply(
    lambda r: float(r["Valor"]) * (1 if r["Papel"] in ("receita_op", "receita_inv", "captacao", "var_ap") else -1)
    if r["Papel"] != "outros" else 0.0, axis=1))
    .groupby("Ref")["_sinal"].sum())
s_var_completo.update(s_var)
s_ini_full, s_fim_full = montar_serie_saldo(refs_calculo, s_var_completo, mapa_saldo)
s_ini, s_fim = s_ini_full.reindex(refs_sel), s_fim_full.reindex(refs_sel)
s_tasy = pd.Series({m: mapa_tasy_fim.get(m, float("nan")) for m in refs_sel}, dtype=float)
s_diferenca = s_fim - s_tasy
saldo_fim_periodo = float(s_fim.iloc[-1]) if len(s_fim) else 0.0
saldo_ini_periodo = float(s_ini.iloc[0]) if len(s_ini) else 0.0

hoje_ref = pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None).normalize()
mes_corrente_ref = pd.Timestamp(hoje_ref.year, hoje_ref.month, 1)
dia_corte_atual = int(hoje_ref.day)


def serie_ate_dia(d, papel, dia_max, tipo=None):
    x = d[(d["Papel"] == papel) & (d["Dia"] <= dia_max)]
    if tipo:
        x = x[x["Tipo"] == tipo]
    return x.groupby("Ref")["Valor"].sum()


def calcular_var_pct_series(base_completa, refs_tabela):
    papeis_config = {
        "fco": [("receita_op", 1.0, None), ("custo_op", -1.0, None), ("imposto", -1.0, None), ("var_ap", 1.0, None)],
        "rec": [("receita_op", 1.0, None)],
        "cus": [("custo_op", 1.0, None)],
        "imp": [("imposto", 1.0, None)],
        "vap": [("var_ap", 1.0, None)],
        "fci": [("receita_inv", 1.0, None), ("capex", -1.0, None)],
        "rec_inv": [("receita_inv", 1.0, None)],
        "capex": [("capex", 1.0, None)],
        "fcf": [("captacao", 1.0, "Entrada"), ("amortizacao", -1.0, None), ("juros", -1.0, None)],
        "cpt": [("captacao", 1.0, "Entrada")],
        "amo_jur": [("amortizacao", 1.0, None), ("juros", 1.0, None)],
    }
    pcts = {k: {} for k in list(papeis_config.keys()) + ["var"]}
    refs_disponiveis = set(base_completa["Ref"])

    for m in refs_tabela:
        m_ant = (m - pd.DateOffset(months=1)).replace(day=1)
        if m_ant not in refs_disponiveis:
            for k in pcts:
                pcts[k][m] = None
            continue

        if m == mes_corrente_ref:
            ult_dia_ant = calendar.monthrange(m_ant.year, m_ant.month)[1]
            corte_atual = dia_corte_atual
            corte_ant = min(dia_corte_atual, ult_dia_ant)
        else:
            corte_atual = 31
            corte_ant = 31

        vals_atual = {}
        vals_ant = {}
        for chave, itens in papeis_config.items():
            tot_at = 0.0
            tot_an = 0.0
            for papel, sinal, tipo in itens:
                tot_at += float(serie_ate_dia(base_completa, papel, corte_atual, tipo).get(m, 0.0)) * sinal
                tot_an += float(serie_ate_dia(base_completa, papel, corte_ant, tipo).get(m_ant, 0.0)) * sinal
            if chave == "capex":
                tot_at, tot_an = abs(tot_at), abs(tot_an)
            vals_atual[chave] = tot_at
            vals_ant[chave] = tot_an

        vals_atual["var"] = vals_atual["fco"] + vals_atual["fci"] + vals_atual["fcf"]
        vals_ant["var"] = vals_ant["fco"] + vals_ant["fci"] + vals_ant["fcf"]

        for chave in pcts:
            v_at = vals_atual[chave]
            v_an = vals_ant[chave]
            if abs(v_an) < 0.01:
                pcts[chave][m] = None
            else:
                pcts[chave][m] = ((v_at - v_an) / abs(v_an)) * 100.0

    return pcts


var_pcts = calcular_var_pct_series(base, refs_sel)

def entradas_saidas_resumo(dados, papeis, referencias):
    """Calcula Entradas e Saídas do resumo espelhando o demonstrativo detalhado."""
    entradas_idx = pd.Series(0.0, index=referencias, dtype=float)
    saidas_idx = pd.Series(0.0, index=referencias, dtype=float)
    if dados.empty:
        return entradas_idx, saidas_idx

    # Caso específico do FCF:
    # - (+) Entrada = apenas captações de entrada (mesma base de df_captacao / s_cpt)
    # - (−) Saída   = amortizações + juros/encargos financeiros (compensados no detalhe)
    if set(papeis) == {"captacao", "amortizacao", "juros"}:
        d_cap = dados[(dados["Papel"] == "captacao") & (dados["Tipo"] == "Entrada")]
        if not d_cap.empty:
            liq_cap = d_cap.groupby(["Ref", "Categoria", "Detalhe"])["Valor"].sum()
            entradas_idx = liq_cap.clip(lower=0).groupby(level="Ref").sum().reindex(referencias, fill_value=0.0)
            estornos_cap = (-liq_cap.clip(upper=0)).groupby(level="Ref").sum().reindex(referencias, fill_value=0.0)
        else:
            estornos_cap = pd.Series(0.0, index=referencias, dtype=float)

        d_enc = dados[dados["Papel"].isin(["amortizacao", "juros"])]
        if not d_enc.empty:
            liq_enc = d_enc.groupby(["Ref", "Papel", "Categoria", "Detalhe"])["Valor"].sum()
            saidas_enc = liq_enc.clip(lower=0).groupby(level="Ref").sum().reindex(referencias, fill_value=0.0)
            estornos_enc = (-liq_enc.clip(upper=0)).groupby(level="Ref").sum().reindex(referencias, fill_value=0.0)
        else:
            saidas_enc = pd.Series(0.0, index=referencias, dtype=float)
            estornos_enc = pd.Series(0.0, index=referencias, dtype=float)

        entradas_tot = (entradas_idx + estornos_enc).clip(lower=0.0)
        saidas_tot = (saidas_enc + estornos_cap).clip(lower=0.0)
        return entradas_tot, saidas_tot

    movimentos = dados[dados["Papel"].isin(papeis)].copy()
    movimentos = movimentos[(movimentos["Papel"] != "captacao") | (movimentos["Tipo"] == "Entrada")]
    movimentos["Caixa"] = movimentos["Valor"] * movimentos["Papel"].map(
        lambda papel: 1.0 if papel in ("receita_op", "receita_inv", "captacao", "var_ap") else -1.0
    )
    liquidos = movimentos.groupby(["Ref", "Papel", "Categoria", "Detalhe"])["Caixa"].sum()
    entradas = liquidos.clip(lower=0).groupby(level="Ref").sum().reindex(referencias, fill_value=0.0)
    saidas = (-liquidos.clip(upper=0)).groupby(level="Ref").sum().reindex(referencias, fill_value=0.0)
    return entradas, saidas


# ==============================================================================
# EXPORTAÇÃO EXCEL — utiliza os mesmos dados, filtros e séries do dashboard.
# Requer a dependência: xlsxwriter
# ==============================================================================
def gerar_excel_fluxo():
    import xlsxwriter

    buffer = BytesIO()
    wb = xlsxwriter.Workbook(buffer, {"in_memory": True})
    wb.set_properties({"title": "Fluxo de Caixa", "subject": txt_per})
    moeda_xls = '#,##0.00;[Red](#,##0.00);–'
    fmt_titulo = wb.add_format({"bold": True, "font_size": 17, "font_color": "#FFFFFF", "bg_color": "#1E40AF", "valign": "vcenter"})
    fmt_subtitulo = wb.add_format({"font_color": "#64748B", "italic": True})
    fmt_header = wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#334155", "border": 0, "valign": "vcenter"})
    fmt_section = wb.add_format({"bold": True, "bg_color": "#DBEAFE", "font_color": "#1E3A8A"})
    fmt_total_txt = wb.add_format({"bold": True, "bg_color": "#E2E8F0"})
    fmt_total_val = wb.add_format({"bold": True, "bg_color": "#E2E8F0", "num_format": moeda_xls})
    fmt_text = wb.add_format({"font_color": "#334155"})
    fmt_num = wb.add_format({"num_format": moeda_xls, "font_color": "#334155"})
    fmt_date = wb.add_format({"num_format": "dd/mm/yyyy"})
    fmt_detail = wb.add_format({"font_color": "#64748B", "indent": 1})
    fmt_detail_num = wb.add_format({"font_color": "#64748B", "num_format": moeda_xls})

    demonstrativo = wb.add_worksheet("Demonstrativo")
    resumo_ws = wb.add_worksheet("Resumo")
    lancamentos = wb.add_worksheet("Lançamentos")
    ncols = len(refs_sel) + 2

    def iniciar(ws):
        ws.hide_gridlines(2)
        ws.set_column(0, 0, 54)
        ws.set_column(1, ncols - 1, 17)
        ws.merge_range(0, 0, 0, ncols - 1, "FLUXO DE CAIXA", fmt_titulo)
        ws.set_row(0, 30)
        ws.write(1, 0, "Período: " + txt_per, fmt_subtitulo)
        ws.write(2, 0, "Valores em R$ · Filtros de grupo: " + (", ".join(grupo_sel) if grupo_sel else "Todos"), fmt_subtitulo)
        for col, label in enumerate(["Descrição"] + x_lab + ["Total"]):
            ws.write(4, col, label, fmt_header)
        ws.freeze_panes(5, 1)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.repeat_rows(4)
        ws.set_header("&CFluxo de Caixa")
        ws.set_footer("&CPágina &P de &N")
        return 5

    def escrever_linha(ws, pos, nome, valores=None, kind="normal", saldo=False):
        if kind == "section":
            ws.merge_range(pos, 0, pos, ncols - 1, nome, fmt_section)
            return pos + 1
        dados = [float(valores.get(m, 0.0)) if pd.notna(valores.get(m, 0.0)) else None for m in refs_sel]
        txt_fmt = fmt_total_txt if kind == "total" else fmt_detail if kind == "detail" else fmt_text
        num_fmt = fmt_total_val if kind == "total" else fmt_detail_num if kind == "detail" else fmt_num
        ws.write(pos, 0, nome, txt_fmt)
        for col, val in enumerate(dados, 1):
            if val is None:
                ws.write_blank(pos, col, None, num_fmt)
            else:
                ws.write_number(pos, col, val, num_fmt)
        if saldo:
            total = next((v for v in (dados if "inicial" in nome.lower() else reversed(dados)) if v is not None), None)
        else:
            total = sum(v for v in dados if v is not None)
        if total is not None:
            ws.write_number(pos, ncols - 1, total, num_fmt)
        return pos + 1

    def categorias(ws, pos, dados, exibir_abs=False):
        if dados.empty:
            return pos
        detalhes = dados.groupby(["Classif", "Detalhe", "Ref"], as_index=False)["Valor"].sum()
        if exibir_abs:
            detalhes["Valor"] = detalhes["Valor"].abs()
        piv = detalhes.pivot_table(index="Classif", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
        piv = piv.reindex(columns=refs_sel, fill_value=0.0)
        for classe in piv.sum(axis=1).sort_values(ascending=False).index:
            pos = escrever_linha(ws, pos, str(classe), piv.loc[classe])
            det_classe = detalhes[detalhes["Classif"] == classe]
            nomes = det_classe["Detalhe"].dropna().unique()
            if len(nomes) > 1 or (len(nomes) == 1 and normalizar_chave(nomes[0]) != normalizar_chave(classe)):
                sub = det_classe.pivot_table(index="Detalhe", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
                sub = sub.reindex(columns=refs_sel, fill_value=0.0)
                for detalhe in sub.sum(axis=1).sort_values(ascending=False).index:
                    pos = escrever_linha(ws, pos, "↳ " + str(detalhe), sub.loc[detalhe], "detail")
        return pos

    pos = iniciar(demonstrativo)
    pos = escrever_linha(demonstrativo, pos, "1. FLUXO DE CAIXA OPERACIONAL (FCO)", s_fco, "total")
    for titulo, papel, serie_val in (
        ("(+) Receitas operacionais", "receita_op", s_rec),
        ("(−) Custos e despesas operacionais", "custo_op", s_cus),
        ("(−) Impostos", "imposto", s_imp),
        ("(±) Variações de Ativos e Passivos", "var_ap", s_vap),
    ):
        pos = escrever_linha(demonstrativo, pos, titulo, serie_val, "total")
        pos = categorias(demonstrativo, pos, df[df["Papel"] == papel])
    pos = escrever_linha(demonstrativo, pos, "2. FLUXO DE CAIXA DE INVESTIMENTOS (FCI)", s_fci, "total")
    if not df[df["Papel"] == "receita_inv"].empty:
        pos = escrever_linha(demonstrativo, pos, "(+) Receitas de aplicações financeiras", s_rec_inv, "total")
        pos = categorias(demonstrativo, pos, df[df["Papel"] == "receita_inv"])
    pos = escrever_linha(demonstrativo, pos, "(−) Desembolsos em CAPEX", s_cap.abs(), "total")
    pos = categorias(demonstrativo, pos, df[df["Papel"] == "capex"], exibir_abs=True)
    pos = escrever_linha(demonstrativo, pos, "3. FLUXO DE CAIXA DE FINANCIAMENTO (FCF)", s_fcf, "total")
    pos = escrever_linha(demonstrativo, pos, "(+) Empréstimos e Financiamentos", s_cpt, "total")
    pos = categorias(demonstrativo, pos, df_captacao)
    pos = categorias(demonstrativo, pos, df_amort)
    pos = categorias(demonstrativo, pos, df_juros)
    pos = escrever_linha(demonstrativo, pos, "Total amortizações e juros/encargos financeiros", s_amo + s_jur, "total")
    pos = escrever_linha(demonstrativo, pos, "VARIAÇÃO LÍQUIDA DE CAIXA (FCO + FCI + FCF)", s_var, "total")
    pos = escrever_linha(demonstrativo, pos, "4. SALDO DE CAIXA", kind="section")
    for titulo, sv, saldo in (
        ("(+) Saldo inicial", s_ini, True),
        ("(+) Variação líquida do mês", s_var, False),
        ("(=) Saldo final de caixa", s_fim, True),
        ("Saldo Tasy", s_tasy, True),
        ("Diferença: fluxo − Tasy", s_diferenca, True),
    ):
        pos = escrever_linha(demonstrativo, pos, titulo, sv, "total", saldo=saldo)
    if not df[df["Papel"] == "outros"].empty:
        pos = escrever_linha(demonstrativo, pos, "ITENS SEM CLASSIFICAÇÃO GERENCIAL", kind="section")
        pos = categorias(demonstrativo, pos, df[df["Papel"] == "outros"])
    demonstrativo.autofilter(4, 0, pos - 1, ncols - 1)

    pos = iniciar(resumo_ws)
    pos = escrever_linha(resumo_ws, pos, "(+) Saldo inicial", s_ini, "total", saldo=True)
    for titulo, papeis, sv in (
        ("1- (=) FCO", ["receita_op", "custo_op", "imposto", "var_ap"], s_fco),
        ("2- (=) FCI", ["receita_inv", "capex"], s_fci),
        ("3- (=) FCF", ["captacao", "amortizacao", "juros"], s_fcf),
    ):
        pos = escrever_linha(resumo_ws, pos, titulo, sv, "total")
        entradas, saidas = entradas_saidas_resumo(df, papeis, refs_sel)
        pos = escrever_linha(resumo_ws, pos, "(+) Entrada", entradas)
        pos = escrever_linha(resumo_ws, pos, "(−) Saída", saidas)
    pos = escrever_linha(resumo_ws, pos, "(=) Saldo final", s_fim, "total", saldo=True)

    lancamentos.hide_gridlines(2)
    campos = ["Mês", "Categoria", "Classificação", "Fluxo", "Papel", "Tipo", "Grupo", "Detalhe", "Valor (R$)"]
    for j, nome in enumerate(campos):
        lancamentos.write(0, j, nome, fmt_header)
    lancamentos.set_column(0, 0, 13)
    lancamentos.set_column(1, 3, 30)
    lancamentos.set_column(4, 6, 22)
    lancamentos.set_column(7, 7, 34)
    lancamentos.set_column(8, 8, 19, fmt_num)
    lancamentos.freeze_panes(1, 0)
    for i, (_, linha) in enumerate(df.sort_values(["Ref", "Fluxo", "Classif", "Categoria"]).iterrows(), 1):
        lancamentos.write_datetime(i, 0, pd.Timestamp(linha["Ref"]).to_pydatetime(), fmt_date)
        for j, campo in enumerate(["Categoria", "Classif", "Fluxo", "Papel", "Tipo", "Grupo", "Detalhe"], 1):
            lancamentos.write_string(i, j, str(linha.get(campo, "") or ""))
        lancamentos.write_number(i, 8, float(linha["Valor"]), fmt_num)
    if not df.empty:
        lancamentos.autofilter(0, 0, len(df), 8)
    wb.close()
    buffer.seek(0)
    return buffer.getvalue()


st.markdown(
    f"""
<div class='kpi-grid'>
    <div class='kpi green'>
        <div class='kpi-t'>FCO · Operacional</div>
        <div class='kpi-v' style='color:{"#059669" if fco>=0 else "#dc2626"}'>{moeda(fco)}</div>
        <div class='kpi-sub'>Rec. − Custos − Imp. ± Var. A/P</div>
    </div>
    <div class='kpi amber'>
        <div class='kpi-t'>FCI · Investimentos</div>
        <div class='kpi-v' style='color:{"#059669" if fci>=0 else "#dc2626"}'>{moeda(fci)}</div>
        <div class='kpi-sub'>Receitas {moeda_curta(rec_inv)} − CAPEX {moeda_curta(capex)}</div>
    </div>
    <div class='kpi purple'>
        <div class='kpi-t'>FCF · Financiamento</div>
        <div class='kpi-v' style='color:{"#059669" if fcf>=0 else "#dc2626"}'>{moeda(fcf)}</div>
        <div class='kpi-sub'>Captações {moeda_curta(captacao)} − Amort. − Juros</div>
    </div>
    <div class='kpi {"green" if variacao>=0 else "red"}'>
        <div class='kpi-t'>Variação líquida de caixa</div>
        <div class='kpi-v' style='color:{"#059669" if variacao>=0 else "#dc2626"}'>{moeda(variacao)}</div>
        <div class='kpi-sub'>FCO + FCI + FCF</div>
    </div>
    <div class='kpi blue'>
        <div class='kpi-t'>Saldo final de caixa</div>
        <div class='kpi-v' style='color:{"#059669" if saldo_fim_periodo>=0 else "#dc2626"}'>{moeda(saldo_fim_periodo)}</div>
        <div class='kpi-sub'>Ini. {moeda_curta(saldo_ini_periodo)} + var. período</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

info_mtd = f" · % vs. mês anterior (mês atual comparado até dia {dia_corte_atual:02d})" if mes_corrente_ref in refs_sel else " · % vs. mês anterior"
st.markdown(
    f"<div class='section-title'>Demonstrativo · FCO / FCI / FCF · Saldo de caixa{info_mtd} · clique nos títulos, subgrupos ou setas para recolher/expandir</div>",
    unsafe_allow_html=True,
)

esta_resumido = st.session_state["visao_fcx"] == "resumida"
_v_ui = st.session_state["visao_fcx_ver"]


def linhas_df(x, titulo, uid_prefix, exibir_abs=False):
    rows = []
    if x.empty:
        return rows
    # Em CAPEX, primeiro compensamos valores positivos e negativos da mesma
    # classificação/conta no mês; só depois exibimos a magnitude positiva.
    # Aplicar abs() em cada lançamento antes da soma transformava abatimentos
    # da FCx_Obra em novos desembolsos e inflava a linha Investimentos / CAPEX.
    x = x.copy()
    if titulo:
        rows.append(
            f"<tr class='subsec'><td>{titulo}</td>"
            + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
        )
    det = x.groupby(["Classif", "Detalhe", "Ref"], as_index=False)["Valor"].sum()
    if exibir_abs:
        # Compensa no nível do detalhe/conta contábil antes de somar a linha
        # principal. Assim a parcela alocada à obra abate a mesma conta, sem
        # virar um desembolso positivo nem compensar contas diferentes.
        det_visual = det.copy()
        det_visual["Valor"] = det_visual["Valor"].abs()
        piv = det_visual.pivot_table(index="Classif", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
    else:
        piv = x.pivot_table(index="Classif", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
    piv = piv.reindex(columns=refs_sel, fill_value=0.0)
    piv["__t__"] = piv.sum(axis=1)
    piv = piv.sort_values("__t__", ascending=False)
    uid = 0
    for classif, r in piv.iterrows():
        uid += 1
        key = f"{uid_prefix}_{uid}"
        cor = cor_cat(classif, mapa_cores)
        sub = det[det["Classif"] == classif]
        tem = sub["Detalhe"].nunique() > 1 or (
            sub["Detalhe"].nunique() == 1
            and normalizar_chave(sub["Detalhe"].iloc[0]) != normalizar_chave(classif)
        )
        if tem:
            label = (
                f"<label class='drill-label' for='{key}'>"
                f"<input type='checkbox' id='{key}' class='toggle-checkbox'>"
                f"<span class='indicator'>▶</span>"
                f"<span class='dot' style='background:{cor}'></span>{classif}</label>"
            )
        else:
            label = f"<span class='dot' style='background:{cor}'></span>{classif}"
        cells = [moeda(r[m]) for m in refs_sel] + [f"<b>{moeda(r['__t__'])}</b>"]
        if tem:
            rows.append(
                f"<tbody class='grp'><tr><td>{label}</td>"
                + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
            )
            ps = sub.pivot_table(index="Detalhe", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
            ps = ps.reindex(columns=refs_sel, fill_value=0.0)
            if exibir_abs:
                ps = ps.abs()
            ps["__t__"] = ps.sum(axis=1)
            ps = ps.sort_values("__t__", ascending=False)
            for dn, rd in ps.iterrows():
                sc = [moeda(rd[m]) for m in refs_sel] + [f"<b>{moeda(rd['__t__'])}</b>"]
                rows.append(
                    f"<tr class='sub-row'><td>↳ {dn}</td>"
                    + "".join(f"<td>{c}</td>" for c in sc) + "</tr>"
                )
            rows.append("</tbody>")
        else:
            rows.append(f"<tr><td>{label}</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return rows


def badge_pct(pct, inverter_cor=False, ref_mes=None):
    if pct is None or pd.isna(pct):
        return ""
    positivo = pct >= 0
    bom = (not positivo) if inverter_cor else positivo
    cor_b = VERDE if bom else VERMELHO
    seta = "▲" if positivo else "▼"
    sinal = "+" if positivo else ""
    sufixo_mtd = f" (até dia {dia_corte_atual:02d})" if ref_mes == mes_corrente_ref else ""
    return (
        f"<div style='font-size:10px;font-weight:700;color:{cor_b};margin-top:2px;line-height:1.15;' "
        f"title='Variação vs. mesmo período do mês anterior{sufixo_mtd}'>"
        f"{seta} {sinal}{_br(pct, 1)}%</div>"
    )


def linha_tot(label, s, cor, cls="tot", pct_map=None, inverter_cor=False):
    def fmt(v):
        return "—" if pd.isna(v) else moeda(float(v))
    def resolver_cor(v):
        if cls == "caixa-total" or cor == "dinamico":
            if pd.isna(v) or abs(float(v)) < 0.005:
                return TXT
            return VERMELHO if float(v) < 0 else VERDE
        return cor
    tot_val = float(s.iloc[0] if label == "(+) Saldo inicial" else s.iloc[-1]) if len(s) else 0.0
    if cls == "saldo":
        tot_html = f"<td><span style='color:{resolver_cor(tot_val)}'><b>{fmt(tot_val)}</b></span></td>"
    else:
        tot_sum = float(s.sum())
        tot_html = f"<td><span style='color:{resolver_cor(tot_sum)}'><b>{moeda(tot_sum)}</b></span></td>"
    return (
        f"<tr class='{cls}'><td><b>{label}</b></td>"
        + "".join(
            f"<td><span style='color:{resolver_cor(s.get(m, float('nan')))}'>{fmt(s.get(m, float('nan')))}</span>"
            f"{badge_pct(pct_map.get(m) if pct_map else None, inverter_cor=inverter_cor, ref_mes=m)}</td>"
            for m in refs_sel
        )
        + tot_html
        + "</tr>"
    )




if df.empty:
    st.markdown("<div class='vazio'>Sem dados no período</div>", unsafe_allow_html=True)
else:
    html = []

    def marcar_secao(linhas_html, classe_sec):
        out = []
        for item in linhas_html:
            item_mod = re.sub(
                r"<tr class='([^']*)'",
                lambda m: f"<tr class='{m.group(1)} {classe_sec}'",
                item,
            )
            item_mod = re.sub(
                r"<tr>",
                f"<tr class='{classe_sec}'>",
                item_mod,
            )
            out.append(item_mod)
        return out

    def cabecalho_total(label, valores, sec_id, recolhido=True, pct_map=None):
        def fmt(v):
            return "—" if pd.isna(v) else moeda(float(v))
        def cor_val(v):
            if pd.isna(v) or abs(float(v)) < 0.005:
                return TXT
            return VERMELHO if float(v) < 0 else VERDE
        tot_s = float(valores.sum())
        chk_attr = " checked" if recolhido else ""
        label_html = (
            f"<label class='sec-drill-label' for='{sec_id}'>"
            f"<input type='checkbox' id='{sec_id}' class='sec-toggle'{chk_attr}>"
            f"<span class='sec-indicator'>▼</span>"
            f"<span>{label}</span></label>"
        )
        return (
            f"<tr class='caixa-total'><td>{label_html}</td>"
            + "".join(
                f"<td><span style='color:{cor_val(valores.get(m, float('nan')))}'>{fmt(valores.get(m, float('nan')))}</span>"
                f"{badge_pct(pct_map.get(m) if pct_map else None, inverter_cor=False, ref_mes=m)}</td>"
                for m in refs_sel
            )
            + f"<td><span style='color:{cor_val(tot_s)}'><b>{moeda(tot_s)}</b></span></td>"
            + "</tr>"
        )

    def linha_subsec_recolhivel(label, s, cor, sub_id, recolhido=False, pct_map=None, inverter_cor=False):
        def fmt(v):
            return "—" if pd.isna(v) else moeda(float(v))
        def resolver_cor(v):
            if cor == "dinamico":
                if pd.isna(v) or abs(float(v)) < 0.005:
                    return TXT
                return VERMELHO if float(v) < 0 else VERDE
            return cor
        tot_sum = float(s.sum())
        chk_attr = " checked" if recolhido else ""
        label_html = (
            f"<label class='subsec-drill-label' for='{sub_id}'>"
            f"<input type='checkbox' id='{sub_id}' class='sec-toggle'{chk_attr}>"
            f"<span class='subsec-indicator'>▼</span>"
            f"<b>{label}</b></label>"
        )
        return (
            f"<tr class='subsec'><td>{label_html}</td>"
            + "".join(
                f"<td><span style='color:{resolver_cor(s.get(m, float('nan')))}'>{fmt(s.get(m, float('nan')))}</span>"
                f"{badge_pct(pct_map.get(m) if pct_map else None, inverter_cor=inverter_cor, ref_mes=m)}</td>"
                for m in refs_sel
            )
            + f"<td><span style='color:{resolver_cor(tot_sum)}'><b>{moeda(tot_sum)}</b></span></td>"
            + "</tr>"
        )

    def bloco_total(buf, dados, label, valores, cor, uid, exibir_abs=False, sub_id=None, sub_cls=None, pct_map=None, inverter_cor=False):
        if sub_id and sub_cls:
            buf.append(linha_subsec_recolhivel(label, valores, cor, sub_id, recolhido=False, pct_map=pct_map, inverter_cor=inverter_cor))
            filhas = linhas_df(dados, None, uid, exibir_abs=exibir_abs)
            buf.extend(marcar_secao(filhas, sub_cls))
        else:
            buf.append(linha_tot(label, valores, cor, cls="subsec", pct_map=pct_map, inverter_cor=inverter_cor))
            buf.extend(linhas_df(dados, None, uid, exibir_abs=exibir_abs))

    # 1. FCO (recolhível ao clicar no título ou pelo botão Visão Resumida/Analítica)
    html.append(cabecalho_total("1. FLUXO DE CAIXA OPERACIONAL (FCO)", s_fco, "sec_fco", recolhido=esta_resumido, pct_map=var_pcts["fco"]))
    fco_rows = []
    bloco_total(
        fco_rows, df[df["Papel"] == "receita_op"], "(+) Receitas operacionais", s_rec, VERDE, f"r_{_v_ui}",
        sub_id="sub_rec_op", sub_cls="sub-rec-op", pct_map=var_pcts["rec"]
    )
    bloco_total(
        fco_rows, df[df["Papel"] == "custo_op"], "(−) Custos e despesas operacionais", s_cus, VERMELHO, f"c_{_v_ui}",
        sub_id="sub_custo_op", sub_cls="sub-custo-op", pct_map=var_pcts["cus"]
    )
    bloco_total(
        fco_rows, df[df["Papel"] == "imposto"], "(−) Impostos", s_imp, VERMELHO, f"i_{_v_ui}",
        sub_id="sub_imposto", sub_cls="sub-imposto", pct_map=var_pcts["imp"]
    )
    bloco_total(
        fco_rows, df_var_ap, "(±) Variações de Ativos e Passivos", s_vap, "dinamico", f"v_{_v_ui}",
        sub_id="sub_var_ap", sub_cls="sub-var-ap", pct_map=var_pcts["vap"]
    )
    html.extend(marcar_secao(fco_rows, "sec-fco"))

    # 2. FCI (recolhível ao clicar no título ou pelo botão Visão Resumida/Analítica)
    html.append(cabecalho_total("2. FLUXO DE CAIXA DE INVESTIMENTOS (FCI)", s_fci, "sec_fci", recolhido=esta_resumido, pct_map=var_pcts["fci"]))
    fci_rows = []
    df_receitas_inv = df[df["Papel"] == "receita_inv"].copy()
    if not df_receitas_inv.empty:
        bloco_total(fci_rows, df_receitas_inv, "(+) Receitas de aplicações financeiras", s_rec_inv, VERDE, f"ri_{_v_ui}", pct_map=var_pcts["rec_inv"])
    df_capex = df[df["Papel"] == "capex"].copy()
    s_capex_visual = s_cap.abs().reindex(refs_sel, fill_value=0.0)
    bloco_total(fci_rows, df_capex, "(−) Desembolsos em CAPEX", s_capex_visual, VERMELHO, f"k_{_v_ui}", exibir_abs=True, pct_map=var_pcts["capex"], inverter_cor=True)
    html.extend(marcar_secao(fci_rows, "sec-fci"))

    # 3. FCF (recolhível ao clicar no título ou pelo botão Visão Resumida/Analítica)
    html.append(cabecalho_total("3. FLUXO DE CAIXA DE FINANCIAMENTO (FCF)", s_fcf, "sec_fcf", recolhido=esta_resumido, pct_map=var_pcts["fcf"]))
    fcf_rows = []
    bloco_total(fcf_rows, df_captacao, "(+) Empréstimos e Financiamentos", s_cpt, VERDE, f"p_{_v_ui}", pct_map=var_pcts["cpt"])
    fcf_rows.extend(linhas_df(df_amort, None, f"a_{_v_ui}"))
    fcf_rows.extend(linhas_df(df_juros, None, f"j_{_v_ui}"))
    fcf_rows.append(linha_tot("Total amortizações e juros/encargos financeiros", s_amo + s_jur, VERMELHO, pct_map=var_pcts["amo_jur"], inverter_cor=True))
    html.extend(marcar_secao(fcf_rows, "sec-fcf"))

    html.append(
        "<tr class='res'><td><b>VARIAÇÃO LÍQUIDA DE CAIXA (FCO + FCI + FCF)</b></td>"
        + "".join(
            f"<td><span style='color:{VERDE if float(s_var.get(m, 0)) >= 0 else VERMELHO};font-weight:800'>"
            f"{moeda(float(s_var.get(m, 0)))}</span>"
            f"{badge_pct(var_pcts['var'].get(m), inverter_cor=False, ref_mes=m)}</td>"
            for m in refs_sel
        )
        + f"<td><span style='color:{VERDE if float(s_var.sum()) >= 0 else VERMELHO}'><b>"
        f"{moeda(float(s_var.sum()))}</b></span></td></tr>"
    )

    # ---- 4. SALDO ----
    html.append(
        "<tr class='sec'><td>4. SALDO DE CAIXA</td>"
        + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
    )
    html.append(linha_tot("(+) Saldo inicial", s_ini, AZUL, cls="saldo"))
    html.append(
        linha_tot(
            "(+) Variação líquida do mês",
            s_var,
            "dinamico",
            cls="tot",
        )
    )
    html.append(
        linha_tot(
            "(=) Saldo final de caixa",
            s_fim,
            VERDE if saldo_fim_periodo >= 0 else VERMELHO,
            cls="saldo",
        )
    )

    html.append(linha_tot("Saldo Tasy", s_tasy, ROXO, cls="saldo"))
    html.append(linha_tot("Diferença: fluxo − Tasy", s_diferenca, AMBAR, cls="saldo"))

    d_out = df[df["Papel"] == "outros"]
    if not d_out.empty:
        html.append(
            "<tr class='sec'><td>ITENS SEM CLASSIFICAÇÃO GERENCIAL</td>"
            + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
        )
        html.extend(linhas_df(d_out, None, f"o_{_v_ui}"))

    th = "".join(f"<th>{h}</th>" for h in (["Descrição"] + x_lab + ["Total"]))
    st.markdown(
        f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{th}</tr></thead>"
        f"{''.join(html)}</table></div>",
        unsafe_allow_html=True,
    )

    # ==========================================================================
    # GRÁFICOS E INDICADORES EXECUTIVOS (ABAIXO DA TABELA)
    # ==========================================================================
    st.markdown(
        "<div class='section-title'>Indicadores e Tendências Mensais</div>",
        unsafe_allow_html=True,
    )

    def criar_grafico_tendencia(titulo, serie_vals, cor_linha, area=False):
        vals = [float(serie_vals.get(m, 0.0)) for m in refs_sel]
        cores_pts = [VERDE if v >= 0 else VERMELHO for v in vals]
        textos_pts = [moeda_curta(v) for v in vals]

        fig = go.Figure()
        fig.add_hline(y=0, line_dash="dot", line_color="#94a3b8", line_width=1)

        r_hex = int(cor_linha[1:3], 16)
        g_hex = int(cor_linha[3:5], 16)
        b_hex = int(cor_linha[5:7], 16)

        fig.add_trace(
            go.Scatter(
                x=x_lab,
                y=vals,
                mode="lines+markers+text",
                line=dict(color=cor_linha, width=3, shape="spline", smoothing=0.35),
                marker=dict(
                    size=9,
                    color=cores_pts,
                    line=dict(color="#ffffff", width=2),
                ),
                text=textos_pts,
                textposition="top center",
                textfont=dict(size=10, color="#334155", family="Inter, Arial"),
                fill="tozeroy" if area else None,
                fillcolor=f"rgba({r_hex},{g_hex},{b_hex},0.09)" if area else None,
                hovertemplate="<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>",
            )
        )

        y_min = min(vals + [0.0])
        y_max = max(vals + [0.0])
        amp = (y_max - y_min) if (y_max - y_min) > 0 else max(abs(y_max), 1000.0)

        fig.update_layout(
            title=dict(
                text=f"<b>{titulo}</b>",
                font=dict(size=13, color=TXT, family="Inter, Arial"),
                x=0.01,
                y=0.95,
            ),
            height=290,
            margin=dict(l=14, r=14, t=44, b=18),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            showlegend=False,
            hovermode="x unified",
            separators=",.",
            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=11, color=MUTED),
                linecolor=BORDA,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#f1f5f9",
                zeroline=False,
                tickfont=dict(size=10, color=MUTED),
                tickprefix="R$ ",
                tickformat=",.0f",
                range=[y_min - amp * 0.16, y_max + amp * 0.24],
            ),
        )
        return fig

    # Linha 1: Saldo Final Mensal + Variação Líquida Mensal
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.plotly_chart(
            criar_grafico_tendencia("Saldo Final de Caixa (Mensal)", s_fim, AZUL, area=True),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with g_col2:
        st.plotly_chart(
            criar_grafico_tendencia("Variação Líquida de Caixa (FCO + FCI + FCF)", s_var, CIANO, area=False),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # Linha 2: FCO, FCI e FCF em indicadores individuais
    g_col3, g_col4, g_col5 = st.columns(3)
    with g_col3:
        st.plotly_chart(
            criar_grafico_tendencia("1. FCO · Fluxo Operacional", s_fco, VERDE, area=True),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with g_col4:
        st.plotly_chart(
            criar_grafico_tendencia("2. FCI · Fluxo de Investimentos", s_fci, AMBAR, area=True),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with g_col5:
        st.plotly_chart(
            criar_grafico_tendencia("3. FCF · Fluxo de Financiamento", s_fcf, ROXO, area=True),
            use_container_width=True,
            config={"displayModeBar": False},
        )


with st.sidebar:
    st.markdown("<div class='side-sec' style='margin-top:12px;'>Exportação</div>", unsafe_allow_html=True)
    try:
        st.download_button(
            label="⬇ Baixar Excel",
            data=gerar_excel_fluxo(),
            file_name=f"fluxo_de_caixa_{pd.Timestamp(ini):%Y%m}_{pd.Timestamp(fim):%Y%m}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="baixar_fluxo_excel",
        )
    except ImportError:
        st.error("Para habilitar o Excel, instale a dependência: pip install XlsxWriter")
