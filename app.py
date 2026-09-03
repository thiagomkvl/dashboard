import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Financeiro Executivo", layout="centered", page_icon="🏢")

# --- CABEÇALHO ---
st.title("🏢 Portal Financeiro Executivo")
st.write("Selecione um módulo abaixo para acessar os painéis de controle e análise.")
st.divider() # Linha divisória

# --- MÓDULO 1: SALDOS ---
st.subheader("Dashboard de Saldos")
st.write("Visão consolidada de todas as contas bancárias, aplicações e limites de crédito em tempo real.")
st.page_link("pages/Dashboard_Saldo.py", label="Acessar Dashboard de Saldos", icon="📊")

st.write("---")

# --- MÓDULO 2: FLUXO DE CAIXA ---
st.subheader("Fluxo de Caixa Analítico")
st.write("Mapeamento da origem e destino do dinheiro, geração líquida e taxa de consumo sob a ótica de caixa.")
st.page_link("pages/painel_fluxo_caixa.py", label="Acessar Fluxo de Caixa", icon="💰")

st.write("---")

# --- MÓDULO 3: PAGAMENTOS ---
st.subheader("Painel de Pagamentos")
st.write("Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e controle de saídas.")
st.page_link("pages/painel_pagar.py", label="Acessar Painel de Pagamentos", icon="📄")
