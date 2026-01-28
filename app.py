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

def limpar_numero(valor):
    """Remove .0 e outros caracteres, mantendo apenas dígitos."""
    if pd.isna(valor): return "0"
    s = str(valor).split('.')[0] # Remove o .0 se existir
    return "".join(filter(str.isdigit, s))

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(limpar_numero(texto) if alinhar == 'direita' else str(texto))
    if alinhar == 'esquerda': return texto[:tamanho].ljust(tamanho, preenchimento)
    return texto[:tamanho].rjust(tamanho, preenchimento)

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 10px; border-radius: 10px; border-left: 5px solid #004a99; }
    .stButton button { width: auto; min-width: 140px; font-weight: bold; }
    [data-testid="column"] { width: fit-content !important; flex: unset !important; min-width: unset !important; padding-right: 5px !important; }
    [data-testid="stHorizontalBlock"] { gap: 5px !important; }
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
# 3. LÓGICA DO APP
# ==========================================
if check_password():
    conn = conectar_sheets()
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Evolução Temporal", "Upload"])

    # ------------------------------------------
    # ABA: DASHBOARD PRINCIPAL (RESTAURADA)
    # ------------------------------------------
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
            m4.metric("Última Atualização", ultima_data)

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Curva ABC")
                df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
                df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
                df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A' if x <= 0.8 else ('Classe B' if x <= 0.95 else 'Classe C'))
                st.plotly_chart(px.pie(df_abc, values='Saldo_Limpo', names='Classe ABC', hole=0.4, color_discrete_map={'Classe A': '#004a99', 'Classe B': '#ffcc00', 'Classe C': '#d1d5db'}), use_container_width=True)
            with c2:
                st.subheader("Ageing (Vencimentos)")
                ordem = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                df_bar = df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem).reset_index().fillna(0)
                st.plotly_chart(px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s'), use_container_width=True)

            st.divider()
            st.subheader("🎯 Radar de Pagamentos - Próximos Vencimentos")
            df_hoje['Vencimento_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
            df_radar = df_hoje[df_hoje['Vencimento_DT'] >= pd.Timestamp.now().normalize()].sort_values('Vencimento_DT')
            if not df_radar.empty:
                df_radar['Data_F'] = df_radar['Vencimento_DT'].dt.strftime('%d/%m/%Y')
                fig_radar = px.bar(df_radar, x='Data_F', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=500)
                st.plotly_chart(fig_radar, use_container_width=True)

    # ------------------------------------------
    # ABA: PAGAMENTOS UNICRED (LÓGICA BLINDADA)
    # ------------------------------------------
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")

        if 'df_pagamentos' not in st.session_state:
            df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            if not df_p.empty:
                if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                # Remove o .0 das colunas numéricas que devem ser texto
                for col in ['BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA']:
                    if col in df_p.columns:
                        df_p[col] = df_p[col].apply(lambda x: str(x).split('.')[0] if pd.notna(x) else "0")
                st.session_state['df_pagamentos'] = df_p
            else:
                st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario'])

        col_btns = st.columns([1, 1, 1, 1.5, 3])
        
        with col_btns[0]:
            with st.popover("➕ Novo Título"):
                with st.form("form_novo", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        f_nome = st.text_input("Fornecedor")
                        f_val = st.number_input("Valor", min_value=0.0, format="%.2f")
                        f_venc = st.date_input("Vencimento")
                        f_cnpj = st.text_input("CNPJ Beneficiário")
                    with c2:
                        f_pix = st.text_input("Chave PIX")
                        f_banco = st.text_input("Banco", value="136")
                        f_ag = st.text_input("Agência", value="0000")
                        f_cc = st.text_input("Conta", value="00000")
                        f_dg = st.text_input("Dígito", value="0")

                    if st.form_submit_button("✅ Adicionar"):
                        nova_linha = pd.DataFrame([{
                            'Pagar?': True, 'NOME_FAVORECIDO': f_nome, 'VALOR_PAGAMENTO': f_val, 
                            'DATA_PAGAMENTO': f_venc.strftime('%d/%m/%Y'), 'CHAVE_PIX': f_pix, 
                            'BANCO_FAVORECIDO': f_banco, 'AGENCIA_FAVORECIDA': f_ag, 
                            'CONTA_FAVORECIDA': f_cc, 'DIGITO_CONTA_FAVORECIDA': f_dg, 'cnpj_beneficiario': f_cnpj
                        }])
                        st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], nova_linha], ignore_index=True)
                        st.rerun()

        with col_btns[1]:
            if st.button("💾 Salvar"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Google Sheets atualizado!", icon="✅")

        with col_btns[2]:
            if st.button("🔄 Atualizar"):
                del st.session_state['df_pagamentos']
                st.rerun()

        with col_btns[3]:
            df_f = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_f.empty:
                v_total = df_f['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Remessa ({formatar_real(v_total)})", gerar_cnab240(df_f, {'cnpj': '00000000000000', 'convenio': '0', 'ag': '0', 'cc': '0'}), f"REM_{datetime.now().strftime('%d%m')}.txt")

        st.divider()
        st.session_state['df_pagamentos'] = st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Arquivo", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Ok!"); st.rerun()

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False
        st.rerun()
