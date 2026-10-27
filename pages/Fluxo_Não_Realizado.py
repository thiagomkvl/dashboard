import streamlit as st
st.set_page_config(page_title="Fluxo de Caixa Não Realizado", layout="wide", page_icon="💵", initial_sidebar_state="expanded")
import re, unicodedata, time
import pandas as pd
import plotly.express as px

try:
    from database import conectar_sheets
except Exception as e:
    _db_err = str(e)
    def conectar_sheets():
        st.error(f"Não foi possível importar database.py: {_db_err}")
        return None

ABA_TITULOS = "Base_Titulos_Vencidos"
ABA_CONTAS = "Base_Contas"
ABA_CLASSIF = "Classificacao_FCx"
FLUXO_OP = "Fluxo de Caixa Operacional"
FLUXO_INV = "Fluxo de Caixa de Investimentos"
FLUXO_FIN = "Fluxo de Caixa de Financiamento"
TAX_BENEF = {"ministerio da fazenda", "prefeitura municipal de florianopolis", "instituto nacional do seguro social"}
AZUL, VERDE, AMBAR, VERMELHO, ROXO = "#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"


def norm(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return ""
    return unicodedata.normalize("NFKD", str(v)).encode("ASCII", "ignore").decode().lower().strip()

def key(v): return re.sub(r"[^a-z0-9]+", " ", norm(v)).strip()
def money(v):
    if pd.isna(v): return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if not s or s.lower() in {"nan", "none", "-"}: return 0.0
    if "," in s: s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return 0.0

def parse_date(v):
    if pd.isna(v) or str(v).strip() in {"", "NaT", "nan", "None"}: return pd.NaT
    if isinstance(v, (int, float)) and 20000 < float(v) < 80000:
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(float(v), unit="D")
    parsed = pd.to_datetime(v, errors="coerce", dayfirst=True)
    if pd.notna(parsed): return parsed
    # Compatível com Mês Faturamento no formato jan/26 usado em Base_Contas.
    t = norm(v)
    months = {"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}
    m = re.match(r"^([a-z]{3,9})[\s\-/\.]*([0-9]{2}|[0-9]{4})$", t)
    if m and m.group(1)[:3] in months:
        year = int(m.group(2)); year += 2000 if year < 100 else 0
        return pd.Timestamp(year, months[m.group(1)[:3]], 1)
    return pd.NaT

def colmap(df): return {key(c): c for c in df.columns}
def get_col(df, *candidates):
    m = colmap(df)
    for c in candidates:
        if key(c) in m: return m[key(c)]
    return None

@st.cache_data(ttl=60, show_spinner=False)
def read_tab(name):
    last = None
    for wait in (0, 5, 10):
        if wait: time.sleep(wait)
        try:
            conn = conectar_sheets()
            if conn is None: raise RuntimeError("Conexão com Google Sheets indisponível.")
            df = conn.read(worksheet=name, ttl=0)
            return pd.DataFrame() if df is None else df
        except Exception as e:
            last = e
            if not any(x in str(e).lower() for x in ("429", "quota", "rate_limit", "resource_exhausted")): raise
    raise last

def read_classifications():
    df = read_tab(ABA_CLASSIF)
    if df.empty: return {}
    m = colmap(df)
    desc = next((m[x] for x in ("descricao", "conta contabil", "categoria") if x in m), df.columns[0])
    cls = next((c for c in df.columns if "classific" in key(c) and "fluxo" not in key(c)), df.columns[1] if len(df.columns)>1 else None)
    flx = next((c for c in df.columns if "fluxo" in key(c)), df.columns[2] if len(df.columns)>2 else None)
    out = {}
    if cls is None: return out
    for _, r in df.iterrows():
        d, c = key(r.get(desc, "")), str(r.get(cls, "") or "").strip()
        f = key(r.get(flx, "")) if flx else ""
        if not d or not c or c.lower() == "nan": continue
        flow = FLUXO_INV if "invest" in f else FLUXO_FIN if "financ" in f else FLUXO_OP
        out[d] = (c, flow)
    return out

def classify(value, mapping):
    k = key(value)
    if k in mapping: return mapping[k]
    matches = [(len(mk), val) for mk, val in mapping.items() if len(mk) >= 6 and (mk in k or k in mk)]
    return sorted(matches, key=lambda x: x[0], reverse=True)[0][1] if matches else ("Não classificado", FLUXO_OP)

def locate_header(raw, required):
    df = raw.copy()
    if all(get_col(df, c) for c in required): return df
    for i in range(min(20, len(df))):
        candidate = df.iloc[i:].copy()
        candidate.columns = list(raw.iloc[i])
        if all(get_col(candidate, c) for c in required): return candidate.iloc[1:].reset_index(drop=True)
    return df

def load_outflows(mapping):
    raw = read_tab(ABA_TITULOS)
    if raw.empty: return pd.DataFrame(), [f"A aba {ABA_TITULOS} está vazia."]
    df = locate_header(raw, ["Beneficiário", "Saldo Atual", "Venc Original"])
    benef, val, venc = get_col(df,"Beneficiário"), get_col(df,"Saldo Atual"), get_col(df,"Venc Original")
    cont = get_col(df,"Conta Contábil"); fin = get_col(df,"Conta Financeira")
    if not all([benef,val,venc,cont,fin]):
        missing = [x for x, c in [("Beneficiário",benef),("Saldo Atual",val),("Venc Original",venc),("Conta Contábil",cont),("Conta Financeira",fin)] if c is None]
        return pd.DataFrame(), ["Colunas não encontradas em Base_Titulos_Vencidos: " + ", ".join(missing)]
    out = pd.DataFrame()
    out["Beneficiário"] = df[benef].fillna("(Sem beneficiário)").astype(str).str.strip()
    out["Conta Contábil"] = df[cont].fillna("").astype(str).str.strip()
    out["Conta Financeira"] = df[fin].fillna("").astype(str).str.strip()
    out["Data"] = df[venc].apply(parse_date)
    out["Valor"] = df[val].apply(money)
    out["Descrição usada"] = out.apply(lambda r: r["Conta Financeira"] if key(r["Beneficiário"]) in TAX_BENEF else r["Conta Contábil"], axis=1)
    out[["Classificação", "Fluxo"]] = out["Descrição usada"].apply(lambda x: pd.Series(classify(x, mapping)))
    out["Tipo"] = "Saída pendente"
    out = out[out["Data"].notna() & (out["Valor"].abs() > 0.005)].copy()
    out["Mês"] = out["Data"].dt.to_period("M").dt.to_timestamp()
    return out, []

def load_receivables():
    raw = read_tab(ABA_CONTAS)
    if raw.empty: return pd.DataFrame(), [f"A aba {ABA_CONTAS} está vazia."]
    df = locate_header(raw, ["Mês Faturamento", "Convênio Conta", "Situação Conta", "Valor Conta", "Valor Recebido"])
    mes, conv, sit, val, rec = [get_col(df, x) for x in ["Mês Faturamento", "Convênio Conta", "Situação Conta", "Valor Conta", "Valor Recebido"]]
    if not all([mes,conv,sit,val,rec]): return pd.DataFrame(), ["Não encontrei todas as colunas necessárias em Base_Contas."]
    acat = get_col(df, "glosa acatada")
    conta = pd.DataFrame({"Mês texto":df[mes].astype(str), "Convênio":df[conv].fillna("(Sem convênio)"), "Situação":df[sit].fillna("(Sem situação)"), "Valor Conta":df[val].apply(money), "Valor Recebido":df[rec].apply(money), "Glosa Acatada":df[acat].apply(money) if acat else 0.0})
    conta["Mês"] = conta["Mês texto"].apply(parse_date)
    # Replica a base de contas do painel Análise_Faturamento: valor em aberto = faturado - recebido - glosa acatada.
    conta["Valor"] = conta["Valor Conta"] - conta["Valor Recebido"] - conta["Glosa Acatada"]
    conta["Situação normalizada"] = conta["Situação"].apply(key)
    conta = conta[conta["Situação normalizada"].str.contains("inadimpl", na=False) & conta["Mês"].notna() & (conta["Valor"] > 0.005)].copy()
    conta["Classificação"] = "Inadimplência"
    conta["Fluxo"] = "Recebimentos pendentes"
    conta["Tipo"] = "Entrada pendente"
    return conta[["Mês","Convênio","Situação","Valor","Classificação","Fluxo","Tipo"]], []

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #f8fafc !important; color: #0f172a; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1.4rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: 0.75rem; }
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

    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 0.75rem; }
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
""",
    unsafe_allow_html=True,
)

with st.spinner("Carregando bases e classificações..."):
    errors=[]
    try: mapping=read_classifications()
    except Exception as e: mapping={}; errors.append(f"Classificações: {e}")
    try: saidas, e = load_outflows(mapping); errors += e
    except Exception as e: saidas=pd.DataFrame(); errors.append(f"Saídas pendentes: {e}")
    try: entradas, e = load_receivables(); errors += e
    except Exception as e: entradas=pd.DataFrame(); errors.append(f"Entradas pendentes: {e}")
for e in errors: st.warning(e)
if saidas.empty and entradas.empty:
    st.info("Não há dados disponíveis para exibir. Confira a conexão e os nomes das colunas nas abas de origem.")
    st.stop()

frames=[]
if not saidas.empty:
    s=saidas[["Mês","Valor","Classificação","Fluxo","Tipo"]].copy(); s["Origem/Detalhe"]=saidas["Beneficiário"] + " — " + saidas["Descrição usada"].astype(str); frames.append(s)
if not entradas.empty:
    r=entradas[["Mês","Valor","Classificação","Fluxo","Tipo"]].copy(); r["Origem/Detalhe"]=entradas["Convênio"].astype(str) + " — " + entradas["Situação"].astype(str); frames.append(r)
base=pd.concat(frames,ignore_index=True)
months=sorted(base["Mês"].dropna().unique())
if not months: st.info("Não há datas válidas para agrupar os dados."); st.stop()
with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)
    c_a, c_b = st.columns(2)
    start=c_a.selectbox("De",months,index=0,format_func=lambda x:pd.Timestamp(x).strftime("%b/%y").title())
    end=c_b.selectbox("Até",months,index=len(months)-1,format_func=lambda x:pd.Timestamp(x).strftime("%b/%y").title())
    types=sorted(base["Tipo"].unique())
    type_sel=st.multiselect("Movimento",types,default=types)
    class_sel=st.multiselect("Classificação",sorted(base["Classificação"].unique()))
    if st.button("↻ Atualizar dados",use_container_width=True): st.cache_data.clear(); st.rerun()
if start>end: start,end=end,start
f=base[(base["Mês"]>=pd.Timestamp(start))&(base["Mês"]<=pd.Timestamp(end))]
if type_sel: f=f[f["Tipo"].isin(type_sel)]
if class_sel: f=f[f["Classificação"].isin(class_sel)]
entr=f.loc[f["Tipo"]=="Entrada pendente","Valor"].sum()
saidas_total=f.loc[f["Tipo"]=="Saída pendente","Valor"].sum()
net=entr-saidas_total
def moeda(v):
    return (f"R$ {v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")

periodo_txt = f"{pd.Timestamp(start).strftime('%b/%y').title()} – {pd.Timestamp(end).strftime('%b/%y').title()}"
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>FLUXO DE CAIXA NÃO REALIZADO</h1>
            <p>Visão gerencial · Entradas e saídas pendentes · Valores projetados</p>
        </div>
        <div class='pills'>
            <div class='pill'><small>Período</small><b>{periodo_txt}</b></div>
            <div class='pill'><small>Variação líquida</small>
                <b style="color:{'#059669' if net >= 0 else '#dc2626'}">{moeda(net)}</b></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f"""
<div class='kpi-grid'>
    <div class='kpi green'><div class='kpi-t'>Entradas pendentes</div><div class='kpi-v' style='color:#059669'>{moeda(entr)}</div><div class='kpi-sub'>Recebimentos em aberto</div></div>
    <div class='kpi red'><div class='kpi-t'>Saídas pendentes</div><div class='kpi-v' style='color:#dc2626'>{moeda(saidas_total)}</div><div class='kpi-sub'>Títulos a pagar</div></div>
    <div class='kpi {'green' if net >= 0 else 'red'}'><div class='kpi-t'>Saldo projetado líquido</div><div class='kpi-v' style='color:{'#059669' if net >= 0 else '#dc2626'}'>{moeda(net)}</div><div class='kpi-sub'>Entradas − saídas</div></div>
    <div class='kpi amber'><div class='kpi-t'>Recebíveis pendentes</div><div class='kpi-v'>{int((f['Tipo'] == 'Entrada pendente').sum()):,}</div><div class='kpi-sub'>Itens a receber</div></div>
    <div class='kpi blue'><div class='kpi-t'>Lançamentos</div><div class='kpi-v'>{len(f):,}</div><div class='kpi-sub'>Itens no período filtrado</div></div>
</div>
""", unsafe_allow_html=True)

from html import escape

def tabela_html(df, colunas=None, max_linhas=None, indice=False):
    dados = df.copy()
    if max_linhas is not None:
        dados = dados.head(max_linhas)
    if colunas is not None:
        dados = dados[colunas]
    headers = list(dados.columns)
    th = "".join(f"<th>{escape(str(c))}</th>" for c in headers)
    linhas = []
    for _, row in dados.iterrows():
        cells = []
        for val in row.tolist():
            if pd.isna(val): texto = ""
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                texto = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else: texto = str(val)
            cells.append(f"<td>{escape(texto)}</td>")
        linhas.append("<tr>" + "".join(cells) + "</tr>")
    if not linhas:
        linhas.append(f"<tr><td colspan='{max(1, len(headers))}'>Sem dados no período</td></tr>")
    return "<div class='tbl-wrap'><table class='tbl'><thead><tr>" + th + "</tr></thead><tbody>" + "".join(linhas) + "</tbody></table></div>"

if f.empty:
    st.markdown("<div class='vazio'>Nenhum lançamento corresponde aos filtros selecionados.</div>", unsafe_allow_html=True)
else:
    # Demonstrativo principal no mesmo padrão estrutural do Fluxo de Caixa realizado:
    # linhas por tipo/classificação, colunas mensais e total do período.
    st.markdown("<div class='section-title'>Demonstrativo · Entradas e saídas pendentes por mês</div>", unsafe_allow_html=True)
    mensal = f.pivot_table(index=["Tipo", "Classificação"], columns="Mês", values="Valor", aggfunc="sum", fill_value=0)
    all_months = sorted(f["Mês"].dropna().unique())
    mensal = mensal.reindex(columns=all_months, fill_value=0)
    mensal["Total do período"] = mensal.sum(axis=1)
    mensal = mensal.sort_index(level=[0, 1])
    mensal = mensal.reset_index()
    mensal.columns = [pd.Timestamp(c).strftime("%b/%y").title() if isinstance(c, (pd.Timestamp,)) else str(c) for c in mensal.columns]
    for c in mensal.columns[2:]:
        mensal[c] = mensal[c].apply(moeda)
    st.markdown(tabela_html(mensal), unsafe_allow_html=True)

import streamlit as st
st.set_page_config(page_title="Fluxo de Caixa Não Realizado", layout="wide", page_icon="💵", initial_sidebar_state="expanded")
import re, unicodedata, time
import pandas as pd
import plotly.express as px

try:
    from database import conectar_sheets
except Exception as e:
    _db_err = str(e)
    def conectar_sheets():
        st.error(f"Não foi possível importar database.py: {_db_err}")
        return None

ABA_TITULOS = "Base_Titulos_Vencidos"
ABA_CONTAS = "Base_Contas"
ABA_CLASSIF = "Classificacao_FCx"
FLUXO_OP = "Fluxo de Caixa Operacional"
FLUXO_INV = "Fluxo de Caixa de Investimentos"
FLUXO_FIN = "Fluxo de Caixa de Financiamento"
TAX_BENEF = {"ministerio da fazenda", "prefeitura municipal de florianopolis", "instituto nacional do seguro social"}
AZUL, VERDE, AMBAR, VERMELHO, ROXO = "#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"


def norm(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return ""
    return unicodedata.normalize("NFKD", str(v)).encode("ASCII", "ignore").decode().lower().strip()

def key(v): return re.sub(r"[^a-z0-9]+", " ", norm(v)).strip()
def money(v):
    if pd.isna(v): return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if not s or s.lower() in {"nan", "none", "-"}: return 0.0
    if "," in s: s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return 0.0

def parse_date(v):
    if pd.isna(v) or str(v).strip() in {"", "NaT", "nan", "None"}: return pd.NaT
    if isinstance(v, (int, float)) and 20000 < float(v) < 80000:
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(float(v), unit="D")
    parsed = pd.to_datetime(v, errors="coerce", dayfirst=True)
    if pd.notna(parsed): return parsed
    # Compatível com Mês Faturamento no formato jan/26 usado em Base_Contas.
    t = norm(v)
    months = {"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}
    m = re.match(r"^([a-z]{3,9})[\s\-/\.]*([0-9]{2}|[0-9]{4})$", t)
    if m and m.group(1)[:3] in months:
        year = int(m.group(2)); year += 2000 if year < 100 else 0
        return pd.Timestamp(year, months[m.group(1)[:3]], 1)
    return pd.NaT

def colmap(df): return {key(c): c for c in df.columns}
def get_col(df, *candidates):
    m = colmap(df)
    for c in candidates:
        if key(c) in m: return m[key(c)]
    return None

@st.cache_data(ttl=60, show_spinner=False)
def read_tab(name):
    last = None
    for wait in (0, 5, 10):
        if wait: time.sleep(wait)
        try:
            conn = conectar_sheets()
            if conn is None: raise RuntimeError("Conexão com Google Sheets indisponível.")
            df = conn.read(worksheet=name, ttl=0)
            return pd.DataFrame() if df is None else df
        except Exception as e:
            last = e
            if not any(x in str(e).lower() for x in ("429", "quota", "rate_limit", "resource_exhausted")): raise
    raise last

def read_classifications():
    df = read_tab(ABA_CLASSIF)
    if df.empty: return {}
    m = colmap(df)
    desc = next((m[x] for x in ("descricao", "conta contabil", "categoria") if x in m), df.columns[0])
    cls = next((c for c in df.columns if "classific" in key(c) and "fluxo" not in key(c)), df.columns[1] if len(df.columns)>1 else None)
    flx = next((c for c in df.columns if "fluxo" in key(c)), df.columns[2] if len(df.columns)>2 else None)
    out = {}
    if cls is None: return out
    for _, r in df.iterrows():
        d, c = key(r.get(desc, "")), str(r.get(cls, "") or "").strip()
        f = key(r.get(flx, "")) if flx else ""
        if not d or not c or c.lower() == "nan": continue
        flow = FLUXO_INV if "invest" in f else FLUXO_FIN if "financ" in f else FLUXO_OP
        out[d] = (c, flow)
    return out

def classify(value, mapping):
    k = key(value)
    if k in mapping: return mapping[k]
    matches = [(len(mk), val) for mk, val in mapping.items() if len(mk) >= 6 and (mk in k or k in mk)]
    return sorted(matches, key=lambda x: x[0], reverse=True)[0][1] if matches else ("Não classificado", FLUXO_OP)

def locate_header(raw, required):
    df = raw.copy()
    if all(get_col(df, c) for c in required): return df
    for i in range(min(20, len(df))):
        candidate = df.iloc[i:].copy()
        candidate.columns = list(raw.iloc[i])
        if all(get_col(candidate, c) for c in required): return candidate.iloc[1:].reset_index(drop=True)
    return df

def load_outflows(mapping):
    raw = read_tab(ABA_TITULOS)
    if raw.empty: return pd.DataFrame(), [f"A aba {ABA_TITULOS} está vazia."]
    df = locate_header(raw, ["Beneficiário", "Saldo Atual", "Venc Original"])
    benef, val, venc = get_col(df,"Beneficiário"), get_col(df,"Saldo Atual"), get_col(df,"Venc Original")
    cont = get_col(df,"Conta Contábil"); fin = get_col(df,"Conta Financeira")
    if not all([benef,val,venc,cont,fin]):
        missing = [x for x, c in [("Beneficiário",benef),("Saldo Atual",val),("Venc Original",venc),("Conta Contábil",cont),("Conta Financeira",fin)] if c is None]
        return pd.DataFrame(), ["Colunas não encontradas em Base_Titulos_Vencidos: " + ", ".join(missing)]
    out = pd.DataFrame()
    out["Beneficiário"] = df[benef].fillna("(Sem beneficiário)").astype(str).str.strip()
    out["Conta Contábil"] = df[cont].fillna("").astype(str).str.strip()
    out["Conta Financeira"] = df[fin].fillna("").astype(str).str.strip()
    out["Data"] = df[venc].apply(parse_date)
    out["Valor"] = df[val].apply(money)
    out["Descrição usada"] = out.apply(lambda r: r["Conta Financeira"] if key(r["Beneficiário"]) in TAX_BENEF else r["Conta Contábil"], axis=1)
    out[["Classificação", "Fluxo"]] = out["Descrição usada"].apply(lambda x: pd.Series(classify(x, mapping)))
    out["Tipo"] = "Saída pendente"
    out = out[out["Data"].notna() & (out["Valor"].abs() > 0.005)].copy()
    out["Mês"] = out["Data"].dt.to_period("M").dt.to_timestamp()
    return out, []

def load_receivables():
    raw = read_tab(ABA_CONTAS)
    if raw.empty: return pd.DataFrame(), [f"A aba {ABA_CONTAS} está vazia."]
    df = locate_header(raw, ["Mês Faturamento", "Convênio Conta", "Situação Conta", "Valor Conta", "Valor Recebido"])
    mes, conv, sit, val, rec = [get_col(df, x) for x in ["Mês Faturamento", "Convênio Conta", "Situação Conta", "Valor Conta", "Valor Recebido"]]
    if not all([mes,conv,sit,val,rec]): return pd.DataFrame(), ["Não encontrei todas as colunas necessárias em Base_Contas."]
    acat = get_col(df, "glosa acatada")
    conta = pd.DataFrame({"Mês texto":df[mes].astype(str), "Convênio":df[conv].fillna("(Sem convênio)"), "Situação":df[sit].fillna("(Sem situação)"), "Valor Conta":df[val].apply(money), "Valor Recebido":df[rec].apply(money), "Glosa Acatada":df[acat].apply(money) if acat else 0.0})
    conta["Mês"] = conta["Mês texto"].apply(parse_date)
    # Replica a base de contas do painel Análise_Faturamento: valor em aberto = faturado - recebido - glosa acatada.
    conta["Valor"] = conta["Valor Conta"] - conta["Valor Recebido"] - conta["Glosa Acatada"]
    conta["Situação normalizada"] = conta["Situação"].apply(key)
    conta = conta[conta["Situação normalizada"].str.contains("inadimpl", na=False) & conta["Mês"].notna() & (conta["Valor"] > 0.005)].copy()
    conta["Classificação"] = "Inadimplência"
    conta["Fluxo"] = "Recebimentos pendentes"
    conta["Tipo"] = "Entrada pendente"
    return conta[["Mês","Convênio","Situação","Valor","Classificação","Fluxo","Tipo"]], []

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #f8fafc !important; color: #0f172a; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1.4rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: 0.75rem; }
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

    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 0.75rem; }
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
""",
    unsafe_allow_html=True,
)

