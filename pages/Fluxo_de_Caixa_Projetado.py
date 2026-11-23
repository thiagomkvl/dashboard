import html
import io
import json
import re
import time
import unicodedata
from datetime import date, datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
html, body, [class*="css"] { font-family: Inter, Segoe UI, Arial, sans-serif; }
.stApp { background:#f8fafc; color:#0f172a; }
[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer { visibility:hidden; }
.block-container { max-width:99%; padding:1.2rem 1.4rem 2.5rem; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid #e2e8f0; }
[data-testid="stWidgetLabel"] p { color:#64748b !important; font-size:12px; font-weight:650; }

/* Hero / Header */
.hero { display:flex; justify-content:space-between; align-items:flex-start; gap:15px;
        padding:2px 0 12px; margin-bottom:6px; }
.hero h1 { margin:0; font-size:23px; font-weight:850; color:#0f172a; letter-spacing:-0.3px; }
.hero p { margin:4px 0 0; color:#64748b; font-size:12.5px; }
.hero-badges { display:flex; gap:10px; align-items:center; }
.badge-box { background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:6px 12px; min-width:120px; }
.badge-lbl { font-size:10px; color:#64748b; font-weight:600; }
.badge-val { font-size:12.5px; font-weight:800; color:#0f172a; margin-top:2px; }
.badge-val.pos { color:#059669; }
.badge-val.neg { color:#dc2626; }

@media(max-width:950px){
    .hero{flex-direction:column;}
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
    """Identifica colunas mensais como 2026-11, 11/2026, Nov/26, Novembro/2026, 01/11/2026."""
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
    sinal = "-" if val < 0 else ""
    num = f"{abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {sinal}{num}"

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
        "Detalhe": str(detalhe or categoria or fonte),
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
                det = f"{raw_cat} — {prot}" if prot and prot != raw_cat else raw_cat
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
                det = f"{r.get(c_bank, '')} {r.get(c_contr, '')}".strip() or "Parcela PMT"
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
        c_tit = col(df, ["Título", "Documento", "Histórico"])
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
                tit_txt = str(r.get(c_tit, "") or "").strip()
                det = f"{forn_txt} · Título {tit_txt}".strip(" ·") if tit_txt and tit_txt != forn_txt else (forn_txt or conta_txt)
                cls, flx = classificar(conta_txt or forn_txt, mapping)
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
    media_aplicada = 0.0
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
                        "(-) Custos e despesas operacionais", f"Média diária ({media_dias}d históricos)"
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
                det_txt = (
                    f"Orçado {MESES_PT[ref.month]}/{str(ref.year)[2:]}: {brl_kpi(valor_orcado)} | "
                    f"Realizado: {brl_kpi(valor_realizado)} | Saldo: {brl_kpi(saldo_a_realizar)}"
                )
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

# ===================== CONSTRUÇÃO DA MATRIZ INTERATIVA ======================
def construir_matriz_component(base_mov, inicio, dias, saldo_inicial, granularidade="Diária", consolidar_receitas=True):
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

    def montar_detalhes_linha(sub_df):
        if sub_df.empty:
            return []
        s_ord = sub_df.sort_values(["Data", "Valor"])
        registros = []
        for _, r in s_ord.iterrows():
            registros.append({
                "data": r["Data"].strftime("%d/%m/%Y"),
                "fonte": r["Fonte"],
                "classificacao": r["Classificacao"],
                "detalhe": r["Detalhe"],
                "valor": float(r["Valor"]),
                "valor_fmt": brl_kpi(r["Valor"]),
            })
        return registros

    def linhas_classificacao(sub_df, dot_color="dot-blue"):
        if sub_df.empty:
            return []
        grp = (
            sub_df.groupby(["Classificacao", "_periodo"])["Valor"]
            .sum()
            .unstack(fill_value=0.0)
            .reindex(columns=col_keys, fill_value=0.0)
        )
        ordem = grp.abs().sum(axis=1).sort_values(ascending=False).index
        out = []
        for cls in ordem:
            df_cls = sub_df[sub_df["Classificacao"] == cls]
            out.append({
                "label": cls,
                "tipo": "item",
                "dot": dot_color,
                "vals": grp.loc[cls],
                "detalhes": montar_detalhes_linha(df_cls),
            })
        return out

    linhas = []
    export_rows = []

    # ---------------- 1. FCO ----------------
    df_fco = df[df["Fluxo"] == "FCO"] if not df.empty else pd.DataFrame()
    s_fco = get_serie(df_fco)
    linhas.append({"label": "1. FLUXO DE CAIXA OPERACIONAL (FCO)", "tipo": "section", "vals": s_fco})

    # (+) Receitas operacionais
    df_rec = df_fco[df_fco["Subgrupo"] == "(+) Receitas operacionais"] if not df_fco.empty else pd.DataFrame()
    s_rec = get_serie(df_rec)
    linhas.append({"label": "(+) Receitas operacionais", "tipo": "subtotal", "vals": s_rec})
    if consolidar_receitas:
        linhas.append({
            "label": "Convênios (Consolidado)",
            "tipo": "item",
            "dot": "dot-green",
            "vals": s_rec,
            "detalhes": montar_detalhes_linha(df_rec),
        })
    else:
        linhas.extend(linhas_classificacao(df_rec, "dot-green"))

    # (-) Custos e despesas operacionais
    df_desp = df_fco[df_fco["Subgrupo"] == "(-) Custos e despesas operacionais"] if not df_fco.empty else pd.DataFrame()
    s_desp = get_serie(df_desp)
    linhas.append({"label": "(-) Custos e despesas operacionais", "tipo": "subtotal", "vals": s_desp})
    linhas.extend(linhas_classificacao(df_desp, "dot-blue"))

    # (-) Impostos
    df_imp = df_fco[df_fco["Subgrupo"] == "(-) Impostos"] if not df_fco.empty else pd.DataFrame()
    s_imp = get_serie(df_imp)
    linhas.append({"label": "(-) Impostos", "tipo": "subtotal", "vals": s_imp})
    linhas.extend(linhas_classificacao(df_imp, "dot-amber"))

    # ---------------- 2. FCI ----------------
    df_fci = df[df["Fluxo"] == "FCI"] if not df.empty else pd.DataFrame()
    s_fci = get_serie(df_fci)
    linhas.append({"label": "2. FLUXO DE CAIXA DE INVESTIMENTOS (FCI)", "tipo": "section", "vals": s_fci})

    df_fci_in = df_fci[df_fci["Valor"] > 0] if not df_fci.empty else pd.DataFrame()
    if not df_fci_in.empty:
        linhas.append({"label": "(+) Receitas de aplicações financeiras", "tipo": "subtotal", "vals": get_serie(df_fci_in)})
        linhas.extend(linhas_classificacao(df_fci_in, "dot-green"))

    df_fci_out = df_fci[df_fci["Valor"] < 0] if not df_fci.empty else pd.DataFrame()
    linhas.append({"label": "(-) Desembolsos em CAPEX", "tipo": "subtotal", "vals": get_serie(df_fci_out)})
    linhas.extend(linhas_classificacao(df_fci_out, "dot-red"))

    # ---------------- 3. FCF ----------------
    df_fcf = df[df["Fluxo"] == "FCF"] if not df.empty else pd.DataFrame()
    s_fcf = get_serie(df_fcf)
    linhas.append({"label": "3. FLUXO DE CAIXA DE FINANCIAMENTO (FCF)", "tipo": "section", "vals": s_fcf})

    df_fcf_in = df_fcf[df_fcf["Valor"] > 0] if not df_fcf.empty else pd.DataFrame()
    if not df_fcf_in.empty:
        linhas.append({"label": "(+) Captações e Empréstimos", "tipo": "subtotal", "vals": get_serie(df_fcf_in)})
        linhas.extend(linhas_classificacao(df_fcf_in, "dot-green"))

    df_fcf_out = df_fcf[df_fcf["Valor"] < 0] if not df_fcf.empty else pd.DataFrame()
    linhas.append({"label": "(-) Amortização e juros de empréstimos", "tipo": "subtotal", "vals": get_serie(df_fcf_out)})
    linhas.extend(linhas_classificacao(df_fcf_out, "dot-purple"))

    # ---------------- NÃO CLASSIFICADO ----------------
    df_nc = df[df["Fluxo"] == "NAO_CLASSIFICADO"] if not df.empty else pd.DataFrame()
    if not df_nc.empty:
        s_nc = get_serie(df_nc)
        linhas.append({"label": "ITENS SEM CLASSIFICAÇÃO GERENCIAL", "tipo": "section", "vals": s_nc})
        linhas.extend(linhas_classificacao(df_nc, "dot-amber"))
    else:
        s_nc = serie_vazia()

    # ---------------- VARIAÇÃO E SALDO DE CAIXA ----------------
    s_var = s_fco + s_fci + s_fcf + s_nc
    linhas.append({"label": "VARIAÇÃO LÍQUIDA DE CAIXA (FCO + FCI + FCF)", "tipo": "highlight", "vals": s_var})
    linhas.append({"label": "4. SALDO DE CAIXA", "tipo": "section", "vals": serie_vazia(), "blank_vals": True})

    s_ini = serie_vazia()
    s_fim = serie_vazia()
    acum = float(saldo_inicial)
    for k in col_keys:
        s_ini[k] = acum
        acum += float(s_var[k])
        s_fim[k] = acum

    linhas.append({"label": "(+) Saldo inicial", "tipo": "item", "dot": None, "vals": s_ini})
    linhas.append({"label": "(+) Variação líquida do período", "tipo": "item", "dot": None, "vals": s_var})
    linhas.append({"label": "(=) Saldo final projetado", "tipo": "highlight", "vals": s_fim})

    # Montagem HTML interativa com painel alinhado à esquerda (sticky) e auto-resize
    num_cols = len(col_labels) + 2
    header_cells = "".join([f"<th>{html.escape(lbl)}</th>" for lbl in col_labels]) + "<th>TOTAL PERÍODO</th>"
    body_html = []
    detalhes_payload = {}
    row_idx = 0

    for row in linhas:
        tipo = row["tipo"]
        tr_cls = f"row-{tipo}"
        vals = row["vals"]
        blank_vals = row.get("blank_vals", False)
        detalhes = row.get("detalhes", [])
        tem_drill = (tipo == "item" and len(detalhes) > 0)

        if row["label"] == "(+) Saldo inicial":
            total_val = float(s_ini.iloc[0]) if len(s_ini) else float(saldo_inicial)
        elif row["label"] == "(=) Saldo final projetado":
            total_val = float(s_fim.iloc[-1]) if len(s_fim) else float(saldo_inicial)
        else:
            total_val = float(vals.sum())

        rid = f"r_{row_idx}"
        row_idx += 1

        if tem_drill:
            detalhes_payload[rid] = detalhes
            lbl_html = (
                f'<div class="lbl-flex">'
                f'<span class="lbl-left">'
                f'<span class="caret" id="caret_{rid}">▶</span>'
                f'<span class="dot {row["dot"]}"></span>'
                f'<span class="lbl-text" title="{html.escape(row["label"])}">{html.escape(row["label"])}</span>'
                f'</span>'
                f'<span class="badge-cnt">{len(detalhes)}</span>'
                f'</div>'
            )
            tr_attr = f'id="row_{rid}" class="{tr_cls} clickable-row" onclick="toggleRow(\'{rid}\')"'
        elif tipo == "item" and row.get("dot"):
            lbl_html = (
                f'<div class="lbl-flex">'
                f'<span class="lbl-left">'
                f'<span class="caret" style="opacity:.35;">▶</span>'
                f'<span class="dot {row["dot"]}"></span>'
                f'<span class="lbl-text">{html.escape(row["label"])}</span>'
                f'</span>'
                f'</div>'
            )
            tr_attr = f'class="{tr_cls}"'
        else:
            lbl_html = html.escape(row["label"])
            tr_attr = f'class="{tr_cls}"'

        tds = [f"<td>{lbl_html}</td>"]
        exp_dict = {"DESCRIÇÃO": row["label"]}

        for k, lbl in zip(col_keys, col_labels):
            if blank_vals:
                tds.append("<td></td>")
                exp_dict[lbl] = None
                continue
            v = float(vals[k])
            exp_dict[lbl] = v
            if abs(v) < 0.005:
                tds.append('<td class="v-zero">—</td>')
            else:
                cls_cor = "v-pos" if v > 0 else "v-neg"
                tds.append(f'<td class="{cls_cor}">{brl(v)}</td>')

        if blank_vals:
            tds.append("<td></td>")
            exp_dict["TOTAL PERÍODO"] = None
        else:
            exp_dict["TOTAL PERÍODO"] = total_val
            if abs(total_val) < 0.005:
                tds.append('<td class="v-zero">—</td>')
            else:
                cls_cor = "v-pos" if total_val > 0 else "v-neg"
                tds.append(f'<td class="{cls_cor}">{brl(total_val)}</td>')

        export_rows.append(exp_dict)
        body_html.append(f'<tr {tr_attr}>{"".join(tds)}</tr>')

        # Linha oculta de drill-down alinhada à esquerda (sticky) para não exigir scroll horizontal
        if tem_drill:
            body_html.append(
                f'<tr id="detail_{rid}" class="detail-row" style="display:none;">'
                f'<td colspan="{num_cols}" class="detail-cell">'
                f'<div class="detail-sticky">'
                f'<div id="box_{rid}" class="detail-container"></div>'
                f'</div>'
                f'</td></tr>'
            )

    payload_json = json.dumps(detalhes_payload, ensure_ascii=False)
    altura_inicial = min(1300, max(540, 115 + len(linhas) * 35))

    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * {{ box-sizing: border-box; }}
    body {{
        margin:0;
        padding:0;
        font-family: Inter, Segoe UI, Arial, sans-serif;
        background:transparent;
        color:#0f172a;
    }}
    .matrix-bar {{
        background:#e2e8f0;
        color:#334155;
        font-size:11px;
        font-weight:800;
        letter-spacing:0.4px;
        padding:9px 14px;
        border-radius:8px 8px 0 0;
        border:1px solid #cbd5e1;
        border-bottom:none;
        text-transform:uppercase;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
    }}
    .matrix-hint {{
        font-size:10.5px;
        font-weight:600;
        color:#475569;
        text-transform:none;
        letter-spacing:0;
        white-space:nowrap;
    }}
    .fcx-wrap {{
        width:100%;
        overflow-x:auto;
        background:#fff;
        border:1px solid #cbd5e1;
        border-radius:0 0 8px 8px;
        box-shadow:0 1px 3px rgba(15,23,42,0.04);
    }}
    table.fcx-table {{
        width:100%;
        border-collapse:collapse;
        font-size:12px;
        white-space:nowrap;
    }}
    table.fcx-table th {{
        background:#f1f5f9;
        color:#475569;
        font-size:10.5px;
        font-weight:800;
        text-transform:uppercase;
        padding:9px 12px;
        border-bottom:1px solid #cbd5e1;
        text-align:right;
    }}
    table.fcx-table th:first-child {{
        text-align:left;
        position:sticky;
        left:0;
        z-index:3;
        background:#f1f5f9;
        min-width:320px;
        max-width:340px;
        border-right:1px solid #cbd5e1;
    }}
    table.fcx-table td {{
        padding:8px 12px;
        border-bottom:1px solid #f1f5f9;
        text-align:right;
        font-variant-numeric:tabular-nums;
    }}
    table.fcx-table td:first-child {{
        text-align:left;
        position:sticky;
        left:0;
        z-index:2;
        min-width:320px;
        max-width:340px;
        border-right:1px solid #cbd5e1;
    }}
    tr.row-section td {{
        background:#cbd5e1 !important;
        color:#0f172a;
        font-weight:800;
        font-size:11.5px;
        border-top:1px solid #94a3b8;
        border-bottom:1px solid #94a3b8;
    }}
    tr.row-subtotal td {{
        background:#e2e8f0 !important;
        color:#1e293b;
        font-weight:750;
        border-top:1px solid #cbd5e1;
        border-bottom:1px solid #cbd5e1;
    }}
    tr.row-highlight td {{
        background:#f1f5f9 !important;
        color:#0f172a;
        font-weight:800;
        border-top:1px solid #cbd5e1;
        border-bottom:1px solid #cbd5e1;
    }}
    tr.row-item td {{
        background:#ffffff;
        color:#334155;
        font-weight:500;
    }}
    tr.clickable-row {{ cursor:pointer; }}
    tr.clickable-row:hover td {{ background:#eff6ff !important; }}
    tr.clickable-row.expanded td {{
        background:#dbeafe !important;
        color:#1e3a8a;
        font-weight:700;
        border-bottom-color:#93c5fd;
    }}
    tr.row-item td:first-child {{ padding-left:18px; }}

    /* Alinhamento flex do rótulo + badge de contagem na coluna esquerda */
    .lbl-flex {{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:8px;
        width:100%;
    }}
    .lbl-left {{
        display:flex;
        align-items:center;
        min-width:0;
        overflow:hidden;
    }}
    .lbl-text {{
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
    }}

    .v-pos {{ color:#059669; font-weight:700; }}
    .v-neg {{ color:#dc2626; font-weight:700; }}
    .v-zero {{ color:#94a3b8; font-weight:400; }}

    .dot {{
        display:inline-block;
        flex-shrink:0;
        width:7px;
        height:7px;
        border-radius:50%;
        margin-right:7px;
    }}
    .dot-blue {{ background:#2563eb; }}
    .dot-green {{ background:#10b981; }}
    .dot-red {{ background:#ef4444; }}
    .dot-amber {{ background:#f59e0b; }}
    .dot-purple {{ background:#8b5cf6; }}

    .caret {{
        display:inline-block;
        flex-shrink:0;
        color:#2563eb;
        font-size:9px;
        margin-right:6px;
        transition:transform 0.16s ease;
    }}
    .caret.open {{ transform:rotate(90deg); }}

    .badge-cnt {{
        flex-shrink:0;
        background:#f1f5f9;
        color:#475569;
        border:1px solid #cbd5e1;
        border-radius:10px;
        padding:1px 7px;
        font-size:10px;
        font-weight:700;
    }}
    tr.clickable-row.expanded .badge-cnt {{
        background:#2563eb;
        color:#ffffff;
        border-color:#2563eb;
    }}

    /* Bloco de abertura ancorado à esquerda (sem necessidade de scroll horizontal) */
    td.detail-cell {{
        padding:0 !important;
        background:#f8fafc !important;
        text-align:left !important;
        position:static !important;
        border-bottom:1px solid #cbd5e1 !important;
    }}
    .detail-sticky {{
        position:sticky;
        left:0;
        width:min(96vw, 1040px);
        padding:10px 14px 14px 26px;
        border-left:3px solid #2563eb;
        background:#f8fafc;
    }}
    .detail-toolbar {{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        margin-bottom:8px;
        flex-wrap:wrap;
    }}
    .detail-summary {{
        font-size:11px;
        color:#475569;
        font-weight:650;
    }}
    .detail-search {{
        border:1px solid #cbd5e1;
        border-radius:6px;
        padding:4px 9px;
        font-size:11.5px;
        font-family:inherit;
        color:#0f172a;
        background:#fff;
        min-width:230px;
        outline:none;
    }}
    .detail-search:focus {{
        border-color:#2563eb;
        box-shadow:0 0 0 2px rgba(37,99,235,0.12);
    }}
    .sub-scroll {{
        max-height:290px;
        overflow-y:auto;
        border:1px solid #cbd5e1;
        border-radius:6px;
        background:#fff;
    }}
    table.sub-table {{
        width:100%;
        border-collapse:collapse;
        font-size:11.5px;
        table-layout:fixed;
    }}
    table.sub-table thead th {{
        position:sticky;
        top:0;
        z-index:2;
        background:#f1f5f9;
        color:#475569;
        font-size:10px;
        font-weight:800;
        text-transform:uppercase;
        padding:7px 10px;
        text-align:left;
        border-bottom:1px solid #cbd5e1;
        min-width:auto !important;
        max-width:none !important;
        border-right:none !important;
    }}
    table.sub-table thead th:last-child,
    table.sub-table tbody td:last-child {{
        text-align:right;
    }}
    table.sub-table tbody td {{
        padding:6px 10px;
        border-bottom:1px solid #f1f5f9;
        text-align:left;
        position:static !important;
        min-width:auto !important;
        max-width:none !important;
        border-right:none !important;
        white-space:normal;
        word-break:break-word;
        vertical-align:middle;
    }}
    table.sub-table tbody tr:nth-child(even) td {{
        background:#fcfdfe;
    }}
    table.sub-table tbody tr:hover td {{
        background:#eff6ff;
    }}
    </style>
    </head>
    <body>
    <div id="app-root">
        <div class="matrix-bar">
            <span>DEMONSTRATIVO PROJETADO • FCO / FCI / FCF / SALDO DE CAIXA • POR CLASSIFICAÇÃO FINANCEIRA</span>
            <span class="matrix-hint">Clique em qualquer linha com ▶ para detalhar</span>
        </div>
        <div class="fcx-wrap">
            <table class="fcx-table">
                <thead><tr><th>DESCRIÇÃO</th>{header_cells}</tr></thead>
                <tbody>{"".join(body_html)}</tbody>
            </table>
        </div>
    </div>

    <script>
    const DETALHES = {payload_json};

    function escapeHtml(str) {{
        return String(str || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }}

    function formatBRL(val) {{
        const num = Number(val || 0);
        const sign = num < -0.005 ? "-" : "";
        const abs = Math.abs(num).toLocaleString("pt-BR", {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        return `R$ ${{sign}}${{abs}}`;
    }}

    function resizeFrame() {{
        const root = document.getElementById("app-root");
        if (!root) return;
        const h = Math.ceil(root.getBoundingClientRect().height) + 16;
        if (window.parent) {{
            window.parent.postMessage({{
                isStreamlitMessage: true,
                type: "streamlit:setFrameHeight",
                height: h
            }}, "*");
        }}
    }}

    function renderSubRows(rid, termo) {{
        const itens = DETALHES[rid] || [];
        const q = (termo || "").toLowerCase().trim();
        const filtrados = q
            ? itens.filter(it =>
                (it.data + " " + it.fonte + " " + it.classificacao + " " + it.detalhe + " " + it.valor_fmt)
                    .toLowerCase()
                    .includes(q)
              )
            : itens;

        const tbody = document.getElementById("sub_body_" + rid);
        const sumEl = document.getElementById("sub_sum_" + rid);
        if (!tbody) return;

        let total = 0;
        tbody.innerHTML = filtrados.map(it => {{
            total += Number(it.valor || 0);
            const cls = it.valor >= 0 ? "v-pos" : "v-neg";
            return `<tr>
                <td>${{escapeHtml(it.data)}}</td>
                <td>${{escapeHtml(it.fonte)}}</td>
                <td>${{escapeHtml(it.classificacao)}}</td>
                <td>${{escapeHtml(it.detalhe)}}</td>
                <td class="${{cls}}">${{escapeHtml(it.valor_fmt)}}</td>
            </tr>`;
        }}).join("");

        if (sumEl) {{
            const clsTot = total >= 0 ? "v-pos" : "v-neg";
            sumEl.innerHTML = `Exibindo <b>${{filtrados.length}}</b> de <b>${{itens.length}}</b> lançamento(s) · Total: <span class="${{clsTot}}">${{formatBRL(total)}}</span>`;
        }}
        resizeFrame();
    }}

    function toggleRow(rid) {{
        const tr = document.getElementById("detail_" + rid);
        const parentRow = document.getElementById("row_" + rid);
        const caret = document.getElementById("caret_" + rid);
        const box = document.getElementById("box_" + rid);
        if (!tr) return;

        const isHidden = (tr.style.display === "none" || tr.style.display === "");
        if (isHidden) {{
            if (!box.dataset.rendered) {{
                const itens = DETALHES[rid] || [];
                const showSearch = itens.length > 6;
                const searchInput = showSearch
                    ? `<input type="text" class="detail-search" placeholder="Filtrar lançamentos..." oninput="renderSubRows('${{rid}}', this.value)" onclick="event.stopPropagation()">`
                    : "";

                box.innerHTML = `
                    <div class="detail-toolbar">
                        <div class="detail-summary" id="sub_sum_${{rid}}"></div>
                        ${{searchInput}}
                    </div>
                    <div class="sub-scroll">
                        <table class="sub-table">
                            <colgroup>
                                <col style="width:95px;">
                                <col style="width:165px;">
                                <col style="width:210px;">
                                <col style="width:auto;">
                                <col style="width:130px;">
                            </colgroup>
                            <thead>
                                <tr>
                                    <th>Data</th>
                                    <th>Origem</th>
                                    <th>Classificação</th>
                                    <th>Descrição / Composição</th>
                                    <th>Valor</th>
                                </tr>
                            </thead>
                            <tbody id="sub_body_${{rid}}"></tbody>
                        </table>
                    </div>
                `;
                box.dataset.rendered = "1";
                renderSubRows(rid, "");
            }}
            tr.style.display = "table-row";
            if (caret) caret.classList.add("open");
            if (parentRow) parentRow.classList.add("expanded");
        }} else {{
            tr.style.display = "none";
            if (caret) caret.classList.remove("open");
            if (parentRow) parentRow.classList.remove("expanded");
        }}
        setTimeout(resizeFrame, 20);
    }}

    window.addEventListener("load", () => setTimeout(resizeFrame, 60));
    window.addEventListener("resize", () => setTimeout(resizeFrame, 60));
    </script>
    </body>
    </html>
    """

    return component_html, altura_inicial, pd.DataFrame(export_rows), float(s_var.sum())

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

component_html, altura_matriz, df_export, variacao_liquida = construir_matriz_component(
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
            <div class="badge-lbl">Período</div>
            <div class="badge-val">{periodo_str}</div>
        </div>
        <div class="badge-box">
            <div class="badge-lbl">Variação líquida</div>
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

components.html(component_html, height=altura_matriz, scrolling=True)
