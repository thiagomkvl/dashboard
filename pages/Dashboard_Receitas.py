import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import conectar_sheets

st.set_page_config(page_title="Faturamento & Receita", page_icon="📊", layout="wide")

# ==========================================
# 1. IDENTIDADE VISUAL (CSS DARK MODE)
# ==========================================
st.markdown("""
    <style>
    /* Fundo da aplicação */
    .stApp {
        background-color: #0F172A;
    }
    
    /* Estilização dos Cards de KPI */
    div[data-testid="metric-container"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Cor do rótulo do KPI */
    div[data-testid="metric-container"] > div:first-child > div {
        color: #94A3B8 !important;
        font-weight: 600;
        font-size: 14px;
    }
    
    /* Cor do valor do KPI */
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] > div {
        color: #FFFFFF !important;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Configuração padrão de layout para todos os gráficos Plotly
LAYOUT_PLOTLY = dict(
    plot_bgcolor='#1E293B',
    paper_bgcolor='#1E293B',
    font=dict(color='#94A3B8'),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor='#334155', zeroline=False)
)

# ==========================================
# 2. CARREGAMENTO DOS DADOS (Simulação)
# ==========================================
# conn = conectar_sheets()
# df_sit_contas = conn.read(worksheet="Situação_Contas", ttl=0)
# df_sit_convenios = conn.read(worksheet="Situação_Contas_Convênio", ttl=0)
# df_fat_convenio = conn.read(worksheet="Faturamento_Convênio", ttl=0)

st.title("📊 FATURAMENTO, RECEBIMENTO & INADIMPLÊNCIA")
st.markdown("<p style='color: #94A3B8; margin-top: -15px;'>Visão completa da carteira de contas a receber</p>", unsafe_allow_html=True)

# Filtros Globais (Linha superior)
col_f1, col_f2, col_f3 = st.columns([2, 2, 6])
with col_f1:
    st.selectbox("Período", ["Jan/2026 - Set/2026", "Out/2026 - Dez/2026"])
with col_f2:
    st.selectbox("Convênio", ["Todos", "Unimed", "Bradesco", "SulAmérica", "Cassi"])

# ==========================================
# 3. ESTRUTURA DAS 3 VISÕES (ABAS)
# ==========================================
tab1, tab2, tab3 = st.tabs(["💰 Análise de Receita", "🏥 Análise de Convênios", "⚙️ Análise de Produção"])

# ------------------------------------------
# ABA 1: RECEITA GLOBAL
# ------------------------------------------
with tab1:
    st.markdown("### Visão Executiva e Fluxo de Caixa")
    # Base ideal para usar aqui: df_sit_contas
    
    # 4 KPIs Superiores
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("FATURAMENTO EMITIDO", "R$ 140.283.762", "8.4% vs anterior")
    k2.metric("RECEBIMENTOS", "R$ 118.734.521", "12.1% vs anterior")
    k3.metric("CONTAS A RECEBER", "R$ 21.549.241", "-2.3% vs anterior")
    k4.metric("INADIMPLÊNCIA", "R$ 8.203.416", "5.8% da carteira")
    
    col_graf1, col_graf2 = st.columns([2, 1])
    with col_graf1:
        st.markdown("##### Faturamento vs Recebimento")
        # Exemplo estrutural de gráfico
        # fig_linha = px.line(df_sit_contas, x='Mes', y=['Faturado', 'Recebido'])
        # fig_linha.update_layout(**LAYOUT_PLOTLY)
        # st.plotly_chart(fig_linha, use_container_width=True)
        st.info("Gráfico de Linha de Faturamento x Recebimento entrará aqui.")
        
    with col_graf2:
        st.markdown("##### Carteira em Aberto (Aging)")
        # Exemplo estrutural de rosca
        # fig_rosca = px.pie(df_sit_contas, values='Valor', names='Faixa_Atraso', hole=0.7)
        # fig_rosca.update_layout(**LAYOUT_PLOTLY)
        # st.plotly_chart(fig_rosca, use_container_width=True)
        st.info("Gráfico de Rosca (A vencer, 30, 60, +90 dias) entrará aqui.")

# ------------------------------------------
# ABA 2: CONVÊNIOS
# ------------------------------------------
with tab2:
    st.markdown("### Performance Tática por Plano de Saúde")
    # Base ideal para usar aqui: df_sit_convenios
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("##### Top 10 Convênios por Faturamento")
        # fig_barras_fat = px.bar(df_sit_convenios, x='Faturamento', y='Convenio', orientation='h')
        # fig_barras_fat.update_traces(marker_color='#3B82F6') # Azul
        st.info("Gráfico de Barras Horizontais Azuis entrará aqui.")
        
    with col_c2:
        st.markdown("##### Inadimplência por Convênio")
        # fig_barras_inad = px.bar(df_sit_convenios, x='Inadimplencia', y='Convenio', orientation='h')
        # fig_barras_inad.update_traces(marker_color='#EF4444') # Vermelho
        st.info("Gráfico de Barras Horizontais Vermelhas entrará aqui.")
        
    st.markdown("##### Desempenho Detalhado")
    # st.dataframe(df_sit_convenios, use_container_width=True)

# ------------------------------------------
# ABA 3: PRODUÇÃO E GLOSAS
# ------------------------------------------
with tab3:
    st.markdown("### Qualidade Operacional e Glosas")
    # Base ideal para usar aqui: df_fat_convenio
    
    g1, g2, g3 = st.columns(3)
    g1.metric("GLOSAS ACATADAS", "R$ 1.247.860", "3.2% do faturado")
    g2.metric("EM RECURSO", "R$ 803.542", "2.1% do faturado")
    g3.metric("PRAZO MÉDIO EMISSÃO", "34 dias", "-2 dias vs anterior")
    
    st.info("Gráficos de motivos de glosa (técnica, administrativa) e evolução de recursos entrarão aqui.")
