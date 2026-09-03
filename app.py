import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Portal Financeiro Executivo",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# NAVEGAÇÃO NATIVA EXPLICITA (FORÇA O MENU LATERAL A APARECER)
# ==============================================================================
pg_saldos = st.Page("pages/Dashboard_Saldo.py", title="Dashboard de Saldos", icon="📊")
pg_fluxo = st.Page("pages/painel_fluxo_caixa.py", title="Fluxo de Caixa Analítico", icon="💰")
pg_pagar = st.Page("pages/painel_pagar.py", title="Painel de Pagamentos", icon="📄")

# 'position="sidebar"' força o Streamlit a desenhar o menu lateral com os links
nav = st.navigation(
    {
        "Módulos Financeiros": [pg_saldos, pg_fluxo, pg_pagar]
    },
    position="sidebar"
)

# Executa a página selecionada no menu
nav.run()
