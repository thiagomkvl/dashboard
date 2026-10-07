import streamlit as st

try:
    st.set_page_config(
        page_title="Painel Financeiro Mensal",
        layout="wide",
        page_icon="📊",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import re
import unicodedata
from datetime import datetime
import textwrap

try:
    from database import conectar_sheets
except Exception as _err:
    _erro_import_db = str(_err)

    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {_erro_import_db}")
        return None

# ==============================================================================
# PALETA (mesma de Obras / Faturamento)
# ==============================================================================
AZUL, VERDE, AMBAR, VERMELHO = "#3b82f6", "#10b981", "#f59e0b", "#ef4444"
ROXO, CIANO = "#8b5cf6", "#22d3ee"
TXT, MUTED, BORDA = "#e6ecf5", "#8fa3c4", "#1c2a47"

css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: #0a1020 !important; color: #e6ecf5; }
    [data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .main .block-container { padding: 1.1rem 1.4rem 1rem; max-width: 99%; }
    div[data-testid="stVerticalBlock"] { gap: 1.0rem; }
    [data-testid="stMarkdownContainer"] { color: #e6ecf5; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #0b1326 !important; border-right: 1px solid #1a2744; }
    [data-testid="stWidgetLabel"] p { color: #8fa3c4 !important; font-size: 12px; font-weight: 600; }
    .side-sec { font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #8fa3c4; text-transform: uppercase; margin: 6px 0 -2px; }
    .side-card { background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 10px; padding: 10px 12px; margin-top: 8px; }
    .side-card small { display: block; color: #8fa3c4; font-size: 11px; }
    .side-card b { color: #e6ecf5; font-size: 13px; }

    /* Widgets */
    [data-baseweb="select"] > div, [data-testid="stDateInput"] > div > div {
        background: #101b32 !important; border-color: #1e2d4d !important; color: #e6ecf5 !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #f97316, #ea580c); color: #fff; border: none;
        border-radius: 10px; font-weight: 700;
    }

    /* Cabeçalho */
    .top {
        display: flex; justify-content: space-between; align-items: center; gap: 16px;
        padding-bottom: 12px; margin-bottom: 8px; border-bottom: 1px solid #1a2744;
    }
    .top h1 { margin: 0; font-size: 22px; font-weight: 800; color: #fff; letter-spacing: 0.3px; }
    .top p { margin: 2px 0 0; font-size: 13px; color: #8fa3c4; }
    .pills { display: flex; gap: 10px; flex-wrap: wrap; }
    .pill { background: #0f1a2e; border: 1px solid #1c2a47; border-radius: 10px; padding: 6px 14px; min-width: 120px; }
    .pill small { display: block; font-size: 10px; color: #8fa3c4; }
    .pill b { font-size: 13px; color: #fff; white-space: nowrap; }

    /* KPIs */
    .kpi {
        padding: 12px 14px; border-radius: 12px; min-height: 96px;
        background: linear-gradient(135deg, rgba(59,130,246,0.10), #0f1a2e 70%);
        border: 1px solid rgba(59,130,246,0.22);
    }
    .kpi.green { background: linear-gradient(135deg, rgba(16,185,129,0.10), #0f1a2e 70%); border-color: rgba(16,185,129,0.22); }
    .kpi.cyan { background: linear-gradient(135deg, rgba(34,211,238,0.10), #0f1a2e 70%); border-color: rgba(34,211,238,0.22); }
    .kpi.purple { background: linear-gradient(135deg, rgba(139,92,246,0.10), #0f1a2e 70%); border-color: rgba(139,92,246,0.22); }
    .kpi-t { font-size: 10px; font-weight: 800; letter-spacing: 0.4px; text-transform: uppercase; color: #9db2d3; }
    .kpi-v { font-size: 20px; font-weight: 800; color: #fff; margin: 8px 0 4px; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .kpi-sub { font-size: 11px; color: #8fa3c4; font-weight: 600; }
    .kpi-var { font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 999px; display: inline-flex; margin-right: 6px; }
    .kpi-var.up { background: rgba(16,185,129,0.18); color: #34d399; border: 1px solid rgba(16,185,129,0.35); }
    .kpi-var.down { background: rgba(239,68,68,0.18); color: #f87171; border: 1px solid rgba(239,68,68,0.35); }
    .kpi-var.neutral { background: rgba(143,163,196,0.15); color: #8fa3c4; border: 1px solid rgba(143,163,196,0.3); }

    /* Seções */
    .section-title {
        font-size: 12px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;
        color: #fff; margin: 10px 0 8px; padding-left: 10px; border-left: 3px solid #3b82f6;
        display: flex; align-items: center; gap: 8px;
    }
    .section-title span { font-size: 10px; font-weight: 600; text-transform: none; letter-spacing: 0.2px; color: #8fa3c4; margin-left: auto; }
    .section-title-inline { font-size: 9px; font-weight: 800; color: #8fa3c4; text-transform: uppercase; letter-spacing: 0.45px; margin-bottom: 2px; }

    /* Cards movimento */
    .movement-card {
        padding: 10px 12px; border: 1px solid #1c2a47; border-left: 3px solid #3b82f6;
        border-radius: 10px; background: #0f1a2e; min-height: 56px;
    }
    .movement-card div:last-child { font-variant-numeric: tabular-nums; color: #fff; font-weight: 800; font-size: 14px; }

    /* Tabelas */
    .tabela-container, .tabela-container-scroll {
        overflow: auto; border: 1px solid #1c2a47; border-radius: 12px; background: #0f1a2e; width: 100%;
    }
    .tabela-container-scroll { max-height: 520px; }
    .tabela-container::-webkit-scrollbar, .tabela-container-scroll::-webkit-scrollbar { height: 6px; width: 6px; }
    .tabela-container::-webkit-scrollbar-thumb, .tabela-container-scroll::-webkit-scrollbar-thumb { background: #2a3a5c; border-radius: 6px; }

    .tabela-financeira { width: 100%; border-collapse: collapse; margin: 0; font-size: 11px; color: #dbe6f7; }
    .tabela-financeira th {
        background: #0f1a2e; color: #8fa3c4; font-size: 10px; font-weight: 700; text-align: left;
        padding: 9px 10px; border-bottom: 1px solid #1c2a47; text-transform: uppercase;
        position: sticky; top: 0; z-index: 2; white-space: nowrap;
    }
    .tabela-financeira td {
        padding: 8px 10px; border-bottom: 1px solid #16213a; font-size: 11px; font-weight: 600;
        color: #dbe6f7; white-space: nowrap; font-variant-numeric: tabular-nums;
    }
    .tabela-financeira tbody tr:hover td { background: #13203a; }
    .tabela-financeira .linha-total td {
        background: #0d1730 !important; color: #fff; font-weight: 800;
        border-top: 1px solid #2a3a5c; border-bottom: 1px solid #2a3a5c;
    }
    .tabela-financeira .linha-limite td {
        background: rgba(245,158,11,0.12) !important; color: #fbbf24; font-weight: 700;
        border-top: 1px solid rgba(245,158,11,0.3);
    }
    .tabela-financeira td.valor-destaque { font-weight: 800; color: #fff; }

    [data-testid="stInfo"] { background: #0f1a2e; border: 1px solid #1c2a47; color: #8fa3c4; }

    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        .stApp { background: #fff !important; }
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================
hoje = datetime.now().date()
primeiro_dia_mes = hoje.replace(day=1)

with st.sidebar:
    st.markdown("<div class='side-sec'>Filtros</div>", unsafe_allow_html=True)
    data_selecionada = st.date_input(
        "Selecione o Período:",
        value=(primeiro_dia_mes, hoje),
        min_value=datetime(2020, 1, 1).date(),
        max_value=hoje,
        format="DD/MM/YYYY",
    )
    st.markdown("<div class='side-sec' style='margin-top:14px'>Relatório</div>", unsafe_allow_html=True)
    st.caption("Para PDF de qualidade: orientação Paisagem e sem cabeçalhos/rodapés.")
    components.html(
        """
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }"
        style="width:100%; background:linear-gradient(135deg,#3b82f6,#2563eb); color:white; border:none;
        padding:12px; border-radius:10px; font-family:Inter,sans-serif; font-weight:700; font-size:13px; cursor:pointer;">
        🖨️ Salvar Dashboard (PDF)
        </button>
        """,
        height=55,
    )

if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
    data_inicio_filtro, data_fim_filtro = data_selecionada
else:
    data_inicio_filtro = data_selecionada[0] if isinstance(data_selecionada, tuple) else data_selecionada
    data_fim_filtro = data_inicio_filtro

# ==============================================================================
# FUNÇÕES
# ==============================================================================
def limpa_valor_bruto(valor):
    try:
        if isinstance(valor, pd.Series):
            valor = valor.iloc[0] if not valor.empty else 0.0
        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan", "NaN", "None"]:
            return 0.0
        if isinstance(valor, (int, float)):
            return float(valor)
        v_str = str(valor).strip()
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        v_str = v_str.replace('R$', '').strip()
        if '.' in v_str and ',' in v_str:
            v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
        return float(v_str)
    except Exception:
        return 0.0


def formatar_moeda(valor, exibir_traco_zero=True):
    try:
        val = float(valor)
        if val == 0 and exibir_traco_zero:
            return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "-" if exibir_traco_zero else "R$ 0,00"


def formatar_abreviado(valor):
    try:
        val = float(valor)
        if val == 0:
            return "-"
        if abs(val) >= 1_000_000:
            return f"R$ {val/1_000_000:.1f}M".replace('.', ',')
        if abs(val) >= 1_000:
            return f"R$ {val/1_000:.1f}K".replace('.', ',')
        return f"R$ {val:.0f}"
    except Exception:
        return ""


def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()


def layout_fig(fig, h=220, legenda=True):
    fig.update_layout(
        height=h,
        margin=dict(l=0, r=0, t=28 if legenda else 8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=11, color=MUTED),
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11, color="#fff")),
        hoverlabel=dict(bgcolor="#101b32", font_color=TXT, bordercolor=BORDA),
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDA, tickfont=dict(size=10, color=MUTED))
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.12)", zeroline=False, tickfont=dict(size=10, color=MUTED))
    return fig


# ==============================================================================
# CARGA DE DADOS (mesma lógica)
# ==============================================================================
@st.cache_data(ttl=60, show_spinner="Carregando dados…")
def carregar_dados(data_inicio, data_fim):
    conn = conectar_sheets()
    if conn is None:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim

    try:
        df_saldo_inicial = pd.DataFrame(columns=['Conta Bancária', 'Saldo Inicial', 'Conta Garantida'])
        try:
            df_si = conn.read(worksheet="Saldo_Inicial", ttl=0)
            if not df_si.empty:
                df_si.columns = [str(c).strip() for c in df_si.columns]
                df_si = df_si.loc[:, ~df_si.columns.duplicated()].copy()
                col_si_conta = next((c for c in df_si.columns if 'banco' in c.lower() or 'conta' in c.lower()), df_si.columns[0])
                col_si_valor = next((c for c in df_si.columns if 'saldo' in c.lower() or 'inicial' in c.lower() or 'valor' in c.lower()), df_si.columns[1] if len(df_si.columns) > 1 else df_si.columns[0])
                col_si_garantida = next((c for c in df_si.columns if 'garantida' in c.lower() or 'limite' in c.lower()), None)

                df_si[col_si_valor] = df_si[col_si_valor].apply(limpa_valor_bruto)
                cols_to_keep = [col_si_conta, col_si_valor]
                new_cols = ['Conta Bancária', 'Saldo Inicial']

                if col_si_garantida:
                    df_si[col_si_garantida] = df_si[col_si_garantida].apply(limpa_valor_bruto)
                    cols_to_keep.append(col_si_garantida)
                    new_cols.append('Conta Garantida')

                df_saldo_inicial = df_si[cols_to_keep].copy()
                df_saldo_inicial.columns = new_cols
                if 'Conta Garantida' not in df_saldo_inicial.columns:
                    df_saldo_inicial['Conta Garantida'] = 0.0
                df_saldo_inicial['Conta Bancária'] = df_saldo_inicial['Conta Bancária'].astype(str).str.strip()
        except Exception as e:
            print("Aviso ao ler Saldo_Inicial:", e)

        df_extratos = None
        df_fim_mes = pd.DataFrame()
        entradas_periodo = 0.0
        saidas_periodo = 0.0
        df_process = pd.DataFrame()
        df_graficos = pd.DataFrame(columns=['Data', 'Vl Crédito', 'Vl Débito', 'Movimentação Líquida', 'Saldo Final', 'Saldo Inicial', 'Data_Label', 'Entrada Op', 'Saída Op', 'Delta R$', 'Delta %'])

        try:
            df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
            if not df_ext.empty:
                while len(df_ext.columns) < 12:
                    df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""

                col_banco = df_ext.columns[0]
                col_data = df_ext.columns[1]
                col_deb = df_ext.columns[4]
                col_cred = df_ext.columns[5]
                col_tipo = df_ext.columns[7]
                col_operac = df_ext.columns[10]
                col_subgrupo = df_ext.columns[11]

                df_process['Conta Bancária'] = df_ext[col_banco].astype(str).str.strip()
                df_process['Data'] = pd.to_datetime(df_ext[col_data], dayfirst=True, errors='coerce').dt.normalize()
                df_process['Vl Débito'] = df_ext[col_deb].apply(limpa_valor_bruto)
                df_process['Vl Crédito'] = df_ext[col_cred].apply(limpa_valor_bruto)
                df_process['SubGrupo'] = df_ext[col_subgrupo].astype(str).str.strip()
                df_process['Mov_Total'] = df_process['Vl Crédito'] - df_process['Vl Débito']
                df_process['Vl_Absoluto'] = df_process['Vl Crédito'] + df_process['Vl Débito']

                serie_tipo = df_ext[col_tipo].apply(normalizar_texto)
                df_process['É Transf'] = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')
                df_process['É Emprestimo'] = serie_tipo.str.contains('liberacao de emprestimo')

                serie_operac_k = df_ext[col_operac].apply(normalizar_texto)
                is_operacional = (serie_operac_k == 'operacional')

                df_process['Cred_Op'] = df_process['Vl Crédito'].where(is_operacional, 0.0)
                df_process['Deb_Op'] = df_process['Vl Débito'].where(is_operacional, 0.0)
                df_process['Cred_Tr'] = df_process['Vl Crédito'].where(df_process['É Transf'], 0.0)
                df_process['Deb_Tr'] = df_process['Vl Débito'].where(df_process['É Transf'], 0.0)
                df_process['Cred_Emp'] = df_process['Vl Crédito'].where(df_process['É Emprestimo'], 0.0)
                df_process['Deb_Emp'] = df_process['Vl Débito'].where(df_process['É Emprestimo'], 0.0)

                dt_ini_pd = pd.to_datetime(data_inicio)
                dt_fim_pd = pd.to_datetime(data_fim)

                df_before = df_process[df_process['Data'] < dt_ini_pd].copy()
                if not df_before.empty:
                    df_before_grouped = df_before.groupby('Conta Bancária')['Mov_Total'].sum().reset_index()
                    df_saldo_dinamico = pd.merge(df_saldo_inicial, df_before_grouped, on='Conta Bancária', how='outer').fillna(0)
                    df_saldo_dinamico['Saldo Inicial'] = df_saldo_dinamico['Saldo Inicial'] + df_saldo_dinamico['Mov_Total']
                else:
                    df_saldo_dinamico = df_saldo_inicial.copy()

                df_fim_mes = df_saldo_dinamico[['Conta Bancária', 'Saldo Inicial', 'Conta Garantida']].copy()
                df_period = df_process[(df_process['Data'] >= dt_ini_pd) & (df_process['Data'] <= dt_fim_pd)].copy()
                df_extratos = df_period

                def definir_tipo_aux(nome):
                    n_norm = normalizar_texto(nome)
                    if 'getnet' in n_norm:
                        return 'Limite'
                    return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

                if not df_period.empty:
                    df_period_grouped = df_period.groupby('Conta Bancária').agg({
                        'Cred_Op': 'sum', 'Deb_Op': 'sum',
                        'Cred_Tr': 'sum', 'Deb_Tr': 'sum',
                        'Cred_Emp': 'sum', 'Deb_Emp': 'sum',
                    }).reset_index()
                    df_fim_mes = df_fim_mes.merge(df_period_grouped, on='Conta Bancária', how='outer').fillna(0)
                    df_period_caixa = df_period[df_period['Conta Bancária'].apply(definir_tipo_aux).isin(['Disponível', 'Aplicação'])]
                    entradas_periodo = df_period_caixa['Cred_Op'].sum()
                    saidas_periodo = df_period_caixa['Deb_Op'].sum()
                else:
                    for c in ['Cred_Op', 'Deb_Op', 'Cred_Tr', 'Deb_Tr', 'Cred_Emp', 'Deb_Emp']:
                        df_fim_mes[c] = 0.0

                df_fim_mes['Saldo Inicial'] = df_fim_mes['Saldo Inicial'].fillna(0)
                df_fim_mes['Conta Garantida'] = df_fim_mes['Conta Garantida'].fillna(0)
                df_fim_mes.rename(columns={
                    'Cred_Op': 'Entrada Op', 'Deb_Op': 'Saída Op',
                    'Cred_Tr': 'Entrada Tr', 'Deb_Tr': 'Saída Tr',
                    'Cred_Emp': 'Entrada Emp', 'Deb_Emp': 'Saída Emp',
                }, inplace=True)
        except Exception as e:
            print("Aviso ao ler e processar extratos:", e)

        def definir_tipo(nome):
            n_norm = normalizar_texto(nome)
            if 'getnet' in n_norm:
                return 'Limite'
            return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

        df_fim_mes['Tipo'] = df_fim_mes['Conta Bancária'].apply(definir_tipo)
        df_fim_mes['Saldo Final'] = (
            df_fim_mes['Saldo Inicial']
            + df_fim_mes['Entrada Op'] - df_fim_mes['Saída Op']
            + df_fim_mes['Entrada Tr'] - df_fim_mes['Saída Tr']
            + df_fim_mes['Entrada Emp'] - df_fim_mes['Saída Emp']
        )

        saldo_inicial_caixa = df_fim_mes[df_fim_mes['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()

        if df_extratos is not None and not df_extratos.empty:
            df_ext_caixa = df_extratos[df_extratos['Conta Bancária'].apply(definir_tipo).isin(['Disponível', 'Aplicação'])].copy()
            df_extratos_diario = df_ext_caixa.groupby('Data').agg({
                'Vl Crédito': 'sum', 'Vl Débito': 'sum', 'Cred_Op': 'sum', 'Deb_Op': 'sum',
            }).reset_index()

            df_graficos = df_extratos_diario.sort_values('Data').copy()
            df_graficos['Movimentação Líquida'] = df_graficos['Vl Crédito'] - df_graficos['Vl Débito']
            df_graficos['Entrada Op'] = df_graficos['Cred_Op']
            df_graficos['Saída Op'] = df_graficos['Deb_Op']

            saldos_iniciais, saldos_finais, delta_rs, delta_pct = [], [], [], []
            saldo_atual_iter = saldo_inicial_caixa
            for _, row in df_graficos.iterrows():
                si = saldo_atual_iter
                mov = row['Vl Crédito'] - row['Vl Débito']
                sf = si + mov
                d_rs = sf - saldo_inicial_caixa
                d_pct = ((sf / saldo_inicial_caixa) - 1) * 100 if saldo_inicial_caixa != 0 else 0.0
                saldos_iniciais.append(si)
                saldos_finais.append(sf)
                delta_rs.append(d_rs)
                delta_pct.append(d_pct)
                saldo_atual_iter = sf

            df_graficos['Saldo Inicial'] = saldos_iniciais
            df_graficos['Saldo Final'] = saldos_finais
            df_graficos['Delta R$'] = delta_rs
            df_graficos['Delta %'] = delta_pct
            df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%d/%m')

        df_aplicacoes_nova = pd.DataFrame()
        saldo_aplicado_kpi = 0.0
        try:
            if not df_process.empty:
                serie_sub = df_process['SubGrupo'].apply(normalizar_texto)
                df_process['Aplicações_Val'] = df_process['Vl_Absoluto'].where(serie_sub == 'aplicacao financeira', 0.0)
                df_process['Impostos_Val'] = df_process['Vl_Absoluto'].where(serie_sub == 'impostos sobre aplicacoes', 0.0)
                df_process['Rendimentos_Val'] = df_process['Vl_Absoluto'].where(serie_sub == 'rendimentos de aplicacoes', 0.0)
                df_process['Resgates_Val'] = df_process['Vl_Absoluto'].where(serie_sub == 'resgates de aplicacoes', 0.0)

                df_period_app = df_process[
                    (df_process['Data'] >= pd.to_datetime(data_inicio))
                    & (df_process['Data'] <= pd.to_datetime(data_fim))
                ].copy()
                if not df_period_app.empty:
                    df_app_grouped = df_period_app.groupby('Conta Bancária').agg({
                        'Aplicações_Val': 'sum', 'Impostos_Val': 'sum',
                        'Rendimentos_Val': 'sum', 'Resgates_Val': 'sum',
                    }).reset_index()
                else:
                    df_app_grouped = pd.DataFrame(columns=['Conta Bancária', 'Aplicações_Val', 'Impostos_Val', 'Rendimentos_Val', 'Resgates_Val'])

                df_app_full = df_fim_mes[['Conta Bancária', 'Tipo', 'Saldo Inicial', 'Saldo Final']].merge(
                    df_app_grouped, on='Conta Bancária', how='left'
                ).fillna(0)

                def check_nome_app(nome):
                    n_norm = normalizar_texto(nome)
                    return 'aplicacao' in n_norm or 'investimento' in n_norm

                mask_is_app = df_app_full['Conta Bancária'].apply(check_nome_app)
                mask_has_movimentacao = (
                    (df_app_full['Aplicações_Val'] != 0)
                    | (df_app_full['Impostos_Val'] != 0)
                    | (df_app_full['Rendimentos_Val'] != 0)
                    | (df_app_full['Resgates_Val'] != 0)
                    | (round(df_app_full['Saldo Inicial'], 2) != round(df_app_full['Saldo Final'], 2))
                )
                df_aplicacoes_nova = df_app_full[mask_is_app & mask_has_movimentacao].copy()
                df_aplicacoes_nova = df_aplicacoes_nova.rename(columns={
                    'Conta Bancária': 'banco', 'Saldo Inicial': 'inicial',
                    'Aplicações_Val': 'aplicaç', 'Impostos_Val': 'imposto',
                    'Rendimentos_Val': 'rendimento', 'Resgates_Val': 'resgate', 'Saldo Final': 'atual',
                })
                saldo_aplicado_kpi = df_app_full[mask_is_app]['Saldo Final'].sum()
        except Exception as e:
            print("Erro ao processar Aplicações do Extrato:", e)

        return df_fim_mes, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, 'Conta Bancária', entradas_periodo, saidas_periodo, data_inicio, data_fim
    except Exception as e:
        st.error(f"Erro fatal ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim


df_consolidado, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, col_conta, entradas_operacionais, saidas_operacionais, data_ini_painel, data_fim_painel = carregar_dados(data_inicio_filtro, data_fim_filtro)
if not col_conta:
    col_conta = 'Conta Bancária'

if df_consolidado.empty:
    st.warning("⚠️ Os dados não foram carregados ou a planilha está vazia.")
    st.stop()

# ==============================================================================
# KPIs
# ==============================================================================
saldo_inicial_periodo = df_consolidado[df_consolidado['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()
saldo_aplicado = saldo_aplicado_kpi
saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()
saldo_total = saldo_disponivel + saldo_aplicado
saldo_inicial_corrente = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Inicial'].sum()
saldo_inicial_aplicado = df_consolidado[df_consolidado['Tipo'] == 'Aplicação']['Saldo Inicial'].sum()


def calc_var(final, inicial):
    if inicial == 0 and final == 0:
        return 0.0
    if inicial == 0:
        return 100.0 if final > 0 else -100.0
    return ((final / inicial) - 1) * 100


var_total_pct = calc_var(saldo_total, saldo_inicial_periodo)
var_aplicado_pct = calc_var(saldo_aplicado, saldo_inicial_aplicado)
entradas_mes = entradas_operacionais
saidas_mes = saidas_operacionais
resultado_liquido_mes = entradas_mes - saidas_mes

periodo_str = f"{data_ini_painel.strftime('%d/%m/%Y')} – {data_fim_painel.strftime('%d/%m/%Y')}"
dt_ini_short = data_ini_painel.strftime('%d/%m')
dt_fim_short = data_fim_painel.strftime('%d/%m')

# ==============================================================================
# GRÁFICOS
# ==============================================================================
fig_donut = go.Figure(go.Pie(
    values=[saldo_aplicado, saldo_disponivel],
    labels=['Saldo Aplicado', 'Conta Corrente'],
    hole=0.64, textinfo='none',
    marker=dict(colors=[CIANO, AZUL], line=dict(color="#0f1a2e", width=2)),
    hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
))
fig_donut.update_layout(annotations=[dict(
    text=f"<b>{formatar_abreviado(saldo_total)}</b><br><span style='font-size:10px;color:#8fa3c4'>Saldo total</span>",
    x=0.5, y=0.5, font_size=13, font_color="#fff", showarrow=False,
)])
layout_fig(fig_donut, 210)

fig_combinado = go.Figure()
fig_combinado.add_trace(go.Bar(
    x=df_graficos['Data_Label'],
    y=df_graficos['Saldo Inicial'],
    name='Saldo diário',
    marker_color=AZUL,
    text=[formatar_abreviado(v) for v in df_graficos['Saldo Inicial']],
    textposition='outside',
    textfont=dict(size=10, color="#e6ecf5"),
    opacity=0.95,
    width=0.45,
))
layout_fig(fig_combinado, 150, False)
fig_combinado.update_yaxes(showticklabels=False, showgrid=False)

# ==============================================================================
# CABEÇALHO + KPIs
# ==============================================================================
st.markdown(
    f"""
    <div class='top'>
        <div>
            <h1>PAINEL FINANCEIRO MENSAL</h1>
            <p>Controle consolidado de bancos</p>
        </div>
        <div class='pills'>
            <div class='pill'><small>Período</small><b>{periodo_str}</b></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


def get_var_html(pct):
    if pct > 0:
        return f"<span class='kpi-var up'>↗ +{pct:.1f}%</span>"
    if pct < 0:
        return f"<span class='kpi-var down'>↘ {pct:.1f}%</span>"
    return "<span class='kpi-var neutral'>→ 0.0%</span>"


kpi_row = st.columns(4)
kp_data = [
    (kpi_row[0], "Saldo total atual", formatar_moeda(saldo_total, False), "kpi", get_var_html(var_total_pct)),
    (kpi_row[1], "Saldo conta corrente", formatar_moeda(saldo_disponivel, False), "kpi green", ""),
    (kpi_row[2], "Saldo aplicado", formatar_moeda(saldo_aplicado, False), "kpi cyan", get_var_html(var_aplicado_pct)),
    (kpi_row[3], "Saldo inicial período", formatar_moeda(saldo_inicial_periodo, False), "kpi purple", "<span class='kpi-var neutral'>→ Ref.</span>"),
]
for col, title, val, cls, var_html in kp_data:
    col.markdown(
        f"<div class='{cls}'><div class='kpi-t'>{var_html}{title}</div>"
        f"<div class='kpi-v'>{val}</div></div>",
        unsafe_allow_html=True,
    )

c1, c2, c3 = st.columns([0.85, 1.25, 1.6], gap="small")

with c1:
    st.markdown("<div class='section-title'>Distribuição do caixa</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(
        f"<div class='section-title'>Movimentação operacional <span>REF: {periodo_str}</span></div>",
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    m1.markdown(
        f"<div class='movement-card'><div class='section-title-inline' style='color:{VERDE}'>Entradas</div>"
        f"<div>{formatar_moeda(entradas_mes, False)}</div></div>",
        unsafe_allow_html=True,
    )
    m2.markdown(
        f"<div class='movement-card'><div class='section-title-inline' style='color:{VERMELHO}'>Saídas</div>"
        f"<div>{formatar_moeda(saidas_mes, False)}</div></div>",
        unsafe_allow_html=True,
    )
    cor_res = VERDE if resultado_liquido_mes >= 0 else VERMELHO
    m3.markdown(
        f"<div class='movement-card'><div class='section-title-inline' style='color:{cor_res}'>Resultado líquido</div>"
        f"<div style='color:{cor_res}'>{formatar_moeda(resultado_liquido_mes, False)}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='section-title' style='margin-top:10px'>Evolução diária do saldo total</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown(
        f"<div class='section-title'>Resumo aplicações <span>REF: {periodo_str}</span></div>",
        unsafe_allow_html=True,
    )
    tabela_app = (
        "<div class='tabela-container'><table class='tabela-financeira'><thead><tr>"
        f"<th>Banco</th><th>Saldo inicial {dt_ini_short}</th><th>Aplicações</th>"
        f"<th>Impostos</th><th>Rendimentos</th><th>Resgates</th><th>Saldo atual {dt_fim_short}</th>"
        "</tr></thead><tbody>"
    )
    tot_ini = tot_app = tot_imp = tot_ren = tot_res = tot_atu = 0.0
    if df_aplicacoes_nova.empty:
        tabela_app += "<tr><td colspan='7' style='text-align:center;color:#8fa3c4'>Nenhuma aplicação no período</td></tr>"
    else:
        for _, row in df_aplicacoes_nova.sort_values(by='atual', ascending=False).iterrows():
            v_ini, v_app = row.get('inicial', 0), row.get('aplicaç', 0)
            v_imp, v_ren = row.get('imposto', 0), row.get('rendimento', 0)
            v_res, v_atu = row.get('resgate', 0), row.get('atual', 0)
            tot_ini += v_ini; tot_app += v_app; tot_imp += v_imp
            tot_ren += v_ren; tot_res += v_res; tot_atu += v_atu
            tabela_app += (
                f"<tr><td><b>{str(row.get('banco','')).title()}</b></td>"
                f"<td>{formatar_moeda(v_ini)}</td>"
                f"<td style='color:{AZUL}'>{formatar_moeda(v_app)}</td>"
                f"<td style='color:{VERMELHO}'>{formatar_moeda(v_imp)}</td>"
                f"<td style='color:{VERDE}'>{formatar_moeda(v_ren)}</td>"
                f"<td style='color:{VERMELHO}'>{formatar_moeda(v_res)}</td>"
                f"<td class='valor-destaque'>{formatar_moeda(v_atu)}</td></tr>"
            )
        tabela_app += (
            f"<tr class='linha-total'><td><b>TOTAL</b></td>"
            f"<td>{formatar_moeda(tot_ini)}</td><td>{formatar_moeda(tot_app)}</td>"
            f"<td>{formatar_moeda(tot_imp)}</td><td>{formatar_moeda(tot_ren)}</td>"
            f"<td>{formatar_moeda(tot_res)}</td><td class='valor-destaque'>{formatar_moeda(tot_atu)}</td></tr>"
        )
    tabela_app += "</tbody></table></div>"
    st.markdown(tabela_app, unsafe_allow_html=True)

# ==============================================================================
# TABELAS INFERIORES
# ==============================================================================
col_bancos, col_diario = st.columns([1.75, 1.0], gap="small")

with col_bancos:
    st.markdown("<div class='section-title'>Saldo de todos os bancos</div>", unsafe_allow_html=True)
    df_padrao = df_consolidado[df_consolidado['Tipo'] != 'Limite'].copy()
    df_limite = df_consolidado[df_consolidado['Tipo'] == 'Limite'].copy()
    df_padrao['Ordem'] = df_padrao['Tipo'].map({'Disponível': 1, 'Aplicação': 2}).fillna(3)
    df_padrao = df_padrao.sort_values(by=['Ordem', 'Saldo Final'], ascending=[True, False]).reset_index(drop=True)

    tb = (
        "<div class='tabela-container'><table class='tabela-financeira'><thead><tr>"
        f"<th>#</th><th>Conta bancária</th><th>Tipo</th>"
        f"<th>Saldo inicial {dt_ini_short}</th><th>Entrada (op.)</th><th>Saída (op.)</th>"
        f"<th>Entrada (int.)</th><th>Saída (int.)</th><th>Saldo atual {dt_fim_short}</th>"
        "</tr></thead><tbody>"
    )
    tot_banco_ini = tot_banco_ent_op = tot_banco_sai_op = tot_banco_ent_tr = tot_banco_sai_tr = tot_banco_atu = 0.0
    idx_count = 1
    for _, row in df_padrao.iterrows():
        si = row.get('Saldo Inicial', 0)
        e_op = row.get('Entrada Op', 0)
        s_op = row.get('Saída Op', 0)
        e_tr = row.get('Entrada Tr', 0) + row.get('Entrada Emp', 0)
        s_tr = row.get('Saída Tr', 0) + row.get('Saída Emp', 0)
        sf = row.get('Saldo Final', 0)
        tot_banco_ini += si; tot_banco_ent_op += e_op; tot_banco_sai_op += s_op
        tot_banco_ent_tr += e_tr; tot_banco_sai_tr += s_tr; tot_banco_atu += sf
        tb += (
            f"<tr><td><span style='color:#6b7fa3'>{idx_count}</span></td>"
            f"<td><b>{str(row['Conta Bancária']).title()}</b></td>"
            f"<td>{str(row['Tipo']).capitalize()}</td>"
            f"<td>{formatar_moeda(si)}</td>"
            f"<td style='color:{AZUL}'>{formatar_moeda(e_op)}</td>"
            f"<td style='color:{VERMELHO}'>{formatar_moeda(s_op)}</td>"
            f"<td>{formatar_moeda(e_tr)}</td><td>{formatar_moeda(s_tr)}</td>"
            f"<td class='valor-destaque'>{formatar_moeda(sf)}</td></tr>"
        )
        idx_count += 1

    tb += (
        f"<tr class='linha-total'><td colspan='3'><b>TOTAL</b></td>"
        f"<td>{formatar_moeda(tot_banco_ini)}</td>"
        f"<td>{formatar_moeda(tot_banco_ent_op)}</td>"
        f"<td>{formatar_moeda(tot_banco_sai_op)}</td>"
        f"<td>-</td><td>-</td>"
        f"<td class='valor-destaque'>{formatar_moeda(tot_banco_atu)}</td></tr>"
    )
    if not df_limite.empty:
        for _, row_lim in df_limite.iterrows():
            garantida_val = row_lim.get('Conta Garantida', 0) or row_lim.get('Saldo Inicial', 0)
            tb += (
                f"<tr class='linha-limite'><td>{idx_count}</td>"
                f"<td><b>{str(row_lim['Conta Bancária']).title()}</b></td>"
                f"<td>Limite</td><td>{formatar_moeda(garantida_val)}</td>"
                f"<td>-</td><td>-</td><td>-</td><td>-</td>"
                f"<td class='valor-destaque'>{formatar_moeda(garantida_val)}</td></tr>"
            )
            idx_count += 1
    tb += "</tbody></table></div>"
    st.markdown(tb, unsafe_allow_html=True)

with col_diario:
    st.markdown("<div class='section-title'>Saldo diário consolidado</div>", unsafe_allow_html=True)
    tb_d = (
        "<div class='tabela-container-scroll'><table class='tabela-financeira'><thead><tr>"
        "<th>Data</th><th>Saldo inic.</th><th>Entradas</th><th>Saídas</th><th>Saldo final</th><th>Delta</th>"
        "</tr></thead><tbody>"
    )
    if df_graficos.empty:
        tb_d += "<tr><td colspan='6' style='text-align:center;color:#8fa3c4'>Sem movimentações no período</td></tr>"
    else:
        for _, row_d in df_graficos.sort_values(by='Data', ascending=False).iterrows():
            delta = row_d.get('Delta R$', 0)
            cor_delta = VERDE if delta >= 0 else VERMELHO
            sinal = "+" if delta > 0 else ""
            tb_d += (
                f"<tr><td><b>{row_d.get('Data_Label','')}</b></td>"
                f"<td>{formatar_moeda(row_d.get('Saldo Inicial', 0), False)}</td>"
                f"<td style='color:{VERDE}'>{formatar_moeda(row_d.get('Entrada Op', 0), False)}</td>"
                f"<td style='color:{VERMELHO}'>{formatar_moeda(row_d.get('Saída Op', 0), False)}</td>"
                f"<td class='valor-destaque'>{formatar_moeda(row_d.get('Saldo Final', 0), False)}</td>"
                f"<td style='color:{cor_delta};font-weight:800'>{sinal}{formatar_moeda(delta, False)}</td></tr>"
            )
    tb_d += "</tbody></table></div>"
    st.markdown(tb_d, unsafe_allow_html=True)
