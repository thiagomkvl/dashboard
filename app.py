import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets

# 1. CONFIGURAÇÃO E CSS
st.set_page_config(page_title="SOS CARDIO - Dívida Fornecedores", layout="wide")

def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; }
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- CARREGAMENTO ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        conn = conectar_sheets()
        df = conn.read(worksheet="Historico", ttl=60)
        if not df.empty:
            df['Saldo_Limpo'] = pd.to_numeric(df['Saldo Atual'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

df_hist = carregar_dados()

# --- MENU LATERAL ---
st.sidebar.title("🏥 Menu Principal")
aba = st.sidebar.radio("Selecione o Painel:", ["Dívida Fornecedores", "Evolução Temporal", "Upload de Dados"])

if not df_hist.empty:
    ultima_data = df_hist['data_processamento'].max()
    df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()

    # --- ABA 1: DÍVIDA ATUAL ---
    if aba == "Dívida Fornecedores":
        st.title("📊 Gestão de Dívida com Fornecedores")
        st.info(f"Exibindo dados da última atualização: {ultima_data}")

        m1, m2, m3 = st.columns(3)
        m1.metric("Dívida Total", formatar_real(df_hoje['Saldo_Limpo'].sum()))
        m2.metric("Fornecedores Ativos", len(df_hoje['Beneficiario'].unique()))
        m3.metric("Maior Título", formatar_real(df_hoje['Saldo_Limpo'].max()))

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            # Filtro local do gráfico de pizza
            opcoes_cat = sorted(df_hoje['Carteira'].unique())
            sel_cat = st.multiselect("Filtrar Categorias (Pizza):", opcoes_cat, default=opcoes_cat, key="f_pizza")
            df_p = df_hoje[df_hoje['Carteira'].isin(sel_cat)]
            fig_p = px.pie(df_p, values='Saldo_Limpo', names='Carteira', hole=0.4, title="Distribuição por Faixa")
            st.plotly_chart(fig_p, use_container_width=True)

        with c2:
            # Filtro local do gráfico de barras
            top_n = st.slider("Mostrar Top Fornecedores:", 5, 30, 10, key="f_bar")
            df_b = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).head(top_n).reset_index()
            fig_b = px.bar(df_b, x='Beneficiario', y='Saldo_Limpo', title=f"Top {top_n} Devedores", color_discrete_sequence=['#004a99'])
            st.plotly_chart(fig_b, use_container_width=True)

        st.divider()
        st.subheader("📋 Detalhamento (Drill-down)")
        
        # Agrupamento para o cabeçalho do expander
        df_agrup = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
        
        for _, row in df_agrup.iterrows():
            with st.expander(f"🏢 {row['Beneficiario']} — Total: {formatar_real(row['Saldo_Limpo'])}"):
                # Mostra as linhas individuais desse fornecedor
                detalhe = df_hoje[df_hoje['Beneficiario'] == row['Beneficiario']][['Vencimento', 'Saldo Atual', 'Carteira']]
                st.table(detalhe)

    # --- ABA 2: EVOLUÇÃO ---
    elif aba == "Evolução Temporal":
        st.title("📈 Evolução da Dívida")
        df_ev = df_hist.groupby('data_processamento')['Saldo_Limpo'].sum().reset_index()
        # Ordenação correta por data
        df_ev['dt_ordem'] = pd.to_datetime(df_ev['data_processamento'], format='%d/%m/%Y')
        df_ev = df_ev.sort_values('dt_ordem')
        
        fig_ev = px.line(df_ev, x='data_processamento', y='Saldo_Limpo', title="Tendência da Dívida Total", markers=True)
        st.plotly_chart(fig_ev, use_container_width=True)
        st.dataframe(df_ev[['data_processamento', 'Saldo_Limpo']].rename(columns={'Saldo_Limpo': 'Total (R$)'}))

    # --- ABA 3: UPLOAD ---
    elif aba == "Upload de Dados":
        st.title("⚙️ Atualizar Base de Dados")
        uploaded = st.file_uploader("Suba o arquivo original (.xlsx ou .csv)", type=["xlsx", "csv"])
        if uploaded and st.button("🚀 Processar e Arquivar no Google Sheets"):
            df_new = pd.read_excel(uploaded) if uploaded.name.endswith('.xlsx') else pd.read_csv(uploaded, encoding='latin-1', sep=None, engine='python')
            
            # Mapeamento para garantir o padrão do banco
            df_push = df_new.copy()
            df_push.columns = df_push.columns.str.strip()
            # Mapeie aqui se os nomes das colunas variarem
            if salvar_no_historico(df_push):
                st.success("Sucesso! Os dados foram empilhados no histórico.")
                st.rerun()

else:
    st.warning("Aguardando o primeiro upload para carregar o histórico.")
