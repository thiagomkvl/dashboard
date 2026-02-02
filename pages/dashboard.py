import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import conectar_sheets
from modules.utils import formatar_real

# --- PALETA CORPORATE FINTECH ---
COR_AZUL_BASE = "#2c3e50" 
COR_AZUL_CLARO = "#3498db"
COR_LINHA_TENDENCIA = "#e74c3c" 
PALETA_AZUIS = px.colors.sequential.Blues_r 
PALETA_VERMELHOS = px.colors.sequential.Reds

MAPA_CORES_AGEING = {
    'A Vencer': COR_AZUL_CLARO,
    '0-15 Dias': '#f5b7b1',
    '16-30 Dias': '#ec7063',
    '31-60 Dias': '#c0392b',
    '> 60 Dias': '#78281f'
}

# --- MODAIS ---
@st.dialog("🔍 Detalhes do Dia")
def mostrar_detalhes_dia(data_selecionada, df_completo):
    data_sel = pd.to_datetime(data_selecionada).normalize()
    mask_dia = pd.to_datetime(df_completo['Vencimento_DT']).dt.normalize() == data_sel
    exibir_tabela_detalhada(df_completo[mask_dia].copy(), f"📅 Data: {data_sel.strftime('%d/%m/%Y')}")

@st.dialog("⏳ Detalhes da Faixa de Atraso")
def mostrar_detalhes_ageing(faixa_selecionada, df_completo):
    exibir_tabela_detalhada(df_completo[df_completo['Faixa_Ageing'] == faixa_selecionada].copy(), f"📂 Faixa: {faixa_selecionada}")

@st.dialog("📅 Visão Mensal Completa", width="large")
def mostrar_grafico_completo(df_futuro):
    st.caption("Visão macro de todos os lançamentos futuros disponíveis.")
    df_grafico = df_futuro.sort_values('Vencimento_DT')
    df_totais = df_grafico.groupby('Vencimento_DT', as_index=False)['Saldo_Limpo'].sum()
    max_val = df_totais['Saldo_Limpo'].max()

    fig = px.bar(
        df_grafico, x='Vencimento_DT', y='Saldo_Limpo', color='Beneficiario',
        title=None, height=500, labels={'Saldo_Limpo': 'Valor', 'Vencimento_DT': 'Data'},
        color_discrete_sequence=PALETA_AZUIS
    )
    fig.add_trace(go.Scatter(
        x=df_totais['Vencimento_DT'], y=df_totais['Saldo_Limpo'] * 1.05,
        mode='lines+markers', name='Tendência',
        line=dict(color=COR_LINHA_TENDENCIA, width=1.5),
        marker=dict(size=5, color=COR_LINHA_TENDENCIA)
    ))
    fig.update_layout(xaxis=dict(tickformat="%d/%m", dtick="D1"), yaxis=dict(range=[0, max_val * 1.2]), showlegend=False, margin=dict(r=20, t=20))
    st.plotly_chart(fig, use_container_width=True)

# --- FUNÇÃO TABELA ---
def exibir_tabela_detalhada(df_filtrado, titulo_contexto):
    if not df_filtrado.empty:
        total = df_filtrado['Saldo_Limpo'].sum()
        c1, c2 = st.columns(2)
        c1.write(f"**{titulo_contexto}**")
        c2.metric("Total Selecionado", formatar_real(total))
        st.divider()
        cols_view = ['Beneficiario', 'Saldo Atual', 'Vencimento', 'Carteira', 'Nr. Titulo']
        for col in cols_view:
            if col not in df_filtrado.columns: df_filtrado[col] = "-"
        df_filtrado['Valor_Num'] = pd.to_numeric(df_filtrado['Saldo Atual'], errors='coerce').fillna(0)
        st.dataframe(df_filtrado.sort_values('Valor_Num', ascending=False)[cols_view], hide_index=True, use_container_width=True)
    else:
        st.warning("Nenhum registro encontrado.")

# --- APP ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.title("📉 Gestão de Dívida com Fornecedores")
st.caption("Visão analítica do Passivo e Contas a Pagar")

