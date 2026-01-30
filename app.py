import streamlit as st
import os

# 1. Configuração da Página
st.set_page_config(page_title="SOS CARDIO - Login", layout="centered", page_icon="🏥")

# 2. Diagnóstico de Arquivos (Vai mostrar na tela o que o Python está enxergando)
# Se isso der erro, é porque a pasta não está onde pensamos.
try:
    arquivos_pages = os.listdir('pages')
except FileNotFoundError:
    arquivos_pages = "PASTA 'pages' NÃO ENCONTRADA!"

# --- LÓGICA DE LOGIN ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.markdown("<br><h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Acesso ao Sistema</h3>", unsafe_allow_html=True)
    
    # Exibe diagnóstico apenas se não estiver logado (para você conferir)
    with st.expander("🔍 Diagnóstico de Estrutura (Debug)", expanded=False):
        st.write(f"Pasta atual: `{os.getcwd()}`")
        st.write(f"Arquivos na pasta 'pages': {arquivos_pages}")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Senha:", type="password", key="pwd_input")
        if st.button("Entrar", use_container_width=True):
            if pwd == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta.")
    return False

# --- FLUXO PRINCIPAL ---
if not check_password():
    st.stop()

# =========================================================
# SE CHEGOU AQUI, O LOGIN FUNCIONOU!
# =========================================================

st.toast("Login realizado com sucesso!", icon="✅")

# Em vez de forçar o redirecionamento (que estava dando erro),
# vamos mostrar o menu e orientar o usuário.
st.success("✅ **Acesso Liberado!**")

st.info("""
**O menu de navegação já está disponível na barra lateral esquerda (👈).**

Selecione um módulo para começar:
* **01 Dashboard:** Indicadores e Gráficos.
* **02 Cockpit:** Emissão de Boletos e Pix.
* **03 Upload:** Carga de dados.
""")

# Botão de Logout
if st.button("Sair"):
    st.session_state["password_correct"] = False
    st.rerun()
