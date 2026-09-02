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
import textwrap

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Mensal", layout="wide", page_icon="📊", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
css = """
<style>
    :root {
        --bg: #f5f7fb;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --border: #d0e3e4; /* Borda Ciano Suave (SOS Cardio) */
        --text: #172033; /* Cinza Escuro Principal */
        --muted: #6b7280;
        --primary: #008A8C; /* Cor da Logo SOS Cardio */
        --success: #159570;
        --danger: #d94a4a;
        --warning: #c58a16;
        --shadow: 0 4px 15px rgba(0, 138, 140, 0.15);
    }

    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .main { background: var(--bg); }
    .main .block-container { padding-top: 0.8rem; padding-bottom: 0.7rem; max-width: 97%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.38rem !important; }
    .stPlotlyChart { background: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }

    /* Cabeçalho */
    .dashboard-header { display: flex; justify-content: space-between; align-items: center; min-height: 64px; padding: 8px 4px 10px; margin-bottom: 10px; border-bottom: 1px solid var(--border); }
    .header-period { min-width: 200px; }
    .header-period .date { font-size: 18px; font-weight: 900; color: var(--text); letter-spacing: -0.25px; }
    .header-period .label { margin-top: 2px; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
    .header-center { text-align: center; }
    .header-center h1 { margin: 0; color: var(--text); font-size: 21px; line-height: 1.2; font-weight: 800; letter-spacing: 0.35px; }
    .header-center p { margin: 3px 0 0; color: var(--muted); font-size: 10px; font-weight: 500; letter-spacing: 0.3px; }
    .update-badge { min-width: 105px; padding: 6px 12px; text-align: center; border: 1px solid #ccebdc; border-radius: 8px; background: #ecfdf5; color: #23795d; }
    .update-badge span { font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .update-badge b { font-size: 12px; font-weight: 800; }

    /* KPIs com a Paleta Institucional (S.O.S. Cardio) */
    .kpi-card { position: relative; overflow: hidden; min-height: 90px; padding: 18px 20px; border-radius: 10px; box-shadow: var(--shadow); text-align: left; border: none; display: flex; flex-direction: column; justify-content: center; }
    
    .kpi-card.total { background: linear-gradient(135deg, #004D4E, #003334); }
    .kpi-card.corrente { background: linear-gradient(135deg, #006E6F, #004b4c); }
    .kpi-card.aplicado { background: linear-gradient(135deg, #008A8C, #006869); }
    .kpi-card.inicial { background: linear-gradient(135deg, #1CB0B2, #148b8d); }
    
    .kpi-title { font-size: 11px; line-height: 1.2; font-weight: 750; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); }
    .kpi-value { font-size: 26px; line-height: 1.15; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; white-space: nowrap; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); }

    /* Seções Harmonizadas com Fonte Cinza Escura */
    .section-title { display: flex; align-items: center; min-height: 25px; margin-bottom: 5px; padding: 0 0 5px; border-bottom: 1px solid var(--border); color: var(--text); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.75px; }
    .section-title::before { content: ""; width: 3px; height: 12px; margin-right: 7px; border-radius: 4px; background: var(--primary); }
    .section-title-inline { font-size: 9px; font-weight: 750; color: var(--muted); text-transform: uppercase; letter-spacing: 0.45px; }
    .movement-card { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; background: #f4fafa; }

    /* Tabelas Harmonizadas com Fonte Cinza Escura */
    .tabela-container { overflow-x: auto; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); box-shadow: 0 2px 8px rgba(0, 138, 140, 0.04); font-size: 12px; width: 100%; margin-bottom: 8px; }
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; }
    
    .tabela-financeira th { background: #eaf4f4; color: #596274; font-size: 10px; font-weight: 800; text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.35px; }
    .tabela-financeira td { padding: 10px 8px; border-bottom: 1px solid #ebf2f2; font-size: 13px; font-weight: 550; color: #273043; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #f0f7f7; }
    
    .tabela-financeira .linha-total { background: #e0efef; border-top: 2px solid #008A8C; }
    .tabela-financeira .linha-total td { color: var(--text); font-weight: 800; }
    
    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: left !important; font-weight: 750; font-variant-numeric: tabular-nums; font-size: 14px; }
    .tabela-financeira td.valor-destaque { font-size: 16px !important; font-weight: 800; color: var(--text); }
    
    hr { border: 0 !important; border-top: 1px solid var(--border) !important; margin: 15px 0 !important; }

    /* MODO IMPRESSÃO (PDF) */
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
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 0. CONFIGURAÇÃO DA BARRA LATERAL (MENU ORIGINAL)
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
    st.info("💡 Para um relatório de alta qualidade, gere um PDF. Escolha a orientação **Paisagem** e desmarque 'Cabeçalhos/Rodapés'.", icon="ℹ️")
    
    components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }" 
        style="width:100%; background:linear-gradient(135deg, #008A8C, #004D4E); color:white; border:none; padding:12px; border-radius:8px; font-family:sans-serif; font-weight:bold; font-size:14px; cursor:pointer; box-shadow: 0 4px 6px rgba(0, 138, 140, 0.2); transition: transform 0.2s;">
        🖨️ Salvar Dashboard (PDF)
        </button>
    """, height=55)

