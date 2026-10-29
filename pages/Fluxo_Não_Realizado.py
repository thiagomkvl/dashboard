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

ABA_VENCIDOS_2026 = "Vencidos_Aberto_2026"
ABA_VENCIDOS_2025 = "Vencidos_Aberto_2025"
ABA_INADIMPLENCIA = "Base_Inadinplência"
ABA_INADIMPLENCIA_ALT = "Base_Inadimplência"
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
    """Lê o de-para oficial da aba Classificacao_FCx.

    Mantém mapas separados para Conta Contábil (fornecedores) e Conta
    Financeira (impostos), evitando que nomes iguais em colunas diferentes
    sobrescrevam a classificação correta.
    """
    df = read_tab(ABA_CLASSIF)
    maps = {"contabil": {}, "financeira": {}, "geral": {}}
    if df.empty:
        return maps

    cls_col = next((c for c in df.columns if "classific" in key(c) and "fluxo" not in key(c)), None)
    flow_col = next((c for c in df.columns if "fluxo" in key(c)), None)
    if cls_col is None:
        cls_col = df.columns[1] if len(df.columns) > 1 else None
    if flow_col is None:
        flow_col = df.columns[2] if len(df.columns) > 2 else None
    if cls_col is None:
        return maps

    account_cols = {
        "contabil": next((c for c in df.columns if "conta contabil" in key(c)), None),
        "financeira": next((c for c in df.columns if "conta financeira" in key(c)), None),
    }
    general_cols = [c for c in df.columns if any(token in key(c) for token in
                    ("descricao", "categoria", "fornecedor"))]
    if not any(account_cols.values()) and not general_cols:
        general_cols = [df.columns[0]]

    for _, r in df.iterrows():
        classificacao = str(r.get(cls_col, "") or "").strip()
        if not classificacao or classificacao.lower() == "nan":
            continue
        f = key(r.get(flow_col, "")) if flow_col else ""
        fluxo = FLUXO_INV if "invest" in f else FLUXO_FIN if "financ" in f else FLUXO_OP
        resultado = (classificacao, fluxo)
        for tipo, col in account_cols.items():
            if col is not None:
                valor = key(r.get(col, ""))
                if valor and valor not in {"nan", "none", "-"}:
                    maps[tipo][valor] = resultado
        for col in general_cols:
            valor = key(r.get(col, ""))
            if valor and valor not in {"nan", "none", "-"}:
                maps["geral"][valor] = resultado
    return maps


def classify(value, mapping, account_type="contabil", strict_account=False):
    """Classifica pela chave correta; impostos não usam fallback genérico."""
    k = key(value)
    if isinstance(mapping, dict) and any(isinstance(v, dict) for v in mapping.values()):
        primary = mapping.get(account_type, {})
        if k in primary:
            return primary[k]
        matches = [(len(mk), val) for mk, val in primary.items()
                   if len(mk) >= 3 and (mk in k or k in mk)]
        if matches:
            return sorted(matches, key=lambda x: x[0], reverse=True)[0][1]
        if strict_account:
            return ("Não classificado", FLUXO_OP)
        general = mapping.get("geral", {})
        if k in general:
            return general[k]
        matches = [(len(mk), val) for mk, val in general.items()
                   if len(mk) >= 4 and (mk in k or k in mk)]
        if matches:
            return sorted(matches, key=lambda x: x[0], reverse=True)[0][1]
        return ("Não classificado", FLUXO_OP)
    if k in mapping:
        return mapping[k]
    matches = [(len(mk), val) for mk, val in mapping.items()
               if len(mk) >= 6 and (mk in k or k in mk)]
    return sorted(matches, key=lambda x: x[0], reverse=True)[0][1] if matches else ("Não classificado", FLUXO_OP)

def locate_header(raw, required):
    df = raw.copy()
    if all(get_col(df, c) for c in required): return df
    for i in range(min(20, len(df))):
        candidate = df.iloc[i:].copy()
        candidate.columns = list(raw.iloc[i])
        if all(get_col(candidate, c) for c in required): return candidate.iloc[1:].reset_index(drop=True)
    return df

