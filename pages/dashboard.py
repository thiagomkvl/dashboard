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
    # Lê a aba 'Historico' (onde fica a base completa de contas a pagar)
    df_hist = conn.read(worksheet="Historico", ttl=300)
    
    if not df_hist.empty:
        # 1. Tratamento e Limpeza
        # Garante que 'Saldo Atual' seja numérico
        df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
        
        # Filtra apenas o último processamento (Snapshot mais recente)
        ultima_data = df_hist['data_processamento'].max()
        df_full = df_hist[df_hist['data_processamento'] == ultima_data].copy()
        
        # Tratamento de Datas
        df_full['Vencimento_DT'] = pd.to_datetime(df_full['Vencimento'], dayfirst=True, errors='coerce')
        hoje = pd.Timestamp.now().normalize()
        
        # Categorização de Status (Vencido vs A Vencer)
        def definir_status(row):
            if row['Vencimento_DT'] < hoje: return "🚨 Vencido"
            elif row['Vencimento_DT'] == hoje: return "⚠️ Vence Hoje"
            else: return "📅 A Vencer"
            
        df_full['Status_Tempo'] = df_full.apply(definir_status, axis=1)

        # --- 2. PAINEL DE KPIs (TOPO) ---
        total_divida = df_full['Saldo_Limpo'].sum()
        total_vencido = df_full[df_full['Status_Tempo'] == "🚨 Vencido"]['Saldo_Limpo'].sum()
        total_hoje = df_full[df_full['Status_Tempo'] == "⚠️ Vence Hoje"]['Saldo_Limpo'].sum()
        
        # Cálculo da dívida da semana (Próximos 7 dias)
        proxima_semana = hoje + pd.Timedelta(days=7)
        mask_semana = (df_full['Vencimento_DT'] > hoje) & (df_full['Vencimento_DT'] <= proxima_semana)
        total_semana = df_full[mask_semana]['Saldo_Limpo'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Dívida Total", formatar_real(total_divida), help="Soma de todos os títulos em aberto")
        col2.metric("Vencido (Backlog)", formatar_real(total_vencido), delta_color="inverse", help="Títulos com data passada")
        col3.metric("Vence Hoje", formatar_real(total_hoje), delta_color="inverse")
        col4.metric("Próximos 7 Dias", formatar_real(total_semana), help="Projeção de caixa curto prazo")

        st.divider()

        # --- 3. GRÁFICO 1: CRONOGRAMA DE DESEMBOLSO (STACKED BAR OTIMIZADO) ---
        # Filtra apenas o futuro (Hoje em diante) para previsão de caixa
        df_futuro = df_full[df_full['Vencimento_DT'] >= hoje].copy()
        
        if not df_futuro.empty:
            st.subheader("📅 Cronograma de Desembolso (Previsão)")
            
            # Filtro de período dinâmico para o gráfico não ficar poluido
            dias_visualizacao = st.slider("Horizonte de Visualização (Dias):", 7, 90, 30)
            data_limite = hoje + pd.Timedelta(days=dias_visualizacao)
            df_grafico = df_futuro[df_futuro['Vencimento_DT'] <= data_limite].copy()
            
            # Formata data para string (eixo X bonito)
            df_grafico['Data_Str'] = df_grafico['Vencimento_DT'].dt.strftime('%d/%m/%Y')
            df_grafico = df_grafico.sort_values('Vencimento_DT') # Ordena cronologicamente
            
            # O Gráfico Empilhado que você gosta
            fig_stack = px.bar(
                df_grafico, 
                x='Data_Str', 
                y='Saldo_Limpo', 
                color='Beneficiario', 
                title=f"Fluxo de Pagamentos - Próximos {dias_visualizacao} dias",
                labels={'Saldo_Limpo': 'Valor (R$)', 'Data_Str': 'Vencimento', 'Beneficiario': 'Fornecedor'},
                text_auto='.2s',
                height=500
            )
            fig_stack.update_layout(xaxis_type='category', showlegend=True) # Eixo X categórico evita buracos de fds
            st.plotly_chart(fig_stack, use_container_width=True)
        
        st.divider()

        # --- 4. ANÁLISE DE COMPOSIÇÃO (TREEMAP & AGEING) ---
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.subheader("🏗️ Composição da Dívida (Quem?)")
            st.caption("Tamanho do retângulo = Valor da Dívida")
            
            # Agrupamento para o Treemap
            df_tree = df_full.groupby('Beneficiario')['Saldo_Limpo'].sum().reset_index()
            # Pega apenas os Top 30 para não travar o gráfico se tiver milhares
            df_tree = df_tree.sort_values('Saldo_Limpo', ascending=False).head(30)
            
            fig_tree = px.treemap(
                df_tree, 
                path=['Beneficiario'], 
                values='Saldo_Limpo',
                color='Saldo_Limpo',
                color_continuous_scale='Blues',
                hover_data={'Saldo_Limpo': ':,.2f'}
            )
            fig_tree.update_layout(margin=dict(t=0, l=0, r=0, b=0))
            st.plotly_chart(fig_tree, use_container_width=True)

        with c_right:
            st.subheader("⏳ Ageing List (Idade da Dívida)")
            
            # Lógica de Ageing
            def faixas_atraso(dias):
                if dias < 0: return "A Vencer"
                if dias <= 15: return "0-15 Dias"
                if dias <= 30: return "16-30 Dias"
                if dias <= 60: return "31-60 Dias"
                else: return "> 60 Dias"
            
            df_full['Dias_Atraso'] = (hoje - df_full['Vencimento_DT']).dt.days
            df_full['Faixa_Ageing'] = df_full['Dias_Atraso'].apply(faixas_atraso)
            
            # Agrupa e Ordena
            ordem_ageing = ['> 60 Dias', '31-60 Dias', '16-30 Dias', '0-15 Dias', 'A Vencer']
            df_ageing = df_full.groupby('Faixa_Ageing')['Saldo_Limpo'].sum().reindex(ordem_ageing).reset_index().fillna(0)
            
            fig_ageing = px.bar(
                df_ageing, 
                x='Saldo_Limpo', 
                y='Faixa_Ageing', 
                orientation='h',
                text_auto='.2s',
                color='Faixa_Ageing',
                color_discrete_map={'A Vencer': '#2ecc71', '> 60 Dias': '#c0392b'}, # Verde e Vermelho escuro
                title="Distribuição por Atraso"
            )
            fig_ageing.update_layout(showlegend=False)
            st.plotly_chart(fig_ageing, use_container_width=True)

        # --- 5. TABELA DE OFENSORES (CRÍTICO) ---
        st.subheader("🔥 Top 10 Maiores Títulos Vencidos")
        df_vencidos = df_full[df_full['Status_Tempo'] == "🚨 Vencido"].sort_values('Saldo_Limpo', ascending=False).head(10)
        
        if not df_vencidos.empty:
            st.dataframe(
                df_vencidos[['Beneficiario', 'Vencimento', 'Saldo Atual', 'Carteira']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ Nenhum título vencido encontrado! Parabéns pela gestão.")

    else:
        st.info("📭 A base de histórico está vazia. Vá em 'Upload' para carregar os dados.")

except Exception as e:
    st.error(f"Erro ao carregar Dashboard: {e}")
