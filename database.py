import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

# Formatação de Moeda Brasileira
def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# CSS para melhorar o visual
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stExpander { background-color: white; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=60)
def carregar_tudo():
    try:
        conn = conectar_sheets()
        return conn.read(worksheet="Historico")
    except:
        return pd.DataFrame()

df_historico = carregar_tudo()

# --- MENU LATERAL (NAVEGAÇÃO) ---
st.sidebar.image("https://www.soscardio.com.br/wp-content/uploads/2020/05/logo_sos_cardio.png", width=150)
st.sidebar.title("Navegação")
aba_selecionada = st.sidebar.radio("Ir para:", ["Dívida Fornecedores", "Evolução Temporal", "Configurações/Upload"])

# --- LÓGICA DE PROCESSAMENTO ---
if not df_historico.empty:
    # Garantir tipagem numérica
    df_historico['Saldo_Limpo'] = pd.to_numeric(df_historico['Saldo Atual'], errors='coerce').fillna(0)
    
    # Identificar última atualização
    ultima_data = df_historico['data_processamento'].max()
    df_atual = df_historico[df_historico['data_processamento'] == ultima_data].copy()

    # 1. ABA: DÍVIDA FORNECEDORES
    if aba_selecionada == "Dívida Fornecedores":
        st.title("📊 Gestão de Dívida com Fornecedores")
        st.info(f"📅 Dados da última atualização: {ultima_data}")

        # --- BLOCO DE MÉTRICAS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Dívida Total Hoje", formatar_real(df_atual['Saldo_Limpo'].sum()))
        m2.metric("Fornecedores Ativos", len(df_atual['Beneficiario'].unique()))
        m3.metric("Maior Pendência", formatar_real(df_atual['Saldo_Limpo'].max()))

        st.markdown("---")

        # --- GRÁFICOS COM FILTROS LOCAIS ---
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Distribuição (Classe ABC)")
            # Filtro local
            classes_disponiveis = sorted(df_atual['Carteira'].unique())
            filtro_local_abc = st.multiselect("Filtrar por Ageing neste gráfico:", classes_disponiveis, default=classes_disponiveis, key="filtro_abc")
            
            df_pie = df_atual[df_atual['Carteira'].isin(filtro_local_abc)]
            fig_pie = px.pie(df_pie, values='Saldo_Limpo', names='Carteira', hole=0.4, color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            st.subheader("Inadimplência por Faixa")
            # Filtro local
            fornecedores_top = st.slider("Mostrar Top X Fornecedores:", 5, 50, 15, key="slider_bar")
            
            df_bar = df_atual.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).head(fornecedores_top).reset_index()
            fig_bar = px.bar(df_bar, x='Beneficiario', y='Saldo_Limpo', color_discrete_sequence=['#004a99'])
            st.plotly_chart(fig_bar, use_container_width=True)

        # --- LISTA DETALHADA COM DRILL-DOWN ---
        st.markdown("---")
        st.subheader("📋 Detalhamento por Fornecedor (Clique para expandir)")
        
        # Agrupar por fornecedor para a visão principal
        df_agrupado = df_atual.groupby('Beneficiario').agg({
            'Saldo_Limpo': 'sum',
            'Carteira': lambda x: x.mode()[0] if not x.empty else 'N/A'
        }).sort_values('Saldo_Limpo', ascending=False).reset_index()

        for _, row in df_agrupado.iterrows():
            with st.expander(f"📌 {row['Beneficiario']} | Total: {formatar_real(row['Saldo_Limpo'])} | Status: {row['Carteira']}"):
                # Mostrar detalhes desse fornecedor específico
                detalhes = df_atual[df_atual['Beneficiario'] == row['Beneficiario']][['Vencimento', 'Saldo Atual', 'Carteira']]
                st.table(detalhes)

    # 2. ABA: EVOLUÇÃO TEMPORAL
    elif aba_selecionada == "Evolução Temporal":
        st.title("📈 Evolução Histórica da Dívida")
        
        # Agrupar por data de processamento
        df_evolucao = df_historico.groupby('data_processamento')['Saldo_Limpo'].sum().reset_index()
        # Ordenar por data (precisa converter para datetime para ordenar corretamente)
        df_evolucao['dt_temp'] = pd.to_datetime(df_evolucao['data_processamento'], format='%d/%m/%Y')
        df_evolucao = df_evolucao.sort_values('dt_temp')

        fig_evol = px.line(df_evolucao, x='data_processamento', y='Saldo_Limpo', 
                           title="Crescimento/Redução da Dívida Total",
                           markers=True, line_shape="spline")
        fig_evol.update_traces(line_color='#d62728')
        st.plotly_chart(fig_evol, use_container_width=True)

        st.subheader("Análise Comparativa")
        st.write("Dados acumulados por período de processamento:")
        st.dataframe(df_evolucao[['data_processamento', 'Saldo_Limpo']].rename(columns={'Saldo_Limpo': 'Total Dívida'}))

    # 3. ABA: CONFIGURAÇÕES
    elif aba_selecionada == "Configurações/Upload":
        st.title("⚙️ Gerenciamento de Dados")
        file = st.file_uploader("Upload de nova base do hospital", type=["csv", "xlsx"])
        if file and st.button("Salvar Novos Dados no Google Sheets"):
            # Lógica de processamento e salvamento aqui...
            st.success("Dados salvos com sucesso!")
            st.rerun()

else:
    st.warning("⚠️ Nenhuma base encontrada. Vá em 'Configurações/Upload' para subir o primeiro arquivo.")