def parse_month_header(v, default_year):
    """Converte os cabeçalhos mensais das tabelas dinâmicas em datas de referência."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    t = key(v)
    months = {"jan":1,"janeiro":1,"fev":2,"fevereiro":2,"mar":3,"marco":3,"abr":4,"abril":4,
              "mai":5,"maio":5,"jun":6,"junho":6,"jul":7,"julho":7,"ago":8,"agosto":8,
              "set":9,"setembro":9,"out":10,"outubro":10,"nov":11,"novembro":11,"dez":12,"dezembro":12}
    m = re.match(r"^([a-z]{3,9})\s*([0-9]{2,4})?$", t)
    if m and m.group(1)[:3] in months:
        year = default_year
        if m.group(2):
            year = int(m.group(2)); year += 2000 if year < 100 else 0
        return pd.Timestamp(year, months[m.group(1)[:3]], 1)
    return None

def parse_pivot_matrix(raw, default_year, kind, mapping, tab_name):
    """Lê tabelas dinâmicas empilhadas de fornecedores e impostos.

    Cada bloco possui seu próprio cabeçalho mensal. Os rótulos da primeira
    coluna são usados como Conta Contábil no bloco de fornecedores e Conta
    Financeira no bloco de impostos. A leitura não depende de a classificação
    existir: movimentos sem correspondência permanecem como Não classificado.
    """
    out = []
    if raw is None or raw.empty:
        return pd.DataFrame(), [f"A aba {tab_name} está vazia."]

    grid = [list(raw.columns)] + raw.astype(object).where(pd.notna(raw), None).values.tolist()
    ncols = max(len(r) for r in grid)
    grid = [r + [None] * (ncols - len(r)) for r in grid]
    active_map = {}
    active_year = default_year
    section = "fornecedores"
    headers_found = 0
    tax_rows_found = 0
    tax_unclassified = set()

    for row in grid:
        row_text = " ".join(str(x) for x in row if x is not None).strip()
        row_key = key(row_text)
        years = re.findall(r"\b(20\d{2})\b", row_text)
        # Identifica o bloco pelo título da tabela dinâmica.
        if "posicao impostos vencidos" in row_key or "impostos vencidos" in row_key:
            section = "impostos"
        elif "posicao fornecedores vencidos" in row_key or "fornecedores vencidos" in row_key:
            section = "fornecedores"
        if years and not any(parse_month_header(x, int(years[-1])) for x in row):
            active_year = int(years[-1])

        month_map = {}
        for j in range(1, ncols):
            ref = parse_month_header(row[j], active_year)
            if ref is not None:
                month_map[j] = ref
        if len(month_map) >= 2:
            active_map = month_map
            headers_found += 1
            # Se o cabeçalho identifica Conta Financeira, trata esse bloco como impostos.
            first_cell = key(row[0]) if row else ""
            if "financeira" in first_cell:
                section = "impostos"
            elif "contabil" in first_cell:
                section = "fornecedores"
            continue
        if not active_map:
            continue

        label = row[0] if row else None
        label_s = str(label).strip() if label is not None else ""
        label_key = key(label_s)
        if not label_key:
            continue
        if label_key.startswith("total") or label_key in {
            "conta contabil", "conta financeira", "convenio conta", "convenio",
            "mes faturamento mes", "inadimplencia contas faturadas",
            "posicao fornecedores vencidos", "posicao impostos vencidos",
        }:
            continue
        if any(x in label_key for x in ("inadimplencia contas faturadas", "posicao fornecedores vencidos", "posicao impostos vencidos")):
            continue

        classification, flow = classify(
            label_s,
            mapping,
            "financeira" if section == "impostos" else "contabil",
            strict_account=(section == "impostos"),
        )
        found_in_row = False
        for j, ref in active_map.items():
            val = money(row[j] if j < len(row) else 0)
            if abs(val) <= 0.005:
                continue
            found_in_row = True
            out.append({
                "Mês": ref, "Valor": abs(val), "Classificação": classification,
                "Fluxo": flow, "Tipo": kind, "Conta origem": label_s,
                "Origem/Detalhe": f"{tab_name} — {'Impostos / Conta Financeira' if section == 'impostos' else 'Fornecedores / Conta Contábil'} — {label_s}",
                "Grupo origem": section,
            })
        if found_in_row and section == "impostos":
            tax_rows_found += 1
            if classification == "Não classificado":
                tax_unclassified.add(label_s)

    if not out:
        msg = f"Não identifiquei linhas mensais nas tabelas dinâmicas da aba {tab_name}. Confira os cabeçalhos mensais e os valores."
        return pd.DataFrame(), [msg]
    warnings = []
    if headers_found == 0:
        warnings.append(f"Não encontrei cabeçalhos mensais em {tab_name}.")
    if "2025" in tab_name and tax_rows_found == 0:
        warnings.append(f"A tabela de impostos de {tab_name} não foi identificada; confira se o bloco 'Posição Impostos Vencidos 2025' está na mesma aba e se os meses estão em colunas separadas.")
    if tax_unclassified:
        warnings.append(
            f"Impostos sem correspondência na Conta Financeira de Classificacao_FCx ({tab_name}): "
            + ", ".join(sorted(tax_unclassified))
        )
    return pd.DataFrame(out), warnings

def load_outflows(mapping):
    partes, avisos = [], []
    for tab, year in [(ABA_VENCIDOS_2026, 2026), (ABA_VENCIDOS_2025, 2025)]:
        try:
            raw = read_tab(tab)
            dados, erros = parse_pivot_matrix(raw, year, "Saída pendente", mapping, tab)
            partes.append(dados) if not dados.empty else None
            avisos.extend(erros)
        except Exception as e:
            avisos.append(f"Não foi possível ler {tab}: {e}")
    if not partes:
        return pd.DataFrame(), avisos or ["Não foram encontrados dados de pagamentos pendentes."]
    return pd.concat(partes, ignore_index=True), avisos

def load_receivables(mapping):
    avisos = []
    raw = pd.DataFrame()
    for tab in (ABA_INADIMPLENCIA, ABA_INADIMPLENCIA_ALT):
        try:
            raw = read_tab(tab)
            if not raw.empty:
                break
        except Exception as e:
            avisos.append(f"Não foi possível ler {tab}: {e}")
    if raw.empty:
        return pd.DataFrame(), avisos + [f"Não encontrei a aba {ABA_INADIMPLENCIA} (ou {ABA_INADIMPLENCIA_ALT})."]
    dados, erros = parse_pivot_matrix(raw, 2026, "Entrada pendente", mapping, ABA_INADIMPLENCIA)
    if not dados.empty:
        # O demonstrativo de inadimplência é classificado como Inadimplência,
        # preservando o rótulo de convênio/conta da tabela dinâmica como detalhe.
        dados["Classificação"] = "Inadimplência"
        dados["Fluxo"] = "Recebimentos pendentes"
    return dados, avisos + erros

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
    try: entradas, e = load_receivables(mapping); errors += e
    except Exception as e: entradas=pd.DataFrame(); errors.append(f"Entradas pendentes: {e}")
for e in errors: st.warning(e)
if saidas.empty and entradas.empty:
    st.info("Não há dados disponíveis para exibir. Confira a conexão e os nomes das colunas nas abas de origem.")
    st.stop()

frames=[]
if not saidas.empty:
    s=saidas[["Mês","Valor","Classificação","Fluxo","Tipo"]].copy(); s["Origem/Detalhe"]=saidas.get("Origem/Detalhe", saidas.get("Conta origem", "Pagamentos pendentes")); frames.append(s)
if not entradas.empty:
    r=entradas[["Mês","Valor","Classificação","Fluxo","Tipo"]].copy(); r["Origem/Detalhe"]=entradas.get("Origem/Detalhe", entradas.get("Conta origem", "Recebimentos pendentes")); frames.append(r)
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

