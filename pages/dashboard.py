import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import conectar_sheets
from modules.utils import formatar_real

# --- PALETA DE CORES (CORPORATE FINTECH) ---
COR_AZUL_BASE = "#2c3e50" 
COR_AZUL_CLARO = "#3498db"
COR_LINHA_TENDENCIA = "#e74c3c" 
PALETA_AZUIS = px.colors.sequential.Blues_r 

MAPA_CORES_AGEING = {
    'A Vencer': COR_AZUL_CLARO,
    '0-15 Dias': '#f5b7b1',
    '16-30 Dias': '#ec7063',
    '31-60 Dias': '#c0392b',
    '> 60 Dias': '#78281f'
}

# --- 1. MODAL DETALHES POR DIA ---
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

# --- 3. MODAL GRÁFICO MÊS COMPLETO (EXPANDIDO) ---
# Adicionado width="large" para ocupar mais espaço na tela
@st.dialog("📅 Visão Mensal Completa", width="large")
def mostrar_grafico_completo(df_futuro):
    st.caption("Visão macro de todos os lançamentos futuros disponíveis.")
    
    df_grafico = df_futuro.sort_values('Vencimento_DT')
    df_totais = df_grafico.groupby('Vencimento_DT', as_index=False)['Saldo_Limpo'].sum()
    max_val = df_totais['Saldo_Limpo'].max()

    # Gráfico Base
    fig = px.bar(
        df_grafico, x='Vencimento_DT', y='Saldo_Limpo', color='Beneficiario',
        title=None, height=500,
        labels={'Saldo_Limpo': 'Valor', 'Vencimento_DT': 'Data'},
        color_discrete_sequence=PALETA_AZUIS
    )
    
    # Linha de Tendência (Sutil)
    fig.add_trace(go.Scatter(
        x=df_totais['Vencimento_DT'], 
        y=df_totais['Saldo_Limpo'] * 1.05, # Levanta a linha 5%
        mode='lines+markers', name='Tendência',
        line=dict(color=COR_LINHA_TENDENCIA, width=1.5), # Linha mais fina
        marker=dict(size=5, color=COR_LINHA_TENDENCIA)
    ))

    fig.update_layout(
        xaxis=dict(tickformat="%d/%m", dtick="D1"),
        yaxis=dict(range=[0, max_val * 1.2]),
        showlegend=False,
        margin=dict(r=20, t=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)


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
        
        def faixas_atraso(dias):
            if dias < 0: return "A Vencer"
            if dias <= 15: return "0-15 Dias"
            if dias <= 30: return "16-30 Dias"
            if dias <= 60: return "31-60 Dias"
            else: return "> 60 Dias"
        df_full['Dias_Atraso'] = (hoje - df_full['Vencimento_DT']).dt.days
        df_full['Faixa_Ageing'] = df_full['Dias_Atraso'].apply(faixas_atraso)

        def definir_status(row):
            if row['Vencimento_DT'] < hoje: return "🚨 Vencido"
            elif row['Vencimento_DT'] == hoje: return "⚠️ Vence Hoje"
            else: return "📅 A Vencer"
        df_full['Status_Tempo'] = df_full.apply(definir_status, axis=1)

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

        # --- 3. CRONOGRAMA ---
        df_futuro = df_full[df_full['Vencimento_DT'] >= hoje].copy()
        
        if not df_futuro.empty:
            c_head1, c_head2 = st.columns([0.8, 0.2])
            with c_head1:
                st.subheader("📅 Cronograma de Desembolso")
                st.caption("🖐️ Arraste para navegar. 🖱️ Clique na barra para detalhes.")
            with c_head2:
                if st.button("🔍 Ver Mês"):
                    mostrar_grafico_completo(df_futuro)
            
            df_grafico = df_futuro.sort_values('Vencimento_DT')
            df_totais = df_grafico.groupby('Vencimento_DT', as_index=False)['Saldo_Limpo'].sum()
            df_totais['Label'] = df_totais['Saldo_Limpo'].apply(lambda x: f"R$ {x/1000:.1f}k" if x > 1000 else f"{int(x)}")
            max_val = df_totais['Saldo_Limpo'].max()

            fig_stack = px.bar(
                df_grafico, x='Vencimento_DT', y='Saldo_Limpo', 
                color='Beneficiario',
                title="Fluxo de Pagamentos Diário", height=550,
                labels={'Saldo_Limpo': 'Valor', 'Vencimento_DT': 'Data', 'Beneficiario': 'Fornecedor'},
                color_discrete_sequence=PALETA_AZUIS 
            )
            
            # LINHA DE TENDÊNCIA (Flutuante e Sutil)
            fig_stack.add_trace(go.Scatter(
                x=df_totais['Vencimento_DT'],
                y=df_totais['Saldo_Limpo'] * 1.05, # Mágica: Levanta a linha 5%
                mode='lines+markers', 
                name='Tendência',
                line=dict(color=COR_LINHA_TENDENCIA, width=1.5), # Linha Fina (Sutil)
                marker=dict(size=6, color='white', line=dict(width=1.5, color=COR_LINHA_TENDENCIA)),
                hoverinfo='skip'
            ))

            # Rótulos de Texto (Fonte Normal)
            fig_stack.add_trace(go.Scatter(
                x=df_totais['Vencimento_DT'], y=df_totais['Saldo_Limpo'],
                text=df_totais['Label'], mode='text', textposition='top center',
                # Removido "Arial Black" -> Agora é fonte padrão (Normal)
                textfont=dict(size=12, color=COR_AZUL_BASE), 
                showlegend=False, hoverinfo='skip'
            ))

            fig_stack.update_traces(selector=dict(type='bar'), marker_line_width=0, selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))

            fig_stack.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    range=[hoje-pd.Timedelta(days=0.5), hoje+pd.Timedelta(days=6.5)], 
                    tickmode='linear', dtick="D1", tickformat="%d/%m", 
                    rangeslider=dict(visible=False), showgrid=False
                ),
                yaxis=dict(range=[0, max_val * 1.25], fixedrange=True, showgrid=True, gridcolor='#ecf0f1'),
                showlegend=True, legend=dict(orientation="v", y=1, x=1.01, title=None),
                margin=dict(r=20, t=50), dragmode="pan", clickmode="event+select"
            )
            
            evento_crono = st.plotly_chart(
                fig_stack, use_container_width=True, 
                config={'scrollZoom': False, 'displayModeBar': False, 'doubleClick': False},
                on_select="rerun", selection_mode="points"
            )

            if evento_crono and "selection" in evento_crono and evento_crono["selection"]["points"]:
                # Ignora cliques na linha de tendência
                try:
                    point = evento_crono["selection"]["points"][0]
                    mostrar_detalhes_dia(point["x"], df_full)
                except:
                    pass

        st.divider()

        # --- 4. SEÇÃO MACRO ---
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.subheader("📆 Dívida por Mês (Visão Macro)")
            
            df_full['Mes_Ref'] = df_full['Vencimento_DT'].dt.to_period('M').dt.to_timestamp()
            df_mes = df_full.groupby('Mes_Ref')['Saldo_Limpo'].sum().reset_index()
            df_mes['Mes_Label'] = df_mes['Mes_Ref'].dt.strftime('%b/%y')
            
            fig_mes = px.treemap(
                df_mes, path=['Mes_Label'], values='Saldo_Limpo', color='Saldo_Limpo',
                color_continuous_scale='Blues', hover_data={'Saldo_Limpo': ':,.2f'}
            )
            fig_mes.update_traces(textinfo="label+value+percent entry", texttemplate="<b>%{label}</b><br>R$ %{value:,.0f}", marker=dict(line=dict(width=2, color='white')))
            fig_mes.update_layout(margin=dict(t=30, l=0, r=0, b=0))
            st.plotly_chart(fig_mes, use_container_width=True)

        with c_right:
            st.subheader("⏳ Ageing List (Por Valor)")
            st.caption("🖱️ **Clique na barra** para ver detalhes.")

            df_ageing = df_full.groupby('Faixa_Ageing')['Saldo_Limpo'].sum().reset_index()
            df_ageing = df_ageing.sort_values('Saldo_Limpo', ascending=True)
            
            fig_ageing = px.bar(
                df_ageing, x='Saldo_Limpo', y='Faixa_Ageing', orientation='h', text_auto='.2s',
                color='Faixa_Ageing', color_discrete_map=MAPA_CORES_AGEING
            )
            fig_ageing.update_traces(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)), marker_line_width=0)
            fig_ageing.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, plot_bgcolor="rgba(0,0,0,0)", clickmode="event+select", dragmode=False, xaxis=dict(showgrid=True, gridcolor='#ecf0f1'))
            
            evento_ageing = st.plotly_chart(
                fig_ageing, use_container_width=True,
                config={'displayModeBar': False, 'doubleClick': False},
                on_select="rerun", selection_mode="points"
            )
            
            if evento_ageing and "selection" in evento_ageing and evento_ageing["selection"]["points"]:
                mostrar_detalhes_ageing(evento_ageing["selection"]["points"][0]["y"], df_full)

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
