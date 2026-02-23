import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import conectar_sheets

# --- IMPORTAÇÃO SEGURA ---
try:
    from modules.utils import formatar_real, identificar_tipo_pagamento
    from modules.cnab_engine import gerar_cnab_pix 
except ImportError as e:
    st.error(f"Erro crítico nos módulos: {e}")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Cockpit Financeiro - SOS Cardio", page_icon="🎛️", layout="wide")

# --- CUSTOM CSS (Magia do UI/UX) ---
st.markdown("""
    <style>
    /* Status Bar Header */
    .status-dot { height: 12px; width: 12px; background-color: #00C851; border-radius: 50%; display: inline-block; margin-left: 5px; margin-right: 20px;}
    .status-text { font-size: 16px; font-weight: bold; color: #4F4F4F; display: inline-block; }
    
    /* Estilo dos Cards de KPI Superiores */
    .kpi-card {
        background-color: #F8F9FA; 
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .kpi-title { font-size: 16px; color: #6c757d; text-align: center; margin-bottom: 5px;}
    .kpi-value { font-size: 32px; font-weight: bold; color: #343a40; text-align: center; margin-bottom: 15px;}
    .kpi-perc-text { font-size: 13px; color: #6c757d; margin-top: 5px; display: flex; justify-content: space-between;}
    
    /* Destaque do Topo da Tabela (Workaround para Canvas) */
    [data-testid="stDataFrame"] > div:first-child {
        border-top: 4px solid #212529 !important;
        border-radius: 4px 4px 0 0;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. HEADER (STATUS DE CONEXÕES)
# ==============================================================================
st.markdown("""
    <div style='display: flex; align-items: center; margin-bottom: 20px;'>
        <div class='status-text'>Dashboard Financeiro</div><span class='status-dot'></span>
        <div class='status-text'>Banco de dados Tasy</div><span class='status-dot'></span>
        <div class='status-text'>API Santander</div><span class='status-dot'></span>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CARGA DE DADOS (REAL + FICTÍCIO)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_reais():
    try:
        conn = conectar_sheets()
        df = conn.read(worksheet="Pagamentos_Dia", ttl=0)
        if df.empty: return pd.DataFrame()
        
        if 'Pagar?' not in df.columns: df.insert(0, 'Pagar?', True)
        df['Pagar?'] = df['Pagar?'].astype(bool)
        
        if 'VALOR_PAGAMENTO' in df.columns:
            df['VALOR_PAGAMENTO'] = pd.to_numeric(df['VALOR_PAGAMENTO'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        
        # Mockups de colunas faltantes para bater com a imagem
        if 'Categoria' not in df.columns: df['Categoria'] = 'Estoque Medicamentos'
        if 'OC' not in df.columns: df['OC'] = np.random.randint(100000, 999999, df.shape[0])
        if 'NF' not in df.columns: df['NF'] = np.random.randint(1000, 9999, df.shape[0])
        if 'Observação' not in df.columns: df['Observação'] = '-x-'
        if 'Banco_Origem' not in df.columns: df['Banco_Origem'] = 'Unicred - C.C'
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar Sheets: {e}")
        return pd.DataFrame()

df_real = carregar_dados_reais()

# ==============================================================================
# 3. MÓDULO DE KPIs SUPERIORES
# ==============================================================================
total_saidas = df_real['VALOR_PAGAMENTO'].sum() if not df_real.empty else 457590.90
saldo_disponivel = 957590.90
saldo_resgate = 20457590.90
saldo_final = saldo_disponivel - total_saidas

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

def gerar_html_kpi(titulo, valor, pct_progress, cor_barra, texto_rodape):
    return f"""
    <div class='kpi-card'>
        <div class='kpi-title'>{titulo}</div>
        <div class='kpi-value'>{valor}</div>
        <div class='kpi-perc-text'>
            <span>% Comprometido: {pct_progress}%</span>
            <span>{pct_progress}%</span>
        </div>
        <div style='width: 100%; background-color: #E0E0E0; border-radius: 4px; height: 8px; margin-top: 5px;'>
            <div style='width: {pct_progress}%; background-color: {cor_barra}; height: 8px; border-radius: 4px;'></div>
        </div>
    </div>
    """

kpi1.markdown(gerar_html_kpi("Saldo disponível", formatar_real(saldo_disponivel), 50, "#1cc88a", "50%"), unsafe_allow_html=True)
kpi2.markdown(gerar_html_kpi("Saldo Resgate", formatar_real(saldo_resgate), 56, "#e74a3b", "56%"), unsafe_allow_html=True)
kpi3.markdown(gerar_html_kpi("Saídas Previstas", formatar_real(total_saidas), 100, "#f6c23e", "100%"), unsafe_allow_html=True)
kpi4.markdown(gerar_html_kpi("Saldo Final Previsto", formatar_real(saldo_final), 26, "#5a5c69", "26%"), unsafe_allow_html=True)

st.divider()

# ==============================================================================
# 4. CORPO PRINCIPAL (TABELA À ESQUERDA, GRÁFICOS À DIREITA)
# ==============================================================================
col_left, col_right = st.columns([1.3, 1])

# --- ESQUERDA: TABELA E GERAÇÃO CNAB ---
with col_left:
    tab1, tab2 = st.tabs(["Enviar Remessa de Pagamentos", "Títulos Vencidos"])
    
    with tab1:
        if not df_real.empty:
            colunas_visuais = ['Pagar?', 'NOME_FAVORECIDO', 'Categoria', 'OC', 'NF', 'Observação', 'DATA_PAGAMENTO', 'VALOR_PAGAMENTO', 'Banco_Origem', 'CHAVE_PIX_OU_COD_BARRAS', 'cnpj_beneficiario']
            for col in colunas_visuais:
                if col not in df_real.columns: df_real[col] = ""
                
            df_display = df_real[colunas_visuais].copy()
            
            # Altura cravada em 760 para alinhar com o bloco de HTML + os 2 gráficos da direita
            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                height=760, 
                column_config={
                    "Pagar?": st.column_config.CheckboxColumn("Pagar", default=True),
                    "NOME_FAVORECIDO": "Pagamento",
                    "DATA_PAGAMENTO": "Venc. original",
                    "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Banco_Origem": "Banco",
                    "CHAVE_PIX_OU_COD_BARRAS": None, 
                    "cnpj_beneficiario": None
                }
            )
            
            st.write("")
            
            df_pagar = edited_df[edited_df['Pagar?'] == True].copy()
            if st.button("🚀 Gerar Arquivo de Remessa (CNAB 240)", type="primary"):
                if not df_pagar.empty:
                    arquivo_cnab = gerar_cnab_pix(df_pagar)
                    if arquivo_cnab:
                        st.download_button(
                            label="📥 Baixar CNAB", 
                            data=arquivo_cnab, 
                            file_name=f"REM_{datetime.now().strftime('%d%m')}.txt",
                            mime="text/plain"
                        )
                else:
                    st.warning("Nenhum título selecionado para pagamento.")
        else:
            st.info("Nenhum dado encontrado na planilha.")

    with tab2:
        st.info("Aqui entrará a query direta do banco de dados do Tasy listando os títulos vencidos.")

# --- DIREITA: GRÁFICOS ALINHADOS À REALIDADE DO HOSPITAL ---
with col_right:
    # Blocos HTML Alinhados com a Tabela (margin-top compensa as Abas) e linha vertical
    st.markdown("""
    <div style="display: flex; gap: 15px; margin-top: 48px; margin-bottom: 20px;">
        <div style="flex: 1; background-color: #F8F9FA; padding: 15px; border-radius: 8px; border: 1px solid #E9ECEF; border-left: 5px solid #36b9cc;">
            <div style="font-size: 14px; color: #6c757d; font-weight: 600;">Total Acordos</div>
            <div style="font-size: 22px; color: #343a40; font-weight: bold;">R$ 45.320,00</div>
        </div>
        <div style="flex: 1; background-color: #F8F9FA; padding: 15px; border-radius: 8px; border: 1px solid #E9ECEF; border-left: 5px solid #f6c23e;">
            <div style="font-size: 14px; color: #6c757d; font-weight: 600;">Total Ordem de Compras</div>
            <div style="font-size: 22px; color: #343a40; font-weight: bold;">R$ 128.450,00</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Função auxiliar para formatar em K (ex: 120k) e não poluir o gráfico
    def form_k(valor):
        return f"{valor/1000:.0f}k" if valor >= 1000 else str(valor)

    # Configuração de Interatividade (Arrastar/Pan Mode)
    chart_config = {'scrollZoom': False, 'displayModeBar': False}

    # ---------------------------------------------------------
    # Gráfico 1: Total a Pagar x Total Pago (DUAS TENDÊNCIAS)
    # ---------------------------------------------------------
    dias = [(datetime.now() - timedelta(days=i)).strftime('%d/%m') for i in range(13, -1, -1)] # 14 dias para dar efeito de scroll
    a_pagar = [100000, 95000, 120000, 150000, 110000, 180000, 90000, 130000, 250000, 140000, 160000, 110000, 190000, 145000]
    pago =    [80000,  90000, 90000,  110000, 110000, 130000, 80000, 100000, 150000, 100000, 150000, 100000, 180000, 120000]
    
    text_pagar = [form_k(v) for v in a_pagar]
    text_pago = [form_k(v) for v in pago]

    fig1 = go.Figure()
    
    # Barras principais
    fig1.add_trace(go.Bar(x=dias, y=a_pagar, name='A Pagar', marker_color='#e74a3b', text=text_pagar, textposition='outside', textfont=dict(size=11))) 
    fig1.add_trace(go.Bar(x=dias, y=pago, name='Pago', marker_color='#1cc88a', text=text_pago, textposition='outside', textfont=dict(size=11)))    
    
    # Duas Linhas de Tendência (Uma para cada métrica)
    fig1.add_trace(go.Scatter(x=dias, y=a_pagar, name='Tend. (A Pagar)', mode='lines', line=dict(color='#e74a3b', width=2, dash='dash')))
    fig1.add_trace(go.Scatter(x=dias, y=pago, name='Tend. (Pago)', mode='lines', line=dict(color='#1cc88a', width=2, dash='dash')))

    fig1.update_layout(
        title=dict(text="Total a Pagar x Total Pago", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='group', 
        margin=dict(l=20, r=20, t=50, b=20), 
        height=300, 
        paper_bgcolor='#F8F9FA',
        plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        dragmode='pan' # Ativa o arraste
    )
    # Mostra apenas os últimos 6 dias e permite arrastar para a esquerda
    fig1.update_xaxes(fixedrange=False, range=[len(dias)-6.5, len(dias)-0.5]) 
    fig1.update_yaxes(fixedrange=True, range=[0, max(a_pagar)*1.2]) # Espaço para o texto no topo
    
    st.plotly_chart(fig1, use_container_width=True, config=chart_config)
    
    # ---------------------------------------------------------
    # Gráfico 2: Categorias das Despesas Diarizadas
    # ---------------------------------------------------------
    # Dados expandidos para 14 dias
    cat_med = [40000, 50000, 30000, 60000, 35000, 40000, 70000, 40000, 50000, 30000, 60000, 35000, 40000, 70000]
    cat_hon = [30000, 40000, 50000, 40000, 25000, 30000, 50000, 30000, 40000, 50000, 40000, 25000, 30000, 50000]
    cat_man = [10000, 10000, 15000, 20000, 10000, 20000, 15000, 10000, 10000, 15000, 20000, 10000, 20000, 15000]
    cat_imp = [10000, 10000, 15000, 10000, 10000, 10000, 15000, 10000, 10000, 15000, 10000, 10000, 10000, 15000]
    
    # Calculando Totais para colocar no topo da barra
    totais = [m+h+ma+i for m, h, ma, i in zip(cat_med, cat_hon, cat_man, cat_imp)]
    text_totais = [f"<b>{form_k(v)}</b>" for v in totais]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=dias, y=cat_med, name='Insumos', marker_color='#4e73df')) 
    fig2.add_trace(go.Bar(x=dias, y=cat_hon, name='Médicos', marker_color='#36b9cc'))   
    fig2.add_trace(go.Bar(x=dias, y=cat_man, name='Geral', marker_color='#f6c23e'))     
    fig2.add_trace(go.Bar(x=dias, y=cat_imp, name='Impostos', marker_color='#858796'))             
    
    # Linha de Tendência + Rótulo Total Fixo no Topo
    fig2.add_trace(go.Scatter(x=dias, y=totais, name='Tendência (Geral)', mode='lines+text', text=text_totais, textposition='top center', textfont=dict(size=12, color='#343a40'), line=dict(color='#858796', width=2)))

    fig2.update_layout(
        title=dict(text="Despesas por Categoria (Visão Diária)", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='stack', 
        margin=dict(l=20, r=20, t=50, b=20), 
        height=300, 
        paper_bgcolor='#F8F9FA',
        plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        dragmode='pan'
    )
    
    fig2.update_xaxes(fixedrange=False, range=[len(dias)-6.5, len(dias)-0.5]) 
    fig2.update_yaxes(fixedrange=True, range=[0, max(totais)*1.2])
    
    st.plotly_chart(fig2, use_container_width=True, config=chart_config)
