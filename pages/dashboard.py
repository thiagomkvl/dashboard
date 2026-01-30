import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import conectar_sheets
from modules.utils import formatar_real

# --- CONFIGURAÇÃO DA JANELA MODAL ---
@st.dialog("🔍 Detalhes do Dia")
def mostrar_detalhes_dia(data_selecionada, df_completo):
    # 1. Padroniza a data clicada
    data_sel = pd.to_datetime(data_selecionada).normalize()
    
    # 2. Filtra o dia
    mask_dia = pd.to_datetime(df_completo['Vencimento_DT']).dt.normalize() == data_sel
    df_dia = df_completo[mask_dia].copy()
    
    if not df_dia.empty:
        total_dia = df_dia['Saldo_Limpo'].sum()
        qtd_titulos = len(df_dia)
        
        c1, c2 = st.columns(2)
        c1.write(f"📅 **Data:** {data_sel.strftime('%d/%m/%Y')}")
        c2.write(f"🔢 **Qtd Títulos:** {qtd_titulos}")
        st.metric("Total a Pagar no Dia", formatar_real(total_dia))
        
        st.divider()
        
        # --- BLINDAGEM DE COLUNAS ---
        colunas_desejadas = ['Beneficiario', 'Saldo Atual', 'Carteira', 'Nr. Titulo']
        for col in colunas_desejadas:
            if col not in df_dia.columns:
                df_dia[col] = "-"
        
        df_tabela = df_dia[colunas_desejadas].copy()
        
        # Ordenação segura
        df_tabela['Valor_Num'] = pd.to_numeric(df_tabela['Saldo Atual'], errors='coerce').fillna(0)
        df_tabela = df_tabela.sort_values('Valor_Num', ascending=False).drop(columns=['Valor_Num'])
        
        st.dataframe(
            df_tabela,
            column_config={
                "Beneficiario": st.column_config.TextColumn("Fornecedor", width="medium"),
                "Saldo Atual": st.column_config.TextColumn("Valor"),
                "Carteira": st.column_config.TextColumn("Status", width="small"),
                "Nr. Titulo": st.column_config.TextColumn("Nota/Título", width="small")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning(f"Não foram encontrados dados para a data {data_sel.strftime('%d/%m/%Y')}.")

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
        ultima_data = df_hist['data_processamento'].max()
        df_full = df_hist[df_hist['data_processamento'] == ultima_data].copy()
        df_full['Vencimento_DT'] = pd.to_datetime(df_full['Vencimento'], dayfirst=True, errors='coerce')
        hoje = pd.Timestamp.now().normalize()
        
        # Categorização de Status
        def definir_status(row):
            if row['Vencimento_DT'] < hoje: return "🚨 Vencido"
            elif row['Vencimento_DT'] == hoje: return "⚠️ Vence Hoje"
            else: return "📅 A Vencer"
            
        df_full['Status_Tempo'] = df_full.apply(definir_status, axis=1)

        # --- 2. PAINEL DE KPIs ---
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

        # --- 3. GRÁFICO 1: CRONOGRAMA DE DESEMBOLSO ---
        df_futuro = df_full[df_full['Vencimento_DT'] >= hoje].copy()
        
        if not df_futuro.empty:
            st.subheader("📅 Cronograma de Desembolso")
            st.caption("🖐️ Arraste para navegar. 🖱️ **Clique na barra** para ver TODOS os pagamentos do dia.")
            
            # Ordenação
            df_grafico = df_futuro.sort_values('Vencimento_DT')
            
            # TOTAIS NO TOPO
            df_totais = df_grafico.groupby('Vencimento_DT', as_index=False)['Saldo_Limpo'].sum()
            df_totais['Label'] = df_totais['Saldo_Limpo'].apply(lambda x: f"R$ {x/1000:.1f}k" if x > 1000 else f"{int(x)}")
            max_valor_dia = df_totais['Saldo_Limpo'].max()

            # GRÁFICO BASE
            fig_stack = px.bar(
                df_grafico, 
                x='Vencimento_DT', 
                y='Saldo_Limpo', 
                color='Beneficiario', 
                title="Fluxo de Pagamentos Diário",
                labels={'Saldo_Limpo': 'Valor', 'Vencimento_DT': 'Data', 'Beneficiario': 'Fornecedor'},
                height=550
            )
            
            # RÓTULOS DE TOTAL
            fig_stack.add_trace(
                go.Scatter(
                    x=df_totais['Vencimento_DT'],
                    y=df_totais['Saldo_Limpo'],
                    text=df_totais['Label'],
                    mode='text',
                    textposition='top center',
                    textfont=dict(size=12, color='black', family="Arial Black"),
                    showlegend=False,
                    hoverinfo='skip'
                )
            )

            # CONFIGURAÇÃO DE LAYOUT
            fig_stack.update_layout(
                xaxis=dict(
                    range=[hoje - pd.Timedelta(days=0.5), hoje + pd.Timedelta(days=6.5)],
                    tickmode='linear',
                    dtick="D1",
                    tickformat="%d/%m",
                    rangeslider=dict(visible=False), 
                    type="date"
                ),
                yaxis=dict(
                    range=[0, max_valor_dia * 1.2], 
                    fixedrange=True
                ),
                showlegend=True,
                legend=dict(
                    orientation="v",       
                    y=1, yanchor="top",    
                    x=1.01, xanchor="left",
                    title_text="Fornecedores"
                ),
                margin=dict(r=20, t=50),
                dragmode="pan", 
                # MUDANÇA IMPORTANTE: 'event' apenas dispara o dado, não seleciona visualmente
                clickmode="event" 
            )
            
            # RENDERIZAÇÃO E LÓGICA DE EVENTO
            # doubleClick='reset+autosize' -> 'False' (desativa o reset no duplo clique)
            evento = st.plotly_chart(
                fig_stack, 
                use_container_width=True, 
                config={'scrollZoom': False, 'displayModeBar': False, 'doubleClick': False},
                on_select="rerun", # Mantém rerun para processar o clique
                selection_mode="points"
            )

            # LÓGICA DE ABERTURA
            if evento and "selection" in evento and evento["selection"]["points"]:
                ponto_clicado = evento["selection"]["points"][0]
                data_clicada = ponto_clicado["x"]
                mostrar_detalhes_dia(data_clicada, df_full)

        st.divider()

        # --- 4. ANÁLISE DE COMPOSIÇÃO ---
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
            st.subheader("⏳ Ageing List")
            
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
        
        # Blinda colunas
        cols_vencidos = ['Beneficiario', 'Vencimento', 'Saldo Atual', 'Carteira']
        for col in cols_vencidos:
            if col not in df_vencidos.columns:
                df_vencidos[col] = "-"

        if not df_vencidos.empty:
            st.dataframe(
                df_vencidos[cols_vencidos],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ Nenhum título vencido encontrado!")

    else:
        st.info("📭 A base de histórico está vazia. Faça upload na aba correspondente.")

except Exception as e:
    st.error(f"Erro ao carregar Dashboard: {e}")
