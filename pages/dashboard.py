import streamlit as st
import pandas as pd
import plotly.express as px
from database import conectar_sheets
from modules.utils import formatar_real

# --- BLOQUEIO DE SEGURANÇA ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.title("📉 Gestão de Dívida com Fornecedores")
st.caption("Visão analítica do Passivo e Contas a Pagar")

# --- CARREGAMENTO DE DADOS ---
conn = conectar_sheets()
try:
    df_hist = conn.read(worksheet="Historico", ttl=300)
    
    if not df_hist.empty:
        # 1. Tratamento e Limpeza
        df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
        
        # Filtra apenas o último processamento
        ultima_data = df_hist['data_processamento'].max()
        df_full = df_hist[df_hist['data_processamento'] == ultima_data].copy()
        
        # Tratamento de Datas
        df_full['Vencimento_DT'] = pd.to_datetime(df_full['Vencimento'], dayfirst=True, errors='coerce')
        hoje = pd.Timestamp.now().normalize()
        
        # Categorização de Status
        def definir_status(row):
            if row['Vencimento_DT'] < hoje: return "🚨 Vencido"
            elif row['Vencimento_DT'] == hoje: return "⚠️ Vence Hoje"
            else: return "📅 A Vencer"
            
        df_full['Status_Tempo'] = df_full.apply(definir_status, axis=1)

        # --- 2. PAINEL DE KPIs (TOPO) ---
        total_divida = df_full['Saldo_Limpo'].sum()
        total_vencido = df_full[df_full['Status_Tempo'] == "🚨 Vencido"]['Saldo_Limpo'].sum()
        total_hoje = df_full[df_full['Status_Tempo'] == "⚠️ Vence Hoje"]['Saldo_Limpo'].sum()
        
        proxima_semana = hoje + pd.Timedelta(days=7)
        mask_semana = (df_full['Vencimento_DT'] > hoje) & (df_full['Vencimento_DT'] <= proxima_semana)
        total_semana = df_full[mask_semana]['Saldo_Limpo'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Dívida Total", formatar_real(total_divida))
        col2.metric("Vencido (Backlog)", formatar_real(total_vencido), delta_color="inverse")
        col3.metric("Vence Hoje", formatar_real(total_hoje), delta_color="inverse")
        col4.metric("Próximos 7 Dias", formatar_real(total_semana))

        st.divider()

            st.caption("Barra inferior para navegação | Legenda lateral para filtro.")

        # --- 4. ANÁLISE DE COMPOSIÇÃO (TREEMAP & AGEING) ---
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.subheader("🏗️ Composição da Dívida")
            df_tree = df_full.groupby('Beneficiario')['Saldo_Limpo'].sum().reset_index()
            df_tree = df_tree.sort_values('Saldo_Limpo', ascending=False).head(30)
            
            fig_tree = px.treemap(
                df_tree, 
                path=['Beneficiario'], 
                values='Saldo_Limpo',
                color='Saldo_Limpo',
                color_continuous_scale='Blues',
                hover_data={'Saldo_Limpo': ':,.2f'}
            )
            st.plotly_chart(fig_tree, use_container_width=True)

        with c_right:
            st.subheader("⏳ Ageing List (Idade da Dívida)")
            
            def faixas_atraso(dias):
                if dias < 0: return "A Vencer"
                if dias <= 15: return "0-15 Dias"
                if dias <= 30: return "16-30 Dias"
                if dias <= 60: return "31-60 Dias"
                else: return "> 60 Dias"
            
            df_full['Dias_Atraso'] = (hoje - df_full['Vencimento_DT']).dt.days
            df_full['Faixa_Ageing'] = df_full['Dias_Atraso'].apply(faixas_atraso)
            
            ordem_ageing = ['> 60 Dias', '31-60 Dias', '16-30 Dias', '0-15 Dias', 'A Vencer']
            df_ageing = df_full.groupby('Faixa_Ageing')['Saldo_Limpo'].sum().reindex(ordem_ageing).reset_index().fillna(0)
            
            fig_ageing = px.bar(
                df_ageing, 
                x='Saldo_Limpo', 
                y='Faixa_Ageing', 
                orientation='h',
                text_auto='.2s',
                color='Faixa_Ageing',
                color_discrete_map={'A Vencer': '#2ecc71', '> 60 Dias': '#c0392b'}
            )
            fig_ageing.update_layout(showlegend=False)
            st.plotly_chart(fig_ageing, use_container_width=True)

        # --- 5. TABELA DE OFENSORES ---
        st.subheader("🔥 Top 10 Maiores Títulos Vencidos")
        df_vencidos = df_full[df_full['Status_Tempo'] == "🚨 Vencido"].sort_values('Saldo_Limpo', ascending=False).head(10)
        
        if not df_vencidos.empty:
            st.dataframe(
                df_vencidos[['Beneficiario', 'Vencimento', 'Saldo Atual', 'Carteira']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ Nenhum título vencido encontrado!")

    else:
        st.info("📭 A base de histórico está vazia.")

except Exception as e:
    st.error(f"Erro ao carregar Dashboard: {e}")
