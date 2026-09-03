import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Portal Financeiro Executivo",
    layout="centered",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# --- TELA PRINCIPAL DO HUB ---
st.title("🏢 Portal Financeiro Executivo")
st.markdown("---")

st.write("### Bem-vindo ao sistema de controle financeiro.")
st.write("Para acessar os relatórios e painéis analíticos, utilize o **menu lateral esquerdo**.")

st.info("""
👉 **Como navegar:**
1. Olhe no canto superior esquerdo da tela (se o menu estiver recolhido, clique na seta `>`).
2. Escolha entre **Dashboard de Saldos**, **Fluxo de Caixa Analítico** ou **Painel de Pagamentos**.
""")
