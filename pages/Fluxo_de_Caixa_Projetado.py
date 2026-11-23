import re
import time
import unicodedata
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
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
CORES = {
    "azul": "#2563eb", "verde": "#059669", "vermelho": "#dc2626",
    "ambar": "#d97706", "roxo": "#7c3aed", "texto": "#0f172a",
    "muted": "#64748b", "borda": "#e2e8f0", "fundo": "#f8fafc",
}

# ================================ CSS =========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: Inter, Segoe UI, Arial, sans-serif; }
.stApp { background:#f8fafc; color:#0f172a; }
[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer { visibility:hidden; }
.block-container { max-width:99%; padding:1.2rem 1.4rem 2rem; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid #e2e8f0; }
[data-testid="stWidgetLabel"] p { color:#64748b !important; font-size:12px; font-weight:650; }
.hero { display:flex; justify-content:space-between; align-items:center; gap:15px;
        padding:3px 0 15px; border-bottom:1px solid #e2e8f0; margin-bottom:14px; }
.hero h1 { margin:0; font-size:24px; font-weight:850; color:#0f172a; }
.hero p { margin:4px 0 0; color:#64748b; font-size:13px; }
.tag { border:1px solid #dbeafe; background:#eff6ff; color:#1d4ed8;
       border-radius:9px; padding:8px 12px; font-size:11px; font-weight:800; white-space:nowrap; }
.kpis { display:grid; grid-template-columns:repeat(5,minmax(140px,1fr)); gap:10px; margin:12px 0 16px; }
.kpi { background:#fff; border:1px solid #e2e8f0; border-left:4px solid #2563eb;
        border-radius:12px; padding:13px 15px; box-shadow:0 1px 3px #0f172a08; min-height:98px; }
.kpi.green { border-left-color:#059669; } .kpi.red { border-left-color:#dc2626; }
.kpi.amber { border-left-color:#d97706; } .kpi.purple { border-left-color:#7c3aed; }
.kpi-label { color:#64748b; font-size:10px; font-weight:800; letter-spacing:.45px; text-transform:uppercase; }
.kpi-value { margin:8px 0 3px; font-size:clamp(17px,1.5vw,23px); font-weight:850; color:#0f172a; white-space:nowrap; }
.kpi-sub { color:#64748b; font-size:11px; }
.sec { margin:16px 0 9px; padding-left:10px; border-left:3px solid #2563eb;
       font-size:12px; font-weight:850; letter-spacing:.5px; text-transform:uppercase; }
div[data-testid="stDataFrame"] { border:1px solid #e2e8f0; border-radius:10px; }
@media(max-width:900px){ .kpis{grid-template-columns:repeat(2,minmax(130px,1fr));}
 .hero{align-items:flex-start;flex-direction:column;} }
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
    return ("R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

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

def criar_mov(data, valor, fonte, categoria, fluxo="", grupo="", detalhe=""):
    data = dt(data)
    valor = money(valor)
    if pd.isna(data) or abs(valor) < 0.005:
        return None
    return {
        "Data": data, "Valor": valor, "Fonte": fonte, "Categoria": str(categoria or fonte),
        "Fluxo": str(fluxo or ""), "Grupo": str(grupo or fonte), "Detalhe": str(detalhe or categoria or fonte)
    }

# =========================== CLASSIFICAÇÃO ====================================
def mapa_classificacao(df):
    out = {}
    if df is None or df.empty:
        return out
    c_desc = col(df, ["Descrição", "Conta contábil", "Categoria"], df.columns[0])
    c_cls = col(df, ["Classificação FCx", "Classificação"], df.columns[1] if len(df.columns)>1 else None)
    c_flux = col(df, ["Fluxo de Caixa", "Fluxo"], df.columns[2] if len(df.columns)>2 else None)
    for _, row in df.iterrows():
        desc = norm(row.get(c_desc))
        if not desc:
            continue
        cls = str(row.get(c_cls, "") or "")
        flx = str(row.get(c_flux, "") or "")
        out[desc] = (cls, flx)
    return out

def is_fci(text, mapping):
    n = norm(text)
    if any("invest" in norm(v[1]) for k,v in mapping.items() if k and (k in n or n in k)):
        return True
    return any(k in n for k in ("obra", "capex", "investimento", "aplicacao financeira", "imobilizado"))

def classificar(text, mapping):
    n = norm(text)
    exact = mapping.get(n)
    if exact:
        return exact
    matches = [(len(k), v) for k,v in mapping.items() if len(k)>=5 and (k in n or n in k)]
    if matches:
        matches.sort(key=lambda x:x[0], reverse=True)
        return matches[0][1]
    return ("Não classificado", "Fluxo de Caixa Operacional")

# ============================= PROJEÇÃO ======================================
def montar_projecao(dados, inicio, dias, media_dias, mapping):
    fim = inicio + pd.Timedelta(days=dias-1)
    movs = []

    # 1181 — Receitas previstas por data de vencimento
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
                # A aba de protocolo contém situações; somente títulos com valor e vencimento são considerados.
                status = work[c_status].map(norm)
                work = work[~status.isin(["cancelado", "cancelada", "excluido", "excluida"])]
            for _, r in work.iterrows():
                m = criar_mov(r["_data"], r["_valor"], "1181 — Receita", r.get(c_cat, "Receita"), "Receita", "Receitas 1181", r.get(c_cat, ""))
                if m: movs.append(m)

    # PMTs — prestação total (PMT), com vencimento
    df = dados.get("PMTs", pd.DataFrame())
    if not df.empty:
        c_data, c_val = col(df, ["Vcto", "Vencimento"]), col(df, ["PMT", "Parcela"])
        c_bank = col(df, ["Banco"])
        if c_data and c_val:
            for _, r in df.iterrows():
                m = criar_mov(r[c_data], -abs(money(r[c_val])), "PMTs", "Parcela empréstimo", "Fluxo de Caixa de Financiamento", "PMTs", r.get(c_bank, ""))
                if m: movs.append(m)

    # 1147 — contas a pagar em aberto, usando saldo atual
    df = dados.get("1147", pd.DataFrame())
    if not df.empty:
        c_data = col(df, ["Vencimento Atual", "Vencimento Original", "Vencimento"])
        c_val = col(df, ["Vl Saldo", "Valor Saldo", "Saldo"])
        c_status = col(df, ["Situação", "Status"])
        c_cat = col(df, ["Razão Social", "Conta contábil", "Título"])
        c_conta = col(df, ["Conta contábil"])
        c_fluxo = col(df, ["Conta Financeira"])
        if c_data and c_val:
            work = df.copy()
            work["_data"] = work[c_data].map(dt)
            work["_valor"] = work[c_val].map(money)
            if c_status:
                work = work[~work[c_status].map(norm).isin(["liquidado", "pago", "baixado", "cancelado", "cancelada"])]
            work = work[work["_valor"] > 0.005]
            for _, r in work.iterrows():
                categoria = r.get(c_conta, r.get(c_cat, "Conta a pagar"))
                cls, flx = classificar(categoria, mapping)
                m = criar_mov(r["_data"], -abs(r["_valor"]), "1147 — Contas a pagar", categoria, flx, "1147", r.get(c_cat, ""))
                if m: movs.append(m)

    # Impostos
    df = dados.get("Impostos", pd.DataFrame())
    if not df.empty:
        c_data, c_val = col(df, ["Data", "Vencimento"]), col(df, ["Valor", "Valor imposto"])
        c_cat = col(df, ["Beneficiario", "Beneficiário", "Tipo"])
        c_tipo = col(df, ["Tipo"])
        if c_data and c_val:
            for _, r in df.iterrows():
                m = criar_mov(r[c_data], -abs(money(r[c_val])), "Impostos", r.get(c_cat, "Impostos"), "Fluxo de Caixa Operacional", "Impostos", r.get(c_tipo, ""))
                if m: movs.append(m)

    # Á Vista — média de saídas históricas por dia corrido, sem FCI
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
                # Usa histórico liquidado/realizado para formar média, sem títulos cancelados.
                work = work[~work[c_status].map(norm).isin(["cancelado", "cancelada", "estornado"])]
            if c_cat:
                work = work[~work[c_cat].map(lambda x:is_fci(x, mapping))]
            work = work[(work["_data"] < inicio) & (work["_data"] >= inicio-pd.Timedelta(days=media_dias)) & (work["_valor"]>0)]
            # Média diária sobre o período completo, incluindo dias sem saída.
            media_aplicada = float(work["_valor"].sum()) / max(1, media_dias)
            if media_aplicada > 0:
                for d in pd.date_range(inicio, fim, freq="D"):
                    m = criar_mov(d, -media_aplicada, "Á Vista — média diária", "Despesas à vista (média)", "Fluxo de Caixa Operacional", "Á Vista", f"Média dos últimos {media_dias} dias")
                    if m: movs.append(m)

    # Orçamento_Obra — valores mensais; distribui igualmente pelos dias do mês.
    df = dados.get("Orçamento_Obra", pd.DataFrame())
    if not df.empty:
        # Normaliza cabeçalho para identificar colunas mensais; TOTAL e linhas de total não entram.
        cols_mes = []
        for c in df.columns:
            d = dt(c)
            if not pd.isna(d) and (d.day == 1):
                cols_mes.append((c, d))
            else:
                # Cabeçalhos podem vir como "2026-01" ou "Jan/26".
                m = re.match(r"^(20\d{2})[-/](\d{1,2})$", str(c).strip())
                if m:
                    cols_mes.append((c, pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)))
        c_nome = col(df, ["RESUMO OBRAS", "Obra", "Descrição"], df.columns[0])
        c_total = col(df, ["TOTAL"])
        c_custo = col(df, ["Custo R$"])
        for _, row in df.iterrows():
            nome = str(row.get(c_nome, "") or "").strip()
            if not nome or norm(nome) in ("total", "total geral") or norm(nome).startswith("total "):
                continue
            # Evita linhas-resumo agregadas: usa somente linhas com valor mensal não-zero.
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
                    m = criar_mov(d, -diario, "Orçamento_Obra", f"Obra: {nome}", "Fluxo de Caixa de Investimentos", f"Obra — {nome}", f"Rateio diário de {brl(valor_mes)}")
                    if m: movs.append(m)

    base = pd.DataFrame(movs, columns=["Data","Valor","Fonte","Categoria","Fluxo","Grupo","Detalhe"])
    if base.empty:
        base = pd.DataFrame(columns=["Data","Valor","Fonte","Categoria","Fluxo","Grupo","Detalhe"])
    base = base[(base["Data"] >= inicio) & (base["Data"] <= fim)].copy()
    base["Tipo"] = base["Valor"].apply(lambda x:"Entrada" if x>0 else "Saída")
    base["Dia"] = base["Data"].dt.date
    diario = base.groupby("Data", as_index=False).agg(
        Entradas=("Valor", lambda s: s[s>0].sum()),
        Saídas=("Valor", lambda s: -s[s<0].sum()),
        Líquido=("Valor", "sum"),
    )
    calendario = pd.DataFrame({"Data":pd.date_range(inicio,fim,freq="D")})
    diario = calendario.merge(diario,on="Data",how="left").fillna(0)
    diario["Saldo projetado"] = float(saldo_inicial) if False else 0.0
    return base, diario, media_aplicada

# ============================== INTERFACE =====================================
st.markdown('<div class="hero"><div><h1>Fluxo de Caixa Projetado</h1><p>Visão diária de entradas, saídas e saldo futuro · integrado ao realizado</p></div><div class="tag">PROJEÇÃO • 30 DIAS</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Parâmetros da projeção")
    hoje = pd.Timestamp.today().normalize()
    inicio = st.date_input("Data inicial", value=hoje.date(), format="DD/MM/YYYY")
    dias = st.select_slider("Horizonte", options=[7, 15, 30, 45, 60, 90], value=30)
    media_dias = st.select_slider("Janela média Á Vista", options=[30, 60, 90], value=30)
    st.caption("A média de Á Vista considera dias corridos e exclui despesas identificadas como FCI.")
    st.divider()
    if st.button("Atualizar dados do Sheets", use_container_width=True):
        carregar_fontes.clear()
        st.rerun()

try:
    fontes, erros = carregar_fontes()
except Exception as exc:
    st.error(f"Falha ao conectar ao Google Sheets: {exc}")
    st.stop()

mapping = mapa_classificacao(fontes.get("Classificacao_FCx", pd.DataFrame()))
saldo = SALDO_INICIAL_MANUAL
saldo_origem = "configuração manual"
saldo_detectado = False

# Tentativa conservadora de localizar saldo corrente na aba Resumo_FCx.
resumo = fontes.get("Resumo_FCx", pd.DataFrame())
if saldo is None and not resumo.empty:
    # Detecta tabela transacional de realizado e calcula o último saldo quando houver coluna explícita.
    c_saldo = col(resumo, ["Saldo atual", "Saldo final", "Saldo caixa", "Saldo"])
    c_data = col(resumo, ["Data", "Mês", "Data movimento", "Competência"])
    if c_saldo:
        vals = resumo[c_saldo].map(money)
        if c_data:
            dates = resumo[c_data].map(dt)
            valid = dates.notna() & vals.notna()
            if valid.any():
                saldo = float(vals[valid].iloc[-1])
                saldo_origem = "Resumo_FCx — última linha com saldo"
                saldo_detectado = True
        elif vals.notna().any():
            # Só aceita um valor escalar de saldo explícito; não soma coluna ambígua.
            saldo = float(vals.dropna().iloc[-1])
            saldo_origem = "Resumo_FCx — coluna de saldo"
            saldo_detectado = True

if saldo is None:
    saldo = 0.0
    saldo_origem = "não identificado (saldo manual necessário)"

base_mov, diario, media_avista = montar_projecao(fontes, pd.Timestamp(inicio), int(dias), int(media_dias), mapping)
diario["Saldo projetado"] = float(saldo) + diario["Líquido"].cumsum()
diario["Saldo inicial do dia"] = diario["Saldo projetado"].shift(1, fill_value=float(saldo))

entradas = float(diario["Entradas"].sum())
saidas = float(diario["Saídas"].sum())
liquido = entradas - saidas
saldo_final = float(diario["Saldo projetado"].iloc[-1]) if len(diario) else float(saldo)
saldo_min = float(diario["Saldo projetado"].min()) if len(diario) else float(saldo)

if not saldo_detectado and SALDO_INICIAL_MANUAL is None:
    st.warning("Saldo inicial não identificado automaticamente em Resumo_FCx. Configure SALDO_INICIAL_MANUAL no início do arquivo para que o saldo acumulado reflita o caixa real. A projeção de entradas e saídas continua disponível.")

st.markdown(f"""
<div class="kpis">
 <div class="kpi"><div class="kpi-label">Saldo inicial</div><div class="kpi-value">{brl(saldo)}</div><div class="kpi-sub">{saldo_origem}</div></div>
 <div class="kpi green"><div class="kpi-label">Entradas previstas</div><div class="kpi-value">{brl(entradas)}</div><div class="kpi-sub">No horizonte selecionado</div></div>
 <div class="kpi red"><div class="kpi-label">Saídas previstas</div><div class="kpi-value">{brl(saidas)}</div><div class="kpi-sub">Inclui médias e rateios</div></div>
 <div class="kpi {'green' if liquido>=0 else 'red'}"><div class="kpi-label">Fluxo líquido</div><div class="kpi-value">{brl(liquido)}</div><div class="kpi-sub">Entradas menos saídas</div></div>
 <div class="kpi {'red' if saldo_min<0 else 'purple'}"><div class="kpi-label">Saldo final projetado</div><div class="kpi-value">{brl(saldo_final)}</div><div class="kpi-sub">Mínimo no período: {brl(saldo_min)}</div></div>
</div>
""", unsafe_allow_html=True)

# Curva diária de saldo e barras de fluxo
st.markdown('<div class="sec">Evolução diária do caixa</div>', unsafe_allow_html=True)
fig = go.Figure()
fig.add_trace(go.Scatter(x=diario["Data"], y=diario["Saldo projetado"], name="Saldo projetado",
                         mode="lines+markers", line=dict(color=CORES["azul"], width=3),
                         fill="tozeroy", fillcolor="rgba(37,99,235,0.08)"))
fig.add_hline(y=0, line_dash="dash", line_color=CORES["vermelho"], opacity=.65)
fig.update_layout(height=360, margin=dict(l=10,r=10,t=15,b=10), paper_bgcolor="white",
                 plot_bgcolor="white", font=dict(family="Inter, Arial",color="#334155"),
                 legend=dict(orientation="h",y=1.02,x=0), xaxis=dict(showgrid=False),
                 yaxis=dict(gridcolor="#e2e8f0",tickprefix="R$ ",tickformat=",.0f"),
                 hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

fig2 = go.Figure()
fig2.add_bar(x=diario["Data"], y=diario["Entradas"], name="Entradas", marker_color=CORES["verde"])
fig2.add_bar(x=diario["Data"], y=-diario["Saídas"], name="Saídas", marker_color=CORES["vermelho"])
fig2.update_layout(height=300,barmode="relative",margin=dict(l=10,r=10,t=15,b=10),
                   paper_bgcolor="white",plot_bgcolor="white",
                   font=dict(family="Inter, Arial",color="#334155"),
                   legend=dict(orientation="h",y=1.02,x=0),xaxis=dict(showgrid=False),
                   yaxis=dict(gridcolor="#e2e8f0",tickprefix="R$ ",tickformat=",.0f"))
st.plotly_chart(fig2,use_container_width=True)

# Calendário diário e detalhe por origem
st.markdown('<div class="sec">Projeção por dia</div>', unsafe_allow_html=True)
view = diario.copy()
view["Data"] = view["Data"].dt.strftime("%d/%m/%Y")
for c in ["Entradas","Saídas","Líquido","Saldo inicial do dia","Saldo projetado"]:
    view[c] = view[c].map(brl)
st.dataframe(view, hide_index=True, use_container_width=True, height=390)

st.markdown('<div class="sec">Detalhamento dos movimentos projetados</div>', unsafe_allow_html=True)
if base_mov.empty:
    st.info("Nenhum movimento previsto foi encontrado no período selecionado.")
else:
    opcoes = ["Todas"] + sorted(base_mov["Fonte"].dropna().astype(str).unique().tolist())
    fonte_sel = st.selectbox("Filtrar fonte", opcoes)
    detalhado = base_mov.copy()
    if fonte_sel != "Todas":
        detalhado = detalhado[detalhado["Fonte"] == fonte_sel]
    detalhado = detalhado.sort_values(["Data","Fonte","Categoria"])
    detalhado["Data"] = detalhado["Data"].dt.strftime("%d/%m/%Y")
    detalhado["Valor"] = detalhado["Valor"].map(brl)
    st.dataframe(detalhado[["Data","Fonte","Categoria","Fluxo","Grupo","Detalhe","Valor"]],
                 hide_index=True,use_container_width=True,height=420)

# Diagnóstico de fontes: explicita aba que falhou ou está sem dados
with st.expander("Status das abas do Google Sheets"):
    for aba in ABAS:
        df = fontes.get(aba, pd.DataFrame())
        if aba in erros:
            st.error(f"{aba}: {erros[aba]}")
        else:
            st.write(f"**{aba}** — {len(df):,} linhas carregadas" if not df.empty else f"**{aba}** — aba carregada, mas sem registros.")

st.caption("Projeção gerencial. Datas e valores são tratados conforme as abas de origem; revise duplicidades e regras de rateio antes de utilizar como previsão oficial.")