with st.spinner("Carregando bases e classificações..."):
    errors=[]
    try: mapping=read_classifications()
    except Exception as e: mapping={}; errors.append(f"Classificações: {e}")
    try: saidas, e = load_outflows(mapping); errors += e
    except Exception as e: saidas=pd.DataFrame(); errors.append(f"Saídas pendentes: {e}")
    try: entradas, e = load_receivables(); errors += e
    except Exception as e: entradas=pd.DataFrame(); errors.append(f"Entradas pendentes: {e}")
for e in errors: st.warning(e)
if saidas.empty and entradas.empty:
    st.info("Não há dados disponíveis para exibir. Confira a conexão e os nomes das colunas nas abas de origem.")
    st.stop()

frames=[]
if not saidas.empty:
    s=saidas[["Mês","Valor","Classificação","Fluxo","Tipo"]].copy(); s["Origem/Detalhe"]=saidas["Beneficiário"] + " — " + saidas["Descrição usada"].astype(str); frames.append(s)
if not entradas.empty:
    r=entradas[["Mês","Valor","Classificação","Fluxo","Tipo"]].copy(); r["Origem/Detalhe"]=entradas["Convênio"].astype(str) + " — " + entradas["Situação"].astype(str); frames.append(r)
base=pd.concat(frames,ignore_index=True)
months=sorted(base["Mês"].dropna().unique())
if not months: st.info("Não há datas válidas para agrupar os dados."); st.stop()
with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)
    c_a, c_b = st.columns(2)
    start=c_a.selectbox("De",months,index=0,format_func=lambda x:pd.Timestamp(x).strftime("%b/%y").title())
    end=c_b.selectbox("Até",months,index=len(months)-1,format_func=lambda x:pd.Timestamp(x).strftime("%b/%y").title())
    types=sorted(base["Tipo"].unique())
    type_sel=st.multiselect("Movimento",types,default=types)
    class_sel=st.multiselect("Classificação",sorted(base["Classificação"].unique()))
    if st.button("↻ Atualizar dados",use_container_width=True): st.cache_data.clear(); st.rerun()
