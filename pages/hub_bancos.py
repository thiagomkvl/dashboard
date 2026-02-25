import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- FUNÇÃO UTILITÁRIA ---
def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Hub Multi Bancos", page_icon="🏦", layout="wide")

# --- CUSTOM CSS (Inspirado no Design de Referência) ---
st.markdown("""
    <style>
    .main-bg { background-color: #F4F7FE; }
    
    /* Cards Brancos */
    .dashboard-card {
        background-color: #FFFFFF; 
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
        height: 100%;
    }
    
    /* Textos dos KPIs */
    .kpi-label { font-size: 14px; color: #A3AED0; font-weight: 500; margin-bottom: 5px; }
    .kpi-value-main { font-size: 32px; font-weight: 700; color: #2B3674; margin-bottom: 0px; line-height: 1.2;}
    .kpi-value-sub { font-size: 24px; font-weight: 700; color: #2B3674; margin-bottom: 0px;}
    
    /* Cards Coloridos (Inspiração da Imagem) */
    .color-card { padding: 20px; border-radius: 16px; color: white; margin-bottom: 10px; display: flex; flex-direction: column; justify-content: center;}
    .card-blue { background: linear-gradient(135deg, #4481EB 0%, #04BEFE 100%); }
    .card-green { background: linear-gradient(135deg, #20E2D7 0%, #F9FEA5 100%); color: #2B3674 !important; }
    .card-orange { background: linear-gradient(135deg, #FF9A44 0%, #FC6076 100%); }
    
    .color-card-title { font-size: 13px; font-weight: 600; opacity: 0.9; margin-bottom: 5px;}
    .color-card-value { font-size: 22px; font-weight: bold; }
    
    /* Botão Sincronizar */
    .sync-btn { background-color: #4318FF; color: white; padding: 10px 20px; border-radius: 10px; font-weight: bold; text-align: center; cursor: pointer; float: right;}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. DADOS DAS CONTAS (Fornecidos por você)
# ==============================================================================
dados_contas = [
    {"Banco": "Banco do Brasil", "Tipo": "C.C", "Saldo": 8366.95},
    {"Banco": "Caixa-Itaú 1566-8*", "Tipo": "C.C", "Saldo": 128542.12},
    {"Banco": "Unicred", "Tipo": "C.C", "Saldo": 157429.54},
    {"Banco": "Unicred", "Tipo": "Aplicação", "Saldo": 10211640.00},
    {"Banco": "Uniprime", "Tipo": "C.C", "Saldo": 1920640.24},
    {"Banco": "Santander", "Tipo": "Aplicação", "Saldo": 839457.95},
    {"Banco": "Bradesco 70860", "Tipo": "C.C", "Saldo": 1.00},
    {"Banco": "Bradesco", "Tipo": "Aplicação", "Saldo": 56804.47},
    {"Banco": "Bradesco/Comerc", "Tipo": "C.C", "Saldo": 10000.00},
    {"Banco": "Sicoob", "Tipo": "C.C", "Saldo": 33817.08},
    {"Banco": "GetNet", "Tipo": "Recebíveis", "Saldo": 3195012.40}
]

df_contas = pd.DataFrame(dados_contas)

# Cálculos Consolidados
total_geral = df_contas["Saldo"].sum()
total_aplicacao = df_contas[df_contas["Tipo"] == "Aplicação"]["Saldo"].sum()
total_cc = df_contas[df_contas["Tipo"].isin(["C.C", "Recebíveis"])]["Saldo"].sum()
qtd_contas = len(df_contas)

# ==============================================================================
# 2. CABEÇALHO (KPIs e Botão de Sync API)
# ==============================================================================
st.markdown("### 🌐 Hub Multi Bancos - Open Finance")
st.caption("Consolidação via API Santander & BACEN")

c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1.5])

with c1:
    st.markdown(f"""
    <div class='dashboard-card'>
        <div class='kpi-label'>Liquidez Total (Consolidada)</div>
        <div class='kpi-value-main'>{formatar_real(total_geral)}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class='dashboard-card'>
        <div class='kpi-label'>Contas Ativas</div>
        <div class='kpi-value-sub'>{qtd_contas}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class='dashboard-card' style='background-color: #FFF4E5;'>
        <div class='kpi-label' style='color: #FF9A44;'>Sincronização API</div>
        <div class='kpi-value-sub' style='color: #FF9A44;'>Online</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("<div style='padding-top: 30px;'><div class='sync-btn'>🔄 Sincronizar Open Finance</div></div>", unsafe_allow_html=True)

# ==============================================================================
# 3. LINHA DO MEIO (Gráfico Donut + Cards Coloridos)
# ==============================================================================
col_donut, col_cards = st.columns([1.5, 1])

with col_donut:
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight:bold; color:#2B3674; margin-bottom: 10px;'>Distribuição de Liquidez</div>", unsafe_allow_html=True)
    
    # Gráfico de Donut (Inspirado na imagem)
    labels = ['Aplicações/Investimentos', 'Conta Corrente/Livre', 'Recebíveis (GetNet)']
    values = [total_aplicacao, df_contas[df_contas['Tipo'] == 'C.C']['Saldo'].sum(), df_contas[df_contas['Tipo'] == 'Recebíveis']['Saldo'].sum()]
    colors = ['#4318FF', '#05CD99', '#FF9A44']
    
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.7, marker=dict(colors=colors))])
    fig_donut.update_layout(
        showlegend=True, 
        margin=dict(t=10, b=10, l=10, r=10), 
        height=220,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
    )
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_cards:
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight:bold; color:#2B3674; margin-bottom: 15px;'>Maiores Posições (Top 3)</div>", unsafe_allow_html=True)
    
    # Cards Coloridos da Imagem
    st.markdown(f"""
        <div class='color-card card-blue'>
            <div class='color-card-title'>Unicred - Aplicação</div>
            <div class='color-card-value'>{formatar_real(10211640.00)}</div>
        </div>
        <div class='color-card card-green'>
            <div class='color-card-title'>GetNet (Recebíveis)</div>
            <div class='color-card-value'>{formatar_real(3195012.40)}</div>
        </div>
        <div class='color-card card-orange'>
            <div class='color-card-title'>Uniprime - C.C</div>
            <div class='color-card-value'>{formatar_real(1920640.24)}</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 4. LINHA INFERIOR (Gráficos Combinados da Imagem e Tabela)
# ==============================================================================
col_chart1, col_chart2 = st.columns(2)

# Mockup de Dados Temporais para os Gráficos
dias = [(datetime.now() - timedelta(days=i)).strftime('%d/%m') for i in range(14, -1, -1)]
bar_data1 = np.random.uniform(10, 15, 15) * 1000000
line_data1 = bar_data1 * 1.1 + np.random.uniform(1, 3, 15) * 1000000

bar_data2 = np.random.uniform(2, 5, 15) * 1000000
area_data2 = np.cumsum(bar_data2) * 0.5 + 10000000

with col_chart1:
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight:bold; color:#2B3674; margin-bottom: 10px;'>Evolução Consolidada (Últimos 15 dias)</div>", unsafe_allow_html=True)
    
    fig_mix1 = go.Figure()
    fig_mix1.add_trace(go.Bar(x=dias, y=bar_data1, name='Saldo C.C', marker_color='#4318FF', opacity=0.8))
    fig_mix1.add_trace(go.Scatter(x=dias, y=line_data1, name='Liquidez Total', mode='lines+markers', fill='tozeroy', fillcolor='rgba(5, 205, 153, 0.2)', line=dict(color='#05CD99', width=3)))
    
    fig_mix1.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=250, legend=dict(orientation="h", y=1.1, x=0), dragmode='pan')
    fig_mix1.update_yaxes(showgrid=True, gridcolor='#E9ECEF')
    fig_mix1.update_xaxes(showgrid=False)
    st.plotly_chart(fig_mix1, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_chart2:
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight:bold; color:#2B3674; margin-bottom: 10px;'>Rentabilidade das Aplicações (Santander/Unicred)</div>", unsafe_allow_html=True)
    
    fig_mix2 = go.Figure()
    fig_mix2.add_trace(go.Bar(x=dias, y=bar_data2, name='Aportes', marker_color='#FF9A44', opacity=0.8))
    fig_mix2.add_trace(go.Scatter(x=dias, y=area_data2, name='Saldo Aplicado', mode='lines', fill='tozeroy', fillcolor='rgba(67, 24, 255, 0.1)', line=dict(color='#4318FF', width=3)))
    
    fig_mix2.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=250, legend=dict(orientation="h", y=1.1, x=0), dragmode='pan')
    fig_mix2.update_yaxes(showgrid=True, gridcolor='#E9ECEF')
    fig_mix2.update_xaxes(showgrid=False)
    st.plotly_chart(fig_mix2, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 5. TABELA ANALÍTICA DE CONTAS
# ==============================================================================
st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
st.markdown("<div style='font-weight:bold; color:#2B3674; margin-bottom: 15px; font-size: 18px;'>Extrato de Contas Conectadas via Open Finance</div>", unsafe_allow_html=True)

# Formatação visual para a tabela
df_view = df_contas.copy()
df_view['Saldo Disponível'] = df_view['Saldo'].apply(formatar_real)
df_view = df_view.sort_values(by='Saldo', ascending=False).drop(columns=['Saldo'])

st.dataframe(
    df_view,
    hide_index=True,
    use_container_width=True,
    height=400
)
st.markdown("</div>", unsafe_allow_html=True)
