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

# --- FUNÇÕES DE TRATAMENTO DE DADOS ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def limpar_ids(valor):
    if pd.isna(valor) or valor == "": return ""
    s = str(valor).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(limpar_ids(texto) if alinhar == 'direita' else str(texto))
    if alinhar == 'esquerda': 
        res = texto[:tamanho].ljust(tamanho, preenchimento)
    else:
        texto_num = "".join(filter(str.isdigit, texto))
        res = texto_num[:tamanho].rjust(tamanho, preenchimento)
    return res[:tamanho] # Garante corte no tamanho exato

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 10px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .stButton button { width: auto; min-width: 140px; font-weight: bold; }
    [data-testid="column"] { width: fit-content !important; flex: unset !important; min-width: unset !important; padding-right: 5px !important; }
    [data-testid="stHorizontalBlock"] { gap: 5px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR CNAB 240 AJUSTADO (FIX 240 CARACTERES) ---
def gerar_cnab240(df_sel, h):
    linhas = []
    hoje = datetime.now()
    
    # Registro 0: Header de Arquivo
    h0 = f"00100000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000"
    linhas.append(h0[:240].ljust(240)) [cite: 17]
    
    # Registro 1: Header de Lote (Pix Lançamento 45 / Layout 046)
    h1 = f"00100011C2045046 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{' '*80}{hoje.strftime('%d%m%Y')}{'0'*8}"
    linhas.append(h1[:240].ljust(240)) [cite: 17, 23, 24]
    
    reg_lote = 0
    for i, r in df_sel.reset_index(drop=True).iterrows():
        v = int(float(str(r['VALOR_PAGAMENTO']).replace(',','.')) * 100)
        chave_pix = limpar_ids(r.get('CHAVE_PIX', ''))
        
        # Iniciação Dinâmica (G100)
        if chave_pix:
            if "@" in chave_pix: forma_ini = "02" # Email [cite: 79]
            elif len(chave_pix) in [11, 14]: forma_ini = "03" # CPF/CNPJ [cite: 81]
            elif chave_pix.startswith("+") or (len(chave_pix) >= 10 and chave_pix.isdigit()): forma_ini = "01" # Tel [cite: 77]
            else: forma_ini = "04" # Aleatória [cite: 82]
        else:
            forma_ini = "05" # Dados Bancários [cite: 83]

        # Segmento A (Câmara 009 - Pix)
        reg_lote += 1
        segA = f"00100013{formatar_campo(reg_lote,5,'0','r')}A00001009{formatar_campo(r['BANCO_FAVORECIDO'],3,'0','r')}{formatar_campo(r['AGENCIA_FAVORECIDA'],5,'0','r')} {formatar_campo(r['CONTA_FAVORECIDA'],12,'0','r')}{formatar_campo(r['DIGITO_CONTA_FAVORECIDA'],1)} {formatar_campo(r['NOME_FAVORECIDO'],30)}{formatar_campo(r.get('Nr. Titulo',''),20)}{pd.to_datetime(r['DATA_PAGAMENTO']).strftime('%d%m%Y')}BRL{'0'*15}{formatar_campo(v,15,'0','r')}{' '*40}00"
        linhas.append(segA[:240].ljust(240)) [cite: 36, 51]
        
        # Segmento B (Iniciação + ISPB)
        reg_lote += 1
        segB = f"00100013{formatar_campo(reg_lote,5,'0','r')}B   {forma_ini}{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}{' '*100}{formatar_campo(chave_pix,35)}{' '*68}00000000"
        linhas.append(segB[:240].ljust(240)) [cite: 67, 72]
        
    # Registro 5: Trailer de Lote
    reg_lote += 1
    v_total = int(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100)
    t5 = f"00100015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total,18,'0','r')}{'0'*100}"
    linhas.append(t5[:240].ljust(240)) [cite: 164]
    
    # Registro 9: Trailer de Arquivo
    t9 = f"00199999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}"
    linhas.append(t9[:240].ljust(240))
    
    return "\n".join(linhas) # Uso de \n simples para evitar caracteres de controle invisíveis

# ==========================================
# 3. LÓGICA DO APP (Dashboard Mantido)
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
            df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
            total_hoje = df_abc['Saldo_Limpo'].sum()
            df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
            df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A (80%)' if x <= 0.8 else ('Classe B (15%)' if x <= 0.95 else 'Classe C (5%)'))
            df_hoje = df_hoje.merge(df_abc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')
            st.title("Gestão de Passivo - SOS CARDIO")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Dívida Total", formatar_real(total_hoje))
            m2.metric("Total Vencido", formatar_real(df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()))
            m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
            m4.metric("Última Atualização", ultima_data)
            st.divider(); c1, c2 = st.columns(2)
            with c1: st.plotly_chart(px.pie(df_hoje, values='Saldo_Limpo', names='Classe ABC', hole=0.4, color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'}), use_container_width=True)
            with c2: st.plotly_chart(px.bar(df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']).reset_index().fillna(0), x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s'), use_container_width=True)

    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")
        if 'df_pagamentos' not in st.session_state:
            df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            if not df_p.empty:
                if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                cols_id = ['BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario', 'CHAVE_PIX']
                for c in cols_id:
                    if c in df_p.columns: df_p[c] = df_p[c].apply(limpar_ids)
                st.session_state['df_pagamentos'] = df_p
            else:
                st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario'])

        col_btns = st.columns([1, 1, 1, 1.5, 3])
        with col_btns[0]:
            with st.popover("➕ Novo"):
                with st.form("form_novo", clear_on_submit=True):
                    fn = st.text_input("Fornecedor"); fv = st.number_input("Valor", format="%.2f"); fd = st.date_input("Vencimento"); fc = st.text_input("CNPJ")
                    fp = st.text_input("PIX"); fb = st.text_input("Banco", "136"); fa = st.text_input("Agência"); fcc = st.text_input("Conta"); fdg = st.text_input("DG")
                    if st.form_submit_button("✅ Adicionar"):
                        nova = pd.DataFrame([{'Pagar?': True, 'NOME_FAVORECIDO': fn, 'VALOR_PAGAMENTO': fv, 'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'), 'CHAVE_PIX': fp, 'BANCO_FAVORECIDO': fb, 'AGENCIA_FAVORECIDA': fa, 'CONTA_FAVORECIDA': fcc, 'DIGITO_CONTA_FAVORECIDA': fdg, 'cnpj_beneficiario': fc}])
                        st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], nova], ignore_index=True); st.rerun()
        with col_btns[1]:
            if st.button("💾 Salvar"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Sincronizado!", icon="✅")
        with col_btns[2]:
            if st.button("🔄 Atualizar"): del st.session_state['df_pagamentos']; st.rerun()
        with col_btns[3]:
            df_rem = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_rem.empty:
                v_total = df_rem['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Remessa ({formatar_real(v_total)})", gerar_cnab240(df_rem, {'cnpj': '00000000000000', 'ag': '0', 'cc': '0'}), f"REM_SOS_{datetime.now().strftime('%d%m')}.txt")
        st.divider(); st.session_state['df_pagamentos'] = st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base"); up = st.file_uploader("Arquivo", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Ok!"); st.rerun()
