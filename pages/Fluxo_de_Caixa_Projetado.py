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
    "Classificacao_FCx", "Orçamento_Obra", "Resumo_FCx",
]
CACHE_SEGUNDOS = 90
SALDO_INICIAL_MANUAL = None  # Informe o saldo atual aqui se não for reconhecido em Resumo_FCx.

MESES_PT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
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

/* Hero / Header idêntico ao Realizado */
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

/* Barra de título da matriz */
.matrix-bar {
    background:#e2e8f0;
    color:#334155;
    font-size:11px;
    font-weight:800;
    letter-spacing:0.4px;
    padding:8px 14px;
    border-radius:8px 8px 0 0;
    border:1px solid #cbd5e1;
    border-bottom:none;
    margin-top:10px;
    text-transform:uppercase;
}

/* Tabela Matricial estilo Realizado */
.fcx-wrap {
    width:100%;
    overflow-x:auto;
    background:#fff;
    border:1px solid #cbd5e1;
    border-radius:0 0 8px 8px;
    box-shadow:0 1px 3px rgba(15,23,42,0.04);
}
table.fcx-table {
    width:100%;
    border-collapse:collapse;
    font-size:12px;
    white-space:nowrap;
}
table.fcx-table th {
    background:#f1f5f9;
    color:#475569;
    font-size:10.5px;
    font-weight:800;
    text-transform:uppercase;
    padding:9px 12px;
    border-bottom:1px solid #cbd5e1;
    text-align:right;
}
table.fcx-table th:first-child {
    text-align:left;
    position:sticky;
    left:0;
    z-index:2;
    background:#f1f5f9;
    min-width:290px;
    border-right:1px solid #e2e8f0;
}
table.fcx-table td {
    padding:8px 12px;
    border-bottom:1px solid #f1f5f9;
    text-align:right;
    font-variant-numeric:tabular-nums;
}
table.fcx-table td:first-child {
    text-align:left;
    position:sticky;
    left:0;
    z-index:1;
    border-right:1px solid #e2e8f0;
}

/* Hierarquia de Linhas */
tr.row-section td {
    background:#cbd5e1 !important;
    color:#0f172a;
    font-weight:800;
    font-size:11.5px;
    border-top:1px solid #94a3b8;
    border-bottom:1px solid #94a3b8;
}
tr.row-subtotal td {
    background:#e2e8f0 !important;
    color:#1e293b;
    font-weight:750;
    border-top:1px solid #cbd5e1;
    border-bottom:1px solid #cbd5e1;
}
tr.row-highlight td {
    background:#f1f5f9 !important;
    color:#0f172a;
    font-weight:800;
    border-top:1px solid #cbd5e1;
    border-bottom:1px solid #cbd5e1;
}
tr.row-item td {
    background:#ffffff;
    color:#334155;
    font-weight:500;
}
tr.row-item:hover td {
    background:#f8fafc;
}
tr.row-item td:first-child {
    padding-left:22px;
}

