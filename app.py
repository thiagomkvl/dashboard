import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 1. CONFIGURAÇÃO E SEGURANÇA
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
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")
    return False

# --- FUNÇÕES DE LIMPEZA E FORMATAÇÃO ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def tratar_texto_puro(valor):
    if pd.isna(valor) or valor == "": return ""
    if isinstance(valor, float):
        if valor == int(valor): valor = int(valor)
    return str(valor).strip()

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(tratar_texto_puro(texto))
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

    # --- ABA: DASHBOARD PRINCIPAL ---
    if aba == "Dashboard Principal":
        df_hist = conn.read(worksheet="Historico", ttl=300)
        if not df_hist.empty:
            df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
            ultima_data = df_hist['data_processamento'].max()
            df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()
            
            # Cálculo de ABC e Enriquecimento
            df_abc_calc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
            total_geral = df_abc_calc['Saldo_Limpo'].sum()
            df_abc_calc['Acum'] = df_abc_calc['Saldo_Limpo'].cumsum() / total_geral
            df_abc_calc['Classe ABC'] = df_abc_calc['Acum'].apply(lambda x: 'Classe A' if x <= 0.8 else ('Classe B' if x <= 0.95 else 'Classe C'))
            df_hoje = df_hoje.merge(df_abc_calc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

            # --- FILTROS LATERAIS ---
            st.sidebar.divider()
            st.sidebar.subheader("Filtros do Dashboard")
            f_abc = st.sidebar.multiselect("Filtrar por Classe:", options=['Classe A', 'Classe B', 'Classe C'], default=['Classe A', 'Classe B', 'Classe C'])
            f_forn = st.sidebar.multiselect("Filtrar Fornecedor:", options=sorted(df_hoje['Beneficiario'].unique()))
            
            df_view = df_hoje[df_hoje['Classe ABC'].isin(f_abc)]
            if f_forn: df_view = df_view[df_view['Beneficiario'].isin(f_forn)]

            st.title("Gestão de Passivo - SOS CARDIO")
            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
            c_m1.metric("Dívida Filtrada", formatar_real(df_view['Saldo_Limpo'].sum()))
            c_m2.metric("Total Vencido", formatar_real(df_view[df_view['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()))
            c_m3.metric("Qtd Títulos", len(df_view))
            c_m4.metric("Fornecedores", len(df_view['Beneficiario'].unique()))

            st.divider()
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.subheader("Curva ABC")
                fig_pie = px.pie(df_view, values='Saldo_Limpo', names='Classe ABC', hole=0.4, 
                               color_discrete_map={'Classe A': '#004a99', 'Classe B': '#ffcc00', 'Classe C': '#d1d5db'})
                st.plotly_chart(fig_pie, use_container_width=True)
            with c_col2:
                st.subheader("Distribuição por Vencimento")
                ordem_ageing = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                df_bar_age = df_view.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem_ageing).reset_index().fillna(0)
                st.plotly_chart(px.bar(df_bar_age, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99']), use_container_width=True)

            st.divider()
            st.subheader("🎯 Radar de Pagamentos (Arraste para navegar no tempo)")
            df_view['Venc_DT'] = pd.to_datetime(df_view['Vencimento'], dayfirst=True, errors='coerce')
            df_radar = df_view[df_view['Venc_DT'] >= pd.Timestamp.now().normalize()].groupby('Venc_DT')['Saldo_Limpo'].sum().reset_index()
            
            if not df_radar.empty:
                fig_radar = px.area(df_radar, x='Venc_DT', y='Saldo_Limpo', markers=True, 
                                  color_discrete_sequence=['#004a99'], labels={'Saldo_Limpo': 'Total do Dia', 'Venc_DT': 'Data'})
                fig_radar.update_xaxes(rangeslider_visible=True) # BARRA DE ARRASTAR
                st.plotly_chart(fig_radar, use_container_width=True)

    # --- ABA: PAGAMENTOS UNICRED ---
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")

        if 'df_pagamentos' not in st.session_state:
            df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            if not df_p.empty:
                if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                cols_limpar = ['BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario', 'CHAVE_PIX']
                for c in cols_limpar:
                    if c in df_p.columns: df_p[c] = df_p[c].apply(tratar_texto_puro)
                st.session_state['df_pagamentos'] = df_p
            else:
                st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario'])

        # Botões Compactos
        c_b1, c_b2, c_b3, c_b4, _ = st.columns([1, 1, 1, 1.5, 2])
        with c_b1:
            with st.popover("➕ Novo"):
                with st.form("form_novo"):
                    fn = st.text_input("Fornecedor")
                    fv = st.number_input("Valor", min_value=0.0)
                    fd = st.date_input("Vencimento")
                    fc = st.text_input("CNPJ")
                    fp = st.text_input("PIX")
                    if st.form_submit_button("Ok"):
                        nova = pd.DataFrame([{'Pagar?': True, 'NOME_FAVORECIDO': fn, 'VALOR_PAGAMENTO': fv, 'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'), 'CHAVE_PIX': fp, 'BANCO_FAVORECIDO': '136', 'AGENCIA_FAVORECIDA': '0000', 'CONTA_FAVORECIDA': '00000', 'DIGITO_CONTA_FAVORECIDA': '0', 'cnpj_beneficiario': fc}])
                        st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], nova], ignore_index=True)
                        st.rerun()
        with c_b2:
            if st.button("💾 Salvar"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Salvo!"); 
        with c_b3:
            if st.button("🔄 Atualizar"): del st.session_state['df_pagamentos']; st.rerun()
        with c_b4:
            df_remessa = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_remessa.empty:
                st.download_button("🚀 Baixar Remessa", gerar_cnab240(df_remessa, {'cnpj': '00000000000000', 'ag': '0', 'cc': '0'}), f"REM_{datetime.now().strftime('%d%m')}.txt")

        st.divider()
        st.session_state['df_pagamentos'] = st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("XLSX", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Sucesso!"); st.rerun()

    if st.sidebar.button("🔒 Sair"): st.session_state["password_correct"] = False; st.rerun()
