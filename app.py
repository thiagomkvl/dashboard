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

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 10px; border-radius: 10px; border-left: 5px solid #004a99; }
    .stButton button { width: 100%; font-weight: bold; }
    div[data-testid="column"] { padding: 0 5px !important; }
    [data-testid="stExpander"] { border: 1px solid #e6e9ef; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR CNAB 240 (UNICRED) ---
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
# 3. LÓGICA DE NAVEGAÇÃO
# ==========================================
if check_password():
    conn = conectar_sheets()
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Evolução Temporal", "Upload"])

    if aba == "Dashboard Principal":
        df_hist = conn.read(worksheet="Historico", ttl=300)
        if not df_hist.empty:
            df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
            ultima_data = df_hist['data_processamento'].max()
            df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()
            
            st.title("Gestão de Passivo - SOS CARDIO")
            m1, m2, m3, m4 = st.columns(4)
            total_hoje = df_hoje['Saldo_Limpo'].sum()
            total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
            m1.metric("Dívida Total", formatar_real(total_hoje))
            m2.metric("Total Vencido", formatar_real(total_vencido))
            m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
            m4.metric("Qtd Classe A", "Processando...")

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Curva ABC")
                df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
                df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
                df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A' if x <= 0.8 else ('Classe B' if x <= 0.95 else 'Classe C'))
                st.plotly_chart(px.pie(df_abc, values='Saldo_Limpo', names='Classe ABC', hole=0.4), use_container_width=True)
            with c2:
                st.subheader("Ageing (Vencimentos)")
                ordem = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                df_bar = df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem).reset_index().fillna(0)
                st.plotly_chart(px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99']), use_container_width=True)

    # ------------------------------------------
    # ABA: PAGAMENTOS UNICRED (REVISADA)
    # ------------------------------------------
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")

        # 1. Carregamento e Tratamento Booleano (Resolve o KeyError/APIException)
        if 'df_pagamentos' not in st.session_state:
            df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            if not df_p.empty:
                if 'Pagar?' not in df_p.columns: 
                    df_p.insert(0, 'Pagar?', True)
                # Forçamos a conversão para bool para o st.data_editor aceitar
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                st.session_state['df_pagamentos'] = df_p
            else:
                st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario'])

        # 2. Botões Harmonizados e Popover para Novo Registro
        c_btn1, c_btn2, c_btn3, c_btn4 = st.columns([1, 1, 1, 2])
        
        with c_btn1:
            with st.popover("➕ Novo Título"):
                with st.form("form_novo", clear_on_submit=True):
                    st.write("### Detalhes do Pagamento")
                    fn = st.text_input("Fornecedor")
                    fv = st.number_input("Valor", min_value=0.0, format="%.2f")
                    fd = st.date_input("Vencimento", datetime.now())
                    fc = st.text_input("CNPJ Favorecido")
                    fp = st.text_input("Chave PIX")
                    if st.form_submit_button("Adicionar à Lista"):
                        nova_row = pd.DataFrame([{
                            'Pagar?': True, 'NOME_FAVORECIDO': fn, 'VALOR_PAGAMENTO': fv,
                            'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'), 'CHAVE_PIX': fp,
                            'BANCO_FAVORECIDO': '001', 'AGENCIA_FAVORECIDA': '0',
                            'CONTA_FAVORECIDA': '0', 'DIGITO_CONTA_FAVORECIDA': '0', 'cnpj_beneficiario': fc
                        }])
                        st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], nova_row], ignore_index=True)
                        st.rerun()

        with c_btn2:
            if st.button("💾 Salvar Planilha"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Google Sheets atualizado!", icon="✅")

        with c_btn3:
            if st.button("🔄 Atualizar"):
                del st.session_state['df_pagamentos']
                st.rerun()

        with c_btn4:
            df_final = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_final.empty:
                v_total = df_final['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Baixar Remessa ({formatar_real(v_total)})", 
                                 gerar_cnab240(df_final, {'cnpj': '00000000000000', 'convenio': '0', 'ag': '0', 'cc': '0'}),
                                 f"REM_{datetime.now().strftime('%d%m')}.txt")

        st.divider()

        # 3. Editor de Dados Blindado
        st.session_state['df_pagamentos'] = st.data_editor(
            st.session_state['df_pagamentos'],
            column_config={
                "Pagar?": st.column_config.CheckboxColumn("Pagar?", help="Marque para incluir no arquivo"),
                "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor R$", format="%.2f")
            },
            hide_index=True, 
            use_container_width=True
        )

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Arquivo", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Ok!"); st.rerun()

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False
        st.rerun()
