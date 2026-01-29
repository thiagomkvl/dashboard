import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 0. DADOS CADASTRAIS DO HOSPITAL (SOS CARDIO)
# Configurado conforme os logs de erro da Unicred
# ==========================================
DADOS_HOSPITAL = {
    'cnpj': '28067375000174',      # CNPJ da Matriz/Pagador
    'convenio': '000000000985597', # Código do Convênio (20 dígitos)
    'ag': '1214',                  # Agência
    'ag_dv': '0',                  # DV Agência
    'cc': '5886',                  # Conta Corrente
    'cc_dv': '6',                  # DV Conta (Corrigido para 6 conforme validador)
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'endereco': 'RODOVIA SC 401',
    'num_end': '123',
    'complemento': 'SALA 01',
    'cidade': 'FLORIANOPOLIS',
    'cep': '88000000',             # CEP (8 dígitos)
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
        else:
            st.session_state["password_correct"] = False
    
    st.markdown("<h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Senha de Acesso:", type="password", on_change=password_entered, key="password")
    return False

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def limpar_ids(valor):
    """Remove caracteres não numéricos e espaços."""
    if pd.isna(valor) or str(valor).strip() == "": return ""
    return "".join(filter(str.isalnum, str(valor).split('.')[0]))

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='l'):
    """
    Formata campos para o padrão estrito do CNAB.
    alinhar='l': Texto (Alinhado à esquerda, completa com espaços à direita)
    alinhar='r': Número (Alinhado à direita, completa com zeros à esquerda)
    """
    texto_str = remover_acentos(str(texto))
    
    if alinhar == 'r':
        # Mantém apenas números para campos numéricos
        texto_limpo = "".join(filter(str.isdigit, texto_str))
        if texto_limpo == "": texto_limpo = "0"
        res = texto_limpo[:tamanho].rjust(tamanho, '0') # Preenchimento com ZERO
    else:
        res = texto_str[:tamanho].ljust(tamanho, preenchimento) # Preenchimento com ESPAÇO
    
    return res[:tamanho] # Garante que nunca exceda o tamanho