/* Cores de Valores */
.v-pos { color:#059669; font-weight:700; }
.v-neg { color:#dc2626; font-weight:700; }
.v-neu { color:#0f172a; font-weight:700; }
.v-zero { color:#94a3b8; font-weight:400; }

/* Indicadores visuais (bolinhas e setas) */
.dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:7px; vertical-align:middle; }
.dot-blue { background:#2563eb; }
.dot-green { background:#10b981; }
.dot-red { background:#ef4444; }
.dot-amber { background:#f59e0b; }
.dot-purple { background:#8b5cf6; }
.caret { color:#2563eb; font-size:9px; margin-right:6px; }

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
        if c_data and c_val:
            work = df.copy()
            work["_data"] = work[c_data].map(dt)
            work["_valor"] = work[c_val].map(money)
            if c_status:
                status = work[c_status].map(norm)
                work = work[~status.isin(["cancelado", "cancelada", "excluido", "excluida"])]
            for _, r in work.iterrows():
                raw_cat = str(r.get(c_cat, "Convênio") or "Convênio").strip()
                cls_map, _ = classificar(raw_cat, mapping)
                classif = cls_map if cls_map != "Não classificado" else raw_cat
                m = criar_mov(
                    r["_data"], abs(r["_valor"]), "1181 — Receita", raw_cat,
                    classif, "FCO", "(+) Receitas operacionais", raw_cat
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
        if c_data and c_val:
            for _, r in df.iterrows():
                desc_pmt = str(r.get(c_tipo, "") or "").strip()
                classif = desc_pmt if desc_pmt else "Amortização e Juros de Empréstimos"
                m = criar_mov(
                    r[c_data], -abs(money(r[c_val])), "PMTs", "Parcela empréstimo",
                    classif, "FCF", "(-) Amortização e juros de empréstimos", r.get(c_bank, "")
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
                    conta_txt or forn_txt or "Conta a pagar", cls, flx, sub, forn_txt
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
                cls_map, _ = classificar(tipo_imp, mapping)
                classif = cls_map if cls_map != "Não classificado" else tipo_imp
                m = criar_mov(
                    r[c_data], -abs(money(r[c_val])), "Impostos", tipo_imp,
                    classif, "FCO", "(-) Impostos", r.get(c_ben, "")
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
                        "(-) Custos e despesas operacionais", f"Média dos últimos {media_dias} dias"
                    )
                    if m:
                        movs.append(m)

    # 6. Orçamento_Obra -> FCI / (-) Desembolsos em CAPEX
    df = dados.get("Orçamento_Obra", pd.DataFrame())
    if not df.empty:
        cols_mes = []
        for c in df.columns:
            d = dt(c)
            if not pd.isna(d) and (d.day == 1):
                cols_mes.append((c, d))
            else:
                m = re.match(r"^(20\d{2})[-/](\d{1,2})$", str(c).strip())
                if m:
                    cols_mes.append((c, pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)))
        c_nome = col(df, ["RESUMO OBRAS", "Obra", "Descrição"], df.columns[0])
        for _, row in df.iterrows():
            nome = str(row.get(c_nome, "") or "").strip()
            if not nome or norm(nome) in ("total", "total geral") or norm(nome).startswith("total "):
                continue
            for c_mes, ref in cols_mes:
                valor_mes = money(row.get(c_mes, 0))
                if valor_mes <= 0:
                    continue
                primeiro = max(ref, inicio.replace(day=1))
                ultimo = min(ref + pd.offsets.MonthEnd(0), fim)
                if ultimo < inicio or primeiro > fim:
                    continue
                dias_mes = (ref + pd.offsets.MonthEnd(0)).day
                diario = valor_mes / dias_mes
                for d in pd.date_range(max(inicio, ref), min(fim, ref + pd.offsets.MonthEnd(0)), freq="D"):
                    m = criar_mov(
                        d, -diario, "Orçamento_Obra", f"Obra: {nome}",
                        f"Obra: {nome}", "FCI", "(-) Desembolsos em CAPEX",
                        f"Rateio diário de {brl_kpi(valor_mes)}"
                    )
                    if m:
                        movs.append(m)

    cols_base = ["Data", "Valor", "Fonte", "Categoria", "Classificacao", "Fluxo", "Subgrupo", "Detalhe"]
    base = pd.DataFrame(movs, columns=cols_base) if movs else pd.DataFrame(columns=cols_base)
    base = base[(base["Data"] >= inicio) & (base["Data"] <= fim)].copy()
    return base

# ===================== CONSTRUÇÃO DA MATRIZ GERENCIAL =========================
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
            out.append({
                "label": cls,
                "tipo": "item",
                "dot": dot_color,
                "vals": grp.loc[cls],
            })
        return out

    linhas = []
    export_rows = []

    # ---------------- 1. FCO ----------------
    df_fco = df[df["Fluxo"] == "FCO"] if not df.empty else pd.DataFrame()
    s_fco = get_serie(df_fco)
    linhas.append({"label": "1. FLUXO DE CAIXA OPERACIONAL (FCO)", "tipo": "section", "vals": s_fco})

    # (+) Receitas operacionais (com opção de consolidação)
    df_rec = df_fco[df_fco["Subgrupo"] == "(+) Receitas operacionais"] if not df_fco.empty else pd.DataFrame()
    s_rec = get_serie(df_rec)
    linhas.append({"label": "(+) Receitas operacionais", "tipo": "subtotal", "vals": s_rec})
    if consolidar_receitas:
        linhas.append({
            "label": "Convênios (Consolidado)",
            "tipo": "item",
            "dot": "dot-green",
            "vals": s_rec,
            "icon": "▸",
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

    # ---------------- NÃO CLASSIFICADO (se houver) ----------------
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

    # Monta HTML da tabela principal e DataFrame para exportação Excel
    header_cells = "".join([f"<th>{lbl}</th>" for lbl in col_labels]) + "<th>TOTAL PERÍODO</th>"
    body_html = []

    for row in linhas:
        tipo = row["tipo"]
        tr_cls = f"row-{tipo}"
        vals = row["vals"]
        blank_vals = row.get("blank_vals", False)

        if row["label"] == "(+) Saldo inicial":
            total_val = float(s_ini.iloc[0]) if len(s_ini) else float(saldo_inicial)
        elif row["label"] == "(=) Saldo final projetado":
            total_val = float(s_fim.iloc[-1]) if len(s_fim) else float(saldo_inicial)
        else:
            total_val = float(vals.sum())

        if tipo == "item" and row.get("dot"):
            icone = row.get("icon", "▶")
            lbl_html = f'<span class="caret">{icone}</span><span class="dot {row["dot"]}"></span>{row["label"]}'
        else:
            lbl_html = row["label"]

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
        body_html.append(f'<tr class="{tr_cls}">{"".join(tds)}</tr>')

    html_matriz = f"""
    <div class="matrix-bar">DEMONSTRATIVO PROJETADO • FCO / FCI / FCF / SALDO DE CAIXA • POR CLASSIFICAÇÃO FINANCEIRA</div>
    <div class="fcx-wrap">
        <table class="fcx-table">
            <thead><tr><th>DESCRIÇÃO</th>{header_cells}</tr></thead>
            <tbody>{"".join(body_html)}</tbody>
        </table>
    </div>
    """

    return html_matriz, pd.DataFrame(export_rows), float(s_var.sum())

def gerar_excel_bytes(df_matriz):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_matriz.to_excel(writer, sheet_name="Demonstrativo_Projetado", index=False)
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
saldo_detectado = False

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
                saldo_detectado = True
        elif vals.notna().any():
            saldo = float(vals.dropna().iloc[-1])
            saldo_detectado = True

if saldo is None:
    saldo = 0.0

inicio_ts = pd.Timestamp(inicio)
fim_ts = inicio_ts + pd.Timedelta(days=int(dias) - 1)
base_mov = montar_projecao(fontes, inicio_ts, int(dias), int(media_dias), mapping)

html_matriz, df_export, variacao_liquida = construir_matriz_html(
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

if not saldo_detectado and SALDO_INICIAL_MANUAL is None:
    st.warning("Saldo inicial não identificado automaticamente em Resumo_FCx. Configure `SALDO_INICIAL_MANUAL` no código para que o saldo acumulado parta do caixa real.")

st.download_button(
    label="⬇ Baixar Excel",
    data=gerar_excel_bytes(df_export),
    file_name=f"Fluxo_Caixa_Projetado_{inicio_ts.strftime('%Y%m%d')}_{dias}d.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.markdown(html_matriz, unsafe_allow_html=True)
