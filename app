import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração visual profissional
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

# Estilização customizada
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Dashboard Estratégico de Fornecedores")
st.sidebar.header("Filtros de Análise")

# Upload do arquivo que você já tem pronto
file = st.sidebar.file_uploader("Carregar Base Analítica", type="csv")

if file:
    df = pd.read_csv(file, sep=',') # Usando o arquivo otimizado que te enviei
    
    # Métricas Principais
    total_divida = df['Saldo Atual'].sum()
    vencido_critico = df[df['Dias venc.'] > 30]['Saldo Atual'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Exposição Total", f"R$ {total_divida:,.2f}")
    m2.metric("Inadimplência > 30 dias", f"R$ {vencido_critico:,.2f}", delta="- Estimar Acordo", delta_color="inverse")
    m3.metric("Qtd. Fornecedores Classe A", len(df[df['Classe ABC'] == 'Classe A']['Beneficiario'].unique()))

    # Gráfico de Pareto (Curva ABC)
    st.subheader("Análise de Concentração de Dívida (Pareto)")
    fig_abc = px.pie(df, values='Saldo Atual', names='Classe ABC', hole=0.4,
                     color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c'])
    st.plotly_chart(fig_abc, use_container_width=True)

    # Matriz de Prioridade (Ageing x Classe)
    st.subheader("Matriz de Prioridade: Onde negociar primeiro?")
    pivot_table = df.pivot_table(index='Carteira de Atraso', columns='Classe ABC', values='Saldo Atual', aggfunc='sum').fillna(0)
    st.table(pivot_table.style.format("R$ {:,.2f}").background_gradient(cmap='Reds'))

    # Lista de Ação
    st.subheader("📋 Lista de Negociação Prioritária (Classe A)")
    lista_a = df[df['Classe ABC'] == 'Classe A'].sort_values(by='Saldo Atual', ascending=False)
    st.dataframe(lista_a[['Beneficiario', 'Saldo Atual', 'Carteira de Atraso', 'Vencimento']], use_container_width=True)