conn = conectar_sheets()
try:
    df_hist = conn.read(worksheet="Historico", ttl=300)
    
    if not df_hist.empty:
        df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
        ultima_data = df_hist['data_processamento'].max()
        df_full = df_hist[df_hist['data_processamento'] == ultima_data].copy()
        df_full['Vencimento_DT'] = pd.to_datetime(df_full['Vencimento'], dayfirst=True, errors='coerce')
        hoje = pd.Timestamp.now().normalize()
        
        # Lógicas
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

        # KPIs
        total_divida = df_full['Saldo_Limpo'].sum()
        total_vencido = df_full[df_full['Status_Tempo'] == "🚨 Vencido"]['Saldo_Limpo'].sum()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Dívida Total", formatar_real(total_divida))
        col2.metric("Vencido (Backlog)", formatar_real(total_vencido), delta_color="inverse")
        col3.metric("Vence Hoje", formatar_real(df_full[df_full['Status_Tempo'] == "⚠️ Vence Hoje"]['Saldo_Limpo'].sum()), delta_color="inverse")
        col4.metric("Próximos 7 Dias", formatar_real(df_full[(df_full['Vencimento_DT'] > hoje) & (df_full['Vencimento_DT'] <= hoje + pd.Timedelta(days=7))]['Saldo_Limpo'].sum()))
        st.divider()

        # GRÁFICO 1
        df_futuro = df_full[df_full['Vencimento_DT'] >= hoje].copy()
        if not df_futuro.empty:
            c_h1, c_h2 = st.columns([0.8, 0.2])
            with c_h1:
                st.subheader("📅 Cronograma de Desembolso")
                st.caption("🖐️ Arraste para navegar. 🖱️ Clique na barra para detalhes.")
            with c_h2:
                if st.button("🔍 Ver Mês"): mostrar_grafico_completo(df_futuro)
            
            df_crono = df_futuro.sort_values('Vencimento_DT')
            df_tot = df_crono.groupby('Vencimento_DT', as_index=False)['Saldo_Limpo'].sum()
            df_tot['Label'] = df_tot['Saldo_Limpo'].apply(lambda x: f"R$ {x/1000:.1f}k" if x > 1000 else f"{int(x)}")
            
            fig_stk = px.bar(df_crono, x='Vencimento_DT', y='Saldo_Limpo', color='Beneficiario', title=None, height=550, color_discrete_sequence=PALETA_AZUIS)
            fig_stk.add_trace(go.Scatter(x=df_tot['Vencimento_DT'], y=df_tot['Saldo_Limpo'] * 1.05, mode='lines+markers', line=dict(color=COR_LINHA_TENDENCIA, width=1.5), marker=dict(size=6, color='white', line=dict(width=1.5, color=COR_LINHA_TENDENCIA)), hoverinfo='skip'))
            fig_stk.add_trace(go.Scatter(x=df_tot['Vencimento_DT'], y=df_tot['Saldo_Limpo'], text=df_tot['Label'], mode='text', textposition='top center', textfont=dict(size=12, color=COR_AZUL_BASE), showlegend=False, hoverinfo='skip'))
            fig_stk.update_traces(selector=dict(type='bar'), marker_line_width=0, selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))
            fig_stk.update_layout(plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(range=[hoje-pd.Timedelta(days=0.5), hoje+pd.Timedelta(days=6.5)], tickmode='linear', dtick="D1", tickformat="%d/%m", rangeslider=dict(visible=False), showgrid=False), yaxis=dict(range=[0, df_tot['Saldo_Limpo'].max()*1.25], fixedrange=True, showgrid=True, gridcolor='#ecf0f1'), showlegend=True, legend=dict(orientation="v", y=1, x=1.01, title=None), margin=dict(r=20, t=50), dragmode="pan", clickmode="event+select")
            ev_cr = st.plotly_chart(fig_stk, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False, 'doubleClick': False}, on_select="rerun", selection_mode="points")
            if ev_cr and "selection" in ev_cr and ev_cr["selection"]["points"]: 
                try: mostrar_detalhes_dia(ev_cr["selection"]["points"][0]["x"], df_full)
                except: pass
        st.divider()

        # GRÁFICOS MACRO
        c_l, c_r = st.columns([1, 1])
        with c_l:
            st.subheader("📆 Dívida por Mês")
            df_mes = df_full.groupby(df_full['Vencimento_DT'].dt.to_period('M').dt.to_timestamp())['Saldo_Limpo'].sum().reset_index()
            df_mes.columns = ['Mes_Ref', 'Saldo_Limpo']
            df_mes['Mes_Label'] = df_mes['Mes_Ref'].dt.strftime('%b/%y')
            fig_m = px.treemap(df_mes, path=['Mes_Label'], values='Saldo_Limpo', color='Saldo_Limpo', color_continuous_scale='Blues')
            fig_m.update_traces(textinfo="label+value+percent entry", texttemplate="<b>%{label}</b><br>R$ %{value:,.0f}", marker=dict(line=dict(width=2, color='white')))
            fig_m.update_layout(margin=dict(t=30, l=0, r=0, b=0))
            st.plotly_chart(fig_m, use_container_width=True)

        with c_r:
            st.subheader("⏳ Ageing List (Por Valor)")
            st.caption("🖱️ Clique na barra para detalhes.")
            df_ag = df_full.groupby('Faixa_Ageing')['Saldo_Limpo'].sum().reset_index().sort_values('Saldo_Limpo')
            fig_ag = px.bar(df_ag, x='Saldo_Limpo', y='Faixa_Ageing', orientation='h', text_auto='.2s', color='Faixa_Ageing', color_discrete_map=MAPA_CORES_AGEING)
            fig_ag.update_traces(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)), marker_line_width=0)
            fig_ag.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, plot_bgcolor="rgba(0,0,0,0)", clickmode="event+select", dragmode=False, xaxis=dict(showgrid=True, gridcolor='#ecf0f1'))
            ev_ag = st.plotly_chart(fig_ag, use_container_width=True, config={'displayModeBar': False, 'doubleClick': False}, on_select="rerun", selection_mode="points")
            if ev_ag and "selection" in ev_ag and ev_ag["selection"]["points"]: mostrar_detalhes_ageing(ev_ag["selection"]["points"][0]["y"], df_full)

        st.divider()

        # --- SEÇÃO ANALÍTICA: TOP OFENSORES (DONUT + TABELA) ---
        st.subheader("🔥 Análise de Ofensores (Vencidos)")
        
        df_vencidos = df_full[df_full['Status_Tempo'] == "🚨 Vencido"].copy()
        
        if not df_vencidos.empty:
            # Agrupa dados
            df_ofensores = df_vencidos.groupby('Beneficiario').agg(
                Total_Divida=('Saldo_Limpo', 'sum'),
                Dias_Medio_Atraso=('Dias_Atraso', 'mean'),
                Qtd_Titulos=('Saldo_Limpo', 'count')
            ).reset_index()
            
            df_top10 = df_ofensores.sort_values('Total_Divida', ascending=False).head(10)
            
            # KPI Pareto
            total_top10 = df_top10['Total_Divida'].sum()
            perc = (total_top10 / total_vencido) * 100
            st.info(f"💡 **Pareto:** Os 10 maiores devedores representam **{perc:.1f}%** de todo o seu passivo vencido.")
            
            c_donut, c_table = st.columns([0.8, 1.2]) # Coluna da Tabela um pouco maior
            
            with c_donut:
                st.markdown("#### 🥧 Concentração")
                st.caption("Participação dos Top 10 no total vencido")
                
                # Visual Diferente: Donut Chart
                fig_donut = px.pie(
                    df_top10, 
                    values='Total_Divida', 
                    names='Beneficiario',
                    hole=0.6, # Faz virar uma rosca (mais moderno)
                    color_discrete_sequence=px.colors.sequential.RdBu # Paleta corporativa
                )
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                fig_donut.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=350)
                st.plotly_chart(fig_donut, use_container_width=True)

            with c_table:
                st.markdown("#### 📋 Ranking Detalhado")
                st.dataframe(
                    df_top10[['Beneficiario', 'Total_Divida', 'Dias_Medio_Atraso', 'Qtd_Titulos']],
                    column_config={
                        "Beneficiario": st.column_config.TextColumn("Fornecedor"),
                        "Total_Divida": st.column_config.ProgressColumn(
                            "Dívida Total", 
                            format="R$ %.2f", 
                            min_value=0, 
                            max_value=df_top10['Total_Divida'].max()
                        ),
                        "Dias_Medio_Atraso": st.column_config.NumberColumn("Atraso (dias)", format="%.0f"),
                        "Qtd_Titulos": st.column_config.NumberColumn("Qtd Docs")
                    },
                    hide_index=True, use_container_width=True, height=400
                )
        else:
            st.success("✅ Parabéns! Não há títulos vencidos na base.")

    else:
        st.info("📭 A base de histórico está vazia.")

except Exception as e:
    st.error(f"Erro ao carregar Dashboard: {e}")
