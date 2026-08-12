import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
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
st.set_page_config(page_title="Painel Financeiro Mensal", layout="wide", page_icon="📊")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    /* =========================================================
       IDENTIDADE VISUAL
       ========================================================= */
    :root {
        --bg: #f5f7fb;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --border: #e7ebf2;
        --text: #172033;
        --muted: #6b7280;
        --primary: #3157d5;
        --primary-soft: #eef2ff;
        --success: #159570;
        --success-soft: #ecfdf5;
        --danger: #d94a4a;
        --danger-soft: #fff1f2;
        --warning: #c58a16;
        --warning-soft: #fffbeb;
        --info: #2388a7;
        --info-soft: #ecfeff;
        --purple: #7654c8;
        --purple-soft: #f5f3ff;
        --shadow: 0 2px 10px rgba(24, 39, 75, 0.055);
    }

    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .main { background: var(--bg); }
    .main .block-container { padding-top: 0.8rem; padding-bottom: 0.7rem; max-width: 97%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.38rem !important; }
    .stPlotlyChart { background: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }

    /* Cabeçalho */
    .dashboard-header { display: flex; justify-content: space-between; align-items: center; min-height: 64px; padding: 8px 4px 10px; margin-bottom: 10px; border-bottom: 1px solid var(--border); }
    .header-period { min-width: 170px; }
    .header-period .date { font-size: 17px; font-weight: 750; color: var(--text); letter-spacing: -0.25px; }
    .header-period .label { margin-top: 2px; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
    .header-center { text-align: center; }
    .header-center h1 { margin: 0; color: var(--text); font-size: 21px; line-height: 1.2; font-weight: 800; letter-spacing: 0.35px; }
    .header-center p { margin: 3px 0 0; color: var(--muted); font-size: 10px; font-weight: 500; letter-spacing: 0.3px; }
    .update-badge { min-width: 105px; padding: 6px 12px; text-align: center; border: 1px solid #ccebdc; border-radius: 8px; background: var(--success-soft); color: #23795d; }
    .update-badge span { font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .update-badge b { font-size: 12px; font-weight: 750; }

    /* KPIs */
    .kpi-card { position: relative; overflow: hidden; min-height: 78px; padding: 12px 15px 11px; border: 1px solid var(--border); border-radius: 10px; background: var(--surface); box-shadow: var(--shadow); text-align: left; }
    .kpi-card::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--primary); }
    .kpi-card.total::before { background: var(--primary); }
    .kpi-card.disponivel::before { background: var(--success); }
    .kpi-card.limites::before { background: var(--info); }
    .kpi-card.aplicacoes::before { background: var(--purple); }
    .kpi-card.total { background: linear-gradient(135deg, #fff, #f8faff); }
    .kpi-card.disponivel { background: linear-gradient(135deg, #fff, #f7fdf9); }
    .kpi-card.limites { background: linear-gradient(135deg, #fff, #f6fcfe); }
    .kpi-card.aplicacoes { background: linear-gradient(135deg, #fff, #faf8ff); }
    .kpi-icon { width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 5px; border-radius: 7px; background: var(--primary-soft); font-size: 13px; }
    .kpi-card.disponivel .kpi-icon { background: var(--success-soft); }
    .kpi-card.limites .kpi-icon { background: var(--info-soft); }
    .kpi-card.aplicacoes .kpi-icon { background: var(--purple-soft); }
    .kpi-title { font-size: 9px; line-height: 1; font-weight: 750; color: var(--muted); text-transform: uppercase; letter-spacing: 0.65px; margin-bottom: 5px; }
    .kpi-value { font-size: 20px; line-height: 1.15; font-weight: 800; color: var(--text); letter-spacing: -0.35px; white-space: nowrap; }

    /* Seções */
    .section-title { display: flex; align-items: center; min-height: 25px; margin-bottom: 5px; padding: 0 0 5px; border-bottom: 1px solid var(--border); color: var(--text); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.75px; }
    .section-title::before { content: ""; width: 3px; height: 12px; margin-right: 7px; border-radius: 4px; background: var(--primary); }
    .section-title-inline { font-size: 9px; font-weight: 750; color: var(--muted); text-transform: uppercase; letter-spacing: 0.45px; }
    .movement-card { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-soft); }

    /* Tabelas */
    .tabela-container { overflow-x: auto; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); box-shadow: var(--shadow); font-size: 12px; width: 100%; margin-bottom: 8px; }
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; }
    .tabela-financeira th { background: #f7f9fc; color: #596274; font-size: 10px; font-weight: 800; text-align: left; padding: 11px 10px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.35px; }
    .tabela-financeira td { padding: 10px 10px; border-bottom: 1px solid #f0f2f6; font-size: 13px; font-weight: 550; color: #273043; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #fafbfe; }
    .tabela-financeira .linha-total { background: #eef2f7; border-top: 2px solid #d8dee8; }
    .tabela-financeira .linha-total td { color: #172033; font-weight: 800; }
    
    /* Alinhamento de Números para a Direita */
    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: right !important; font-weight: 750; font-variant-numeric: tabular-nums; }
    
    /* Custo Oportunidade */
    .custo-oportunidade { background: var(--danger-soft); border: 1px solid #f5d6da; border-left: 3px solid var(--danger); padding: 8px 10px; margin-top: 8px; border-radius: 7px; display: flex; justify-content: space-between; }
    .custo-oportunidade span { font-weight: 750; color: var(--danger); }
    hr { border: 0 !important; border-top: 1px solid var(--border) !important; }
    </style>
""", unsafe_allow_html=True)

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

def formatar_transf(valor):
    try:
        val = float(valor)
        if val == 0: return "-"
        prefixo = "+ " if val > 0 else "- "
        return f"{prefixo}R$ {abs(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "-"

# ==============================================================================
# 2. CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    conn = conectar_sheets()
    mes_referencia = pd.to_datetime(datetime.now().date()).replace(day=1)
    
    if conn is None: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, "", 0.0, 0.0, mes_referencia
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
        # 2. EXTRATOS (Mapeamento Posicional)
        # =========================================================
        df_extratos = None
        proximo_mes = mes_referencia + relativedelta(months=1)
        
        try:
            df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
            if not df_ext.empty:
                while len(df_ext.columns) < 8:
                    df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""
                
                df_ext = df_ext.iloc[:, [0, 1, 4, 5, 7]].copy()
                df_ext.columns = ['Conta Bancária', 'Data', 'Vl Débito', 'Vl Crédito', 'Tipo de Transação']

                df_ext['Data'] = pd.to_datetime(df_ext['Data'], dayfirst=True, errors='coerce').dt.normalize()
                
                datas_validas = df_ext['Data'].dropna()
                if not datas_validas.empty:
                    mes_referencia = datas_validas.mode().iloc[0].replace(day=1)
                    proximo_mes = mes_referencia + relativedelta(months=1)
                
                df_ext = df_ext[(df_ext['Data'] >= mes_referencia) & (df_ext['Data'] < proximo_mes)].copy()
                
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
        df_fim_mes['Disponível'] = df_fim_mes['Saldo Final'] + df_fim_mes['Conta Garantida']

        # =========================================================
        # 4. GRÁFICO DIÁRIO (Excluindo GetNet e Limites)
        # =========================================================
        saldo_inicial_caixa = df_fim_mes[df_fim_mes['Tipo'] != 'Limite']['Saldo Inicial'].sum()
        
        if df_extratos is not None and not df_extratos.empty:
            df_ext_caixa = df_extratos[df_extratos['Conta Bancária'].apply(definir_tipo) != 'Limite'].copy()
            
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
            
        if saldo_inicial_caixa != 0 and not df_graficos.empty:
            df_graficos['Variação %'] = ((df_graficos['Saldo Final'] - saldo_inicial_caixa) / abs(saldo_inicial_caixa)) * 100
        else:
            df_graficos['Variação %'] = 0.0

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
        # 6. LER A ABA DE RENDIMENTOS
        # =========================================================
        df_rend_resumo = pd.DataFrame()
        rendimento_total_mes = 0.0
        try:
            df_rend = conn.read(worksheet="Rendimentos", ttl=0)
            if not df_rend.empty:
                df_rend.columns = [str(c).strip() for c in df_rend.columns]
                df_rend = df_rend.loc[:, ~df_rend.columns.duplicated()].copy()
                
                col_conta_rend = next((c for c in df_rend.columns if 'conta' in c.lower() or 'banco' in c.lower()), None)
                col_rendimento = next((c for c in df_rend.columns if 'rendimento' in c.lower() or 'l\u00edquido' in c.lower() or 'liquido' in c.lower()), None)
                
                if col_rendimento:
                    df_rend[col_rendimento] = df_rend[col_rendimento].apply(limpa_valor_bruto)
                    if col_conta_rend:
                        df_rend_resumo = df_rend.groupby(col_conta_rend)[col_rendimento].sum().reset_index()
                        df_rend_resumo.columns = ['Conta Bancária', 'Valor Líquido']
                    else:
                        rend_sum = df_rend[col_rendimento].sum()
                        df_rend_resumo = pd.DataFrame({'Conta Bancária': ['Aplicações Consolidadas'], 'Valor Líquido': [rend_sum]})

                    rendimento_total_mes = df_rend_resumo['Valor Líquido'].sum()
        except Exception:
            pass

        # =========================================================
        # 7. LER A ABA DE CUSTO DE OPORTUNIDADE
        # =========================================================
        custo_oportunidade_total = 0.0
        try:
            df_custos = conn.read(worksheet="Custo_Oportunidade", ttl=0)
            if not df_custos.empty:
                df_custos.columns = [str(c).strip() for c in df_custos.columns]
                df_custos = df_custos.loc[:, ~df_custos.columns.duplicated()].copy()
                col_custo = next((c for c in df_custos.columns if 'custo' in c.lower()), None)
                if col_custo:
                    df_custos[col_custo] = df_custos[col_custo].apply(limpa_valor_bruto)
                    custo_oportunidade_total = df_custos[col_custo].sum()
        except Exception:
            pass

        return df_fim_mes, df_graficos, df_rend_resumo, rendimento_total_mes, custo_oportunidade_total, 'Conta Bancária', entradas_operacionais, saidas_operacionais, mes_referencia
        
    except Exception as e:
        st.error(f"Erro fatal ao carregar dados: {e}")
        mes_fallback = pd.to_datetime(datetime.now().date()).replace(day=1)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, "", 0.0, 0.0, mes_fallback

# ==============================================================================
# CHAMADA PRINCIPAL E MONTAGEM DO PAINEL
# ==============================================================================
df_consolidado, df_graficos, df_rend_resumo, rendimento_total_mes, custo_oportunidade_total, col_conta, entradas_operacionais, saidas_operacionais, mes_referencia = carregar_dados()
if not col_conta: col_conta = 'Conta Bancária'
if df_consolidado.empty: st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs MENSAIS (Sem GetNet e Limites no Saldo Total)
# ==============================================================================
saldo_aplicado = df_consolidado[df_consolidado['Tipo'] == 'Aplicação']['Saldo Final'].sum()
saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()

saldo_getnet = df_consolidado[df_consolidado['Tipo'] == 'Limite']['Saldo Final'].sum()
saldo_conta_garantida = df_consolidado['Conta Garantida'].sum()
limites_totais = saldo_getnet + saldo_conta_garantida

# Saldo Total do Caixa REAL (Soma apenas Disponível + Aplicação)
saldo_total = saldo_disponivel + saldo_aplicado

entradas_mes = entradas_operacionais
saidas_mes = saidas_operacionais
resultado_liquido_mes = entradas_mes - saidas_mes

# ==============================================================================
# 4. GRÁFICOS
# ==============================================================================
fig_donut = go.Figure(data=[go.Pie(
    values=[saldo_aplicado, saldo_disponivel], 
    labels=['Aplicado', 'Disponível'], 
    hole=0.6, 
    marker=dict(colors=['#4e73df', '#1cc88a']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+percent'
)])
fig_donut.update_layout(
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=10, b=40, l=0, r=0), height=320,
    annotations=[dict(text=f"<b>R$ {saldo_total/1000000:,.1f}M</b><br>Saldo Total", x=0.5, y=0.48, font_size=12, showarrow=False)]
)

fig_combinado = go.Figure()
fig_combinado.add_trace(go.Bar(
    x=df_graficos['Data_Label'],
    y=df_graficos['Saldo Final'],
    name='Saldo Total',
    marker_color='#4e73df',
    text=[formatar_moeda(v) for v in df_graficos['Saldo Final']],
    textposition='outside',
    textfont=dict(size=10, color="#273043", weight="bold"),
    opacity=0.85,
    width=0.45
))
fig_combinado.update_layout(
    margin=dict(t=25, b=15, l=5, r=5), height=190, 
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
data_hoje = datetime.now().strftime('%d/%m/%Y')
meses_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
mes_str = meses_pt[mes_referencia.month - 1]
mes_referencia_nome = f"{mes_str}/{mes_referencia.year}"

st.markdown(f"""
<div class="dashboard-header">
    <div class="header-period">
        <div class="date">📅 {mes_referencia_nome}</div>
        <div class="label">Período de referência</div>
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
    (kpi_row[0], "🏛️", "SALDO TOTAL", f"R$ {saldo_total:,.2f}", "total"),
    (kpi_row[1], "💳", "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "disponivel"),
    (kpi_row[2], "🛡️", "LIMITES TOTAIS", f"R$ {limites_totais:,.2f}", "limites"),
    (kpi_row[3], "📊", "APLICAÇÕES", f"R$ {saldo_aplicado:,.2f}", "aplicacoes")
]
for col, icon, title, val, color in kp_data:
    col.markdown(f"<div class='kpi-card {color}'><div class='kpi-icon'>{icon}</div><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.1, 1.4, 1])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown("<div class='section-title'>MOVIMENTAÇÃO OPERACIONAL DO MÊS</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#1cc88a;'>⬇ ENTRADAS</div><div style='font-size:19px; font-weight:800;'>R$ {entradas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#e74a3b;'>⬆ SAÍDAS</div><div style='font-size:19px; font-weight:800;'>R$ {saidas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    
    if resultado_liquido_mes >= 0:
        m3.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#1cc88a;'>✅ RESULTADO LÍQUIDO</div><div style='font-size:19px; font-weight:800; color:#1cc88a;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)
    else:
        m3.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#e74a3b;'>🔻 RESULTADO LÍQUIDO</div><div style='font-size:19px; font-weight:800; color:#e74a3b;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown("<div class='section-title'>RESUMO APLICAÇÕES</div>", unsafe_allow_html=True)
    
    df_aplicacoes = df_consolidado[df_consolidado['Tipo'] == 'Aplicação'].copy()
    if not df_aplicacoes.empty:
        # Resgates é a soma de todas as saídas da conta de aplicação
        df_aplicacoes['Resgates'] = df_aplicacoes['Saída Op'] + df_aplicacoes['Saída Tr']
        
        if not df_rend_resumo.empty:
            df_app_table = pd.merge(df_aplicacoes, df_rend_resumo, on=col_conta, how='left')
        else:
            df_app_table = df_aplicacoes.copy()
            df_app_table['Valor Líquido'] = 0.0
            
        df_app_table['Valor Líquido'] = df_app_table['Valor Líquido'].fillna(0.0)
        
        # Montagem da Tabela de Aplicações
        html_app = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>BANCO</th><th class="valores">TOTAL APLICADO</th><th class="valores">RENDIMENTO</th><th class="valores">RESGATES</th></tr></thead><tbody>'
        
        tot_aplicado = 0
        tot_rend = 0
        tot_resg = 0
        
        for _, row in df_app_table.iterrows():
            banco = row[col_conta]
            aplicado = row['Saldo Final']
            rendimento = row['Valor Líquido']
            resgate = row['Resgates']
            
            tot_aplicado += aplicado
            tot_rend += rendimento
            tot_resg += resgate
            
            cor_rend = "#858796" if rendimento == 0 else ("#1cc88a" if rendimento > 0 else "#e74a3b")
            
            html_app += f'<tr><td style="font-size:12px; font-weight:600; color:#4b5563;">{banco}</td><td class="valores">{formatar_moeda(aplicado)}</td><td class="valores" style="color:{cor_rend};">{formatar_moeda(rendimento)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(resgate)}</td></tr>'
            
        cor_tot_rend = "#858796" if tot_rend == 0 else ("#1cc88a" if tot_rend > 0 else "#e74a3b")
        html_app += f'<tr class="linha-total"><td style="font-size:12px;">TOTAL</td><td class="valores">{formatar_moeda(tot_aplicado)}</td><td class="valores" style="color:{cor_tot_rend};">{formatar_moeda(tot_rend)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(tot_resg)}</td></tr>'
        html_app += '</tbody></table></div>'
        
        st.markdown(html_app, unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding: 10px; text-align:center; color: #888; font-size: 13px; border: 1px dashed #ccc; border-radius: 8px; margin-bottom: 8px;'>Nenhuma aplicação encontrada.</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='custo-oportunidade'><span>🔻 PERDA MENSAL (NÃO APLICADO)</span><span>- {formatar_moeda(custo_oportunidade_total)}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

col_tab, col_diario = st.columns([1.6, 1])

with col_tab:
    st.markdown(f"<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    df_view = df_consolidado[['Tipo', col_conta, 'Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final', 'Conta Garantida', 'Disponível']].copy()
    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final', 'Conta Garantida', 'Disponível']}
    
    html_tabela = '<div class="tabela-container tabela-bancos"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th class="valores">SALDO INICIAL</th><th class="valores">ENTRADA (OP.)</th><th class="valores">SAÍDA (OP.)</th><th class="valores">ENTRADA (INT.)</th><th class="valores">SAÍDA (INT.)</th><th class="valores">SALDO FINAL</th><th class="valores">DISPONÍVEL</th></tr></thead><tbody>'
    for idx, row in df_view.iterrows():
        cor_transf = "#858796" if row["Entrada Tr"] == 0 else "#1cc88a"
        cor_transf_saida = "#858796" if row["Saída Tr"] == 0 else "#e74a3b"
        html_tabela += f'<tr><td>{idx+1}</td><td>{row[col_conta]}</td><td style="font-size:11px; font-weight:700; color:#4b5563;">{row["Tipo"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(row["Entrada Op"])}</td><td class="valores">{formatar_moeda(row["Saída Op"])}</td><td class="valores" style="color:{cor_transf};">{formatar_moeda(row["Entrada Tr"])}</td><td class="valores" style="color:{cor_transf_saida};">{formatar_moeda(row["Saída Tr"])}</td><td class="valores">{formatar_moeda(row["Saldo Final"])}</td><td class="valores">{formatar_moeda(row["Disponível"])}</td></tr>'
    
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada Op"])}</td><td class="valores">{formatar_moeda(totais["Saída Op"])}</td><td class="valores" style="color:#858796;">-</td><td class="valores" style="color:#858796;">-</td><td class="valores">{formatar_moeda(totais["Saldo Final"])}</td><td class="valores">{formatar_moeda(totais["Disponível"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    
    st.markdown(html_tabela, unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; color:gray; margin-top:2px;'>* As colunas Entrada (INT.) e Saída (INT.) representam o fluxo de transferências internas e impactam o Saldo Final. O KPI de Movimentação Operacional ignora estas movimentações para mostrar o resultado real da empresa.</div>", unsafe_allow_html=True)

with col_diario:
    st.markdown("<div class='section-title'>SALDO DIÁRIO CONSOLIDADO</div>", unsafe_allow_html=True)
    
    df_diario_view = df_graficos[['Data_Label', 'Entrada', 'Saída', 'Saldo Final']].copy()
    df_diario_view = df_diario_view.sort_values(by='Data_Label', ascending=False)
    
    html_diario = '<div class="tabela-container" style="font-size:14px;"><table class="tabela-financeira"><thead><tr><th>DATA</th><th class="valores">ENTRADA (OP.)</th><th class="valores">SAÍDA (OP.)</th><th class="valores">SALDO FINAL</th></tr></thead><tbody>'
    
    for _, row in df_diario_view.iterrows():
        html_diario += f'<tr><td style="font-size:13px; font-weight:750; color:#273043;">{row["Data_Label"]}</td><td class="valores" style="color:#1cc88a;">{formatar_moeda(row["Entrada"])}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(row["Saída"])}</td><td class="valores" style="font-size:14px;">{formatar_moeda(row["Saldo Final"])}</td></tr>'
    html_diario += '</tbody></table></div>'
    st.markdown(html_diario, unsafe_allow_html=True)

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em {data_hoje}</div>", unsafe_allow_html=True)
