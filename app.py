import streamlit as st

# Configuração Geral da Janela (Ícone e Título do Navegador)
st.set_page_config(page_title="SOS CARDIO", layout="wide", page_icon="🏥")

# --- 1. SISTEMA DE LOGIN ---
def check_password():
    """Retorna True se o usuário estiver logado, caso contrário mostra tela de login."""
    if st.session_state.get("password_correct", False):
        return True

    # Layout da Tela de Login (Centralizado)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Acesso ao Sistema</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        pwd = st.text_input("Digite sua senha:", type="password")
        
        if st.button("Acessar Sistema", use_container_width=True):
            if pwd == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta.")
    return False

# --- 2. ROTEAMENTO (Mapeando sua pasta 'pages') ---
if not check_password():
    st.stop() # Para o código aqui se não estiver logado

# Definição das Páginas (Apontando para seus arquivos)
pg = st.navigation([
    # O seu dashboard original (mantido como página inicial padrão)
    st.Page("pages/dashboard.py", title="Dashboard Gerencial", icon="📊", default=True),
    
    # O novo painel de Fluxo de Caixa que acabamos de criar
    st.Page("pages/Fluxo_de_Caixa.py", title="Fluxo de Caixa (FCx)", icon="📈"), 
    
    st.Page("pages/cockpit.py",   title="Cockpit de Pagamentos", icon="💸"),
    st.Page("pages/hub_bancos.py", title="Hub Multi Bancos", icon="🏦"), 
    st.Page("pages/upload.py",    title="Upload de Base", icon="📂"),
])

# --- 3. BARRA LATERAL (Logout) ---
with st.sidebar:
    st.title("Navegação")
    # O menu de páginas aparece aqui automaticamente pelo pg.run()
    st.divider()
    st.caption(f"Usuário Logado\nSOS Cardio")
    if st.button("🔒 Sair", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# --- 4. EXECUTA A PÁGINA SELECIONADA ---
pg.run()
