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
import re
import textwrap
import unicodedata
from datetime import datetime

import pandas as pd

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
ABA_FCX_OBRA = "FCx_Obra"
ABA_BORDERO = "Fluxo_Despesas_Borderô"
ABA_ADIANT = "Fluxo_Adiantamentos"
ABA_RECEITA = "Fluxo_Receita"
ABA_CLASSIF = "Classificacao_FCx"
ABA_SALDO = "Saldo_FCx"
ABA_SALDO_TASY = "Base_Saldo_FCx_Tasy"
ABA_DEVOL = "FCx_Devolução_Adiantamento"
ABA_DEVOL_ALT = "FCx_Devolucao_Adiantamento"  # fallback sem acento

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

    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-weight: 700 !important; padding: 0.55rem 1rem !important;
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
    .vazio { color: #64748b; font-size: 12px; padding: 28px 8px; text-align: center; }
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


def parse_ref_mes(v, ano_ref=None):
    """Converte data, serial ou texto de mês em referência no primeiro dia do mês."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return pd.NaT
    ano = ano_ref or ANO_REF
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        n = float(v)
        if 1 <= n <= 12:
            return pd.Timestamp(ano, int(n), 1)
    texto = str(v).strip()
    if re.fullmatch(r"\d{1,2}", texto) and 1 <= int(texto) <= 12:
        return pd.Timestamp(ano, int(texto), 1)
    # Cabeçalhos de matriz no formato 2026.01 / 2026-01 / 2026/01.
    m_ano_mes = re.fullmatch(r"(20\d{2})[./-](\d{1,2})", texto)
    if m_ano_mes and 1 <= int(m_ano_mes.group(2)) <= 12:
        return pd.Timestamp(int(m_ano_mes.group(1)), int(m_ano_mes.group(2)), 1)
    d = parse_data(v)
    if pd.notna(d):
        return pd.Timestamp(d.year, d.month, 1)
    mes = parse_mes_header(v, ano)
    return mes if mes is not None else pd.NaT


def chave_conta_contabil(v):
    """Normaliza a conta contábil para conciliação entre abas."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    # Evita divergência entre códigos numéricos lidos como 123 e 123.0.
    texto = str(v).strip()
    if re.fullmatch(r"\d+\.0+", texto):
        texto = texto.split(".", 1)[0]
    return normalizar_chave(texto)


def parse_mes_header(h, ano_ref=None):
    if h is None or (isinstance(h, float) and pd.isna(h)):
        return None
    if isinstance(h, (pd.Timestamp, datetime)):
        return pd.Timestamp(ano_ref or ANO_REF, h.month, 1)
    if isinstance(h, (int, float)) and not isinstance(h, bool):
        n = float(h)
        if 1 <= n <= 12:
            return pd.Timestamp(ano_ref or ANO_REF, int(n), 1)
        if 20000 < n < 80000:
            d = pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
            return pd.Timestamp(ano_ref or ANO_REF, d.month, 1)
    t = normalizar(h)
    if not t or t in SKIP_HEADER or "total" in t:
        return None
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
    cols_out = ["Ref", "Categoria", "Valor", "Tipo"]
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
            reg.append({"Ref": ref, "Categoria": cat_s, "Valor": val, "Tipo": tipo})

    if not reg:
        return pd.DataFrame(columns=cols_out)
    return pd.DataFrame(reg)[cols_out]


def sinal_devolucao(categoria):
    """
    Fornecedores / Salarial → devolução ENTRA no caixa (+).
    Paciente / Prontuário → devolução SAI do caixa (−).
    """
    n = normalizar_chave(categoria)
    if "fornecedor" in n or "salarial" in n:
        return 1.0
    if "paciente" in n or "prontuario" in n:
        return -1.0
    # genérico sem fornecedor/salarial → saída (paciente)
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
        raw = conn.read(worksheet=ABA_SALDO, ttl=0)
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
    """Lê somente os totais de cada bloco; não soma bancos e total novamente."""
    inicial, final, avisos = {}, {}, []
    try:
        conn = conectar_sheets()
        if conn is None:
            return inicial, final, ["Saldo Tasy: conexão indisponível."]
        raw = conn.read(worksheet=ABA_SALDO_TASY, ttl=0)
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
    """Fonte específica tem prioridade por mês e natureza; fallback sem duplicar."""
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
    # Base_Despesas agrupa paciente e prontuário em uma única categoria.
    # Só substitui esse agregado quando o mês existe na fonte específica.
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
                raw = conn.read(worksheet=ABA_CLASSIF, ttl=0)
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

    # Devoluções de adiantamento → bloco Var. Ativos/Passivos no FCO
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


def papel_classif(classif, fluxo=""):
    n = normalizar(classif)
    nf = normalizar(fluxo)

    if "variacoes de ativos" in n or "variações de ativos" in n or n == normalizar(CLASSIF_VAR_AP):
        return "var_ap"

    if "invest" in nf:
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
def carregar_fluxo():
    cols = ["Ref", "Categoria", "Valor", "Tipo", "Grupo"]
    vazio = pd.DataFrame(columns=cols)
    avisos = []
    conn = conectar_sheets()
    if conn is None:
        return vazio, ["Conexão indisponível."]
    partes = []

    # FCx_Obra: matriz mensal agregada por obra (Categoria) e Conta Contábil.
    # Os valores dessa aba serão transferidos para o FCI via Classificacao_FCx,
    # abatendo primeiro o mesmo valor da Base_Despesas para a mesma conta/mês.
    raw_obra = None
    try:
        raw_obra = conn.read(worksheet=ABA_FCX_OBRA, ttl=0)
    except Exception as e:
        avisos.append(f"FCx_Obra: não foi possível ler a aba ({e})")

    fcx_obra = pd.DataFrame(columns=["Ref", "Categoria", "Valor", "Tipo", "Grupo", "ContaContabil"])
    if raw_obra is None:
        avisos.append("FCx_Obra: aba indisponível; fluxo calculado sem essa fonte.")
    elif raw_obra.empty:
        avisos.append("FCx_Obra: aba vazia.")
    else:
        c_obra = col_por_nomes(raw_obra, ["Categoria", "Obra", "Empreendimento"])
        c_conta_obra = col_por_nomes(raw_obra, ["Conta Contábil", "Conta Contabil", "Conta Contábil FCx", "Conta Contabil FCx"])
        if c_conta_obra is None:
            avisos.append("FCx_Obra: não encontrei a coluna Conta Contábil.")
        else:
            # A aba é uma tabela dinâmica: a obra pode aparecer apenas na primeira
            # linha de cada grupo; preencher para baixo recupera as linhas mescladas.
            obra_series = (raw_obra[c_obra].astype(str).replace({"nan": "", "None": ""}).str.strip().ffill()
                           if c_obra else pd.Series("Obra não informada", index=raw_obra.index))
            meses_colunas = {}
            for coluna in raw_obra.columns:
                ref_mes = parse_ref_mes(coluna)
                if pd.notna(ref_mes):
                    meses_colunas[coluna] = ref_mes
            linhas_obra = []
            for idx, row in raw_obra.iterrows():
                conta_original = row.get(c_conta_obra, "")
                conta_txt = str(conta_original).strip() if pd.notna(conta_original) else ""
                conta_norm = chave_conta_contabil(conta_original)
                obra_txt = str(obra_series.loc[idx]).strip()
                if (not conta_norm or conta_norm in {"total", "total geral", "nan", "none"}
                        or normalizar_chave(conta_txt).endswith(" total")
                        or normalizar_chave(obra_txt) in {"total", "total geral", "nan", "none", ""}):
                    continue
                for coluna_mes, ref_mes in meses_colunas.items():
                    valor = abs(limpa_valor(row.get(coluna_mes)))
                    if valor <= 0.005:
                        continue
                    linhas_obra.append({
                        "Ref": ref_mes,
                        # A conta contábil é a descrição a classificar no FCx.
                        "Categoria": conta_txt,
                        "Valor": valor,
                        "Tipo": "Saída",
                        "Grupo": "FCx_Obra",
                        "ContaContabil": conta_norm,
                        "Obra": obra_txt,
                    })
            if linhas_obra:
                fcx_obra = pd.DataFrame(linhas_obra)
            else:
                avisos.append("FCx_Obra: nenhuma combinação válida de conta contábil, mês e valor foi encontrada.")

    # Total mensal por conta contábil que deve ser retirado das outras bases.
    abatimentos_obra = {}
    if not fcx_obra.empty:
        soma_obra = fcx_obra.groupby(["Ref", "ContaContabil"], as_index=False)["Valor"].sum()
        abatimentos_obra = {
            (r["Ref"], r["ContaContabil"]): float(r["Valor"])
            for _, r in soma_obra.iterrows()
        }

    # Base_Despesas
    try:
        raw_d = conn.read(worksheet=ABA_DESPESAS, ttl=0)
    except Exception as e:
        raw_d = None
        avisos.append(f"Despesas: {e}")
    if raw_d is not None and not raw_d.empty:
        df = raw_d.copy()
        c_data = col_por_letra(df, "B") or col_por_nomes(df, ["Data"])
        c_trans = col_por_letra(df, "D") or col_por_nomes(df, ["Transação FCx", "Transacao FCx"])
        c_clas = col_por_letra(df, "E") or col_por_nomes(df, ["Classificação FCx", "Classificacao FCx"])
        c_val = col_por_letra(df, "F") or col_por_nomes(df, ["Vl Débito", "Vl Debito", "Valor"])
        c_conta = col_por_nomes(df, ["Conta Contábil", "Conta Contabil", "Conta Contábil FCx", "Conta Contabil FCx"])
        if all([c_data, c_trans, c_clas, c_val]):
            tmp = pd.DataFrame({
                "Data": df[c_data].apply(parse_data),
                "Transação": df[c_trans].fillna("").astype(str).str.strip(),
                "Categoria": df[c_clas].fillna("(Sem classificação)").astype(str).str.strip(),
                "Valor": df[c_val].apply(limpa_valor),
                "ContaContabil": df[c_conta].apply(chave_conta_contabil) if c_conta else "",
            })
            devolucoes = tmp["Transação"].map(eh_linha_devolucao)
            permitidas = tmp["Transação"].map(normalizar).isin(TRANSACOES_DESPESAS)
            tmp.loc[devolucoes, "Categoria"] = tmp.loc[devolucoes, "Transação"]
            tmp = tmp[permitidas | devolucoes]
            tmp = tmp[tmp["Data"].notna() & (tmp["Valor"].abs() > 0.005)]
            if not tmp.empty:
                tmp["Ref"] = tmp["Data"].apply(lambda d: pd.Timestamp(d.year, d.month, 1))

                # Abater FCx_Obra da Base_Despesas por conta contábil e mês.
                # O abatimento é limitado ao saldo encontrado na base antiga; se
                # FCx_Obra superar a base, o excedente fica registrado em FCx_Obra
                # e é sinalizado para conferência (não criamos valores negativos).
                if abatimentos_obra:
                    if c_conta is None:
                        avisos.append(
                            "FCx_Obra: a Base_Despesas não possui coluna Conta Contábil; "
                            "não foi possível abater os valores nessa base."
                        )
                    else:
                        tmp["_ChaveConciliacao"] = list(zip(tmp["Ref"], tmp["ContaContabil"]))
                        tmp["_ValorDisponivel"] = tmp["Valor"].clip(lower=0)
                        totais_base = tmp.groupby("_ChaveConciliacao")["_ValorDisponivel"].sum().to_dict()
                        faltas = []
                        for chave, valor_obra in abatimentos_obra.items():
                            total_base = float(totais_base.get(chave, 0.0))
                            valor_abatido = min(total_base, float(valor_obra))
                            if valor_abatido > 0.005 and total_base > 0.005:
                                mask = tmp["_ChaveConciliacao"].map(lambda x: x == chave)
                                idxs = tmp.index[mask & (tmp["Valor"] > 0)].tolist()
                                # Distribui o abatimento proporcionalmente entre os
                                # lançamentos da mesma conta/mês, preservando categoria.
                                restante = valor_abatido
                                soma_disponivel = float(tmp.loc[idxs, "Valor"].clip(lower=0).sum())
                                for pos, idx in enumerate(idxs):
                                    original = max(float(tmp.at[idx, "Valor"]), 0.0)
                                    if pos == len(idxs) - 1:
                                        desconto = min(original, restante)
                                    elif soma_disponivel > 0:
                                        desconto = min(original, valor_abatido * original / soma_disponivel)
                                    else:
                                        desconto = 0.0
                                    tmp.at[idx, "Valor"] = float(tmp.at[idx, "Valor"]) - desconto
                                    restante -= desconto
                            if float(valor_obra) > total_base + 0.01:
                                faltas.append((chave, float(valor_obra) - total_base))
                        if faltas:
                            avisos.append(
                                f"FCx_Obra: em {len(faltas)} combinação(ões) de mês/conta contábil, "
                                "o valor da obra superou o encontrado na Base_Despesas. "
                                "O saldo excedente foi mantido em FCx_Obra; confira possível duplicidade em outras fontes."
                            )
                        tmp = tmp.drop(columns=[c for c in tmp.columns if c.startswith("_")], errors="ignore")

                tmp = tmp[tmp["Valor"].abs() > 0.005]
                if not tmp.empty:
                    g = tmp.groupby(["Ref", "Categoria"], as_index=False)["Valor"].sum()
                    g["Tipo"], g["Grupo"] = "Saída", "Despesas"
                    partes.append(g[cols])
        else:
            avisos.append("Despesas: não foi possível identificar Data, Transação FCx, Classificação FCx e Valor.")

    # Incluir FCx_Obra integralmente após o abatimento da Base_Despesas.
    # A classificação da Conta Contábil será aplicada abaixo pelo mapa Classificacao_FCx.
    if not fcx_obra.empty:
        partes.append(fcx_obra[cols].copy())

    # Borderô
    try:
        raw_b = conn.read(worksheet=ABA_BORDERO, ttl=0)
    except Exception as e:
        raw_b = None
        avisos.append(f"Borderô: {e}")
    if raw_b is not None and not raw_b.empty:
        if abatimentos_obra:
            avisos.append(
                "FCx_Obra: o abatimento foi aplicado à Base_Despesas; não foi possível validar "
                "sobreposição com Borderô, pois essa aba não preserva conta contábil no processamento atual."
            )
        mb = melt_matriz(raw_b, 1, 0, 2, "Saída", ANO_REF)
        if mb.empty:
            mb = melt_matriz(raw_b, 1, 2, 2, "Saída", ANO_REF)
        if not mb.empty:
            mb = mb.copy()
            mb["Grupo"] = "Borderô"
            partes.append(mb[cols])

    # Adiantamentos (saídas de adiantamento)
    try:
        raw_a = conn.read(worksheet=ABA_ADIANT, ttl=0)
    except Exception as e:
        raw_a = None
        avisos.append(f"Adiantamentos: {e}")
    if raw_a is not None and not raw_a.empty:
        if abatimentos_obra:
            avisos.append(
                "FCx_Obra: o abatimento foi aplicado à Base_Despesas; não foi possível validar "
                "sobreposição com Adiantamentos, pois essa aba não preserva conta contábil no processamento atual."
            )
        ma = melt_matriz(raw_a, 1, 0, 2, "Saída", ANO_REF)
        if ma.empty:
            ma = melt_matriz(raw_a, 1, 1, 2, "Saída", ANO_REF)
        if not ma.empty:
            ma = ma.copy()
            ma["Grupo"] = "Adiantamentos"
            partes.append(ma[cols])

    # Receita
    try:
        raw_r = conn.read(worksheet=ABA_RECEITA, ttl=0)
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

    # Devoluções de adiantamento (Var. Ativos e Passivos)
    raw_dev = None
    for nome_aba in (ABA_DEVOL, ABA_DEVOL_ALT):
        try:
            raw_dev = conn.read(worksheet=nome_aba, ttl=0)
            if raw_dev is not None and not raw_dev.empty:
                break
        except Exception as e:
            raw_dev = None
            last_err = e
    if raw_dev is None:
        avisos.append(f"Devolução Adiantamento: aba não encontrada ({ABA_DEVOL})")
    elif raw_dev.empty:
        avisos.append("Devolução Adiantamento: aba vazia")
    else:
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
        else:
            avisos.append("Devolução Adiantamento: estrutura não reconhecida")

    if not partes:
        return vazio, avisos or ["Nenhum lançamento."]
    base = consolidar_devolucoes(pd.concat(partes, ignore_index=True))
    base["Categoria"] = base["Categoria"].replace({"": "(Sem classificação)", "nan": "(Sem classificação)"})
    base = base.groupby(["Ref", "Categoria", "Tipo", "Grupo"], as_index=False)["Valor"].sum()
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
pares = base["Categoria"].apply(lambda c: aplicar_classificacao(c, mapa_cls))
base["Classif"] = pares.apply(lambda x: x[0])
base["Fluxo"] = pares.apply(lambda x: x[1])
base["Detalhe"] = pares.apply(lambda x: x[2])
base["Papel"] = base.apply(lambda r: papel_classif(r["Classif"], r["Fluxo"]), axis=1)

# Ajustes aprovados já possuem papel e sinal definidos pelo robô.
# Ler fora do cache da base permite refletir aprovações e estornos ao abrir a página.
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
    base = pd.concat([base, base_ajustes], ignore_index=True)

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
    grupo_sel = st.multiselect("Grupo", grupos_all, default=grupos_all)
    if st.button("↻ Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown(
        f"<div class='side-card'><small>De-para</small><b>{len(mapa_cls)} classificações</b></div>"
        f"<div class='side-card'><small>Saldo inicial (aba)</small><b>{len(mapa_saldo)} mês(es)</b></div>",
        unsafe_allow_html=True,
    )

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
var_ap = total_papel(df, "var_ap")  # já com sinal (+ fornecedor / − paciente)
capex = total_papel(df, "capex")
amort = total_papel(df, "amortizacao")
juros = total_papel(df, "juros")
captacao = total_papel(df, "captacao", tipo="Entrada")

fco = rec_op - custo_op - impostos + var_ap
fci = -capex
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
s_fci = -s_cap
s_cpt = serie(df, "captacao", tipo="Entrada")
s_amo = serie(df, "amortizacao")
s_jur = serie(df, "juros")
s_fcf = s_cpt - s_amo - s_jur
s_var = s_fco + s_fci + s_fcf

# Calcula os meses anteriores também, para filtros que começam após janeiro.
refs_calculo = list(pd.date_range(min(meses_all), max(refs_sel), freq="MS")) if refs_sel else []
s_var_completo = (base.assign(_sinal=base.apply(
    lambda r: float(r["Valor"]) * (1 if r["Papel"] in ("receita_op", "captacao", "var_ap") else -1)
    if r["Papel"] != "outros" else 0.0, axis=1))
    .groupby("Ref")["_sinal"].sum())
s_var_completo.update(s_var)
s_ini_full, s_fim_full = montar_serie_saldo(refs_calculo, s_var_completo, mapa_saldo)
s_ini, s_fim = s_ini_full.reindex(refs_sel), s_fim_full.reindex(refs_sel)
s_tasy = pd.Series({m: mapa_tasy_fim.get(m, float("nan")) for m in refs_sel}, dtype=float)
s_diferenca = s_fim - s_tasy
saldo_fim_periodo = float(s_fim.iloc[-1]) if len(s_fim) else 0.0
saldo_ini_periodo = float(s_ini.iloc[0]) if len(s_ini) else 0.0
if grupo_sel and set(grupo_sel) != set(grupos_all):
    st.info("Comparativo Tasy com grupos filtrados: a diferença não representa a conciliação completa.")

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
        <div class='kpi-sub'>− CAPEX ({moeda_curta(capex)})</div>
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

st.markdown(
    "<div class='section-title'>Demonstrativo · FCO / FCI / FCF · Saldo de caixa · clique na seta para composição</div>",
    unsafe_allow_html=True,
)


def linhas_df(x, titulo, uid_prefix):
    rows = []
    if x.empty:
        return rows
    if titulo:
        rows.append(
            f"<tr class='subsec'><td>{titulo}</td>"
            + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
        )
    piv = x.pivot_table(index="Classif", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
    piv = piv.reindex(columns=refs_sel, fill_value=0.0)
    piv["__t__"] = piv.sum(axis=1)
    piv = piv.sort_values("__t__", ascending=False)
    det = x.groupby(["Classif", "Detalhe", "Ref"], as_index=False)["Valor"].sum()
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


def linha_tot(label, s, cor, cls="tot"):
    def fmt(v):
        return "—" if pd.isna(v) else moeda(float(v))
    tot_val = float(s.iloc[0] if label == "(+) Saldo inicial" else s.iloc[-1]) if len(s) else 0.0
    if cls == "saldo":
        tot_html = f"<td><span style='color:{cor}'><b>{fmt(tot_val)}</b></span></td>"
    else:
        tot_html = f"<td><span style='color:{cor}'><b>{moeda(float(s.sum()))}</b></span></td>"
    return (
        f"<tr class='{cls}'><td><b>{label}</b></td>"
        + "".join(
            f"<td><span style='color:{cor}'>{fmt(s.get(m, float("nan")))}</span></td>"
            for m in refs_sel
        )
        + tot_html
        + "</tr>"
    )


if df.empty:
    st.markdown("<div class='vazio'>Sem dados no período</div>", unsafe_allow_html=True)
else:
    html = []

    # ---- 1. FCO ----
    html.append(
        "<tr class='sec'><td>1. FLUXO DE CAIXA OPERACIONAL (FCO)</td>"
        + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
    )
    html.extend(linhas_df(df[df["Papel"] == "receita_op"], "(+) Receitas operacionais", "r"))
    html.append(linha_tot("Total receitas operacionais", s_rec, VERDE))

    html.extend(linhas_df(df[df["Papel"] == "custo_op"], "(−) Custos e despesas operacionais", "c"))
    html.append(linha_tot("Total custos e despesas operacionais", s_cus, VERMELHO))

    html.extend(linhas_df(df[df["Papel"] == "imposto"], "(−) Impostos", "i"))
    html.append(linha_tot("Total impostos", s_imp, VERMELHO))

    # Variações de Ativos e Passivos (devoluções)
    html.extend(
        linhas_df(
            df_var_ap,
            "(±) Variações de Ativos e Passivos",
            "v",
        )
    )
    html.append(
        linha_tot(
            "Total variações de ativos e passivos",
            s_vap,
            VERDE if float(s_vap.sum()) >= 0 else VERMELHO,
        )
    )

    html.append(linha_tot("= FCO", s_fco, VERDE if float(s_fco.sum()) >= 0 else VERMELHO))

    # ---- 2. FCI ----
    html.append(
        "<tr class='sec'><td>2. FLUXO DE CAIXA DE INVESTIMENTOS (FCI)</td>"
        + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
    )
    html.extend(linhas_df(df[df["Papel"] == "capex"], "(−) Desembolsos em CAPEX", "k"))
    html.append(linha_tot("= FCI (− CAPEX)", s_fci, VERDE if float(s_fci.sum()) >= 0 else VERMELHO))

    # ---- 3. FCF ----
    html.append(
        "<tr class='sec'><td>3. FLUXO DE CAIXA DE FINANCIAMENTO (FCF)</td>"
        + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
    )
    html.extend(linhas_df(df_captacao, "(+) Novas captações (empréstimos)", "p"))
    html.append(linha_tot("Total captações", s_cpt, VERDE))

    html.extend(linhas_df(df_amort, "(−) Amortizações de empréstimos", "a"))
    html.append(linha_tot("Total amortizações", s_amo, VERMELHO))

    html.extend(linhas_df(df_juros, "(−) Juros e encargos financeiros", "j"))
    html.append(linha_tot("Total juros e encargos", s_jur, VERMELHO))

    html.append(linha_tot("= FCF", s_fcf, VERDE if float(s_fcf.sum()) >= 0 else VERMELHO))

    html.append(
        "<tr class='res'><td><b>VARIAÇÃO LÍQUIDA DE CAIXA (FCO + FCI + FCF)</b></td>"
        + "".join(
            f"<td><span style='color:{VERDE if float(s_var.get(m, 0)) >= 0 else VERMELHO};font-weight:800'>"
            f"{moeda(float(s_var.get(m, 0)))}</span></td>"
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
            VERDE if float(s_var.sum()) >= 0 else VERMELHO,
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
        html.extend(linhas_df(d_out, None, "o"))

    th = "".join(f"<th>{h}</th>" for h in (["Descrição"] + x_lab + ["Total"]))
    st.markdown(
        f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{th}</tr></thead>"
        f"{''.join(html)}</table></div>",
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown(
        f"<div class='side-card'><small>FCO</small>"
        f"<b style='color:{'#059669' if fco >= 0 else '#dc2626'}'>{moeda(fco)}</b></div>"
        f"<div class='side-card'><small>Var. Ativos/Passivos</small>"
        f"<b style='color:{'#059669' if var_ap >= 0 else '#dc2626'}'>{moeda(var_ap)}</b></div>"
        f"<div class='side-card'><small>FCI</small>"
        f"<b style='color:{'#059669' if fci >= 0 else '#dc2626'}'>{moeda(fci)}</b></div>"
        f"<div class='side-card'><small>FCF</small>"
        f"<b style='color:{'#059669' if fcf >= 0 else '#dc2626'}'>{moeda(fcf)}</b></div>"
        f"<div class='side-card'><small>Saldo final</small>"
        f"<b style='color:{'#059669' if saldo_fim_periodo >= 0 else '#dc2626'}'>{moeda(saldo_fim_periodo)}</b></div>"
        f"<div class='side-card'><small>Última atualização</small>"
        f"<b>{datetime.now():%d/%m/%Y %H:%M}</b></div>",
        unsafe_allow_html=True,
    )
