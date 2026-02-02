import streamlit as st
import pandas as pd
from datetime import datetime
from database import conectar_sheets

# --- IMPORTAÇÃO SEGURA DAS FUNÇÕES ---
try:
    from modules.utils import formatar_real, identificar_tipo_pagamento
    # Importa a função do arquivo que acabamos de ajustar na Parte 1
    from modules.cnab_engine import gerar_cnab_pix 
except ImportError as e:
    st.error(f"Erro crítico nos módulos: {e}")
    st.stop()

# --- SEGURANÇA ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.title("🎛️ Cockpit de Pagamentos - SOS CARDIO")

# --- CONEXÃO GOOGLE SHEETS ---
if 'df_pagamentos' not in st.session_state:
    try:
        conn = conectar_sheets()
        df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
        
        # Garante estrutura mínima
        if df_p.empty:
            df_p = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX_OU_COD_BARRAS', 'cnpj_beneficiario'])
            
        if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
        
        # Unifica colunas de pagamento
        if 'CHAVE_PIX_OU_COD_BARRAS' not in df_p.columns: 
            if 'CHAVE_PIX' in df_p.columns: 
                df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX']
            else: 
                df_p['CHAVE_PIX_OU_COD_BARRAS'] = ""
        
        # Garante booleano para checkbox
        df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
        
        st.session_state['df_pagamentos'] = df_p
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        st.session_state['df_pagamentos'] = pd.DataFrame()

# --- FORMULÁRIO DE INSERÇÃO ---
with st.expander("➕ Inserir Novo Título", expanded=False):
    with st.form("form_novo", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        fn = c1.text_input("Fornecedor/Beneficiário")
        fv = c2.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        fd = c3.date_input("Vencimento", datetime.now())
        
        c4, c5 = st.columns([2, 1])
        cod = c4.text_input("Chave PIX ou Código de Barras (Boleto)")
        fc = c5.text_input("CNPJ/CPF Beneficiário (Somente Números)")
        
        st.caption("Dados Bancários (Apenas se for TED - Opcional para PIX/Boleto):")
        cb1, cb2, cb3, cb4 = st.columns(4)
        fb = cb1.text_input("Banco")
        fa = cb2.text_input("Agência")
        fcc = cb3.text_input("Conta")
        fdg = cb4.text_input("DV")
        
        if st.form_submit_button("Adicionar"):
            # --- LIMPEZA DE DADOS ---
            cod_limpo = cod.strip()
            # Remove pontos/traços se não for email
            if "@" not in cod_limpo:
                cod_limpo = cod_limpo.replace(".", "").replace("-", "").replace("/", "").replace(" ", "")
            
            # Cria linha
            novo = pd.DataFrame([{
                'Pagar?': True, 
                'NOME_FAVORECIDO': fn, 
                'VALOR_PAGAMENTO': fv, 
                'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'),
                'cnpj_beneficiario': fc.replace(".", "").replace("-", "").replace("/", ""),
                'CHAVE_PIX_OU_COD_BARRAS': cod_limpo,
                'BANCO_FAVORECIDO': fb, 
                'AGENCIA_FAVORECIDA': fa, 
                'CONTA_FAVORECIDA': fcc, 
                'DIGITO_CONTA_FAVORECIDA': fdg
            }])
            
            st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], novo], ignore_index=True)
            st.rerun()

# --- TABELA PRINCIPAL ---
st.subheader("Lista de Pagamentos do Dia")
if not st.session_state['df_pagamentos'].empty:
    df_display = st.session_state['df_pagamentos'].copy()
    
    # Identifica tipo visualmente
    df_display['Tipo'] = df_display.apply(identificar_tipo_pagamento, axis=1)
    
    edited_df = st.data_editor(
        df_display, 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Pagar?": st.column_config.CheckboxColumn("Pagar?", default=True),
            "Tipo": st.column_config.TextColumn("Tipo", width="small", disabled=True),
            "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "CHAVE_PIX_OU_COD_BARRAS": st.column_config.TextColumn("Chave/Código", width="medium")
        }
    )
    
    # Atualiza estado se houver edição
    if not edited_df.equals(df_display):
        # Remove coluna auxiliar 'Tipo' antes de salvar no estado
        colunas_reais = [c for c in edited_df.columns if c != 'Tipo']
        st.session_state['df_pagamentos'] = edited_df[colunas_reais]

    st.divider()
    
    # --- RESUMO E GERAÇÃO ---
    col_resumo, col_botoes = st.columns([1, 2])
    
    # Filtra apenas os marcados
    df_pagar = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True].copy()
    
    if not df_pagar.empty:
        df_pagar['TIPO_DETECTADO'] = df_pagar.apply(identificar_tipo_pagamento, axis=1)
        lote_pix = df_pagar[df_pagar['TIPO_DETECTADO'] == 'PIX']
        lote_boleto = df_pagar[df_pagar['TIPO_DETECTADO'] == 'BOLETO']
        
        with col_resumo:
            total = lote_pix['VALOR_PAGAMENTO'].sum() + lote_boleto['VALOR_PAGAMENTO'].sum()
            st.metric("Total a Pagar", formatar_real(total))
            st.caption(f"Pix: {len(lote_pix)} | Boletos: {len(lote_boleto)}")
        
        with col_botoes:
            st.write("### 🚀 Gerar Remessa")
            c_btn1, c_btn2 = st.columns(2)
            
            # BOTÃO PIX (Com Sequencial Automático)
            if not lote_pix.empty:
                arquivo_pix = gerar_cnab_pix(lote_pix) # Não precisa mais passar DADOS_HOSPITAL, já está no módulo
                if arquivo_pix:
                    c_btn1.download_button(
                        label=f"📥 Baixar PIX ({len(lote_pix)})", 
                        data=arquivo_pix, 
                        file_name=f"CB{datetime.now().strftime('%d%m')}_PIX.txt",
                        mime="text/plain"
                    )
            
            # Placeholder Boleto (Se precisar ativar, importe a função)
            if not lote_boleto.empty:
                c_btn2.info("Função Boleto em manutenção.")

    else:
        st.info("Selecione itens na tabela para processar.")

st.divider()
if st.button("💾 Salvar na Planilha"):
    conectar_sheets().update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
    st.toast("Dados salvos no Google Sheets!", icon="✅")
