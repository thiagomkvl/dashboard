import streamlit as st
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Portal Financeiro Executivo",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 0. LÓGICA DE AUTENTICAÇÃO E CONTROLE DE SESSÃO
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Tela de Login (Caso o usuário não esteja autenticado)
if not st.session_state.autenticado:
    # Custom CSS para a tela de login ficar limpa (esconde barra lateral e cabeçalho)
    css_login = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .stApp { background-color: #f4f6f9; }
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }
    
    .login-title { font-size: 24px; font-weight: 800; color: #1e40af; margin-bottom: 5px; text-align: center; }
    .login-subtitle { font-size: 13px; color: #64748b; margin-bottom: 20px; font-weight: 500; text-align: center; }
    </style>
    """
    st.markdown(textwrap.dedent(css_login), unsafe_allow_html=True)

    # Caixa centralizada do formulário
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<div class='login-title'>🏢 Portal Executivo</div>", unsafe_allow_html=True)
            st.markdown("<div class='login-subtitle'>S.O.S. Cardio - Insira sua senha para acessar.</div>", unsafe_allow_html=True)
            
            with st.form("form_login_portal"):
                senha_digitada = st.text_input("Senha de Acesso", type="password", placeholder="Digite a senha...")
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                botao_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                
                if botao_entrar:
                    # 🔐 Senha corporativa do sistema
                    SENHA_MESTRE = "S@SCARDIO2k26"
                    
                    if senha_digitada == SENHA_MESTRE:
                        st.session_state.autenticado = True
                        st.rerun() # Recarrega a página para liberar a navegação
                    else:
                        st.error("Senha incorreta. Tente novamente.")
                        
    # O st.stop() é crucial! Ele impede que o painel e o menu carreguem se não logar
    st.stop() 


# ==============================================================================
# 1. NAVEGAÇÃO NATIVA (SÓ EXECUTA SE PASSAR PELA SENHA)
# ==============================================================================

# Adiciona o botão de Logout no topo do menu lateral
with st.sidebar:
    st.markdown("### 👤 Minha Sessão")
    if st.button("🔒 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.markdown("---")

# Registra os painéis
pg_saldos = st.Page("pages/Dashboard_Saldo.py", title="Dashboard de Saldos", icon="📊")
pg_fluxo = st.Page("pages/painel_fluxo_caixa.py", title="Fluxo de Caixa Analítico", icon="💰")
pg_pagar = st.Page("pages/painel_pagar.py", title="Painel de Pagamentos", icon="📄")

# Cria o menu lateral automaticamente
nav = st.navigation(
    {"Módulos Financeiros": [pg_saldos, pg_fluxo, pg_pagar]},
    position="sidebar"
)

# Executa o roteador da página correspondente
nav.run()
