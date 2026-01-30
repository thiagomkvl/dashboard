import streamlit as st

# Configuração da Página Inicial (Tela de Login)
st.set_page_config(page_title="SOS CARDIO - Login", layout="centered", page_icon="🏥")

# --- LÓGICA DE LOGIN ---
def check_password():
    """Retorna True se o usuário já estiver logado."""
    if st.session_state.get("password_correct", False):
        return True

    # Layout do Login
    st.markdown("<br><br><h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Sistema Integrado de Gestão Financeira</h3>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Digite sua senha de acesso:", type="password", key="pwd_input")
        if st.button("Entrar", use_container_width=True):
            if pwd == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()  # Recarrega a página para validar o estado
            else:
                st.error("❌ Senha incorreta.")
    return False

# --- FLUXO PRINCIPAL ---

if not check_password():
    st.stop()  # Se não estiver logado, para o código aqui e mostra só o login

# =========================================================
# 🚀 REDIRECIONAMENTO AUTOMÁTICO
# Se o código chegou aqui, significa que a senha está correta.
# Vamos enviar o usuário direto para o Dashboard.
# =========================================================
try:
    st.switch_page("pages/1_📊_Dashboard.py")
except Exception as e:
    # Caso o arquivo não seja encontrado (ex: nome diferente), mostra o menu padrão
    st.warning("Login realizado! Selecione uma página no menu lateral.")
    st.error(f"Erro ao redirecionar: {e}")
