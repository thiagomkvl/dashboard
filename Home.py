import streamlit as st

# Configuração da Página Inicial
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
                st.rerun()  # Recarrega para atualizar o estado
            else:
                st.error("❌ Senha incorreta.")
    return False

# --- FLUXO PRINCIPAL ---
if not check_password():
    st.stop()  # Para a execução aqui se não estiver logado

# Se passou pelo check_password, mostra a tela de boas-vindas
st.toast("Login efetuado com sucesso!", icon="✅")
st.title("Bem-vindo ao Sistema SOS Cardio")

st.info("""
**👈 Utilize o menu na barra lateral esquerda para navegar:**

* **📊 Dashboard:** Visão gerencial, Fluxo de Caixa e Curva ABC.
* **💸 Cockpit:** Gestão de pagamentos diários (Pix e Boletos).
* **📂 Upload:** Atualização da base de dados histórica.
""")

if st.button("🔒 Sair do Sistema"):
    st.session_state["password_correct"] = False
    st.rerun()
