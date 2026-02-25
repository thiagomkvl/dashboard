import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Gerencial - SOS Cardio", page_icon="📊", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .status-dot { height: 12px; width: 12px; background-color: #00C851; border-radius: 50%; display: inline-block; margin-left: 5px; margin-right: 20px;}
    .status-text { font-size: 16px; font-weight: bold; color: #4F4F4F; display: inline-block; }
    
    .kpi-card {
        background-color: #F8F9FA; 
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
        border-left: 5px solid #4e73df;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 20px;
    }
    .kpi-title { font-size: 14px; color: #6c757d; font-weight: 600; margin-bottom: 5px;}
    .kpi-value { font-size: 28px; font-weight: bold; color: #343a40;}
    .kpi-delta { font-size: 13px; font-weight: bold; margin-top: 5px;}
    .delta-up { color: #1cc88a; }
    .delta-down { color: #e74a3b; }
    </style>
""", unsafe_allow_html=True)

def formatar_k(valor):
    if valor >= 1000000: return f"R$ {valor/1000000:.1f}M"
    if valor >= 1000: return f"R$ {valor/1000:.0f}k"
    return f"R$ {valor:.2f}"

# ==============================================================================
# 1. HEADER
# ==============================================================================
st.markdown("""
    <div style='display: flex; align-items: center; margin-bottom: 20px;'>
        <div class='status-text'>Planejamento Estratégico & FCx</div><span class='status-dot'></span>
        <div class='status-text'>Bases de Projeção Ativas</div><span class='status-dot'></span>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. DADOS (Baseados na planilha de FCx Projeção 2026 e Faturamento)
# ==============================================================================
# Meses do ano
meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

# Faturamento Realizado 2025 vs Projetado 2026 (Com base nos 14.7M de Jan/25)
fat_realizado_25 = [14789523, 15162673, 14689192, 15786600, 15200000, 14900000, 15500000, 16100000, 15800000, 16200000, 15900000, 16500000]
fat_projetado_26 = [v * 0.9 for v in fat_realizado_25] # Aplicando o redutor de 0.9 da planilha
fat_realizado_26 = [13500000, 13800000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # Simulação: Apenas Jan e Fev consolidados em 2026

# Fluxo de Caixa Diário/Mensal 2026 (Saldos Iniciais projetados)
saldo_inicial_26 = [17710825, 9776541, 6742379, 4234696, 2893941, 2202602, 1381900, 12155811, 12066452, 12347873, 13870899, 11673453]
despesas_fin =     [5966344, 911344,  911344,  911344,  911344,  911344,  911344,  911344,   911344,   911344,   911344,   911344]

# ==============================================================================
# 3. KPIs SUPERIORES
# ==============================================================================
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class='kpi-card' style='border-left-color: #4e73df;'>
        <div class='kpi-title'>Faturamento Realizado (YTD)</div>
        <div class='kpi-value'>{formatar_k(sum(fat_realizado_26[:2]))}</div>
        <div class='kpi-delta delta-down'>▼ Meta: {formatar_k(sum(fat_projetado_26[:2]))}</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class='kpi-card' style='border-left-color: #1cc88a;'>
        <div class='kpi-title'>Projeção Faturamento 2026</div>
        <div class='kpi-value'>{formatar_k(sum(fat_projetado_26))}</div>
        <div class='kpi-delta delta-up'>▲ Base 2025: {formatar_k(sum(fat_realizado_25))}</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class='kpi-card' style='border-left-color: #f6c23e;'>
        <div class='kpi-title'>Despesas Financeiras (Ano)</div>
        <div class='kpi-value'>{formatar_k(sum(despesas_fin))}</div>
        <div class='kpi-delta delta-down'>Pico em Jan: {formatar_k(despesas_fin[0])}</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class='kpi-card' style='border-left-color: #36b9cc;'>
        <div class='kpi-title'>Variação de Caixa Projetada</div>
        <div class='kpi-value'>{formatar_k(saldo_inicial_26[-1] - saldo_inicial_26[0])}</div>
        <div class='kpi-delta delta-down'>Saldo Inicial Dez x Jan</div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 4. GRÁFICOS PRINCIPAIS
# ==============================================================================
c_graf1, c_graf2 = st.columns(2)
chart_config = {'scrollZoom': False, 'displayModeBar': False}

# --- Gráfico 1: Projetado x Realizado (Faturamento) ---
with c_graf1:
    fig1 = go.Figure()
    
    # Barra de Projeção (Cinza claro/Tracejado)
    fig1.add_trace(go.Bar(
        x=meses, y=fat_projetado_26, name='Projetado 2026', 
        marker_color='#D1D3E2', opacity=0.8
    ))
    
    # Barra de Realizado (Azul Hospital)
    fig1.add_trace(go.Bar(
        x=meses[:2], y=fat_realizado_26[:2], name='Realizado 2026', 
        marker_color='#4e73df'
    ))
    
    # Linha Histórica de 2025 para comparação (Preto/Cinza Escuro)
    fig1.add_trace(go.Scatter(
        x=meses, y=fat_realizado_25, name='Realizado 2025 (Histórico)', 
        mode='lines+markers', line=dict(color='#5a5c69', width=2, dash='dot')
    ))

    fig1.update_layout(
        title=dict(text="Faturamento: Projetado x Realizado (2026)", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='overlay', # Overlay para mostrar o realizado preenchendo o projetado
        margin=dict(l=20, r=20, t=50, b=20), height=350,
        paper_bgcolor='#F8F9FA', plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        dragmode='pan'
    )
    st.plotly_chart(fig1, use_container_width=True, config=chart_config)

# --- Gráfico 2: Curva do Fluxo de Caixa (Saldo Inicial Projetado) ---
with c_graf2:
    fig2 = go.Figure()
    
    # Área de Saldo Inicial
    fig2.add_trace(go.Scatter(
        x=meses, y=saldo_inicial_26, name='Saldo Inicial FCx', 
        mode='lines+markers', fill='tozeroy', 
        fillcolor='rgba(28, 200, 138, 0.2)', line=dict(color='#1cc88a', width=3)
    ))
    
    # Barras de impacto de Despesas Financeiras
    fig2.add_trace(go.Bar(
        x=meses, y=despesas_fin, name='Despesas Fin. (Impacto)', 
        marker_color='#e74a3b', opacity=0.7
    ))

    fig2.update_layout(
        title=dict(text="Projeção de Curva de Caixa x Despesas Financeiras", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='group',
        margin=dict(l=20, r=20, t=50, b=20), height=350,
        paper_bgcolor='#F8F9FA', plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        dragmode='pan'
    )
    st.plotly_chart(fig2, use_container_width=True, config=chart_config)

# ==============================================================================
# 5. TABELA DE DETALHAMENTO (FCX)
# ==============================================================================
st.markdown("<h4 style='color: #4F4F4F; margin-top: 20px;'>Detalhamento de Caixa Projetado (R$)</h4>", unsafe_allow_html=True)

df_detalhe = pd.DataFrame({
    'Mês': meses,
    'Saldo Inicial': [f"{v:,.2f}".replace(',','X').replace('.',',').replace('X','.') for v in saldo_inicial_26],
    'Faturamento (Projetado)': [f"{v:,.2f}".replace(',','X').replace('.',',').replace('X','.') for v in fat_projetado_26],
    'Despesas Financeiras': [f"{v:,.2f}".replace(',','X').replace('.',',').replace('X','.') for v in despesas_fin],
    'Devolução Paciente': ['170.000,00'] * 12,
    'Despesas Processuais': ['15.000,00'] * 12
})

st.dataframe(
    df_detalhe, 
    hide_index=True, 
    use_container_width=True,
    column_config={
        "Mês": st.column_config.TextColumn("Período", width="small")
    }
)
