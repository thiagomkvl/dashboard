import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 0. CONFIGURAÇÃO DE DADOS DO HOSPITAL (SOS CARDIO)
# Preencha estes dados conforme o cadastro na Unicred
# ==========================================
DADOS_HOSPITAL = {
    'cnpj': '00000000000000',      
    'convenio': '00000000000000000000', 
    'ag': '1214',                  # Ajustado conforme erro
    'ag_dv': '0',                  
    'cc': '5886',                  # Ajustado conforme erro
    'cc_dv': '0',                  # Obrigatório conforme manual 
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'endereco': 'RUA DO HOSPITAL 123',
    'num_end': '123',
    'cidade': 'FLORIANOPOLIS',
    'cep': '88000000',             
    'uf': 'SC'
}

# ==========================================
# 1. CONFIGURAÇÃO, CSS E SEGURANÇA
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

def check_password():
    if st.session_state.get("password_correct"): return True
    def password_entered():
        if "password" in st.session_state and st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
    st.markdown("<h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2: st.text_input("Senha:", type="password", on_change=password_entered, key="password")
    return False

# --- FUNÇÕES DE SUPORTE ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def limpar_ids(valor):
    if pd.isna(valor) or valor == "": return ""
    return "".join(filter(str.isalnum, str(valor).split('.')[0]))

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(str(texto))
    if alinhar == 'direita':
        texto = "".join(filter(str.isdigit, texto))
        res = texto[:tamanho].rjust(tamanho, preenchimento)
    else:
        res = texto[:tamanho].ljust(tamanho, preenchimento)
    return res[:tamanho]

# ==========================================
# 2. MOTOR CNAB 240 (UNICRED V10.9) - FIX ERROS
# ==========================================
def gerar_cnab240(df_sel, h):
    linhas = []
    hoje = datetime.now()
    COD_BANCO = "136" # Fix erro 001 

    # Registro 0: Header de Arquivo
    h0 = (f"{COD_BANCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20)}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1)} "
          f"{formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000")
    linhas.append(h0[:240].ljust(240))
    
    # Registro 1: Header de Lote (Pix=45 [cite: 23], Layout=046 [cite: 13, 17])
    # Inclui Endereço, CEP e UF obrigatórios 
    h1 = (f"{COD_BANCO}00011C2045046 {' '*1}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20)}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1)} "
          f"{formatar_campo(h['nome'],30)}{' '*40}{formatar_campo(h['endereco'],30)}{formatar_campo(h['num_end'],5,'0','r')}{' '*15}{formatar_campo(h['cidade'],20)}{formatar_campo(h['cep'],8,'0','r')}{formatar_campo(h['uf'],2)}{' '*10}{' '*10}")
    linhas.append(h1[:240].ljust(240))
    
    reg_lote = 0
    for i, r in df_sel.reset_index(drop=True).iterrows():
        v = int(float(str(r['VALOR_PAGAMENTO']).replace(',','.')) * 100)
        chave_pix = limpar_ids(r.get('CHAVE_PIX', ''))
        data_p = pd.to_datetime(r['DATA_PAGAMENTO']).strftime('%d%m%Y') # 8 dígitos 
        
        # Identificação de Chave Pix [cite: 62, 83]
        if chave_pix:
            if "@" in str(r.get('CHAVE_PIX','')): forma_ini = "02"
            elif len(chave_pix) in [11, 14]: forma_ini = "03"
            else: forma_ini = "04"
        else: forma_ini = "05"

        # Segmento A (SPI/Pix=009 [cite: 51])
        reg_lote += 1
        segA = (f"{COD_BANCO}00013{formatar_campo(reg_lote,5,'0','r')}A00001009{formatar_campo(r['BANCO_FAVORECIDO'],3,'0','r')}{formatar_campo(r['AGENCIA_FAVORECIDA'],5,'0','r')} "
                f"{formatar_campo(r['CONTA_FAVORECIDA'],12,'0','r')}{formatar_campo(r['DIGITO_CONTA_FAVORECIDA'],1)} {formatar_campo(r['NOME_FAVORECIDO'],30)}{formatar_campo(r.get('Nr. Titulo',''),20)}{data_p}BRL{'0'*15}{formatar_campo(v,15,'0','r')}{' '*40}00")
        linhas.append(segA[:240].ljust(240))
        
        # Segmento B [cite: 63, 67]
        reg_lote += 1
        segB = f"{COD_BANCO}00013{formatar_campo(reg_lote,5,'0','r')}B   {forma_ini}{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}{' '*100}{formatar_campo(chave_pix,35)}{' '*68}00000000"
        linhas.append(segB[:240].ljust(240))
        
    # Registro 5: Trailer de Lote
    reg_lote += 1
    v_total = int(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100)
    t5 = f"{COD_BANCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total,18,'0','r')}{'0'*100}"
    linhas.append(t5[:240].ljust(240))
    
    # Registro 9: Trailer de Arquivo (Fix espaços [cite: 164])
    t9 = f"{COD_BANCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    
    return "\n".join(linhas)

# ==========================================
# 3. LÓGICA DO APP
# ==========================================
if check_password():
    conn = conectar_sheets()
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Upload"])

    # --- ABA: DASHBOARD PRINCIPAL (VERSÃO COMPLETA APROVADA) ---
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
            total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
            m1.metric("Dívida Total", formatar_real(total_hoje))
            m2.metric("Total Vencido", formatar_real(total_vencido))
            m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
            m4.metric("Última Atualização", ultima_data)

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Curva ABC")
                st.plotly_chart(px.pie(df_hoje, values='Saldo_Limpo', names='Classe ABC', hole=0.4, 
                             color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'}), use_container_width=True)
            with c2:
                st.subheader("Ageing (Vencimentos)")
                ordem = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                df_bar = df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem).reset_index().fillna(0)
                st.plotly_chart(px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s'), use_container_width=True)

            st.divider()
            st.subheader("🎯 Radar de Pagamentos - Detalhamento por Mês")
            df_hoje['Vencimento_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
            df_futuro = df_hoje[df_hoje['Vencimento_DT'] >= pd.Timestamp.now().normalize()].copy()
            if not df_futuro.empty:
                df_futuro['Mes_Ref'] = df_futuro['Vencimento_DT'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Selecione o Mês:", sorted(df_futuro['Mes_Ref'].unique()))
                df_mes = df_futuro[df_futuro['Mes_Ref'] == mes_sel].sort_values('Vencimento_DT')
                df_mes['Data_F'] = df_mes['Vencimento_DT'].dt.strftime('%d/%m/%Y')
                fig_radar = px.bar(df_mes, x='Data_F', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=600)
                df_totais = df_mes.groupby('Data_F')['Saldo_Limpo'].sum().reset_index()
                for i, row in df_totais.iterrows():
                    fig_radar.add_annotation(x=row['Data_F'], y=row['Saldo_Limpo'], text=f"<b>{formatar_real(row['Saldo_Limpo'])}</b>", showarrow=False, yshift=12)
                fig_radar.update_layout(xaxis_type='category', showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)

    # --- ABA: PAGAMENTOS UNICRED ---
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred")
        df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
        if not df_p.empty:
            if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
            df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
            for c in ['BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'cnpj_beneficiario', 'CHAVE_PIX']:
                if c in df_p.columns: df_p[c] = df_p[c].apply(limpar_ids)
            st.session_state['df_pagamentos'] = df_p

        if 'df_pagamentos' in st.session_state:
            col_b1, col_b2 = st.columns([1, 4])
            df_rem = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            with col_b1:
                if not df_rem.empty:
                    v_t = df_rem['VALOR_PAGAMENTO'].astype(float).sum()
                    st.download_button(f"🚀 Gerar Remessa ({formatar_real(v_t)})", gerar_cnab240(df_rem, DADOS_HOSPITAL), f"REM_SOS_{datetime.now().strftime('%d%m')}.txt")
            st.divider()
            st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Arquivo Excel", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Base Atualizada!"); st.rerun()

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False; st.rerun()
