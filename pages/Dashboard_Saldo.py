"""
Dashboard Financeiro Mensal - Versão Refatorada
Controle consolidado de bancos e aplicações com integração a Google Sheets.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import re
import difflib
import unicodedata
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from functools import lru_cache

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

@st.cache_resource
def load_database():
    """Carrega módulo de conexão com Sheets de forma segura."""
    try:
        from database import conectar_sheets
        return conectar_sheets
    except ImportError:
        st.error("Arquivo 'database.py' não encontrado.")
        return None


def configure_page():
    """Configuração inicial da página."""
    st.set_page_config(
        page_title="Painel Financeiro Mensal",
        layout="wide",
        page_icon="📊",
        initial_sidebar_state="expanded"
    )


# ============================================================================
# ESTILOS CSS - SISTEMA DE DESIGN
# ============================================================================

COLORS = {
    "bg": "#f4f6f8",
    "surface": "#ffffff",
    "surface_soft": "#f8fafc",
    "border": "#dfe4ea",
    "border_strong": "#cbd3dc",
    "text": "#17212b",
    "text_secondary": "#44515f",
    "muted": "#6b7785",
    "primary": "#234a78",
    "primary_dark": "#193754",
    "primary_soft": "#eef4fa",
    "success": "#157a5b",
    "success_soft": "#eef8f4",
    "danger": "#b74242",
    "danger_soft": "#fdf1f1",
    "warning": "#996b10",
    "warning_soft": "#fcf7ea",
    "info": "#2f657a",
}

TYPOGRAPHY = {
    "font_family": '"Inter", "Segoe UI", Arial, sans-serif',
    "shadow": "0 1px 3px rgba(16, 24, 40, 0.05)",
}


def get_css_styles():
    """Retorna todas as regras CSS do dashboard."""
    return f"""
    <style>
        :root {{
            --bg: {COLORS['bg']};
            --surface: {COLORS['surface']};
            --surface-soft: {COLORS['surface_soft']};
            --border: {COLORS['border']};
            --border-strong: {COLORS['border_strong']};
            --text: {COLORS['text']};
            --text-secondary: {COLORS['text_secondary']};
            --muted: {COLORS['muted']};
            --primary: {COLORS['primary']};
            --primary-dark: {COLORS['primary_dark']};
            --primary-soft: {COLORS['primary_soft']};
            --success: {COLORS['success']};
            --success-soft: {COLORS['success_soft']};
            --danger: {COLORS['danger']};
            --danger-soft: {COLORS['danger_soft']};
            --warning: {COLORS['warning']};
            --warning-soft: {COLORS['warning_soft']};
            --info: {COLORS['info']};
            --shadow: {TYPOGRAPHY['shadow']};
        }}

        html, body, [class*="css"] {{
            font-family: {TYPOGRAPHY['font_family']};
        }}

        .main {{
            background: var(--bg);
        }}

        .main .block-container {{
            padding-top: 0.65rem;
            padding-bottom: 0.65rem;
            max-width: 98%;
        }}

        div[data-testid="stVerticalBlock"] > div {{
            gap: 0.28rem !important;
        }}

        .stPlotlyChart {{
            background: transparent !important;
        }}

        .js-plotly-plot, .plot-container {{
            margin: 0 auto;
        }}

        /* ====== SIDEBAR ====== */
        [data-testid="stSidebar"] {{
            background: #f8fafc;
            border-right: 1px solid var(--border);
        }}

        [data-testid="stSidebar"] h3 {{
            color: var(--text);
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.2px;
        }}

        [data-testid="stSidebar"] .stInfo {{
            border-radius: 5px;
            border: 1px solid #dbe5ef;
            background: #f3f7fb;
        }}

        /* ====== HEADER ====== */
        .dashboard-header {{
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            min-height: 64px;
            padding: 5px 0 11px;
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border-strong);
        }}

        .header-period {{
            min-width: 210px;
            text-align: left;
        }}

        .header-period .date {{
            font-size: 16px;
            font-weight: 800;
            color: var(--text);
            letter-spacing: -0.15px;
        }}

        .header-period .label {{
            margin-top: 3px;
            font-size: 9px;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.75px;
        }}

        .header-center {{
            text-align: center;
            padding: 0 25px;
        }}

        .header-center h1 {{
            margin: 0;
            color: var(--primary-dark);
            font-size: 20px;
            line-height: 1.2;
            font-weight: 850;
            letter-spacing: 0.4px;
        }}

        .header-center p {{
            margin: 4px 0 0;
            color: var(--muted);
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.45px;
            text-transform: uppercase;
        }}

        .update-wrapper {{
            display: flex;
            justify-content: flex-end;
        }}

        .update-badge {{
            min-width: 122px;
            padding: 6px 11px;
            text-align: left;
            border-left: 3px solid var(--primary);
            background: #f8fafc;
        }}

        .update-badge span {{
            display: block;
            font-size: 8px;
            font-weight: 800;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.65px;
        }}

        .update-badge b {{
            display: block;
            margin-top: 2px;
            font-size: 11px;
            font-weight: 800;
            color: var(--text);
        }}

        /* ====== KPI CARDS ====== */
        .kpi-card {{
            position: relative;
            min-height: 92px;
            padding: 13px 16px 12px 17px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }}

        .kpi-card::before {{
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--primary);
        }}

        .kpi-card.disponivel::before {{
            background: var(--success);
        }}

        .kpi-card.aplicacoes::before {{
            background: #5d66a8;
        }}

        .kpi-card.limites::before {{
            background: var(--warning);
        }}

        .kpi-title {{
            font-size: 9px;
            line-height: 1.2;
            font-weight: 800;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.72px;
            margin-bottom: 6px;
        }}

        .kpi-value {{
            font-size: 23px;
            line-height: 1.15;
            font-weight: 850;
            color: var(--text);
            letter-spacing: -0.4px;
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
        }}

        .kpi-foot {{
            margin-top: 6px;
            font-size: 8px;
            color: #7a8591;
            text-transform: uppercase;
            letter-spacing: 0.45px;
        }}

        /* ====== SECTIONS ====== */
        .section-title {{
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
        }}

        .section-title::before {{
            content: "";
            width: 3px;
            height: 13px;
            margin-right: 7px;
            background: var(--primary);
            border-radius: 1px;
        }}

        .section-ref {{
            margin-left: auto;
            color: var(--muted);
            font-size: 8px;
            font-weight: 700;
            letter-spacing: 0.4px;
        }}

        /* ====== MOVEMENT CARDS ====== */
        .movement-card {{
            min-height: 64px;
            padding: 9px 11px;
            border: 1px solid var(--border);
            border-radius: 4px;
            background: var(--surface);
        }}

        .movement-card .movement-label {{
            font-size: 8px;
            font-weight: 800;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .movement-card .movement-value {{
            margin-top: 4px;
            font-size: 17px;
            line-height: 1.1;
            font-weight: 850;
            color: var(--text);
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}

        /* ====== TABLES ====== */
        .tabela-container {{
            overflow-x: auto;
            border: 1px solid var(--border-strong);
            border-radius: 4px;
            background: var(--surface);
            box-shadow: var(--shadow);
            font-size: 11px;
            width: 100%;
            margin-bottom: 7px;
        }}

        .tabela-financeira {{
            width: 100%;
            border-collapse: collapse;
        }}

        .tabela-financeira th {{
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
        }}

        .tabela-financeira td {{
            padding: 7px 8px;
            border-bottom: 1px solid #edf0f3;
            font-size: 11px;
            font-weight: 600;
            color: #2d3742;
            white-space: nowrap;
            vertical-align: middle;
            font-variant-numeric: tabular-nums;
        }}

        .tabela-financeira tbody tr:last-child td {{
            border-bottom: 0;
        }}

        .tabela-financeira tbody tr:hover td {{
            background: #f8fafc;
        }}

        .tabela-financeira th.valores,
        .tabela-financeira td.valores {{
            text-align: right !important;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}

        .tabela-financeira th.centro,
        .tabela-financeira td.centro {{
            text-align: center !important;
        }}

        .tabela-financeira td.valor-destaque {{
            font-size: 12px !important;
            font-weight: 850;
            color: #17212b;
        }}

        .tabela-financeira .linha-total {{
            background: #eef2f6;
        }}

        .tabela-financeira .linha-total td {{
            color: #17212b;
            font-weight: 850;
            border-top: 2px solid var(--border-strong);
        }}

        .tabela-financeira .linha-limite {{
            background: #fcf8ef;
        }}

        .tabela-financeira .linha-limite td {{
            border-top: 1px solid #e5cf98;
        }}

        .tabela-financeira .linha-limite td:first-child {{
            border-left: 3px solid #bd8a22;
        }}

        .tabela-financeira .linha-limite td:last-child {{
            color: var(--warning);
            font-weight: 850;
        }}

        /* ====== CHARTS ====== */
        .chart-container {{
            padding: 4px 5px 0;
            border: 1px solid var(--border);
            border-radius: 4px;
            background: var(--surface);
        }}

        /* ====== FOOTER ====== */
        .dashboard-footer {{
            margin-top: 9px;
            padding-top: 7px;
            border-top: 1px solid var(--border-strong);
            font-size: 8px;
            color: var(--muted);
            text-align: right;
            letter-spacing: 0.15px;
        }}

        hr {{
            border: 0 !important;
            border-top: 1px solid var(--border-strong) !important;
            margin: 12px 0 !important;
        }}

        /* ====== PRINT ====== */
        @media print {{
            @page {{
                size: landscape;
                margin: 8mm;
            }}

            [data-testid="stSidebar"] {{
                display: none !important;
            }}

            header[data-testid="stHeader"] {{
                display: none !important;
            }}

            .main .block-container {{
                max-width: 100% !important;
                padding: 0 !important;
            }}

            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}

            .kpi-card, .tabela-container, .movement-card, .chart-container {{
                break-inside: avoid;
            }}

            .dashboard-header {{
                margin-bottom: 8px;
            }}

            .kpi-card {{
                min-height: 82px;
            }}

            .tabela-financeira th {{
                padding: 6px 7px;
            }}

            .tabela-financeira td {{
                padding: 5px 7px;
            }}

            .dashboard-footer {{
                margin-top: 5px;
            }}
        }}

        @media (max-width: 900px) {{
            .dashboard-header {{
                grid-template-columns: 1fr;
                gap: 8px;
            }}

            .header-center {{
                order: -1;
                padding: 0;
            }}

            .header-period, .update-wrapper {{
                text-align: left;
                justify-content: flex-start;
            }}

            .kpi-value {{
                font-size: 19px;
            }}
        }}
    </style>
    """


# ============================================================================
# FUNÇÕES DE FORMATAÇÃO
# ============================================================================

def limpa_valor_bruto(valor):
    """
    Converte valores brutos (strings, floats, series) para float limpo.
    Trata parênteses como negativos, R$, pontos e vírgulas.
    """
    try:
        if isinstance(valor, pd.Series):
            valor = valor.iloc[0] if not valor.empty else 0.0

        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan", "NaN", "None"]:
            return 0.0

        if isinstance(valor, (int, float)):
            return float(valor)

        v_str = str(valor).strip()
        # Converte (valor) para -valor
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        v_str = v_str.replace('R$', '').strip()

        # Trata separadores decimais
        if '.' in v_str and ',' in v_str:
            v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')

        return float(v_str)
    except Exception:
        return 0.0


def formatar_moeda(valor):
    """Formata valor como moeda brasileira (R$ X.XXX,XX)."""
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
    """Formata valor com abreviação (M = milhões, K = milhares)."""
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
    """Formata valor de transferência com + ou - prefixo."""
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


# ============================================================================
# FUNÇÕES DE BUSCA E MATCHING
# ============================================================================

def normalizar_texto(txt):
    """Normaliza texto removendo acentos e convertendo para minúsculas."""
    if pd.isna(txt) or txt is None:
        return ""
    return (
        unicodedata.normalize('NFKD', str(txt))
        .encode('ASCII', 'ignore')
        .decode('utf-8')
        .lower()
    )


def criar_dicionario_contas(df_cadastro):
    """Cria dicionário de contas a partir do cadastro de fornecedores."""
    dicionario = {}
    try:
        if df_cadastro.empty:
            return dicionario
        
        col_razao = df_cadastro.columns[1]
        col_conta = df_cadastro.columns[2]

        for _, row in df_cadastro.iterrows():
            razao = str(row[col_razao]).strip().upper()
            conta = str(row[col_conta]).strip()
            if razao not in ['NAN', '']:
                dicionario[razao] = conta
    except Exception as e:
        print(f"Erro ao criar dicionário de contas: {e}")
    
    return dicionario


def achar_conta_fuzzy(lancamento, dicionario_contas):
    """Encontra conta usando match fuzzy no dicionário de fornecedores."""
    if not dicionario_contas:
        return "Não Mapeado"

    lanc = str(lancamento).upper()
    nome_extrato = lanc

    # Extrai nome após /
    match = re.search(r'/\s*([^)]+)', lanc)
    if match:
        nome_extrato = match.group(1).strip()

    # Remove lixo comum
    lixos = [' LTDA', ' S.A.', ' S.A', ' S/A', ' COMERCIO', 
             ' COM.', ' DE ', ' PRODUTOS', ' PROD.', ' HOSPITALARES', ' HOSP.']
    for lixo in lixos:
        nome_extrato = nome_extrato.replace(lixo, '')

    nome_extrato = nome_extrato.strip()

    # Prepara chaves para matching
    chaves_cadastro = list(dicionario_contas.keys())
    chaves_limpas = []
    for chave in chaves_cadastro:
        chave_tmp = chave
        for lixo in lixos:
            chave_tmp = chave_tmp.replace(lixo, '')
        chaves_limpas.append(chave_tmp.strip())

    # Busca match fuzzy
    matches = difflib.get_close_matches(
        nome_extrato, chaves_limpas, n=1, cutoff=0.4
    )

    if matches:
        idx_match = chaves_limpas.index(matches[0])
        chave_original = chaves_cadastro[idx_match]
        return dicionario_contas[chave_original]

    return "Não Mapeado"


# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================

@st.cache_data(ttl=60)
def carregar_dados(data_inicio, data_fim):
    """Carrega e processa todos os dados do Google Sheets."""
    
    conectar_sheets = load_database()
    if not conectar_sheets:
        return criar_resposta_vazia(data_inicio, data_fim)

    try:
        conn = conectar_sheets()
        if conn is None:
            return criar_resposta_vazia(data_inicio, data_fim)

        # Carrega dados de cada aba
        df_saldo_inicial = carregar_saldo_inicial(conn)
        dicionario_contas = carregar_cadastro_fornecedores(conn)
        df_extratos = carregar_extratos(conn, data_inicio, data_fim)
        df_fim_mes = processar_consolidacao(df_saldo_inicial, df_extratos)
        df_graficos = processar_grafico_diario(df_fim_mes, df_extratos)
        df_aplicacoes = carregar_aplicacoes(conn)

        # Calcula KPIs
        entradas = df_extratos['Cred_Op'].sum() if df_extratos is not None else 0.0
        saidas = df_extratos['Deb_Op'].sum() if df_extratos is not None else 0.0
        saldo_app = df_aplicacoes[proxima_col_valor(df_aplicacoes, 'atual')].sum() if not df_aplicacoes.empty else 0.0

        return (df_fim_mes, df_graficos, df_aplicacoes, saldo_app, 
                'Conta Bancária', entradas, saidas, data_inicio, data_fim)

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return criar_resposta_vazia(data_inicio, data_fim)


def criar_resposta_vazia(data_inicio, data_fim):
    """Retorna estrutura vazia quando há erro."""
    return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 
            'Conta Bancária', 0.0, 0.0, data_inicio, data_fim)


def carregar_saldo_inicial(conn):
    """Carrega dados da aba Saldo_Inicial."""
    df_si = pd.DataFrame(columns=['Conta Bancária', 'Saldo Inicial', 'Conta Garantida'])
    try:
        df = conn.read(worksheet="Saldo_Inicial", ttl=0)
        if not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]

            col_conta = next((c for c in df.columns 
                            if 'banco' in c.lower() or 'conta' in c.lower()), df.columns[0])
            col_valor = next((c for c in df.columns 
                            if 'saldo' in c.lower() or 'inicial' in c.lower() or 'valor' in c.lower()),
                           df.columns[1] if len(df.columns) > 1 else df.columns[0])
            col_garantida = next((c for c in df.columns if 'garantida' in c.lower() or 'limite' in c.lower()), None)

            df[col_valor] = df[col_valor].apply(limpa_valor_bruto)
            cols = [col_conta, col_valor]
            new_cols = ['Conta Bancária', 'Saldo Inicial']

            if col_garantida:
                df[col_garantida] = df[col_garantida].apply(limpa_valor_bruto)
                cols.append(col_garantida)
                new_cols.append('Conta Garantida')

            df_si = df[cols].copy()
            df_si.columns = new_cols
            if 'Conta Garantida' not in df_si.columns:
                df_si['Conta Garantida'] = 0.0
    except Exception as e:
        print(f"Aviso ao ler Saldo_Inicial: {e}")
    
    return df_si


def carregar_cadastro_fornecedores(conn):
    """Carrega cadastro de fornecedores."""
    try:
        df_cad = conn.read(worksheet="Cadastro Fornecedores", ttl=0)
        return criar_dicionario_contas(df_cad) if not df_cad.empty else {}
    except Exception as e:
        print(f"Erro ao ler Cadastro: {e}")
        return {}


def carregar_extratos(conn, data_inicio, data_fim):
    """Carrega extratos bancários."""
    try:
        df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
        if df_ext.empty:
            return None

        while len(df_ext.columns) < 8:
            df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""

        df_ext = df_ext.iloc[:, [0, 1, 4, 5, 7]].copy()
        df_ext.columns = ['Conta Bancária', 'Data', 'Vl Débito', 'Vl Crédito', 'Tipo de Transação']

        df_ext['Data'] = pd.to_datetime(df_ext['Data'], dayfirst=True, errors='coerce').dt.normalize()

        # Filtra por período
        dt_ini_pd = pd.to_datetime(data_inicio)
        dt_fim_pd = pd.to_datetime(data_fim)
        df_ext = df_ext[(df_ext['Data'] >= dt_ini_pd) & (df_ext['Data'] <= dt_fim_pd)].copy()

        # Limpa valores
        df_ext['Vl Crédito'] = df_ext['Vl Crédito'].apply(limpa_valor_bruto)
        df_ext['Vl Débito'] = df_ext['Vl Débito'].apply(limpa_valor_bruto)
        df_ext['Conta Bancária'] = df_ext['Conta Bancária'].astype(str).str.strip()

        # Classifica transações
        serie_tipo = df_ext['Tipo de Transação'].apply(normalizar_texto)
        df_ext['É Transf'] = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')

        df_ext['Cred_Op'] = df_ext['Vl Crédito'].where(~df_ext['É Transf'], 0.0)
        df_ext['Deb_Op'] = df_ext['Vl Débito'].where(~df_ext['É Transf'], 0.0)
        df_ext['Cred_Tr'] = df_ext['Vl Crédito'].where(df_ext['É Transf'], 0.0)
        df_ext['Deb_Tr'] = df_ext['Vl Débito'].where(df_ext['É Transf'], 0.0)

        return df_ext
    except Exception as e:
        print(f"Aviso ao ler extratos: {e}")
        return None


def processar_consolidacao(df_saldo_inicial, df_extratos):
    """Processa consolidação de bancos com extratos."""
    df_fim_mes = df_saldo_inicial.copy()

    if df_extratos is not None and not df_extratos.empty:
        df_grouped = df_extratos.groupby('Conta Bancária')[
            ['Cred_Op', 'Deb_Op', 'Cred_Tr', 'Deb_Tr']
        ].sum().reset_index()

        df_fim_mes = df_fim_mes.merge(df_grouped, on='Conta Bancária', how='outer')
        
        for col in ['Saldo Inicial', 'Conta Garantida', 'Cred_Op', 'Deb_Op', 'Cred_Tr', 'Deb_Tr']:
            if col in df_fim_mes.columns:
                df_fim_mes[col] = df_fim_mes[col].fillna(0)
    else:
        for col in ['Cred_Op', 'Deb_Op', 'Cred_Tr', 'Deb_Tr']:
            df_fim_mes[col] = 0.0

    # Renomeia colunas de entrada/saída
    df_fim_mes['Entrada Op'] = df_fim_mes.get('Cred_Op', 0.0)
    df_fim_mes['Saída Op'] = df_fim_mes.get('Deb_Op', 0.0)
    df_fim_mes['Entrada Tr'] = df_fim_mes.get('Cred_Tr', 0.0)
    df_fim_mes['Saída Tr'] = df_fim_mes.get('Deb_Tr', 0.0)

    # Define tipo de conta
    df_fim_mes['Tipo'] = df_fim_mes['Conta Bancária'].apply(
        lambda x: 'Limite' if 'getnet' in str(x).lower() else 
                  ('Aplicação' if any(t in str(x).lower() for t in ['aplicação', 'investimentos']) else 'Disponível')
    )

    # Calcula saldo final
    df_fim_mes['Saldo Final'] = (
        df_fim_mes['Saldo Inicial'] +
        df_fim_mes['Entrada Op'] -
        df_fim_mes['Saída Op'] +
        df_fim_mes['Entrada Tr'] -
        df_fim_mes['Saída Tr']
    )

    return df_fim_mes


def processar_grafico_diario(df_fim_mes, df_extratos):
    """Processa dados para gráfico de evolução diária."""
    if df_extratos is None or df_extratos.empty:
        return pd.DataFrame(columns=['Data', 'Entrada', 'Saída', 'Movimentação Líquida', 'Saldo Final', 'Data_Label'])

    saldo_inicial = df_fim_mes[
        df_fim_mes['Tipo'].isin(['Disponível', 'Aplicação'])
    ]['Saldo Inicial'].sum()

    df_diario = df_extratos.groupby('Data')[
        ['Cred_Op', 'Deb_Op', 'Cred_Tr', 'Deb_Tr']
    ].sum().reset_index().sort_values('Data')

    df_diario['Entrada'] = df_diario['Cred_Op'].fillna(0)
    df_diario['Saída'] = df_diario['Deb_Op'].fillna(0)
    df_diario['Movimentação Líquida'] = (
        (df_diario['Cred_Op'] + df_diario['Cred_Tr']) -
        (df_diario['Deb_Op'] + df_diario['Deb_Tr'])
    ).fillna(0)
    df_diario['Saldo Final'] = saldo_inicial + df_diario['Movimentação Líquida'].cumsum()
    df_diario['Data_Label'] = df_diario['Data'].dt.strftime('%d/%m')

    return df_diario


def proxima_col_valor(df, palavras_chave):
    """Localiza próxima coluna que contém as palavras-chave."""
    for c in df.columns:
        if any(kw in c.lower() for kw in (palavras_chave if isinstance(palavras_chave, list) else [palavras_chave])):
            return c
    return None


def carregar_aplicacoes(conn):
    """Carrega dados de aplicações."""
    df_app = pd.DataFrame()
    try:
        df = conn.read(worksheet="Aplicações", ttl=0)
        if not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            col_banco = df.columns[0]
            for c in df.columns:
                if 'banco' in c.lower() or 'conta' in c.lower():
                    col_banco = c
                    break

            df = df[df[col_banco].notna() & (df[col_banco].astype(str).str.strip() != '')]
            df = df[~df[col_banco].astype(str).str.lower().str.contains('total')]

            # Limpa valores numéricos
            for c in df.columns:
                if any(kw in c.lower() for kw in ['inicial', 'aplicaç', 'aplicac', 'imposto', 'rendimento', 'resgate', 'atual', 'final']):
                    df[c] = df[c].apply(limpa_valor_bruto)

            df_app = df
    except Exception as e:
        print(f"Erro ao ler Aplicações: {e}")
    
    return df_app


# ============================================================================
# GRÁFICOS PLOTLY
# ============================================================================

def criar_grafico_donut(saldo_aplicado, saldo_disponivel):
    """Cria gráfico donut de distribuição do caixa."""
    saldo_total = saldo_aplicado + saldo_disponivel
    
    fig = go.Figure(data=[
        go.Pie(
            values=[saldo_aplicado, saldo_disponivel],
            labels=['Aplicado', 'Disponível'],
            hole=0.68,
            marker=dict(
                colors=['#5d66a8', '#157a5b'],
                line=dict(color='#ffffff', width=2)
            ),
            textinfo='percent',
            texttemplate='%{percent:.1%}',
            textfont=dict(size=10, color='#26313c'),
            hoverinfo='label+percent'
        )
    ])

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.04,
            xanchor="center", x=0.5, font=dict(size=9), bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(t=8, b=25, l=0, r=0),
        height=285,
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        annotations=[dict(
            text=f"<b>R$ {saldo_total/1000000:,.1f}M</b><br>"
                 f"<span style='font-size:10px'>Saldo Total</span>",
            x=0.5, y=0.5,
            font=dict(size=14, color='#17212b'),
            showarrow=False
        )]
    )
    return fig


def criar_grafico_evolucao(df_graficos):
    """Cria gráfico de evolução diária do saldo."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_graficos['Data_Label'],
        y=df_graficos['Saldo Final'],
        name='Saldo Total',
        marker_color='#315d8c',
        marker_line_width=0,
        text=[formatar_abreviado(v) for v in df_graficos['Saldo Final']],
        textposition='outside',
        textfont=dict(size=10, color='#26313c'),
        opacity=0.92,
        width=0.55
    ))

    fig.update_layout(
        margin=dict(t=25, b=12, l=5, r=5),
        height=205,
        xaxis=dict(
            tickfont=dict(size=9), showgrid=False,
            linecolor='#dfe4ea', linewidth=1, showline=True
        ),
        yaxis=dict(
            showticklabels=False, showgrid=True,
            gridcolor='#edf0f3', zeroline=False
        ),
        showlegend=False,
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        hovermode='x unified'
    )
    return fig


# ============================================================================
# RENDERIZAÇÃO HTML (COMPONENTES)
# ============================================================================

def render_header(periodo_str, data_hoje):
    """Renderiza cabeçalho do dashboard."""
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="header-period">
            <div class="date">{periodo_str}</div>
            <div class="label">Período Selecionado</div>
        </div>
        <div class="header-center">
            <h1>PAINEL FINANCEIRO MENSAL</h1>
            <p>Controle Consolidado de Bancos</p>
        </div>
        <div class="update-wrapper">
            <div class="update-badge">
                <span>Atualização</span>
                <b>{data_hoje}</b>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpis(saldo_total, saldo_disponivel, saldo_aplicado, limites_totais):
    """Renderiza cards de KPI."""
    kpi_row = st.columns(4)
    kpis = [
        (kpi_row[0], "SALDO TOTAL", f"R$ {saldo_total:,.2f}", "total"),
        (kpi_row[1], "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "disponivel"),
        (kpi_row[2], "APLICAÇÕES", f"R$ {saldo_aplicado:,.2f}", "aplicacoes"),
        (kpi_row[3], "LIMITES TOTAIS", f"R$ {limites_totais:,.2f}", "limites"),
    ]

    for col, title, val, color in kpis:
        col.markdown(f"""
        <div class="kpi-card {color}">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-foot">Valores em Reais (R$)</div>
        </div>
        """, unsafe_allow_html=True)


def render_movimentacao(entradas_mes, saidas_mes, resultado_liquido_mes):
    """Renderiza seção de movimentação operacional."""
    m1, m2, m3 = st.columns(3)

    cor_resultado = "#157a5b" if resultado_liquido_mes >= 0 else "#b74242"

    m1.markdown(f"""
    <div class="movement-card">
        <div class="movement-label" style="color:#157a5b;">ENTRADAS</div>
        <div class="movement-value">R$ {entradas_mes:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    m2.markdown(f"""
    <div class="movement-card">
        <div class="movement-label" style="color:#b74242;">SAÍDAS</div>
        <div class="movement-value">R$ {saidas_mes:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    m3.markdown(f"""
    <div class="movement-card">
        <div class="movement-label" style="color:{cor_resultado};">RESULTADO LÍQUIDO</div>
        <div class="movement-value" style="color:{cor_resultado};">R$ {resultado_liquido_mes:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)


def render_tabela_bancos(df_consolidado, df_view, dt_ini_short, dt_fim_short):
    """Renderiza tabela principal de bancos."""
    html = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr>'
    html += '<th class="centro">#</th>'
    html += f'<th>Conta Bancária</th>'
    html += '<th class="centro">TIPO</th>'
    html += f'<th class="valores">SALDO INICIAL {dt_ini_short}</th>'
    html += '<th class="valores">ENTRADA (OP.)</th>'
    html += '<th class="valores">SAÍDA (OP.)</th>'
    html += '<th class="valores">ENTRADA (INT.)</th>'
    html += '<th class="valores">SAÍDA (INT.)</th>'
    html += f'<th class="valores">SALDO ATUAL {dt_fim_short}</th>'
    html += '</tr></thead><tbody>'

    df_bancos = df_view[df_view['Tipo'] != 'Limite']
    df_getnet = df_view[df_view['Tipo'] == 'Limite']

    totais = {
        col: df_bancos[col].sum()
        for col in ['Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final']
    }

    for idx, row in enumerate(df_bancos.itertuples()):
        cor_transf = "#6b7785" if row._6 == 0 else "#2f657a"
        cor_transf_saida = "#6b7785" if row._7 == 0 else "#b74242"
        
        html += f"""<tr>
            <td class="centro">{idx + 1}</td>
            <td style="font-weight:700;color:#34404c;">{row._2}</td>
            <td class="centro" style="font-size:9px;font-weight:800;color:#5b6672;">{row.Tipo}</td>
            <td class="valores">{formatar_moeda(row._3)}</td>
            <td class="valores">{formatar_moeda(row._4)}</td>
            <td class="valores">{formatar_moeda(row._5)}</td>
            <td class="valores" style="color:{cor_transf};">{formatar_moeda(row._6)}</td>
            <td class="valores" style="color:{cor_transf_saida};">{formatar_moeda(row._7)}</td>
            <td class="valores valor-destaque">{formatar_moeda(row._8)}</td>
        </tr>"""

    # Linha total
    html += f"""<tr class="linha-total">
        <td></td><td>TOTAL</td><td></td>
        <td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td>
        <td class="valores">{formatar_moeda(totais["Entrada Op"])}</td>
        <td class="valores">{formatar_moeda(totais["Saída Op"])}</td>
        <td class="valores" style="color:#6b7785;">-</td>
        <td class="valores" style="color:#6b7785;">-</td>
        <td class="valores valor-destaque">{formatar_moeda(totais["Saldo Final"])}</td>
    </tr>"""

    # Limites/Getnet
    if not df_getnet.empty:
        for idx, row in enumerate(df_getnet.itertuples()):
            idx_display = len(df_bancos) + idx + 1
            cor_transf = "#6b7785" if row._6 == 0 else "#2f657a"
            cor_transf_saida = "#6b7785" if row._7 == 0 else "#b74242"
            
            html += f"""<tr class="linha-limite">
                <td class="centro">{idx_display}</td>
                <td style="font-weight:800;">{row._2}</td>
                <td class="centro" style="font-size:9px;font-weight:800;color:#996b10;">{row.Tipo}</td>
                <td class="valores">{formatar_moeda(row._3)}</td>
                <td class="valores">{formatar_moeda(row._4)}</td>
                <td class="valores">{formatar_moeda(row._5)}</td>
                <td class="valores" style="color:{cor_transf};">{formatar_moeda(row._6)}</td>
                <td class="valores" style="color:{cor_transf_saida};">{formatar_moeda(row._7)}</td>
                <td class="valores valor-destaque">{formatar_moeda(row._8)}</td>
            </tr>"""

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)


def render_rodape(data_hoje):
    """Renderiza rodapé."""
    st.markdown(f"""
    <div class="dashboard-footer">
        Valores em Reais (R$) | Dados atualizados em {data_hoje}
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Função principal do dashboard."""
    configure_page()
    st.markdown(get_css_styles(), unsafe_allow_html=True)

    # Sidebar com filtros
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
            "Para gerar um relatório, utilize a impressão do navegador em **Paisagem** "
            "e desative cabeçalhos/rodapés.",
            icon="ℹ️"
        )

        components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }"
            style="width:100%;background:#234a78;color:white;border:1px solid #193754;
                   padding:11px;border-radius:4px;font-family:'Segoe UI',Arial,sans-serif;
                   font-weight:700;font-size:13px;cursor:pointer;">
            Salvar Dashboard (PDF)
        </button>
        """, height=50)

    # Processa datas
    if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
        data_inicio_filtro, data_fim_filtro = data_selecionada
    else:
        data_inicio_filtro = data_selecionada[0] if isinstance(data_selecionada, tuple) else data_selecionada
        data_fim_filtro = data_inicio_filtro

    # Carrega dados
    (df_consolidado, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi,
     col_conta, entradas_operacionais, saidas_operacionais,
     data_ini_painel, data_fim_painel) = carregar_dados(data_inicio_filtro, data_fim_filtro)

    if df_consolidado.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return

    # Calcula KPIs
    saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()
    saldo_getnet = df_consolidado[df_consolidado['Tipo'] == 'Limite']['Saldo Final'].sum()
    saldo_conta_garantida = df_consolidado['Conta Garantida'].sum()
    limites_totais = saldo_getnet + saldo_conta_garantida
    saldo_total = saldo_disponivel + saldo_aplicado_kpi
    resultado_liquido_mes = entradas_operacionais - saidas_operacionais

    # Variáveis para exibição
    data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
    periodo_str = f"{data_ini_painel.strftime('%d/%m/%Y')} - {data_fim_painel.strftime('%d/%m/%Y')}"
    dt_ini_short = data_ini_painel.strftime('%d/%m')
    dt_fim_short = data_fim_painel.strftime('%d/%m')

    # Gráficos
    fig_donut = criar_grafico_donut(saldo_aplicado_kpi, saldo_disponivel)
    fig_evolucao = criar_grafico_evolucao(df_graficos) if not df_graficos.empty else None

    # Renderização
    render_header(periodo_str, data_hoje)
    render_kpis(saldo_total, saldo_disponivel, saldo_aplicado_kpi, limites_totais)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([0.85, 1.25, 1.6])

    # Distribuição do caixa
    with c1:
        st.markdown('<div class="section-title">DISTRIBUIÇÃO DO CAIXA</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Movimentação operacional
    with c2:
        st.markdown(f'<div class="section-title">MOVIMENTAÇÃO OPERACIONAL<span class="section-ref">REF.: {periodo_str}</span></div>', 
                   unsafe_allow_html=True)
        render_movimentacao(entradas_operacionais, saidas_operacionais, resultado_liquido_mes)
        
        st.markdown('<div class="section-title" style="margin-top:10px;">EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>', 
                   unsafe_allow_html=True)
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        if fig_evolucao:
            st.plotly_chart(fig_evolucao, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Aplicações (resumo simplificado)
    with c3:
        st.markdown(f'<div class="section-title">RESUMO APLICAÇÕES<span class="section-ref">REF.: {periodo_str}</span></div>', 
                   unsafe_allow_html=True)
        if not df_aplicacoes_nova.empty:
            st.dataframe(df_aplicacoes_nova, use_container_width=True)
        else:
            st.info("Nenhuma aplicação encontrada.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Tabelas inferiores
    col_tab, col_diario = st.columns([1.6, 1])

    with col_tab:
        st.markdown('<div class="section-title">SALDO DE TODOS OS BANCOS</div>', unsafe_allow_html=True)
        df_view = df_consolidado[['Tipo', col_conta, 'Saldo Inicial', 'Entrada Op', 'Saída Op', 
                                  'Entrada Tr', 'Saída Tr', 'Saldo Final']].copy()
        render_tabela_bancos(df_consolidado, df_view, dt_ini_short, dt_fim_short)

    with col_diario:
        st.markdown('<div class="section-title">SALDO DIÁRIO CONSOLIDADO</div>', unsafe_allow_html=True)
        if not df_graficos.empty:
            st.dataframe(df_graficos[['Data_Label', 'Saldo Final', 'Entrada', 'Saída']], use_container_width=True)

    render_rodape(data_hoje)


if __name__ == "__main__":
    main()