# ==========================================
# 2. MOTOR CNAB 240 (UNICRED V10.9 - BLINDADO)
# ==========================================
def gerar_cnab240(df_sel, h):
    linhas = []
    hoje = datetime.now()
    BCO = "136" # Código Unicred

    # ---------------------------------------------------------
    # REGISTRO 0: HEADER DE ARQUIVO
    # ---------------------------------------------------------
    h0 = (f"{BCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}" # DV Ag/Conta
          f"{formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000")
    linhas.append(h0[:240].ljust(240))
    
    # ---------------------------------------------------------
    # REGISTRO 1: HEADER DE LOTE (Pix = 45 / Layout = 046)
    # ---------------------------------------------------------
    # Correção: Posição 18 fixa em '2' (CNPJ) e Endereço Completo
    h1 = (f"{BCO}00011C2045046 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{' '*40}" # Mensagem 1
          f"{formatar_campo(h['endereco'],30)}{formatar_campo(h['num_end'],5,'0','r')}"
          f"{formatar_campo(h.get('complemento',' '),15)}{formatar_campo(h['cidade'],20)}"
          f"{formatar_campo(h['cep'],8,'0','r')}{formatar_campo(h['uf'],2)}01{' '*10}") # 01=Crédito em Conta
    linhas.append(h1[:240].ljust(240))
    
    reg_lote = 0
    for _, r in df_sel.reset_index(drop=True).iterrows():
        # Tratamento de Valores e Datas
        v_float = float(str(r['VALOR_PAGAMENTO']).replace(',','.'))
        v_int = int(round(v_float * 100))
        
        # Garante Data com 8 dígitos (DDMMAAAA)
        try: 
            data_pagto = pd.to_datetime(r['DATA_PAGAMENTO'], dayfirst=True).strftime('%d%m%Y')
        except: 
            data_pagto = hoje.strftime('%d%m%Y')

        # Identificação da Chave PIX
        chave_pix = limpar_ids(r.get('CHAVE_PIX', ''))
        tipo_chave = "05" # Default: Dados Bancários
        if chave_pix:
            raw_pix = str(r.get('CHAVE_PIX',''))
            if "@" in raw_pix: tipo_chave = "02"   # Email
            elif len(chave_pix) == 11: tipo_chave = "03" # CPF
            elif len(chave_pix) == 14: tipo_chave = "03" # CNPJ
            elif len(chave_pix) > 20: tipo_chave = "04"  # Aleatória
            else: tipo_chave = "01" # Telefone (suposição por exclusão)

        # Dados Bancários do Favorecido (Obrigatórios mesmo com Pix)
        banco_fav = r.get('BANCO_FAVORECIDO', '') or '000'
        ag_fav = r.get('AGENCIA_FAVORECIDA', '') or '0'
        cc_fav = r.get('CONTA_FAVORECIDA', '') or '0'
        dv_cc_fav = r.get('DIGITO_CONTA_FAVORECIDA', '') or ' '

        # -----------------------------------------------------
        # SEGMENTO A (Detalhe do Pagamento)
        # Câmara 009 (SPI/Pix) | Data 8 pos | Valor 15 pos
        # -----------------------------------------------------
        reg_lote += 1
        segA = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}A000009{formatar_campo(banco_fav,3,'0','r')}"
                f"{formatar_campo(ag_fav,5,'0','r')}{formatar_campo(' ',1)}" # DV Agência (geralmente vazio)
                f"{formatar_campo(cc_fav,12,'0','r')}{formatar_campo(dv_cc_fav,1,' ','l')}"
                f"{formatar_campo(' ',1)}{formatar_campo(r['NOME_FAVORECIDO'],30)}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}{data_pagto}BRL{'0'*15}{formatar_campo(v_int,15,'0','r')}"
                f"{' '*40}00") # Finalidade e Ocorrências
        linhas.append(segA[:240].ljust(240))
        
        # -----------------------------------------------------
        # SEGMENTO B (Dados Complementares / Chave Pix)
        # -----------------------------------------------------
        reg_lote += 1
        # Se endereço vazio, preenche com placeholder para evitar erro de obrigatoriedade
        end_fav = "ENDERECO NAO INFORMADO" 
        
        segB = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{formatar_campo(tipo_chave,3,'0','r')}" 
                f"2{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}"
                f"{formatar_campo(end_fav,35)}" # Informação 10 (Endereço Obrigatório)
                f"{' '*60}" # Informação 11
                f"{formatar_campo(chave_pix,99)}" # Informação 12 (Chave PIX no final)
                f"{' '*8}") # Reservado (ISPB já coberto pelo layout se necessário, ou brancos)
        
        # Ajuste Fino Segmento B conforme manual Unicred Pix (Pág 11)
        # Posições: 001-003(BCO), 004-007(Lote), 008(3), 009-013(Seq), 014(B), 015-017(FormaIni)
        # 018(TipoInsc), 019-032(Insc), 033-067(Info10/End), 068-127(Info11), 128-226(Info12/Chave)
        # 227-232(SIAPE/Vazio), 233-240(ISPB)
        
        # Recriando Seg B estritamente posicional:
        segB_strict = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{formatar_campo(tipo_chave,3,'0','r')}" # até 17
                       f"2{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}" # 18-32 (CNPJ)
                       f"{formatar_campo(end_fav,35)}" # 33-67 (Info 10 / Endereço)
                       f"{' '*60}" # 68-127 (Info 11)
                       f"{formatar_campo(chave_pix,99)}" # 128-226 (Info 12 / Chave Pix)
                       f"{' '*6}{'0'*8}") # 227-232 (Vazio) + 233-240 (ISPB)
                       
        linhas.append(segB_strict[:240].ljust(240))
        
    # ---------------------------------------------------------
    # TRAILER DE LOTE (Registro 5)
    # ---------------------------------------------------------
    reg_lote += 1
    v_total_int = int(round(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100))
    t5 = f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total_int,18,'0','r')}{'0'*18}{' '*171}"
    # Ajuste: Qtd Moeda (18) + Aviso (6) + CNAB (165) = Completa 240
    t5_strict = f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total_int,18,'0','r')}{'0'*18}{' '*165}0000000000"
    linhas.append(t5_strict[:240].ljust(240))
    
    # ---------------------------------------------------------
    # TRAILER DE ARQUIVO (Registro 9)
    # ---------------------------------------------------------
    t9 = f"{BCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    
    return "\r\n".join(linhas)

