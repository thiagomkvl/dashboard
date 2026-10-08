import streamlit as st

# O set_page_config OBRIGATORIAMENTE tem que ser a primeira chamada do Streamlit
st.set_page_config(
    page_title="Faturamento & Situação das Contas",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded",
)

import re
import textwrap
import unicodedata
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

# BLINDAGEM DE CONEXÃO (mesmo padrão do painel financeiro)
try:
    from database import conectar_sheets
except Exception as _err:
    _erro_import_db = str(_err)

    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {_erro_import_db}")
        return None

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
# Espaçamento vertical
ESPACO_ENTRE_BLOCOS = "1.0rem"  # espaço geral entre os elementos da página
AJUSTE_APOS_KPIS = "1.0rem"    # espaço extra entre os cards do topo e os blocos

ABA_BASE = "Base_Contas"  # uma linha por conta (substitui as 3 abas dinâmicas)

AZUL, VERDE, AMBAR, VERMELHO = "#3b82f6", "#10b981", "#f59e0b", "#ef4444"
ROXO, LARANJA, CIANO, ROSA = "#8b5cf6", "#f97316", "#22d3ee", "#fb7185"
TXT, MUTED, BORDA = "#e6ecf5", "#8fa3c4", "#1c2a47"

# Cor de cada Situação (chave normalizada: minúsculo e sem acento)
COR_SIT = {
    "liquidada": VERDE, "em faturamento": AZUL, "em producao": CIANO,
    "recebimentos futuros": ROXO, "inadimplencias": VERMELHO,
    "glosas nao analisadas": AMBAR, "recursos enviados": LARANJA, "recursos negados": ROSA,
    "glosa acatada": "#94a3b8",
}
ORDEM_SIT = list(COR_SIT)

