import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import conectar_sheets
from modules.utils import formatar_real

# --- 1. MODAL DETALHES POR DIA (CRONOGRAMA) ---
@st.dialog("🔍 Detalhes do Dia")
def mostrar_detalhes_dia(data_selecionada, df_completo):
    data_sel = pd.to_datetime(data_selecionada).normalize()
    mask_dia = pd.to_datetime(df_completo['Vencimento_DT']).dt.normalize() == data_sel
    df_dia = df_completo[mask_dia].copy()
    
    exibir_tabela_detalhada(df_dia, f"📅 Data: {data_sel.strftime('%d/%m/%Y')}")

# --- 2. MODAL DETALHES POR AGEING ---
@st.dialog("⏳ Detalhes da Faixa de Atraso")
def mostrar_detalhes_ageing(faixa_selecionada, df_completo):
    df_faixa = df_completo[df_completo['Faixa_Ageing'] == faixa_selecionada].copy()
    exibir_tabela_detalhada(df_faixa, f"📂 Faixa: {faixa_selecionada}")

# --- FUNÇÃO AUXILIAR DE TABELA ---
def exibir_tabela_detalhada(df_filtrado, titulo_contexto):
    if not df_filtrado.empty:
        total = df_filtrado['Saldo_Limpo'].sum()
        qtd = len(df_filtrado)
        
        c1, c2 = st.columns(2)
        c1.write(f"**{titulo_contexto}**")
        c2.write(f"🔢 **Qtd Títulos:** {qtd}")
        st.metric("Total Selecionado", formatar_real(total))
        
        st.divider()
        
        cols_view = ['Beneficiario', 'Saldo Atual', 'Vencimento', 'Carteira', 'Nr. Titulo']
        for col in cols_view:
            if col not in df_filtrado.columns: df_filtrado[col] = "-"
        
        df_filtrado['Valor_Num'] = pd.to_numeric(df_filtrado['Saldo Atual'], errors='coerce').fillna(0)
        df_tabela = df_filtrado.sort_values('Valor_Num', ascending=False)
        
        st.dataframe(
            df_tabela[cols_view],
            column_config={
                "Beneficiario": st.column_config.TextColumn("Fornecedor", width="medium"),
                "Saldo Atual": st.column_config.TextColumn("Valor"),
                "Vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                "Carteira": st.column_config.TextColumn("Status", width="small"),
                "Nr. Titulo": st.column_config.TextColumn("Nota/Título", width="small")
            },
            hide_index=True, use_container_width=True
        )
    else:
        st.warning("Nenhum registro encontrado.")

# --- BLOQUEIO DE SEGURANÇA ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.title("📉 Gestão de Dívida com Fornecedores")
st.caption("Visão analítica do Passivo e Contas a Pagar")

