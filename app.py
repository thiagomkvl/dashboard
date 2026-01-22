import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração visual profissional
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

# Estilização customizada para o ambiente corporativo
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #004a99;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Dashboard Estratégico de Fornecedores - SOS CARDIO")
st.sidebar.header("Painel de Controle")

# Upload do arquivo CSV
file = st.sidebar.file_uploader("Carregar Base PARA_AIRTABLE_SOS_CARDIO.csv", type="csv")

if file:
    # --- TRATAMENTO DE ERRO DE ENCODING ---
    try:
        # Tenta ler no padrão internacional
        df = pd.read_csv(file, sep=',', encoding='utf-8', engine='python')
    except Exception:
        # Se falhar, tenta o padrão do Excel brasileiro
        file.seek(0)
        df = pd.read_csv(file, sep=',', encoding='latin-1', engine='python')
    
    # Limpeza básica: remover espaços extras nos nomes das colunas
    df.columns = df.columns.str.strip()

    # Métricas Principais
    # Nota: Certifique-se que o nome da coluna é 'Saldo Atual' sem espaços
    total_divida = df['Saldo Atual'].sum()
    vencido_critico = df[df['Dias venc.'] > 30]['Saldo Atual'].sum()
    
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Exposição Total", f"R$ {total_divida:,.2f}")
    m2.metric("Vencido > 30 dias", f"R$ {vencido_critico:,.2f}", delta="- Risco de Corte", delta_color="inverse")
    
    # Contagem de fornecedores únicos na Classe A
    qtd_classe_a = len(df[df['Classe ABC'] == 'Classe A']['Beneficiario'].unique())
    m3.metric("Foco: Fornecedores Classe A", qtd_classe_a)

    # Gráfico de Pareto (Curva ABC)
    st.markdown("---")
    col_graf1, col_graf2 = st.columns([1, 1])

    with col_graf1:
        st.subheader("Concentração por Rating (ABC)")
        fig_abc = px.pie(df, values='Saldo Atual', names='Classe ABC', hole=0.4,
                         color_discrete_map={'Classe A': '#d62728', 'Classe B': '#ff7f0e', 'Classe C': '#2ca02c'})
        st.plotly_chart(fig_abc, use_container_width=True)

    with col_graf2:
        st.subheader("Dívida por Carteira de Atraso")
        # Agrupando por carteira para o gráfico de barras
        ageing_sum = df.groupby('Carteira de Atraso')['Saldo Atual'].sum().reset_index()
        fig_bar = px.bar(ageing_sum, x='Carteira de Atraso', y='Saldo Atual', 
                         color_discrete_sequence=['#004a99'])
        st.plotly_chart(fig_bar, use_container_width=True)

    # Matriz de Prioridade (Ageing x Classe)
    st.markdown("---")
    st.subheader("🎯 Matriz de Decisão: Valor por Classe e Atraso")
    
    # Criando a tabela dinâmica para o dashboard
    pivot_table = df.pivot_table(
        index='Carteira de Atraso', 
        columns='Classe ABC', 
        values='Saldo Atual', 
        aggfunc='sum'
    ).fillna(0)
    
    # Ordenação lógica das linhas da matriz
    ordem_ageing = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '91-180 dias', '> 180 dias']
    pivot_table = pivot_table.reindex(ordem_ageing).fillna(0)
    
    st.table(pivot_table.style.format("R$ {:,.2f}").background_gradient(cmap='Reds'))

    # Lista de Ação
    st.markdown("---")
    st.subheader("📋 Lista de Negociação Prioritária (Classe A)")
    lista_a = df[df['Classe ABC'] == 'Classe A'].sort_values(by='Saldo Atual', ascending=False)
    
    # Exibindo apenas colunas essenciais para o negociador
    cols_display = ['Beneficiario', 'Saldo Atual', 'Carteira de Atraso', 'Vencimento', 'status']
    st.dataframe(lista_a[cols_display], use_container_width=True)

else:
    st.info("Aguardando upload do arquivo CSV na barra lateral para gerar a análise.")
