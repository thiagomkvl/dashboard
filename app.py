import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 1. CONFIGURAÇÃO, CSS E SEGURANÇA
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

def check_password():
    def password_entered():
        if "password" in st.session_state:
            if st.session_state["password"] == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False
    if st.session_state.get("password_correct"):
        return True
    st.markdown("<h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Senha de Acesso:", type="password", on_change=password_entered, key="password")
    return False

# --- FUNÇÕES DE SUPORTE ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(str(texto))
    if alinhar == 'esquerda': return texto[:tamanho].ljust(tamanho, preenchimento)
    texto_num = "".join(filter(str.isdigit, str(texto)))
    return texto_num[:tamanho].rjust(tamanho, preenchimento)

# CSS PARA BOTÕES ULTRA-COMPACTOS E ALINHADOS
st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 10px; border-radius: 10px; border-left: 5px solid #004a99; }
    .stButton button { width: auto; min-width: 140px; font-weight: bold; padding: 0.5rem 1rem; }
    /* Estilo para colar os botões */
    [data-testid="column"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: unset !important;
        padding-right: 5px !important;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 5px !important;
        align-items: flex-start;
    }
    div[data-testid="stPopover"] > button {
        min-width: 160px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR CNAB 240 ---
def gerar_cnab240(df_sel, h):
    l = []
    hoje = datetime.now()
    l.append((f"00100000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000").ljust(240))
    l.append((f"00100011C2001046 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{' '*80}{hoje.strftime('%d%m%Y')}{'0'*8}").ljust(240))
    for i, r in df_sel.reset_index(drop=True).iterrows():
        v = int(float(str(r['VALOR_PAGAMENTO']).replace(',','.')) * 100)
        l.append((f"00100013{formatar_campo(i*2+1,5,'0','r')}A00001000{formatar_campo(r.get('BANCO_FAVORECIDO','001'),3,'0','r')}{formatar_campo(r.get('AGENCIA_FAVORECIDA','0'),5,'0','r')} {formatar_campo(r.get('CONTA_FAVORECIDA','0'),12,'0','r')}{formatar_campo(r.get('DIGITO_CONTA_FAVORECIDA','0'),1)} {formatar_campo(r['NOME_FAVORECIDO'],30)}{formatar_campo(r.get('Nr. Titulo',''),20)}{pd.to_datetime(r['DATA_PAGAMENTO']).strftime('%d%m%Y')}BRL{'0'*15}{formatar_campo(v,15,'0','r')}{' '*40}00").ljust(240))
        l.append((f"00100013{formatar_campo(i*2+2,5,'0','r')}B   2{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}{' '*100}{formatar_campo(r.get('CHAVE_PIX',''),35)}").ljust(240))
    l.append((f"00100015{' '*9}{formatar_campo(len(l)+1,6,'0','r')}{'0'*100}").ljust(240))
    l.append((f"00199999{' '*9}000001{formatar_campo(len(l)+1,6,'0','r')}").ljust(240))
    return "\r\n".join(l)

# ==========================================
# 3. LÓGICA DO APP
# ==========================================
if check_password():
    conn = conectar_sheets()
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Evolução Temporal", "Upload"])

    if aba == "Dashboard Principal":
        st.title("Gestão de Passivo - SOS CARDIO")
        # [Código do Dashboard Principal aqui...]

    # ------------------------------------------
    # ABA: PAGAMENTOS UNICRED (REVISADA)
    # ------------------------------------------
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")

        # 1. Carregamento e Tratamento Booleano
        if 'df_pagamentos' not in st.session_state:
            df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            if not df_p.empty:
                if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                st.session_state['df_pagamentos'] = df_p
            else:
                st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario'])

        # 2. BOTÕES COMPACTOS LADO A LADO
        col_btns = st.columns([1, 1, 1, 1, 3])
        
        with col_btns[0]:
            # JANELA DE NOVO TÍTULO COM TODOS OS CAMPOS
            with st.popover("➕ Novo Título"):
                st.markdown("### Cadastro Manual de Título")
                with st.form("form_novo_pagamento", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        f_nome = st.text_input("Nome Favorecido")
                        f_val = st.number_input("Valor do Título", min_value=0.0, format="%.2f")
                        f_venc = st.date_input("Data de Vencimento")
                        f_cnpj = st.text_input("CNPJ Beneficiário")
                    with c2:
                        f_pix = st.text_input("Chave PIX")
                        f_banco = st.text_input("Banco (ex: 001)", value="136") # Unicred padrão
                        f_ag = st.text_input("Agência", value="0000")
                        f_cc = st.text_input("Conta", value="00000")
                        f_dg = st.text_input("Dígito", value="0")

                    if st.form_submit_button("✅ Adicionar à Lista"):
                        nova_linha = pd.DataFrame([{
                            'Pagar?': True, 
                            'NOME_FAVORECIDO': f_nome, 
                            'VALOR_PAGAMENTO': f_val, 
                            'DATA_PAGAMENTO': f_venc.strftime('%d/%m/%Y'), 
                            'CHAVE_PIX': f_pix, 
                            'BANCO_FAVORECIDO': f_banco, 
                            'AGENCIA_FAVORECIDA': f_ag, 
                            'CONTA_FAVORECIDA': f_cc, 
                            'DIGITO_CONTA_FAVORECIDA': f_dg, 
                            'cnpj_beneficiario': f_cnpj
                        }])
                        st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], nova_linha], ignore_index=True)
                        st.rerun()

        with col_btns[1]:
            if st.button("💾 Salvar Planilha"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Sincronizado com Google Sheets!", icon="✅")

        with col_btns[2]:
            if st.button("🔄 Atualizar"):
                del st.session_state['df_pagamentos']
                st.rerun()

        with col_btns[3]:
            # Lógica de Remessa com total dinâmico
            df_final = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_final.empty:
                v_total = df_final['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Remessa ({formatar_real(v_total)})", 
                                 gerar_cnab240(df_final, {'cnpj': '00000000000000', 'convenio': '0', 'ag': '0', 'cc': '0'}),
                                 f"REM_{datetime.now().strftime('%d%m')}.txt")

        st.divider()

        # 3. Editor de Dados
        st.session_state['df_pagamentos'] = st.data_editor(
            st.session_state['df_pagamentos'],
            column_config={
                "Pagar?": st.column_config.CheckboxColumn("Pagar?"),
                "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor R$", format="%.2f")
            },
            hide_index=True, 
            use_container_width=True
        )

    elif aba == "Upload":
        st.title("Upload da Base")
        # [Código de Upload...]

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False
        st.rerun()
