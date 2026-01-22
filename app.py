import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets

# 1. CONFIGURAÇÃO E CSS
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

# Função de formatação robusta para Real Brasileiro
def formatar_real(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 5px; background-color: white; }
    
    /* Scroll interno fixo para o detalhamento */
    [data-testid="stVerticalBlock"] > div:nth-child(10) {
        max-height: 480px;
        overflow-y: auto;
        border: 1px solid #d1d5db;
        padding: 15px;
        border-radius: 10px;
        background-color: #f9fafb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CARREGAMENTO ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        conn = conectar_sheets()
        df = conn.read(worksheet="Historico", ttl=60)
        if not df.empty:
            df['Beneficiario'] = df['Beneficiario'].astype(str).str.strip()
            df['Saldo_Limpo'] = pd.to_numeric(df['Saldo Atual'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

df_hist = carregar_dados()

# --- MENU LATERAL ---
st.sidebar.title("Dívida Fornecedores")
aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Evolução Temporal", "Upload"])

if not df_hist.empty:
    ultima_data = df_hist['data_processamento'].max()
    df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()

    # LÓGICA CURVA ABC
    df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
    total_hoje = df_abc['Saldo_Limpo'].sum()
    df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
    df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A (80%)' if x <= 0.8 else ('Classe B (15%)' if x <= 0.95 else 'Classe C (5%)'))
    df_hoje = df_hoje.merge(df_abc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

    if aba == "Dashboard Principal":
        st.title("Gestão de Passivo - SOS CARDIO")
        
        # MÉTRICAS
        m1, m2, m3, m4 = st.columns(4)
        total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
        m1.metric("Dívida Total", formatar_real(total_hoje))
        m2.metric("Total Vencido", formatar_real(total_vencido))
        m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
        m4.metric("Qtd Classe A", len(df_abc[df_abc['Classe ABC'] == 'Classe A (80%)']))

        st.divider()

        # GRÁFICOS
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Curva ABC de Fornecedores")
            sel_abc = st.multiselect("Filtrar Classes:", ['Classe A (80%)', 'Classe B (15%)', 'Classe C (5%)'], default=['Classe A (80%)', 'Classe B (15%)', 'Classe C (5%)'], key="f_abc")
            df_pie = df_hoje[df_hoje['Classe ABC'].isin(sel_abc)]
            fig_p = px.pie(df_pie, values='Saldo_Limpo', names='Classe ABC', hole=0.4, 
                           color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
            st.plotly_chart(fig_p, use_container_width=True)

        with c2:
            st.subheader("Volume por Faixa (Ageing)")
            ordem_cart = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
            sel_cart = st.multiselect("Filtrar Faixas:", ordem_cart, default=ordem_cart, key="f_age")
            df_bar = df_hoje[df_hoje['Carteira'].isin(sel_cart)].groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem_cart).reset_index().fillna(0)
            fig_b = px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s')
            st.plotly_chart(fig_b, use_container_width=True)

        st.divider()
        
        # --- BLOCO COM SCROLL (FORNECEDORES) ---
        st.subheader("Detalhamento com Análise de Risco")
        with st.container(height=480):
            df_agrup = df_hoje.groupby(['Beneficiario', 'Classe ABC']).agg(
                Total_Aberto=('Saldo_Limpo', 'sum'),
                Total_Vencido=('Saldo_Limpo', lambda x: df_hoje.loc[x.index][df_hoje.loc[x.index, 'Carteira'] != 'A Vencer']['Saldo_Limpo'].sum())
            ).sort_values('Total_Aberto', ascending=False).reset_index()

            for _, row in df_agrup.iterrows():
                label = f"{row['Beneficiario']} ({row['Classe ABC']}) | Aberto: {formatar_real(row['Total_Aberto'])} | Vencido: {formatar_real(row['Total_Vencido'])}"
                with st.expander(label):
                    detalhe = df_hoje[df_hoje['Beneficiario'] == row['Beneficiario']].copy()
                    detalhe['Valor'] = detalhe['Saldo_Limpo'].apply(formatar_real)
                    st.table(detalhe[['Vencimento', 'Valor', 'Carteira']])

# --- BLOCO: RADAR DE PAGAMENTOS (FOCO MENSAL E MAIORES VALORES) ---
        st.divider()
        st.subheader("🎯 Radar de Pagamentos - Análise Mensal")

        # 1. Preparar Datas e Filtro de Mês
        hoje = pd.Timestamp.now().normalize()
        df_hoje['Vencimento_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
        df_futuro = df_hoje[df_hoje['Vencimento_DT'] >= hoje].copy()

        if not df_futuro.empty:
            # Filtro de Mês para o Gráfico
            df_futuro['Mes_Ref'] = df_futuro['Vencimento_DT'].dt.strftime('%m/%Y')
            meses_disponiveis = sorted(df_futuro['Mes_Ref'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
            
            col_f1, col_f2 = st.columns([1, 2])
            with col_f1:
                mes_selecionado = st.selectbox("Selecione o Mês para Análise:", meses_disponiveis)
            
            df_mes_filtrado = df_futuro[df_futuro['Mes_Ref'] == mes_selecionado].sort_values('Vencimento_DT')

            # 2. Métricas de Tesouraria (Baseadas no mês selecionado)
            c_p1, c_p2, c_p3 = st.columns(3)
            total_mes = df_mes_filtrado['Saldo_Limpo'].sum()
            maior_pag = df_mes_filtrado['Saldo_Limpo'].max()
            qtd_pag = len(df_mes_filtrado)

            c_p1.metric(f"Total em {mes_selecionado}", formatar_real(total_mes))
            c_p2.metric("Maior Saída do Mês", formatar_real(maior_pag))
            c_p3.metric("Qtd. de Pagamentos", qtd_pag)

            # 3. Gráfico de Cronograma Mensal (Bolhas maiores para melhor visualização)
            fig_radar = px.scatter(df_mes_filtrado, x='Vencimento_DT', y='Saldo_Limpo', 
                                 size='Saldo_Limpo', color='Classe ABC',
                                 hover_name='Beneficiario',
                                 size_max=50, # Aumenta o tamanho máximo das bolhas
                                 title=f"Distribuição de Vencimentos: {mes_selecionado}",
                                 labels={'Vencimento_DT': 'Dia do Vencimento', 'Saldo_Limpo': 'Valor'},
                                 color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
            
            fig_radar.update_layout(xaxis_tickformat='%d/%m') # Mostra apenas o dia/mês no eixo X
            st.plotly_chart(fig_radar, use_container_width=True)

            # 4. Tabela: 15 MAIORES PAGAMENTOS PREVISTOS (Geral Futuro)
            st.divider()
            st.write("📋 **Top 15 Maiores Pagamentos Previstos (Visão Estratégica)**")
            # Aqui filtramos o TOP 15 por VALOR de todo o futuro disponível
            df_maiores = df_futuro.sort_values('Saldo_Limpo', ascending=False).head(15)
            df_maiores['Valor'] = df_maiores['Saldo_Limpo'].apply(formatar_real)
            
            st.table(df_maiores[['Vencimento', 'Beneficiario', 'Valor', 'Classe ABC', 'Carteira']])
        else:
            st.info("Nenhum vencimento futuro encontrado nos dados carregados.")

    elif aba == "Evolução Temporal":
        st.title("Evolução da Inadimplência")
        df_ev = df_hist.groupby('data_processamento')['Saldo_Limpo'].sum().reset_index()
        df_ev['dt_ordem'] = pd.to_datetime(df_ev['data_processamento'], format='%d/%m/%Y')
        df_ev = df_ev.sort_values('dt_ordem')
        fig_ev = px.line(df_ev, x='data_processamento', y='Saldo_Limpo', markers=True, title="Passivo Total Acumulado")
        st.plotly_chart(fig_ev, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        uploaded = st.file_uploader("Selecione o arquivo Excel do Hospital", type=["xlsx"])
        if uploaded and st.button("🚀 Salvar e Atualizar Dashboard"):
            df_new = pd.read_excel(uploaded)
            df_push = df_new.copy()
            df_push.columns = df_push.columns.str.strip()
            if salvar_no_historico(df_push):
                st.success("Dados arquivados com sucesso!")
                st.rerun()
else:
    st.warning("Aguardando o primeiro upload para carregar o histórico.")