if start>end: start,end=end,start
f=base[(base["Mês"]>=pd.Timestamp(start))&(base["Mês"]<=pd.Timestamp(end))]
if type_sel: f=f[f["Tipo"].isin(type_sel)]
if class_sel: f=f[f["Classificação"].isin(class_sel)]
entr=f.loc[f["Tipo"]=="Entrada pendente","Valor"].sum()
saidas_total=f.loc[f["Tipo"]=="Saída pendente","Valor"].sum()
net=entr-saidas_total
def moeda(v):
    return (f"R$ {v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")

periodo_txt = f"{pd.Timestamp(start).strftime('%b/%y').title()} – {pd.Timestamp(end).strftime('%b/%y').title()}"
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>FLUXO DE CAIXA NÃO REALIZADO</h1>
            <p>Visão gerencial · Entradas e saídas pendentes · Valores projetados</p>
        </div>
        <div class='pills'>
            <div class='pill'><small>Período</small><b>{periodo_txt}</b></div>
            <div class='pill'><small>Variação líquida</small>
                <b style="color:{'#059669' if net >= 0 else '#dc2626'}">{moeda(net)}</b></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f"""
<div class='kpi-grid'>
    <div class='kpi green'><div class='kpi-t'>Entradas pendentes</div><div class='kpi-v' style='color:#059669'>{moeda(entr)}</div><div class='kpi-sub'>Recebimentos em aberto</div></div>
    <div class='kpi red'><div class='kpi-t'>Saídas pendentes</div><div class='kpi-v' style='color:#dc2626'>{moeda(saidas_total)}</div><div class='kpi-sub'>Títulos a pagar</div></div>
    <div class='kpi {'green' if net >= 0 else 'red'}'><div class='kpi-t'>Saldo projetado líquido</div><div class='kpi-v' style='color:{'#059669' if net >= 0 else '#dc2626'}'>{moeda(net)}</div><div class='kpi-sub'>Entradas − saídas</div></div>
    <div class='kpi amber'><div class='kpi-t'>Recebíveis pendentes</div><div class='kpi-v'>{int((f['Tipo'] == 'Entrada pendente').sum()):,}</div><div class='kpi-sub'>Itens a receber</div></div>
    <div class='kpi blue'><div class='kpi-t'>Lançamentos</div><div class='kpi-v'>{len(f):,}</div><div class='kpi-sub'>Itens no período filtrado</div></div>
</div>
""", unsafe_allow_html=True)

