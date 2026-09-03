import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Financeiro Executivo", layout="centered", page_icon="🏢")

# --- CABEÇALHO ---
st.title("🏢 Portal Financeiro Executivo")

st.info("👈 **Por favor, use o menu lateral esquerdo para acessar os painéis.**")
st.write("Se o menu não estiver visível, clique na pequena seta (>) no canto superior esquerdo da tela.")

st.warning("""
**Diagnóstico:**
Se você clicar no nome do painel no menu lateral e a tela continuar sem fazer nada, o problema NÃO é a navegação. Significa que há um erro de código dentro do arquivo (ex: `Dashboard_Saldo.py`) que está travando o carregamento dele na nuvem.
""")
