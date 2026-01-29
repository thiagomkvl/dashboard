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
    """Remove .0 e espaços de campos de identificação."""
    if pd.isna(valor) or valor == "": return ""
    s = str(valor).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(limpar_ids(texto) if alinhar == 'direita' else str(texto))
    if alinhar == 'esquerda': return texto[:tamanho].ljust(tamanho, preenchimento)
    texto_num = "".join(filter(str.isdigit, texto))
    return texto_num[:tamanho].rjust(tamanho, preenchimento)

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 10px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .stButton button { width: auto; min-width: 140px; font-weight: bold; }
    [data-testid="column"] { width: fit-content !important; flex: unset !important; min-width: unset !important; padding-right: 5px !important; }
    [data-testid="stHorizontalBlock"] { gap: 5px !important; }
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
        l.append((f"00100013{formatar_campo(i*2+1,5,'0','r')}A00001000{formatar_campo(r['BANCO_FAVORECIDO'],3,'0','r')}{formatar_campo(r['AGENCIA_FAVORECIDA'],5,'0','r')} {formatar_campo(r['CONTA_FAVORECIDA'],12,'0','r')}{formatar_campo(r['DIGITO_CONTA_FAVORECIDA'],1)} {formatar_campo(r['NOME_FAVORECIDO'],30)}{formatar_campo(r.get('Nr. Titulo',''),20)}{pd.to_datetime(r['DATA_PAGAMENTO']).strftime('%d%m%Y')}BRL{'0'*15}{formatar_campo(v,15,'0','r')}{' '*40}00").ljust(240))
        l.append((f"00100013{formatar_campo(i*2+2,5,'0','r')}B   2{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}{' '*100}{formatar_campo(r['CHAVE_PIX'],35)}").ljust(240))
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
        df_hist = conn.read(worksheet="Historico", ttl=300)
        if not df_hist.empty:
            df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
            ultima_data = df_hist['data_processamento'].max()
            df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()
            
            # Cálculo Curva ABC
            df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
            total_hoje = df_abc['Saldo_Limpo'].sum()
            df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
            df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A (80%)' if x <= 0.8 else ('Classe B (15%)' if x <= 0.95 else 'Classe C (5%)'))
            df_hoje = df_hoje.merge(df_abc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

            st.title("Gestão de Passivo - SOS CARDIO")
            m1, m2, m3, m4 = st.columns(4)
            total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
            m1.metric("Dívida Total", formatar_real(total_hoje))
            m2.metric("Total Vencido", formatar_real(total_vencido))
            m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
            m4.metric("Última Atualização", ultima_data)

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Curva ABC")
                fig_p = px.pie(df_hoje, values='Saldo_Limpo', names='Classe ABC', hole=0.4, 
                             color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
                st.plotly_chart(fig_p, use_container_width=True)
            with c2:
                st.subheader("Ageing (Vencimentos)")
                ordem = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                df_bar = df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem).reset_index().fillna(0)
                st.plotly_chart(px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s'), use_container_width=True)

            st.divider()
            st.subheader("🎯 Radar de Pagamentos - Detalhamento Diário")
            df_hoje['Vencimento_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
            df_futuro = df_hoje[df_hoje['Vencimento_DT'] >= pd.Timestamp.now().normalize()].copy()
            
            if not df_futuro.empty:
                df_futuro['Mes_Ref'] = df_futuro['Vencimento_DT'].dt.strftime('%m/%Y')
                meses_disp = sorted(df_futuro['Mes_Ref'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
                mes_sel = st.selectbox("Selecione o Mês para Visualizar:", meses_disp)
                
                df_mes = df_futuro[df_futuro['Mes_Ref'] == mes_sel].copy()
                df_mes['Data_F'] = df_mes['Vencimento_DT'].dt.strftime('%d/%m/%Y')
                df_mes = df_mes.sort_values('Vencimento_DT')

                fig_radar = px.bar(df_mes, x='Data_F', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=600, color_discrete_sequence=px.colors.qualitative.Prism)
                
                df_totais = df_mes.groupby('Data_F')['Saldo_Limpo'].sum().reset_index()
                for i, row in df_totais.iterrows():
                    fig_radar.add_annotation(x=row['Data_F'], y=row['Saldo_Limpo'], text=f"<b>{formatar_real(row['Saldo_Limpo'])}</b>", showarrow=False, yshift=12, font=dict(size=11))
                
                fig_radar.update_layout(xaxis_type='category', showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)

    # --- ABA: PAGAMENTOS UNICRED (LÓGICA BLINDADA) ---
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")

        if 'df_pagamentos' not in st.session_state:
            df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            if not df_p.empty:
                if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                # Limpeza rigorosa contra .0
                cols_id = ['BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario', 'CHAVE_PIX']
                for c in cols_id:
                    if c in df_p.columns: df_p[c] = df_p[c].apply(limpar_ids)
                st.session_state['df_pagamentos'] = df_p
            else:
                st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario'])

        col_btns = st.columns([1, 1, 1, 1.5, 3])
        
        with col_btns[0]:
            with st.popover("➕ Novo Título"):
                with st.form("form_novo", clear_on_submit=True):
                    st.write("### Detalhes do Pagamento")
                    c1, c2 = st.columns(2)
                    with c1:
                        fn = st.text_input("Fornecedor")
                        fv = st.number_input("Valor", min_value=0.0, format="%.2f")
                        fd = st.date_input("Vencimento", datetime.now())
                        fc = st.text_input("CNPJ Favorecido")
                    with c2:
                        fp = st.text_input("Chave PIX")
                        fb = st.text_input("Banco", value="136")
                        fa = st.text_input("Agência", value="0000")
                        fcc = st.text_input("Conta", value="00000")
                        fdg = st.text_input("Dígito", value="0")
                    if st.form_submit_button("✅ Adicionar"):
                        nova = pd.DataFrame([{'Pagar?': True, 'NOME_FAVORECIDO': fn, 'VALOR_PAGAMENTO': fv, 'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'), 'CHAVE_PIX': fp, 'BANCO_FAVORECIDO': fb, 'AGENCIA_FAVORECIDA': fa, 'CONTA_FAVORECIDA': fcc, 'DIGITO_CONTA_FAVORECIDA': fdg, 'cnpj_beneficiario': fc}])
                        st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], nova], ignore_index=True)
                        st.rerun()

        with col_btns[1]:
            if st.button("💾 Salvar"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Google Sheets atualizado!", icon="✅")

        with col_btns[2]:
            if st.button("🔄 Atualizar"):
                del st.session_state['df_pagamentos']; st.rerun()

        with col_btns[3]:
            df_rem = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_rem.empty:
                v_total = df_rem['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Remessa ({formatar_real(v_total)})", gerar_cnab240(df_rem, {'cnpj': '00000000000000', 'convenio': '0', 'ag': '0', 'cc': '0'}), f"REM_{datetime.now().strftime('%d%m')}.txt")

        st.divider()
        st.session_state['df_pagamentos'] = st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Arquivo", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Ok!"); st.rerun()

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False; st.rerun()
