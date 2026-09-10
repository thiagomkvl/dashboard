import streamlit as st

# O set_page_config OBRIGATORIAMENTE tem que ser a primeira coisa do arquivo
st.set_page_config(page_title="Painel Financeiro Mensal", layout="wide", page_icon="📊", initial_sidebar_state="expanded")

import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import unicodedata
from datetime import datetime
import textwrap

# BLINDAGEM MÁXIMA DE CONEXÃO
try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# --- CUSTOM CSS ---
css = """
<style>
    :root {
        --bg: #f5f7fb;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --border: #d0e3e4;
        --text: #172033;
        --muted: #6b7280;
        --primary: #008A8C;
        --success: #1cc88a;
        --danger: #e74a3b;
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
    .header-period .date { font-size: 16px; font-weight: 900; color: var(--text); letter-spacing: -0.25px; }
    .header-period .label { margin-top: 2px; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
    .header-center { text-align: center; }
    .header-center h1 { margin: 0; color: var(--text); font-size: 21px; line-height: 1.2; font-weight: 800; letter-spacing: 0.35px; }
    .header-center p { margin: 3px 0 0; color: var(--muted); font-size: 10px; font-weight: 500; letter-spacing: 0.3px; }
    /* KPIs */
    .kpi-card { position: relative; overflow: hidden; min-height: 90px; padding: 18px 20px; border-radius: 10px; box-shadow: var(--shadow); text-align: left; border: none; display: flex; flex-direction: column; justify-content: center; }
    .kpi-card.total { background: linear-gradient(135deg, #004D4E, #003334); }
    .kpi-card.corrente { background: linear-gradient(135deg, #006E6F, #004b4c); }
    .kpi-card.aplicado { background: linear-gradient(135deg, #008A8C, #006869); }
    .kpi-card.inicial { background: linear-gradient(135deg, #1CB0B2, #148b8d); }
    .kpi-title { font-size: 11px; line-height: 1.2; font-weight: 750; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); }
    .kpi-value { font-size: 26px; line-height: 1.15; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; white-space: nowrap; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); margin-top: 6px; }
    .kpi-var { font-size: 11px; font-weight: 800; padding: 2px 7px; border-radius: 5px; display: inline-flex; align-items: center; letter-spacing: 0.5px;}
    .kpi-var.up { background: rgba(74, 222, 128, 0.2); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
    .kpi-var.down { background: rgba(248, 113, 113, 0.2); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }
    .kpi-var.neutral { background: rgba(255, 255, 255, 0.15); color: #e2e8f0; border: 1px solid rgba(255, 255, 255, 0.2); }
    .section-title { display: flex; align-items: center; min-height: 25px; margin-bottom: 5px; padding: 0 0 5px; border-bottom: 1px solid var(--border); color: var(--text); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.75px; }
    .section-title::before { content: ""; width: 3px; height: 12px; margin-right: 7px; border-radius: 4px; background: var(--primary); }
    .section-title-inline { font-size: 9px; font-weight: 750; color: var(--muted); text-transform: uppercase; letter-spacing: 0.45px; }
    .movement-card { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; background: #f4fafa; }
    .tabela-container { overflow-x: auto; overflow-y: auto; max-height: 380px; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); box-shadow: 0 2px 8px rgba(0, 138, 140, 0.04); font-size: 12px; width: 100%; margin-bottom: 8px; }
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; margin: 0; }
    .tabela-financeira th { background: #eaf4f4; color: #596274; font-size: 10px; font-weight: 800; text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.35px; position: sticky; top: 0; z-index: 2; }
    .tabela-financeira td { padding: 10px 8px; border-bottom: 1px solid #ebf2f2; font-size: 13px; font-weight: 550; color: #273043; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #f0f7f7; }
    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: right !important; font-weight: 750; font-variant-numeric: tabular-nums; }
    hr { border: 0 !important; border-top: 1px solid var(--border) !important; margin: 15px 0 !important; }
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .main .block-container { max-width: 100% !important; padding: 10px !important; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 0. CONFIGURAÇÃO DA BARRA LATERAL (FILTRO MÊS A MÊS)
# ==============================================================================
hoje = datetime.now().date()

with st.sidebar:
    st.markdown("### Filtros Mensais")
    
    # Criando opções de meses para seleção limpa (Mês/Ano)
    anos_disponiveis = list(range(2024, hoje.year + 1))
    meses_dict = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        ano_inicio = st.selectbox("Ano Início", anos_disponiveis, index=len(anos_disponiveis)-1)
        mes_inicio = st.selectbox("Mês Início", list(meses_dict.keys()), format_func=lambda x: meses_dict[x], index=0)
    with col_s2:
        ano_fim = st.selectbox("Ano Fim", anos_disponiveis, index=len(anos_disponiveis)-1)
        mes_fim = st.selectbox("Mês Fim", list(meses_dict.keys()), format_func=lambda x: meses_dict[x], index=hoje.month - 1 if hoje.year == anos_disponiveis[-1] else 11)

    # Definir primeiro dia do mês inicial e último dia do mês final
    data_inicio_filtro = datetime(ano_inicio, mes_inicio, 1).date()
    # Último dia do mês fim
    if mes_fim == 12:
        data_fim_filtro = datetime(ano_fim + 1, 1, 1).date() - timedelta(days=1)
    else:
        data_fim_filtro = datetime(ano_fim, mes_fim + 1, 1).date() - timedelta(days=1)
        
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    st.markdown("### Relatório")
    st.info("💡 Para salvar o painel mensal em PDF, utilize a opção abaixo em orientação Paisagem.", icon="ℹ️")
    
    components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }" 
        style="width:100%; background:linear-gradient(135deg, #008A8C, #004D4E); color:white; border:none; padding:12px; border-radius:8px; font-family:sans-serif; font-weight:bold; font-size:14px; cursor:pointer; box-shadow: 0 4px 6px rgba(0, 138, 140, 0.2);">
        🖨️ Salvar Dashboard (PDF)
        </button>
    """, height=55)

