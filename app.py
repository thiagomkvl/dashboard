import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 1. CONFIGURAÇÃO, CSS E SEGURANÇA (LOGIN)
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

def check_password():
    """Retorna True se o usuário digitou a senha correta ou já está logado."""
    def password_entered():
        # Proteção contra KeyError: verifica se a chave existe antes de comparar
        if "password" in st.session_state:
            if st.session_state["password"] == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False

    # Se já estiver logado, retorna True
    if st.session_state.get("password_correct"):
        return True

    # Tela de Login centralizada
    st.markdown("<h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Acesso Restrito - Gestão Financeira</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        # Usamos o 'on_change' para processar assim que der Enter
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
        if st.session_state.get("password_correct") == False:
            st.error("😕 Senha incorreta.")
    return False

# --- FUNÇÕES DE FORMATAÇÃO ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(str(texto))
    if alinhar == 'esquerda':
        return texto[:tamanho].ljust(tamanho, preenchimento)
    # Limpa números para campos de valor/conta
    texto_num = "".join(filter(str.isdigit, str(texto)))
    return texto_num[:tamanho].rjust(tamanho, preenchimento)

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 5px; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE GERAÇÃO CNAB 240 (UNICRED)
# ==========================================
def gerar_cnab240(df_selecionado, h):
    linhas = []
    hoje = datetime.now()
    
    # Registro 0: Header de Arquivo
    header_arq = (
        "00100000" + " " * 9 + "2" + 
        formatar_campo(h['cnpj'], 14, '0', 'direita') +
        formatar_campo(h.get('convenio', '0'), 20, '0', 'direita') +
        formatar_campo(h['agencia'], 5, '0', 'direita') + " " +
        formatar_campo(h['conta'], 12, '0', 'direita') + "  " +
        formatar_campo("SOS CARDIO SERVICOS HOSP", 30) +
        formatar_campo("UNICRED", 30) + " " * 10 + "1" +
        hoje.strftime("%d%m%Y") + hoje.strftime("%H%M%S") +
        "000001" + "103" + "00000"
    )
    linhas.append(header_arq.ljust(240))

    # Registro 1: Header de Lote
    header_lote = (
        "00100011C2001046 " + "2" +
        formatar_campo(h['cnpj'], 14, '0', 'direita') +
        formatar_campo(h.get('convenio', '0'), 20, '0', 'direita') +
        formatar_campo(h['agencia'], 5, '0', 'direita') + " " +
        formatar_campo(h['conta'], 12, '0', 'direita') + "  " +
        formatar_campo("SOS CARDIO SERVICOS HOSP", 30) + " " * 80 +
        hoje.strftime("%d%m%Y") + "0" * 8
    )
    linhas.append(header_lote.ljust(240))

    for i, row in df_selecionado.reset_index(drop=True).iterrows():
        n_seq = i + 1
        # Usando o nome da coluna vindo da sua aba processada no Sheets
        valor_pag = int(float(row['VALOR_PAGAMENTO']) * 100)
        
        # Segmento A
        seg_a = (
            "00100013" + formatar_campo(n_seq * 2 - 1, 5, '0', 'direita') + "A" +
            "00001000" + formatar_campo(row.get('BANCO_FAVORECIDO', '001'), 3, '0', 'direita') +
            formatar_campo(row.get('AGENCIA_FAVORECIDA', '0'), 5, '0', 'direita') + " " +
            formatar_campo(row.get('CONTA_FAVORECIDA', '0'), 12, '0', 'direita') + 
            formatar_campo(row.get('DIGITO_CONTA_FAVORECIDA', '0'), 1) + " " +
            formatar_campo(row['NOME_FAVORECIDO'], 30) +
            formatar_campo(row.get('Nr. Titulo', ''), 20) + 
            pd.to_datetime(row['DATA_PAGAMENTO']).strftime("%d%m%Y") + "BRL" +
            "0" * 15 + formatar_campo(valor_pag, 15, '0', 'direita') + " " * 40 + "00"
        )
        linhas.append(seg_a.ljust(240))
        
        # Segmento B
        seg_b = (
            "00100013" + formatar_campo(n_seq * 2, 5, '0', 'direita') + "B" +
            " " * 3 + "2" + formatar_campo(row.get('cnpj_beneficiario', '0'), 14, '0', 'direita') + 
            " " * 100 + formatar_campo(row.get('CHAVE_PIX', ''), 35)
        )
        linhas.append(seg_b.ljust(240))

    # Trailers
    linhas.append(("00100015" + " " * 9 + formatar_campo(len(linhas) + 1, 6, '0', 'direita') + "0" * 100).ljust(240))
    linhas.append(("00199999" + " " * 9 + "000001" + formatar_campo(len(linhas) + 1, 6, '0', 'direita')).ljust(240))

    return "\r\n".join(linhas)

# ==========================================
# 3. LÓGICA DO APP (NAVEGAÇÃO)
# ==========================================
if check_password():
    @st.cache_data(ttl=60)
    def carregar_dados_historico():
        try:
            conn = conectar_sheets()
            df = conn.read(worksheet="Historico", ttl=60)
            if not df.empty:
                df['Beneficiario'] = df['Beneficiario'].astype(str).str.strip()
                df['Saldo_Limpo'] = pd.to_numeric(df['Saldo Atual'], errors='coerce').fillna(0)
            return df
        except: return pd.DataFrame()

    df_hist = carregar_dados_historico()

    st.sidebar.title("Módulos SOS CARDIO")
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Upload"])

    if aba == "Pagamentos Unicred":
        st.title("🔌 Gerador CNAB 240 - Unicred")
        
        st.sidebar.subheader("Dados Bancários Hospital")
        h_dados = {
            'cnpj': st.sidebar.text_input("CNPJ SOS Cardio:", "00000000000000"),
            'convenio': st.sidebar.text_input("Código Convênio (Opcional):", "0"),
            'agencia': st.sidebar.text_input("Agência:", "0000"),
            'conta': st.sidebar.text_input("Conta Corrente:", "00000")
        }

        try:
            conn = conectar_sheets()
            df_dia = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            
            if not df_dia.empty:
                st.write(f"📋 **{len(df_dia)}** títulos encontrados para processamento hoje.")
                if 'Pagar?' not in df_dia.columns:
                    df_dia.insert(0, 'Pagar?', True)
                
                edited_df = st.data_editor(df_dia, hide_index=True, use_container_width=True)
                df_para_pagar = edited_df[edited_df['Pagar?'] == True].copy()
                
                if not df_para_pagar.empty:
                    st.metric("Total da Remessa", formatar_real(df_para_pagar['VALOR_PAGAMENTO'].sum()))
                    if st.button("🚀 Gerar Arquivo de Remessa"):
                        txt_cnab = gerar_cnab240(df_para_pagar, h_dados)
                        st.download_button(
                            label="📥 Baixar Arquivo .REM",
                            data=txt_cnab,
                            file_name=f"REM_UNICRED_{datetime.now().strftime('%d%m%Y')}.txt",
                            mime="text/plain"
                        )
                        st.success("Arquivo pronto! Valide no portal da Unicred.")
            else:
                st.warning("Aba 'Pagamentos_Dia' está vazia ou sem títulos para hoje.")
        except Exception as e:
            st.error(f"Erro ao conectar ao Google Sheets: {e}")

    elif aba == "Dashboard Principal":
        if not df_hist.empty:
            # [Seu código de visualização do Dashboard Principal...]
            st.title("Gestão de Passivo - SOS CARDIO")
            st.info("Utilize as abas laterais para navegar pelos módulos.")
            
    elif aba == "Upload":
        st.title("Upload da Base de Histórico")
        uploaded = st.file_uploader("Selecione o arquivo Excel do Tasy", type=["xlsx"])
        if uploaded and st.button("Salvar e Atualizar"):
            df_new = pd.read_excel(uploaded)
            if salvar_no_historico(df_new):
                st.success("Dados salvos!")
                st.rerun()

    # Logout na barra lateral
    if st.sidebar.button("🔒 Sair / Bloquear App"):
        st.session_state["password_correct"] = False
        st.rerun()