from html import escape

def tabela_html(df, colunas=None, max_linhas=None, indice=False):
    dados = df.copy()
    if max_linhas is not None:
        dados = dados.head(max_linhas)
    if colunas is not None:
        dados = dados[colunas]
    headers = list(dados.columns)
    th = "".join(f"<th>{escape(str(c))}</th>" for c in headers)
    linhas = []
    for _, row in dados.iterrows():
        cells = []
        for val in row.tolist():
            if pd.isna(val): texto = ""
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                texto = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else: texto = str(val)
            cells.append(f"<td>{escape(texto)}</td>")
        linhas.append("<tr>" + "".join(cells) + "</tr>")
    if not linhas:
        linhas.append(f"<tr><td colspan='{max(1, len(headers))}'>Sem dados no período</td></tr>")
    return "<div class='tbl-wrap'><table class='tbl'><thead><tr>" + th + "</tr></thead><tbody>" + "".join(linhas) + "</tbody></table></div>"

if f.empty:
    st.markdown("<div class='vazio'>Nenhum lançamento corresponde aos filtros selecionados.</div>", unsafe_allow_html=True)
else:
    # Demonstrativo principal no mesmo padrão estrutural do Fluxo de Caixa realizado:
    # linhas por tipo/classificação, colunas mensais e total do período.
    st.markdown("<div class='section-title'>Demonstrativo · Entradas e saídas pendentes por mês</div>", unsafe_allow_html=True)
    mensal = f.pivot_table(index=["Tipo", "Classificação"], columns="Mês", values="Valor", aggfunc="sum", fill_value=0)
    all_months = sorted(f["Mês"].dropna().unique())
    mensal = mensal.reindex(columns=all_months, fill_value=0)
    mensal["Total do período"] = mensal.sum(axis=1)
    mensal = mensal.sort_index(level=[0, 1])
    mensal = mensal.reset_index()
    mensal.columns = [pd.Timestamp(c).strftime("%b/%y").title() if isinstance(c, (pd.Timestamp,)) else str(c) for c in mensal.columns]
    for c in mensal.columns[2:]:
        mensal[c] = mensal[c].apply(moeda)
    st.markdown(tabela_html(mensal), unsafe_allow_html=True)