if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
    data_inicio_filtro, data_fim_filtro = data_selecionada
else:
    data_inicio_filtro = data_selecionada[0] if isinstance(data_selecionada, tuple) else data_selecionada
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
        if val == 0: return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
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

# ==============================================================================
# 2. CARGA DE DADOS (COM SALDO INICIAL DESLOCADO E FILTRO ESTRITO DE NOME)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados(data_inicio, data_fim):
    conn = conectar_sheets()
    
    if conn is None: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim
    try:
        # =========================================================
        # 1. ABA SALDO_INICIAL FIXO (A ÂNCORA DA TESOURARIA)
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
        # 2. LER TODOS OS EXTRATOS E FAZER O DESLOCAMENTO DO SALDO
        # =========================================================
        df_extratos = None
        df_fim_mes = pd.DataFrame()
        entradas_operacionais = 0.0
        saidas_operacionais = 0.0
        df_process = pd.DataFrame()
        df_graficos = pd.DataFrame(columns=['Data', 'Vl Crédito', 'Vl Débito', 'Movimentação Líquida', 'Saldo Final', 'Saldo Inicial', 'Data_Label', 'Entrada Op', 'Saída Op'])

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
                
                def normalizar_texto(txt):
                    if pd.isna(txt) or txt is None: return ""
                    return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower()
                
                serie_tipo = df_ext[col_tipo].apply(normalizar_texto)
                df_process['É Transf'] = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')

                serie_operac = df_ext[col_operac].fillna('OPERACIONAL').astype(str).str.strip().str.upper()
                is_operacional = (serie_operac == 'OPERACIONAL')

                # SEPARANDO OPERACIONAL DE INTERNO
                df_process['Cred_Op'] = df_process['Vl Crédito'].where((~df_process['É Transf']) & is_operacional, 0.0)
                df_process['Deb_Op'] = df_process['Vl Débito'].where((~df_process['É Transf']) & is_operacional, 0.0)
                df_process['Cred_Tr'] = df_process['Vl Crédito'].where(df_process['É Transf'], 0.0)
                df_process['Deb_Tr'] = df_process['Vl Débito'].where(df_process['É Transf'], 0.0)
                
                dt_ini_pd = pd.to_datetime(data_inicio)
                dt_fim_pd = pd.to_datetime(data_fim)
                
                # --- PASSO A: SALDO INICIAL DESLOCADO ---
                df_before = df_process[df_process['Data'] < dt_ini_pd].copy()
                
                if not df_before.empty:
                    df_before_grouped = df_before.groupby('Conta Bancária')['Mov_Total'].sum().reset_index()
                    df_saldo_dinamico = pd.merge(df_saldo_inicial, df_before_grouped, on='Conta Bancária', how='outer').fillna(0)
                    df_saldo_dinamico['Saldo Inicial'] = df_saldo_dinamico['Saldo Inicial'] + df_saldo_dinamico['Mov_Total']
                else:
                    df_saldo_dinamico = df_saldo_inicial.copy()
                    
                df_fim_mes = df_saldo_dinamico[['Conta Bancária', 'Saldo Inicial', 'Conta Garantida']].copy()
                
                # --- PASSO B: MOVIMENTAÇÃO DO PERÍODO SELECIONADO ---
                df_period = df_process[(df_process['Data'] >= dt_ini_pd) & (df_process['Data'] <= dt_fim_pd)].copy()
                df_extratos = df_period 

                if not df_period.empty:
                    df_period_grouped = df_period.groupby('Conta Bancária').agg({
                        'Cred_Op': 'sum',
                        'Deb_Op': 'sum',
                        'Cred_Tr': 'sum',
                        'Deb_Tr': 'sum',
                    }).reset_index()
                    
                    df_fim_mes = df_fim_mes.merge(df_period_grouped, on='Conta Bancária', how='outer').fillna(0)
                else:
                    df_fim_mes['Cred_Op'] = 0.0
                    df_fim_mes['Deb_Op'] = 0.0
                    df_fim_mes['Cred_Tr'] = 0.0
                    df_fim_mes['Deb_Tr'] = 0.0
                
                df_fim_mes['Saldo Inicial'] = df_fim_mes['Saldo Inicial'].fillna(0)
                df_fim_mes['Conta Garantida'] = df_fim_mes['Conta Garantida'].fillna(0)
                df_fim_mes.rename(columns={'Cred_Op': 'Entrada Op', 'Deb_Op': 'Saída Op', 'Cred_Tr': 'Entrada Tr', 'Deb_Tr': 'Saída Tr'}, inplace=True)

        except Exception as e:
            print("Aviso ao ler e processar extratos dinâmicos:", e)

        # =========================================================
        # 3. FECHAMENTO DO SALDO FINAL DA TABELA DE BANCOS
        # =========================================================
        def definir_tipo(nome): 
            n_norm = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('utf-8').lower()
            if 'getnet' in n_norm: return 'Limite'
            return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

        df_fim_mes['Tipo'] = df_fim_mes['Conta Bancária'].apply(definir_tipo)
        df_fim_mes['Saldo Final'] = df_fim_mes['Saldo Inicial'] + df_fim_mes['Entrada Op'] - df_fim_mes['Saída Op'] + df_fim_mes['Entrada Tr'] - df_fim_mes['Saída Tr']

        # =========================================================
        # 4. GRÁFICO DIÁRIO E TABELA DE ACOMPANHAMENTO DIÁRIO
        # =========================================================
        saldo_inicial_caixa = df_fim_mes[df_fim_mes['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()
        
        if df_extratos is not None and not df_extratos.empty:
            df_ext_caixa = df_extratos[df_extratos['Conta Bancária'].apply(definir_tipo).isin(['Disponível', 'Aplicação'])].copy()
            
            df_extratos_diario = df_ext_caixa.groupby('Data').agg({
                'Vl Crédito': 'sum',
                'Vl Débito': 'sum',
                'Cred_Op': 'sum',
                'Deb_Op': 'sum'
            }).reset_index()

            df_graficos = df_extratos_diario.sort_values('Data').copy()
            df_graficos['Movimentação Líquida'] = df_graficos['Vl Crédito'] - df_graficos['Vl Débito']
            
            df_graficos['Saldo Final'] = saldo_inicial_caixa + df_graficos['Movimentação Líquida'].cumsum()
            df_graficos['Saldo Inicial'] = df_graficos['Saldo Final'] - df_graficos['Movimentação Líquida']
            df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%d/%m')
            
            df_graficos['Entrada Op'] = df_graficos['Cred_Op']
            df_graficos['Saída Op'] = df_graficos['Deb_Op']

        entradas_operacionais = df_fim_mes['Entrada Op'].sum()
        saidas_operacionais = df_fim_mes['Saída Op'].sum()

        # =========================================================
        # 5. GERAR RESUMO DE APLICAÇÕES A PARTIR DO EXTRATO (COLUNA L)
        # =========================================================
        df_aplicacoes_nova = pd.DataFrame()
        saldo_aplicado_kpi = 0.0
        
        try:
            if not df_process.empty:
                serie_sub = df_process['SubGrupo'].apply(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ASCII', 'ignore').decode('utf-8').lower())
                
                app_mask = serie_sub == 'aplicacao financeira'
                imp_mask = serie_sub == 'impostos sobre aplicacoes'
                rend_mask = serie_sub == 'rendimentos de aplicacoes'
                resg_mask = serie_sub == 'resgates de aplicacoes'
                
                df_process['Aplicações_Val'] = df_process['Vl_Absoluto'].where(app_mask, 0.0)
                df_process['Impostos_Val'] = df_process['Vl_Absoluto'].where(imp_mask, 0.0)
                df_process['Rendimentos_Val'] = df_process['Vl_Absoluto'].where(rend_mask, 0.0)
                df_process['Resgates_Val'] = df_process['Vl_Absoluto'].where(resg_mask, 0.0)
                
                df_period_app = df_process[(df_process['Data'] >= pd.to_datetime(data_inicio)) & (df_process['Data'] <= pd.to_datetime(data_fim))].copy()
                
                if not df_period_app.empty:
                    df_app_grouped = df_period_app.groupby('Conta Bancária').agg({
                        'Aplicações_Val': 'sum',
                        'Impostos_Val': 'sum',
                        'Rendimentos_Val': 'sum',
                        'Resgates_Val': 'sum'
                    }).reset_index()
                else:
                    df_app_grouped = pd.DataFrame(columns=['Conta Bancária', 'Aplicações_Val', 'Impostos_Val', 'Rendimentos_Val', 'Resgates_Val'])
                
                df_app_full = df_fim_mes[['Conta Bancária', 'Tipo', 'Saldo Inicial', 'Saldo Final']].merge(
                    df_app_grouped, on='Conta Bancária', how='left'
                ).fillna(0)
                
                # Exibir somente se a Conta Bancária tem 'aplicação' ou 'investimento' no nome
                def check_nome_app(nome):
                    n = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('utf-8').lower()
                    return 'aplicacao' in n or 'investimento' in n

                mask_is_app = df_app_full['Conta Bancária'].apply(check_nome_app)
                
                mask_has_data = (df_app_full['Aplicações_Val'] != 0) | (df_app_full['Impostos_Val'] != 0) | \
                                (df_app_full['Rendimentos_Val'] != 0) | (df_app_full['Resgates_Val'] != 0) | \
                                (df_app_full['Saldo Inicial'] != 0) | (df_app_full['Saldo Final'] != 0)
                
                df_aplicacoes_nova = df_app_full[mask_is_app & mask_has_data].copy()
                
                df_aplicacoes_nova = df_aplicacoes_nova.rename(columns={
                    'Conta Bancária': 'banco',
                    'Saldo Inicial': 'inicial',
                    'Aplicações_Val': 'aplicaç',
                    'Impostos_Val': 'imposto',
                    'Rendimentos_Val': 'rendimento',
                    'Resgates_Val': 'resgate',
                    'Saldo Final': 'atual'
                })
                
                saldo_aplicado_kpi = df_app_full[mask_is_app]['Saldo Final'].sum()
        except Exception as e:
            print("Erro ao processar Aplicações do Extrato:", e)

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
# 3. CÁLCULOS DOS KPIs MENSAIS E HARMONIZAÇÃO DE CORES
# ==============================================================================
saldo_inicial_periodo = df_consolidado[df_consolidado['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()
saldo_aplicado = saldo_aplicado_kpi
saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()

saldo_getnet = df_consolidado[df_consolidado['Tipo'] == 'Limite']['Saldo Final'].sum()
saldo_conta_garantida = df_consolidado['Conta Garantida'].sum()
limites_totais = saldo_getnet + saldo_conta_garantida

saldo_total = saldo_disponivel + saldo_aplicado

entradas_mes = entradas_operacionais
saidas_mes = saidas_operacionais
resultado_liquido_mes = entradas_mes - saidas_mes

# ==============================================================================
# 4. GRÁFICOS E VARIÁVEIS DE DATA
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
periodo_str = f"{data_ini_painel.strftime('%d/%m/%Y')} - {data_fim_painel.strftime('%d/%m/%Y')}"

dt_ini_short = data_ini_painel.strftime('%d/%m')
dt_fim_short = data_fim_painel.strftime('%d/%m')

# HARMONIZAÇÃO:
fig_donut = go.Figure(data=[go.Pie(
    values=[saldo_aplicado, saldo_disponivel], 
    labels=['Saldo Aplicado', 'Conta Corrente'], 
    hole=0.6, 
    marker=dict(colors=['#008A8C', '#006E6F']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+percent'
)])
fig_donut.update_layout(
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=10, b=40, l=0, r=0), height=320,
    annotations=[dict(text=f"<b>R$ {saldo_total/1000000:,.1f}M</b><br>Saldo Total", x=0.5, y=0.48, font_size=12, font_color="#172033", showarrow=False)]
)

fig_combinado = go.Figure()
fig_combinado.add_trace(go.Bar(
    x=df_graficos['Data_Label'],
    y=df_graficos['Saldo Final'],
    name='Saldo Total',
    marker_color='#004D4E', 
    text=[formatar_abreviado(v) for v in df_graficos['Saldo Final']],
    textposition='outside',
    textfont=dict(size=13, color="#1a2035", weight="bold"),
    opacity=0.9,
    width=0.45
))
fig_combinado.update_layout(
    margin=dict(t=25, b=15, l=5, r=5), height=200, # Altura ajustada natural (200px) para alinhar com a tabela flexível
    xaxis=dict(tickfont=dict(size=10), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False),
    barmode='overlay',
    showlegend=False,
    plot_bgcolor='#f1f5f9', paper_bgcolor='#f1f5f9',
    hovermode='x unified'
)

# ==============================================================================
# 5. MONTAGEM DO PAINEL
# ==============================================================================
st.markdown(f"""
<div class="dashboard-header">
    <div class="header-period">
        <div class="date"> {periodo_str}</div>
        <div class="label">Período Selecionado</div>
    </div>
    <div class="header-center">
        <h1>PAINEL FINANCEIRO MENSAL</h1>
        <p>Controle Consolidado de Bancos</p>
    </div>
    <div class="update-badge">
        <span>Atualização</span><br>
        <b>{data_hoje}</b>
    </div>
</div>
""", unsafe_allow_html=True)

kpi_row = st.columns(4)

kp_data = [
    (kpi_row[0], "SALDO TOTAL ATUAL", f"R$ {saldo_total:,.2f}", "total"),
    (kpi_row[1], "SALDO CONTA CORRENTE", f"R$ {saldo_disponivel:,.2f}", "corrente"),
    (kpi_row[2], "SALDO APLICADO", f"R$ {saldo_aplicado:,.2f}", "aplicado"),
    (kpi_row[3], "SALDO INICIAL PERÍODO", f"R$ {saldo_inicial_periodo:,.2f}", "inicial")
]

for col, title, val, color in kp_data:
    col.markdown(f"<div class='kpi-card {color}'><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([0.85, 1.25, 1.6])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(f"<div class='section-title'>MOVIMENTAÇÃO OPERACIONAL <span style='margin-left:auto; font-size:11px; color:#6b7280; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div class='movement-card'><div class='section-title-inline'> ENTRADAS</div><div style='font-size:19px; font-weight:800;'>R$ {entradas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='movement-card'><div class='section-title-inline'> SAÍDAS</div><div style='font-size:19px; font-weight:800;'>R$ {saidas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    
    if resultado_liquido_mes >= 0:
        m3.markdown(f"<div class='movement-card'><div class='section-title-inline'> RESULTADO LÍQUIDO</div><div style='font-size:19px; font-weight:800; color:#1cc88a;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)
    else:
        m3.markdown(f"<div class='movement-card'><div class='section-title-inline'> RESULTADO LÍQUIDO</div><div style='font-size:19px; font-weight:800; color:#e74a3b;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown(f"<div class='section-title'>RESUMO APLICAÇÕES <span style='margin-left:auto; font-size:11px; color:#6b7280; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    
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
        
        # APLICANDO O ENQUADRAMENTO PERFEITO SEM ESPAÇO VAZIO
        # Removido o style="height: 320px;" para a tabela abraçar o conteúdo.
        html_app = f'<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>BANCO</th><th class="valores">SALDO INICIAL {dt_ini_short}</th><th class="valores">APLICAÇÕES</th><th class="valores">IMPOSTOS</th><th class="valores">RENDIMENTOS</th><th class="valores">RESGATES</th><th class="valores">SALDO ATUAL {dt_fim_short}</th></tr></thead><tbody>'
        
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
            
            cor_rend = "#858796" if rend == 0 else ("#1cc88a" if rend > 0 else "#e74a3b")
            html_app += f'<tr><td style="font-size:12px; font-weight:600; color:#4b5563;">{banco}</td><td class="valores">{formatar_moeda(si)}</td><td class="valores">{formatar_moeda(app)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(imp)}</td><td class="valores" style="color:{cor_rend};">{formatar_moeda(rend)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(resg)}</td><td class="valores valor-destaque">{formatar_moeda(atual)}</td></tr>'
            
        cor_tot_rend = "#858796" if tot_rend == 0 else ("#1cc88a" if tot_rend > 0 else "#e74a3b")
        html_app += f'<tr class="linha-total"><td style="font-size:12px;">TOTAL</td><td class="valores">{formatar_moeda(tot_si)}</td><td class="valores">{formatar_moeda(tot_app)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(tot_imp)}</td><td class="valores" style="color:{cor_tot_rend};">{formatar_moeda(tot_rend)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(tot_resg)}</td><td class="valores valor-destaque">{formatar_moeda(tot_atual)}</td></tr>'
        html_app += '</tbody></table></div>'
        st.markdown(html_app, unsafe_allow_html=True)
    else:
        st.markdown("<div class='tabela-container' style='display: flex; align-items: center; justify-content: center; color: #888; font-size: 13px; border: 1px dashed #ccc; padding: 20px;'>Nenhuma aplicação encontrada no período.</div>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

col_tab, col_diario = st.columns([1.6, 1])

with col_tab:
    st.markdown(f"<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
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

    df_bancos = df_view[df_view['Tipo'] != 'Limite']
    df_getnet = df_view[df_view['Tipo'] == 'Limite']

    totais = {col: df_bancos[col].sum() for col in ['Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final']}
    
    html_tabela = f'<div class="tabela-container tabela-bancos"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+f'</th><th>TIPO</th><th class="valores">SALDO INICIAL {dt_ini_short}</th><th class="valores">ENTRADA (OP.)</th><th class="valores">SAÍDA (OP.)</th><th class="valores">ENTRADA (INT.)</th><th class="valores">SAÍDA (INT.)</th><th class="valores">SALDO ATUAL {dt_fim_short}</th></tr></thead><tbody>'
    
    for idx, row in enumerate(df_bancos.itertuples()):
        cor_transf = "#858796" if row._6 == 0 else "#1cc88a"
        cor_transf_saida = "#858796" if row._7 == 0 else "#e74a3b"
        html_tabela += f'<tr><td>{idx+1}</td><td>{row._2}</td><td style="font-size:11px; font-weight:700; color:#4b5563;">{row.Tipo}</td><td class="valores">{formatar_moeda(row._3)}</td><td class="valores">{formatar_moeda(row._4)}</td><td class="valores">{formatar_moeda(row._5)}</td><td class="valores" style="color:{cor_transf};">{formatar_moeda(row._6)}</td><td class="valores" style="color:{cor_transf_saida};">{formatar_moeda(row._7)}</td><td class="valores valor-destaque">{formatar_moeda(row._8)}</td></tr>'
    
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada Op"])}</td><td class="valores">{formatar_moeda(totais["Saída Op"])}</td><td class="valores" style="color:#858796;">-</td><td class="valores" style="color:#858796;">-</td><td class="valores valor-destaque">{formatar_moeda(totais["Saldo Final"])}</td></tr>'

    if not df_getnet.empty:
        for idx, row in enumerate(df_getnet.itertuples()):
            idx_display = len(df_bancos) + idx + 1
            cor_transf = "#858796" if row._6 == 0 else "#1cc88a"
            cor_transf_saida = "#858796" if row._7 == 0 else "#e74a3b"
            html_tabela += f'<tr style="background-color: #fff9f0;"><td style="border-top: 2px dashed #f5c070;">{idx_display}</td><td style="border-top: 2px dashed #f5c070; font-weight:700;">{row._2}</td><td style="border-top: 2px dashed #f5c070; font-size:11px; font-weight:700; color:#c58a16;">{row.Tipo}</td><td class="valores" style="border-top: 2px dashed #f5c070;">{formatar_moeda(row._3)}</td><td class="valores" style="border-top: 2px dashed #f5c070;">{formatar_moeda(row._4)}</td><td class="valores" style="border-top: 2px dashed #f5c070;">{formatar_moeda(row._5)}</td><td class="valores" style="border-top: 2px dashed #f5c070; color:{cor_transf};">{formatar_moeda(row._6)}</td><td class="valores" style="border-top: 2px dashed #f5c070; color:{cor_transf_saida};">{formatar_moeda(row._7)}</td><td class="valores valor-destaque" style="border-top: 2px dashed #f5c070; color:#c58a16;">{formatar_moeda(row._8)}</td></tr>'

    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)

with col_diario:
    st.markdown("<div class='section-title'>SALDO DIÁRIO CONSOLIDADO</div>", unsafe_allow_html=True)
    
    if not df_graficos.empty:
        df_diario_view = df_graficos[['Data_Label', 'Saldo Inicial', 'Entrada Op', 'Saída Op', 'Saldo Final']].copy()
        df_diario_view = df_diario_view.sort_values(by='Data_Label', ascending=False)
    else:
        df_diario_view = pd.DataFrame(columns=['Data_Label', 'Saldo Inicial', 'Entrada Op', 'Saída Op', 'Saldo Final'])
    
    html_diario = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>DATA</th><th class="valores">SALDO INICIAL</th><th class="valores">ENTRADAS (OP.)</th><th class="valores">SAÍDAS (OP.)</th><th class="valores">SALDO FINAL</th></tr></thead><tbody>'
    for _, row in df_diario_view.iterrows():
        html_diario += f'<tr><td style="font-size:13px; font-weight:750; color:#273043;">{row["Data_Label"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores" style="color:#1cc88a;">{formatar_moeda(row["Entrada Op"])}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(row["Saída Op"])}</td><td class="valores valor-destaque">{formatar_moeda(row["Saldo Final"])}</td></tr>'
    html_diario += '</tbody></table></div>'
    st.markdown(html_diario, unsafe_allow_html=True)

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em {data_hoje}</div>", unsafe_allow_html=True)
