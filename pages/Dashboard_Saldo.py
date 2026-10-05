import streamlit as st

# O set_page_config OBRIGATORIAMENTE tem que ser a primeira coisa do arquivo
st.set_page_config(
    page_title="Painel Financeiro Mensal", 
    layout="wide", 
    page_icon="📊", 
    initial_sidebar_state="expanded"
)

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
except Exception as _err:
    _erro_import_db = str(_err)
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {_erro_import_db}")
        return None

# --- CUSTOM CSS (MILIMETRICAMENTE ALINHADO) ---
css = """
<style>
    :root {
        --bg: #f8fafc;
        --surface: #ffffff;
        --border: #d0e3e4;
        --text: #1a2035;
        --muted: #64748b;
        --primary: #008A8C;
        --primary-dark: #004D4E;
        --primary-medium: #006E6F;
        --success: #10b981;
        --danger: #ef4444;
        --shadow: 0 4px 15px rgba(0, 77, 78, 0.08);
    }
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .main { background: var(--bg); }
    .main .block-container { padding-top: 0.8rem; padding-bottom: 0.7rem; max-width: 98%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.38rem !important; }
    .stPlotlyChart { background: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }
    
    /* Cabeçalho */
    .dashboard-header { display: flex; justify-content: space-between; align-items: center; min-height: 60px; padding: 6px 4px 10px; margin-bottom: 10px; border-bottom: 1px solid var(--border); }
    .header-period { min-width: 200px; }
    .header-period .date { font-size: 17px; font-weight: 900; color: var(--text); letter-spacing: -0.25px; }
    .header-period .label { margin-top: 2px; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
    .header-center { text-align: center; }
    .header-center h1 { margin: 0; color: var(--primary-dark); font-size: 20px; line-height: 1.2; font-weight: 800; letter-spacing: 0.35px; }
    .header-center p { margin: 2px 0 0; color: var(--muted); font-size: 10px; font-weight: 500; letter-spacing: 0.3px; }
    
    /* KPIs Topo */
    .kpi-card { position: relative; overflow: hidden; min-height: 85px; padding: 14px 18px; border-radius: 8px; box-shadow: var(--shadow); text-align: left; border: none; display: flex; flex-direction: column; justify-content: center; }
    .kpi-card.total { background: #003839; }
    .kpi-card.corrente { background: #004D4E; }
    .kpi-card.aplicado { background: #006E6F; }
    .kpi-card.inicial { background: #008A8C; }
    .kpi-title { font-size: 10px; line-height: 1.2; font-weight: 800; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0; }
    .kpi-value { font-size: 24px; line-height: 1.15; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; white-space: nowrap; margin-top: 4px; }
    .kpi-var { font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; letter-spacing: 0.4px; }
    .kpi-var.up { background: rgba(74, 222, 128, 0.25); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.4); }
    .kpi-var.down { background: rgba(248, 113, 113, 0.25); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.4); }
    .kpi-var.neutral { background: rgba(255, 255, 255, 0.18); color: #e2e8f0; border: 1px solid rgba(255, 255, 255, 0.3); }
    
    /* Seções */
    .section-title { display: flex; align-items: center; min-height: 22px; margin-bottom: 4px; padding: 0 0 3px; border-bottom: 1.5px solid var(--border); color: var(--primary-dark); font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.75px; }
    .section-title::before { content: ""; width: 3px; height: 11px; margin-right: 6px; border-radius: 3px; background: var(--primary); }
    .section-title-inline { font-size: 9px; font-weight: 800; color: var(--muted); text-transform: uppercase; letter-spacing: 0.45px; }
    
    .movement-card { padding: 5px 8px; border: 1px solid var(--border); border-radius: 6px; background: #f0f7f7; }
    
    /* Tabelas */
    .tabela-container { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); box-shadow: var(--shadow); width: 100%; margin-bottom: 0px; }
    .tabela-container-scroll { overflow-x: auto; overflow-y: auto; max-height: 520px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); box-shadow: var(--shadow); width: 100%; margin-bottom: 8px; }
    
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; margin: 0; font-size: 11px; }
    .tabela-financeira th { background: #edf6f6; color: #475569; font-size: 9px; font-weight: 800; text-align: left; padding: 7px 6px; border-bottom: 1.5px solid var(--border); text-transform: uppercase; letter-spacing: 0.35px; position: sticky; top: 0; z-index: 2; white-space: nowrap; }
    .tabela-financeira td { padding: 6px 6px; border-bottom: 1px solid #f1f5f9; font-size: 11px; font-weight: 600; color: #1e293b; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #f0fdfa; }
    
    .tabela-financeira .linha-total td { background: #e0f2f1; color: var(--primary-dark); font-weight: 800; border-top: 2px solid var(--primary); border-bottom: 2px solid var(--primary); font-size: 11px; }
    .tabela-financeira .linha-limite td { background: #fef3c7; color: #92400e; font-weight: 700; border-top: 1px solid #fde68a; }
    
    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: right !important; font-weight: 700; font-variant-numeric: tabular-nums; }
    .tabela-financeira td.valor-destaque { font-weight: 800; color: var(--text); }
    
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .main .block-container { max-width: 100% !important; padding: 5px !important; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; color-adjust: exact !important; }
        .kpi-card, .tabela-container, .tabela-container-scroll, .movement-card { break-inside: avoid; max-height: none !important; overflow: visible !important; }
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 0. CONFIGURAÇÃO DA BARRA LATERAL
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
    st.info("💡 Para um relatório de alta qualidade, gere um PDF. Escolha a orientação **Paisagem** e desmarque 'Cabeçalhos/Rodapés'.", icon="ℹ")
    
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

def formatar_moeda(valor, exibir_traco_zero=True):
    try:
        val = float(valor)
        if val == 0 and exibir_traco_zero: return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "-" if exibir_traco_zero else "R$ 0,00"

def formatar_abreviado(valor):
    try:
        val = float(valor)
        if val == 0: return "-"
        if abs(val) >= 1_000_000:
            return f"R$ {val/1_000_000:.1f}M".replace('.', ',')
        elif abs(val) >= 1_000:
            return f"R$ {val/1_000:.1f}K".replace('.', ',')
        else:
            return f"R$ {val:.0f}"
    except Exception:
        return ""

def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()

# ==============================================================================
# 2. CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados(data_inicio, data_fim):
    conn = conectar_sheets()
    if conn is None: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim
    
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
                if 'Conta Garantida' not in df_saldo_inicial.columns: df_saldo_inicial['Conta Garantida'] = 0.0
                df_saldo_inicial['Conta Bancária'] = df_saldo_inicial['Conta Bancária'].astype(str).str.strip()
        except Exception as e: print("Aviso ao ler Saldo_Inicial:", e)
            
        df_extratos = None
        df_fim_mes = pd.DataFrame()
        entradas_periodo = 0.0
        saidas_periodo = 0.0
        df_process = pd.DataFrame()
        df_graficos = pd.DataFrame(columns=['Data', 'Vl Crédito', 'Vl Débito', 'Movimentação Líquida', 'Saldo Final', 'Saldo Inicial', 'Data_Label', 'Entrada Op', 'Saída Op', 'Delta R$', 'Delta %'])

        try:
            df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
            if not df_ext.empty:
                while len(df_ext.columns) < 12: df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""
                
                col_banco = df_ext.columns[0]
                col_data = df_ext.columns[1]
                col_deb = df_ext.columns[4]
                col_cred = df_ext.columns[5]
                col_tipo = df_ext.columns[7]
                col_operac = df_ext.columns[10] # Coluna K (índice 10: "Operacional" / "Não Operacional")
                col_subgrupo = df_ext.columns[11]

                df_process['Conta Bancária'] = df_ext[col_banco].astype(str).str.strip()
                df_process['Data'] = pd.to_datetime(df_ext[col_data], dayfirst=True, errors='coerce').dt.normalize()
                df_process['Vl Débito'] = df_ext[col_deb].apply(limpa_valor_bruto)
                df_process['Vl Crédito'] = df_ext[col_cred].apply(limpa_valor_bruto)
                df_process['SubGrupo'] = df_ext[col_subgrupo].astype(str).str.strip()
                df_process['Mov_Total'] = df_process['Vl Crédito'] - df_process['Vl Débito']
                df_process['Vl_Absoluto'] = df_process['Vl Crédito'] + df_process['Vl Débito']
                
                serie_tipo = df_ext[col_tipo].apply(normalizar_texto)
                
                # --- IDENTIFICAÇÃO DE TRANSFERÊNCIAS E EMPRÉSTIMO ---
                df_process['É Transf'] = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')
                df_process['É Emprestimo'] = serie_tipo.str.contains('liberacao de emprestimo')
                
                # --- REGRA DA COLUNA K (OPERACIONAL VS NÃO OPERACIONAL) ---
                serie_operac_k = df_ext[col_operac].apply(normalizar_texto)
                is_operacional = (serie_operac_k == 'operacional')

                df_process['Cred_Op'] = df_process['Vl Crédito'].where(is_operacional, 0.0)
                df_process['Deb_Op'] = df_process['Vl Débito'].where(is_operacional, 0.0)
                
                df_process['Cred_Tr'] = df_process['Vl Crédito'].where(df_process['É Transf'], 0.0)
                df_process['Deb_Tr'] = df_process['Vl Débito'].where(df_process['É Transf'], 0.0)
                
                df_process['Cred_Emp'] = df_process['Vl Crédito'].where(df_process['É Emprestimo'], 0.0)
                df_process['Deb_Emp'] = df_process['Vl Débito'].where(df_process['É Emprestimo'], 0.0)
                
                dt_ini_pd = pd.to_datetime(data_inicio); dt_fim_pd = pd.to_datetime(data_fim)
                
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
                    if 'getnet' in n_norm: return 'Limite'
                    return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

                if not df_period.empty:
                    df_period_grouped = df_period.groupby('Conta Bancária').agg({
                        'Cred_Op': 'sum', 'Deb_Op': 'sum', 
                        'Cred_Tr': 'sum', 'Deb_Tr': 'sum',
                        'Cred_Emp': 'sum', 'Deb_Emp': 'sum'
                    }).reset_index()
                    df_fim_mes = df_fim_mes.merge(df_period_grouped, on='Conta Bancária', how='outer').fillna(0)
                    
                    df_period_caixa = df_period[df_period['Conta Bancária'].apply(definir_tipo_aux).isin(['Disponível', 'Aplicação'])]
                    entradas_periodo = df_period_caixa['Cred_Op'].sum()
                    saidas_periodo = df_period_caixa['Deb_Op'].sum()
                else:
                    for c in ['Cred_Op', 'Deb_Op', 'Cred_Tr', 'Deb_Tr', 'Cred_Emp', 'Deb_Emp']: df_fim_mes[c] = 0.0
                
                df_fim_mes['Saldo Inicial'] = df_fim_mes['Saldo Inicial'].fillna(0)
                df_fim_mes['Conta Garantida'] = df_fim_mes['Conta Garantida'].fillna(0)
                df_fim_mes.rename(columns={
                    'Cred_Op': 'Entrada Op', 'Deb_Op': 'Saída Op', 
                    'Cred_Tr': 'Entrada Tr', 'Deb_Tr': 'Saída Tr',
                    'Cred_Emp': 'Entrada Emp', 'Deb_Emp': 'Saída Emp'
                }, inplace=True)
        except Exception as e: print("Aviso ao ler e processar extratos:", e)

        def definir_tipo(nome): 
            n_norm = normalizar_texto(nome)
            if 'getnet' in n_norm: return 'Limite'
            return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

        df_fim_mes['Tipo'] = df_fim_mes['Conta Bancária'].apply(definir_tipo)
        
        df_fim_mes['Saldo Final'] = (
            df_fim_mes['Saldo Inicial'] + 
            df_fim_mes['Entrada Op'] - df_fim_mes['Saída Op'] + 
            df_fim_mes['Entrada Tr'] - df_fim_mes['Saída Tr'] + 
            df_fim_mes['Entrada Emp'] - df_fim_mes['Saída Emp']
        )

        saldo_inicial_caixa = df_fim_mes[df_fim_mes['Tipo'].isin(['Disponível', 'Aplicação'])]['Saldo Inicial'].sum()
        
        if df_extratos is not None and not df_extratos.empty:
            df_ext_caixa = df_extratos[df_extratos['Conta Bancária'].apply(definir_tipo).isin(['Disponível', 'Aplicação'])].copy()
            df_extratos_diario = df_ext_caixa.groupby('Data').agg({'Vl Crédito': 'sum', 'Vl Débito': 'sum', 'Cred_Op': 'sum', 'Deb_Op': 'sum'}).reset_index()
            
            df_graficos = df_extratos_diario.sort_values('Data').copy()
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
            df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%d/%m')

        df_aplicacoes_nova = pd.DataFrame()
        saldo_aplicado_kpi = 0.0
        try:
            if not df_process.empty:
                serie_sub = df_process['SubGrupo'].apply(normalizar_texto)
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
                else: 
                    df_app_grouped = pd.DataFrame(columns=['Conta Bancária', 'Aplicações_Val', 'Impostos_Val', 'Rendimentos_Val', 'Resgates_Val'])
                
                df_app_full = df_fim_mes[['Conta Bancária', 'Tipo', 'Saldo Inicial', 'Saldo Final']].merge(df_app_grouped, on='Conta Bancária', how='left').fillna(0)
                
                def check_nome_app(nome): 
                    n_norm = normalizar_texto(nome)
                    return 'aplicacao' in n_norm or 'investimento' in n_norm
                
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
        except Exception as e: print("Erro ao processar Aplicações do Extrato:", e)

        return df_fim_mes, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, 'Conta Bancária', entradas_periodo, saidas_periodo, data_inicio, data_fim
    except Exception as e:
        st.error(f"Erro fatal ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 'Conta Bancária', 0.0, 0.0, data_inicio, data_fim

# ==============================================================================
# CHAMADA PRINCIPAL
# ==============================================================================
df_consolidado, df_graficos, df_aplicacoes_nova, saldo_aplicado_kpi, col_conta, entradas_operacionais, saidas_operacionais, data_ini_painel, data_fim_painel = carregar_dados(data_inicio_filtro, data_fim_filtro)
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
periodo_str = f"{data_ini_painel.strftime('%d/%m/%Y')} - {data_fim_painel.strftime('%d/%m/%Y')}"
dt_ini_short = data_ini_painel.strftime('%d/%m')
dt_fim_short = data_fim_painel.strftime('%d/%m')

# Gráfico de Rosca (Altura total alinhada com c2 e c3: ~205px)
fig_donut = go.Figure(data=[go.Pie(
    values=[saldo_aplicado, saldo_disponivel], 
    labels=['Saldo Aplicado', 'Conta Corrente'], 
    hole=0.6, 
    marker=dict(colors=['#008A8C', '#004D4E']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+percent'
)])
fig_donut.update_layout(
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=0, b=0, l=0, r=0), height=205,
    annotations=[dict(text=f"<b>R$ {saldo_total/1000000:,.1f}M</b><br>Saldo Total", x=0.5, y=0.5, font_size=11, font_color="#004D4E", showarrow=False)]
)

# Gráfico de Barras Evolução Diária
fig_combinado = go.Figure()
fig_combinado.add_trace(go.Bar(
    x=df_graficos['Data_Label'],
    y=df_graficos['Saldo Inicial'],
    name='Saldo Diário Inicial',
    marker_color='#004D4E', 
    text=[formatar_abreviado(v) for v in df_graficos['Saldo Inicial']],
    textposition='outside',
    textfont=dict(size=10, color="#1a2035", weight="bold"),
    opacity=0.9,
    width=0.45
))

fig_combinado.update_layout(
    margin=dict(t=15, b=0, l=0, r=0), height=138,
    xaxis=dict(tickfont=dict(size=9), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False),
    barmode='overlay',
    showlegend=False,
    plot_bgcolor='#f8fafc', paper_bgcolor='#f8fafc',
    hovermode='x unified'
)

# ==============================================================================
# 5. MONTAGEM DO PAINEL SUPERIOR
# ==============================================================================

header_html = (
    f'<div class="dashboard-header">'
    f'<div class="header-period">'
    f'<div class="date">{periodo_str}</div>'
    f'<div class="label">Período Selecionado</div>'
    f'</div>'
    f'<div class="header-center">'
    f'<h1>PAINEL FINANCEIRO MENSAL</h1>'
    f'<p>Controle Consolidado de Bancos</p>'
    f'</div>'
    f'<div style="min-width: 200px;"></div>'
    f'</div>'
)
st.markdown(header_html, unsafe_allow_html=True)

kpi_row = st.columns(4)

def get_var_html(pct):
    if pct > 0: return f"<div class='kpi-var up'>↗ +{pct:.1f}%</div>"
    elif pct < 0: return f"<div class='kpi-var down'>↘ {pct:.1f}%</div>"
    else: return f"<div class='kpi-var neutral'>→ 0.0%</div>"

kp_data = [
    (kpi_row[0], "SALDO TOTAL ATUAL", f"R$ {saldo_total:,.2f}", "total", get_var_html(var_total_pct)),
    (kpi_row[1], "SALDO CONTA CORRENTE", f"R$ {saldo_disponivel:,.2f}", "corrente", ""),
    (kpi_row[2], "SALDO APLICADO", f"R$ {saldo_aplicado:,.2f}", "aplicado", get_var_html(var_aplicado_pct)),
    (kpi_row[3], "SALDO INICIAL PERÍODO", f"R$ {saldo_inicial_periodo:,.2f}", "inicial", "<div class='kpi-var neutral'>→ Ref.</div>")
]

for col, title, val, color, var_html in kp_data:
    margem = "8px" if var_html.strip() else "0px"
    card_html = (
        f"<div class='kpi-card {color}'>"
        f"<div style='display: flex; align-items: center;'>"
        f"{var_html}"
        f"<div class='kpi-title' style='margin-left: {margem};'>{title}</div>"
        f"</div>"
        f"<div class='kpi-value'>{val}</div>"
        f"</div>"
    )
    col.markdown(card_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([0.85, 1.25, 1.6])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(f"<div class='section-title'>MOVIMENTAÇÃO OPERACIONAL <span style='margin-left:auto; font-size:10px; color:var(--muted); font-weight:800;'>REF: {periodo_str}</span></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    
    m1.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#10b981;'>ENTRADAS</div><div style='font-size:15px; font-weight:800;'>R$ {entradas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#ef4444;'>SAÍDAS</div><div style='font-size:15px; font-weight:800;'>R$ {saidas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    
    cor_res = "#10b981" if resultado_liquido_mes >= 0 else "#ef4444"
    m3.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:{cor_res};'>RESULTADO LÍQUIDO</div><div style='font-size:15px; font-weight:800; color:{cor_res};'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:6px;'>EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown(f"<div class='section-title'>RESUMO APLICAÇÕES <span style='margin-left:auto; font-size:10px; color:var(--muted); font-weight:800;'>REF: {periodo_str}</span></div>", unsafe_allow_html=True)
    
    tabela_app = f"<div class='tabela-container'><table class='tabela-financeira'>"
    tabela_app += f"<thead><tr><th>BANCO</th><th class='valores'>SALDO INICIAL {dt_ini_short}</th><th class='valores'>APLICAÇÕES</th><th class='valores'>IMPOSTOS</th><th class='valores'>RENDIMENTOS</th><th class='valores'>RESGATES</th><th class='valores'>SALDO ATUAL {dt_fim_short}</th></tr></thead><tbody>"
    
    tot_ini = 0.0
    tot_app = 0.0
    tot_imp = 0.0
    tot_ren = 0.0
    tot_res = 0.0
    tot_atu = 0.0

    if df_aplicacoes_nova.empty:
        tabela_app += f"<tr><td colspan='7' style='text-align:center;'>Nenhuma aplicação registrada no período</td></tr>"
    else:
        for _, row in df_aplicacoes_nova.sort_values(by='atual', ascending=False).iterrows():
            banco_nome = str(row.get('banco', '')).title()
            v_ini = row.get('inicial', 0)
            v_app = row.get('aplicaç', 0)
            v_imp = row.get('imposto', 0)
            v_ren = row.get('rendimento', 0)
            v_res = row.get('resgate', 0)
            v_atu = row.get('atual', 0)

            tot_ini += v_ini
            tot_app += v_app
            tot_imp += v_imp
            tot_ren += v_ren
            tot_res += v_res
            tot_atu += v_atu

            tabela_app += f"<tr>"
            tabela_app += f"<td><b>{banco_nome}</b></td>"
            tabela_app += f"<td class='valores'>{formatar_moeda(v_ini)}</td>"
            tabela_app += f"<td class='valores' style='color:#004D4E;'>{formatar_moeda(v_app)}</td>"
            tabela_app += f"<td class='valores' style='color:var(--danger);'>{formatar_moeda(v_imp)}</td>"
            tabela_app += f"<td class='valores' style='color:var(--success);'>{formatar_moeda(v_ren)}</td>"
            tabela_app += f"<td class='valores' style='color:var(--danger);'>{formatar_moeda(v_res)}</td>"
            tabela_app += f"<td class='valores valor-destaque'>{formatar_moeda(v_atu)}</td>"
            tabela_app += f"</tr>"

        tabela_app += f"<tr class='linha-total'>"
        tabela_app += f"<td><b>TOTAL</b></td>"
        tabela_app += f"<td class='valores'>{formatar_moeda(tot_ini)}</td>"
        tabela_app += f"<td class='valores'>{formatar_moeda(tot_app)}</td>"
        tabela_app += f"<td class='valores'>{formatar_moeda(tot_imp)}</td>"
        tabela_app += f"<td class='valores'>{formatar_moeda(tot_ren)}</td>"
        tabela_app += f"<td class='valores'>{formatar_moeda(tot_res)}</td>"
        tabela_app += f"<td class='valores valor-destaque'>{formatar_moeda(tot_atu)}</td>"
        tabela_app += f"</tr>"
            
    tabela_app += f"</tbody></table></div>"
    st.markdown(tabela_app, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 6. TABELAS INFERIORES (LADO A LADO)
# ==============================================================================
col_bancos, col_diario = st.columns([1.75, 1.0])

# --- TABELA DA ESQUERDA: SALDO DE TODOS OS BANCOS ---
with col_bancos:
    st.markdown("<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    
    df_padrao = df_consolidado[df_consolidado['Tipo'] != 'Limite'].copy()
    df_limite = df_consolidado[df_consolidado['Tipo'] == 'Limite'].copy()
    
    df_padrao['Ordem'] = df_padrao['Tipo'].map({'Disponível': 1, 'Aplicação': 2}).fillna(3)
    df_padrao = df_padrao.sort_values(by=['Ordem', 'Saldo Final'], ascending=[True, False]).reset_index(drop=True)
    
    tb_bancos = f"<div class='tabela-container-scroll'><table class='tabela-financeira'>"
    tb_bancos += f"<thead><tr>"
    tb_bancos += f"<th>#</th>"
    tb_bancos += f"<th>CONTA BANCÁRIA</th>"
    tb_bancos += f"<th>TIPO</th>"
    tb_bancos += f"<th class='valores'>SALDO INICIAL {dt_ini_short}</th>"
    tb_bancos += f"<th class='valores'>ENTRADA (OP.)</th>"
    tb_bancos += f"<th class='valores'>SAÍDA (OP.)</th>"
    tb_bancos += f"<th class='valores'>ENTRADA (INT.)</th>"
    tb_bancos += f"<th class='valores'>SAÍDA (INT.)</th>"
    tb_bancos += f"<th class='valores'>SALDO ATUAL {dt_fim_short}</th>"
    tb_bancos += f"</tr></thead><tbody>"
    
    tot_banco_ini = 0.0
    tot_banco_ent_op = 0.0
    tot_banco_sai_op = 0.0
    tot_banco_ent_tr = 0.0
    tot_banco_sai_tr = 0.0
    tot_banco_atu = 0.0
    
    idx_count = 1
    for _, row in df_padrao.iterrows():
        nome = str(row['Conta Bancária']).title()
        tipo = str(row['Tipo']).capitalize()
        
        si = row.get('Saldo Inicial', 0)
        e_op = row.get('Entrada Op', 0)
        s_op = row.get('Saída Op', 0)
        e_tr = row.get('Entrada Tr', 0) + row.get('Entrada Emp', 0)
        s_tr = row.get('Saída Tr', 0) + row.get('Saída Emp', 0)
        sf = row.get('Saldo Final', 0)
        
        tot_banco_ini += si
        tot_banco_ent_op += e_op
        tot_banco_sai_op += s_op
        tot_banco_ent_tr += e_tr
        tot_banco_sai_tr += s_tr
        tot_banco_atu += sf
        
        tb_bancos += f"<tr>"
        tb_bancos += f"<td><b>{idx_count}</b></td>"
        tb_bancos += f"<td><b>{nome}</b></td>"
        tb_bancos += f"<td>{tipo}</td>"
        tb_bancos += f"<td class='valores'>{formatar_moeda(si)}</td>"
        tb_bancos += f"<td class='valores' style='color:#004D4E;'>{formatar_moeda(e_op)}</td>"
        tb_bancos += f"<td class='valores' style='color:var(--danger);'>{formatar_moeda(s_op)}</td>"
        tb_bancos += f"<td class='valores' style='color:var(--success);'>{formatar_moeda(e_tr)}</td>"
        tb_bancos += f"<td class='valores' style='color:var(--danger);'>{formatar_moeda(s_tr)}</td>"
        tb_bancos += f"<td class='valores valor-destaque'>{formatar_moeda(sf)}</td>"
        tb_bancos += f"</tr>"
        idx_count += 1

    tb_bancos += f"<tr class='linha-total'>"
    tb_bancos += f"<td colspan='3'><b>TOTAL</b></td>"
    tb_bancos += f"<td class='valores'>{formatar_moeda(tot_banco_ini)}</td>"
    tb_bancos += f"<td class='valores'>{formatar_moeda(tot_banco_ent_op)}</td>"
    tb_bancos += f"<td class='valores'>{formatar_moeda(tot_banco_sai_op)}</td>"
    tb_bancos += f"<td class='valores'>-</td>"
    tb_bancos += f"<td class='valores'>-</td>"
    tb_bancos += f"<td class='valores valor-destaque'>{formatar_moeda(tot_banco_atu)}</td>"
    tb_bancos += f"</tr>"
    
    if not df_limite.empty:
        for _, row_lim in df_limite.iterrows():
            nome_lim = str(row_lim['Conta Bancária']).title()
            garantida_val = row_lim.get('Conta Garantida', 0)
            if garantida_val == 0:
                garantida_val = row_lim.get('Saldo Inicial', 0)
                
            tb_bancos += f"<tr class='linha-limite'>"
            tb_bancos += f"<td><b>{idx_count}</b></td>"
            tb_bancos += f"<td><b>{nome_lim}</b></td>"
            tb_bancos += f"<td><span style='color:#b45309; font-weight:800;'>Limite</span></td>"
            tb_bancos += f"<td class='valores'>{formatar_moeda(garantida_val)}</td>"
            tb_bancos += f"<td class='valores'>-</td>"
            tb_bancos += f"<td class='valores'>-</td>"
            tb_bancos += f"<td class='valores'>-</td>"
            tb_bancos += f"<td class='valores'>-</td>"
            tb_bancos += f"<td class='valores valor-destaque' style='color:#b45309;'>{formatar_moeda(garantida_val)}</td>"
            tb_bancos += f"</tr>"
            idx_count += 1
            
    tb_bancos += f"</tbody></table></div>"
    st.markdown(tb_bancos, unsafe_allow_html=True)


# --- TABELA DA DIREITA: SALDO DIÁRIO CONSOLIDADO ---
with col_diario:
    st.markdown("<div class='section-title'>SALDO DIÁRIO CONSOLIDADO</div>", unsafe_allow_html=True)
    
    tb_diario = f"<div class='tabela-container-scroll'><table class='tabela-financeira'>"
    tb_diario += f"<thead><tr>"
    tb_diario += f"<th>DATA</th>"
    tb_diario += f"<th class='valores'>SALDO INIC.</th>"
    tb_diario += f"<th class='valores'>ENTRADAS</th>"
    tb_diario += f"<th class='valores'>SAÍDAS</th>"
    tb_diario += f"<th class='valores'>SALDO FINAL</th>"
    tb_diario += f"<th class='valores'>DELTA</th>"
    tb_diario += f"</tr></thead><tbody>"
    
    if df_graficos.empty:
        tb_diario += f"<tr><td colspan='6' style='text-align:center;'>Sem movimentações diárias no período</td></tr>"
    else:
        df_diario_rev = df_graficos.sort_values(by='Data', ascending=False)
        
        for _, row_d in df_diario_rev.iterrows():
            d_str = row_d.get('Data_Label', '')
            s_inic = row_d.get('Saldo Inicial', 0)
            
            # Puxando estritamente movimentações filtradas pela Coluna K ("Operacional")
            entr = row_d.get('Entrada Op', 0) 
            said = row_d.get('Saída Op', 0)   
            
            s_fin = row_d.get('Saldo Final', 0)
            delta = row_d.get('Delta R$', 0)
            
            cor_delta = "var(--success)" if delta >= 0 else "var(--danger)"
            sinal_delta = "+" if delta > 0 else ""
            
            tb_diario += f"<tr>"
            tb_diario += f"<td><b>{d_str}</b></td>"
            tb_diario += f"<td class='valores'>{formatar_moeda(s_inic, False)}</td>"
            tb_diario += f"<td class='valores' style='color:var(--success);'>{formatar_moeda(entr, False)}</td>"
            tb_diario += f"<td class='valores' style='color:var(--danger);'>{formatar_moeda(said, False)}</td>"
            tb_diario += f"<td class='valores valor-destaque'>{formatar_moeda(s_fin, False)}</td>"
            tb_diario += f"<td class='valores' style='color:{cor_delta}; font-weight:800;'>{sinal_delta}{formatar_moeda(delta, False)}</td>"
            tb_diario += f"</tr>"
            
    tb_diario += f"</tbody></table></div>"
    st.markdown(tb_diario, unsafe_allow_html=True)