# ==============================================================================
# 1. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
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
# 2. CARGA DE DADOS (Consumindo Saldo_Inicial_Ano e Extratos_Tasy)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_mensais(data_inicio, data_fim):
    conn = conectar_sheets()
    if conn is None: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim
    try:
        df_saldo_inicial = pd.DataFrame(columns=['Conta Bancária', 'Saldo Inicial', 'Conta Garantida'])
        try:
            # Consumindo Saldo_Inicial_Ano conforme solicitado
            df_si = conn.read(worksheet="Saldo_Inicial_Ano", ttl=0)
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
                if 'Conta Garantida' not in df_saldo_inicial.columns: df_saldo_inicial['Conta Garantida'] = 0.0
                df_saldo_inicial['Conta Bancária'] = df_saldo_inicial['Conta Bancária'].astype(str).str.strip()
        except Exception as e: print("Aviso ao ler Saldo_Inicial_Ano:", e)
            
        df_extratos = None
        df_fim_mes = pd.DataFrame()
        entradas_periodo = 0.0
        saidas_periodo = 0.0
        df_process = pd.DataFrame()
        df_graficos = pd.DataFrame()

        try:
            # Consumindo Extratos_Tasy conforme solicitado
            df_ext = conn.read(worksheet="Extratos_Tasy", ttl=0)
            if not df_ext.empty:
                while len(df_ext.columns) < 12: df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""
                col_banco = df_ext.columns[0]; col_data = df_ext.columns[1]; col_deb = df_ext.columns[4]; col_cred = df_ext.columns[5]
                col_tipo = df_ext.columns[7]; col_operac = df_ext.columns[10]; col_subgrupo = df_ext.columns[11]

                df_process['Conta Bancária'] = df_ext[col_banco].astype(str).str.strip()
                df_process['Data'] = pd.to_datetime(df_ext[col_data], dayfirst=True, errors='coerce').dt.normalize()
                df_process['Vl Débito'] = df_ext[col_deb].apply(limpa_valor_bruto)
                df_process['Vl Crédito'] = df_ext[col_cred].apply(limpa_valor_bruto)
                df_process['SubGrupo'] = df_ext[col_subgrupo].astype(str).str.strip()
                df_process['Mov_Total'] = df_process['Vl Crédito'] - df_process['Vl Débito']
                df_process['Vl_Absoluto'] = df_process['Vl Crédito'] + df_process['Vl Débito']
                
                def normalizar_texto(txt): return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower() if pd.notna(txt) else ""
                serie_tipo = df_ext[col_tipo].apply(normalizar_texto)
                df_process['É Transf'] = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')
                serie_operac = df_ext[col_operac].fillna('OPERACIONAL').astype(str).str.strip().str.upper()
                is_operacional = (serie_operac == 'OPERACIONAL')

                df_process['Cred_Op'] = df_process['Vl Crédito'].where((~df_process['É Transf']) & is_operacional, 0.0)
                df_process['Deb_Op'] = df_process['Vl Débito'].where((~df_process['É Transf']) & is_operacional, 0.0)
                df_process['Cred_Tr'] = df_process['Vl Crédito'].where(df_process['É Transf'], 0.0)
                df_process['Deb_Tr'] = df_process['Vl Débito'].where(df_process['É Transf'], 0.0)
                
                dt_ini_pd = pd.to_datetime(data_inicio); dt_fim_pd = pd.to_datetime(data_fim)
                
                df_before = df_process[df_process['Data'] < dt_ini_pd].copy()
                if not df_before.empty:
                    df_before_grouped = df_before.groupby('Conta Bancária')['Mov_Total'].sum().reset_index()
                    df_saldo_dinamico = pd.merge(df_saldo_inicial, df_before_grouped, on='Conta Bancária', how='outer').fillna(0)
                    df_saldo_dinamico['Saldo Inicial'] = df_saldo_dinamico['Saldo Inicial'] + df_saldo_dinamico['Mov_Total']
                else: df_saldo_dinamico = df_saldo_inicial.copy()
                    
                df_fim_mes = df_saldo_dinamico[['Conta Bancária', 'Saldo Inicial', 'Conta Garantida']].copy()
                
                df_period = df_process[(df_process['Data'] >= dt_ini_pd) & (df_process['Data'] <= dt_fim_pd)].copy()
                df_extratos = df_period 

                def definir_tipo_aux(nome): 
                    n_norm = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('utf-8').lower()
                    if 'getnet' in n_norm: return 'Limite'
                    return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

                if not df_period.empty:
                    df_period_grouped = df_period.groupby('Conta Bancária').agg({'Cred_Op': 'sum', 'Deb_Op': 'sum', 'Cred_Tr': 'sum', 'Deb_Tr': 'sum'}).reset_index()
                    df_fim_mes = df_fim_mes.merge(df_period_grouped, on='Conta Bancária', how='outer').fillna(0)
                    
                    df_period_caixa = df_period[df_period['Conta Bancária'].apply(definir_tipo_aux).isin(['Disponível', 'Aplicação']) & (~df_period['É Transf'])]
                    entradas_periodo = df_period_caixa['Vl Crédito'].sum()
                    saidas_periodo = df_period_caixa['Vl Débito'].sum()
                else:
                    for c in ['Cred_Op', 'Deb_Op', 'Cred_Tr', 'Deb_Tr']: df_fim_mes[c] = 0.0
                
                df_fim_mes['Saldo Inicial'] = df_fim_mes['Saldo Inicial'].fillna(0)
                df_fim_mes['Conta Garantida'] = df_fim_mes['Conta Garantida'].fillna(0)
                df_fim_mes.rename(columns={'Cred_Op': 'Entrada Op', 'Deb_Op': 'Saída Op', 'Cred_Tr': 'Entrada Tr', 'Deb_Tr': 'Saída Tr'}, inplace=True)
        except Exception as e: print("Aviso ao ler e processar extratos Tasy:", e)

        def definir_tipo(nome): 
            n_norm = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('utf-8').lower()
            if 'getnet' in n_norm: return 'Limite'
            return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

        df_fim_mes['Tipo'] = df_fim_mes['Conta Bancária'].apply(definir_tipo)
        df_fim_mes['Saldo Final'] = df_fim_mes['Saldo Inicial'] + df_fim_mes['Entrada Op'] - df_fim_mes['Saída Op'] + df_fim_mes['Entrada Tr'] - df_fim_mes['Saída Tr']

        saldo_inicial_caixa = df_fim_mes[df_fim_mes['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()
        
        # Agrupamento Mensal para o Gráfico de Evolução (Mês a Mês)
        if df_extratos is not None and not df_extratos.empty:
            df_ext_caixa = df_extratos[df_extratos['Conta Bancária'].apply(definir_tipo).isin(['Disponível', 'Aplicação'])].copy()
            df_ext_caixa['AnoMes'] = df_ext_caixa['Data'].dt.to_period('M')
            df_extratos_mensal = df_ext_caixa.groupby('AnoMes').agg({'Vl Crédito': 'sum', 'Vl Débito': 'sum', 'Cred_Op': 'sum', 'Deb_Op': 'sum'}).reset_index()
            df_extratos_mensal['Data'] = df_extratos_mensal['AnoMes'].dt.to_timestamp()
            
            df_graficos = df_extratos_mensal.sort_values('Data').copy()
            df_graficos['Movimentação Líquida'] = df_graficos['Vl Crédito'] - df_graficos['Vl Débito']
            df_graficos['Entrada Op'] = df_graficos['Cred_Op']
            df_graficos['Saída Op'] = df_graficos['Deb_Op']
            
            saldos_iniciais = []
            saldos_finais = []
            delta_rs = []
            delta_pct = []
            
            saldo_atual_iter = saldo_inicial_caixa
            for idx, row in df_graficos.iterrows():
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
            df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%b/%Y').str.capitalize()

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
                    df_app_grouped = df_period_app.groupby('Conta Bancária').agg({'Aplicações_Val': 'sum', 'Impostos_Val': 'sum', 'Rendimentos_Val': 'sum', 'Resgates_Val': 'sum'}).reset_index()
                else: df_app_grouped = pd.DataFrame(columns=['Conta Bancária', 'Aplicações_Val', 'Impostos_Val', 'Rendimentos_Val', 'Resgates_Val'])
                
                df_app_full = df_fim_mes[['Conta Bancária', 'Tipo', 'Saldo Inicial', 'Saldo Final']].merge(df_app_grouped, on='Conta Bancária', how='left').fillna(0)
                
                def check_nome_app(nome): return 'aplicacao' in unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('utf-8').lower() or 'investimento' in unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('utf-8').lower()
                mask_is_app = df_app_full['Conta Bancária'].apply(check_nome_app)
                
                mask_has_movimentacao = (
                    (df_app_full['Aplicações_Val'] != 0) | 
                    (df_app_full['Impostos_Val'] != 0) | 
                    (df_app_full['Rendimentos_Val'] != 0) | 
                    (df_app_full['Resgates_Val'] != 0) | 
                    (round(df_app_full['Saldo Inicial'], 2) != round(df_app_full['Saldo Final'], 2))
                )
                
                df_aplicacoes_nova = df_app_full[mask_is_app & mask_has_movimentacao].copy()
                df_aplicacoes_nova = df_aplicacoes_nova.rename(columns={'Conta Bancária': 'banco', 'Saldo Inicial': 'inicial', 'Aplicações_Val': 'aplicaç', 'Impostos_Val': 'imposto', 'Rendimentos_Val': 'rendimento', 'Resgates_Val': 'resgate', 'Saldo Final': 'atual'})
                saldo_aplicado_kpi = df_app_full[mask_is_app]['Saldo Final'].sum()
        except Exception as e: print("Erro ao processar Aplicações do Extrato Tasy:", e)

        return df_fim_mes, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, 'Conta Bancária', entradas_periodo, saidas_periodo, data_inicio, data_fim
    except Exception as e:
        st.error(f"Erro fatal ao carregar dados mensais: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim

# ==============================================================================
# CHAMADA PRINCIPAL
# ==============================================================================
df_consolidado, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, col_conta, entradas_operacionais, saidas_operacionais, data_ini_painel, data_fim_painel = carregar_dados_mensais(data_inicio_filtro, data_fim_filtro)
if not col_conta: col_conta = 'Conta Bancária'

if df_consolidado.empty:
    st.warning("⚠️ Os dados não foram carregados ou a planilha está vazia.")
    st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs MENSAIS E VARIAÇÕES (%)
# ==============================================================================
saldo_inicial_periodo = df_consolidado[df_consolidado['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()
saldo_aplicado = saldo_aplicado_kpi
saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()
saldo_total = saldo_disponivel + saldo_aplicado

saldo_inicial_corrente = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Inicial'].sum()
saldo_inicial_aplicado = df_consolidado[df_consolidado['Tipo'] == 'Aplicação']['Saldo Inicial'].sum()

def calc_var(final, inicial):
    if inicial == 0 and final == 0: return 0.0
    if inicial == 0: return 100.0 if final > 0 else -100.0
    return ((final / inicial) - 1) * 100

var_total_pct = calc_var(saldo_total, saldo_inicial_periodo)
var_corrente_pct = calc_var(saldo_disponivel, saldo_inicial_corrente)
var_aplicado_pct = calc_var(saldo_aplicado, saldo_inicial_aplicado)

entradas_mes = entradas_operacionais
saidas_mes = saidas_operacionais
resultado_liquido_mes = entradas_mes - saidas_mes

# ==============================================================================
# 4. GRÁFICOS E VARIÁVEIS DE DATA
# ==============================================================================
periodo_str = f"{data_ini_painel.strftime('%B/%Y').capitalize()} a {data_fim_painel.strftime('%B/%Y').capitalize()}"

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
    margin=dict(t=10, b=10, l=0, r=0), height=315,
    annotations=[dict(text=f"<b>R$ {saldo_total/1000000:,.1f}M</b><br>Saldo Total", x=0.5, y=0.48, font_size=12, font_color="#004D4E", showarrow=False)]
)

fig_combinado = go.Figure()
if not df_graficos.empty:
    fig_combinado.add_trace(go.Bar(
        x=df_graficos['Data_Label'],
        y=df_graficos['Saldo Final'],
        name='Saldo Final Mensal',
        marker_color='#004D4E', 
        text=[formatar_abreviado(v) for v in df_graficos['Saldo Final']],
        textposition='outside',
        textfont=dict(size=11, color="#1a2035", weight="bold"),
        opacity=0.9,
        width=0.45
    ))

fig_combinado.update_layout(
    margin=dict(t=25, b=10, l=5, r=5), height=230,
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
        <div class="label">Período Mensal Selecionado</div>
    </div>
    <div class="header-center">
        <h1>PAINEL FINANCEIRO MENSAL (TASY)</h1>
        <p>Controle Consolidado de Extratos</p>
    </div>
    <div style="min-width: 200px;"></div>
</div>
""", unsafe_allow_html=True)

kpi_row = st.columns(4)

def get_var_html(pct):
    if pct > 0: return f"<div class='kpi-var up'>↗ +{pct:.1f}%</div>"
    elif pct < 0: return f"<div class='kpi-var down'>↘ {pct:.1f}%</div>"
    else: return f"<div class='kpi-var neutral'>→ 0.0%</div>"

kp_data = [
    (kpi_row[0], "SALDO TOTAL ATUAL", f"R$ {saldo_total:,.2f}", "total", get_var_html(var_total_pct)),
    (kpi_row[1], "SALDO CONTA CORRENTE", f"R$ {saldo_disponivel:,.2f}", "corrente", get_var_html(var_corrente_pct)),
    (kpi_row[2], "SALDO APLICADO", f"R$ {saldo_aplicado:,.2f}", "aplicado", get_var_html(var_aplicado_pct)),
    (kpi_row[3], "SALDO INICIAL ANO", f"R$ {saldo_inicial_periodo:,.2f}", "inicial", "<div class='kpi-var neutral'>→ Ref.</div>")
]

for col, title, val, color, var_html in kp_data:
    card_html = f"""
    <div class='kpi-card {color}'>
        <div style='display: flex; align-items: center;'>
            {var_html}
            <div class='kpi-title' style='margin-left: 10px;'>{title}</div>
        </div>
        <div class='kpi-value'>{val}</div>
    </div>
    """
    col.markdown(card_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([0.85, 1.25, 1.6])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(f"<div class='section-title'>MOVIMENTAÇÃO OPERACIONAL <span style='margin-left:auto; font-size:11px; color:#000000; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    
    m1.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#1cc88a;'> ENTRADAS</div><div style='font-size:17px; font-weight:800;'>R$ {entradas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#e74a3b;'> SAÍDAS</div><div style='font-size:17px; font-weight:800;'>R$ {saidas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    
    if resultado_liquido_mes >= 0:
        m3.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#1cc88a;'> RESULTADO LÍQ.</div><div style='font-size:17px; font-weight:800; color:#1cc88a;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)
    else:
        m3.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#e74a3b;'> RESULTADO LÍQ.</div><div style='font-size:17px; font-weight:800; color:#e74a3b;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO MÊS A MÊS DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown(f"<div class='section-title'>RESUMO APLICAÇÕES (TASY) <span style='margin-left:auto; font-size:11px; color:#000000; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    
    if not df_aplicacoes_nova.empty:
        html_app = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>BANCO</th><th class="valores">SALDO INICIAL</th><th class="valores">APLICAÇÕES</th><th class="valores">IMPOSTOS</th><th class="valores">RENDIMENTOS</th><th class="valores">RESGATES</th><th class="valores">SALDO ATUAL</th></tr></thead><tbody>'
        
        tot_si = 0; tot_app = 0; tot_imp = 0; tot_rend = 0; tot_resg = 0; tot_atual = 0
        
        for _, row in df_aplicacoes_nova.iterrows():
            banco = row['banco']
            si = row['inicial']
            ap = row['aplicaç']
            im = row['imposto']
            rd = row['rendimento']
            rs = row['resgate']
            at = row['atual']
            
            tot_si += si
            tot_app += ap
            tot_imp += im
            tot_rend += rd
            tot_resg += rs
            tot_atual += at
            
            html_app += f"<tr><td>{banco}</td><td class='valores'>{formatar_moeda(si)}</td><td class='valores'>{formatar_moeda(ap)}</td><td class='valores'>{formatar_moeda(im)}</td><td class='valores'>{formatar_moeda(rd)}</td><td class='valores'>{formatar_moeda(rs)}</td><td class='valores' style='font-weight:800;'>{formatar_moeda(at)}</td></tr>"
            
        html_app += f"<tr class='linha-total'><td><strong>TOTAIS</strong></td><td class='valores'><strong>{formatar_moeda(tot_si)}</strong></td><td class='valores'><strong>{formatar_moeda(tot_app)}</strong></td><td class='valores'><strong>{formatar_moeda(tot_imp)}</strong></td><td class='valores'><strong>{formatar_moeda(tot_rend)}</strong></td><td class='valores'><strong>{formatar_moeda(tot_resg)}</strong></td><td class='valores'><strong>{formatar_moeda(tot_atual)}</strong></td></tr>"
        html_app += '</tbody></table></div>'
        st.markdown(html_app, unsafe_allow_html=True)
    else:
        st.info("Nenhuma movimentação de aplicações registrada no período selecionado.")
