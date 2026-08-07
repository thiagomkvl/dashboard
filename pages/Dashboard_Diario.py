import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Diário", layout="wide", page_icon="📊")

# --- CUSTOM CSS (NOVAS CORES E ALINHAMENTO) ---
st.markdown("""
    <style>
    .main .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 95%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
    
    .stPlotlyChart { background-color: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }
    
    .kpi-card { background: white; border-radius: 6px; border-top: 4px solid #4e73df; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 10px; text-align: center; }
    .kpi-card.green { border-top-color: #1cc88a; }
    .kpi-card.purple { border-top-color: #6f42c1; }
    .kpi-card.cyan { border-top-color: #36b9cc; }
    .kpi-card.red { border-top-color: #e74a3b; }
    .kpi-card.orange { border-top-color: #f6c23e; }
    .kpi-title { font-size: 10px; font-weight: bold; color: #858796; text-transform: uppercase; }
    .kpi-value { font-size: 20px; font-weight: bold; color: #3a3b45; }
    
    .section-title { font-size: 13px; font-weight: bold; color: #1a2035; text-transform: uppercase; margin-bottom: 6px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
    .section-title-inline { font-size: 10px; font-weight: bold; color: #858796; text-transform: uppercase; }

    /* Tabela com cores e alinhamentos melhorados */
    .tabela-container { border: 1px solid #e3e6f0; border-radius: 4px; background: white; font-size: 11px; width: 100%; }
    .tabela-financeira { width: 100%; border-collapse: collapse; }
    .tabela-financeira th { background-color: #4e73df; color: white; font-weight: bold; text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e6f0; }
    .tabela-financeira td { padding: 5px 8px; border-bottom: 1px solid #f6f6f6; }
    .tabela-financeira .linha-total { background-color: #e2e6ea; font-weight: bold; border-top: 2px solid #ccc; }
    
    /* Colunas de valores alinhadas à direita */
    .tabela-financeira .valores { text-align: right; font-family: 'Courier New', monospace; }
    /* Coluna do Saldo Final com destaque em azul claro */
    .tabela-financeira .col-destaque { background-color: #eef2ff; font-weight: bold; color: #2c3e50; }
    
    .ind-item { display: flex; justify-content: space-between; font-size: 11px; padding: 2px 0; }
    .box-total-blue { background: #f8f9fc; border: 1px solid #4e73df; border-radius: 4px; padding: 6px; text-align: center; margin: 4px 0; }
    .box-total-grey { background: #e2e6ea; border: 1px solid #d1d3e2; border-radius: 4px; padding: 6px; text-align: center; margin: 4px 0; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÃO DE LEITURA E LIMPEZA
# ==============================================================================
def limpa_valor_bruto(valor):
    if pd.isna(valor) or str(valor).strip() == "" or str(valor).strip() == "-":
        return 0.0
    try:
        return float(str(valor).strip())
    except ValueError:
        return 0.0

def formatar_moeda(valor):
    if valor == 0: return "-"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# ==============================================================================
# 2. CARGA DE DADOS (COM LEITURA DE LIMITE GETNET)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    conn = conectar_sheets()
    if conn is None: return pd.DataFrame(), pd.DataFrame()
    try:
        df = conn.read(worksheet="Historico_Saldos", ttl=0)
        
        if df.empty:
            st.warning("A aba 'Historico_Saldos' está vazia.")
            return pd.DataFrame(), pd.DataFrame()
        
        df.columns = [c.strip() for c in df.columns]
        col_conta = 'Contas Bancárias' if 'Contas Bancárias' in df.columns else 'Conta Bancária'
        col_data = 'Data'
        
        df[col_data] = pd.to_datetime(df[col_data], format='%d/%m/%Y', errors='coerce')
        ultima_data = df[col_data].max()
        df_hoje = df[df[col_data] == ultima_data].copy()
        
        # Limpeza financeira
        for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']:
            if col in df_hoje.columns:
                df_hoje[col] = df_hoje[col].apply(limpa_valor_bruto)

        if 'Saída' in df_hoje.columns: 
            df_hoje['Saída'] = df_hoje['Saída'].apply(lambda x: -abs(x) if x != 0 else 0)
        if 'Entrada' in df_hoje.columns: 
            df_hoje['Entrada'] = df_hoje['Entrada'].apply(lambda x: abs(x))

        def definir_tipo(nome): 
            if 'getnet' in str(nome).lower():
                return 'Limite'
            return 'Aplicação' if ('aplicação' in str(nome).lower() or 'investimentos' in str(nome).lower()) else 'Disponível'
        
        df_hoje['Tipo'] = df_hoje[col_conta].apply(definir_tipo)
        df_hoje = df_hoje.sort_values(by=col_conta)

        # =========================================
        # GERAÇÃO DE MOCK PARA OS GRÁFICOS
        # =========================================
        saldo_total_hoje = df_hoje['Saldo Final'].sum()
        
        dados_graficos = []
        for i in range(7, -1, -1):
            data = ultima_data - timedelta(days=i)
            variacao = saldo_total_hoje * 0.01 * (i - 3) 
            saldo_mock = saldo_total_hoje + variacao
            entrada_mock = max(0, (saldo_mock - (saldo_total_hoje - 50000)) * 0.5)
            saida_mock = max(0, ((saldo_total_hoje - 50000) - saldo_mock) * 0.5)
            
            dados_graficos.append({
                'Data': data, 
                'Saldo': saldo_mock, 
                'Entrada': abs(entrada_mock), 
                'Saída': abs(saida_mock)
            })
        
        df_graficos = pd.DataFrame(dados_graficos)
        df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%d/%m')

        return df_hoje, df_graficos, col_conta
        
    except Exception as e:
        st.error(f"Erro fatal: {e}")
        return pd.DataFrame(), pd.DataFrame(), ""

df_hoje, df_graficos, col_conta = carregar_dados()
if df_hoje.empty: st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs
# ==============================================================================
saldo_aplicado = df_hoje[df_hoje['Tipo'] == 'Aplicação']['Saldo Final'].sum()
saldo_disponivel = df_hoje[df_hoje['Tipo'] == 'Disponível']['Saldo Final'].sum()
saldo_total = saldo_aplicado + saldo_disponivel

# Cálculo dos Limites Totais (GetNet + Contas Garantidas)
limite_getnet = df_hoje[df_hoje['Tipo'] == 'Limite']['Disponível'].sum()
limites_garantidos = df_hoje['Conta Garantida'].sum()
limites_totais = limite_getnet + limites_garantidos

saldo_com_limites = saldo_total + limites_totais
entradas_dia = df_hoje['Entrada'].sum()
saidas_dia = df_hoje['Saída'].sum()
resultado_liquido = entradas_dia + saidas_dia

# ==============================================================================
# 4. GERAÇÃO DOS GRÁFICOS
# ==============================================================================
# Gráfico 1: Distribuição do Caixa (Donut)
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
    showlegend=True, 
    legend=dict(orientation="h", yanchor="bottom", y=0, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=0, b=0, l=0, r=0), 
    height=230,
    annotations=[dict(text=f"<b>R$ {saldo_total:,.2f}</b><br>Saldo Total", x=0.5, y=0.48, font_size=12, showarrow=False)]
)

# Gráfico 2: Evolução do Saldo (Linha com %)
fig_linha = go.Figure()
fig_linha.add_trace(go.Scatter(
    x=df_graficos['Data_Label'], 
    y=df_graficos['Saldo'], 
    mode='lines+markers+text',
    line=dict(color='#4e73df', width=2),
    marker=dict(size=8, color='#4e73df'),
    text=[f"{((df_graficos['Saldo'].iloc[i] - df_graficos['Saldo'].iloc[i-1])/df_graficos['Saldo'].iloc[i-1])*100:.1f}%" if i > 0 else "" for i in range(len(df_graficos))],
    textposition="top center",
    textfont=dict(size=10, color="#333"),
    showlegend=False
))
fig_linha.update_layout(
    margin=dict(t=20, b=10, l=5, r=5), height=130, 
    xaxis=dict(tickfont=dict(size=10), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False)
)

# Gráfico 3: Análise de Saídas
if len(df_graficos) > 1:
    df_saidas = df_graficos[['Data_Label', 'Saída']].tail(7).copy()
    fig_saidas = px.bar(df_saidas, x='Data_Label', y='Saída')
    fig_saidas.update_traces(marker_color='#e74a3b', width=0.6)
    fig_saidas.update_layout(
        margin=dict(t=10, b=10, l=5, r=5), height=100,
        xaxis=dict(tickfont=dict(size=9), showgrid=False), 
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False,
        title=dict(text="<b>Saídas</b>", font=dict(size=11, color="#e74a3b"), x=0.5)
    )
else:
    fig_saidas = None

# Gráfico 4: Análise de Entradas
if len(df_graficos) > 1:
    df_entradas = df_graficos[['Data_Label', 'Entrada']].tail(7).copy()
    fig_entradas = px.bar(df_entradas, x='Data_Label', y='Entrada')
    fig_entradas.update_traces(marker_color='#1cc88a', width=0.6)
    fig_entradas.update_layout(
        margin=dict(t=10, b=10, l=5, r=5), height=100,
        xaxis=dict(tickfont=dict(size=9), showgrid=False), 
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False,
        title=dict(text="<b>Entradas</b>", font=dict(size=11, color="#1cc88a"), x=0.5)
    )
else:
    fig_entradas = None

# ==============================================================================
# 5. MONTAGEM DO PAINEL
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')

st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; margin-bottom: 5px; border-bottom: 1px solid #e3e6f0;">
    <div><b style="font-size:18px;">📅 {data_hoje}</b><br><span style="font-size:10px; color:gray;">Data de referência</span></div>
    <div style="text-align:center;"><h2 style="margin:0; color:#1a2035; font-size:22px;">PAINEL FINANCEIRO DIÁRIO</h2><p style="margin:0; font-size:11px; color:gray;">Controle Consolidado de Bancos</p></div>
    <div style="display:flex; gap:10px;">
        <div style="background:#d4edda; border-radius:12px; padding:1px 15px; text-align:center;"><span style="font-size:10px;">Transferências Entrada</span><br><b style="font-size:14px;">R$ 0,00</b></div>
        <div style="background:#f8d7da; border-radius:12px; padding:1px 15px; text-align:center;"><span style="font-size:10px;">Transferências Saída</span><br><b style="font-size:14px;">R$ 0,00</b></div>
    </div>
</div>
""", unsafe_allow_html=True)

