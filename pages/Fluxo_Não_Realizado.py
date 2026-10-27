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

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:Inter,Segoe UI,Arial,sans-serif}
.stApp,[data-testid="stAppViewContainer"]{background:#f8fafc;color:#0f172a}
[data-testid="stHeader"]{background:transparent}#MainMenu,footer{visibility:hidden}
.main .block-container{padding:1.1rem 1.4rem 1.4rem;max-width:99%}
[data-testid="stMetric"]{background:white;border:1px solid #e2e8f0;padding:14px;border-radius:12px}
</style>""", unsafe_allow_html=True)
st.markdown("# Fluxo de Caixa Não Realizado")
st.caption("Visão separada para validar títulos e recebimentos pendentes, sem alterar o dashboard de Fluxo de Caixa realizado.")
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
    st.markdown("### Filtros")
    start=st.selectbox("De",months,index=0,format_func=lambda x:pd.Timestamp(x).strftime("%b/%y").title())
    end=st.selectbox("Até",months,index=len(months)-1,format_func=lambda x:pd.Timestamp(x).strftime("%b/%y").title())
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
c1,c2,c3,c4=st.columns(4)
c1.metric("Entradas pendentes",f"R$ {entr:,.2f}".replace(",","X").replace(".",",").replace("X","."))
c2.metric("Saídas pendentes",f"R$ {saidas_total:,.2f}".replace(",","X").replace(".",",").replace("X","."))
c3.metric("Saldo projetado líquido",f"R$ {net:,.2f}".replace(",","X").replace(".",",").replace("X","."))
c4.metric("Lançamentos",f"{len(f):,}".replace(",","."))

if f.empty:
    st.info("Nenhum lançamento corresponde aos filtros selecionados.")
else:
    monthly=f.groupby(["Mês","Tipo"],as_index=False)["Valor"].sum()
    monthly["Mês"] = monthly["Mês"].apply(lambda x:pd.Timestamp(x).strftime("%b/%y").title())
    st.markdown("### Evolução mensal")
    fig=px.bar(monthly,x="Mês",y="Valor",color="Tipo",barmode="group",color_discrete_map={"Entrada pendente":VERDE,"Saída pendente":VERMELHO})
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend_title_text="",margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig,use_container_width=True)
    left,right=st.columns(2)
    with left:
        st.markdown("### Valores por classificação")
        grp=f.groupby(["Tipo","Classificação"],as_index=False)["Valor"].sum().sort_values("Valor",ascending=False)
        st.dataframe(grp,hide_index=True,use_container_width=True)
    with right:
        st.markdown("### Detalhamento mensal")
        piv=f.pivot_table(index="Classificação",columns="Mês",values="Valor",aggfunc="sum",fill_value=0)
        piv.columns=[pd.Timestamp(x).strftime("%b/%y").title() for x in piv.columns]
        st.dataframe(piv,use_container_width=True)
    st.markdown("### Lançamentos")
    show=f.copy(); show["Mês"]=show["Mês"].apply(lambda x:pd.Timestamp(x).strftime("%m/%Y"))
    show["Valor"] = show["Valor"].round(2)
    st.dataframe(show[["Mês","Tipo","Classificação","Fluxo","Origem/Detalhe","Valor"]],hide_index=True,use_container_width=True)
    st.download_button("Baixar dados filtrados (CSV)",show.to_csv(index=False).encode("utf-8-sig"),"fluxo_caixa_nao_realizado.csv","text/csv")
