import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import difflib
import unicodedata
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Painel Financeiro Mensal",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CUSTOM CSS — VISUAL CORPORATIVO
# ==============================================================================
st.markdown("""
<style>
    :root {
        --bg: #f4f6f8;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --border: #dfe4ea;
        --border-strong: #cbd3dc;
        --text: #17212b;
        --text-secondary: #44515f;
        --muted: #6b7785;
        --primary: #234a78;
        --primary-dark: #193754;
        --primary-soft: #eef4fa;
        --success: #157a5b;
        --success-soft: #eef8f4;
        --danger: #b74242;
        --danger-soft: #fdf1f1;
        --warning: #996b10;
        --warning-soft: #fcf7ea;
        --info: #2f657a;
        --shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
    }

    html, body, [class*="css"] {
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
    }

    .main {
        background: var(--bg);
    }

    .main .block-container {
        padding-top: 0.65rem;
        padding-bottom: 0.65rem;
        max-width: 98%;
    }

    div[data-testid="stVerticalBlock"] > div {
        gap: 0.28rem !important;
    }

    .stPlotlyChart {
        background: transparent !important;
    }

    .js-plotly-plot,
    .plot-container {
        margin: 0 auto;
    }

    /* =========================================================
       SIDEBAR
       ========================================================= */

    [data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] h3 {
        color: var(--text);
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 0.2px;
    }

    [data-testid="stSidebar"] .stInfo {
        border-radius: 5px;
        border: 1px solid #dbe5ef;
        background: #f3f7fb;
    }

    /* =========================================================
       CABEÇALHO
       ========================================================= */

    .dashboard-header {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        min-height: 64px;
        padding: 5px 0 11px;
        margin-bottom: 12px;
        border-bottom: 1px solid var(--border-strong);
    }

    .header-period {
        min-width: 210px;
        text-align: left;
    }

    .header-period .date {
        font-size: 16px;
        font-weight: 800;
        color: var(--text);
        letter-spacing: -0.15px;
    }

    .header-period .label {
        margin-top: 3px;
        font-size: 9px;
        font-weight: 700;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.75px;
    }

    .header-center {
        text-align: center;
        padding: 0 25px;
    }

    .header-center h1 {
        margin: 0;
        color: var(--primary-dark);
        font-size: 20px;
        line-height: 1.2;
        font-weight: 850;
        letter-spacing: 0.4px;
    }

    .header-center p {
        margin: 4px 0 0;
        color: var(--muted);
        font-size: 9px;
        font-weight: 600;
        letter-spacing: 0.45px;
        text-transform: uppercase;
    }

    .update-wrapper {
        display: flex;
        justify-content: flex-end;
    }

    .update-badge {
        min-width: 122px;
        padding: 6px 11px;
        text-align: left;
        border-left: 3px solid var(--primary);
        background: #f8fafc;
    }

    .update-badge span {
        display: block;
        font-size: 8px;
        font-weight: 800;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.65px;
    }

    .update-badge b {
        display: block;
        margin-top: 2px;
        font-size: 11px;
        font-weight: 800;
        color: var(--text);
    }

    /* =========================================================
       KPI CARDS
       ========================================================= */

    .kpi-card {
        position: relative;
        min-height: 92px;
        padding: 13px 16px 12px 17px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 4px;
        box-shadow: var(--shadow);
        overflow: hidden;
    }

    .kpi-card::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: var(--primary);
    }

    .kpi-card.disponivel::before {
        background: var(--success);
    }

    .kpi-card.aplicacoes::before {
        background: #5d66a8;
    }

    .kpi-card.limites::before {
        background: var(--warning);
    }

    .kpi-title {
        font-size: 9px;
        line-height: 1.2;
        font-weight: 800;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.72px;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-size: 23px;
        line-height: 1.15;
        font-weight: 850;
        color: var(--text);
        letter-spacing: -0.4px;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }

    .kpi-foot {
        margin-top: 6px;
        font-size: 8px;
        color: #7a8591;
        text-transform: uppercase;
        letter-spacing: 0.45px;
    }

    /* =========================================================
       SEÇÕES
       ========================================================= */

    .section-title {
        display: flex;
        align-items: center;
        min-height: 27px;
        margin-bottom: 5px;
        padding: 0 0 6px 0;
        border-bottom: 1px solid var(--border-strong);
        color: var(--text);
        font-size: 10px;
        font-weight: 850;
        text-transform: uppercase;
        letter-spacing: 0.75px;
    }

    .section-title::before {
        content: "";
        width: 3px;
        height: 13px;
        margin-right: 7px;
        background: var(--primary);
        border-radius: 1px;
    }

    .section-ref {
        margin-left: auto;
        color: var(--muted);
        font-size: 8px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }

    .section-title-inline {
        font-size: 8px;
        font-weight: 800;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.55px;
    }

    /* =========================================================
       CARDS DE MOVIMENTAÇÃO
       ========================================================= */

    .movement-card {
        min-height: 64px;
        padding: 9px 11px;
        border: 1px solid var(--border);
        border-radius: 4px;
        background: var(--surface);
    }

    .movement-card .movement-label {
        font-size: 8px;
        font-weight: 800;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .movement-card .movement-value {
        margin-top: 4px;
        font-size: 17px;
        line-height: 1.1;
        font-weight: 850;
        color: var(--text);
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }

    /* =========================================================
       TABELAS
       ========================================================= */

    .tabela-container {
        overflow-x: auto;
        border: 1px solid var(--border-strong);
        border-radius: 4px;
        background: var(--surface);
        box-shadow: var(--shadow);
        font-size: 11px;
        width: 100%;
        margin-bottom: 7px;
    }

    .tabela-financeira {
        width: 100%;
        border-collapse: collapse;
    }

    .tabela-financeira th {
        background: #edf1f5;
        color: #46525f;
        font-size: 8px;
        font-weight: 850;
        text-align: left;
        padding: 8px 8px;
        border-bottom: 1px solid var(--border-strong);
        text-transform: uppercase;
        letter-spacing: 0.4px;
        white-space: nowrap;
    }

    .tabela-financeira td {
        padding: 7px 8px;
        border-bottom: 1px solid #edf0f3;
        font-size: 11px;
        font-weight: 600;
        color: #2d3742;
        white-space: nowrap;
        vertical-align: middle;
        font-variant-numeric: tabular-nums;
    }

    .tabela-financeira tbody tr:last-child td {
        border-bottom: 0;
    }

    .tabela-financeira tbody tr:hover td {
        background: #f8fafc;
    }

    .tabela-financeira th.valores,
    .tabela-financeira td.valores {
        text-align: right !important;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }

    .tabela-financeira th.centro,
    .tabela-financeira td.centro {
        text-align: center !important;
    }

    .tabela-financeira td.valor-destaque {
        font-size: 12px !important;
        font-weight: 850;
        color: #17212b;
    }

    .tabela-financeira .linha-total {
        background: #eef2f6;
    }

    .tabela-financeira .linha-total td {
        color: #17212b;
        font-weight: 850;
        border-top: 2px solid var(--border-strong);
    }

    .tabela-financeira .linha-limite td {
        background: #fcf8ef;
        border-top: 1px solid #e5cf98;
    }

    .tabela-financeira .linha-limite td:first-child {
        border-left: 3px solid #bd8a22;
    }

    .tabela-financeira .linha-limite td:last-child {
        color: var(--warning);
        font-weight: 850;
    }

    /* =========================================================
       GRÁFICO
       ========================================================= */

    .chart-container {
        padding: 4px 5px 0;
        border: 1px solid var(--border);
        border-radius: 4px;
        background: var(--surface);
    }

    /* =========================================================
       RODAPÉ
       ========================================================= */

    .dashboard-footer {
        margin-top: 9px;
        padding-top: 7px;
        border-top: 1px solid var(--border-strong);
        font-size: 8px;
        color: var(--muted);
        text-align: right;
        letter-spacing: 0.15px;
    }

    hr {
        border: 0 !important;
        border-top: 1px solid var(--border-strong) !important;
        margin: 12px 0 !important;
    }

    /* =========================================================
       IMPRESSÃO
       ========================================================= */

    @media print {

        @page {
            size: landscape;
            margin: 8mm;
        }

        [data-testid="stSidebar"] {
            display: none !important;
        }

        header[data-testid="stHeader"] {
            display: none !important;
        }

        .main .block-container {
            max-width: 100% !important;
            padding: 0 !important;
        }

        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            color-adjust: exact !important;
        }

        .kpi-card,
        .tabela-container,
        .movement-card,
        .chart-container {
            break-inside: avoid;
        }

        .dashboard-header {
            margin-bottom: 8px;
        }

        .kpi-card {
            min-height: 82px;
        }

        .tabela-financeira th {
            padding: 6px 7px;
        }

        .tabela-financeira td {
            padding: 5px 7px;
        }

        .dashboard-footer {
            margin-top: 5px;
        }
    }

    @media (max-width: 900px) {
        .dashboard-header {
            grid-template-columns: 1fr;
            gap: 8px;
        }

        .header-center {
            order: -1;
            padding: 0;
        }

        .header-period,
        .update-wrapper {
            text-align: left;
            justify-content: flex-start;
        }

        .kpi-value {
            font-size: 19px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 0. CONFIGURAÇÃO DA BARRA LATERAL (FILTROS)
# ==============================================================================
hoje = datetime.now().date()
primeiro_dia_mes = hoje.replace(day=1)

with st.sidebar:
    st.markdown("### Filtros do Painel")

    data_selecionada = st.date_input(
        "Selecione o Período:",
        value=(primeiro_dia_mes, hoje),
        min_value=datetime(2020, 1, 1).date(),
        max_value=hoje,
        format="DD/MM/YYYY"
    )

    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)

    st.markdown("### Relatório")

    st.info(
        "Para gerar um relatório, utilize a impressão do navegador em "
        "**Paisagem** e desative cabeçalhos/rodapés.",
        icon="ℹ️"
    )

    components.html("""
        <button
            onclick="try { window.parent.print(); } catch(e) { window.print(); }"
            style="
                width:100%;
                background:#234a78;
                color:white;
                border:1px solid #193754;
                padding:11px;
                border-radius:4px;
                font-family:'Segoe UI',Arial,sans-serif;
                font-weight:700;
                font-size:13px;
                cursor:pointer;
            "
        >
            Salvar Dashboard (PDF)
        </button>
    """, height=50)

# Validação segura para garantir que o usuário escolheu duas datas no calendário
if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
    data_inicio_filtro, data_fim_filtro = data_selecionada
else:
    data_inicio_filtro = (
        data_selecionada[0]
        if isinstance(data_selecionada, tuple)
        else data_selecionada
    )
    data_fim_filtro = data_inicio_filtro


# ==============================================================================
# 1. FUNÇÃO DE LEITURA E LIMPEZA BLINDADA
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


def formatar_moeda(valor):
    try:
        val = float(valor)

        if val == 0:
            return "-"

        return (
            f"R$ {val:,.2f}"
            .replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )

    except Exception:
        return "-"


def formatar_abreviado(valor):
    try:
        val = float(valor)

        if abs(val) >= 1_000_000:
            return f"R$ {val/1_000_000:.1f}M".replace('.', ',')

        elif abs(val) >= 1_000:
            return f"R$ {val/1_000:.1f}K".replace('.', ',')

        else:
            return f"R$ {val:.0f}"

    except Exception:
        return ""


def formatar_transf(valor):
    try:
        val = float(valor)

        if val == 0:
            return "-"

        prefixo = "+ " if val > 0 else "- "

        return (
            f"{prefixo}R$ {abs(val):,.2f}"
            .replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )

    except Exception:
        return "-"


# ==============================================================================
# 2. CARGA DE DADOS
# ==============================================================================

@st.cache_data(ttl=60)
def carregar_dados(data_inicio, data_fim):

    conn = conectar_sheets()

    if conn is None:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            0.0,
            'Conta Bancária',
            0.0,
            0.0,
            data_inicio,
            data_fim
        )

    try:

        # =========================================================
        # 1. ABA SALDO_INICIAL
        # =========================================================

        df_saldo_inicial = pd.DataFrame(
            columns=[
                'Conta Bancária',
                'Saldo Inicial',
                'Conta Garantida'
            ]
        )

        try:

            df_si = conn.read(
                worksheet="Saldo_Inicial",
                ttl=0
            )

            if not df_si.empty:

                df_si.columns = [
                    str(c).strip()
                    for c in df_si.columns
                ]

                df_si = df_si.loc[
                    :,
                    ~df_si.columns.duplicated()
                ].copy()

                col_si_conta = next(
                    (
                        c for c in df_si.columns
                        if 'banco' in c.lower()
                        or 'conta' in c.lower()
                    ),
                    df_si.columns[0]
                )

                col_si_valor = next(
                    (
                        c for c in df_si.columns
                        if 'saldo' in c.lower()
                        or 'inicial' in c.lower()
                        or 'valor' in c.lower()
                    ),
                    df_si.columns[1]
                    if len(df_si.columns) > 1
                    else df_si.columns[0]
                )

                col_si_garantida = next(
                    (
                        c for c in df_si.columns
                        if 'garantida' in c.lower()
                        or 'limite' in c.lower()
                    ),
                    None
                )

                df_si[col_si_valor] = (
                    df_si[col_si_valor]
                    .apply(limpa_valor_bruto)
                )

                cols_to_keep = [
                    col_si_conta,
                    col_si_valor
                ]

                new_cols = [
                    'Conta Bancária',
                    'Saldo Inicial'
                ]

                if col_si_garantida:

                    df_si[col_si_garantida] = (
                        df_si[col_si_garantida]
                        .apply(limpa_valor_bruto)
                    )

                    cols_to_keep.append(
                        col_si_garantida
                    )

                    new_cols.append(
                        'Conta Garantida'
                    )

                df_saldo_inicial = (
                    df_si[cols_to_keep]
                    .copy()
                )

                df_saldo_inicial.columns = new_cols

                if 'Conta Garantida' not in df_saldo_inicial.columns:
                    df_saldo_inicial['Conta Garantida'] = 0.0

                df_saldo_inicial['Conta Bancária'] = (
                    df_saldo_inicial['Conta Bancária']
                    .astype(str)
                    .str.strip()
                )

        except Exception as e:
            print("Aviso ao ler Saldo_Inicial:", e)

        # =========================================================
        # LEITURA DO CADASTRO
        # =========================================================

        dicionario_contas = {}

        try:

            df_cad = conn.read(
                worksheet="Cadastro Fornecedores",
                ttl=0
            )

            if not df_cad.empty:

                col_razao = df_cad.columns[1]
                col_conta = df_cad.columns[2]

                for _, row in df_cad.iterrows():

                    razao = (
                        str(row[col_razao])
                        .strip()
                        .upper()
                    )

                    conta = (
                        str(row[col_conta])
                        .strip()
                    )

                    if (
                        razao != 'NAN'
                        and razao != ''
                    ):
                        dicionario_contas[razao] = conta

        except Exception as e:
            print(
                "Erro ao ler Cadastro de Fornecedores:",
                e
            )

        # =========================================================
        # MATCH FUZZY
        # =========================================================

        def achar_conta_fuzzy(lancamento):

            if not dicionario_contas:
                return "Não Mapeado"

            lanc = str(lancamento).upper()

            nome_extrato = lanc

            match = re.search(
                r'/\s*([^)]+)',
                lanc
            )

            if match:
                nome_extrato = (
                    match.group(1)
                    .strip()
                )

            lixos = [
                ' LTDA',
                ' S.A.',
                ' S.A',
                ' S/A',
                ' COMERCIO',
                ' COM.',
                ' DE ',
                ' PRODUTOS',
                ' PROD.',
                ' HOSPITALARES',
                ' HOSP.'
            ]

            for lixo in lixos:
                nome_extrato = (
                    nome_extrato
                    .replace(lixo, '')
                )

            nome_extrato = nome_extrato.strip()

            chaves_cadastro = list(
                dicionario_contas.keys()
            )

            chaves_limpas = []

            for chave in chaves_cadastro:

                chave_tmp = chave

                for lixo in lixos:
                    chave_tmp = (
                        chave_tmp
                        .replace(lixo, '')
                    )

                chaves_limpas.append(
                    chave_tmp.strip()
                )

            matches = difflib.get_close_matches(
                nome_extrato,
                chaves_limpas,
                n=1,
                cutoff=0.4
            )

            if matches:

                idx_match = (
                    chaves_limpas
                    .index(matches[0])
                )

                chave_original = (
                    chaves_cadastro[idx_match]
                )

                return dicionario_contas[
                    chave_original
                ]

            return "Não Mapeado"

        # =========================================================
        # 2. EXTRATOS
        # =========================================================

        df_extratos = None

        try:

            df_ext = conn.read(
                worksheet="Extratos_Bancos",
                ttl=0
            )

            if not df_ext.empty:

                while len(df_ext.columns) < 8:
                    df_ext[
                        f"Col_Extra_{len(df_ext.columns)}"
                    ] = ""

                df_ext = df_ext.iloc[
                    :,
                    [0, 1, 4, 5, 7]
                ].copy()

                df_ext.columns = [
                    'Conta Bancária',
                    'Data',
                    'Vl Débito',
                    'Vl Crédito',
                    'Tipo de Transação'
                ]

                df_ext['Data'] = (
                    pd.to_datetime(
                        df_ext['Data'],
                        dayfirst=True,
                        errors='coerce'
                    )
                    .dt.normalize()
                )

                dt_ini_pd = pd.to_datetime(
                    data_inicio
                )

                dt_fim_pd = pd.to_datetime(
                    data_fim
                )

                df_ext = df_ext[
                    (df_ext['Data'] >= dt_ini_pd)
                    &
                    (df_ext['Data'] <= dt_fim_pd)
                ].copy()

                df_ext['Vl Crédito'] = (
                    df_ext['Vl Crédito']
                    .apply(limpa_valor_bruto)
                )

                df_ext['Vl Débito'] = (
                    df_ext['Vl Débito']
                    .apply(limpa_valor_bruto)
                )

                df_ext['Conta Bancária'] = (
                    df_ext['Conta Bancária']
                    .astype(str)
                    .str.strip()
                )

                def normalizar_texto(txt):

                    if pd.isna(txt) or txt is None:
                        return ""

                    return (
                        unicodedata.normalize(
                            'NFKD',
                            str(txt)
                        )
                        .encode(
                            'ASCII',
                            'ignore'
                        )
                        .decode('utf-8')
                        .lower()
                    )

                serie_tipo = (
                    df_ext[
                        'Tipo de Transação'
                    ]
                    .apply(normalizar_texto)
                )

                df_ext['É Transf'] = (
                    serie_tipo.str.contains(
                        'transferencia'
                    )
                    &
                    serie_tipo.str.contains(
                        'interna'
                    )
                )

                df_ext['Cred_Op'] = (
                    df_ext['Vl Crédito']
                    .where(
                        ~df_ext['É Transf'],
                        0.0
                    )
                )

                df_ext['Deb_Op'] = (
                    df_ext['Vl Débito']
                    .where(
                        ~df_ext['É Transf'],
                        0.0
                    )
                )

                df_ext['Cred_Tr'] = (
                    df_ext['Vl Crédito']
                    .where(
                        df_ext['É Transf'],
                        0.0
                    )
                )

                df_ext['Deb_Tr'] = (
                    df_ext['Vl Débito']
                    .where(
                        df_ext['É Transf'],
                        0.0
                    )
                )

                df_extratos = df_ext

        except Exception as e:
            print(
                "Aviso ao ler extratos:",
                e
            )

        # =========================================================
        # 3. CONSTRUÇÃO DA TABELA FINAL DE BANCOS
        # =========================================================

        def definir_tipo(nome):

            if 'getnet' in str(nome).lower():
                return 'Limite'

            return (
                'Aplicação'
                if (
                    'aplicação'
                    in str(nome).lower()
                    or
                    'investimentos'
                    in str(nome).lower()
                )
                else 'Disponível'
            )

        df_fim_mes = (
            df_saldo_inicial.copy()
        )

        if (
            df_extratos is not None
            and not df_extratos.empty
        ):

            df_extratos_grouped = (
                df_extratos
                .groupby('Conta Bancária')
                .agg({
                    'Cred_Op': 'sum',
                    'Deb_Op': 'sum',
                    'Cred_Tr': 'sum',
                    'Deb_Tr': 'sum'
                })
                .reset_index()
            )

            df_fim_mes = df_fim_mes.merge(
                df_extratos_grouped,
                on='Conta Bancária',
                how='outer'
            )

            df_fim_mes['Saldo Inicial'] = (
                df_fim_mes['Saldo Inicial']
                .fillna(0)
            )

            df_fim_mes['Conta Garantida'] = (
                df_fim_mes['Conta Garantida']
                .fillna(0)
            )

            df_fim_mes['Entrada Op'] = (
                df_fim_mes['Cred_Op']
                .fillna(0)
            )

            df_fim_mes['Saída Op'] = (
                df_fim_mes['Deb_Op']
                .fillna(0)
            )

            df_fim_mes['Entrada Tr'] = (
                df_fim_mes['Cred_Tr']
                .fillna(0)
            )

            df_fim_mes['Saída Tr'] = (
                df_fim_mes['Deb_Tr']
                .fillna(0)
            )

        else:

            df_fim_mes['Entrada Op'] = 0.0
            df_fim_mes['Saída Op'] = 0.0
            df_fim_mes['Entrada Tr'] = 0.0
            df_fim_mes['Saída Tr'] = 0.0

        df_fim_mes['Tipo'] = (
            df_fim_mes['Conta Bancária']
            .apply(definir_tipo)
        )

        df_fim_mes['Saldo Final'] = (
            df_fim_mes['Saldo Inicial']
            +
            df_fim_mes['Entrada Op']
            -
            df_fim_mes['Saída Op']
            +
            df_fim_mes['Entrada Tr']
            -
            df_fim_mes['Saída Tr']
        )

        # =========================================================
        # 4. GRÁFICO DIÁRIO
        # =========================================================

        saldo_inicial_caixa = (
            df_fim_mes[
                df_fim_mes['Tipo'].isin(
                    ['Disponível', 'Aplicação']
                )
            ]['Saldo Inicial']
            .sum()
        )

        if (
            df_extratos is not None
            and not df_extratos.empty
        ):

            df_ext_caixa = (
                df_extratos[
                    df_extratos[
                        'Conta Bancária'
                    ]
                    .apply(definir_tipo)
                    .isin([
                        'Disponível',
                        'Aplicação'
                    ])
                ]
                .copy()
            )

            df_extratos_diario = (
                df_ext_caixa
                .groupby('Data')
                .agg({
                    'Cred_Op': 'sum',
                    'Deb_Op': 'sum',
                    'Cred_Tr': 'sum',
                    'Deb_Tr': 'sum'
                })
                .reset_index()
            )

            df_graficos = (
                df_extratos_diario
                .sort_values('Data')
                .copy()
            )

            df_graficos['Entrada'] = (
                df_graficos['Cred_Op']
                .fillna(0)
            )

            df_graficos['Saída'] = (
                df_graficos['Deb_Op']
                .fillna(0)
            )

            df_graficos['Movimentação Líquida'] = (
                (
                    df_graficos['Cred_Op']
                    +
                    df_graficos['Cred_Tr']
                )
                -
                (
                    df_graficos['Deb_Op']
                    +
                    df_graficos['Deb_Tr']
                )
            ).fillna(0)

            df_graficos['Saldo Final'] = (
                saldo_inicial_caixa
                +
                df_graficos[
                    'Movimentação Líquida'
                ].cumsum()
            )

        else:

            df_graficos = pd.DataFrame(
                columns=[
                    'Data',
                    'Entrada',
                    'Saída',
                    'Movimentação Líquida',
                    'Saldo Final'
                ]
            )

        if not df_graficos.empty:

            df_graficos['Data_Label'] = (
                df_graficos['Data']
                .dt.strftime('%d/%m')
            )

        else:

            df_graficos['Data_Label'] = (
                pd.Series(dtype='object')
            )

        # =========================================================
        # 5. KPI OPERACIONAL
        # =========================================================

        entradas_operacionais = (
            df_extratos['Cred_Op'].sum()
            if df_extratos is not None
            else 0.0
        )

        saidas_operacionais = (
            df_extratos['Deb_Op'].sum()
            if df_extratos is not None
            else 0.0
        )

        # =========================================================
        # 6. APLICAÇÕES
        # =========================================================

        df_aplicacoes_nova = pd.DataFrame()
        saldo_aplicado_kpi = 0.0

        try:

            df_app = conn.read(
                worksheet="Aplicações",
                ttl=0
            )

            if not df_app.empty:

                df_app.columns = [
                    str(c).strip()
                    for c in df_app.columns
                ]

                col_banco = df_app.columns[0]

                for c in df_app.columns:

                    if (
                        'banco' in c.lower()
                        or
                        'conta' in c.lower()
                    ):

                        col_banco = c
                        break

                df_app = df_app[
                    df_app[col_banco].notna()
                    &
                    (
                        df_app[col_banco]
                        .astype(str)
                        .str.strip()
                        != ''
                    )
                ]

                df_app = df_app[
                    ~df_app[col_banco]
                    .astype(str)
                    .str.lower()
                    .str.contains('total')
                ]

                def get_col(kws):

                    for c in df_app.columns:

                        if any(
                            kw in c.lower()
                            for kw in kws
                        ):
                            return c

                    return None

                c_si = get_col(['inicial'])
                c_app = get_col([
                    'aplicaç',
                    'aplicac'
                ])
                c_imp = get_col(['imposto'])
                c_rend = get_col(['rendimento'])
                c_resg = get_col(['resgate'])
                c_atual = get_col([
                    'atual',
                    'final'
                ])

                cols_to_clean = [
                    c for c in [
                        c_si,
                        c_app,
                        c_imp,
                        c_rend,
                        c_resg,
                        c_atual
                    ]
                    if c
                ]

                for c in cols_to_clean:
                    df_app[c] = (
                        df_app[c]
                        .apply(limpa_valor_bruto)
                    )

                df_aplicacoes_nova = (
                    df_app.copy()
                )

                if c_atual:
                    saldo_aplicado_kpi = (
                        df_aplicacoes_nova[c_atual]
                        .sum()
                    )

        except Exception as e:
            print(
                "Erro ao ler Aplicações:",
                e
            )

        return (
            df_fim_mes,
            df_graficos,
            df_aplicacoes_nova,
            saldo_aplicado_kpi,
            'Conta Bancária',
            entradas_operacionais,
            saidas_operacionais,
            data_inicio,
            data_fim
        )

    except Exception as e:

        st.error(
            f"Erro fatal ao carregar dados: {e}"
        )

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            0.0,
            'Conta Bancária',
            0.0,
            0.0,
            data_inicio,
            data_fim
        )


# ==============================================================================
# CHAMADA PRINCIPAL
# ==============================================================================

(
    df_consolidado,
    df_graficos,
    df_aplicacoes_nova,
    saldo_aplicado_kpi,
    col_conta,
    entradas_operacionais,
    saidas_operacionais,
    data_ini_painel,
    data_fim_painel
) = carregar_dados(
    data_inicio_filtro,
    data_fim_filtro
)

if not col_conta:
    col_conta = 'Conta Bancária'

if df_consolidado.empty:
    st.stop()


# ==============================================================================
# 3. CÁLCULOS DOS KPIs
# ==============================================================================

saldo_aplicado = saldo_aplicado_kpi

saldo_disponivel = (
    df_consolidado[
        df_consolidado['Tipo'] == 'Disponível'
    ]['Saldo Final']
    .sum()
)

saldo_getnet = (
    df_consolidado[
        df_consolidado['Tipo'] == 'Limite'
    ]['Saldo Final']
    .sum()
)

saldo_conta_garantida = (
    df_consolidado['Conta Garantida']
    .sum()
)

limites_totais = (
    saldo_getnet
    +
    saldo_conta_garantida
)

saldo_total = (
    saldo_disponivel
    +
    saldo_aplicado
)

entradas_mes = entradas_operacionais
saidas_mes = saidas_operacionais
resultado_liquido_mes = (
    entradas_mes
    -
    saidas_mes
)


# ==============================================================================
# 4. GRÁFICOS E VARIÁVEIS
# ==============================================================================

data_hoje = datetime.now().strftime(
    '%d/%m/%Y %H:%M'
)

periodo_str = (
    f"{data_ini_painel.strftime('%d/%m/%Y')} "
    f"- "
    f"{data_fim_painel.strftime('%d/%m/%Y')}"
)

dt_ini_short = data_ini_painel.strftime(
    '%d/%m'
)

dt_fim_short = data_fim_painel.strftime(
    '%d/%m'
)


# ==============================================================================
# GRÁFICO DONUT
# ==============================================================================

fig_donut = go.Figure(
    data=[
        go.Pie(
            values=[
                saldo_aplicado,
                saldo_disponivel
            ],
            labels=[
                'Aplicado',
                'Disponível'
            ],
            hole=0.68,
            marker=dict(
                colors=[
                    '#5d66a8',
                    '#157a5b'
                ],
                line=dict(
                    color='#ffffff',
                    width=2
                )
            ),
            textinfo='percent',
            texttemplate='%{percent:.1%}',
            textfont=dict(
                size=10,
                color='#26313c'
            ),
            hoverinfo='label+percent'
        )
    ]
)

fig_donut.update_layout(
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.04,
        xanchor="center",
        x=0.5,
        font=dict(size=9),
        bgcolor='rgba(0,0,0,0)'
    ),
    margin=dict(
        t=8,
        b=25,
        l=0,
        r=0
    ),
    height=285,
    paper_bgcolor='#ffffff',
    plot_bgcolor='#ffffff',
    annotations=[
        dict(
            text=(
                f"<b>R$ "
                f"{saldo_total/1000000:,.1f}M"
                f"</b><br>"
                f"<span style='font-size:10px'>"
                f"Saldo Total"
                f"</span>"
            ),
            x=0.5,
            y=0.5,
            font=dict(
                size=14,
                color='#17212b'
            ),
            showarrow=False
        )
    ]
)


# ==============================================================================
# GRÁFICO EVOLUÇÃO
# ==============================================================================

fig_combinado = go.Figure()

fig_combinado.add_trace(
    go.Bar(
        x=df_graficos['Data_Label'],
        y=df_graficos['Saldo Final'],
        name='Saldo Total',
        marker_color='#315d8c',
        marker_line_width=0,
        text=[
            formatar_abreviado(v)
            for v in df_graficos['Saldo Final']
        ],
        textposition='outside',
        textfont=dict(
            size=10,
            color='#26313c'
        ),
        opacity=0.92,
        width=0.55
    )
)

fig_combinado.update_layout(
    margin=dict(
        t=25,
        b=12,
        l=5,
        r=5
    ),
    height=205,
    xaxis=dict(
        tickfont=dict(size=9),
        showgrid=False,
        linecolor='#dfe4ea',
        linewidth=1,
        showline=True
    ),
    yaxis=dict(
        showticklabels=False,
        showgrid=True,
        gridcolor='#edf0f3',
        zeroline=False
    ),
    barmode='overlay',
    showlegend=False,
    plot_bgcolor='#ffffff',
    paper_bgcolor='#ffffff',
    hovermode='x unified'
)


# ==============================================================================
# 5. CABEÇALHO
# ==============================================================================

st.markdown(
    f"""
    <div class="dashboard-header">

        <div class="header-period">
            <div class="date">
                {periodo_str}
            </div>

            <div class="label">
                Período Selecionado
            </div>
        </div>

        <div class="header-center">
            <h1>
                PAINEL FINANCEIRO MENSAL
            </h1>

            <p>
                Controle Consolidado de Bancos
            </p>
        </div>

        <div class="update-wrapper">
            <div class="update-badge">
                <span>
                    Atualização
                </span>

                <b>
                    {data_hoje}
                </b>
            </div>
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# ==============================================================================
# KPIs
# ==============================================================================

kpi_row = st.columns(4)

kp_data = [

    (
        kpi_row[0],
        "SALDO TOTAL",
        f"R$ {saldo_total:,.2f}",
        "total"
    ),

    (
        kpi_row[1],
        "SALDO DISPONÍVEL",
        f"R$ {saldo_disponivel:,.2f}",
        "disponivel"
    ),

    (
        kpi_row[2],
        "APLICAÇÕES",
        f"R$ {saldo_aplicado:,.2f}",
        "aplicacoes"
    ),

    (
        kpi_row[3],
        "LIMITES TOTAIS",
        f"R$ {limites_totais:,.2f}",
        "limites"
    )
]

for col, title, val, color in kp_data:

    col.markdown(
        f"""
        <div class="kpi-card {color}">
            <div class="kpi-title">
                {title}
            </div>

            <div class="kpi-value">
                {val}
            </div>

            <div class="kpi-foot">
                Valores em Reais (R$)
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.markdown("<br>", unsafe_allow_html=True)


# ==============================================================================
# BLOCO SUPERIOR
# ==============================================================================

c1, c2, c3 = st.columns(
    [0.85, 1.25, 1.6]
)


# ==============================================================================
# DISTRIBUIÇÃO DO CAIXA
# ==============================================================================

with c1:

    st.markdown(
        """
        <div class="section-title">
            DISTRIBUIÇÃO DO CAIXA
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='chart-container'>",
        unsafe_allow_html=True
    )

    st.plotly_chart(
        fig_donut,
        use_container_width=True,
        config={
            'displayModeBar': False
        }
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# ==============================================================================
# MOVIMENTAÇÃO OPERACIONAL
# ==============================================================================

with c2:

    st.markdown(
        f"""
        <div class="section-title">
            MOVIMENTAÇÃO OPERACIONAL
            <span class="section-ref">
                REF.: {periodo_str}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    m1, m2, m3 = st.columns(3)

    m1.markdown(
        f"""
        <div class="movement-card">
            <div
                class="movement-label"
                style="color:#157a5b;"
            >
                ENTRADAS
            </div>

            <div class="movement-value">
                R$ {entradas_mes:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    m2.markdown(
        f"""
        <div class="movement-card">
            <div
                class="movement-label"
                style="color:#b74242;"
            >
                SAÍDAS
            </div>

            <div class="movement-value">
                R$ {saidas_mes:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if resultado_liquido_mes >= 0:

        cor_resultado = "#157a5b"

    else:

        cor_resultado = "#b74242"

    m3.markdown(
        f"""
        <div class="movement-card">
            <div
                class="movement-label"
                style="color:{cor_resultado};"
            >
                RESULTADO LÍQUIDO
            </div>

            <div
                class="movement-value"
                style="color:{cor_resultado};"
            >
                R$ {resultado_liquido_mes:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-title" style="margin-top:10px;">
            EVOLUÇÃO DIÁRIA DO SALDO TOTAL
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='chart-container'>",
        unsafe_allow_html=True
    )

    st.plotly_chart(
        fig_combinado,
        use_container_width=True,
        config={
            'displayModeBar': False
        }
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# ==============================================================================
# RESUMO APLICAÇÕES
# ==============================================================================

with c3:

    st.markdown(
        f"""
        <div class="section-title">
            RESUMO APLICAÇÕES
            <span class="section-ref">
                REF.: {periodo_str}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not df_aplicacoes_nova.empty:

        def find_c(kws):

            for c in df_aplicacoes_nova.columns:

                if any(
                    kw in c.lower()
                    for kw in kws
                ):
                    return c

            return None

        c_banco = (
            find_c([
                'conta',
                'banco'
            ])
            or
            df_aplicacoes_nova.columns[0]
        )

        c_si = find_c(['inicial'])
        c_app = find_c([
            'aplicaç',
            'aplicac'
        ])

        c_imp = find_c(['imposto'])
        c_rend = find_c(['rendimento'])
        c_resg = find_c(['resgate'])

        c_atual = find_c([
            'atual',
            'final'
        ])

        html_app = (
            '<div class="tabela-container">'
            '<table class="tabela-financeira">'
            '<thead>'
            '<tr>'
            '<th>BANCO</th>'
            f'<th class="valores">'
            f'SALDO INICIAL {dt_ini_short}'
            f'</th>'
            '<th class="valores">APLICAÇÕES</th>'
            '<th class="valores">IMPOSTOS</th>'
            '<th class="valores">RENDIMENTOS</th>'
            '<th class="valores">RESGATES</th>'
            f'<th class="valores">'
            f'SALDO ATUAL {dt_fim_short}'
            f'</th>'
            '</tr>'
            '</thead>'
            '<tbody>'
        )

        tot_si = 0
        tot_app = 0
        tot_imp = 0
        tot_rend = 0
        tot_resg = 0
        tot_atual = 0

        for _, row in df_aplicacoes_nova.iterrows():

            banco = row[c_banco]

            si = (
                row[c_si]
                if c_si
                else 0
            )

            app = (
                row[c_app]
                if c_app
                else 0
            )

            imp = (
                row[c_imp]
                if c_imp
                else 0
            )

            rend = (
                row[c_rend]
                if c_rend
                else 0
            )

            resg = (
                row[c_resg]
                if c_resg
                else 0
            )

            atual = (
                row[c_atual]
                if c_atual
                else 0
            )

            tot_si += si
            tot_app += app
            tot_imp += imp
            tot_rend += rend
            tot_resg += resg
            tot_atual += atual

            cor_rend = (
                "#6b7785"
                if rend == 0
                else
                "#157a5b"
                if rend > 0
                else
                "#b74242"
            )

            html_app += f"""
            <tr>
                <td style="
                    font-size:11px;
                    font-weight:700;
                    color:#34404c;
                ">
                    {banco}
                </td>

                <td class="valores">
                    {formatar_moeda(si)}
                </td>

                <td class="valores">
                    {formatar_moeda(app)}
                </td>

                <td
                    class="valores"
                    style="color:#b74242;"
                >
                    {formatar_moeda(imp)}
                </td>

                <td
                    class="valores"
                    style="color:{cor_rend};"
                >
                    {formatar_moeda(rend)}
                </td>

                <td
                    class="valores"
                    style="color:#b74242;"
                >
                    {formatar_moeda(resg)}
                </td>

                <td
                    class="valores valor-destaque"
                >
                    {formatar_moeda(atual)}
                </td>
            </tr>
            """

        cor_tot_rend = (
            "#6b7785"
            if tot_rend == 0
            else
            "#157a5b"
            if tot_rend > 0
            else
            "#b74242"
        )

        html_app += f"""
        <tr class="linha-total">

            <td>
                TOTAL
            </td>

            <td class="valores">
                {formatar_moeda(tot_si)}
            </td>

            <td class="valores">
                {formatar_moeda(tot_app)}
            </td>

            <td
                class="valores"
                style="color:#b74242;"
            >
                {formatar_moeda(tot_imp)}
            </td>

            <td
                class="valores"
                style="color:{cor_tot_rend};"
            >
                {formatar_moeda(tot_rend)}
            </td>

            <td
                class="valores"
                style="color:#b74242;"
            >
                {formatar_moeda(tot_resg)}
            </td>

            <td class="valores valor-destaque">
                {formatar_moeda(tot_atual)}
            </td>

        </tr>
        """

        html_app += (
            '</tbody>'
            '</table>'
            '</div>'
        )

        st.markdown(
            html_app,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div style="
                padding:18px;
                text-align:center;
                color:#6b7785;
                font-size:11px;
                border:1px dashed #cbd3dc;
                border-radius:4px;
                background:#ffffff;
                margin-bottom:8px;
            ">
                Nenhuma aplicação encontrada na aba Aplicações.
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# SEPARADOR
# ==============================================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True
)


# ==============================================================================
# TABELAS INFERIORES
# ==============================================================================

col_tab, col_diario = st.columns(
    [1.6, 1]
)


# ==============================================================================
# SALDO DE TODOS OS BANCOS
# ==============================================================================

with col_tab:

    st.markdown(
        """
        <div class="section-title">
            SALDO DE TODOS OS BANCOS
        </div>
        """,
        unsafe_allow_html=True
    )

    df_view = df_consolidado[
        [
            'Tipo',
            col_conta,
            'Saldo Inicial',
            'Entrada Op',
            'Saída Op',
            'Entrada Tr',
            'Saída Tr',
            'Saldo Final'
        ]
    ].copy()

    def get_ordem(banco_nome):

        nome = (
            str(banco_nome)
            .lower()
            .strip()
        )

        if (
            "aplicação" in nome
            or
            "aplicacao" in nome
            or
            "invest" in nome
        ):

            if "unicred" in nome:
                return 11

            if "bradesco" in nome:
                return 12

            if "santander" in nome:
                return 13

            if (
                "itaú" in nome
                or
                "itau" in nome
            ):
                return 14

            return 50

        if "caixa" in nome:
            return 1

        if "unicred" in nome:
            return 2

        if "uniprime" in nome:
            return 3

        if (
            "brasil" in nome
            or
            "bb" in nome
        ):
            return 4

        if "70860" in nome:
            return 5

        if "comerc" in nome:
            return 6

        if (
            "itaú" in nome
            or
            "itau" in nome
        ):
            return 7

        if "santander" in nome:
            return 8

        if "sicoob" in nome:
            return 9

        if "cofre" in nome:
            return 10

        if "getnet" in nome:
            return 100

        return 999

    df_view['Ordem'] = (
        df_view[col_conta]
        .apply(get_ordem)
    )

    df_view = (
        df_view
        .sort_values('Ordem')
        .drop(columns=['Ordem'])
    )

    # Separação da lógica
    df_bancos = (
        df_view[
            df_view['Tipo'] != 'Limite'
        ]
    )

    df_getnet = (
        df_view[
            df_view['Tipo'] == 'Limite'
        ]
    )

    totais = {
        col: df_bancos[col].sum()
        for col in [
            'Saldo Inicial',
            'Entrada Op',
            'Saída Op',
            'Entrada Tr',
            'Saída Tr',
            'Saldo Final'
        ]
    }

    html_tabela = (
        '<div class="tabela-container tabela-bancos">'
        '<table class="tabela-financeira">'
        '<thead>'
        '<tr>'
        '<th class="centro">#</th>'
        f'<th>{col_conta}</th>'
        '<th class="centro">TIPO</th>'
        f'<th class="valores">SALDO INICIAL {dt_ini_short}</th>'
        '<th class="valores">ENTRADA (OP.)</th>'
        '<th class="valores">SAÍDA (OP.)</th>'
        '<th class="valores">ENTRADA (INT.)</th>'
        '<th class="valores">SAÍDA (INT.)</th>'
        f'<th class="valores">SALDO ATUAL {dt_fim_short}</th>'
        '</tr>'
        '</thead>'
        '<tbody>'
    )

    # Bancos normais
    for idx, row in enumerate(
        df_bancos.itertuples()
    ):

        cor_transf = (
            "#6b7785"
            if row._6 == 0
            else
            "#2f657a"
        )

        cor_transf_saida = (
            "#6b7785"
            if row._7 == 0
            else
            "#b74242"
        )

        html_tabela += f"""
        <tr>

            <td class="centro">
                {idx + 1}
            </td>

            <td
                style="
                    font-weight:700;
                    color:#34404c;
                "
            >
                {row._2}
            </td>

            <td
                class="centro"
                style="
                    font-size:9px;
                    font-weight:800;
                    color:#5b6672;
                "
            >
                {row.Tipo}
            </td>

            <td class="valores">
                {formatar_moeda(row._3)}
            </td>

            <td class="valores">
                {formatar_moeda(row._4)}
            </td>

            <td class="valores">
                {formatar_moeda(row._5)}
            </td>

            <td
                class="valores"
                style="color:{cor_transf};"
            >
                {formatar_moeda(row._6)}
            </td>

            <td
                class="valores"
                style="color:{cor_transf_saida};"
            >
                {formatar_moeda(row._7)}
            </td>

            <td
                class="valores valor-destaque"
            >
                {formatar_moeda(row._8)}
            </td>

        </tr>
        """

    # Total
    html_tabela += f"""
    <tr class="linha-total">

        <td></td>

        <td>
            TOTAL
        </td>

        <td></td>

        <td class="valores">
            {formatar_moeda(totais["Saldo Inicial"])}
        </td>

        <td class="valores">
            {formatar_moeda(totais["Entrada Op"])}
        </td>

        <td class="valores">
            {formatar_moeda(totais["Saída Op"])}
        </td>

        <td
            class="valores"
            style="color:#6b7785;"
        >
            -
        </td>

        <td
            class="valores"
            style="color:#6b7785;"
        >
            -
        </td>

        <td class="valores valor-destaque">
            {formatar_moeda(totais["Saldo Final"])}
        </td>

    </tr>
    """

    # Getnet / Limite
    if not df_getnet.empty:

        for idx, row in enumerate(
            df_getnet.itertuples()
        ):

            idx_display = (
                len(df_bancos)
                +
                idx
                +
                1
            )

            cor_transf = (
                "#6b7785"
                if row._6 == 0
                else
                "#2f657a"
            )

            cor_transf_saida = (
                "#6b7785"
                if row._7 == 0
                else
                "#b74242"
            )

            html_tabela += f"""
            <tr class="linha-limite">

                <td class="centro">
                    {idx_display}
                </td>

                <td
                    style="
                        font-weight:800;
                    "
                >
                    {row._2}
                </td>

                <td
                    class="centro"
                    style="
                        font-size:9px;
                        font-weight:800;
                        color:#996b10;
                    "
                >
                    {row.Tipo}
                </td>

                <td class="valores">
                    {formatar_moeda(row._3)}
                </td>

                <td class="valores">
                    {formatar_moeda(row._4)}
                </td>

                <td class="valores">
                    {formatar_moeda(row._5)}
                </td>

                <td
                    class="valores"
                    style="color:{cor_transf};"
                >
                    {formatar_moeda(row._6)}
                </td>

                <td
                    class="valores"
                    style="color:{cor_transf_saida};"
                >
                    {formatar_moeda(row._7)}
                </td>

                <td
                    class="valores valor-destaque"
                >
                    {formatar_moeda(row._8)}
                </td>

            </tr>
            """

    html_tabela += (
        '</tbody>'
        '</table>'
        '</div>'
    )

    st.markdown(
        html_tabela,
        unsafe_allow_html=True
    )


# ==============================================================================
# SALDO DIÁRIO CONSOLIDADO
# ==============================================================================

with col_diario:

    st.markdown(
        """
        <div class="section-title">
            SALDO DIÁRIO CONSOLIDADO
        </div>
        """,
        unsafe_allow_html=True
    )

    df_diario_view = df_graficos[
        [
            'Data_Label',
            'Saldo Final',
            'Entrada',
            'Saída'
        ]
    ].copy()

    df_diario_view = (
        df_diario_view
        .sort_values(
            by='Data_Label',
            ascending=False
        )
    )

    html_diario = (
        '<div class="tabela-container">'
        '<table class="tabela-financeira">'
        '<thead>'
        '<tr>'
        '<th class="centro">DATA</th>'
        '<th class="valores">SALDO FINAL</th>'
        '<th class="valores">ENTRADA (OP.)</th>'
        '<th class="valores">SAÍDA (OP.)</th>'
        '</tr>'
        '</thead>'
        '<tbody>'
    )

    for _, row in df_diario_view.iterrows():

        html_diario += f"""
        <tr>

            <td
                class="centro"
                style="
                    font-size:10px;
                    font-weight:800;
                    color:#34404c;
                "
            >
                {row["Data_Label"]}
            </td>

            <td
                class="valores valor-destaque"
            >
                {formatar_moeda(row["Saldo Final"])}
            </td>

            <td
                class="valores"
                style="color:#157a5b;"
            >
                {formatar_moeda(row["Entrada"])}
            </td>

            <td
                class="valores"
                style="color:#b74242;"
            >
                {formatar_moeda(row["Saída"])}
            </td>

        </tr>
        """

    html_diario += (
        '</tbody>'
        '</table>'
        '</div>'
    )

    st.markdown(
        html_diario,
        unsafe_allow_html=True
    )


# ==============================================================================
# RODAPÉ
# ==============================================================================

st.markdown(
    f"""
    <div class="dashboard-footer">
        Valores em Reais (R$)
        &nbsp;|&nbsp;
        Dados atualizados em {data_hoje}
    </div>
    """,
    unsafe_allow_html=True
)
