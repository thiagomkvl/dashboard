import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets # Importando conexão

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

# Estilização CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { 
        background-color: #ffffff; padding: 15px; border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #004a99;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Dashboard Financeiro - SOS CARDIO")

# --- FUNÇÃO PARA CARREGAR DADOS DO GOOGLE SHEETS ---
@st.cache_data(ttl=60) # Atualiza a cada 1 minuto se houver mudança
def carregar_dados_salvos():
    try:
        conn = conectar_sheets()
        df = conn.read(worksheet="Historico")
        # Filtrar apenas a última data processada para o Dashboard principal
        if not df.empty:
            ultima_data = df['data_processamento'].max()
            return df[df['data_processamento'] == ultima_data], ultima_data
        return pd.DataFrame(), None
    except:
        return pd.DataFrame(), None

# --- SIDEBAR: UPLOAD E FILTROS ---
st.sidebar.image("https://www.soscardio.com.br/wp-content/uploads/2020/05/logo_sos_cardio.png", width=150) # Exemplo de logo
st.sidebar.title("Controles")

# Busca automática dos últimos dados
df_db, data_ref = carregar_dados_salvos()

# Opção de subir novos dados
file = st.sidebar.file_uploader("Atualizar Base (Upload)", type=["csv", "xlsx"])

if file:
    # ... (mesma lógica de limpeza que já tínhamos)
    try:
        if file.name.endswith('.csv'):
            df_upload = pd.read_csv(file, sep=None, encoding='latin-1', engine='python')
        else:
            df_upload = pd.read_excel(file)
        
        # Processamento rápido para o botão de salvar
        df_upload.columns = df_upload.columns.str.strip()
        # Mapeamento (Ajuste conforme seus nomes de coluna)
        df_para_banco = df_upload[['Beneficiario', 'Saldo Atual', 'Vencimento', 'Dias venc.']].copy()
        df_para_banco.columns = ['Beneficiario', 'Saldo Atual', 'Vencimento', 'Carteira']
        
        if st.sidebar.button("🚀 Enviar Novos Dados para Nuvem"):
            if salvar_no_historico(df_para_banco):
                st.sidebar.success("Base Atualizada!")
                st.rerun()
    except Exception as e:
        st.sidebar.error(f"Erro no processamento: {e}")

# --- LÓGICA DO DASHBOARD (USANDO O QUE ESTÁ NO BANCO) ---
if not df_db.empty:
    # Limpeza e Tipagem
    df_db['Saldo_Limpo'] = pd.to_numeric(df_db['Saldo Atual'], errors='coerce').fillna(0)
    
    # 1. CÁLCULO CURVA ABC
    agg = df_db.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
    total_debt = agg['Saldo_Limpo'].sum()
    agg['Acumulado'] = agg['Saldo_Limpo'].cumsum() / total_debt
    agg['Classe ABC'] = agg['Acumulado'].apply(lambda x: 'A' if x <= 0.8 else ('B' if x <= 0.95 else 'C'))
    df_db = df_db.merge(agg[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

    # --- FILTROS EM BOTÕES (MULTIPLO VALORES) ---
    st.sidebar.markdown("---")
    filtro_abc = st.sidebar.multiselect("Filtrar Classe ABC", options=['A', 'B', 'C'], default=['A', 'B', 'C'])
    filtro_atraso = st.sidebar.multiselect("Filtrar Faixa de Atraso", options=df_db['Carteira'].unique(), default=df_db['Carteira'].unique())

    # Aplicar Filtros
    df_filtrado = df_db[(df_db['Classe ABC'].isin(filtro_abc)) & (df_db['Carteira'].isin(filtro_atraso))]

    # --- MÉTRICAS ---
    st.info(f"📅 Dados referentes à última atualização em: **{data_ref}**")
    m1, m2, m3 = st.columns(3)
    m1.metric("Dívida Total (Filtro)", f"R$ {df_filtrado['Saldo_Limpo'].sum():,.2f}")
    m2.metric("Fornecedores em Exibição", len(df_filtrado['Beneficiario'].unique()))
    m3.metric("Classe A Total", f"R$ {df_db[df_db['Classe ABC'] == 'A']['Saldo_Limpo'].sum():,.2f}")

    # --- GRÁFICOS ---
    c1, c2 = st.columns(2)
    with c1:
        fig_abc = px.pie(df_filtrado, values='Saldo_Limpo', names='Classe ABC', 
                         title="Distribuição de Dívida (ABC)", 
                         color_discrete_sequence=px.colors.qualitative.Prism, hole=0.4)
        st.plotly_chart(fig_abc, use_container_width=True)
    
    with c2:
        # Gráfico de barras ordenado
        ageing_order = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
        fig_bar = px.bar(df_filtrado.groupby('Carteira')['Saldo_Limpo'].sum().reset_index(), 
                         x='Carteira', y='Saldo_Limpo', title="Dívida por Ageing",
                         color_discrete_sequence=['#004a99'])
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📋 Lista Detalhada de Fornecedores")
    st.dataframe(df_filtrado[['Beneficiario', 'Saldo Atual', 'Vencimento', 'Classe ABC', 'Carteira']], use_container_width=True)

else:
    st.warning("Nenhum dado encontrado no histórico. Por favor, faça o primeiro upload na barra lateral.")