# KPI's (7 Colunas - Substituindo Pendências por Limites)
kpi_row = st.columns(7)
kp_data = [
    (kpi_row[0], "🏛️", "SALDO TOTAL", f"R$ {saldo_total:,.2f}", ""),
    (kpi_row[1], "💳", "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "green"),
    (kpi_row[2], "🛡️", "LIMITES TOTAIS", f"R$ {limites_totais:,.2f}", "cyan"), # NOVO KPI
    (kpi_row[3], "📊", "SALDO APLICADO", f"R$ {saldo_aplicado:,.2f}", "purple"),
    (kpi_row[4], "⬇️", "ENTRADAS DO DIA", f"R$ {entradas_dia:,.2f}", "green"),
    (kpi_row[5], "⬆️", "SAÍDAS DO DIA", f"R$ {abs(saidas_dia):,.2f}", "red"),
    (kpi_row[6], "💎", "SALDO + LIMITES", f"R$ {saldo_com_limites:,.2f}", "orange")
]
for col, icon, title, val, color in kp_data:
    col.markdown(f"<div class='kpi-card {color}'><div style='font-size:12px;'>{icon}</div><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.1, 1.4, 1])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown("<div class='section-title'>MOVIMENTAÇÃO DO DIA</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div style='background:#d4edda; border-radius:4px; padding:6px; text-align:center;'><span class='section-title-inline'>⬇ ENTRADAS</span><br><b>R$ {entradas_dia:,.2f}</b></div>", unsafe_allow_html=True)
    m2.markdown(f"<div style='background:#f8d7da; border-radius:4px; padding:6px; text-align:center;'><span class='section-title-inline'>⬆ SAÍDAS</span><br><b>R$ {abs(saidas_dia):,.2f}</b></div>", unsafe_allow_html=True)
    m3.markdown(f"<div style='background:#fff3cd; border-radius:4px; padding:6px; text-align:center;'><span class='section-title-inline'>RESULTADO LÍQUIDO</span><br><b>R$ {resultado_liquido:,.2f}</b></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_linha, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown("<div class='section-title'>LIQUIDEZ BANCÁRIA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Caixa Disponível:</span> <b>R$ {saldo_disponivel:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Limites Bancários:</span> <b>R$ {limites_totais:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-total-blue'><b>LIQUIDEZ TOTAL</b><br><span style='font-size:15px;'>R$ {saldo_com_limites:,.2f}</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:12px;'>INDICADORES DE TESOURARIA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos monitorados</span> <b>{len(df_hoje)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Aplicação</span> <b>{len(df_hoje[df_hoje['Tipo'] == 'Aplicação'])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Limite</span> <b>{len(df_hoje[df_hoje['Conta Garantida']>0]) + (1 if limite_getnet > 0 else 0)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span style='color:#e74a3b;'>Mov. Saída</span> <b style='color:#e74a3b;'>{len(df_hoje[df_hoje['Saída'] != 0])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-total-grey'><b>SALDO CONSOLIDADO</b><br><span style='font-size:14px;'>R$ {saldo_total:,.2f}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

col_tab, col_inf = st.columns([1.6, 1])

with col_tab:
    st.markdown("<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    df_view = df_hoje[['Tipo', col_conta, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']].copy()
    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']}
    
    html_tabela = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th>SALDO INICIAL</th><th>ENTRADA</th><th>SAÍDA</th><th class="valores">SALDO FINAL</th><th>CONTA GARANTIDA</th><th>DISPONÍVEL</th></tr></thead><tbody>'
    for idx, row in df_view.iterrows():
        # Adiciona a classe col-destaque na célula do Saldo Final
        html_tabela += f'<tr><td>{idx+1}</td><td>{row[col_conta]}</td><td style="font-size:10px;">{row["Tipo"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(row["Entrada"])}</td><td class="valores">{formatar_moeda(row["Saída"])}</td><td class="valores col-destaque">{formatar_moeda(row["Saldo Final"])}</td><td class="valores">{formatar_moeda(row["Conta Garantida"])}</td><td class="valores">{formatar_moeda(row["Disponível"])}</td></tr>'
    
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada"])}</td><td class="valores">{formatar_moeda(totais["Saída"])}</td><td class="valores col-destaque">{formatar_moeda(totais["Saldo Final"])}</td><td class="valores">{formatar_moeda(totais["Conta Garantida"])}</td><td class="valores">{formatar_moeda(totais["Disponível"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; color:gray; margin-top:2px;'><span style='display:inline-block; width:10px; height:10px; background:#1cc88a; border-radius:2px; margin-right:4px;'></span> Disponível <span style='display:inline-block; width:10px; height:10px; background:#4e73df; border-radius:2px; margin-left:15px; margin-right:4px;'></span> Aplicação</div>", unsafe_allow_html=True)

with col_inf:
    st.markdown("<div class='section-title'>ANÁLISE DE SAÍDAS</div>", unsafe_allow_html=True)
    if fig_saidas:
        st.plotly_chart(fig_saidas, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown("<div class='box-card' style='text-align:center; padding:10px; color:gray; font-size:11px;'>Sem dados suficientes.</div>", unsafe_allow_html=True)
        
    st.markdown("<div class='section-title'>ANÁLISE DE ENTRADAS</div>", unsafe_allow_html=True)
    if fig_entradas:
        st.plotly_chart(fig_entradas, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown("<div class='box-card' style='text-align:center; padding:10px; color:gray; font-size:11px;'>Sem dados suficientes.</div>", unsafe_allow_html=True)

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em {data_hoje}</div>", unsafe_allow_html=True)
