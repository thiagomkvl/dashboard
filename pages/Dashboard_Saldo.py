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
        --success: #159570;
        --danger: #d94a4a;
        --warning: #c58a16;
        --info: #2388a7;
        --purple: #7654c8;
        --shadow: 0 4px 15px rgba(24, 39, 75, 0.08);
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

    /* KPIs SÓLIDOS COM GRADIENTE E TRANSPARÊNCIA */
    .kpi-card { position: relative; overflow: hidden; min-height: 85px; padding: 14px 18px 12px; border-radius: 10px; box-shadow: var(--shadow); text-align: left; border: none; backdrop-filter: blur(5px); }
    .kpi-card.total { background: linear-gradient(135deg, rgba(49, 87, 213, 0.95), rgba(78, 115, 223, 0.75)); }
    .kpi-card.disponivel { background: linear-gradient(135deg, rgba(21, 149, 112, 0.95), rgba(28, 200, 138, 0.75)); }
    .kpi-card.aplicacoes { background: linear-gradient(135deg, rgba(118, 84, 200, 0.95), rgba(143, 104, 228, 0.75)); }
    .kpi-card.limites { background: linear-gradient(135deg, rgba(35, 136, 167, 0.95), rgba(54, 185, 204, 0.75)); }
    
    .kpi-icon { width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 6px; border-radius: 7px; background: rgba(255,255,255,0.2); font-size: 14px; color: white; }
    .kpi-title { font-size: 10px; line-height: 1; font-weight: 750; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.65px; margin-bottom: 4px; }
    .kpi-value { font-size: 24px; line-height: 1.15; font-weight: 800; color: #ffffff; letter-spacing: -0.35px; white-space: nowrap; }

    /* Seções */
    .section-title { display: flex; align-items: center; min-height: 25px; margin-bottom: 5px; padding: 0 0 5px; border-bottom: 1px solid var(--border); color: var(--text); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.75px; }
    .section-title::before { content: ""; width: 3px; height: 12px; margin-right: 7px; border-radius: 4px; background: var(--primary); }
    .section-title-inline { font-size: 9px; font-weight: 750; color: var(--muted); text-transform: uppercase; letter-spacing: 0.45px; }
    .movement-card { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-soft); }

    /* Tabelas */
    .tabela-container { overflow-x: auto; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); box-shadow: 0 2px 8px rgba(0,0,0,0.03); font-size: 12px; width: 100%; margin-bottom: 8px; }
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; }
    .tabela-financeira th { background: #f7f9fc; color: #596274; font-size: 10px; font-weight: 800; text-align: left; padding: 11px 12px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.35px; }
    .tabela-financeira td { padding: 11px 12px; border-bottom: 1px solid #f0f2f6; font-size: 13px; font-weight: 550; color: #273043; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #fafbfe; }
    .tabela-financeira .linha-total { background: #eef2f7; border-top: 2px solid #d8dee8; }
    .tabela-financeira .linha-total td { color: #172033; font-weight: 800; }
    
    /* Alinhamento de Números para a Esquerda e Tamanho */
    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: left !important; font-weight: 750; font-variant-numeric: tabular-nums; font-size: 14px; }
    .tabela-financeira td.valor-destaque { font-size: 16px !important; font-weight: 800; color: #1a2035; }
    
    hr { border: 0 !important; border-top: 1px solid var(--border) !important; margin: 15px 0 !important; }
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
        if val == 0: return "-"
        prefixo = "+ " if val > 0 else "- "
        return f"{prefixo}R$ {abs(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "-"

# ==============================================================================
# 2. CARGA DE DADOS (BASE ZERO + TIMELINE COM MAPEAMENTO POSICIONAL)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    conn = conectar_sheets()
    mes_referencia = pd.to_datetime(datetime.now().date()).replace(day=1)
    
    if conn is None: 
        return pd.DataFrame(), pd.DataFrame(), 'Conta Bancária', 0.0, 0.0, mes_referencia
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
        # 2. EXTRATOS (Com Leitura da Nova Coluna I)
        # =========================================================
        df_extratos = None
        proximo_mes = mes_referencia + relativedelta(months=1)
        
        try:
            df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
            if not df_ext.empty:
                while len(df_ext.columns) < 9:
                    df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""
                
                df_ext = df_ext.iloc[:, [0, 1, 4, 5, 7, 8]].copy()
                df_ext.columns = ['Conta Bancária', 'Data', 'Vl Débito', 'Vl Crédito', 'Tipo de Transação', 'Categoria App']

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
                
                # Regra Operacional baseada 100% na COLUNA H
                serie_tipo = df_ext['Tipo de Transação'].apply(normalizar_texto)
                df_ext['É Transf'] = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')

                df_ext['Cred_Op'] = df_ext['Vl Crédito'].where(~df_ext['É Transf'], 0.0)
                df_ext['Deb_Op'] = df_ext['Vl Débito'].where(~df_ext['É Transf'], 0.0)
                df_ext['Cred_Tr'] = df_ext['Vl Crédito'].where(df_ext['É Transf'], 0.0)
                df_ext['Deb_Tr'] = df_ext['Vl Débito'].where(df_ext['É Transf'], 0.0)
                
                # --- LÓGICA DE APLICAÇÕES ISOLADA (COLUNA I) ---
                serie_cat_app = df_ext['Categoria App'].apply(normalizar_texto)
                
                # Aplicação e Rendimento = Vl Crédito na conta de investimento
                df_ext['App_Aplic'] = df_ext['Vl Crédito'].where(serie_cat_app.str.contains('aplicacao'), 0.0)
                df_ext['App_Rend']  = df_ext['Vl Crédito'].where(serie_cat_app.str.contains('rendimento'), 0.0)
                
                # Resgate = Vl Débito na conta de investimento
                df_ext['App_Resg']  = df_ext['Vl Débito'].where(serie_cat_app.str.contains('resgate'), 0.0)
                
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
                'App_Aplic': 'sum',
                'App_Resg': 'sum',
                'App_Rend': 'sum'
            }).reset_index()
            
            df_fim_mes = df_fim_mes.merge(df_extratos_grouped, on='Conta Bancária', how='outer')
            df_fim_mes['Saldo Inicial'] = df_fim_mes['Saldo Inicial'].fillna(0)
            df_fim_mes['Conta Garantida'] = df_fim_mes['Conta Garantida'].fillna(0)
            
            df_fim_mes['Entrada Op'] = df_fim_mes['Cred_Op'].fillna(0)
            df_fim_mes['Saída Op'] = df_fim_mes['Deb_Op'].fillna(0)
            df_fim_mes['Entrada Tr'] = df_fim_mes['Cred_Tr'].fillna(0)
            df_fim_mes['Saída Tr'] = df_fim_mes['Deb_Tr'].fillna(0)
            
            # Cestas de aplicação isoladas para o Resumo
            df_fim_mes['App_Aplic'] = df_fim_mes['App_Aplic'].fillna(0)
            df_fim_mes['App_Resg'] = df_fim_mes['App_Resg'].fillna(0)
            df_fim_mes['App_Rend'] = df_fim_mes['App_Rend'].fillna(0)
        else:
            df_fim_mes['Entrada Op'] = 0.0
            df_fim_mes['Saída Op'] = 0.0
            df_fim_mes['Entrada Tr'] = 0.0
            df_fim_mes['Saída Tr'] = 0.0
            df_fim_mes['App_Aplic'] = 0.0
            df_fim_mes['App_Resg'] = 0.0
            df_fim_mes['App_Rend'] = 0.0

        df_fim_mes['Tipo'] = df_fim_mes['Conta Bancária'].apply(definir_tipo)
        df_fim_mes['Saldo Final'] = df_fim_mes['Saldo Inicial'] + df_fim_mes['Entrada Op'] - df_fim_mes['Saída Op'] + df_fim_mes['Entrada Tr'] - df_fim_mes['Saída Tr']

        # =========================================================
        # 4. GRÁFICO DIÁRIO E EVOLUÇÃO (Caixa Real)
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

        return df_fim_mes, df_graficos, 'Conta Bancária', entradas_operacionais, saidas_operacionais, mes_referencia
        
    except Exception as e:
        st.error(f"Erro fatal ao carregar dados: {e}")
        mes_fallback = pd.to_datetime(datetime.now().date()).replace(day=1)
        return pd.DataFrame(), pd.DataFrame(), 'Conta Bancária', 0.0, 0.0, mes_fallback

# ==============================================================================
# CHAMADA PRINCIPAL E MONTAGEM DO PAINEL
# ==============================================================================
df_consolidado, df_graficos, col_conta, entradas_operacionais, saidas_operacionais, mes_referencia = carregar_dados()
if not col_conta: col_conta = 'Conta Bancária'
if df_consolidado.empty: st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs MENSAIS
# ==============================================================================
saldo_aplicado = df_consolidado[df_consolidado['Tipo'] == 'Aplicação']['Saldo Final'].sum()
saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()

# Limites
saldo_getnet = df_consolidado[df_consolidado['Tipo'] == 'Limite']['Saldo Final'].sum()
saldo_conta_garantida = df_consolidado['Conta Garantida'].sum()
limites_totais = saldo_getnet + saldo_conta_garantida

# Saldo Total REAL (Soma apenas Conta Corrente + Aplicação)
saldo_total = saldo_disponivel + saldo_aplicado

entradas_mes = entradas_operacionais
saidas_mes = saidas_operacionais
resultado_liquido_mes = entradas_mes - saidas_mes

# ==============================================================================
# 4. GRÁFICOS E DATAS
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')
data_inicio_str = mes_referencia.strftime('%d/%m/%Y')

if not df_graficos.empty and 'Data' in df_graficos.columns:
    data_fim_str = df_graficos['Data'].max().strftime('%d/%m/%Y')
else:
    data_fim_str = data_hoje
    
periodo_str = f"{data_inicio_str} - {data_fim_str}"

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
    text=[formatar_abreviado(v) for v in df_graficos['Saldo Final']],
    textposition='outside',
    textfont=dict(size=13, color="#1a2035", weight="bold"),
    opacity=0.9,
    width=0.45
))
fig_combinado.update_layout(
    margin=dict(t=25, b=15, l=5, r=5), height=210, 
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
        <div class="date">📅 {periodo_str}</div>
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
    (kpi_row[2], "📊", "APLICAÇÕES", f"R$ {saldo_aplicado:,.2f}", "aplicacoes"),
    (kpi_row[3], "🛡️", "LIMITES TOTAIS", f"R$ {limites_totais:,.2f}", "limites")
]
for col, icon, title, val, color in kp_data:
    col.markdown(f"<div class='kpi-card {color}'><div class='kpi-icon'>{icon}</div><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.1, 1.4, 1])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(f"<div class='section-title'>MOVIMENTAÇÃO OPERACIONAL DO MÊS <span style='margin-left:auto; font-size:11px; color:#1a2035; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
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
        # Matemática Inteligente isolada da Coluna I
        df_aplicacoes['Total Aplicado'] = df_aplicacoes['Saldo Inicial'] + df_aplicacoes['App_Aplic']
        df_aplicacoes['Rendimento'] = df_aplicacoes['App_Rend']
        df_aplicacoes['Resgates'] = df_aplicacoes['App_Resg']
        
        # Exclui linhas sem histórico
        df_aplicacoes = df_aplicacoes[(df_aplicacoes['Total Aplicado'] != 0) | (df_aplicacoes['Rendimento'] != 0) | (df_aplicacoes['Resgates'] != 0)]
        
        if not df_aplicacoes.empty:
            html_app = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>BANCO</th><th class="valores">TOTAL APLICADO</th><th class="valores">RENDIMENTO</th><th class="valores">RESGATES</th></tr></thead><tbody>'
            
            tot_aplicado = 0; tot_rend = 0; tot_resg = 0
            
            for _, row in df_aplicacoes.iterrows():
                banco = row[col_conta]
                aplicado = row['Total Aplicado']
                rendimento = row['Rendimento']
                resgate = row['Resgates']
                
                tot_aplicado += aplicado; tot_rend += rendimento; tot_resg += resgate
                
                cor_rend = "#858796" if rendimento == 0 else ("#1cc88a" if rendimento > 0 else "#e74a3b")
                html_app += f'<tr><td style="font-size:12px; font-weight:600; color:#4b5563;">{banco}</td><td class="valores">{formatar_moeda(aplicado)}</td><td class="valores" style="color:{cor_rend};">{formatar_moeda(rendimento)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(resgate)}</td></tr>'
                
            cor_tot_rend = "#858796" if tot_rend == 0 else ("#1cc88a" if tot_rend > 0 else "#e74a3b")
            html_app += f'<tr class="linha-total"><td style="font-size:12px;">TOTAL</td><td class="valores">{formatar_moeda(tot_aplicado)}</td><td class="valores" style="color:{cor_tot_rend};">{formatar_moeda(tot_rend)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(tot_resg)}</td></tr>'
            html_app += '</tbody></table></div>'
            st.markdown(html_app, unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding: 10px; text-align:center; color: #888; font-size: 13px; border: 1px dashed #ccc; border-radius: 8px; margin-bottom: 8px;'>Nenhuma aplicação encontrada com movimentação.</div>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

col_tab, col_diario = st.columns([1.6, 1])

with col_tab:
    st.markdown(f"<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    df_view = df_consolidado[['Tipo', col_conta, 'Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final']].copy()
    
    # Motor de Ordenação por Camadas (Filtra "Aplicações" antes para evitar colisões com "Conta Corrente")
    def get_ordem(banco_nome):
        nome = str(banco_nome).lower().strip()
        
        # 1. Tratamento isolado para os investimentos
        if "aplicação" in nome or "aplicacao" in nome or "invest" in nome:
            if "unicred" in nome: return 11
            if "bradesco" in nome: return 12
            if "santander" in nome: return 13
            if "itaú" in nome or "itau" in nome: return 14 
            return 50 # Outras aplicações
            
        # 2. Tratamento exato para o restante na ordem solicitada
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
        if "getnet" in nome: return 100 # Fica por último fixo
        
        return 999

    df_view['Ordem'] = df_view[col_conta].apply(get_ordem)
    df_view = df_view.sort_values('Ordem').drop(columns=['Ordem'])

    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada Op', 'Saída Op', 'Entrada Tr', 'Saída Tr', 'Saldo Final']}
    
    html_tabela = '<div class="tabela-container tabela-bancos"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th class="valores">SALDO INICIAL</th><th class="valores">ENTRADA (OP.)</th><th class="valores">SAÍDA (OP.)</th><th class="valores">ENTRADA (INT.)</th><th class="valores">SAÍDA (INT.)</th><th class="valores">SALDO FINAL</th></tr></thead><tbody>'
    for idx, row in enumerate(df_view.itertuples()):
        cor_transf = "#858796" if row._6 == 0 else "#1cc88a"
        cor_transf_saida = "#858796" if row._7 == 0 else "#e74a3b"
        html_tabela += f'<tr><td>{idx+1}</td><td>{row._2}</td><td style="font-size:11px; font-weight:700; color:#4b5563;">{row.Tipo}</td><td class="valores">{formatar_moeda(row._3)}</td><td class="valores">{formatar_moeda(row._4)}</td><td class="valores">{formatar_moeda(row._5)}</td><td class="valores" style="color:{cor_transf};">{formatar_moeda(row._6)}</td><td class="valores" style="color:{cor_transf_saida};">{formatar_moeda(row._7)}</td><td class="valores valor-destaque">{formatar_moeda(row._8)}</td></tr>'
    
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada Op"])}</td><td class="valores">{formatar_moeda(totais["Saída Op"])}</td><td class="valores" style="color:#858796;">-</td><td class="valores" style="color:#858796;">-</td><td class="valores valor-destaque">{formatar_moeda(totais["Saldo Final"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)

with col_diario:
    st.markdown("<div class='section-title'>SALDO DIÁRIO CONSOLIDADO</div>", unsafe_allow_html=True)
    
    df_diario_view = df_graficos[['Data_Label', 'Saldo Final', 'Entrada', 'Saída']].copy()
    df_diario_view = df_diario_view.sort_values(by='Data_Label', ascending=False)
    
    html_diario = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>DATA</th><th class="valores">SALDO FINAL</th><th class="valores">ENTRADA (OP.)</th><th class="valores">SAÍDA (OP.)</th></tr></thead><tbody>'
    for _, row in df_diario_view.iterrows():
        html_diario += f'<tr><td style="font-size:13px; font-weight:750; color:#273043;">{row["Data_Label"]}</td><td class="valores valor-destaque">{formatar_moeda(row["Saldo Final"])}</td><td class="valores" style="color:#1cc88a;">{formatar_moeda(row["Entrada"])}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(row["Saída"])}</td></tr>'
    html_diario += '</tbody></table></div>'
    st.markdown(html_diario, unsafe_allow_html=True)

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em {data_hoje}</div>", unsafe_allow_html=True)
