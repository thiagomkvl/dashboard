import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

# Estilização CSS para visual corporativo
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

# 2. UPLOAD DO ARQUIVO
file = st.sidebar.file_uploader("Carregar Base PARA_AIRTABLE_SOS_CARDIO.csv", type="csv")

if file:
    # --- LEITURA ROBUSTA (Resolve ParserError e UnicodeDecodeError) ---
    try:
        # sep=None com engine='python' detecta automaticamente o separador (, ou ;)
        # on_bad_lines='skip' pula linhas com erro de formatação (vírgulas extras no texto)
        df = pd.read_csv(file, sep=None, encoding='latin-1', engine='python', on_bad_lines='skip')
    except Exception as e:
        st.error(f"Erro crítico ao ler o arquivo: {e}")
        st.stop()

    # Limpeza de espaços nos nomes das colunas
    df.columns = df.columns.str.strip()

    # --- VALIDAÇÃO DE COLUNAS ---
    colunas_foco = ['Saldo Atual', 'Dias venc.', 'Classe ABC', 'Beneficiario', 'Carteira de Atraso']
    faltantes = [c for c in colunas_foco if c not in df.columns]
    
    if faltantes:
        st.error(f"⚠️ Colunas não encontradas: {', '.join(faltantes)}")
        st.info("O sistema espera um CSV com as colunas calculadas previamente.")
        st.stop()

    # 3. MÉTRICAS EXECUTIVAS
    total_divida = df['Saldo Atual'].sum()
    vencido_30 = df[df['Dias venc.'] > 30]['Saldo Atual'].sum()
    qtd_fornecedores = len(df['Beneficiario'].unique())
    
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Exposição Total", f"R$ {total_divida:,.2f}")
    m2.metric("Inadimplência > 30 dias", f"R$ {vencido_30:,.2f}", delta="Risco de Operação", delta_color="inverse")
    m3.metric("Total de Fornecedores", qtd_fornecedores)

    # 4. GRÁFICOS ANALÍTICOS
    st.markdown("---")
    col_abc, col_ageing = st.columns([1, 1])

    with col_abc:
        st.subheader("Concentração por Rating (ABC)")
        fig_abc = px.pie(df, values='Saldo Atual', names='Classe ABC', hole=0.4,
                         color_discrete_map={'Classe A': '#d62728', 'Classe B': '#ff7f0e', 'Classe C': '#2ca02c'})
        st.plotly_chart(fig_abc, use_container_width=True)

    with col_ageing:
        st.subheader("Dívida por Faixa de Atraso")
        ageing_sum = df.groupby('Carteira de Atraso')['Saldo Atual'].sum().reset_index()
        # Ordenação manual para o gráfico
        ordem = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '91-180 dias', '> 180 dias']
        ageing_sum['Carteira de Atraso'] = pd.Categorical(ageing_sum['Carteira de Atraso'], categories=ordem, ordered=True)
        ageing_sum = ageing_sum.sort_values('Carteira de Atraso')
        
        fig_bar = px.bar(ageing_sum, x='Carteira de Atraso', y='Saldo Atual', color_discrete_sequence=['#004a99'])
        st.plotly_chart(fig_bar, use_container_width=True)

    # 5. MATRIZ DE PRIORIZAÇÃO
    st.markdown("---")
    st.subheader("🎯 Matriz de Decisão: Onde Negociar?")
    
    pivot = df.pivot_table(index='Carteira de Atraso', columns='Classe ABC', values='Saldo Atual', aggfunc='sum').fillna(0)
    # Reordenar linhas conforme a lógica de tempo
    pivot = pivot.reindex([o for o in ordem if o in pivot.index])
    
    st.table(pivot.style.format("R$ {:,.2f}").background_gradient(cmap='Reds'))

    # 6. TABELA DETALHADA DE NEGOCIAÇÃO
    st.markdown("---")
    st.subheader("📋 Detalhamento para Negociação (Top Classe A)")
    
    # Filtro para ver apenas Classe A por padrão
    exibir_classe = st.multiselect("Filtrar por Classe:", options=['Classe A', 'Classe B', 'Classe C'], default=['Classe A'])
    
    df_filtered = df[df['Classe ABC'].isin(exibir_classe)].sort_values('Saldo Atual', ascending=False)
    
    st.dataframe(
        df_filtered[['Beneficiario', 'Saldo Atual', 'Carteira de Atraso', 'Vencimento', 'status']], 
        use_container_width=True
    )

else:
    st.info("👆 Por favor, carregue o arquivo CSV na barra lateral para iniciar a análise.")
    st.image("https://via.placeholder.com/800x400.png?text=Aguardando+Dados+do+Hospital+SOS+CARDIO", use_container_width=True)
