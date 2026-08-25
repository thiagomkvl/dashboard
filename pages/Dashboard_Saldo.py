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
st.set_page_config(page_title="Painel Financeiro Mensal", layout="wide", page_icon="📊", initial_sidebar_state="expanded")

# ==============================================================================
# PALETA CORPORATIVA (FONTE ÚNICA DE VERDADE PARA CORES)
# ==============================================================================
COR_PRIMARIA   = "#17395C"   # Azul-marinho institucional
COR_SECUNDARIA = "#3E6B96"   # Azul-aço (apoio)
COR_SUCESSO    = "#12805C"   # Verde sobrio
COR_ERRO       = "#B42318"   # Vermelho institucional
COR_ALERTA     = "#B54708"   # Âmbar (limites)
COR_NEUTRO     = "#98A2B3"   # Cinza neutro
COR_TEXTO      = "#101828"

FONTE_GRAFICOS = "Inter, Segoe UI, Arial, sans-serif"

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    /* =========================================================
       IDENTIDADE VISUAL CORPORATIVA E LAYOUT
       ========================================================= */
    :root {
        --bg: #f4f6f9;
        --surface: #ffffff;
        --surface-soft: #f9fafc;
        --border: #e3e8ef;
        --border-strong: #d0d7e2;
        --text: #101828;
        --muted: #667085;
        --primary: #17395C;
        --success: #12805C;
        --danger: #B42318;
        --warning: #B54708;
        --shadow: 0 1px 3px rgba(16, 24, 40, 0.07);
    }

    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .main { background: var(--bg); }
    .main .block-container { padding-top: 1rem; padding-bottom: 0.8rem; max-width: 97%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.38rem !important; }
    .stPlotlyChart { background: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }

    /* ---------- Cabeçalho ---------- */
    .dashboard-header {
        display: flex; justify-content: space-between; align-items: center;
        min-height: 68px; padding: 10px 6px; margin-bottom: 12px;
        border-bottom: 2px solid var(--primary);
    }
    .header-period { min-width: 220px; }
    .header-period .label { font-size: 9.5px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; }
    .header-period .date { margin-top: 3px; font-size: 17px; font-weight: 700; color: var(--text); letter-spacing: -0.2px; font-variant-numeric: tabular-nums; }
    .header-center { text-align: center; }
    .header-center h1 { margin: 0; color: var(--primary); font-size: 21px; line-height: 1.2; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase; }
    .header-center p { margin: 4px 0 0; color: var(--muted); font-size: 10.5px; font-weight: 500; letter-spacing: 0.4px; }
    .update-badge { min-width: 150px; padding: 8px 14px; text-align: center; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); }
    .update-badge span { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: var(--muted); }
    .update-badge b { display: block; margin-top: 3px; font-size: 12px; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }

    /* ---------- KPIs (cartões claros com régua superior de cor) ---------- */
    .kpi-card {
        position: relative; overflow: hidden; min-height: 92px;
        padding: 14px 18px 13px; border-radius: 8px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 3px solid var(--primary);
        box-shadow: var(--shadow); text-align: left;
    }
    .kpi-card.disponivel { border-top-color: var(--success); }
    .kpi-card.aplicacoes { border-top-color: var(--secondary, #3E6B96); border-top-color: #3E6B96; }
    .kpi-card.limites    { border-top-color: var(--warning); }

    .kpi-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .kpi-title { font-size: 10px; line-height: 1; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
    .kpi-icon { display: inline-flex; align-items: center; justify-content: center; color: var(--primary); opacity: 0.85; }
    .kpi-card.disponivel .kpi-icon { color: var(--success); }
    .kpi-card.aplicacoes .kpi-icon { color: #3E6B96; }
    .kpi-card.limites    .kpi-icon { color: var(--warning); }
    .kpi-value { font-size: 23px; line-height: 1.1; font-weight: 700; color: var(--text); letter-spacing: -0.3px; white-space: nowrap; font-variant-numeric: tabular-nums; }

    /* ---------- Seções ---------- */
    .section-title { display: flex; align-items: center; min-height: 25px; margin-bottom: 6px; padding: 0 0 5px; border-bottom: 1px solid var(--border-strong); color: var(--text); font-size: 11.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.75px; }
    .section-title::before { content: ""; width: 3px; height: 12px; margin-right: 8px; border-radius: 1px; background: var(--primary); }
    .section-ref { margin-left: auto; font-size: 10px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; font-variant-numeric: tabular-nums; }
    .movement-card { padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); box-shadow: var(--shadow); }
    .movement-label { display: flex; align-items: center; font-size: 9.5px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.55px; }
    .dot { width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; display: inline-block; }
    .movement-value { margin-top: 5px; font-size: 18px; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; letter-spacing: -0.2px; }

    /* ---------- Tabelas (padrão contábil: texto à esquerda, valores à direita) ---------- */
    .tabela-container { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); box-shadow: var(--shadow); font-size: 12px; width: 100%; margin-bottom: 8px; }
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; }
    .tabela-financeira th { background: #f4f6fa; color: #475467; font-size: 9.5px; font-weight: 800; text-align: left; padding: 10px 10px; border-bottom: 1px solid var(--border-strong); text-transform: uppercase; letter-spacing: 0.45px; white-space: nowrap; }
    .tabela-financeira td { padding: 9px 10px; border-bottom: 1px solid #eef1f6; font-size: 13px; font-weight: 500; color: #1d2939; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #f8fafc; }
    .tabela-financeira .linha-total { background: #eef2f7; }
    .tabela-financeira .linha-total td { border-top: 2px solid var(--border-strong); border-bottom: 3px double var(--primary); color: var(--text); font-weight: 800; }
    .tabela-financeira .subheader-row td { background: #fafbfd; color: var(--muted); font-size: 9.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.55px; padding: 7px 10px; border-bottom: 1px solid var(--border); }

    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: right !important; font-variant-numeric: tabular-nums; }
    .tabela-financeira th.valores { font-weight: 800; }
    .tabela-financeira td.valores { font-weight: 600; font-size: 13.5px; }
    .tabela-financeira td.valor-destaque { font-size: 15px !important; font-weight: 800; color: var(--text); }

    hr { border: 0 !important; border-top: 1px solid var(--border) !important; margin: 15px 0 !important; }

    /* =========================================================
       MODO IMPRESSÃO (PDF DE ALTA QUALIDADE VETORIAL)
       ========================================================= */
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }

        .main .block-container { max-width: 100% !important; padding: 10px !important; }

        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            color-adjust: exact !important;
        }

        .kpi-card, .tabela-container, .movement-card { break-inside: avoid; }
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 0. CONFIGURAÇÃO DA BARRA LATERAL (FILTROS)
# ==============================================================================
hoje = datetime.now().date()
primeiro_dia_mes = hoje.replace(day=1)

with st.sidebar:
    st.markdown("### Parâmetros do Relatório")

    data_selecionada = st.date_input(
        "Selecione o Período:",
        value=(primeiro_dia_mes, hoje),
        min_value=datetime(2020, 1, 1).date(),
        max_value=hoje,
        format="DD/MM/YYYY"
    )

    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    st.markdown("### Exportação")
    st.info("Para gerar o PDF em alta qualidade, utilize a orientação **Paisagem** e desmarque a opção 'Cabeçalhos e rodapés'.", icon="ℹ️")

    components.html(f"""
        <button onclick="try {{ window.parent.print(); }} catch(e) {{ window.print(); }}"
        style="width:100%; background:{COR_PRIMARIA}; color:#ffffff; border:none; padding:11px; border-radius:6px;
               font-family:'Inter','Segoe UI',Arial,sans-serif; font-weight:600; font-size:13px; letter-spacing:0.3px;
               cursor:pointer; transition: background 0.2s;"
        onmouseover="this.style.background='#122D49'" onmouseout="this.style.background='{COR_PRIMARIA}'">
        Exportar Painel (PDF)
        </button>
    """, height=50)

# Validação segura para garantir que o usuário escolheu duas datas no calendário
if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
    data_inicio_filtro, data_fim_filtro = data_selecionada
else:
    data_inicio_filtro = data_selecionada[0] if isinstance(data_selecionada, tuple) else data_selecionada
    data_fim_filtro = data_inicio_filtro

# ==============================================================================
# 1. FUNÇÕES DE FORMATAÇÃO E LIMPEZA
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
    """Formata valores de tabelas. Zero é exibido como '-' (padrão contábil)."""
    try:
        val = float(valor)
        if val == 0: return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "-"

def formatar_brl(valor):
    """Formata sempre com R$, incluindo zero e negativos (KPIs e cartões)."""
    try:
        val = float(valor)
        sinal = "-" if val < 0 else ""
        return f"{sinal}R$ {abs(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "R$ 0,00"

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

# Ícones vetoriais monocromáticos (substituem emojis nos KPIs)
ICONES_SVG = {
    "total": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18"/><path d="M5 21V10l7-6 7 6v11"/><path d="M9 21v-6h6v6"/><path d="M9 12h.01M15 12h.01"/></svg>',
    "disponivel": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="14" rx="2"/><path d="M2 10h20"/><circle cx="17" cy="15" r="1"/></svg>',
    "aplicacoes": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/></svg>',
    "limites": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
}

# ==============================================================================
# 2. CARGA DE DADOS (BASE ZERO + TIMELINE COM MAPEAMENTO POSICIONAL)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados(data_inicio, data_fim):
    conn = conectar_sheets()

    if conn is None:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim
    try:
        # =========================================================
        # 1. ABA SALDO_INICIAL
        # =========================================================
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

        # =========================================================
        # LEITURA DO CADASTRO E MOTOR DE MATCH DA CONTA CONTÁBIL
        # =========================================================
        dicionario_contas = {}
        try:
            df_cad = conn.read(worksheet="Cadastro Fornecedores", ttl=0)
            if not df_cad.empty:
                col_razao = df_cad.columns[1]
                col_conta = df_cad.columns[2]

                for _, row in df_cad.iterrows():
                    razao = str(row[col_razao]).strip().upper()
                    conta = str(row[col_conta]).strip()
                    if razao != 'NAN' and razao != '':
                        dicionario_contas[razao] = conta
        except Exception as e:
            print("Erro ao ler Cadastro de Fornecedores:", e)

        def achar_conta_fuzzy(lancamento):
            if not dicionario_contas:
                return "Não Mapeado"

            lanc = str(lancamento).upper()
            nome_extrato = lanc

            match = re.search(r'/\s*([^)]+)', lanc)
            if match:
                nome_extrato = match.group(1).strip()

            lixos = [' LTDA', ' S.A.', ' S.A', ' S/A', ' COMERCIO', ' COM.', ' DE ', ' PRODUTOS', ' PROD.', ' HOSPITALARES', ' HOSP.']
            for lixo in lixos:
                nome_extrato = nome_extrato.replace(lixo, '')
            nome_extrato = nome_extrato.strip()

            chaves_cadastro = list(dicionario_contas.keys())
            chaves_limpas = []
            for chave in chaves_cadastro:
                chave_tmp = chave
                for lixo in lixos:
                    chave_tmp = chave_tmp.replace(lixo, '')
                chaves_limpas.append(chave_tmp.strip())

            matches = difflib.get_close_matches(nome_extrato, chaves_limpas, n=1, cutoff=0.4)

            if matches:
                idx_match = chaves_limpas.index(matches[0])
                chave_original = chaves_cadastro[idx_match]
                return dicionario_contas[chave_original]

            return "Não Mapeado"

        # (Exemplo) Supondo que 'df_ext' seja a base do seu extrato e a descrição esteja na coluna 'Lançamento'
        # df_ext['Conta Contábil'] = df_ext['Lançamento'].apply(achar_conta_fuzzy)

        # =========================================================
        # 2. EXTRATOS (Com Aplicação do Filtro de Datas)
        # =========================================================
        df_extratos = None

        try:
            df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
            if not df_ext.empty:
                while len(df_ext.columns) < 8:
                    df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""

                df_ext = df_ext.iloc[:, [0, 1, 4, 5, 7]].copy()
                df_ext.columns = ['Conta Bancária', 'Data', 'Vl Débito', 'Vl Crédito', 'Tipo de Transação']

                df_ext['Data'] = pd.to_datetime(df_ext['Data'], dayfirst=True, errors='coerce').dt.normalize()

                dt_ini_pd = pd.to_datetime(data_inicio)
                dt_fim_pd = pd.to_datetime(data_fim)

                df_ext = df_ext[(df_ext['Data'] >= dt_ini_pd) & (df_ext['Data'] <= dt_fim_pd)].copy()

                df_ext['Vl Crédito'] = df_ext['Vl Crédito'].apply(limpa_valor_bruto)
                df_ext['Vl Débito'] = df_ext['Vl Débito'].apply(limpa_valor_bruto)
                df_ext['Conta Bancária'] = df_ext['Conta Bancária'].astype(str).str.strip()

                def normalizar_texto(txt):
                    if pd.isna(txt) or txt is None: return ""
                    return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower()

                serie_tipo = df_ext['Tipo de Transação'].apply(normalizar_texto)
                df_ext['É Transf'] = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')

                df_ext['Cred_Op'] = df_ext['Vl Crédito'].where(~df_ext['É Transf'], 0.0)
                df_ext['Deb_Op'] = df_ext['Vl Débito'].where(~df_ext['É Transf'], 0.0)
                df_ext['Cred_Tr'] = df_ext['Vl Crédito'].where(df_ext['É Transf'], 0.0)
                df_ext['Deb_Tr'] = df_ext['Vl Débito'].where(df_ext['É Transf'], 0.0)

                df_extratos = df_ext
        except Exception as e:
            print("Aviso ao ler extratos:", e)

        # =========================================================
        # 3. CONSTRUÇÃO DA TABELA FINAL DE BANCOS
        # =========================================================
        def definir_tipo(nome):
            if 'getnet' in str(nome).lower(): return 'Limite'
            return 'Aplicação' if ('aplicação' in str(nome).lower() or 'investimentos' in str(nome).lower()) else 'Disponível'

        df_fim_mes = df_saldo_inicial.copy()

        if df_extratos is not None and not df_extratos.empty:
            df_extratos_grouped = df_extratos.groupby('Conta Bancária').agg({
                'Cred_Op': 'sum',
                'Deb_Op': 'sum',
                'Cred_Tr': 'sum',
                'Deb_Tr': 'sum',
            }).reset_index()

            df_fim_mes = df_fim_mes.merge(df_extratos_grouped, on='Conta Bancária', how='outer')
            df_fim_mes['Saldo Inicial'] = df_fim_mes['Saldo Inicial'].fillna(0)
            df_fim_mes['Conta Garantida'] = df_fim_mes['Conta Garantida'].fillna(0)

            df_fim_mes['Entrada Op'] = df_fim_mes['Cred_Op'].fillna(0)
            df_fim_mes['Saída Op'] = df_fim_mes['Deb_Op'].fillna(0)
            df_fim_mes['Entrada Tr'] = df_fim_mes['Cred_Tr'].fillna(0)
            df_fim_mes['Saída Tr'] = df_fim_mes['Deb_Tr'].fillna(0)
        else:
            df_fim_mes['Entrada Op'] = 0.0
            df_fim_mes['Saída Op'] = 0.0
            df_fim_mes['Entrada Tr'] = 0.0
            df_fim_mes['Saída Tr'] = 0.0

        df_fim_mes['Tipo'] = df_fim_mes['Conta Bancária'].apply(definir_tipo)

        df_fim_mes['Saldo Final'] = df_fim_mes['Saldo Inicial'] + df_fim_mes['Entrada Op'] - df_fim_mes['Saída Op'] + df_fim_mes['Entrada Tr'] - df_fim_mes['Saída Tr']

        # =========================================================
        # 4. GRÁFICO DIÁRIO E EVOLUÇÃO (Caixa Real = Disponível + Aplicação)
        # =========================================================
        saldo_inicial_caixa = df_fim_mes[df_fim_mes['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()

        if df_extratos is not None and not df_extratos.empty:
            df_ext_caixa = df_extratos[df_extratos['Conta Bancária'].apply(definir_tipo).isin(['Disponível', 'Aplicação'])].copy()

            df_extratos_diario = df_ext_caixa.groupby('Data').agg({
                'Cred_Op': 'sum',
                'Deb_Op': 'sum',
                'Cred_Tr': 'sum',
                'Deb_Tr': 'sum'
            }).reset_index()

            df_graficos = df_extratos_diario.sort_values('Data').copy()

            df_graficos['Entrada'] = df_graficos['Cred_Op'].fillna(0)
            df_graficos['Saída'] = df_graficos['Deb_Op'].fillna(0)

            df_graficos['Movimentação Líquida'] = (df_graficos['Cred_Op'] + df_graficos['Cred_Tr']).fillna(0) - (df_graficos['Deb_Op'] + df_graficos['Deb_Tr']).fillna(0)
            df_graficos['Saldo Final'] = saldo_inicial_caixa + df_graficos['Movimentação Líquida'].cumsum()
        else:
            df_graficos = pd.DataFrame(columns=['Data', 'Entrada', 'Saída', 'Movimentação Líquida', 'Saldo Final'])

        if not df_graficos.empty:
            df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%d/%m')
        else:
            df_graficos['Data_Label'] = pd.Series(dtype='object')

        # =========================================================
        # 5. KPI OPERACIONAL LÍQUIDO
        # =========================================================
        entradas_operacionais = df_extratos['Cred_Op'].sum() if df_extratos is not None else 0.0
        saidas_operacionais = df_extratos['Deb_Op'].sum() if df_extratos is not None else 0.0

        # =========================================================
        # 6. LER A NOVA ABA DE APLICAÇÕES
        # =========================================================
        df_aplicacoes_nova = pd.DataFrame()
        saldo_aplicado_kpi = 0.0

        try:
            df_app = conn.read(worksheet="Aplicações", ttl=0)
            if not df_app.empty:
                df_app.columns = [str(c).strip() for c in df_app.columns]

                col_banco = df_app.columns[0]
                for c in df_app.columns:
                    if 'banco' in c.lower() or 'conta' in c.lower():
                        col_banco = c
                        break

                df_app = df_app[df_app[col_banco].notna() & (df_app[col_banco].astype(str).str.strip() != '')]
                df_app = df_app[~df_app[col_banco].astype(str).str.lower().str.contains('total')]

                def get_col(kws):
                    for c in df_app.columns:
                        if any(kw in c.lower() for kw in kws): return c
                    return None

                c_si = get_col(['inicial'])
                c_app = get_col(['aplicaç', 'aplicac'])
                c_imp = get_col(['imposto'])
                c_rend = get_col(['rendimento'])
                c_resg = get_col(['resgate'])
                c_atual = get_col(['atual', 'final'])

                cols_to_clean = [c for c in [c_si, c_app, c_imp, c_rend, c_resg, c_atual] if c]
                for c in cols_to_clean:
                    df_app[c] = df_app[c].apply(limpa_valor_bruto)

                df_aplicacoes_nova = df_app.copy()

                if c_atual:
                    saldo_aplicado_kpi = df_aplicacoes_nova[c_atual].sum()
        except Exception as e:
            print("Erro ao ler Aplicações:", e)

        return df_fim_mes, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, 'Conta Bancária', entradas_operacionais, saidas_operacionais, data_inicio, data_fim

    except Exception as e:
        st.error(f"Erro fatal ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim

# ==============================================================================
# CHAMADA PRINCIPAL
# ==============================================================================
df_consolidado, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, col_conta, entradas_operacionais, saidas_operacionais, data_ini_painel, data_fim_painel = carregar_dados(data_inicio_filtro, data_fim_filtro)
if not col_conta: col_conta = 'Conta Bancária'
if df_consolidado.empty: st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs MENSAIS
# ==============================================================================
saldo_aplicado = saldo_aplicado_kpi
saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()

# Limites
saldo_getnet = df_consolidado[df_consolidado['Tipo'] == 'Limite']['Saldo Final'].sum()
saldo_conta_garantida = df_consolidado['Conta Garantida'].sum()
limites_totais = saldo_getnet + saldo_conta_garantida

# Saldo Total REAL
saldo_total = saldo_disponivel + saldo_aplicado

entradas_mes = entradas_operacionais
saidas_mes = saidas_operacionais
resultado_liquido_mes = entradas_mes - saidas_mes

# ==============================================================================
# 4. GRÁFICOS E VARIÁVEIS DE DATA
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
periodo_str = f"{data_ini_painel.strftime('%d/%m/%Y')} – {data_fim_painel.strftime('%d/%m/%Y')}"

dt_ini_short = data_ini_painel.strftime('%d/%m')
dt_fim_short = data_fim_painel.strftime('%d/%m')

fig_donut = go.Figure(data=[go.Pie(
    values=[saldo_aplicado, saldo_disponivel],
    labels=['Aplicações', 'Disponível'],
    hole=0.62,
    marker=dict(colors=[COR_SECUNDARIA, COR_PRIMARIA], line=dict(color='#ffffff', width=2)),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    textfont=dict(size=11, color='#ffffff', family=FONTE_GRAFICOS),
    hoverinfo='label+percent',
    sort=False,
    direction='clockwise'
)])
fig_donut.update_layout(
    font=dict(family=FONTE_GRAFICOS),
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5, font=dict(size=10, color='#475467')),
    margin=dict(t=10, b=35, l=0, r=0), height=320,
    annotations=[
        dict(text=f"<b>R$ {saldo_total/1000000:,.1f}M</b>".replace('.', '@TEMP@').replace(',', '.').replace('@TEMP@', ','), x=0.5, y=0.52, font_size=15, font_color=COR_TEXTO, showarrow=False),
        dict(text="Saldo Total", x=0.5, y=0.42, font_size=9.5, font_color='#667085', showarrow=False)
    ],
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)

fig_combinado = go.Figure()
fig_combinado.add_trace(go.Bar(
    x=df_graficos['Data_Label'],
    y=df_graficos['Saldo Final'],
    name='Saldo Consolidado',
    marker_color=COR_PRIMARIA,
    text=[formatar_abreviado(v) for v in df_graficos['Saldo Final']],
    textposition='outside',
    textfont=dict(size=11, color="#344054", family=FONTE_GRAFICOS),
    cliponaxis=False,
    width=0.55
))
fig_combinado.update_layout(
    font=dict(family=FONTE_GRAFICOS),
    margin=dict(t=25, b=15, l=5, r=5), height=215,
    xaxis=dict(tickfont=dict(size=10, color='#475467'), showgrid=False),
    yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    barmode='overlay',
    showlegend=False,
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    hovermode='x unified',
    hoverlabel=dict(bgcolor='#ffffff', bordercolor='#e3e8ef', font=dict(color=COR_TEXTO, family=FONTE_GRAFICOS))
)

# ==============================================================================
# 5. MONTAGEM DO PAINEL
# ==============================================================================
st.markdown(f"""
<div class="dashboard-header">
    <div class="header-period">
        <div class="label">Período Analisado</div>
        <div class="date">{periodo_str}</div>
    </div>
    <div class="header-center">
        <h1>Painel Financeiro Mensal</h1>
        <p>Controle Consolidado de Contas Bancárias</p>
    </div>
    <div class="update-badge">
        <span>Atualizado em</span>
        <b>{data_hoje}</b>
    </div>
</div>
""", unsafe_allow_html=True)

kpi_row = st.columns(4)
kp_data = [
    (kpi_row[0], ICONES_SVG["total"],      "Saldo Total",      formatar_brl(saldo_total),      "total"),
    (kpi_row[1], ICONES_SVG["disponivel"], "Saldo Disponível", formatar_brl(saldo_disponivel), "disponivel"),
    (kpi_row[2], ICONES_SVG["aplicacoes"], "Aplicações",       formatar_brl(saldo_aplicado),   "aplicacoes"),
    (kpi_row[3], ICONES_SVG["limites"],    "Limites Totais",   formatar_brl(limites_totais),   "limites")
]
for col, icon, title, val, color in kp_data:
    col.markdown(
        f"<div class='kpi-card {color}'>"
        f"<div class='kpi-head'><span class='kpi-title'>{title}</span><span class='kpi-icon'>{icon}</span></div>"
        f"<div class='kpi-value'>{val}</div>"
        f"</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([0.85, 1.25, 1.6])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(f"<div class='section-title'>MOVIMENTAÇÃO OPERACIONAL <span class='section-ref'>Ref.: {periodo_str}</span></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div class='movement-card'><div class='movement-label'><span class='dot' style='background:{COR_SUCESSO};'></span>ENTRADAS</div><div class='movement-value' style='color:{COR_SUCESSO};'>{formatar_brl(entradas_mes)}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='movement-card'><div class='movement-label'><span class='dot' style='background:{COR_ERRO};'></span>SAÍDAS</div><div class='movement-value' style='color:{COR_ERRO};'>{formatar_brl(saidas_mes)}</div></div>", unsafe_allow_html=True)

    cor_resultado = COR_SUCESSO if resultado_liquido_mes >= 0 else COR_ERRO
    m3.markdown(f"<div class='movement-card'><div class='movement-label'><span class='dot' style='background:{cor_resultado};'></span>RESULTADO LÍQUIDO</div><div class='movement-value' style='color:{cor_resultado};'>{formatar_brl(resultado_liquido_mes)}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:12px;'>EVOLUÇÃO DIÁRIA DO SALDO CONSOLIDADO</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown(f"<div class='section-title'>RESUMO DAS APLICAÇÕES <span class='section-ref'>Ref.: {periodo_str}</span></div>", unsafe_allow_html=True)

    if not df_aplicacoes_nova.empty:
        def find_c(kws):
            for c in df_aplicacoes_nova.columns:
                if any(kw in c.lower() for kw in kws): return c
            return None

        c_banco = find_c(['conta', 'banco']) or df_aplicacoes_nova.columns[0]
        c_si = find_c(['inicial'])
        c_app = find_c(['aplicaç', 'aplicac'])
        c_imp = find_c(['imposto'])
        c_rend = find_c(['rendimento'])
        c_resg = find_c(['resgate'])
        c_atual = find_c(['atual', 'final'])

        html_app = f'<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>Instituição</th><th class="valores">Saldo Inicial {dt_ini_short}</th><th class="valores">Aplicações</th><th class="valores">Impostos</th><th class="valores">Rendimentos</th><th class="valores">Resgates</th><th class="valores">Saldo Atual {dt_fim_short}</th></tr></thead><tbody>'

        tot_si = 0; tot_app = 0; tot_imp = 0; tot_rend = 0; tot_resg = 0; tot_atual = 0

        for _, row in df_aplicacoes_nova.iterrows():
            banco = row[c_banco]
            si = row[c_si] if c_si else 0
            app = row[c_app] if c_app else 0
            imp = row[c_imp] if c_imp else 0
            rend = row[c_rend] if c_rend else 0
            resg = row[c_resg] if c_resg else 0
            atual = row[c_atual] if c_atual else 0

            tot_si += si; tot_app += app; tot_imp += imp; tot_rend += rend; tot_resg += resg; tot_atual += atual

            cor_rend = COR_NEUTRO if rend == 0 else (COR_SUCESSO if rend > 0 else COR_ERRO)
            html_app += f'<tr><td style="font-size:12.5px; font-weight:600;">{banco}</td><td class="valores">{formatar_moeda(si)}</td><td class="valores">{formatar_moeda(app)}</td><td class="valores" style="color:{COR_ERRO};">{formatar_moeda(imp)}</td><td class="valores" style="color:{cor_rend};">{formatar_moeda(rend)}</td><td class="valores" style="color:{COR_ERRO};">{formatar_moeda(resg)}</td><td class="valores valor-destaque">{formatar_moeda(atual)}</td></tr>'

        cor_tot_rend = COR_NEUTRO if tot_rend == 0 else (COR_SUCESSO if tot_rend > 0 else COR_ERRO)
        html_app += f'<tr class="linha-total"><td>Total Geral</td><td class="valores">{formatar_moeda(tot_si)}</td><td class="valores">{formatar_moeda(tot_app)}</td><td class="valores" style="color:{COR_ERRO};">{formatar_moeda(tot_imp)}</td><td class="valores" style="color:{cor_tot_rend};">{formatar_moeda(tot_rend)}</td><td class="valores" style="color:{COR_ERRO};">{formatar_moeda(tot_resg)}</td><td class="valores valor-destaque">{formatar_moeda(tot_atual)}</td></tr>'
        html_app += '</tbody></table></div>'
        st.markdown(html_app, unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding: 14px; text-align:center; color:#98A2B3; font-size:12.5px; border:1px dashed #d0d7e2; border-radius:8px; margin-bottom:8px;'>Nenhuma aplicação registrada para o período selecionado.</div>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

col_tab, col_diario = st.columns([1.6, 1])

# ==============================================================================
# TABELA CONSOLIDADA DE BANCOS
# ==============================================================================
with col_tab:
    st.markdown(f"<div class='section-title'>SALDO DE TODAS AS INSTITUIÇÕES <span class='section-ref'>Ref.: {periodo_str}</span></div>", unsafe_allow_html=True)
    df_view = df_consolidado[['Tipo', col_conta, 'Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final']].copy()

    def get_ordem(banco_nome):
        nome = str(banco_nome).lower().strip()
        if "aplicação" in nome or "aplicacao" in nome or "invest" in nome:
            if "unicred" in nome: return 11
            if "bradesco" in nome: return 12
            if "santander" in nome: return 13
            if "itaú" in nome or "itau" in nome: return 14
            return 50
        if "caixa" in nome: return 1
        if "unicred" in nome: return 2
        if "uniprime" in nome: return 3
        if "brasil" in nome or "bb" in nome: return 4
        if "70860" in nome: return 5
        if "comerc" in nome: return 6
        if "itaú" in nome or "itau" in nome: return 7
        if "santander" in nome: return 8
        if "sicoob" in nome: return 9
        if "cofre" in nome: return 10
        if "getnet" in nome: return 100
        return 999

    df_view['Ordem'] = df_view[col_conta].apply(get_ordem)
    df_view = df_view.sort_values('Ordem').drop(columns=['Ordem'])

    # --- Separação: Bancos x Limites (GetNet) ---
    df_bancos = df_view[df_view['Tipo'] != 'Limite']
    df_getnet = df_view[df_view['Tipo'] == 'Limite']

    # O TOTAL soma APENAS os bancos normais
    totais = {col: df_bancos[col].sum() for col in ['Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final']}

    html_tabela = f'<div class="tabela-container tabela-bancos"><table class="tabela-financeira"><thead><tr><th>#</th><th>{col_conta}</th><th>Tipo</th><th class="valores">Saldo Inicial {dt_ini_short}</th><th class="valores">Entrada (Op.)</th><th class="valores">Saída (Op.)</th><th class="valores">Entrada (Int.)</th><th class="valores">Saída (Int.)</th><th class="valores">Saldo Atual {dt_fim_short}</th></tr></thead><tbody>'

    # 1. Bancos operacionais
    for idx, row in enumerate(df_bancos.itertuples()):
        cor_entrada_int = COR_NEUTRO if row._6 == 0 else COR_SUCESSO
        cor_saida_int   = COR_NEUTRO if row._7 == 0 else COR_ERRO
        html_tabela += (
            f'<tr><td>{idx+1}</td>'
            f'<td style="font-weight:600;">{row._2}</td>'
            f'<td style="font-size:11px; font-weight:600; color:#475467;">{row.Tipo}</td>'
            f'<td class="valores">{formatar_moeda(row._3)}</td>'
            f'<td class="valores">{formatar_moeda(row._4)}</td>'
            f'<td class="valores">{formatar_moeda(row._5)}</td>'
            f'<td class="valores" style="color:{cor_entrada_int};">{formatar_moeda(row._6)}</td>'
            f'<td class="valores" style="color:{cor_saida_int};">{formatar_moeda(row._7)}</td>'
            f'<td class="valores valor-destaque">{formatar_moeda(row._8)}</td></tr>'
        )

    # 2. Linha de total (apenas bancos)
    html_tabela += (
        f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td>'
        f'<td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td>'
        f'<td class="valores">{formatar_moeda(totais["Entrada Op"])}</td>'
        f'<td class="valores">{formatar_moeda(totais["Saída Op"])}</td>'
        f'<td class="valores" style="color:{COR_NEUTRO};">—</td>'
        f'<td class="valores" style="color:{COR_NEUTRO};">—</td>'
        f'<td class="valores valor-destaque">{formatar_moeda(totais["Saldo Final"])}</td></tr>'
    )

    # 3. Seção de limites (GetNet) — fora do total, com destaque discreto em âmbar
    if not df_getnet.empty:
        html_tabela += '<tr class="subheader-row"><td colspan="9">Limites de Crédito &nbsp;·&nbsp; não integram o saldo consolidado</td></tr>'
        for idx, row in enumerate(df_getnet.itertuples()):
            idx_display = len(df_bancos) + idx + 1
            cor_entrada_int = COR_NEUTRO if row._6 == 0 else COR_SUCESSO
            cor_saida_int   = COR_NEUTRO if row._7 == 0 else COR_ERRO
            html_tabela += (
                f'<tr style="background-color:#fffdf6;">'
                f'<td style="border-top:2px solid {COR_ALERTA};">{idx_display}</td>'
                f'<td style="border-top:2px solid {COR_ALERTA}; font-weight:700;">{row._2}</td>'
                f'<td style="border-top:2px solid {COR_ALERTA}; font-size:11px; font-weight:600; color:{COR_ALERTA};">{row.Tipo}</td>'
                f'<td class="valores" style="border-top:2px solid {COR_ALERTA};">{formatar_moeda(row._3)}</td>'
                f'<td class="valores" style="border-top:2px solid {COR_ALERTA};">{formatar_moeda(row._4)}</td>'
                f'<td class="valores" style="border-top:2px solid {COR_ALERTA};">{formatar_moeda(row._5)}</td>'
                f'<td class="valores" style="border-top:2px solid {COR_ALERTA}; color:{cor_entrada_int};">{formatar_moeda(row._6)}</td>'
                f'<td class="valores" style="border-top:2px solid {COR_ALERTA}; color:{cor_saida_int};">{formatar_moeda(row._7)}</td>'
                f'<td class="valores valor-destaque" style="border-top:2px solid {COR_ALERTA}; color:{COR_ALERTA};">{formatar_moeda(row._8)}</td></tr>'
            )

    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)

# ==============================================================================
# SALDO DIÁRIO CONSOLIDADO
# ==============================================================================
with col_diario:
    st.markdown("<div class='section-title'>SALDO DIÁRIO CONSOLIDADO</div>", unsafe_allow_html=True)

    if not df_graficos.empty:
        # Ordenação pela data real (evita inversão de ordem na virada do mês)
        df_diario_view = df_graficos[['Data', 'Data_Label', 'Saldo Final', 'Entrada', 'Saída']].copy()
        df_diario_view = df_diario_view.sort_values(by='Data', ascending=False).drop(columns=['Data'])

        html_diario = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>Data</th><th class="valores">Saldo Final</th><th class="valores">Entradas (Op.)</th><th class="valores">Saídas (Op.)</th></tr></thead><tbody>'
        for _, row in df_diario_view.iterrows():
            cor_ent = COR_NEUTRO if row["Entrada"] == 0 else COR_SUCESSO
            cor_sai = COR_NEUTRO if row["Saída"] == 0 else COR_ERRO
            html_diario += (
                f'<tr><td style="font-size:13px; font-weight:600; color:#1d2939; font-variant-numeric:tabular-nums;">{row["Data_Label"]}</td>'
                f'<td class="valores valor-destaque">{formatar_moeda(row["Saldo Final"])}</td>'
                f'<td class="valores" style="color:{cor_ent};">{formatar_moeda(row["Entrada"])}</td>'
                f'<td class="valores" style="color:{cor_sai};">{formatar_moeda(row["Saída"])}</td></tr>'
            )
        html_diario += '</tbody></table></div>'
        st.markdown(html_diario, unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding: 14px; text-align:center; color:#98A2B3; font-size:12.5px; border:1px dashed #d0d7e2; border-radius:8px;'>Nenhuma movimentação registrada para o período selecionado.</div>", unsafe_allow_html=True)

st.markdown(
    f"<div style='font-size:9.5px; color:#98A2B3; margin-top:10px; text-align:right; letter-spacing:0.3px;'>"
    f"Valores expressos em Reais (R$) · Fonte: Extratos Bancários · Atualizado em {data_hoje}"
    f"</div>", unsafe_allow_html=True
)