# Agrupamento das Situações nos KPIs (regra por palavra-chave)
CATS = ["Em Produção", "Em Faturamento", "Recebido", "A receber", "Inadimplência", "Glosas e Recursos", "Recursos Negados"]

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# ==============================================================================
# CSS
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #0a1020 !important; color: #e6ecf5; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: __GAP__; }
    [data-testid="stMarkdownContainer"] { color: #e6ecf5; }
    [data-testid="stCaptionContainer"] { color: #8fa3c4 !important; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #0b1326 !important; border-right: 1px solid #1a2744; }
    [data-testid="stWidgetLabel"] p { color: #8fa3c4 !important; font-size: 12px; font-weight: 600; }
    .side-sec { font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #8fa3c4; text-transform: uppercase; margin: 6px 0 -2px; }
    .side-card { background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 10px; padding: 10px 12px; margin-top: 8px; }
    .side-card small { display: block; color: #8fa3c4; font-size: 11px; }
    .side-card b { color: #e6ecf5; font-size: 13px; }

    /* Widgets escuros */
    [data-baseweb="select"] > div { background: #101b32 !important; border-color: #1e2d4d !important; color: #e6ecf5 !important; }
    [data-baseweb="select"] span, [data-baseweb="select"] input { color: #e6ecf5 !important; }
    [data-baseweb="select"] svg { fill: #8fa3c4; }
    [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #101b32 !important; }
    li[role="option"] { color: #e6ecf5 !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background: #1a2a4a !important; }
    span[data-baseweb="tag"] { background: #f97316 !important; color: #fff !important; }
    .stButton > button { background: linear-gradient(135deg, #f97316, #ea580c); color: #fff; border: none; border-radius: 10px; font-weight: 700; padding: 0.55rem 1rem; }
    .stButton > button:hover { filter: brightness(1.1); color: #fff; border: none; }

    /* Cabeçalho */
    .top { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px solid #1a2744; }
    .top h1 { margin: 0; padding: 0; font-size: 22px; font-weight: 800; letter-spacing: 0.3px; color: #fff; }
    .top p { margin: 2px 0 0; font-size: 13px; color: #8fa3c4; }
    .pills { display: flex; gap: 10px; }
    .pill { background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 10px; padding: 6px 14px; min-width: 120px; }
    .pill small { display: block; font-size: 10px; color: #8fa3c4; }
    .pill b { font-size: 13px; color: #fff; white-space: nowrap; }

    /* Filtro por clique */
    .chips { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 8px 0; }
    .chips-t { font-size: 10px; font-weight: 800; letter-spacing: 0.8px; text-transform: uppercase; color: #8fa3c4; }
    .chip { background: rgba(249,115,22,0.14); border: 1px solid rgba(249,115,22,0.4); color: #fdba74; border-radius: 999px; padding: 4px 12px; font-size: 12px; font-weight: 600; }

    /* KPIs */
    .kpi { padding: 12px; border-radius: 12px; height: 100px; container-type: inline-size; overflow: hidden; margin-bottom: __KPI_GAP__; background: linear-gradient(135deg, rgba(59,130,246,0.10), #0f1a2e 70%); border: 1px solid rgba(59,130,246,0.22); }
    .kpi-top { display: flex; align-items: flex-start; gap: 8px; }
    .kpi-t { font-size: 10px; font-weight: 800; letter-spacing: 0.4px; text-transform: uppercase; line-height: 1.2; min-height: 24px; color: #9db2d3; }
    .kpi-v { font-size: clamp(11px, 1vw, 18px); font-size: clamp(11px, 11cqw, 20px); font-weight: 800; color: #fff; letter-spacing: -0.3px; white-space: nowrap; margin: 8px 0 3px; font-variant-numeric: tabular-nums; }
    .kpi-sub { font-size: 11px; color: #8fa3c4; font-weight: 600; }
    .kpi-sub.up { color: #34d399; }
    .kpi-sub.down { color: #f87171; }
    .kpi-sub span { color: #8fa3c4; font-weight: 500; }
    .kpi-sub b { color: #dbe6f7; }

    /* Cards */
    [data-testid="stVerticalBlockBorderWrapper"] { background: #0f1a2e; border: 1px solid #1c2a47 !important; border-radius: 12px; }
    .card-title { display: flex; align-items: center; justify-content: space-between; font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase; color: #fff; margin: 2px 0 4px; }
    .card-title span { font-size: 10px; font-weight: 600; letter-spacing: 0.2px; text-transform: none; color: #8fa3c4; }
    .vazio { color: #8fa3c4; font-size: 12px; padding: 24px 6px; text-align: center; }
    .leg { display: grid; grid-template-columns: 12px 1fr 52px 78px; gap: 8px; align-items: center; font-size: 11.5px; padding: 3px 0; color: #c6d3ea; }
    .leg i { width: 9px; height: 9px; border-radius: 50%; display: block; }
    .leg em { font-style: normal; color: #8fa3c4; }
    .leg b { color: #fff; font-weight: 700; }

    /* Tabelas */
    .tbl-wrap { overflow: auto; max-height: 330px; border-radius: 8px; }
    .tbl { width: 100%; border-collapse: collapse; font-size: 12px; color: #dbe6f7; }
    .tbl th { position: sticky; top: 0; z-index: 2; background: #0f1a2e; color: #8fa3c4; font-weight: 600; font-size: 11px; text-align: left; padding: 7px 8px; border-bottom: 1px solid #1c2a47; white-space: nowrap; }
    .tbl td { padding: 7px 8px; border-bottom: 1px solid #16213a; white-space: nowrap; text-align: left; font-variant-numeric: tabular-nums; }
    .tbl tbody tr:hover td { background: #13203a; }
    .tbl tr.tot td { font-weight: 800; color: #fff; background: #0d1730; border-top: 1px solid #2a3a5c; }
    .tbl .mut { color: #6b7fa3; }
    .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
    .bar { height: 8px; min-width: 90px; background: #16213a; border-radius: 4px; overflow: hidden; }
    .bar span { display: block; height: 100%; border-radius: 4px; }
    .tbl-wrap::-webkit-scrollbar { height: 6px; width: 6px; }
    .tbl-wrap::-webkit-scrollbar-thumb { background: #2a3a5c; border-radius: 6px; }
</style>
"""
st.markdown(textwrap.dedent(css).replace("__GAP__", ESPACO_ENTRE_BLOCOS).replace("__KPI_GAP__", AJUSTE_APOS_KPIS),
            unsafe_allow_html=True)


# ==============================================================================
# 1. FUNÇÕES AUXILIARES
# ==============================================================================
def normalizar_texto(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return ""
    return unicodedata.normalize("NFKD", str(txt)).encode("ASCII", "ignore").decode("utf-8").lower().strip()


def limpa_valor(v):
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace("R$", "").replace(" ", "")
        if s in ("", "-", "nan", "None"):
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


def _serial_para_mes(n):
    if 20000 < n < 80000:  # data serial do Sheets/Excel
        d = pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
        return pd.Timestamp(d.year, d.month, 1)
    return None


def parse_mes(c):
    """Converte 'janeiro-26', 'jan/26', '2026-01-15', '01/01/2026', data ou serial no 1º dia do mês."""
    if c is None:
        return None
    if isinstance(c, (pd.Timestamp, datetime)):
        return None if pd.isna(c) else pd.Timestamp(c.year, c.month, 1)
    if isinstance(c, float) and pd.isna(c):
        return None
    if isinstance(c, (int, float)) and not isinstance(c, bool):
        return _serial_para_mes(float(c))
    t = normalizar_texto(c)
    if not t or t in ("nan", "none", "nat"):
        return None
    m = re.match(r"^([a-z]{3,9})[\s\-/\.]*(\d{2}|\d{4})$", t)
    if m and m.group(1)[:3] in MESES:
        ano = int(m.group(2))
        ano += 2000 if ano < 100 else 0
        return pd.Timestamp(ano, MESES[m.group(1)[:3]], 1)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        return pd.Timestamp(int(m.group(3)), int(m.group(2)), 1)
    m = re.match(r"^(\d{4})-(\d{1,2})(?:-\d{1,2})?(?:[ t].*)?$", t)
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)
    m = re.match(r"^(\d{1,2})/(\d{4})$", t)
    if m:
        return pd.Timestamp(int(m.group(2)), int(m.group(1)), 1)
    if re.fullmatch(r"\d{5}(\.\d+)?", t):
        return _serial_para_mes(float(t))
    return None


def rot_mes(ref):
    return f"{ABREV[ref.month - 1]}/{str(ref.year)[2:]}"


def _br(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(v, casas=0):
    return "R$ " + _br(v, casas)


def num(v):
    return "-" if abs(v) < 0.005 else _br(v)


def abrev(v):
    a = abs(v)
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


def categoria(sit):
    n = normalizar_texto(sit)
    if "liquid" in n:
        return "Recebido"
    if "inadimpl" in n:
        return "Inadimplência"
    if "recursos negados" in n:
        return "Recursos Negados"
    if "glosa" in n or "recurso" in n:
        return "Glosas e Recursos"
    if "producao" in n:
        return "Em Produção"
    if "faturamento" in n:
        return "Em Faturamento"
    return "A receber"


def cor_sit(sit):
    return COR_SIT.get(normalizar_texto(sit), "#94a3b8")


def ordem_sit(sit):
    n = normalizar_texto(sit)
    return (ORDEM_SIT.index(n) if n in ORDEM_SIT else 99, n)


def cor_taxa(p):
    return VERDE if p >= 90 else AMBAR if p >= 75 else VERMELHO


# ==============================================================================
# 2. LEITURA DIRETO DA BASE_CONTAS
# ==============================================================================
# >>> BASE_INICIO
OBRIG = {"mes": "mes faturamento", "conv": "convenio conta", "sit": "situacao conta",
         "val": "valor conta", "rec": "valor recebido"}
NOME_COL = {"mes": "Mês Faturamento", "conv": "Convênio Conta", "sit": "Situação Conta",
            "val": "Valor Conta", "rec": "Valor Recebido"}
COL_ACAT, COL_SALDO = "glosa acatada", "saldo total"


def mapa_colunas(cols):
    return {normalizar_texto(c): c for c in cols}


def localizar_colunas(raw):
    """Acha as colunas pelo cabeçalho (ignora acento/caixa); procura o cabeçalho nas 20 primeiras linhas."""
    df = raw.copy()
    if not all(v in mapa_colunas(df.columns) for v in OBRIG.values()):
        for i in range(min(20, len(df))):
            if all(v in mapa_colunas(df.iloc[i].tolist()) for v in OBRIG.values()):
                df.columns = list(df.iloc[i])
                df = df.iloc[i + 1:].reset_index(drop=True)
                break
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]
    return df, mapa_colunas(df.columns)


def texto_limpo(serie, padrao):
    t = serie.fillna("").astype(str).str.strip()
    return t.where(~t.isin(["", "nan", "None", "NaT"]), padrao)


@st.cache_data(ttl=60, show_spinner="Carregando Base_Contas…")
def carregar_base():
    """
    Cada conta vira até 3 partes (a soma sempre fecha com o Valor Conta):
      1) Valor Recebido  -> situação 'Liquidada' (vale para qualquer situação da conta, inclusive glosas)
      2) Glosa Acatada   -> situação 'Glosa Acatada' (em contas liquidadas, a diferença também entra aqui)
      3) Restante        -> permanece na Situação Conta original
    """
    vazio = pd.DataFrame(columns=["Situação", "Convênio", "Ref", "Valor"])
    conn = conectar_sheets()
    if conn is None:
        return vazio, ["Conexão com o Google Sheets indisponível."], []
    try:
        raw = conn.read(worksheet=ABA_BASE, ttl=0)
    except Exception as e:
        return vazio, [f"Aba '{ABA_BASE}': {e}"], []
    if raw is None or raw.empty:
        return vazio, [f"A aba '{ABA_BASE}' está vazia."], []

    df, m = localizar_colunas(raw)
    faltando = [NOME_COL[k] for k, v in OBRIG.items() if v not in m]
    if faltando:
        return vazio, [f"Aba '{ABA_BASE}': colunas não encontradas: {', '.join(faltando)}."], []

    notas = []
    val = df[m[OBRIG["val"]]].apply(limpa_valor)
    rec = df[m[OBRIG["rec"]]].apply(limpa_valor)
    if COL_ACAT in m:
        acat = df[m[COL_ACAT]].apply(limpa_valor)
    else:
        acat = pd.Series(0.0, index=df.index)
        notas.append("Coluna 'Glosa Acatada' não encontrada; considerada como zero.")
    conv = texto_limpo(df[m[OBRIG["conv"]]], "(Sem convênio)")
    sit = texto_limpo(df[m[OBRIG["sit"]]], "(Sem situação)")

    col_mes = df[m[OBRIG["mes"]]].astype(str)
    mapa_mes = {u: parse_mes(u) for u in col_mes.unique()}
    ref = col_mes.map(mapa_mes)
    sem_mes = ref.isna()
    if sem_mes.any() and val[sem_mes].abs().sum() > 0.005:
        notas.append(f"{int(sem_mes.sum())} contas (R$ {_br(float(val[sem_mes].sum()), 2)}) sem 'Mês Faturamento' "
                     "válido ficaram fora do painel.")

    liquidada = sit.apply(normalizar_texto).str.contains("liquid")
    resto = val - rec - acat
    partes = pd.concat([
        pd.DataFrame({"Situação": "Liquidada", "Convênio": conv, "Ref": ref, "Valor": rec}),
        pd.DataFrame({"Situação": "Glosa Acatada", "Convênio": conv, "Ref": ref,
                      "Valor": acat + resto.where(liquidada, 0.0)}),
        pd.DataFrame({"Situação": sit, "Convênio": conv, "Ref": ref, "Valor": resto.where(~liquidada, 0.0)}),
    ], ignore_index=True)
    partes = partes[partes["Ref"].notna() & (partes["Valor"].abs() > 0.005)].copy()
    if partes.empty:
        return vazio, [f"Aba '{ABA_BASE}' sem contas com 'Mês Faturamento' reconhecido."], notas
    partes["Ref"] = pd.to_datetime(partes["Ref"])
    base = partes.groupby(["Situação", "Convênio", "Ref"], as_index=False)["Valor"].sum()

    if COL_SALDO in m:
        saldo = df[m[COL_SALDO]].apply(limpa_valor)
        dif = float((val - rec - acat - saldo).abs().sum())
        if dif > 1:
            notas.append("Conferência: o 'Saldo Total' da planilha difere de (Valor Conta − Valor Recebido − "
                         f"Glosa Acatada) em R$ {_br(dif, 2)} (soma das diferenças por conta).")
    return base, [], notas
# >>> BASE_FIM


sc, erros, notas = carregar_base()

meses_all = sorted(set(sc["Ref"]))
if not meses_all:
    for e in erros:
        st.warning(e)
    st.warning("⚠️ Nenhum dado encontrado na base de contas.")
    st.stop()
rot = {m: rot_mes(m) for m in meses_all}
rot_inv = {v: k for k, v in rot.items()}

# ==============================================================================
# 3. SIDEBAR (FILTROS)
# ==============================================================================
with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)
    c_a, c_b = st.columns(2)
    ini = c_a.selectbox("De", meses_all, index=0, format_func=rot.get)
    fim = c_b.selectbox("Até", meses_all, index=len(meses_all) - 1, format_func=rot.get)
    conv_sel = st.multiselect("Convênio", sorted(set(sc["Convênio"])), placeholder="Todos")
    sit_sel = st.multiselect("Situação", sorted(set(sc["Situação"]), key=ordem_sit), placeholder="Todas")
    if st.button("↻ Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if ini > fim:
    ini, fim = fim, ini
refs_sel = [m for m in meses_all if ini <= m <= fim]
n_ref, i0 = len(refs_sel), meses_all.index(refs_sel[0])
refs_prev = meses_all[i0 - n_ref:i0] if i0 - n_ref >= 0 else []

# ==============================================================================
# 4. PREPARAÇÃO DOS DADOS
# ==============================================================================
base_f = sc
if conv_sel:
    base_f = base_f[base_f["Convênio"].isin(conv_sel)]
if sit_sel:
    base_f = base_f[base_f["Situação"].isin(sit_sel)]
base_f = base_f.assign(Cat=base_f["Situação"].map(categoria))

# Dados dos gráficos "condutores" (clicáveis): só respeitam os filtros da barra lateral
drv = base_f[base_f["Ref"].isin(refs_sel)]
sits_stack = sorted(drv["Situação"].unique(), key=ordem_sit)  # ordem das séries do gráfico empilhado

# ---- Filtro por clique nos gráficos (estilo cross-filter) --------------------
VER = st.session_state.setdefault("ver_sel", 0)
K_EV, K_ST = f"sel_ev_{VER}", f"sel_st_{VER}"


def pontos_sel(chave):
    try:
        return list(st.session_state[chave]["selection"]["points"])
    except Exception:
        return []


def sit_do_ponto(p):
    for k in ("customdata", "legendgroup"):
        v = p.get(k)
        if isinstance(v, (list, tuple)) and v:
            v = v[0]
        if isinstance(v, str) and v in sits_stack:
            return v
    cn = p.get("curve_number")
    return sits_stack[cn] if isinstance(cn, int) and 0 <= cn < len(sits_stack) else None


meses_click, sits_click = set(), set()
for p in pontos_sel(K_EV):
    if rot_inv.get(p.get("x")) is not None:
        meses_click.add(rot_inv[p.get("x")])
for p in pontos_sel(K_ST):
    if rot_inv.get(p.get("x")) is not None:
        meses_click.add(rot_inv[p.get("x")])
    nome_sit = sit_do_ponto(p)
    if nome_sit:
        sits_click.add(nome_sit)
meses_click &= set(refs_sel)
filtro_click = bool(meses_click or sits_click)

# Meses efetivos para os blocos filtrados (sem clique = todos do período)
refs_c = [m for m in refs_sel if m in meses_click] or refs_sel
x_lab_c = [rot[m] for m in refs_c]

cons = base_f[base_f["Ref"].isin(refs_c)]
if sits_click:
    cons = cons[cons["Situação"].isin(sits_click)]
sit_df = cons  # Situação, Convênio, Ref, Valor, Cat
conv_df = cons.groupby(["Convênio", "Ref"], as_index=False)["Valor"].sum()
cruz = cons
prev_df = base_f[base_f["Ref"].isin([] if filtro_click else refs_prev)]


def totais(d):
    g = d.groupby("Cat")["Valor"].sum()
    return float(g.sum()), {c: float(g.get(c, 0.0)) for c in CATS}


tot, cat = totais(cons)
tot_p, cat_p = totais(prev_df)

mes_a_mes = bool(conv_sel)  # com convênio filtrado, os blocos passam a mostrar mês a mês

if cruz.empty:
    perf = pd.DataFrame()
else:
    perf = cruz.pivot_table(index="Ref" if mes_a_mes else "Convênio", columns="Cat", values="Valor",
                            aggfunc="sum", fill_value=0.0)
    for c in CATS:
        if c not in perf.columns:
            perf[c] = 0.0
    perf = perf[CATS]
    perf["Faturado"] = perf.sum(axis=1)
    if mes_a_mes:
        perf = perf.reindex(refs_c, fill_value=0.0)
        perf.index = [rot[m] for m in refs_c]
    else:
        perf = perf[perf["Faturado"].abs() > 0.005]

x_lab = [rot[m] for m in refs_sel]


# ==============================================================================
# 5. COMPONENTES VISUAIS
# ==============================================================================
def barra(w, cor):
    return f"<div class='bar'><span style='width:{max(0.0, min(100.0, w)):.1f}%;background:{cor}'></span></div>"


def tabela(heads, rows, total=None, altura=330):
    th = "".join(f"<th>{h}</th>" for h in heads)
    tb = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    if total:
        tb += "<tr class='tot'>" + "".join(f"<td>{c}</td>" for c in total) + "</tr>"
    return f"<div class='tbl-wrap' style='max-height:{altura}px'><table class='tbl'><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>"


def vazio_html(msg):
    return f"<div class='vazio'>{msg}</div>"


ALT_CARD = 430  # altura fixa dos blocos das linhas 1 e 2 (mantém tudo alinhado)


def card(coluna, titulo, dica="", fixo=True):
    try:
        ct = coluna.container(border=True, height=ALT_CARD) if fixo else coluna.container(border=True)
    except TypeError:  # versões antigas do Streamlit sem o parâmetro height
        ct = coluna.container(border=True)
    ct.markdown(f"<div class='card-title'>{titulo}<span>{dica}</span></div>", unsafe_allow_html=True)
    return ct


HEAD_ROT = ["Mês"] if mes_a_mes else ["#", "Convênio"]


def rot_cols(i, nome, negrito=False):
    nome = f"<b>{nome}</b>" if negrito else nome
    return [nome] if mes_a_mes else [f"<span class='mut'>{i}</span>", nome]


def layout(fig, h=330, legenda=True):
    fig.update_layout(
        height=h, margin=dict(l=0, r=0, t=30 if legenda else 4, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=11, color=MUTED),
        separators=",.", showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11)),
        hoverlabel=dict(bgcolor="#101b32", font_color=TXT, bordercolor=BORDA),
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDA, tickfont=dict(size=10))
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.12)", zeroline=False, tickprefix="R$ ", tickformat=".2s")
    return fig


def grafico_click(ct, fig, chave):
    """Gráfico clicável: o clique vira filtro do painel (precisa de Streamlit com on_select)."""
    cfg = {"displayModeBar": False}
    try:
        ct.plotly_chart(fig, use_container_width=True, config=cfg, key=chave,
                        on_select="rerun", selection_mode="points")
    except TypeError:  # Streamlit antigo, sem seleção em gráficos
        ct.plotly_chart(fig, use_container_width=True, config=cfg)


def kpi(titulo, valor, sub, cor=None):
    estilo = f" style='color:{cor}'" if cor else ""
    return (
        "<div class='kpi'>"
        f"<div class='kpi-top'><div class='kpi-t'{estilo}>{titulo}</div></div>"
        f"<div class='kpi-v'>{valor}</div>{sub}</div>"
    )


def sub_delta(atual, ant):
    if not ant:
        return "<div class='kpi-sub'><span>sem período anterior</span></div>"
    v = (atual / ant - 1) * 100
    cls, seta = ("up", "↑") if v >= 0 else ("down", "↓")
    return f"<div class='kpi-sub {cls}'>{seta} {pct(abs(v))} <span>vs. período anterior</span></div>"


def sub_pct(v):
    return f"<div class='kpi-sub'><b>{pct(div(v, tot) * 100)}</b> do faturado</div>"


# ==============================================================================
# 6. CABEÇALHO E KPIs
# ==============================================================================
txt_per = f"{rot[refs_sel[0]]} – {rot[refs_sel[-1]]}"
txt_conv = "Todos" if not conv_sel else (conv_sel[0] if len(conv_sel) == 1 else f"{len(conv_sel)} selecionados")
txt_sit = "Todas" if not sit_sel else (sit_sel[0] if len(sit_sel) == 1 else f"{len(sit_sel)} selecionadas")

st.markdown(
    "<div class='top'><div><h1>FATURAMENTO &amp; SITUAÇÃO DAS CONTAS</h1>"
    "<p>Visão completa do faturamento por convênio e situação das contas</p></div>"
    f"<div class='pills'><div class='pill'><small>Período</small><b>{txt_per}</b></div>"
    f"<div class='pill'><small>Convênio</small><b>{txt_conv}</b></div>"
    f"<div class='pill'><small>Situação</small><b>{txt_sit}</b></div></div></div>",
    unsafe_allow_html=True,
)
for e in erros:
    st.warning(e)
for n in notas:
    st.caption(f"ℹ️ {n}")

if filtro_click:
    chips = []
    if meses_click:
        chips.append("Mês: " + ", ".join(rot[m] for m in sorted(meses_click)))
    if sits_click:
        chips.append("Situação: " + ", ".join(sorted(sits_click, key=ordem_sit)))
    cc1, cc2 = st.columns([7, 1.2])
    cc1.markdown("<div class='chips'><span class='chips-t'>Filtro por clique</span>"
                 + "".join(f"<span class='chip'>{x}</span>" for x in chips) + "</div>", unsafe_allow_html=True)
    if cc2.button("✕ Limpar", use_container_width=True):
        st.session_state["ver_sel"] = VER + 1
        st.rerun()

# Combina "Em Produção" e "Em Faturamento" em um único KPI card superior
val_prod_fat = cat["Em Produção"] + cat["Em Faturamento"]

# Cores dos títulos = cores da Composição por situação
kpis = [
    kpi("Faturamento total", moeda(tot), sub_delta(tot, tot_p)),
    kpi(f"<span style='color:{CIANO}'>Em prod.</span> / <span style='color:{AZUL}'>Faturamento</span>",
        moeda(val_prod_fat), sub_pct(val_prod_fat)),
    kpi("Recebido", moeda(cat["Recebido"]), sub_delta(cat["Recebido"], cat_p["Recebido"]), VERDE),
    kpi("A receber", moeda(cat["A receber"]), sub_pct(cat["A receber"]), ROXO),
    kpi("Inadimplência", moeda(cat["Inadimplência"]), sub_pct(cat["Inadimplência"]), VERMELHO),
    kpi(f"<span style='color:{AMBAR}'>Glosas</span> e <span style='color:{LARANJA}'>recursos</span>",
        moeda(cat["Glosas e Recursos"]), sub_pct(cat["Glosas e Recursos"])),
    kpi("Recursos negados", moeda(cat["Recursos Negados"]), sub_pct(cat["Recursos Negados"]), ROSA),
    kpi("Taxa de Recebimento", pct(div(cat["Recebido"], tot) * 100), "<div class='kpi-sub'>do faturado</div>", VERDE),
]
for col, html in zip(st.columns(8, gap="small"), kpis):
    col.markdown(html, unsafe_allow_html=True)

# ==============================================================================
# 7. LINHA 1: EVOLUÇÃO | COMPOSIÇÃO POR SITUAÇÃO | FATURAMENTO POR CONVÊNIO
# ==============================================================================
b1, b2, b3 = st.columns([1.6, 1.1, 1.3], gap="small")

with b1:
    ct = card(b1, "Faturamento × Recebido (R$)", "por mês · clique para filtrar")
    tot_m = drv.groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0)
    liq_m = drv[drv["Cat"] == "Recebido"].groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0)
    fig_ev = go.Figure()
    for nome, serie, cor, fill in (
        ("Faturamento total", tot_m, AZUL, "rgba(59,130,246,0.14)"),
        ("Recebido", liq_m, VERDE, "rgba(16,185,129,0.18)"),
    ):
        fig_ev.add_trace(go.Scatter(
            x=x_lab, y=serie.values, name=nome, mode="lines+markers", line=dict(color=cor, width=2.5),
            marker=dict(size=8), fill="tozeroy", fillcolor=fill,
            selected=dict(marker=dict(size=12, opacity=1)), unselected=dict(marker=dict(opacity=0.55)),
            hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>" + nome + "</extra>",
        ))
    grafico_click(ct, layout(fig_ev), K_EV)

with b2:
    ct = card(b2, "Composição por situação")
    g_sit = sit_df.groupby("Situação")["Valor"].sum()
    g_sit = g_sit[g_sit > 0.005]
    if g_sit.empty:
        ct.markdown(vazio_html("Sem dados no período"), unsafe_allow_html=True)
    else:
        sits = sorted(g_sit.index, key=ordem_sit)
        fig_do = go.Figure(go.Pie(
            labels=sits, values=[g_sit[x] for x in sits], hole=0.64, sort=False, textinfo="none",
            marker=dict(colors=[cor_sit(x) for x in sits], line=dict(color="#0f1a2e", width=2)),
            hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        ))
        layout(fig_do, 150, False)
        fig_do.update_layout(annotations=[dict(
            text=f"<b>{abrev(g_sit.sum())}</b><br><span style='font-size:10px'>Total faturado</span>",
            showarrow=False, font=dict(size=14, color="#fff"))])
        ct.plotly_chart(fig_do, use_container_width=True, config={"displayModeBar": False})
        leg = "".join(
            f"<div class='leg'><i style='background:{cor_sit(x)}'></i><span>{x}</span>"
            f"<em>{pct(div(g_sit[x], g_sit.sum()) * 100)}</em><b>{abrev(g_sit[x])}</b></div>" for x in sits)
        ct.markdown(f"<div>{leg}</div>", unsafe_allow_html=True)

with b3:
    ct = card(b3, "Faturamento mês a mês" if mes_a_mes else "Convênios por faturamento")
    if mes_a_mes and not perf.empty:
        fat = perf[["Faturado"]]
    else:
        fat = conv_df.groupby("Convênio")["Valor"].sum().to_frame("Faturado")
        fat = fat[fat["Faturado"] > 0].sort_values("Faturado", ascending=False)
    if fat.empty:
        ct.markdown(vazio_html("Sem dados no período"), unsafe_allow_html=True)
    else:
        mx, tt = fat["Faturado"].max(), fat["Faturado"].sum()
        rows = [rot_cols(i, nome) + [abrev(r["Faturado"]), barra(div(r["Faturado"], mx) * 100, AZUL),
                                     pct(div(r["Faturado"], tt) * 100)]
                for i, (nome, r) in enumerate(fat.iterrows(), 1)]
        ct.markdown(tabela(HEAD_ROT + ["Faturamento", "", "%"], rows), unsafe_allow_html=True)

# ==============================================================================
# 8. LINHA 2: SITUAÇÃO POR MÊS | INADIMPLÊNCIA | TAXA DE RECEBIMENTO
# ==============================================================================
c1, c2, c3 = st.columns([1.6, 1.1, 1.3], gap="small")

with c1:
    ct = card(c1, "Situação das contas por mês (R$)", "empilhado · clique para filtrar")
    fig_st = go.Figure()
    for sit in sits_stack:
        y = drv[drv["Situação"] == sit].groupby("Ref")["Valor"].sum().reindex(refs_sel, fill_value=0)
        fig_st.add_trace(go.Bar(
            x=x_lab, y=y.values, name=sit, marker_color=cor_sit(sit),
            customdata=[sit] * len(x_lab), legendgroup=sit,
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.4)),
            hovertemplate="%{x}<br>R$ %{y:,.2f}<extra>" + sit + "</extra>"))
    fig_st.update_layout(barmode="stack", bargap=0.35, legend=dict(font=dict(color="#ffffff")))
    grafico_click(ct, layout(fig_st), K_ST)

with c2:
    ct = card(c2, "Inadimplência mês a mês" if mes_a_mes else "Convênios por inadimplência")
    inad = perf[["Inadimplência", "Faturado"]] if not perf.empty else pd.DataFrame()
    if not mes_a_mes and not inad.empty:
        inad = inad[inad["Inadimplência"] > 0].sort_values("Inadimplência", ascending=False)
    if inad.empty:
        ct.markdown(vazio_html("Sem inadimplência no período"), unsafe_allow_html=True)
    else:
        mx = inad["Inadimplência"].max()
        rows = [rot_cols(i, nome) + [abrev(r["Inadimplência"]), barra(div(r["Inadimplência"], mx) * 100, VERMELHO),
                                     pct(div(r["Inadimplência"], r["Faturado"]) * 100)]
                for i, (nome, r) in enumerate(inad.iterrows(), 1)]
        ct.markdown(tabela(HEAD_ROT + ["Inadimplência", "", "% fat."], rows), unsafe_allow_html=True)

with c3:
    ct = card(c3, "Recebimento mês a mês" if mes_a_mes else "Recebimento por convênio")
    if perf.empty:
        ct.markdown(vazio_html("Sem dados no período"), unsafe_allow_html=True)
    else:
        rec = perf.copy()
        rec["_tx"] = [div(a, b) for a, b in zip(rec["Recebido"], rec["Faturado"])]
        if not mes_a_mes:
            rec = rec.sort_values(["_tx", "Faturado"], ascending=False)
        rows = []
        for i, (nome, r) in enumerate(rec.iterrows(), 1):
            tx = div(r["Recebido"], r["Faturado"]) * 100
            rows.append(rot_cols(i, nome) + [abrev(r["Faturado"]), abrev(r["Recebido"]),
                                             barra(tx, cor_taxa(tx)), pct(tx)])
        ct.markdown(tabela(HEAD_ROT + ["Faturado", "Recebido", "", "% Receb."], rows), unsafe_allow_html=True)

# ==============================================================================
# 9. DESEMPENHO POR CONVÊNIO
# ==============================================================================
dica_desemp = "valores em R$ · " + ("convênio(s) selecionado(s)" if mes_a_mes else "período selecionado")
ct = card(st.container(), "Desempenho mês a mês" if mes_a_mes else "Desempenho por convênio", dica_desemp, fixo=False)
if perf.empty:
    ct.markdown(vazio_html("Sem dados no período"), unsafe_allow_html=True)
else:
    pf = perf if mes_a_mes else perf.sort_values("Faturado", ascending=False)
    rows = []
    for i, (nome, r) in enumerate(pf.iterrows(), 1):
        tx, ti = div(r["Recebido"], r["Faturado"]) * 100, div(r["Inadimplência"], r["Faturado"]) * 100
        rows.append(rot_cols(i, nome, True) + [
            num(r["Faturado"]), num(r["Em Produção"]), num(r["Em Faturamento"]),
            f"<span style='color:{VERDE}'>{num(r['Recebido'])}</span>",
            num(r["A receber"]), num(r["Glosas e Recursos"]), num(r["Recursos Negados"]),
            f"<span style='color:{VERMELHO}'>{num(r['Inadimplência'])}</span>",
            pct(ti), f"<span style='color:{cor_taxa(tx)};font-weight:700'>{pct(tx)}</span>"])
    ts = pf.sum()
    total = ([] if mes_a_mes else [""]) + [
        "TOTAL GERAL", num(ts["Faturado"]), num(ts["Em Produção"]), num(ts["Em Faturamento"]), num(ts["Recebido"]),
        num(ts["A receber"]), num(ts["Glosas e Recursos"]), num(ts["Recursos Negados"]), num(ts["Inadimplência"]),
        pct(div(ts["Inadimplência"], ts["Faturado"]) * 100), pct(div(ts["Recebido"], ts["Faturado"]) * 100)]
    ct.markdown(
        tabela(HEAD_ROT + ["Faturado", "Em produção", "Em faturamento", "Recebido", "A receber",
                           "Glosas e recursos", "Recursos negados", "Inadimplência", "% Inadimpl.", "% Receb."],
               rows, total, altura=420),
        unsafe_allow_html=True)

# ==============================================================================
# 10. MATRIZ SITUAÇÃO × MÊS
# ==============================================================================
ct = card(st.container(), "Situação das contas × mês de faturamento", "valores em R$", fixo=False)
if sit_df.empty:
    ct.markdown(vazio_html("Sem dados no período"), unsafe_allow_html=True)
else:
    mat = sit_df.pivot_table(index="Situação", columns="Ref", values="Valor", aggfunc="sum", fill_value=0.0)
    mat = mat.reindex(columns=refs_c, fill_value=0.0)
    mat = mat.loc[sorted(mat.index, key=ordem_sit)]
    rows = [[f"<span class='dot' style='background:{cor_sit(sit)}'></span>{sit}"]
            + [num(mat.loc[sit, m]) for m in refs_c] + [f"<b>{num(mat.loc[sit].sum())}</b>"] for sit in mat.index]
    total = ["TOTAL GERAL"] + [num(mat[m].sum()) for m in refs_c] + [num(mat.values.sum())]
    ct.markdown(tabela(["Situação"] + x_lab_c + ["Total"], rows, total), unsafe_allow_html=True)