# ==========================================
# 3. LÓGICA DO DASHBOARD E INTERFACE
# ==========================================
if check_password():
    conn = conectar_sheets()
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Upload"])

    # --- ABA: DASHBOARD PRINCIPAL ---
    if aba == "Dashboard Principal":
        try:
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
        except Exception as e:
            st.error(f"Erro ao carregar dashboard: {e}")

    # --- ABA: PAGAMENTOS UNICRED (COM FORMULÁRIO COMPLETO) ---
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred")
        
        # Carrega dados
        if 'df_pagamentos' not in st.session_state:
            try:
                df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
                if not df_p.empty:
                    if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                    df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                    # Garante que as colunas existem
                    cols_bancarias = ['BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'CHAVE_PIX']
                    for col in cols_bancarias:
                        if col not in df_p.columns: df_p[col] = ""
                    
                    # Limpeza
                    for c in cols_bancarias + ['cnpj_beneficiario']:
                        df_p[c] = df_p[c].apply(limpar_ids)
                        
                    st.session_state['df_pagamentos'] = df_p
                else:
                    st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'cnpj_beneficiario', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA'])
            except:
                st.session_state['df_pagamentos'] = pd.DataFrame()

        # Botões e Formulário
        c_form, c_action = st.columns([1, 2])
        
        with c_form:
            with st.popover("➕ Novo Pagamento"):
                with st.form("form_novo", clear_on_submit=True):
                    fn = st.text_input("Fornecedor")
                    fv = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
                    fd = st.date_input("Vencimento", datetime.now())
                    fc = st.text_input("CNPJ Favorecido")
                    st.write("--- Dados Bancários (Obrigatórios) ---")
                    fb = st.text_input("Banco (ex: 001)", max_chars=3)
                    fa = st.text_input("Agência (sem DV)", max_chars=5)
                    fcc = st.text_input("Conta (sem DV)", max_chars=12)
                    fdg = st.text_input("DV Conta", max_chars=1)
                    fp = st.text_input("Chave PIX (Opcional)")
                    
                    if st.form_submit_button("Adicionar"):
                        novo = pd.DataFrame([{
                            'Pagar?': True, 'NOME_FAVORECIDO': fn, 'VALOR_PAGAMENTO': fv, 
                            'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'), 'cnpj_beneficiario': fc,
                            'BANCO_FAVORECIDO': fb, 'AGENCIA_FAVORECIDA': fa, 
                            'CONTA_FAVORECIDA': fcc, 'DIGITO_CONTA_FAVORECIDA': fdg, 'CHAVE_PIX': fp
                        }])
                        st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], novo], ignore_index=True)
                        st.rerun()

        with c_action:
            col1, col2 = st.columns(2)
            if col1.button("💾 Salvar na Planilha"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Dados salvos!", icon="✅")
            
            if col2.button("🔄 Recarregar"):
                del st.session_state['df_pagamentos']
                st.rerun()

        st.divider()
        
        # Tabela e Download
        if 'df_pagamentos' in st.session_state and not st.session_state['df_pagamentos'].empty:
            df_rem = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            
            # Alerta de validação prévia
            if not df_rem.empty:
                sem_conta = df_rem[ (df_rem['CONTA_FAVORECIDA'] == "") | (df_rem['CONTA_FAVORECIDA'] == "0") ]
                if not sem_conta.empty:
                    st.warning(f"⚠️ Atenção: {len(sem_conta)} pagamentos estão sem CONTA preenchida. A Unicred exige conta mesmo para PIX.")
                
                v_total = df_rem['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Baixar Remessa ({formatar_real(v_total)})", 
                                 gerar_cnab240(df_rem, DADOS_HOSPITAL), 
                                 f"REM_UNICRED_{datetime.now().strftime('%d%m_%H%M')}.txt")
            
            st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Arquivo Excel", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Base Atualizada!"); st.rerun()

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False; st.rerun()
