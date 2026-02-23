import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
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

# --- CUSTOM CSS (Para deixar mais parecido com o layout da foto) ---
st.markdown("""
    <style>
    .status-dot { height: 12px; width: 12px; background-color: #00C851; border-radius: 50%; display: inline-block; margin-left: 5px; margin-right: 20px;}
    .status-text { font-size: 16px; font-weight: bold; color: #4F4F4F; display: inline-block; }
    .kpi-title { font-size: 16px; color: #6c757d; text-align: center; margin-bottom: -10px;}
    .kpi-value { font-size: 32px; font-weight: bold; color: #343a40; text-align: center; margin-bottom: 10px;}
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
        
        # Tipagem e Formatação Básica
        if 'Pagar?' not in df.columns: df.insert(0, 'Pagar?', True)
        df['Pagar?'] = df['Pagar?'].astype(bool)
        
        if 'VALOR_PAGAMENTO' in df.columns:
            df['VALOR_PAGAMENTO'] = pd.to_numeric(df['VALOR_PAGAMENTO'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        
        # Adiciona colunas visuais fictícias se não existirem (Para bater com a foto)
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
# 3. MÓDULO DE KPIs SUPERIORES (API SANTANDER / OPEN FINANCE MOCKUP)
# ==============================================================================
# Calculando a saída real + fictícia
total_saidas = df_real['VALOR_PAGAMENTO'].sum() if not df_real.empty else 457590.90
saldo_disponivel = 957590.90
saldo_resgate = 20457590.90
saldo_final = saldo_disponivel - total_saidas

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown("<div class='kpi-title'>Saldo disponível</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{formatar_real(saldo_disponivel)}</div>", unsafe_allow_html=True)
    st.progress(0.50) # 50%
    st.caption("Comprometido: 66,7%")

with kpi2:
    st.markdown("<div class='kpi-title'>Saldo Resgate</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{formatar_real(saldo_resgate)}</div>", unsafe_allow_html=True)
    st.progress(0.56) # 56%
    st.caption("Comprometido: 66,7%")

with kpi3:
    st.markdown("<div class='kpi-title'>Saídas Previstas</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{formatar_real(total_saidas)}</div>", unsafe_allow_html=True)
    st.progress(1.0) # 100% (Amarelo no seu print, o Streamlit usa a cor de tema)
    st.caption("Comprometido: 66,7%")

with kpi4:
    st.markdown("<div class='kpi-title'>Saldo Final Previsto</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{formatar_real(saldo_final)}</div>", unsafe_allow_html=True)
    st.progress(0.26) # 26%
    st.caption("Comprometido: 66,7%")

st.divider()

# ==============================================================================
# 4. CORPO PRINCIPAL (TABELA À ESQUERDA, GRÁFICOS À DIREITA)
# ==============================================================================
col_left, col_right = st.columns([1.2, 1])

# --- ESQUERDA: TABELA E GERAÇÃO CNAB ---
with col_left:
    tab1, tab2 = st.tabs(["Enviar Remessa de Pagamentos", "Títulos Vencidos"])
    
    with tab1:
        if not df_real.empty:
            # Organizando as colunas na ordem da sua foto
            colunas_visuais = ['Pagar?', 'NOME_FAVORECIDO', 'Categoria', 'OC', 'NF', 'Observação', 'DATA_PAGAMENTO', 'VALOR_PAGAMENTO', 'Banco_Origem', 'CHAVE_PIX_OU_COD_BARRAS', 'cnpj_beneficiario']
            
            # Garante que as colunas existem
            for col in colunas_visuais:
                if col not in df_real.columns: df_real[col] = ""
                
            df_display = df_real[colunas_visuais].copy()
            
            # Edição da Tabela
            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                height=500,
                column_config={
                    "Pagar?": st.column_config.CheckboxColumn("Pagar", default=True),
                    "NOME_FAVORECIDO": "Pagamento",
                    "DATA_PAGAMENTO": "Venc. original",
                    "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Banco_Origem": "Banco",
                    "CHAVE_PIX_OU_COD_BARRAS": None, # Oculta na tela mas mantém no DF
                    "cnpj_beneficiario": None
                }
            )
            
            st.write("")
            
            # Geração do CNAB
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

# --- DIREITA: GRÁFICOS E KPIs SECUNDÁRIOS ---
with col_right:
    # Sub-KPIs
    skpi1, skpi2 = st.columns(2)
    skpi1.metric("Total Acordos", "R$ 0,00")
    skpi2.metric("Total Ordem de Compras", "R$ 0,00")
    
    st.write("")
    
    # Gráfico 1: Receitas & Despesas
    st.markdown("<h4 style='text-align: center; color: #4F4F4F;'>Receitas & Despesas</h4>", unsafe_allow_html=True)
    meses = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
    receitas = [3000, 2500, 2800, 3200, 3000, 2900, 3100, 3300, 3500, 2900, 4000, 3100]
    despesas = [1500, 1800, 1600, 2000, 2200, 2100, 1900, 1800, 2300, 1700, 2100, 2200]
    saldo = [r - d for r, d in zip(receitas, despesas)]
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=meses, y=receitas, name='Receitas', marker_color='#1cc88a'))
    fig1.add_trace(go.Bar(x=meses, y=despesas, name='Despesas', marker_color='#e74a3b'))
    fig1.add_trace(go.Scatter(x=meses, y=saldo, name='Saldo', mode='lines+markers', line=dict(color='#5a5c69', width=3)))
    
    fig1.update_layout(barmode='group', margin=dict(l=0, r=0, t=30, b=0), height=300, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
    st.plotly_chart(fig1, use_container_width=True)
    
    # Gráfico 2: Investimentos & Poupança
    st.markdown("<h4 style='text-align: center; color: #4F4F4F;'>Investimentos & Poupança</h4>", unsafe_allow_html=True)
    investimento_mensal = [500] * 12
    acumulado = np.cumsum(investimento_mensal)
    meta = [6000] * 12
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=meses, y=investimento_mensal, name='Investimento Mensal', marker_color='#f6c23e'))
    fig2.add_trace(go.Scatter(x=meses, y=acumulado, name='Acumulado', mode='lines', line=dict(color='#f6c23e', width=3, dash='dash')))
    fig2.add_trace(go.Scatter(x=meses, y=meta, name='Meta Anual', mode='lines', line=dict(color='#5a5c69', width=3)))
    
    fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
    st.plotly_chart(fig2, use_container_width=True)
