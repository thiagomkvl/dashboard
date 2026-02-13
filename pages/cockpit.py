import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import conectar_sheets

# --- IMPORTAÇÃO SEGURA ---
try:
    from modules.utils import formatar_real, identificar_tipo_pagamento
    from modules.cnab_engine import gerar_cnab_pix 
    from modules.cnab_return_parser import parse_cnab_retorno
except ImportError as e:
    st.error(f"Erro crítico nos módulos: {e}")
    st.stop()

# --- SEGURANÇA ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.set_page_config(page_title="Cockpit SOS Cardio", page_icon="🎛️", layout="wide")
st.title("🎛️ Cockpit de Pagamentos - SOS CARDIO")

# ==============================================================================
# CARGA DE DADOS COM FORMATAÇÃO DE CNPJ
# ==============================================================================
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
        
        # Normalização de nomes
        if 'CNPJ' in df_p.columns and 'cnpj_beneficiario' not in df_p.columns:
            df_p.rename(columns={'CNPJ': 'cnpj_beneficiario'}, inplace=True)

        # ---------------------------------------------------------
        # 🟢 FUNCIONALIDADE SOLICITADA: FORMATAÇÃO DE CNPJ/CPF
        # ---------------------------------------------------------
        def corrigir_zeros_cnpj(valor):
            """Recupera os zeros à esquerda que o Excel removeu"""
            s_val = str(valor).strip()
            if s_val == 'nan' or s_val == 'None' or not s_val: return ""
            
            # Remove .0 se vier como float
            if s_val.endswith('.0'): s_val = s_val[:-2]
            
            # Deixa só números
            limpo = ''.join(filter(str.isdigit, s_val))
            if not limpo: return ""
            
            # Lógica: >11 dígitos é CNPJ (14), <=11 é CPF (11)
            if len(limpo) > 11:
                return limpo.zfill(14)
            else:
                return limpo.zfill(11)

        # 1. Aplica na coluna de CNPJ do Beneficiário
        if 'cnpj_beneficiario' in df_p.columns:
            df_p['cnpj_beneficiario'] = df_p['cnpj_beneficiario'].apply(corrigir_zeros_cnpj)

        # 2. Aplica na Chave Pix (SOMENTE se for numérica, ou seja, CPF/CNPJ)
        # Se for email ou chave aleatória, não mexe.
        def corrigir_chave_pix(valor):
            s_val = str(valor).strip()
            # Remove .0
            if s_val.endswith('.0'): s_val = s_val[:-2]
            
            # Se tiver @ ou traço longo (UUID), ignora
            if '@' in s_val or (len(s_val) > 20 and '-' in s_val):
                return s_val
            
            # Se for numérico, aplica a correção de zeros
            nums = ''.join(filter(str.isdigit, s_val))
            if len(nums) > 0:
                # Se parece CPF ou CNPJ, formata
                if len(nums) >= 11: 
                    return corrigir_zeros_cnpj(nums)
                return nums
            return s_val

        if 'CHAVE_PIX_OU_COD_BARRAS' in df_p.columns:
            df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX_OU_COD_BARRAS'].apply(corrigir_chave_pix)
        # ---------------------------------------------------------

        # Tipagem Forte do Restante
        df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
        
        if 'VALOR_PAGAMENTO' in df_p.columns:
            df_p['VALOR_PAGAMENTO'] = pd.to_numeric(
                df_p['VALOR_PAGAMENTO'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            ).fillna(0.0)
            
        df_p['DATA_PAGAMENTO'] = pd.to_datetime(df_p['DATA_PAGAMENTO'], dayfirst=True, errors='coerce')
        
        st.session_state['df_pagamentos'] = df_p
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        st.session_state['df_pagamentos'] = pd.DataFrame()

# ==============================================================================
# NAVEGAÇÃO
# ==============================================================================
tab_operacional, tab_cfo, tab_retorno = st.tabs(["📝 Operacional (Mesa)", "📊 Visão CFO", "🔄 Processar Retorno"])

# ABA 1: OPERACIONAL
with tab_operacional:
    with st.expander("➕ Inserir Novo Título Manualmente", expanded=False):
        with st.form("form_novo", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            fn = c1.text_input("Fornecedor/Beneficiário")
            fv = c2.number_input("Valor (R$)", min_value=0.01, format="%.2f")
            fd = c3.date_input("Vencimento", datetime.now())
            
            c4, c5 = st.columns([2, 1])
            cod = c4.text_input("Chave PIX ou Código de Barras")
            fc = c5.text_input("CNPJ/CPF (Números)")
            
            st.caption("Dados Bancários (Ted/Doc):")
            cb1, cb2, cb3, cb4 = st.columns(4)
            fb = cb1.text_input("Banco")
            fa = cb2.text_input("Agência")
            fcc = cb3.text_input("Conta")
            fdg = cb4.text_input("DV")
            
            if st.form_submit_button("Adicionar"):
                cod_limpo = cod.strip()
                if "@" not in cod_limpo:
                    cod_limpo = cod_limpo.replace(".", "").replace("-", "").replace("/", "").replace(" ", "")
                
                novo = pd.DataFrame([{
                    'Pagar?': True, 
                    'NOME_FAVORECIDO': fn, 
                    'VALOR_PAGAMENTO': float(fv),
                    'DATA_PAGAMENTO': pd.to_datetime(fd),
                    'cnpj_beneficiario': fc.replace(".", "").replace("-", "").replace("/", ""),
                    'CHAVE_PIX_OU_COD_BARRAS': str(cod_limpo), 
                    'BANCO_FAVORECIDO': fb, 
                    'AGENCIA_FAVORECIDA': fa, 
                    'CONTA_FAVORECIDA': fcc, 
                    'DIGITO_CONTA_FAVORECIDA': fdg
                }])
                st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], novo], ignore_index=True)
                st.rerun()

    st.subheader("Lista de Pagamentos do Dia")
    if not st.session_state['df_pagamentos'].empty:
        df_display = st.session_state['df_pagamentos'].copy()
        df_display['DATA_VISUAL'] = df_display['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')
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
                    "DATA_VISUAL": st.column_config.TextColumn("Vencimento", disabled=True),
                    "CHAVE_PIX_OU_COD_BARRAS": st.column_config.TextColumn("Chave/Código", width="medium"),
                    "DATA_PAGAMENTO": None
                }
            )
            if not edited_df.equals(df_display):
                colunas_reais = [c for c in st.session_state['df_pagamentos'].columns]
                st.session_state['df_pagamentos'].update(edited_df[colunas_reais])
        except Exception as e:
            st.error(f"Erro tabela: {e}")

        st.divider()
        col_resumo, col_botoes = st.columns([1, 2])
        df_pagar = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True].copy()
        
        if not df_pagar.empty:
            df_pagar['TIPO_DETECTADO'] = df_pagar.apply(identificar_tipo_pagamento, axis=1)
            lote_pix = df_pagar[df_pagar['TIPO_DETECTADO'] == 'PIX']
            lote_boleto = df_pagar[df_pagar['TIPO_DETECTADO'] == 'BOLETO']
            
            with col_resumo:
                total = df_pagar['VALOR_PAGAMENTO'].sum()
                st.metric("Total a Pagar", formatar_real(total))
                st.caption(f"Pix: {len(lote_pix)} | Boletos: {len(lote_boleto)}")
            
            with col_botoes:
                st.write("### 🚀 Gerar Remessa")
                c1, c2 = st.columns(2)
                if not lote_pix.empty:
                    lote_pix['DATA_PAGAMENTO'] = lote_pix['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')
                    arquivo_pix = gerar_cnab_pix(lote_pix)
                    if arquivo_pix:
                        c1.download_button(label=f"📥 Baixar PIX ({len(lote_pix)})", data=arquivo_pix, file_name=f"CB{datetime.now().strftime('%d%m')}_PIX.txt")
                if not lote_boleto.empty:
                    lote_boleto['DATA_PAGAMENTO'] = lote_boleto['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')
                    arquivo_boleto = gerar_cnab_pix(lote_boleto)
                    if arquivo_boleto:
                        c2.download_button(label=f"📥 Baixar Boleto ({len(lote_boleto)})", data=arquivo_boleto, file_name=f"CB{datetime.now().strftime('%d%m')}_BOLETO.txt")
        else:
            st.info("Selecione itens.")

    st.divider()
    if st.button("💾 Salvar na Planilha"):
        df_save = st.session_state['df_pagamentos'].copy()
        df_save['DATA_PAGAMENTO'] = df_save['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')
        conectar_sheets().update(worksheet="Pagamentos_Dia", data=df_save)
        st.toast("Salvo!", icon="✅")

