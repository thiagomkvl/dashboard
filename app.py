import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 0. DADOS CADASTRAIS (ATUALIZADOS CONFORME ERRO)
# ==========================================
DADOS_HOSPITAL = {
    'cnpj': '28067375000174',      # CNPJ sem pontos
    'convenio': '000000000985597', # Convênio 20 dígitos
    'ag': '1214',                  # Agência (sem DV)
    'ag_dv': '0',                  # DV Agência
    'cc': '5886',                  # Conta (sem DV)
    'cc_dv': '6',                  # CORRIGIDO: Validador exigiu '6'
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'endereco': 'RODOVIA SC 401',
    'num_end': '123',
    'complemento': 'SALA 01',
    'cidade': 'FLORIANOPOLIS',
    'cep': '88000000',             # CEP 8 dígitos
    'uf': 'SC'
}

# ==========================================
# 1. CONFIGURAÇÃO E SEGURANÇA
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

def check_password():
    if st.session_state.get("password_correct"): return True
    def password_entered():
        if "password" in st.session_state and st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else: st.session_state["password_correct"] = False
    st.markdown("<h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2: st.text_input("Senha:", type="password", on_change=password_entered, key="password")
    return False

# --- FUNÇÕES AUXILIARES ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def limpar_ids(valor):
    if pd.isna(valor) or valor == "": return ""
    return "".join(filter(str.isalnum, str(valor).split('.')[0]))

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='l'):
    """
    Função de formatação estrita.
    alinhar='l': Texto à esquerda, preenche com espaços à direita (Padrão texto)
    alinhar='r': Texto à direita, preenche com zeros à esquerda (Padrão número)
    """
    texto_str = remover_acentos(str(texto))
    
    if alinhar == 'r':
        # Remove tudo que não for dígito para campos numéricos
        texto_limpo = "".join(filter(str.isdigit, texto_str))
        res = texto_limpo[:tamanho].rjust(tamanho, preenchimento)
    else:
        res = texto_str[:tamanho].ljust(tamanho, preenchimento)
    
    return res[:tamanho] # Garante corte exato

# ==========================================
# 2. MOTOR CNAB 240 (CORREÇÃO DE ERROS)
# ==========================================
def gerar_cnab240(df_sel, h):
    linhas = []
    hoje = datetime.now()
    BCO = "136"

    # --- REGISTRO 0: HEADER DE ARQUIVO ---
    # Fix Erro 1 (Agência 01214) e DV Conta (6)
    h0 = (f"{BCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f" {formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000")
    linhas.append(h0[:240].ljust(240))
    
    # --- REGISTRO 1: HEADER DE LOTE ---
    # Fix Erro 2 (Tipo Insc '2') e Erro 5 (Endereço e CEP)
    h1 = (f"{BCO}00011C2045046 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f" {formatar_campo(h['nome'],30)}{' '*40}"
          f"{formatar_campo(h['endereco'],30)}{formatar_campo(h['num_end'],5,'0','r')}"
          f"{formatar_campo(h.get('complemento',' '),15)}{formatar_campo(h['cidade'],20)}"
          f"{formatar_campo(h['cep'],8,'0','r')}{formatar_campo(h['uf'],2)}01{' '*10}")
    linhas.append(h1[:240].ljust(240))
    
    reg_lote = 0
    for _, r in df_sel.reset_index(drop=True).iterrows():
        v = int(float(str(r['VALOR_PAGAMENTO']).replace(',','.')) * 100)
        chave_pix = limpar_ids(r.get('CHAVE_PIX', ''))
        
        # Fix Erro 7: Data deve ter 8 dígitos (DDMMAAAA)
        try: data_pagto = pd.to_datetime(r['DATA_PAGAMENTO'], dayfirst=True).strftime('%d%m%Y')
        except: data_pagto = hoje.strftime('%d%m%Y')
        
        if chave_pix:
            if "@" in str(r.get('CHAVE_PIX','')): forma_ini = "02"
            elif len(chave_pix) in [11, 14]: forma_ini = "03"
            else: forma_ini = "04"
        else: forma_ini = "05"

        # --- SEGMENTO A ---
        # Fix Erro 6 (Câmara 009) e Erro 8 (Moeda BRL alinhada)
        reg_lote += 1
        segA = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}A000009{formatar_campo(r['BANCO_FAVORECIDO'],3,'0','r')}"
                f"{formatar_campo(r['AGENCIA_FAVORECIDA'],5,'0','r')}{formatar_campo(r.get('DG_AG_FAV',' '),1,' ','l')}"
                f"{formatar_campo(r['CONTA_FAVORECIDA'],12,'0','r')}{formatar_campo(r.get('DIGITO_CONTA_FAVORECIDA',' '),1,' ','l')}"
                f" {formatar_campo(r['NOME_FAVORECIDO'],30)}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}{data_pagto}BRL{'0'*15}{formatar_campo(v,15,'0','r')}"
                f"{' '*40}00")
        linhas.append(segA[:240].ljust(240))
        
        # --- SEGMENTO B ---
        reg_lote += 1
        segB = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{formatar_campo(forma_ini,3,'0','r')}" 
                f"2{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}{' '*100}"
                f"{formatar_campo(chave_pix,35)}{' '*68}00000000")
        linhas.append(segB[:240].ljust(240))
        
    # --- TRAILER DE LOTE ---
    reg_lote += 1
    t5 = f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(int(df_sel['VALOR_PAGAMENTO'].sum()*100),18,'0','r')}{' '*100}" # Fix Erro 9 (Espaços)
    linhas.append(t5[:240].ljust(240))
    
    # --- TRAILER DE ARQUIVO ---
    t9 = f"{BCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    
    return "\n".join(linhas)

# ==========================================
# 3. LÓGICA DO APP
# ==========================================
if check_password():
    conn = conectar_sheets()
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Upload"])

    # --- ABA DASHBOARD (MANTIDA ORIGINAL) ---
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
            st.subheader("🎯 Radar de Pagamentos")
            df_hoje['Venc_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
            df_futuro = df_hoje[df_hoje['Venc_DT'] >= pd.Timestamp.now().normalize()].copy()
            if not df_futuro.empty:
                df_futuro['Mes_Ref'] = df_futuro['Venc_DT'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Selecione o Mês:", sorted(df_futuro['Mes_Ref'].unique()))
                df_mes = df_futuro[df_futuro['Mes_Ref'] == mes_sel].sort_values('Venc_DT')
                df_mes['Data_F'] = df_mes['Venc_DT'].dt.strftime('%d/%m/%Y')
                fig_radar = px.bar(df_mes, x='Data_F', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=600)
                df_tot = df_mes.groupby('Data_F')['Saldo_Limpo'].sum().reset_index()
                for i, row in df_tot.iterrows(): fig_radar.add_annotation(x=row['Data_F'], y=row['Saldo_Limpo'], text=f"<b>{formatar_real(row['Saldo_Limpo'])}</b>", showarrow=False, yshift=12)
                fig_radar.update_layout(xaxis_type='category', showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)

    # --- ABA CONVERSOR (AJUSTADA) ---
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
            df_rem = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_rem.empty:
                v_total = df_rem['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Gerar Remessa ({formatar_real(v_total)})", gerar_cnab240(df_rem, DADOS_HOSPITAL), f"REM_SOS_{datetime.now().strftime('%d%m')}.txt")
            st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Arquivo", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Base Atualizada!"); st.rerun()

    if st.sidebar.button("🔒 Sair"): st.session_state["password_correct"] = False; st.rerun()
