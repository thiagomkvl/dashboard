import streamlit as st
import pandas as pd
from datetime import datetime
from database import conectar_sheets

# --- IMPORTAÇÃO SEGURA DAS FUNÇÕES ---
try:
    from modules.utils import formatar_real, identificar_tipo_pagamento
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
        
        # Garante estrutura mínima se vier vazia
        if df_p.empty:
            df_p = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX_OU_COD_BARRAS', 'cnpj_beneficiario'])
            
        if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
        
        # Unifica colunas de pagamento
        if 'CHAVE_PIX_OU_COD_BARRAS' not in df_p.columns: 
            if 'CHAVE_PIX' in df_p.columns: 
                df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX']
            else: 
                df_p['CHAVE_PIX_OU_COD_BARRAS'] = ""
        
        # --- CORREÇÃO DE TIPAGEM INICIAL ---
        df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
        
        if 'VALOR_PAGAMENTO' in df_p.columns:
            df_p['VALOR_PAGAMENTO'] = pd.to_numeric(
                df_p['VALOR_PAGAMENTO'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            ).fillna(0.0)
            
        # Força Chave Pix para texto (evita erro de float no editor)
        df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX_OU_COD_BARRAS'].astype(str).replace('nan', '').replace('None', '')
        
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
            # Limpeza de Dados
            cod_limpo = cod.strip()
            if "@" not in cod_limpo:
                cod_limpo = cod_limpo.replace(".", "").replace("-", "").replace("/", "").replace(" ", "")
            
            novo = pd.DataFrame([{
                'Pagar?': True, 
                'NOME_FAVORECIDO': fn, 
                'VALOR_PAGAMENTO': float(fv),
                'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'),
                'cnpj_beneficiario': fc.replace(".", "").replace("-", "").replace("/", ""),
                'CHAVE_PIX_OU_COD_BARRAS': str(cod_limpo), # Garante string na origem
                'BANCO_FAVORECIDO': fb, 
                'AGENCIA_FAVORECIDA': fa, 
                'CONTA_FAVORECIDA': fcc, 
                'DIGITO_CONTA_FAVORECIDA': fdg
            }])
            
            st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], novo], ignore_index=True)
            # Reforça tipagem
            st.session_state['df_pagamentos']['VALOR_PAGAMENTO'] = st.session_state['df_pagamentos']['VALOR_PAGAMENTO'].astype(float)
            st.session_state['df_pagamentos']['CHAVE_PIX_OU_COD_BARRAS'] = st.session_state['df_pagamentos']['CHAVE_PIX_OU_COD_BARRAS'].astype(str)
            st.rerun()

# --- TABELA PRINCIPAL ---
st.subheader("Lista de Pagamentos do Dia")

if not st.session_state['df_pagamentos'].empty:
    df_display = st.session_state['df_pagamentos'].copy()
    
    # --- BLINDAGEM CONTRA ERROS DE TIPO (CRÍTICO) ---
    # 1. Valor vira Float
    df_display['VALOR_PAGAMENTO'] = pd.to_numeric(df_display['VALOR_PAGAMENTO'], errors='coerce').fillna(0.0)
    # 2. Checkbox vira Bool
    df_display['Pagar?'] = df_display['Pagar?'].astype(bool)
    # 3. Chave Pix vira String (CORREÇÃO DO ERRO ATUAL)
    # Converte para string, remove 'nan' literal e remove '.0' se o pandas tiver lido como float (ex: 123.0 vira 123)
    df_display['CHAVE_PIX_OU_COD_BARRAS'] = df_display['CHAVE_PIX_OU_COD_BARRAS'].astype(str).replace('nan', '')
    df_display['CHAVE_PIX_OU_COD_BARRAS'] = df_display['CHAVE_PIX_OU_COD_BARRAS'].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
    
    # Identifica tipo visualmente
    df_display['Tipo'] = df_display.apply(identificar_tipo_pagamento, axis=1)
    
    try:
        edited_df = st.data_editor(
            df_display, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Pagar?": st.column_config.CheckboxColumn("Pagar?", default=True),
                "Tipo": st.column_config.TextColumn("Tipo", width="small", disabled=True),
                "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                # Agora é seguro usar TextColumn pois forçamos string acima
                "CHAVE_PIX_OU_COD_BARRAS": st.column_config.TextColumn("Chave/Código", width="medium")
            }
        )
        
        # Atualiza estado se houver edição
        if not edited_df.equals(df_display):
            colunas_reais = [c for c in edited_df.columns if c != 'Tipo']
            st.session_state['df_pagamentos'] = edited_df[colunas_reais]

    except Exception as e:
        st.error(f"Erro ao renderizar tabela: {e}")
        st.caption("Tentando exibir dados brutos:")
        st.dataframe(df_display)

    st.divider()
    
    # --- RESUMO E GERAÇÃO ---
    col_resumo, col_botoes = st.columns([1, 2])
    
    df_pagar = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True].copy()
    
    if not df_pagar.empty:
        df_pagar['TIPO_DETECTADO'] = df_pagar.apply(identificar_tipo_pagamento, axis=1)
        lote_pix = df_pagar[df_pagar['TIPO_DETECTADO'] == 'PIX']
        lote_boleto = df_pagar[df_pagar['TIPO_DETECTADO'] == 'BOLETO']
        
        with col_resumo:
            # Soma segura
            total = pd.to_numeric(lote_pix['VALOR_PAGAMENTO'], errors='coerce').sum() + pd.to_numeric(lote_boleto['VALOR_PAGAMENTO'], errors='coerce').sum()
            st.metric("Total a Pagar", formatar_real(total))
            st.caption(f"Pix: {len(lote_pix)} | Boletos: {len(lote_boleto)}")
        
        with col_botoes:
            st.write("### 🚀 Gerar Remessa")
            c_btn1, c_btn2 = st.columns(2)
            
            # BOTÃO PIX
            if not lote_pix.empty:
                arquivo_pix = gerar_cnab_pix(lote_pix)
                if arquivo_pix:
                    c_btn1.download_button(
                        label=f"📥 Baixar PIX ({len(lote_pix)})", 
                        data=arquivo_pix, 
                        file_name=f"CB{datetime.now().strftime('%d%m')}_PIX.txt",
                        mime="text/plain"
                    )
            
            # BOTÃO BOLETO (DESBLOQUEADO AGORA!)
            if not lote_boleto.empty:
                # Reutilizamos a engine, pois ela agora é híbrida e sabe lidar com boletos
                arquivo_boleto = gerar_cnab_pix(lote_boleto)
                if arquivo_boleto:
                    c_btn2.download_button(
                        label=f"📥 Baixar Boleto ({len(lote_boleto)})", 
                        data=arquivo_boleto, 
                        file_name=f"CB{datetime.now().strftime('%d%m')}_BOLETO.txt",
                        mime="text/plain"
                    )

    else:
        st.info("Selecione itens na tabela para processar.")

st.divider()
if st.button("💾 Salvar na Planilha"):
    conectar_sheets().update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
    st.toast("Dados salvos no Google Sheets!", icon="✅")