# ABA 2: VISÃO CFO
with tab_cfo:
    df_dash = st.session_state['df_pagamentos'].copy()
    if df_dash.empty:
        st.info("Sem dados.")
    else:
        df_dash['DATA_PAGAMENTO'] = pd.to_datetime(df_dash['DATA_PAGAMENTO'])
        st.subheader("1. Visão de Liquidez")
        k1, k2, k3, k4 = st.columns(4)
        hoje = pd.Timestamp.now().normalize()
        tot_hoje = df_dash[df_dash['DATA_PAGAMENTO'] == hoje]['VALOR_PAGAMENTO'].sum()
        k1.metric("A Pagar Hoje", formatar_real(tot_hoje), delta="Pressão", delta_color="inverse")
        
        g1, g2 = st.columns([2, 1])
        with g1:
            df_fluxo = df_dash.groupby('DATA_PAGAMENTO')['VALOR_PAGAMENTO'].sum().reset_index()
            st.plotly_chart(px.bar(df_fluxo, x='DATA_PAGAMENTO', y='VALOR_PAGAMENTO', title="Cronograma"), use_container_width=True)
        with g2:
            df_top = df_dash.groupby('NOME_FAVORECIDO')['VALOR_PAGAMENTO'].sum().reset_index().sort_values('VALOR_PAGAMENTO', ascending=False).head(5)
            st.plotly_chart(px.bar(df_top, x='VALOR_PAGAMENTO', y='NOME_FAVORECIDO', orientation='h', title="Pareto"), use_container_width=True)

# ABA 3: RETORNO
with tab_retorno:
    st.header("🔄 Leitura de Retorno")
    up = st.file_uploader("Arquivo .RET", type=['ret', 'txt'])
    if up:
        try:
            df_ret = parse_cnab_retorno(up.getvalue())
            if not df_ret.empty:
                st.dataframe(df_ret, use_container_width=True)
            else: st.warning("Vazio.")
        except Exception as e: st.error(f"Erro: {e}")
