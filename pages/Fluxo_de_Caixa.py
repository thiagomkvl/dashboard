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
# PALETA — tema claro / clean
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
ABA_CLASSIF = "Classificacao_FCx"  # opcional no Sheets

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

SKIP_LABELS = {
    "", "nan", "none", "total", "total geral", "soma", "geral",
    "mes", "mês", "convenios", "convênios", "origem", "origem receita",
    "conta contabil", "conta contábil", "classificacao", "classificação",
    "transacao", "transação", "sum de vl debito", "sum de vl débito",
    "adiantamento fornecedores - banco total", "adiantamento fornecedores - banco",
    "receitas", "saidas", "saídas",
}
SKIP_HEADER = {"total", "total geral", "soma", "geral", "data - mes", "data - mês"}

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
    .kpi.red { border-left-color: #dc2626; }
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
        overflow-x: auto; overflow-y: visible;
        border-radius: 10px; border: 1px solid #e2e8f0; background: #ffffff;
    }
    .tbl { width: 100%; border-collapse: collapse; font-size: 12px; color: #334155; }
    .tbl th {
        background: #f8fafc; color: #64748b;
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
    .tbl tr.sec td {
        font-weight: 800; color: #0f172a; background: #eef2ff;
        border-top: 1px solid #e2e8f0; text-transform: uppercase; font-size: 11px;
        letter-spacing: 0.4px;
    }
    .tbl tr.res td {
        font-weight: 800; background: #f8fafc; border-top: 2px solid #e2e8f0;
    }
    .tbl tr.sub-row td {
        background: #fafbfc; color: #64748b; font-size: 11px;
    }
    .tbl tr.sub-row td:first-child { padding-left: 28px; }
    .tbl .mut { color: #94a3b8; }
    .dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 8px; vertical-align: middle;
    }

    /* Drill-down */
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
        n = float(h)
        if 1 <= n <= 12:
            return pd.Timestamp(ano_ref or ANO_REF, int(n), 1)
        if 20000 < n < 80000:
            d = pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
            return pd.Timestamp(ano_ref or ANO_REF, d.month, 1)

    t = normalizar(h)
    if not t or t in SKIP_HEADER or "total" in t:
        return None

    # jan / jan. / janeiro / jan 26
    m = re.match(r"^([a-z]{3,9})(?:\s+(\d{2,4}))?$", t)
    if m:
        chave = m.group(1)
        mes = MESES_MAP.get(chave) or MESES_MAP.get(chave[:3])
        if mes:
            if m.group(2):
                ano = int(m.group(2))
                if ano < 100:
                    ano += 2000
            else:
                ano = ano_ref or ANO_REF
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


def cor_cat(nome, mapa):
    if nome not in mapa:
        mapa[nome] = CORES_CAT[len(mapa) % len(CORES_CAT)]
    return mapa[nome]


def melt_matriz(raw, col_label_idx, header_row_idx, start_col_idx, tipo, ano_ref=None):
    cols_out = ["Ref", "Categoria", "Valor", "Tipo"]
    if raw is None or raw.empty:
        return pd.DataFrame(columns=cols_out)

    ano = ano_ref or ANO_REF
    data = raw.values.tolist()
    if not data:
        return pd.DataFrame(columns=cols_out)

    n_rows = len(data)
    n_cols = max((len(r) for r in data), default=0)
    if n_cols == 0:
        return pd.DataFrame(columns=cols_out)

    grid = []
    for r in data:
        row = list(r) + [None] * (n_cols - len(r))
        grid.append(row[:n_cols])

    def score_header(row):
        return sum(1 for j in range(start_col_idx, n_cols) if parse_mes_header(row[j], ano) is not None)

    hr = header_row_idx if 0 <= header_row_idx < n_rows else 0
    if score_header(grid[hr]) < 3:
        best, best_s = hr, score_header(grid[hr])
        for i in range(min(6, n_rows)):
            s = score_header(grid[i])
            if s > best_s:
                best, best_s = i, s
        hr = best

    header = grid[hr]
    li = col_label_idx if 0 <= col_label_idx < n_cols else 0

    mapa_mes = {}
    for j in range(start_col_idx, n_cols):
        ref = parse_mes_header(header[j], ano)
        if ref is not None:
            mapa_mes[j] = ref

    if not mapa_mes:
        k = 0
        for j in range(start_col_idx, min(start_col_idx + 12, n_cols)):
            nt = normalizar(header[j])
            if nt in SKIP_HEADER or "total" in nt:
                continue
            k += 1
            if 1 <= k <= 12:
                mapa_mes[j] = pd.Timestamp(ano, k, 1)

    if not mapa_mes:
        return pd.DataFrame(columns=cols_out)

    registros = []
    for i in range(hr + 1, n_rows):
        row = grid[i]
        cat = row[li] if li < len(row) else None
        if cat is None or (isinstance(cat, float) and pd.isna(cat)):
            continue
        cat_s = str(cat).strip()
        ncat = normalizar(cat_s)
        if ncat in SKIP_LABELS or ncat.startswith("total") or "total geral" in ncat:
            continue
        # ignora linhas de total do adiantamento
        if "adiantamento fornecedores" in ncat and "total" in ncat:
            continue

        for j, ref in mapa_mes.items():
            val = limpa_valor(row[j] if j < len(row) else 0)
            if abs(val) <= 0.005:
                continue
            registros.append({"Ref": ref, "Categoria": cat_s, "Valor": val, "Tipo": tipo})

    if not registros:
        return pd.DataFrame(columns=cols_out)
    return pd.DataFrame(registros)[cols_out]


# ==============================================================================
# MAPA DE CLASSIFICAÇÃO FCx
# ==============================================================================
def _mapa_de_dataframe(df_map):
    """Espera colunas Descrição + Classificação FCx."""
    if df_map is None or df_map.empty:
        return {}
    cols = list(df_map.columns)
    c_desc = None
    c_cls = None
    for c in cols:
        n = normalizar(c)
        if n in ("descricao", "descrição", "conta contabil", "conta contábil", "categoria"):
            c_desc = c
        if "classific" in n:
            c_cls = c
    if c_desc is None:
        c_desc = cols[0]
    if c_cls is None and len(cols) > 1:
        c_cls = cols[1]
    if c_desc is None or c_cls is None:
        return {}

    out = {}
    for _, r in df_map.iterrows():
        d = str(r[c_desc]).strip() if pd.notna(r[c_desc]) else ""
        c = str(r[c_cls]).strip() if pd.notna(r[c_cls]) else ""
        nd, nc = normalizar(d), normalizar(c)
        if not nd or nd in SKIP_LABELS or nd in ("receitas", "saidas", "saídas", "total receitas", "total saidas"):
            continue
        if not nc or nc in SKIP_LABELS:
            continue
        out[nd] = c  # mantém o rótulo original da classificação
    return out


@st.cache_data(ttl=120, show_spinner=False)
def carregar_mapa_classificacao():
    """
    Ordem de busca do de-para:
      1) Google Sheets (aba Classificacao_FCx)
      2) Arquivo local Classificacao_FCx_Concluida.xlsx
    """
    # 1) Sheets
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

    # 2) Arquivo local (vários caminhos possíveis)
    candidatos = [
        "Classificacao_FCx_Concluida.xlsx",
        os.path.join("data", "Classificacao_FCx_Concluida.xlsx"),
        os.path.join("pages", "Classificacao_FCx_Concluida.xlsx"),
        "/home/workdir/attachments/Classificacao_FCx_Concluida.xlsx",
    ]
    for path in candidatos:
        if os.path.isfile(path):
            try:
                raw = pd.read_excel(path)
                m = _mapa_de_dataframe(raw)
                if m:
                    return m
            except Exception:
                continue
    return {}


def aplicar_classificacao(categoria, mapa):
    """Retorna (Classificação FCx, detalhe original)."""
    n = normalizar(categoria)
    if n in mapa:
        return mapa[n], categoria
    # tentativa parcial (contém)
    for k, v in mapa.items():
        if k and (k in n or n in k):
            return v, categoria
    return categoria, categoria  # sem de-para: fica o próprio nome


# ==============================================================================
# CARGA DO FLUXO
# ==============================================================================
@st.cache_data(ttl=60, show_spinner="Carregando fluxo de caixa…")
def carregar_fluxo():
    cols = ["Ref", "Categoria", "Valor", "Tipo", "Grupo"]
    vazio = pd.DataFrame(columns=cols)
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

    # ---- Fluxo_Despesas_Borderô ----
    try:
        raw_b = conn.read(worksheet=ABA_BORDERO, ttl=0)
    except Exception as e:
        raw_b = None
        avisos.append(f"Não foi possível ler borderô de despesas: {e}")

    if raw_b is not None and not raw_b.empty:
        mb = melt_matriz(raw_b, col_label_idx=1, header_row_idx=2, start_col_idx=2, tipo="Saída", ano_ref=ANO_REF)
        if not mb.empty:
            mb = mb.copy()
            mb["Grupo"] = "Borderô"
            partes.append(mb[cols])
        else:
            avisos.append("Borderô de despesas: nenhum valor mensal encontrado.")

    # ---- Fluxo_Adiantamentos ----
    # Estrutura real: A=Transação | B=Conta Contábil | C..=jan. fev. mar. ... | Total geral
    try:
        raw_a = conn.read(worksheet=ABA_ADIANT, ttl=0)
    except Exception as e:
        raw_a = None
        avisos.append(f"Não foi possível ler adiantamentos: {e}")

    if raw_a is not None and not raw_a.empty:
        ma = melt_matriz(
            raw_a, col_label_idx=1, header_row_idx=1, start_col_idx=2,
            tipo="Saída", ano_ref=ANO_REF,
        )
        if ma.empty:
            ma = melt_matriz(
                raw_a, col_label_idx=1, header_row_idx=0, start_col_idx=2,
                tipo="Saída", ano_ref=ANO_REF,
            )
        if not ma.empty:
            ma = ma.copy()
            ma["Grupo"] = "Adiantamentos"
            partes.append(ma[cols])
        else:
            avisos.append("Adiantamentos: nenhum valor mensal encontrado.")

    # ---- Fluxo_Receita ----
    try:
        raw_r = conn.read(worksheet=ABA_RECEITA, ttl=0)
    except Exception as e:
        raw_r = None
        avisos.append(f"Não foi possível ler receitas: {e}")

    if raw_r is not None and not raw_r.empty:
        mr = melt_matriz(
            raw_r, col_label_idx=0, header_row_idx=1, start_col_idx=1,
            tipo="Entrada", ano_ref=ANO_REF,
        )
        if not mr.empty:
            mr = mr.copy()
            mr["Grupo"] = "Receita"
            partes.append(mr[cols])
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
mapa_cls = carregar_mapa_classificacao()

if base.empty:
    for a in avisos:
        st.warning(a)
    st.warning("⚠️ Nenhum dado de fluxo de caixa disponível.")
    st.stop()

# Aplica de-para → Classif + Detalhe
base = base.copy()
pares = base["Categoria"].apply(lambda c: aplicar_classificacao(c, mapa_cls))
base["Classif"] = pares.apply(lambda x: x[0])
base["Detalhe"] = pares.apply(lambda x: x[1])

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

    classifs_all = sorted(base["Classif"].unique().tolist())
    class_sel = st.multiselect("Classificação FCx", classifs_all, placeholder="Todas")

    if st.button("↻ Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if not mapa_cls:
        st.markdown(
            "<div class='side-card'><small>De-para</small>"
            "<b style='color:#d97706'>Mapa não carregado — linhas sem agrupamento</b></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='side-card'><small>De-para</small><b>{len(mapa_cls)} classificações</b></div>",
            unsafe_allow_html=True,
        )

if ini > fim:
    ini, fim = fim, ini
refs_sel = [m for m in meses_all if ini <= m <= fim]
n_ref = len(refs_sel)
i0 = meses_all.index(refs_sel[0]) if refs_sel else 0
refs_prev = meses_all[max(0, i0 - n_ref):i0] if n_ref else []

df = base[base["Ref"].isin(refs_sel)].copy()
if grupo_sel:
    df = df[df["Grupo"].isin(grupo_sel)]
if class_sel:
    df = df[df["Classif"].isin(class_sel)]

df_prev = base[base["Ref"].isin(refs_prev)].copy()
if grupo_sel:
    df_prev = df_prev[df_prev["Grupo"].isin(grupo_sel)]
if class_sel:
    df_prev = df_prev[df_prev["Classif"].isin(class_sel)]

# ==============================================================================
# MÉTRICAS
# ==============================================================================
ent = float(df.loc[df["Tipo"] == "Entrada", "Valor"].sum())
sai = float(df.loc[df["Tipo"] == "Saída", "Valor"].sum())
liq = ent - sai
ent_p = float(df_prev.loc[df_prev["Tipo"] == "Entrada", "Valor"].sum())
sai_p = float(df_prev.loc[df_prev["Tipo"] == "Saída", "Valor"].sum())
liq_p = ent_p - sai_p
tot_desp_op = float(df.loc[df["Grupo"].isin(["Despesas", "Adiantamentos"]), "Valor"].sum())


def delta_sub(atual, ant, invert=False):
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
x_lab = [rot[m] for m in refs_sel]

# ==============================================================================
# CABEÇALHO + KPIs
# ==============================================================================
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>FLUXO DE CAIXA</h1>
            <p>Receitas × saídas consolidadas por Classificação FCx · {ANO_REF}</p>
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

st.markdown(
    f"""
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
        <div class='kpi-t'>Despesas + adiantamentos</div>
        <div class='kpi-v'>{moeda(tot_desp_op)}</div>
        <div class='kpi-sub'><b>{pct(div(tot_desp_op, sai)*100)}</b> das saídas</div>
    </div>
    <div class='kpi {"green" if liq>=0 else "red"}'>
        <div class='kpi-t'>Resultado líquido</div>
        <div class='kpi-v' style='color:{"#059669" if liq>=0 else "#dc2626"}'>{moeda(liq)}</div>
        {delta_sub(liq, liq_p, invert=False) if (ent_p or sai_p) else "<div class='kpi-sub'>receitas − saídas</div>"}
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# TABELA CONSOLIDADA COM DRILL-DOWN
# ==============================================================================
st.markdown(
    "<div class='section-title'>Fluxo de caixa consolidado · clique na seta para ver a composição</div>",
    unsafe_allow_html=True,
)


def bloco_classif(d, tipo_nome, cor_total):
    """Gera linhas HTML: seção + classificações (com sub-linhas de detalhe)."""
    rows_html = []
    rows_html.append(
        f"<tr class='sec'><td>{tipo_nome}</td>" + "".join("<td></td>" for _ in refs_sel) + "<td></td></tr>"
    )
    if d.empty:
        rows_html.append(
            f"<tr><td><span class='mut'>Sem {tipo_nome.lower()}</span></td>"
            + "".join("<td>—</td>" for _ in refs_sel) + "<td>—</td></tr>"
        )
        return rows_html, 0.0

    # total por Classif × mês
    piv = d.pivot_table(index="Classif", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
    piv = piv.reindex(columns=refs_sel, fill_value=0.0)
    piv["__t__"] = piv.sum(axis=1)
    piv = piv.sort_values("__t__", ascending=False)

    # detalhe: Classif × Detalhe × mês
    det = (
        d.groupby(["Classif", "Detalhe", "Ref"], as_index=False)["Valor"].sum()
    )

    uid = 0
    for classif, r in piv.iterrows():
        uid += 1
        key = f"d_{tipo_nome[:3]}_{uid}"
        cor = cor_cat(classif, mapa_cores)
        # subdetalhes desta classificação
        sub = det[det["Classif"] == classif]
        tem_sub = sub["Detalhe"].nunique() > 1 or (
            sub["Detalhe"].nunique() == 1 and normalizar(sub["Detalhe"].iloc[0]) != normalizar(classif)
        )

        if tem_sub:
            label = (
                f"<label class='drill-label' for='{key}'>"
                f"<input type='checkbox' id='{key}' class='toggle-checkbox'>"
                f"<span class='indicator'>▶</span>"
                f"<span class='dot' style='background:{cor}'></span>{classif}"
                f"</label>"
            )
        else:
            label = f"<span class='dot' style='background:{cor}'></span>{classif}"

        cells = [moeda(r[m]) for m in refs_sel] + [f"<b>{moeda(r['__t__'])}</b>"]
        if tem_sub:
            rows_html.append(f"<tbody class='grp'><tr><td>{label}</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            # linhas filhas
            piv_sub = sub.pivot_table(index="Detalhe", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
            piv_sub = piv_sub.reindex(columns=refs_sel, fill_value=0.0)
            piv_sub["__t__"] = piv_sub.sum(axis=1)
            piv_sub = piv_sub.sort_values("__t__", ascending=False)
            for det_nome, rd in piv_sub.iterrows():
                sc = [moeda(rd[m]) for m in refs_sel] + [f"<b>{moeda(rd['__t__'])}</b>"]
                rows_html.append(
                    f"<tr class='sub-row'><td>↳ {det_nome}</td>" + "".join(f"<td>{c}</td>" for c in sc) + "</tr>"
                )
            rows_html.append("</tbody>")
        else:
            rows_html.append(f"<tr><td>{label}</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

    total = float(piv["__t__"].sum())
    tot_m = [float(piv[m].sum()) for m in refs_sel]
    rows_html.append(
        f"<tr class='tot'><td><b>Total {tipo_nome.lower()}</b></td>"
        + "".join(f"<td><span style='color:{cor_total}'>{moeda(v)}</span></td>" for v in tot_m)
        + f"<td><span style='color:{cor_total}'><b>{moeda(total)}</b></span></td></tr>"
    )
    return rows_html, total


if df.empty:
    st.markdown("<div class='vazio'>Sem dados no período</div>", unsafe_allow_html=True)
else:
    ent_df = df[df["Tipo"] == "Entrada"]
    sai_df = df[df["Tipo"] == "Saída"]

    html_rows, _ = bloco_classif(ent_df, "RECEITAS", VERDE)
    html_sai, _ = bloco_classif(sai_df, "SAÍDAS", VERMELHO)
    html_rows.extend(html_sai)

    # Resultado mensal
    ent_m = df[df["Tipo"] == "Entrada"].groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0.0)
    sai_m = df[df["Tipo"] == "Saída"].groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0.0)
    liq_m = ent_m - sai_m
    cells_res = []
    for m in refs_sel:
        v = float(liq_m.get(m, 0.0))
        cor = VERDE if v >= 0 else VERMELHO
        cells_res.append(f"<span style='color:{cor};font-weight:800'>{moeda(v)}</span>")
    cor_t = VERDE if liq >= 0 else VERMELHO
    html_rows.append(
        f"<tr class='res'><td><b>RESULTADO LÍQUIDO</b></td>"
        + "".join(f"<td>{c}</td>" for c in cells_res)
        + f"<td><span style='color:{cor_t}'><b>{moeda(liq)}</b></span></td></tr>"
    )

    th = "".join(f"<th>{h}</th>" for h in (["Descrição"] + x_lab + ["Total"]))
    body = "".join(html_rows)
    st.markdown(
        f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{th}</tr></thead>{body}</table></div>",
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
