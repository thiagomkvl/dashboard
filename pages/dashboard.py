import streamlit as st
import pandas as pd
import plotly.express as px
from database import conectar_sheets
from modules.utils import formatar_real

# --- BLOQUEIO DE SEGURANÇA ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.title("📊 Dashboard Gerencial")
conn = conectar_sheets()

try:
    df_hist = conn.read(worksheet="Historico", ttl=300)
    if not df_hist.empty:
        # Tratamento de dados
        df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
        ultima_data = df_hist['data_processamento'].max()
        df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()
        
        # Cálculo Curva ABC
        df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
        total_hoje = df_abc['Saldo_Limpo'].sum()
        df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
        df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A (80%)' if x <= 0.8 else ('Classe B (15%)' if x <= 0.95 else 'Classe C (5%)'))
        df_hoje = df_hoje.merge(df_abc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

        # KPIs do Topo
        m1, m2, m3, m4 = st.columns(4)
        total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
        m1.metric("Dívida Total", formatar_real(total_hoje))
        m2.metric("Total Vencido", formatar_real(total_vencido), delta_color="inverse")
        m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
        m4.metric("Processamento", ultima_data)
        
        st.divider()
        
        # Gráficos
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Curva ABC")
            fig_abc = px.pie(df_hoje, values='Saldo_Limpo', names='Classe ABC', hole=0.4, 
                             color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
            st.plotly_chart(fig_abc, use_container_width=True)
        with c2:
            st.subheader("Ageing List")
            ordem = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
            df_bar = df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem).reset_index().fillna(0)
            fig_bar = px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'])
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # Radar de Pagamentos Futuros
        st.subheader("📅 Previsão de Pagamentos")
        df_hoje['Venc_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
        df_futuro = df_hoje[df_hoje['Venc_DT'] >= pd.Timestamp.now().normalize()].copy()
        
        if not df_futuro.empty:
            df_futuro['Data_F'] = df_futuro['Venc_DT'].dt.strftime('%d/%m/%Y')
            fig_radar = px.bar(df_futuro, x='Data_F', y='Saldo_Limpo', color='Beneficiario', title="Vencimentos Futuros")
            st.plotly_chart(fig_radar, use_container_width=True)

    else:
        st.info("Base de dados vazia. Faça o upload na aba correspondente.")
except Exception as e:
    st.error(f"Erro ao carregar Dashboard: {e}")
