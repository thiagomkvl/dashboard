import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import conectar_sheets

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Diário", layout="wide", page_icon="📊")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .kpi-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 4px solid #4e73df;
        height: 100%;
    }
    .kpi-card.green { border-top-color: #1cc88a; }
    .kpi-card.purple { border-top-color: #6f42c1; }
    .kpi-card.cyan { border-top-color: #36b9cc; }
    .kpi-card.red { border-top-color: #e74a3b; }
    .kpi-card.orange { border-top-color: #f6c23e; }
    
    .kpi-title { font-size: 12px; font-weight: bold; color: #5a5c69; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { font-size: 24px; font-weight: bold; color: #3a3b45; }
    .kpi-subtitle { font-size: 11px; color: #858796; margin-top: 5px; }
    
    .section-title { font-size: 16px; font-weight: bold; color: #1a2035; margin-bottom: 15px; text-transform: uppercase; }
    .alert-box { background-color: #ffeeba; border-left: 4px solid #ffc107; padding: 15px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        conn = conectar_sheets()
        
        # 1. Carrega as abas do Google Sheets
        df_bancos = conn.read(worksheet="Saldos_Bancos", ttl=0)
        df_historico = conn.read(worksheet="Historico_Saldos", ttl=0)
        
        # --- PROTEÇÃO CONTRA PLANILHA VAZIA ---
        if df_bancos.empty:
            st.warning("A aba 'Saldos_Bancos' está vazia ou não foi encontrada.")
            return pd.DataFrame(), pd.DataFrame()
            
        # --- FUNÇÃO DE LIMPEZA FINANCEIRA AVANÇADA ---
        def limpar_moeda(serie):
            # 1. Troca o formato contábil negativo (R$ 10,00) para padrão -R$ 10,00
            s = serie.astype(str).str.replace(r'^\s*\((.*?)\)\s*$', r'-\1', regex=True)
            # 2. Limpa os textos e converte padrão BR para Matemática
            s = s.str.replace('R\$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
            return pd.to_numeric(s, errors='coerce').fillna(0.0)

        # --- TRATAMENTO DOS DADOS DOS BANCOS ---
        # Ajuste dinâmico de nome de coluna
        if 'Contas Bancárias' in df_bancos.columns:
            df_bancos.rename(columns={'Contas Bancárias': 'Conta Bancária'}, inplace=True)
            
        colunas_financeiras = ['Saldo Inicial', 'Entrada', 'Saída', 'Conta Garantida']
        for col in colunas_financeiras:
            if col in df_bancos.columns:
                df_bancos[col] = limpar_moeda(df_bancos[col])
            else:
                df_bancos[col] = 0.0

        # Recalcula o saldo final e disponível na hora para não depender de fórmula do Sheets
        df_bancos['Saldo Final'] = df_bancos['Saldo Inicial'] + df_bancos['Entrada'] + df_bancos['Saída']
        df_bancos['Disponível'] = df_bancos['Saldo Final'] + df_bancos['Conta Garantida']
            
        # --- TRATAMENTO DOS DADOS DO HISTÓRICO ---
        if not df_historico.empty:
            # Identifica a coluna correta de Saldo
            col_saldo_hist = 'Saldo Final' if 'Saldo Final' in df_historico.columns else 'Saldo Inicial'
            
            # Limpa a coluna de dinheiro usando a nova função
            df_historico[col_saldo_hist] = limpar_moeda(df_historico[col_saldo_hist])
            
            # AGRUPA POR DATA E SOMA: Para gerar a linha do gráfico
            df_hist_agrupado = df_historico.groupby('Data')[col_saldo_hist].sum().reset_index()
            df_hist_agrupado.rename(columns={col_saldo_hist: 'Saldo'}, inplace=True)
            
            # Converte a data para que o gráfico não embaralhe a ordem cronológica
            df_hist_agrupado['Data_Obj'] = pd.to_datetime(df_hist_agrupado['Data'], format='%d/%m/%Y', errors='coerce')
            df_historico = df_hist_agrupado.sort_values('Data_Obj').drop(columns=['Data_Obj'])
            
        else:
            hoje = datetime.now()
            dias = [(hoje - timedelta(days=i)).strftime('%d/%m') for i in range(6, -1, -1)]
            df_historico = pd.DataFrame({'Data': dias, 'Saldo': [0]*7})

        return df_bancos, df_historico
        
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_bancos, df_historico = carregar_dados()

# Proteção de parada dura se a tabela principal não subir
if df_bancos.empty:
    st.stop()
