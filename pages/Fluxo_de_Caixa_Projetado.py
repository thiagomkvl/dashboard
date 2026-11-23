import io
import re
import time
import unicodedata
from datetime import date, datetime

import pandas as pd
import streamlit as st

try:
    from database import conectar_sheets
except Exception as exc:
    conectar_sheets = None
    _DB_IMPORT_ERROR = str(exc)
else:
    _DB_IMPORT_ERROR = ""

st.set_page_config(
    page_title="Fluxo de Caixa Projetado",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================ CONFIGURAÇÃO =====================================
ABAS = [
    "1181", "PMTs", "1147", "Impostos", "Á Vista",
    "Classificacao_FCx", "Orçamento_Obra", "Realizado_Obra", "Resumo_FCx",
]
CACHE_SEGUNDOS = 90
SALDO_INICIAL_MANUAL = None

AZUL, VERDE, AMBAR, VERMELHO = "#2563eb", "#059669", "#d97706", "#dc2626"
ROXO = "#7c3aed"

MESES_PT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

MESES_MAP_NOME = {
    "jan": 1, "janeiro": 1,
    "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3,
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

# ================================ CSS =========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
.stApp, [data-testid="stAppViewContainer"] { background: #f8fafc !important; color: #0f172a; }
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 99%; padding: 1.1rem 1.4rem 2.2rem; }
[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e2e8f0; }
[data-testid="stWidgetLabel"] p { color: #64748b !important; font-size: 12px; font-weight: 600; }

/* Hero / Header */
.hero {
    display: flex; justify-content: space-between; align-items: center; gap: 16px;
    padding-bottom: 12px; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0;
}
.hero h1 { margin: 0; font-size: 22px; font-weight: 800; color: #0f172a; }
.hero p { margin: 2px 0 0; font-size: 13px; color: #64748b; }
.hero-badges { display: flex; gap: 10px; flex-wrap: wrap; }
.badge-box {
    background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 6px 14px; min-width: 120px; box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}
.badge-lbl { display: block; font-size: 10px; color: #64748b; font-weight: 600; }
.badge-val { font-size: 13px; font-weight: 800; color: #0f172a; margin-top: 2px; white-space: nowrap; }
.badge-val.pos { color: #059669; }
.badge-val.neg { color: #dc2626; }

.section-title {
    font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
    color: #0f172a; margin: 14px 0 10px; padding-left: 10px; border-left: 3px solid #2563eb;
}

/* Tabela no mesmo padrão do Fluxo de Caixa Realizado */
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
    cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
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

@media(max-width:950px){
    .hero { flex-direction: column; align-items: flex-start; }
}
</style>
""", unsafe_allow_html=True)

# ================================ HELPERS =====================================
def norm(v):
    if v is None or pd.isna(v):
        return ""
    s = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()

def col(df, candidates, fallback=None):
    lookup = {norm(c): c for c in df.columns}
    for cand in candidates:
        if norm(cand) in lookup:
            return lookup[norm(cand)]
    for c0 in df.columns:
        nc = norm(c0)
        for cand in candidates:
            if norm(cand) and norm(cand) in nc:
                return c0
    return fallback

def money(v):
    if v is None or pd.isna(v):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if not s or s in ("-", "—"):
        return 0.0
    neg = s.startswith("(") or s.startswith("-")
    s = s.strip("()-")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        x = float(s)
        return -x if neg else x
    except Exception:
        return 0.0

def dt(v):
    if v is None or pd.isna(v):
        return pd.NaT
    if isinstance(v, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(v).normalize()
    try:
        return pd.to_datetime(v, dayfirst=True, errors="coerce").normalize()
    except Exception:
        return pd.NaT

def parse_mes_coluna(c):
    d = dt(c)
    if not pd.isna(d) and d.day == 1:
        return pd.Timestamp(d.year, d.month, 1)

    s = norm(c)
    m1 = re.match(r"^(20\d{2}) (\d{1,2})$", s)
    if m1:
        y, m = int(m1.group(1)), int(m1.group(2))
        if 1 <= m <= 12:
            return pd.Timestamp(y, m, 1)

    m2 = re.match(r"^(\d{1,2}) (20\d{2})$", s)
    if m2:
        m, y = int(m2.group(1)), int(m2.group(2))
        if 1 <= m <= 12:
            return pd.Timestamp(y, m, 1)

    m3 = re.match(r"^([a-z]+) (\d{2,4})$", s)
    if m3 and m3.group(1) in MESES_MAP_NOME:
        m = MESES_MAP_NOME[m3.group(1)]
        y = int(m3.group(2))
        if y < 100:
            y += 2000
        return pd.Timestamp(y, m, 1)

    return pd.NaT

def brl(v):
    if v is None or pd.isna(v) or abs(float(v)) < 0.005:
        return "—"
    val = float(v)
    num = f"{abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {num}"

def brl_kpi(v):
    val = float(v or 0.0)
    sinal = "-" if val < -0.005 else ""
    num = f"{abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {sinal}{num}"

def brl_compacto(v):
    val = float(v or 0.0)
    sinal = "-" if val < -0.005 else ""
    av = abs(val)
    if av >= 1_000_000:
        return f"R$ {sinal}{av/1_000_000:,.1f}M".replace(".", ",")
    if av >= 1_000:
        return f"R$ {sinal}{av/1_000:,.1f}k".replace(".", ",")
    return brl_kpi(val)

def ler_aba(conn, name):
    err = None
    for wait in (0, 3, 8, 15):
        if wait:
            time.sleep(wait)
        try:
            df = conn.read(worksheet=name, ttl=0)
            return pd.DataFrame() if df is None else df.copy()
        except Exception as e:
            err = e
            msg = str(e).lower()
            if not any(x in msg for x in ("429", "quota", "resource_exhausted", "rate_limit")):
                raise
    raise err

@st.cache_data(ttl=CACHE_SEGUNDOS, show_spinner=False)
def carregar_fontes():
    if conectar_sheets is None:
        raise RuntimeError("Não foi possível importar database.conectar_sheets(): " + _DB_IMPORT_ERROR)
    conn = conectar_sheets()
    if conn is None:
        raise RuntimeError("conectar_sheets() retornou conexão vazia.")
    dados, erros = {}, {}
    for aba in ABAS:
        try:
            dados[aba] = ler_aba(conn, aba)
        except Exception as e:
            dados[aba] = pd.DataFrame()
            erros[aba] = str(e)
    return dados, erros

def criar_mov(data, valor, fonte, categoria, classificacao, fluxo, subgrupo, detalhe=""):
    data = dt(data)
    valor = money(valor)
    if pd.isna(data) or abs(valor) < 0.005:
        return None
    return {
        "Data": data,
        "Valor": valor,
        "Fonte": str(fonte),
        "Categoria": str(categoria or fonte),
        "Classificacao": str(classificacao or "Não classificado").strip(),
        "Fluxo": str(fluxo or "FCO").strip(),
        "Subgrupo": str(subgrupo or "").strip(),
        "Detalhe": str(detalhe or categoria or fonte).strip(),
    }

# =========================== CLASSIFICAÇÃO ====================================
def mapa_classificacao(df):
    out = {}
    if df is None or df.empty:
        return out
    c_desc = col(df, ["Descrição", "Conta contábil", "Categoria"], df.columns[0])
    c_cls = col(df, ["Classificação FCx", "Classificação"], df.columns[1] if len(df.columns) > 1 else None)
    c_flux = col(df, ["Fluxo de Caixa", "Fluxo"], df.columns[2] if len(df.columns) > 2 else None)
    for _, row in df.iterrows():
        desc = norm(row.get(c_desc))
        if not desc:
            continue
        cls = str(row.get(c_cls, "") or "").strip() or "Não classificado"
        flx = str(row.get(c_flux, "") or "").strip() or "Fluxo de Caixa Operacional"
        out[desc] = (cls, flx)
    return out

def normalizar_tipo_fluxo(flx_raw, cls_raw=""):
    nf = norm(flx_raw)
    nc = norm(cls_raw)
    if "invest" in nf or "fci" in nf or "capex" in nc or "obra" in nc or "aplicac" in nc:
        return "FCI"
    if "financ" in nf or "fcf" in nf or "emprest" in nc or "amortiz" in nc or "juros" in nc or "captac" in nc:
        return "FCF"
    if "nao classificado" in nc or "sem classificacao" in nc:
        return "NAO_CLASSIFICADO"
    return "FCO"

def classificar(text, mapping):
    n = norm(text)
    if n in mapping:
        cls, flx = mapping[n]
        return cls, normalizar_tipo_fluxo(flx, cls)
    matches = [(len(k), v) for k, v in mapping.items() if len(k) >= 4 and (k in n or n in k)]
    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        cls, flx = matches[0][1]
        return cls, normalizar_tipo_fluxo(flx, cls)
    return ("Não classificado", "NAO_CLASSIFICADO")

def is_fci(text, mapping):
    _, flx = classificar(text, mapping)
    if flx == "FCI":
        return True
    n = norm(text)
    return any(k in n for k in ("obra", "capex", "investimento", "aplicacao financeira", "imobilizado"))

# ===================== REALIZADO POR OBRA E MÊS ===============================
def calcular_realizado_obras(df_real):
    realizado_map = {}
    if df_real is None or df_real.empty:
        return realizado_map

    c_obra = col(df_real, ["Obra", "RESUMO OBRAS", "Centro de Custo", "Projeto", "Descrição", "Classificação"], df_real.columns[0])
    c_data = col(df_real, ["Data", "Dt. Pagamento", "Data Pagamento", "Vencimento", "Competência", "Mês"])
    c_val = col(df_real, ["Valor", "Vl. Pago", "Valor Pago", "Total", "Custo R$", "Saída"])
    c_status = col(df_real, ["Status", "Situação"])

    if c_data and c_val and c_data != c_obra and c_val != c_obra:
        work = df_real.copy()
        if c_status:
            work = work[~work[c_status].map(norm).isin(["cancelado", "cancelada", "estornado"])]
        for _, r in work.iterrows():
            obra_raw = str(r.get(c_obra, "") or "").strip()
            if not obra_raw or norm(obra_raw) in ("total", "total geral") or norm(obra_raw).startswith("total "):
                continue
            d = dt(r.get(c_data))
            v = abs(money(r.get(c_val)))
            if pd.isna(d) or v <= 0:
                continue
            chave = (norm(obra_raw), d.to_period("M"))
            realizado_map[chave] = realizado_map.get(chave, 0.0) + v
        return realizado_map

    cols_mes = []
    for c in df_real.columns:
        if c == c_obra:
            continue
        ref = parse_mes_coluna(c)
        if not pd.isna(ref):
            cols_mes.append((c, ref.to_period("M")))

    if cols_mes:
        for _, r in df_real.iterrows():
            obra_raw = str(r.get(c_obra, "") or "").strip()
            if not obra_raw or norm(obra_raw) in ("total", "total geral") or norm(obra_raw).startswith("total "):
                continue
            for c_mes, per in cols_mes:
                v = abs(money(r.get(c_mes, 0)))
                if v > 0:
                    chave = (norm(obra_raw), per)
                    realizado_map[chave] = realizado_map.get(chave, 0.0) + v

    return realizado_map

def obter_realizado_obra_mes(realizado_map, nome_obra, periodo_m):
    n_obra = norm(nome_obra)
    if (n_obra, periodo_m) in realizado_map:
        return realizado_map[(n_obra, periodo_m)]
    n_limpo = re.sub(r"^obra\s+", "", n_obra).strip()
    total = 0.0
    for (k_obra, k_per), val in realizado_map.items():
        if k_per != periodo_m:
            continue
        k_limpo = re.sub(r"^obra\s+", "", k_obra).strip()
        if n_limpo and k_limpo and (n_limpo == k_limpo or n_limpo in k_limpo or k_limpo in n_limpo):
            total += val
    return total

# ============================= PROJEÇÃO ======================================
def montar_projecao(dados, inicio, dias, media_dias, mapping):
    fim = inicio + pd.Timedelta(days=dias - 1)
    movs = []

    # 1. 1181 — Receitas previstas por data de vencimento (Convênios)
    df = dados.get("1181", pd.DataFrame())
    if not df.empty:
        c_data = col(df, ["Dt. Vencimento", "Data Vencimento", "Vencimento"])
        c_val = col(df, ["Valor", "Vl. Valor", "Total"])
        c_status = col(df, ["Estatus", "Status", "Situação"])
        c_cat = col(df, ["Convênio", "Tipo Protocolo", "Título"])
        c_prot = col(df, ["Protocolo", "Título", "Tipo Protocolo"])
        if c_data and c_val:
            work = df.copy()
            work["_data"] = work[c_data].map(dt)
            work["_valor"] = work[c_val].map(money)
            if c_status:
                status = work[c_status].map(norm)
                work = work[~status.isin(["cancelado", "cancelada", "excluido", "excluida"])]
            for _, r in work.iterrows():
                raw_cat = str(r.get(c_cat, "Convênio") or "Convênio").strip()
                prot = str(r.get(c_prot, "") or "").strip()
                det = prot if prot and norm(prot) != norm(raw_cat) else raw_cat
                cls_map, _ = classificar(raw_cat, mapping)
                classif = cls_map if cls_map != "Não classificado" else raw_cat
                m = criar_mov(
                    r["_data"], abs(r["_valor"]), "1181 — Receita", raw_cat,
                    classif, "FCO", "(+) Receitas operacionais", det
                )
                if m:
                    movs.append(m)

    # 2. PMTs — Prestação total (PMT) -> FCF
    df = dados.get("PMTs", pd.DataFrame())
    if not df.empty:
        c_data = col(df, ["Vcto", "Vencimento"])
        c_val = col(df, ["PMT", "Parcela"])
        c_bank = col(df, ["Banco"])
        c_tipo = col(df, ["Tipo", "Classificação"])
        c_contr = col(df, ["Contrato", "Parcela", "Banco"])
        if c_data and c_val:
            for _, r in df.iterrows():
                desc_pmt = str(r.get(c_tipo, "") or "").strip()
                classif = desc_pmt if desc_pmt else "Amortização e Juros de Empréstimos"
                det = f"{r.get(c_bank, '')} {r.get(c_contr, '')}".strip() or classif
                m = criar_mov(
                    r[c_data], -abs(money(r[c_val])), "PMTs", "Parcela empréstimo",
                    classif, "FCF", "(-) Amortização e juros de empréstimos", det
                )
                if m:
                    movs.append(m)

    # 3. 1147 — Contas a pagar em aberto, mapeadas via Classificacao_FCx
    df = dados.get("1147", pd.DataFrame())
    if not df.empty:
        c_data = col(df, ["Vencimento Atual", "Vencimento Original", "Vencimento"])
        c_val = col(df, ["Vl Saldo", "Valor Saldo", "Saldo"])
        c_status = col(df, ["Situação", "Status"])
        c_forn = col(df, ["Razão Social", "Fornecedor", "Título"])
        c_conta = col(df, ["Conta contábil", "Conta Financeira", "Categoria"])
        if c_data and c_val:
            work = df.copy()
            work["_data"] = work[c_data].map(dt)
            work["_valor"] = work[c_val].map(money)
            if c_status:
                work = work[~work[c_status].map(norm).isin(["liquidado", "pago", "baixado", "cancelado", "cancelada"])]
            work = work[work["_valor"] > 0.005]
            for _, r in work.iterrows():
                conta_txt = str(r.get(c_conta, "") or "").strip()
                forn_txt = str(r.get(c_forn, "") or "").strip()
                cls, flx = classificar(conta_txt or forn_txt, mapping)
                det = forn_txt or conta_txt or cls
                if flx == "FCI":
                    sub = "(-) Desembolsos em CAPEX"
                elif flx == "FCF":
                    sub = "(-) Amortização e juros de empréstimos"
                elif flx == "NAO_CLASSIFICADO":
                    sub = "Itens sem classificação gerencial"
                elif "impost" in norm(cls):
                    sub = "(-) Impostos"
                else:
                    sub = "(-) Custos e despesas operacionais"

                m = criar_mov(
                    r["_data"], -abs(r["_valor"]), "1147 — Contas a pagar",
                    conta_txt or forn_txt or "Conta a pagar", cls, flx, sub, det
                )
                if m:
                    movs.append(m)

    # 4. Impostos -> FCO / (-) Impostos
    df = dados.get("Impostos", pd.DataFrame())
    if not df.empty:
        c_data = col(df, ["Data", "Vencimento"])
        c_val = col(df, ["Valor", "Valor imposto"])
        c_cat = col(df, ["Tipo", "Beneficiario", "Beneficiário"])
        c_ben = col(df, ["Beneficiario", "Beneficiário"])
        if c_data and c_val:
            for _, r in df.iterrows():
                tipo_imp = str(r.get(c_cat, "Impostos Correntes") or "Impostos Correntes").strip()
                ben_imp = str(r.get(c_ben, "") or "").strip()
                cls_map, _ = classificar(tipo_imp, mapping)
                classif = cls_map if cls_map != "Não classificado" else tipo_imp
                m = criar_mov(
                    r[c_data], -abs(money(r[c_val])), "Impostos", tipo_imp,
                    classif, "FCO", "(-) Impostos", ben_imp or tipo_imp
                )
                if m:
                    movs.append(m)

    # 5. Á Vista — média de saídas históricas por dia corrido, sem FCI
    df = dados.get("Á Vista", pd.DataFrame())
    if not df.empty:
        c_data = col(df, ["Data", "Venc. original", "Vencimento"])
        c_val = col(df, ["Valor", "Vl. Valor"])
        c_nat = col(df, ["Natureza"])
        c_cat = col(df, ["Categoria", "Pagamento", "Observação"])
        c_status = col(df, ["Status", "Situação"])
        if c_data and c_val:
            work = df.copy()
            work["_data"] = work[c_data].map(dt)
            work["_valor"] = work[c_val].map(money)
            if c_nat:
                work = work[work[c_nat].map(norm).str.contains("saida|saída", na=False)]
            if c_status:
                work = work[~work[c_status].map(norm).isin(["cancelado", "cancelada", "estornado"])]
            if c_cat:
                work = work[~work[c_cat].map(lambda x: is_fci(x, mapping))]
            work = work[(work["_data"] < inicio) & (work["_data"] >= inicio - pd.Timedelta(days=media_dias)) & (work["_valor"] > 0)]
            media_aplicada = float(work["_valor"].sum()) / max(1, media_dias)
            if media_aplicada > 0:
                for d in pd.date_range(inicio, fim, freq="D"):
                    m = criar_mov(
                        d, -media_aplicada, "Á Vista — média diária", "Despesas à vista (média)",
                        "Outras Despesas Operacionais (À Vista)", "FCO",
                        "(-) Custos e despesas operacionais", f"Média {media_dias}d"
                    )
                    if m:
                        movs.append(m)

    # 6. Orçamento_Obra cruzado com Realizado_Obra -> FCI / (-) Desembolsos em CAPEX
    df_orc = dados.get("Orçamento_Obra", pd.DataFrame())
    realizado_obras_map = calcular_realizado_obras(dados.get("Realizado_Obra", pd.DataFrame()))

    if not df_orc.empty:
        cols_mes = []
        for c in df_orc.columns:
            ref = parse_mes_coluna(c)
            if not pd.isna(ref):
                cols_mes.append((c, ref))

        c_nome = col(df_orc, ["RESUMO OBRAS", "Obra", "Descrição"], df_orc.columns[0])
        for _, row in df_orc.iterrows():
            nome = str(row.get(c_nome, "") or "").strip()
            if not nome or norm(nome) in ("total", "total geral") or norm(nome).startswith("total "):
                continue

            for c_mes, ref in cols_mes:
                valor_orcado = money(row.get(c_mes, 0))
                if valor_orcado <= 0:
                    continue

                periodo_m = ref.to_period("M")
                valor_realizado = obter_realizado_obra_mes(realizado_obras_map, nome, periodo_m)
                saldo_a_realizar = max(0.0, valor_orcado - valor_realizado)
                if saldo_a_realizar <= 0.005:
                    continue

                fim_mes = ref + pd.offsets.MonthEnd(0)
                if fim_mes < inicio or ref > fim:
                    continue

                inicio_rateio = max(inicio, ref)
                fim_rateio = min(fim, fim_mes)
                dias_restantes_mes = (fim_mes - inicio_rateio).days + 1
                if dias_restantes_mes <= 0:
                    continue

                diario = saldo_a_realizar / dias_restantes_mes
                det_txt = f"{MESES_PT[ref.month]}/{str(ref.year)[2:]} (Orç. {brl_kpi(valor_orcado)} − Real. {brl_kpi(valor_realizado)})"
                for d in pd.date_range(inicio_rateio, fim_rateio, freq="D"):
                    m = criar_mov(
                        d, -diario, "Orçamento_Obra (Saldo)", f"Obra: {nome}",
                        f"Obra: {nome}", "FCI", "(-) Desembolsos em CAPEX", det_txt
                    )
                    if m:
                        movs.append(m)

    cols_base = ["Data", "Valor", "Fonte", "Categoria", "Classificacao", "Fluxo", "Subgrupo", "Detalhe"]
    base = pd.DataFrame(movs, columns=cols_base) if movs else pd.DataFrame(columns=cols_base)
    base = base[(base["Data"] >= inicio) & (base["Data"] <= fim)].copy()
    return base

# ===================== CONSTRUÇÃO DA MATRIZ (LÓGICA DO REALIZADO) ============
def construir_matriz_html(base_mov, inicio, dias, saldo_inicial, granularidade="Diária", consolidar_receitas=True):
    datas = pd.date_range(inicio, inicio + pd.Timedelta(days=dias - 1), freq="D")
    df = base_mov.copy()

    if granularidade == "Mensal":
        col_keys = sorted(datas.to_period("M").unique())
        col_labels = [f"{MESES_PT[p.month]}/{str(p.year)[2:]}" for p in col_keys]
        if not df.empty:
            df["_periodo"] = df["Data"].dt.to_period("M")
    else:
        col_keys = list(datas)
        col_labels = [d.strftime("%d/%m") for d in col_keys]
        if not df.empty:
            df["_periodo"] = df["Data"]

    def serie_vazia():
        return pd.Series(0.0, index=col_keys)

    def get_serie(filtro_df):
        if filtro_df.empty:
            return serie_vazia()
        s = filtro_df.groupby("_periodo")["Valor"].sum()
        return s.reindex(col_keys, fill_value=0.0)

    def linha_tot(label, s, cor, cls="tot", is_saldo=False):
        tot_val = float(s.iloc[0] if label == "(+) Saldo inicial" else s.iloc[-1]) if len(s) else 0.0
        if is_saldo:
            tot_html = f"<td><span style='color:{cor}'><b>{brl(tot_val)}</b></span></td>"
        else:
            tot_html = f"<td><span style='color:{cor}'><b>{brl(float(s.sum()))}</b></span></td>"
        return (
            f"<tr class='{cls}'><td><b>{label}</b></td>"
            + "".join(f"<td><span style='color:{cor}'>{brl(float(s.get(k, 0.0)))}</span></td>" for k in col_keys)
            + tot_html
            + "</tr>"
        )

    def linhas_com_abertura(sub_df, cor_dot, uid_prefix, label_consolidado=None):
        """Renderiza linhas agrupáveis exatamente como no Fluxo de Caixa Realizado,
        com sublinhas ('↳ Detalhe') alinhadas em cada coluna de data/mês."""
        if sub_df.empty:
            return []

        rows_out = []
        uid = 0

        if label_consolidado:
            uid += 1
            key = f"{uid_prefix}_{uid}"
            piv_main = (
                sub_df.groupby("_periodo")["Valor"]
                .sum()
                .reindex(col_keys, fill_value=0.0)
            )
            sub_det = (
                sub_df.groupby(["Detalhe", "_periodo"])["Valor"]
                .sum()
                .unstack(fill_value=0.0)
                .reindex(columns=col_keys, fill_value=0.0)
            )
            sub_det["__t__"] = sub_det.abs().sum(axis=1)
            sub_det = sub_det.sort_values("__t__", ascending=False)

            label_html = (
                f"<label class='drill-label' for='{key}'>"
                f"<input type='checkbox' id='{key}' class='toggle-checkbox'>"
                f"<span class='indicator'>▶</span>"
                f"<span class='dot' style='background:{cor_dot}'></span>{label_consolidado}</label>"
            )
            cells_main = [brl(float(piv_main[k])) for k in col_keys] + [f"<b>{brl(float(piv_main.sum()))}</b>"]
            rows_out.append(f"<tbody class='grp'><tr><td>{label_html}</td>" + "".join(f"<td>{c}</td>" for c in cells_main) + "</tr>")

            for dn, rd in sub_det.iterrows():
                sc = [brl(float(rd[k])) for k in col_keys] + [f"<b>{brl(float(rd.drop('__t__').sum()))}</b>"]
                rows_out.append(f"<tr class='sub-row'><td>↳ {dn}</td>" + "".join(f"<td>{c}</td>" for c in sc) + "</tr>")
            rows_out.append("</tbody>")
            return rows_out

        piv = (
            sub_df.groupby(["Classificacao", "_periodo"])["Valor"]
            .sum()
            .unstack(fill_value=0.0)
            .reindex(columns=col_keys, fill_value=0.0)
        )
        piv["__t__"] = piv.abs().sum(axis=1)
        piv = piv.sort_values("__t__", ascending=False)

        for classif, r in piv.iterrows():
            uid += 1
            key = f"{uid_prefix}_{uid}"
            sub = sub_df[sub_df["Classificacao"] == classif]
            tem_det = (
                sub["Detalhe"].nunique() > 1
                or (sub["Detalhe"].nunique() == 1 and norm(sub["Detalhe"].iloc[0]) != norm(classif))
            )

            if tem_det:
                label_html = (
                    f"<label class='drill-label' for='{key}'>"
                    f"<input type='checkbox' id='{key}' class='toggle-checkbox'>"
                    f"<span class='indicator'>▶</span>"
                    f"<span class='dot' style='background:{cor_dot}'></span>{classif}</label>"
                )
            else:
                label_html = f"<span class='dot' style='background:{cor_dot}'></span>{classif}"

            tot_linha = float(r.drop("__t__").sum())
            cells = [brl(float(r[k])) for k in col_keys] + [f"<b>{brl(tot_linha)}</b>"]

            if tem_det:
                rows_out.append(f"<tbody class='grp'><tr><td>{label_html}</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
                ps = (
                    sub.groupby(["Detalhe", "_periodo"])["Valor"]
                    .sum()
                    .unstack(fill_value=0.0)
                    .reindex(columns=col_keys, fill_value=0.0)
                )
                ps["__t__"] = ps.abs().sum(axis=1)
                ps = ps.sort_values("__t__", ascending=False)
                for dn, rd in ps.iterrows():
                    sc = [brl(float(rd[k])) for k in col_keys] + [f"<b>{brl(float(rd.drop('__t__').sum()))}</b>"]
                    rows_out.append(f"<tr class='sub-row'><td>↳ {dn}</td>" + "".join(f"<td>{c}</td>" for c in sc) + "</tr>")
                rows_out.append("</tbody>")
            else:
                rows_out.append(f"<tr><td>{label_html}</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

        return rows_out

    # ---------------- 1. FCO ----------------
    df_fco = df[df["Fluxo"] == "FCO"] if not df.empty else pd.DataFrame()
    s_fco = get_serie(df_fco)

    df_rec = df_fco[df_fco["Subgrupo"] == "(+) Receitas operacionais"] if not df_fco.empty else pd.DataFrame()
    s_rec = get_serie(df_rec)

    df_desp = df_fco[df_fco["Subgrupo"] == "(-) Custos e despesas operacionais"] if not df_fco.empty else pd.DataFrame()
    s_desp = get_serie(df_desp)

    df_imp = df_fco[df_fco["Subgrupo"] == "(-) Impostos"] if not df_fco.empty else pd.DataFrame()
    s_imp = get_serie(df_imp)

    # ---------------- 2. FCI ----------------
    df_fci = df[df["Fluxo"] == "FCI"] if not df.empty else pd.DataFrame()
    s_fci = get_serie(df_fci)

    df_fci_in = df_fci[df_fci["Valor"] > 0] if not df_fci.empty else pd.DataFrame()
    s_fci_in = get_serie(df_fci_in)

    df_fci_out = df_fci[df_fci["Valor"] < 0] if not df_fci.empty else pd.DataFrame()
    s_fci_out = get_serie(df_fci_out)

    # ---------------- 3. FCF ----------------
    df_fcf = df[df["Fluxo"] == "FCF"] if not df.empty else pd.DataFrame()
    s_fcf = get_serie(df_fcf)

    df_fcf_in = df_fcf[df_fcf["Valor"] > 0] if not df_fcf.empty else pd.DataFrame()
    s_fcf_in = get_serie(df_fcf_in)

    df_fcf_out = df_fcf[df_fcf["Valor"] < 0] if not df_fcf.empty else pd.DataFrame()
    s_fcf_out = get_serie(df_fcf_out)

    # ---------------- NÃO CLASSIFICADO ----------------
    df_nc = df[df["Fluxo"] == "NAO_CLASSIFICADO"] if not df.empty else pd.DataFrame()
    s_nc = get_serie(df_nc)

    # ---------------- VARIAÇÃO E SALDO ----------------
    s_var = s_fco + s_fci + s_fcf + s_nc
    s_ini = serie_vazia()
    s_fim = serie_vazia()
    acum = float(saldo_inicial)
    for k in col_keys:
        s_ini[k] = acum
        acum += float(s_var[k])
        s_fim[k] = acum

    html_rows = []
    export_rows = []

    def add_export(label, ser, is_saldo=False, blank=False):
        d = {"DESCRIÇÃO": label}
        if blank:
            for lbl in col_labels:
                d[lbl] = None
            d["TOTAL PERÍODO"] = None
        else:
            for k, lbl in zip(col_keys, col_labels):
                d[lbl] = float(ser[k])
            if is_saldo:
                d["TOTAL PERÍODO"] = float(s_ini.iloc[0] if "inicial" in label.lower() else s_fim.iloc[-1]) if len(col_keys) else float(saldo_inicial)
            else:
                d["TOTAL PERÍODO"] = float(ser.sum())
        export_rows.append(d)

    # 1. FCO
    html_rows.append(linha_tot("1. FLUXO DE CAIXA OPERACIONAL (FCO)", s_fco, VERDE if float(s_fco.sum()) >= 0 else VERMELHO, cls="caixa-total"))
    add_export("1. FLUXO DE CAIXA OPERACIONAL (FCO)", s_fco)

    html_rows.append(linha_tot("(+) Receitas operacionais", s_rec, VERDE, cls="subsec"))
    add_export("(+) Receitas operacionais", s_rec)
    html_rows.extend(linhas_com_abertura(
        df_rec, VERDE, "rec",
        label_consolidado="Convênios (Consolidado)" if consolidar_receitas else None
    ))

    html_rows.append(linha_tot("(−) Custos e despesas operacionais", s_desp, VERMELHO, cls="subsec"))
    add_export("(−) Custos e despesas operacionais", s_desp)
    html_rows.extend(linhas_com_abertura(df_desp, AZUL, "desp"))

    html_rows.append(linha_tot("(−) Impostos", s_imp, VERMELHO, cls="subsec"))
    add_export("(−) Impostos", s_imp)
    html_rows.extend(linhas_com_abertura(df_imp, AMBAR, "imp"))

    # 2. FCI
    html_rows.append(linha_tot("2. FLUXO DE CAIXA DE INVESTIMENTOS (FCI)", s_fci, VERDE if float(s_fci.sum()) >= 0 else VERMELHO, cls="caixa-total"))
    add_export("2. FLUXO DE CAIXA DE INVESTIMENTOS (FCI)", s_fci)

    if not df_fci_in.empty:
        html_rows.append(linha_tot("(+) Receitas de aplicações financeiras", s_fci_in, VERDE, cls="subsec"))
        add_export("(+) Receitas de aplicações financeiras", s_fci_in)
        html_rows.extend(linhas_com_abertura(df_fci_in, VERDE, "fci_in"))

    html_rows.append(linha_tot("(−) Desembolsos em CAPEX", s_fci_out, VERMELHO, cls="subsec"))
    add_export("(−) Desembolsos em CAPEX", s_fci_out)
    html_rows.extend(linhas_com_abertura(df_fci_out, VERMELHO, "fci_out"))

    # 3. FCF
    html_rows.append(linha_tot("3. FLUXO DE CAIXA DE FINANCIAMENTO (FCF)", s_fcf, VERDE if float(s_fcf.sum()) >= 0 else VERMELHO, cls="caixa-total"))
    add_export("3. FLUXO DE CAIXA DE FINANCIAMENTO (FCF)", s_fcf)

    if not df_fcf_in.empty:
        html_rows.append(linha_tot("(+) Empréstimos e Financiamentos", s_fcf_in, VERDE, cls="subsec"))
        add_export("(+) Empréstimos e Financiamentos", s_fcf_in)
        html_rows.extend(linhas_com_abertura(df_fcf_in, VERDE, "fcf_in"))

    html_rows.extend(linhas_com_abertura(df_fcf_out, ROXO, "fcf_out"))
    html_rows.append(linha_tot("Total amortizações e juros/encargos financeiros", s_fcf_out, VERMELHO, cls="tot"))
    add_export("Total amortizações e juros/encargos financeiros", s_fcf_out)

    # Variação líquida
    html_rows.append(linha_tot("VARIAÇÃO LÍQUIDA DE CAIXA (FCO + FCI + FCF)", s_var, VERDE if float(s_var.sum()) >= 0 else VERMELHO, cls="res"))
    add_export("VARIAÇÃO LÍQUIDA DE CAIXA (FCO + FCI + FCF)", s_var)

    # 4. Saldo de caixa
    html_rows.append(
        "<tr class='sec'><td>4. SALDO DE CAIXA</td>"
        + "".join("<td></td>" for _ in col_keys) + "<td></td></tr>"
    )
    add_export("4. SALDO DE CAIXA", serie_vazia(), blank=True)

    html_rows.append(linha_tot("(+) Saldo inicial", s_ini, AZUL, cls="saldo", is_saldo=True))
    add_export("(+) Saldo inicial", s_ini, is_saldo=True)

    html_rows.append(linha_tot("(+) Variação líquida do período", s_var, VERDE if float(s_var.sum()) >= 0 else VERMELHO, cls="tot"))
    add_export("(+) Variação líquida do período", s_var)

    saldo_fim_total = float(s_fim.iloc[-1]) if len(s_fim) else float(saldo_inicial)
    html_rows.append(linha_tot("(=) Saldo final projetado", s_fim, VERDE if saldo_fim_total >= 0 else VERMELHO, cls="saldo", is_saldo=True))
    add_export("(=) Saldo final projetado", s_fim, is_saldo=True)

    # Não classificado
    if not df_nc.empty:
        html_rows.append(
            "<tr class='sec'><td>ITENS SEM CLASSIFICAÇÃO GERENCIAL</td>"
            + "".join("<td></td>" for _ in col_keys) + "<td></td></tr>"
        )
        add_export("ITENS SEM CLASSIFICAÇÃO GERENCIAL", s_nc)
        html_rows.extend(linhas_com_abertura(df_nc, AMBAR, "nc"))

    th = "".join(f"<th>{h}</th>" for h in (["Descrição"] + col_labels + ["Total"]))
    tabela_html = (
        f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{th}</tr></thead>"
        f"{''.join(html_rows)}</table></div>"
    )

    return tabela_html, pd.DataFrame(export_rows), float(s_var.sum())

def gerar_excel_bytes(df_matriz, df_detalhe):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_matriz.to_excel(writer, sheet_name="Demonstrativo_Projetado", index=False)
        if not df_detalhe.empty:
            df_detalhe.to_excel(writer, sheet_name="Composicao_Transacoes", index=False)
    return buf.getvalue()

# ============================== SIDEBAR =======================================
with st.sidebar:
    st.markdown("### Parâmetros da projeção")
    hoje = pd.Timestamp.today().normalize()
    inicio = st.date_input("Data inicial", value=hoje.date(), format="DD/MM/YYYY")
    dias = st.select_slider("Horizonte (dias)", options=[7, 15, 30, 45, 60, 90, 120, 180], value=30)
    granularidade = st.radio(
        "Colunas do demonstrativo",
        options=["Diária", "Mensal"],
        index=0 if dias <= 45 else 1,
        horizontal=True,
    )
    consolidar_receitas = st.checkbox(
        "Consolidar receitas operacionais (Convênios)",
        value=True,
        help="Agrupa todos os convênios do 1181 em uma única linha. Desmarque para abrir por convênio."
    )
    media_dias = st.select_slider("Janela média Á Vista", options=[30, 60, 90], value=30)
    st.caption("A média de Á Vista considera dias corridos e exclui despesas identificadas como FCI.")
    st.divider()
    if st.button("Atualizar dados do Sheets", use_container_width=True):
        carregar_fontes.clear()
        st.rerun()

# ============================== CARREGAMENTO ==================================
try:
    fontes, erros = carregar_fontes()
except Exception as exc:
    st.error(f"Falha ao conectar ao Google Sheets: {exc}")
    st.stop()

mapping = mapa_classificacao(fontes.get("Classificacao_FCx", pd.DataFrame()))
saldo = SALDO_INICIAL_MANUAL

resumo = fontes.get("Resumo_FCx", pd.DataFrame())
if saldo is None and not resumo.empty:
    c_saldo = col(resumo, ["Saldo atual", "Saldo final", "Saldo caixa", "Saldo"])
    c_data = col(resumo, ["Data", "Mês", "Data movimento", "Competência"])
    if c_saldo:
        vals = resumo[c_saldo].map(money)
        if c_data:
            dates = resumo[c_data].map(dt)
            valid = dates.notna() & vals.notna()
            if valid.any():
                saldo = float(vals[valid].iloc[-1])
        elif vals.notna().any():
            saldo = float(vals.dropna().iloc[-1])

if saldo is None:
    saldo = 0.0

inicio_ts = pd.Timestamp(inicio)
fim_ts = inicio_ts + pd.Timedelta(days=int(dias) - 1)
base_mov = montar_projecao(fontes, inicio_ts, int(dias), int(media_dias), mapping)

tabela_html, df_export, variacao_liquida = construir_matriz_html(
    base_mov,
    inicio_ts,
    int(dias),
    float(saldo),
    granularidade=granularidade,
    consolidar_receitas=consolidar_receitas,
)

# ============================== INTERFACE =====================================
periodo_str = f"{inicio_ts.strftime('%d/%m/%y')} – {fim_ts.strftime('%d/%m/%y')}"
var_cls = "pos" if variacao_liquida >= 0 else "neg"

st.markdown(f"""
<div class="hero">
    <div>
        <h1>FLUXO DE CAIXA PROJETADO</h1>
        <p>Visão gerencial · FCO · FCI · FCF · Saldo de caixa · {dias} dias</p>
    </div>
    <div class="hero-badges">
        <div class="badge-box">
            <span class="badge-lbl">Período</span>
            <div class="badge-val">{periodo_str}</div>
        </div>
        <div class="badge-box">
            <span class="badge-lbl">Variação líquida</span>
            <div class="badge-val {var_cls}">{brl_compacto(variacao_liquida)}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.download_button(
    label="⬇ Baixar Excel",
    data=gerar_excel_bytes(df_export, base_mov),
    file_name=f"Fluxo_Caixa_Projetado_{inicio_ts.strftime('%Y%m%d')}_{dias}d.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.markdown(
    "<div class='section-title'>Demonstrativo · FCO / FCI / FCF · Saldo de caixa · clique na seta para composição</div>",
    unsafe_allow_html=True,
)
st.markdown(tabela_html, unsafe_allow_html=True)
