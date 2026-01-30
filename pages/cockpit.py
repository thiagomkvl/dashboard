import streamlit as st
import pandas as pd
from datetime import datetime
from database import conectar_sheets
# IMPORTANDO AS FUNÇÕES PERFEITAS DOS MÓDULOS
from modules.utils import formatar_real, identificar_tipo_pagamento
from modules.cnab_engine import gerar_cnab_pix, gerar_cnab_boleto, DADOS_HOSPITAL

# SEGURANÇA
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.title("🎛️ Cockpit de Pagamentos - SOS CARDIO")

# CONEXÃO GOOGLE SHEETS
if 'df_pagamentos' not in st.session_state:
    try:
        df_p = conectar_sheets().read(worksheet="Pagamentos_Dia", ttl=0)
        # Garante colunas
        if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
        if 'CHAVE_PIX_OU_COD_BARRAS' not in df_p.columns: 
            if 'CHAVE_PIX' in df_p.columns: df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX']
            else: df_p['CHAVE_PIX_OU_COD_BARRAS'] = ""
        
        cols_bancarias = ['BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA']
        for col in cols_bancarias:
            if col not in df_p.columns: df_p[col] = ""
            
        df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
        st.session_state['df_pagamentos'] = df_p
    except: st.session_state['df_pagamentos'] = pd.DataFrame()

# FORMULÁRIO DE INSERÇÃO
with st.expander("➕ Inserir Novo Título", expanded=False):
    with st.form("form_novo", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        fn = c1.text_input("Fornecedor/Beneficiário")
        fv = c2.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        fd = c3.date_input("Vencimento", datetime.now())
        c4, c5 = st.columns([2, 1])
        cod = c4.text_input("Chave PIX ou Código de Barras (Boleto)")
        fc = c5.text_input("CNPJ/CPF Beneficiário")
        st.caption("Dados Bancários (Opcional se tiver Pix/Boleto):")
        cb1, cb2, cb3, cb4 = st.columns(4)
        fb = cb1.text_input("Banco"); fa = cb2.text_input("Agência")
        fcc = cb3.text_input("Conta"); fdg = cb4.text_input("DV")
        
        if st.form_submit_button("Adicionar"):
            novo = pd.DataFrame([{
                'Pagar?': True, 'NOME_FAVORECIDO': fn, 'VALOR_PAGAMENTO': fv, 
                'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'), 'cnpj_beneficiario': fc,
                'CHAVE_PIX_OU_COD_BARRAS': cod, 'BANCO_FAVORECIDO': fb, 
                'AGENCIA_FAVORECIDA': fa, 'CONTA_FAVORECIDA': fcc, 'DIGITO_CONTA_FAVORECIDA': fdg
            }])
            st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], novo], ignore_index=True)
            st.rerun()

# TABELA PRINCIPAL
st.subheader("Lista de Pagamentos do Dia")
if not st.session_state['df_pagamentos'].empty:
    df_display = st.session_state['df_pagamentos'].copy()
    df_display['Tipo'] = df_display.apply(identificar_tipo_pagamento, axis=1)
    
    edited_df = st.data_editor(
        df_display, 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Pagar?": st.column_config.CheckboxColumn("Pagar?", default=True),
            "Tipo": st.column_config.TextColumn("Tipo", width="small", disabled=True),
            "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor", format="R$ %.2f")
        }
    )
    if not edited_df.equals(df_display):
        st.session_state['df_pagamentos'] = edited_df.drop(columns=['Tipo'])

    st.divider()
    
    # RESUMO E BOTÕES
    col_resumo, col_botoes = st.columns([1, 2])
    df_pagar = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True].copy()
    
    if not df_pagar.empty:
        # AQUI ESTÁ O SEGREDO: FILTRAGEM PRÉVIA
        df_pagar['TIPO_DETECTADO'] = df_pagar.apply(identificar_tipo_pagamento, axis=1)
        lote_pix = df_pagar[df_pagar['TIPO_DETECTADO'] == 'PIX']
        lote_boleto = df_pagar[df_pagar['TIPO_DETECTADO'] == 'BOLETO']
        
        with col_resumo:
            st.metric("Total a Pagar", formatar_real(lote_pix['VALOR_PAGAMENTO'].sum() + lote_boleto['VALOR_PAGAMENTO'].sum()))
            st.caption(f"Pix: {len(lote_pix)} | Boletos: {len(lote_boleto)}")
        
        with col_botoes:
            st.write("### 🚀 Gerar Remessa")
            c_btn1, c_btn2 = st.columns(2)
            if not lote_pix.empty:
                c_btn1.download_button(f"Baixar Lote PIX ({len(lote_pix)})", gerar_cnab_pix(lote_pix, DADOS_HOSPITAL), f"REM_PIX_{datetime.now().strftime('%d%m_%H%M')}.txt")
            if not lote_boleto.empty:
                c_btn2.download_button(f"Baixar Lote BOLETOS ({len(lote_boleto)})", gerar_cnab_boleto(lote_boleto, DADOS_HOSPITAL), f"REM_BOLETO_{datetime.now().strftime('%d%m_%H%M')}.txt")
    else: st.info("Selecione itens na tabela.")

st.divider()
if st.button("💾 Salvar Alterações"):
    conectar_sheets().update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
    st.toast("Salvo!", icon="✅")
