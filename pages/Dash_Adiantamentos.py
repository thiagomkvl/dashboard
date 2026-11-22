import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import textwrap
import html

try:
    st.set_page_config(
        page_title="Adiantamentos Pagos 2026 · Visão Executiva",
        layout="wide",
        page_icon="📊",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

import streamlit.components.v1 as components

try:
    from database import conectar_sheets
except Exception as _err:
    _erro_import_db = str(_err)
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {_erro_import_db}")
        return None

# ==============================================================================
# PALETA — tema claro / clean (igual ao Dash de Saldo)
# ==============================================================================
AZUL, VERDE, AMBAR, VERMELHO = "#2563eb", "#059669", "#d97706", "#dc2626"
ROXO, CIANO = "#7c3aed", "#0891b2"
TXT, MUTED, BORDA = "#0f172a", "#64748b", "#e2e8f0"
BG, SURFACE = "#f8fafc", "#ffffff"

css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #f8fafc !important; color: #0f172a; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1.4rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: 1.0rem; }
    [data-testid="stMarkdownContainer"] { color: #0f172a; }
    [data-testid="stCaptionContainer"] { color: #64748b !important; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stWidgetLabel"] p { color: #64748b !important; font-size: 12px; font-weight: 600; }
    div[role="radiogroup"] label p { color: #0f172a !important; font-size: 12px; }
    .side-sec {
        font-size: 10px; font-weight: 800; letter-spacing: 1px;
        color: #64748b; text-transform: uppercase; margin: 6px 0 -2px;
    }

    /* Widgets claros */
    [data-baseweb="select"] > div,
    [data-testid="stDateInput"] > div > div {
        background: #ffffff !important;
        border-color: #e2e8f0 !important;
        color: #0f172a !important;
    }
    [data-baseweb="select"] span, [data-baseweb="select"] input { color: #0f172a !important; }
    [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #ffffff !important; }
    li[role="option"] { color: #0f172a !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background: #f1f5f9 !important; }

    /* Cabeçalho */
    .top {
        display: flex; justify-content: space-between; align-items: center; gap: 16px;
        padding-bottom: 12px; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0;
    }
    .top h1 {
        margin: 0; font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: 0.3px;
    }
    .top p { margin: 2px 0 0; font-size: 13px; color: #64748b; }

    /* KPIs */
    .kpi {
        padding: 12px 14px; border-radius: 12px; min-height: 96px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .kpi.green { border-left: 3px solid #059669; }
    .kpi.red { border-left: 3px solid #dc2626; }
    .kpi.amber { border-left: 3px solid #d97706; }
    .kpi.blue { border-left: 3px solid #2563eb; }
    .kpi-t {
        font-size: 10px; font-weight: 800; letter-spacing: 0.4px;
        text-transform: uppercase; color: #64748b;
    }
    .kpi-v {
        font-size: 20px; font-weight: 800; color: #0f172a;
        margin: 8px 0 4px; font-variant-numeric: tabular-nums; white-space: nowrap;
    }
    .kpi-sub { font-size: 11px; color: #64748b; font-weight: 600; }

    /* Seções */
    .section-title {
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #0f172a; margin: 10px 0 8px; padding-left: 10px;
        border-left: 3px solid #2563eb;
        display: flex; align-items: center; gap: 8px;
    }
    .section-title span {
        font-size: 10px; font-weight: 600; text-transform: none;
        letter-spacing: 0.2px; color: #64748b; margin-left: auto;
    }

    /* Barra de Composição */
    .comp-bar-wrap {
        width: 100%; height: 14px; background-color: #e2e8f0;
        border-radius: 999px; overflow: hidden; display: flex; margin: 8px 0 10px 0;
    }
    .comp-seg-green { background-color: #059669; height: 100%; }
    .comp-seg-red { background-color: #dc2626; height: 100%; }
    .comp-legend { display: flex; gap: 20px; font-size: 11.5px; color: #475569; font-weight: 600; }
    .dot { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; }

    /* Cards de Painel */
    .panel-box {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 14px 16px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        margin-bottom: 12px; height: 100%;
    }
    .panel-title {
        font-size: 12px; font-weight: 800; color: #0f172a; text-transform: uppercase;
        letter-spacing: 0.4px; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;
    }

    /* Badges */
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 800; text-align: center; min-width: 68px; }
    .badge-critico { background-color: rgba(220, 38, 38, 0.1); color: #dc2626; border: 1px solid rgba(220, 38, 38, 0.25); }
    .badge-atencao { background-color: rgba(217, 119, 6, 0.1); color: #d97706; border: 1px solid rgba(217, 119, 6, 0.25); }
    .badge-monitorar { background-color: rgba(37, 99, 235, 0.1); color: #2563eb; border: 1px solid rgba(37, 99, 235, 0.25); }

    /* Tabelas */
    .tabela-container {
        overflow: auto; border: 1px solid #e2e8f0; border-radius: 10px;
        background: #ffffff; max-height: 480px; width: 100%;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }
    .tabela-financeira { width: 100%; border-collapse: collapse; margin: 0; font-size: 11px; color: #0f172a; }
    .tabela-financeira th {
        background: #f8fafc; color: #64748b; font-size: 10px; font-weight: 700; text-align: left;
        padding: 9px 10px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase;
        position: sticky; top: 0; z-index: 2; white-space: nowrap;
    }
    .tabela-financeira td {
        padding: 7px 10px; border-bottom: 1px solid #f1f5f9; font-size: 11px; font-weight: 600;
        color: #334155; white-space: nowrap; font-variant-numeric: tabular-nums;
    }
    .tabela-financeira tbody tr:hover td { background: #f8fafc; }
    .td-bold { font-weight: 800; color: #0f172a; }

    .insights { margin:0; padding-left:18px; color:#334155; font-size:12px; line-height:1.85; }
    .insights li { margin:4px 0; }
    [data-testid="stPlotlyChart"] { background:#fff !important; }
    @media(max-width:900px) { .main .block-container {padding:.8rem .7rem;} .kpi-v {font-size:17px;} }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# CARREGAMENTO DOS DADOS DA ABA Base_ADT
# ==============================================================================
ABA_ADT = "Base_ADT"

@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados_adt():
    conn = conectar_sheets()
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet=ABA_ADT, ttl=0)
        return df
    except Exception as e:
        st.error(f"⚠️ Erro ao ler a aba '{ABA_ADT}' do Google Sheets: {e}")
        return pd.DataFrame()

df_bruto = carregar_dados_adt()

if df_bruto.empty:
    st.warning(f"A aba **{ABA_ADT}** está vazia ou não foi encontrada na planilha conectada. Verifique o Google Sheets.")
    st.stop()

# ==============================================================================
# TRATAMENTO E LIMPEZA DOS DADOS
# ==============================================================================
def limpa_valor(val):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if pd.isna(val) or str(val).strip() in ["", "-", "nan", "NaN", "None"]:
            return 0.0
        s = str(val).strip().replace('R$', '').strip()
        if '.' in s and ',' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except Exception:
        return 0.0

df = df_bruto.copy()
df.columns = [str(c).strip() for c in df.columns]

if "Valor" in df.columns:
    df["Valor"] = df["Valor"].apply(limpa_valor)
else:
    df["Valor"] = 0.0

if "Saldo" in df.columns:
    df["Saldo"] = df["Saldo"].apply(limpa_valor)
else:
    df["Saldo"] = df["Valor"]

df["Baixado"] = (df["Valor"] - df["Saldo"]).clip(lower=0.0)

if "Data inclusão" in df.columns:
    df["Data inclusão"] = pd.to_datetime(df["Data inclusão"], dayfirst=True, errors="coerce")
else:
    df["Data inclusão"] = pd.NaT

if "Pessoa física/jurídica" in df.columns:
    df["Fornecedor"] = df["Pessoa física/jurídica"].fillna("Não Informado").astype(str).str.strip()
elif "Fornecedor" not in df.columns:
    df["Fornecedor"] = "Não Informado"

# Campos usados nos filtros/tabelas devem ser texto homogêneo.
# A planilha pode trazer Banco como número em algumas linhas e texto em outras,
# o que provoca TypeError ao executar sorted() sobre valores mistos.
if "Banco" not in df.columns:
    df["Banco"] = "Não Informado"

def limpa_texto_filtro(valor, padrao="Não Informado"):
    if pd.isna(valor):
        return padrao
    texto = str(valor).strip()
    if texto.lower() in {"", "nan", "none", "null"}:
        return padrao
    # Evita exibir códigos numéricos como "1.0" quando vierem como float.
    if isinstance(valor, (int, float, np.integer, np.floating)) and float(valor).is_integer():
        texto = str(int(valor))
    return texto

df["Banco"] = df["Banco"].apply(limpa_texto_filtro)
df["Fornecedor"] = df["Fornecedor"].apply(limpa_texto_filtro)

if "Observação" not in df.columns:
    df["Observação"] = ""
else:
    df["Observação"] = df["Observação"].fillna("").astype(str).str.strip()

data_ref = datetime(2026, 11, 18).date()
df["Dias"] = (pd.to_datetime(data_ref) - df["Data inclusão"]).dt.days.fillna(0).astype(int).clip(lower=0)

meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
df["Mes_Num"] = df["Data inclusão"].dt.month
df["Mes_Nome"] = df["Mes_Num"].map(meses_pt).fillna("N/D")

# ==============================================================================
# SIDEBAR - FILTROS EXECUTIVOS
# ==============================================================================
with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros de Adiantamentos</div>", unsafe_allow_html=True)
    meses_op = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    meses_sel = st.multiselect("Mês de inclusão", [m for m in meses_op if m in df["Mes_Nome"].unique()])
    fornecedores_sel = st.multiselect("Fornecedor", sorted(df["Fornecedor"].astype(str).unique(), key=str.casefold))
    bancos_sel = st.multiselect("Banco", sorted(df["Banco"].astype(str).unique(), key=str.casefold))
    status_saldo = st.radio("Status", ["Todos", "Somente Em Aberto (Saldo > 0)", "Somente Baixados"])

    datas = df["Data inclusão"].dropna()
    if not datas.empty:
        dt_ini, dt_fim = datas.min().date(), datas.max().date()
        periodo = st.date_input("Período de inclusão", value=(dt_ini, dt_fim), min_value=dt_ini, max_value=dt_fim)
    else:
        periodo = ()

    valor_max = max(float(df["Valor"].max()), 1.0)
    faixa_valor = st.slider("Valor do adiantamento (R$)", 0.0, valor_max, (0.0, valor_max),
                            step=max(valor_max/100, 1.0), format="R$ %.2f")
    dias_max = max(int(df["Dias"].max()), 1)
    faixa_dias = st.slider("Idade (dias)", 0, dias_max, (0, dias_max))
    busca = st.text_input("Busca livre", placeholder="Fornecedor, banco ou observação")

df_filt = df.copy()
if meses_sel:
    df_filt = df_filt[df_filt["Mes_Nome"].isin(meses_sel)]
if fornecedores_sel:
    df_filt = df_filt[df_filt["Fornecedor"].isin(fornecedores_sel)]
if bancos_sel:
    df_filt = df_filt[df_filt["Banco"].isin(bancos_sel)]
if status_saldo == "Somente Em Aberto (Saldo > 0)":
    df_filt = df_filt[df_filt["Saldo"] > 0]
elif status_saldo == "Somente Baixados":
    df_filt = df_filt[df_filt["Saldo"] <= 0]
if isinstance(periodo, (tuple, list)) and len(periodo) == 2 and periodo[0] and periodo[1]:
    df_filt = df_filt[df_filt["Data inclusão"].isna() | df_filt["Data inclusão"].dt.date.between(periodo[0], periodo[1])]
df_filt = df_filt[df_filt["Valor"].between(*faixa_valor)]
df_filt = df_filt[df_filt["Dias"].between(*faixa_dias)]
if busca.strip():
    termo = busca.strip().casefold()
    df_filt = df_filt[
        df_filt["Fornecedor"].str.casefold().str.contains(termo, na=False) |
        df_filt["Banco"].str.casefold().str.contains(termo, na=False) |
        df_filt["Observação"].astype(str).str.casefold().str.contains(termo, na=False)
    ]

# ==============================================================================
# CÁLCULOS E INDICADORES
# ==============================================================================
total_adiantado = df_filt["Valor"].sum()
total_baixado = df_filt["Baixado"].sum()
total_aberto = df_filt["Saldo"].sum()

qtd_total = len(df_filt)
qtd_forn = df_filt["Fornecedor"].nunique()
qtd_aberto = len(df_filt[df_filt["Saldo"] > 0])

pct_baixado = (total_baixado / total_adiantado * 100) if total_adiantado > 0 else 0.0
pct_aberto = (total_aberto / total_adiantado * 100) if total_adiantado > 0 else 0.0

df_aberto = df_filt[df_filt["Saldo"] > 0].copy()
def faixa_envelhecimento(dias):
    if dias <= 30: return "0–30 dias"
    if dias <= 60: return "31–60 dias"
    if dias <= 90: return "61–90 dias"
    if dias <= 180: return "91–180 dias"
    return ">180 dias"

df_aberto["Faixa_Idade"] = df_aberto["Dias"].apply(faixa_envelhecimento)

forn_grp = df_aberto.groupby("Fornecedor", as_index=False).agg(
    Saldo_Aberto=("Saldo", "sum"),
    Qtd_Itens=("Valor", "count"),
    Max_Dias=("Dias", "max")
).sort_values("Saldo_Aberto", ascending=False)

def classificar_criticidade(saldo, dias):
    if saldo >= 100_000 or (saldo >= 20_000 and dias > 90):
        return "Crítico"
    elif saldo >= 20_000 or (saldo >= 5_000 and dias > 90):
        return "Atenção"
    else:
        return "Monitorar"

forn_grp["Criticidade"] = forn_grp.apply(lambda r: classificar_criticidade(r["Saldo_Aberto"], r["Max_Dias"]), axis=1)

top5_pct = (forn_grp.head(5)["Saldo_Aberto"].sum() / total_aberto * 100) if total_aberto > 0 else 0.0
top10_pct = (forn_grp.head(10)["Saldo_Aberto"].sum() / total_aberto * 100) if total_aberto > 0 else 0.0
qtd_forn_saldo = len(forn_grp)

df_90 = df_aberto[df_aberto["Dias"] > 90]
saldo_90 = df_90["Saldo"].sum()
qtd_90 = len(df_90)

def fmt_brl(val):
    return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def fmt_int(val):
    return f"{int(val):,}".replace(',', '.')

def fmt_pct(val):
    return f"{val:.1f}%".replace('.', ',')

# ==============================================================================
# CABEÇALHO
# ==============================================================================
st.markdown(f"""
<div class="top">
    <div>
        <h1>Adiantamentos Pagos 2026 · Visão Executiva</h1>
        <p>Posição em {data_ref.strftime("%d/%m/%Y")} · {fmt_int(len(df_filt))} registros filtrados · Valores em Reais (R$)</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# KPIS
# ==============================================================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="kpi blue"><div class="kpi-t">Total Adiantado</div><div class="kpi-v">{fmt_brl(total_adiantado)}</div><div class="kpi-sub">{fmt_int(qtd_total)} adiantamentos · {fmt_int(qtd_forn)} fornecedores</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi green"><div class="kpi-t">Já Baixado</div><div class="kpi-v">{fmt_brl(total_baixado)}</div><div class="kpi-sub">{fmt_pct(pct_baixado)} do total adiantado</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi red"><div class="kpi-t">Em Aberto (Saldo)</div><div class="kpi-v">{fmt_brl(total_aberto)}</div><div class="kpi-sub">{fmt_pct(pct_aberto)} do total · {fmt_int(qtd_aberto)} itens</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi amber"><div class="kpi-t">Fornecedores com Saldo</div><div class="kpi-v">{fmt_int(qtd_forn_saldo)}</div><div class="kpi-sub">Top 5 = {fmt_pct(top5_pct)} · Top 10 = {fmt_pct(top10_pct)}</div></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="kpi red"><div class="kpi-t">Saldo > 90 Dias</div><div class="kpi-v">{fmt_brl(saldo_90)}</div><div class="kpi-sub">{fmt_int(qtd_90)} adiantamentos sem baixa</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ==============================================================================
# COMPOSIÇÃO E ANÁLISES EXECUTIVAS
# ==============================================================================
st.markdown(f"""
<div class="panel-box">
 <div class="panel-title">Composição do total adiantado: baixado × em aberto</div>
 <div class="comp-bar-wrap">
  <div class="comp-seg-green" style="width:{min(max(pct_baixado,0),100):.2f}%;"></div>
  <div class="comp-seg-red" style="width:{min(max(pct_aberto,0),100):.2f}%;"></div>
 </div>
 <div class="comp-legend">
  <div><span class="dot" style="background:#059669;"></span>Baixado {fmt_brl(total_baixado)} ({fmt_pct(pct_baixado)})</div>
  <div><span class="dot" style="background:#dc2626;"></span>Em aberto {fmt_brl(total_aberto)} ({fmt_pct(pct_aberto)})</div>
 </div>
</div>
""", unsafe_allow_html=True)

def estilo_grafico(fig, altura=300):
    fig.update_layout(height=altura, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="Inter, Segoe UI, Arial", color="#334155", size=11),
        margin=dict(l=8,r=12,t=20,b=8), legend=dict(orientation="h", y=1.02, x=0))
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#e2e8f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", zeroline=False)
    return fig

# Fornecedores críticos / classificação / envelhecimento
c_g1, c_g2, c_g3 = st.columns([1.5, 1, 1.25])
with c_g1:
    st.markdown('<div class="panel-box"><div class="panel-title">Fornecedores com maior saldo em aberto</div>', unsafe_allow_html=True)
    if not forn_grp.empty:
        top = forn_grp.head(12).sort_values("Saldo_Aberto")
        cores = [VERMELHO if x=="Crítico" else AMBAR if x=="Atenção" else AZUL for x in top["Criticidade"]]
        fig = go.Figure(go.Bar(x=top["Saldo_Aberto"], y=top["Fornecedor"], orientation="h",
            marker_color=cores, text=[fmt_brl(v) for v in top["Saldo_Aberto"]], textposition="outside"))
        fig.update_layout(showlegend=False); fig.update_xaxes(showticklabels=False); fig.update_yaxes(showgrid=False)
        st.plotly_chart(estilo_grafico(fig, 350), use_container_width=True, config={"displayModeBar":False})
    else: st.info("Sem saldo em aberto para os filtros.")
    st.markdown('</div>', unsafe_allow_html=True)

with c_g2:
    st.markdown('<div class="panel-box"><div class="panel-title">Classificação de criticidade</div>', unsafe_allow_html=True)
    if not forn_grp.empty:
        crit = forn_grp.groupby("Criticidade", as_index=False).agg(Saldo=("Saldo_Aberto","sum"), Fornecedores=("Fornecedor","nunique"))
        order = {"Crítico":0,"Atenção":1,"Monitorar":2}
        crit["_ord"] = crit["Criticidade"].map(order); crit = crit.sort_values("_ord")
        palette = {"Crítico":VERMELHO,"Atenção":AMBAR,"Monitorar":AZUL}
        fig = go.Figure(go.Bar(x=crit["Saldo"], y=crit["Criticidade"], orientation="h",
            marker_color=[palette[x] for x in crit["Criticidade"]],
            text=[f"{fmt_brl(v)} · {int(q)} forn." for v,q in zip(crit["Saldo"],crit["Fornecedores"])],
            textposition="outside", cliponaxis=False))
        fig.update_layout(showlegend=False); fig.update_xaxes(showticklabels=False); fig.update_yaxes(showgrid=False)
        st.plotly_chart(estilo_grafico(fig, 285), use_container_width=True, config={"displayModeBar":False})
        st.caption("Crítico: ≥ R$ 100 mil ou ≥ R$ 20 mil com >90 dias. Atenção: ≥ R$ 20 mil ou ≥ R$ 5 mil com >90 dias.")
    else: st.info("Sem fornecedores em aberto.")
    st.markdown('</div>', unsafe_allow_html=True)

with c_g3:
    st.markdown('<div class="panel-box"><div class="panel-title">Envelhecimento do saldo em aberto</div>', unsafe_allow_html=True)
    if not df_aberto.empty:
        env = df_aberto.groupby("Faixa_Idade", as_index=False).agg(Saldo=("Saldo","sum"), Itens=("Saldo","size"))
        ordem = ["0–30 dias","31–60 dias","61–90 dias","91–180 dias",">180 dias"]
        env["_ord"] = env["Faixa_Idade"].map({x:i for i,x in enumerate(ordem)}); env=env.sort_values("_ord")
        cc = [AZUL if x in ordem[:2] else AMBAR if x==ordem[2] else VERMELHO for x in env["Faixa_Idade"]]
        fig = go.Figure(go.Bar(x=env["Saldo"], y=env["Faixa_Idade"], orientation="h",
            marker_color=cc, text=[f"{fmt_brl(v)} · {int(q)} itens" for v,q in zip(env["Saldo"],env["Itens"])],
            textposition="outside", cliponaxis=False))
        fig.update_layout(showlegend=False); fig.update_xaxes(showticklabels=False); fig.update_yaxes(showgrid=False)
        st.plotly_chart(estilo_grafico(fig, 285), use_container_width=True, config={"displayModeBar":False})
    else: st.info("Sem saldo em aberto.")
    st.markdown('</div>', unsafe_allow_html=True)

# Evolução mensal e leitura gerencial
c_g4, c_g5 = st.columns([1, 2])
with c_g4:
    st.markdown('<div class="panel-box"><div class="panel-title">Evolução mensal: baixado × em aberto</div>', unsafe_allow_html=True)
    mensal = df_filt.dropna(subset=["Data inclusão"]).groupby("Mes_Num", as_index=False).agg(Baixado=("Baixado","sum"), Aberto=("Saldo","sum"))
    if not mensal.empty:
        mensal=mensal.sort_values("Mes_Num"); mensal["Mês"]=mensal["Mes_Num"].map(meses_pt)
        fig=go.Figure()
        fig.add_bar(x=mensal["Mês"],y=mensal["Baixado"],name="Baixado",marker_color=VERDE)
        fig.add_bar(x=mensal["Mês"],y=mensal["Aberto"],name="Em aberto",marker_color=VERMELHO)
        fig.update_layout(barmode="stack"); fig.update_yaxes(tickprefix="R$ ",tickformat=",.0f")
        st.plotly_chart(estilo_grafico(fig,270),use_container_width=True,config={"displayModeBar":False})
    else: st.info("Sem datas válidas.")
    st.markdown('</div>', unsafe_allow_html=True)

with c_g5:
    st.markdown('<div class="panel-box"><div class="panel-title">Principais conclusões</div>', unsafe_allow_html=True)
    if total_adiantado > 0:
        top3=(forn_grp.head(3)["Saldo_Aberto"].sum()/total_aberto*100) if total_aberto>0 else 0
        criticos=forn_grp[forn_grp["Criticidade"]=="Crítico"] if not forn_grp.empty else forn_grp
        saldo_crit=criticos["Saldo_Aberto"].sum() if not criticos.empty else 0
        recente=df_aberto.loc[df_aberto["Dias"]<=30,"Saldo"].sum() if not df_aberto.empty else 0
        pct_rec=recente/total_aberto*100 if total_aberto>0 else 0
        linhas=[
          f"Do total adiantado de <b>{fmt_brl(total_adiantado)}</b>, <b>{fmt_pct(pct_baixado)}</b> já foi baixado; permanecem <b>{fmt_brl(total_aberto)}</b> em aberto.",
          f"Os 3 maiores fornecedores concentram <b>{fmt_pct(top3)}</b> do saldo aberto.",
          f"<b>{len(criticos)} fornecedores críticos</b> concentram <b>{fmt_brl(saldo_crit)}</b>.",
          f"<b>{fmt_brl(saldo_90)}</b> estão há mais de 90 dias sem baixa ({fmt_int(qtd_90)} itens).",
          f"Adiantamentos de até 30 dias representam <b>{fmt_pct(pct_rec)}</b> do saldo."
        ]
        st.markdown("<ul class='insights'>"+''.join(f"<li>{x}</li>" for x in linhas)+"</ul>",unsafe_allow_html=True)
    else: st.info("Sem valores para análise.")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# TABELAS DETALHADAS
# ==============================================================================
col_t1, col_t2 = st.columns(2)

with col_t1:
    st.markdown('<div class="panel-box"><div class="panel-title">Top 20 Fornecedores com Saldo em Aberto</div>', unsafe_allow_html=True)
    if not forn_grp.empty:
        html_t1 = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>Fornecedor</th><th style="text-align:right">Saldo em Aberto</th><th style="text-align:right">Itens</th><th style="text-align:right">% do saldo</th><th style="text-align:right">Mais antigo (dias)</th><th style="text-align:center">Criticidade</th></tr></thead><tbody>'
        for idx, r in forn_grp.head(20).iterrows():
            c_cls = "badge-critico" if r["Criticidade"] == "Crítico" else ("badge-atencao" if r["Criticidade"] == "Atenção" else "badge-monitorar")
            pct_fornecedor = (r["Saldo_Aberto"] / total_aberto * 100) if total_aberto > 0 else 0
            html_t1 += f'<tr><td>{idx+1}</td><td class="td-bold">{html.escape(str(r["Fornecedor"]))}</td><td style="text-align:right" class="td-bold">{fmt_brl(r["Saldo_Aberto"])}</td><td style="text-align:right">{int(r["Qtd_Itens"])}</td><td style="text-align:right">{fmt_pct(pct_fornecedor)}</td><td style="text-align:right">{int(r["Max_Dias"])}</td><td style="text-align:center"><span class="badge {c_cls}">{r["Criticidade"]}</span></td></tr>' 
        html_t1 += '</tbody></table></div>'
        st.markdown(html_t1, unsafe_allow_html=True)
    else:
        st.info("Nenhum registro encontrado.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_t2:
    st.markdown('<div class="panel-box"><div class="panel-title">15 Maiores Adiantamentos em Aberto</div>', unsafe_allow_html=True)
    top15 = df_aberto.sort_values("Saldo", ascending=False).head(15)
    if not top15.empty:
        html_t2 = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>Adiant.</th><th>Fornecedor</th><th>Banco</th><th style="text-align:center">Inclusão</th><th style="text-align:right">Valor</th><th style="text-align:right">Saldo</th><th style="text-align:right">Dias</th><th>Observação</th></tr></thead><tbody>'
        for _, r in top15.iterrows():
            dt_inc = r["Data inclusão"].strftime("%d/%m/%Y") if pd.notna(r["Data inclusão"]) else "—"
            id_col = next((c for c in ["Adiant.", "Adiantamento", "ID", "Código"] if c in r.index), None)
            id_item = html.escape(str(r[id_col])) if id_col else "—"
            html_t2 += f'<tr><td>{id_item}</td><td class="td-bold">{html.escape(str(r["Fornecedor"]))}</td><td>{html.escape(str(r["Banco"]))}</td><td style="text-align:center">{dt_inc}</td><td style="text-align:right">{fmt_brl(r["Valor"])}</td><td style="text-align:right" class="td-bold">{fmt_brl(r["Saldo"])}</td><td style="text-align:right">{int(r["Dias"])}</td><td>{html.escape(str(r["Observação"]))}</td></tr>' 
        html_t2 += '</tbody></table></div>'
        st.markdown(html_t2, unsafe_allow_html=True)
    else:
        st.info("Nenhum registro encontrado.")
    st.markdown('</div>', unsafe_allow_html=True)