# --- PROCESSAMENTO DE DADOS ---
conn = conectar_sheets()
try:
    df_hist = conn.read(worksheet="Historico", ttl=300)
    
    if not df_hist.empty:
        df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
        ultima_data = df_hist['data_processamento'].max()
        df_full = df_hist[df_hist['data_processamento'] == ultima_data].copy()
        df_full['Vencimento_DT'] = pd.to_datetime(df_full['Vencimento'], dayfirst=True, errors='coerce')
        hoje = pd.Timestamp.now().normalize()
        
        # Ageing Logic
        def faixas_atraso(dias):
            if dias < 0: return "A Vencer"
            if dias <= 15: return "0-15 Dias"
            if dias <= 30: return "16-30 Dias"
            if dias <= 60: return "31-60 Dias"
            else: return "> 60 Dias"
        df_full['Dias_Atraso'] = (hoje - df_full['Vencimento_DT']).dt.days
        df_full['Faixa_Ageing'] = df_full['Dias_Atraso'].apply(faixas_atraso)

        # Status Tempo
        def definir_status(row):
            if row['Vencimento_DT'] < hoje: return "🚨 Vencido"
            elif row['Vencimento_DT'] == hoje: return "⚠️ Vence Hoje"
            else: return "📅 A Vencer"
        df_full['Status_Tempo'] = df_full.apply(definir_status, axis=1)

        # KPIs
        total_divida = df_full['Saldo_Limpo'].sum()
        total_vencido = df_full[df_full['Status_Tempo'] == "🚨 Vencido"]['Saldo_Limpo'].sum()
        total_hoje = df_full[df_full['Status_Tempo'] == "⚠️ Vence Hoje"]['Saldo_Limpo'].sum()
        mask_semana = (df_full['Vencimento_DT'] > hoje) & (df_full['Vencimento_DT'] <= hoje + pd.Timedelta(days=7))
        total_semana = df_full[mask_semana]['Saldo_Limpo'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Dívida Total", formatar_real(total_divida))
        col2.metric("Vencido (Backlog)", formatar_real(total_vencido), delta_color="inverse")
        col3.metric("Vence Hoje", formatar_real(total_hoje), delta_color="inverse")
        col4.metric("Próximos 7 Dias", formatar_real(total_semana))

        st.divider()

        # --- 3. CRONOGRAMA (INTERATIVO) ---
        df_futuro = df_full[df_full['Vencimento_DT'] >= hoje].copy()
        
        if not df_futuro.empty:
            st.subheader("📅 Cronograma de Desembolso")
            st.caption("🖐️ Arraste para navegar. 🖱️ **Clique na barra** para ver pagamentos do dia.")
            
            df_grafico = df_futuro.sort_values('Vencimento_DT')
            df_totais = df_grafico.groupby('Vencimento_DT', as_index=False)['Saldo_Limpo'].sum()
            df_totais['Label'] = df_totais['Saldo_Limpo'].apply(lambda x: f"R$ {x/1000:.1f}k" if x > 1000 else f"{int(x)}")
            max_val = df_totais['Saldo_Limpo'].max()

            fig_stack = px.bar(
                df_grafico, x='Vencimento_DT', y='Saldo_Limpo', color='Beneficiario', 
                title="Fluxo de Pagamentos Diário", height=550,
                labels={'Saldo_Limpo': 'Valor', 'Vencimento_DT': 'Data', 'Beneficiario': 'Fornecedor'}
            )
            
            fig_stack.update_traces(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))
            fig_stack.add_trace(go.Scatter(
                x=df_totais['Vencimento_DT'], y=df_totais['Saldo_Limpo'],
                text=df_totais['Label'], mode='text', textposition='top center',
                textfont=dict(size=12, color='black', family="Arial Black"), showlegend=False, hoverinfo='skip'
            ))

            fig_stack.update_layout(
                xaxis=dict(range=[hoje-pd.Timedelta(days=0.5), hoje+pd.Timedelta(days=6.5)], tickmode='linear', dtick="D1", tickformat="%d/%m", rangeslider=dict(visible=False)),
                yaxis=dict(range=[0, max_val * 1.2], fixedrange=True),
                showlegend=True, legend=dict(orientation="v", y=1, x=1.01),
                margin=dict(r=20, t=50), dragmode="pan", clickmode="event+select"
            )
            
            evento_crono = st.plotly_chart(
                fig_stack, use_container_width=True, 
                config={'scrollZoom': False, 'displayModeBar': False, 'doubleClick': False},
                on_select="rerun", selection_mode="points"
            )

            if evento_crono and "selection" in evento_crono and evento_crono["selection"]["points"]:
                mostrar_detalhes_dia(evento_crono["selection"]["points"][0]["x"], df_full)

        st.divider()

        # --- 4. SEÇÃO MACRO ---
        c_left, c_right = st.columns([1, 1])
        
        # --- 4.1 ESQUERDA: TREEMAP MENSAL ---
        with c_left:
            st.subheader("📆 Dívida por Mês (Visão Macro)")
            
            df_full['Mes_Ref'] = df_full['Vencimento_DT'].dt.to_period('M').dt.to_timestamp()
            df_mes = df_full.groupby('Mes_Ref')['Saldo_Limpo'].sum().reset_index()
            df_mes['Mes_Label'] = df_mes['Mes_Ref'].dt.strftime('%b/%y')
            
            fig_mes = px.treemap(
                df_mes, path=['Mes_Label'], values='Saldo_Limpo', color='Saldo_Limpo',
                color_continuous_scale='Reds', hover_data={'Saldo_Limpo': ':,.2f'}
            )
            fig_mes.update_traces(textinfo="label+value+percent entry", texttemplate="%{label}<br>R$ %{value:,.0f}")
            fig_mes.update_layout(margin=dict(t=30, l=0, r=0, b=0))
            st.plotly_chart(fig_mes, use_container_width=True)

        # --- 4.2 DIREITA: AGEING LIST INTERATIVO (REORDENADO) ---
        with c_right:
            st.subheader("⏳ Ageing List (Interativo)")
            st.caption("🖱️ **Clique na barra** para ver detalhes.")

            # MUDANÇA AQUI: Ordem Cronológica (Menor para Maior)
            ordem_ageing = ['A Vencer', '0-15 Dias', '16-30 Dias', '31-60 Dias', '> 60 Dias']
            
            df_ageing = df_full.groupby('Faixa_Ageing')['Saldo_Limpo'].sum().reindex(ordem_ageing).reset_index().fillna(0)
            
            fig_ageing = px.bar(
                df_ageing, x='Saldo_Limpo', y='Faixa_Ageing', orientation='h', text_auto='.2s',
                color='Faixa_Ageing', color_discrete_map={'A Vencer': '#2ecc71', '> 60 Dias': '#c0392b', '31-60 Dias': '#e74c3c'}
            )
            
            fig_ageing.update_traces(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))
            fig_ageing.update_layout(
                showlegend=False, xaxis_title=None, yaxis_title=None,
                clickmode="event+select", dragmode=False
            )
            
            evento_ageing = st.plotly_chart(
                fig_ageing, use_container_width=True,
                config={'displayModeBar': False, 'doubleClick': False},
                on_select="rerun", selection_mode="points"
            )
            
            if evento_ageing and "selection" in evento_ageing and evento_ageing["selection"]["points"]:
                mostrar_detalhes_ageing(evento_ageing["selection"]["points"][0]["y"], df_full)

        # --- 5. TABELA DE OFENSORES ---
        st.subheader("🔥 Top 10 Maiores Títulos Vencidos")
        df_vencidos = df_full[df_full['Status_Tempo'] == "🚨 Vencido"].sort_values('Saldo_Limpo', ascending=False).head(10)
        cols_vencidos = ['Beneficiario', 'Vencimento', 'Saldo Atual', 'Carteira']
        for col in cols_vencidos:
            if col not in df_vencidos.columns: df_vencidos[col] = "-"
            
        if not df_vencidos.empty:
            st.dataframe(df_vencidos[cols_vencidos], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Nenhum título vencido encontrado!")

    else:
        st.info("📭 A base de histórico está vazia.")

except Exception as e:
    st.error(f"Erro ao carregar Dashboard: {e}")
