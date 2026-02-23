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
    
    /* Estilo dos Cards de KPI Superiores (HTML Customizado) */
    .kpi-card {
        background-color: #F8F9FA; /* Cinza leve do fundo */
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .kpi-title { font-size: 16px; color: #6c757d; text-align: center; margin-bottom: 5px;}
    .kpi-value { font-size: 32px; font-weight: bold; color: #343a40; text-align: center; margin-bottom: 15px;}
    .kpi-perc-text { font-size: 13px; color: #6c757d; margin-top: 5px; display: flex; justify-content: space-between;}
    
    /* Estilo dos Sub-KPIs (Nativos do Streamlit) */
    [data-testid="stMetric"] {
        background-color: #F8F9FA;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
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
# 3. MÓDULO DE KPIs SUPERIORES (Design em Cards Fechados)
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
            
            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                height=700, 
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
    # Sub-KPIs (Com fundo cinza aplicado via CSS global)
    skpi1, skpi2 = st.columns(2)
    skpi1.metric("Total Acordos", "R$ 45.320,00") 
    skpi2.metric("Total Ordem de Compras", "R$ 128.450,00")
    
    st.write("")
    
    # ---------------------------------------------------------
    # Gráfico 1: Total a Pagar x Total Pago 
    # ---------------------------------------------------------
    dias = [(datetime.now() - timedelta(days=i)).strftime('%d/%m') for i in range(6, -1, -1)]
    a_pagar = [120000, 150000, 110000, 180000, 90000, 130000, 250000] 
    pago =    [90000,  110000, 110000, 130000, 80000, 100000, 150000]  
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=dias, y=a_pagar, name='A Pagar (Vencido)', marker_color='#e74a3b')) 
    fig1.add_trace(go.Bar(x=dias, y=pago, name='Efetivamente Pago', marker_color='#1cc88a'))    
    
    fig1.update_layout(
        title=dict(text="Total a Pagar x Total Pago (Últimos 7 Dias)", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='group', 
        margin=dict(l=20, r=20, t=50, b=20), 
        height=300, 
        paper_bgcolor='#F8F9FA', # O Fundo Cinza Mágico aqui!
        plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # ---------------------------------------------------------
    # Gráfico 2: Categorias das Despesas Diarizadas
    # ---------------------------------------------------------
    cat_med = [40000, 50000, 30000, 60000, 35000, 40000, 70000]
    cat_hon = [30000, 40000, 50000, 40000, 25000, 30000, 50000]
    cat_man = [10000, 10000, 15000, 20000, 10000, 20000, 15000]
    cat_imp = [10000, 10000, 15000, 10000, 10000, 10000, 15000]
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=dias, y=cat_med, name='Medicamentos', marker_color='#4e73df')) 
    fig2.add_trace(go.Bar(x=dias, y=cat_hon, name='Honorários', marker_color='#36b9cc'))   
    fig2.add_trace(go.Bar(x=dias, y=cat_man, name='Manutenção', marker_color='#f6c23e'))     
    fig2.add_trace(go.Bar(x=dias, y=cat_imp, name='Impostos', marker_color='#858796'))             
    
    fig2.update_layout(
        title=dict(text="Despesas por Categoria (Visão Diária)", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='stack', 
        margin=dict(l=20, r=20, t=50, b=20), 
        height=300, 
        paper_bgcolor='#F8F9FA', # Fundo Cinza no segundo gráfico
        plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig2, use_container_width=True)
