import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import conectar_sheets

# --- IMPORTAÇÃO SEGURA DAS FUNÇÕES ---
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
# 1. CARGA DE DADOS BLINDADA (Lógica Robusta do Excel)
# ==============================================================================
if 'df_pagamentos' not in st.session_state:
    try:
        conn = conectar_sheets()
        df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
        
        # Garante estrutura mínima se vier vazia
        if df_p.empty:
            df_p = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX_OU_COD_BARRAS', 'cnpj_beneficiario'])
            
        if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
        
        # Unifica colunas de pagamento (Lógica de Chave)
        if 'CHAVE_PIX_OU_COD_BARRAS' not in df_p.columns: 
            if 'CHAVE_PIX' in df_p.columns: 
                df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX']
            else: 
                df_p['CHAVE_PIX_OU_COD_BARRAS'] = ""
        
        # Normalização de nomes para garantir compatibilidade
        if 'CNPJ' in df_p.columns and 'cnpj_beneficiario' not in df_p.columns:
            df_p.rename(columns={'CNPJ': 'cnpj_beneficiario'}, inplace=True)

        # --- CORREÇÃO DE TIPAGEM INICIAL ---
        df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
        
        # Tratamento de Valor (Vírgula para Ponto)
        if 'VALOR_PAGAMENTO' in df_p.columns:
            df_p['VALOR_PAGAMENTO'] = pd.to_numeric(
                df_p['VALOR_PAGAMENTO'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            ).fillna(0.0)
            
        # Tratamento de Data
        df_p['DATA_PAGAMENTO'] = pd.to_datetime(df_p['DATA_PAGAMENTO'], dayfirst=True, errors='coerce')
        
        # Força Chave Pix para texto (evita erro de float no editor)
        # Isso resolve o problema de 'nan' e chaves numéricas quebradas
        df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX_OU_COD_BARRAS'].astype(str).replace('nan', '').replace('None', '')
        
        # Se for numérica pura, remove o .0 (ex: "123.0" -> "123")
        df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX_OU_COD_BARRAS'].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
        
        st.session_state['df_pagamentos'] = df_p
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        st.session_state['df_pagamentos'] = pd.DataFrame()

# ==============================================================================
# NAVEGAÇÃO ENTRE VISÕES
# ==============================================================================
tab_operacional, tab_cfo, tab_retorno = st.tabs(["📝 Operacional (Mesa)", "📊 Visão CFO", "🔄 Processar Retorno"])

# ==============================================================================
# ABA 1: OPERACIONAL (CADASTRO E GERAÇÃO)
# ==============================================================================
with tab_operacional:
    
    # --- FORMULÁRIO DE INSERÇÃO ---
    with st.expander("➕ Inserir Novo Título Manualmente", expanded=False):
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

    # --- TABELA PRINCIPAL ---
    st.subheader("Lista de Pagamentos do Dia")

    if not st.session_state['df_pagamentos'].empty:
        df_display = st.session_state['df_pagamentos'].copy()
        
        # --- BLINDAGEM PARA EXIBIÇÃO ---
        # Formata data para string bonita na tabela (DD/MM/AAAA)
        df_display['DATA_VISUAL'] = df_display['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')

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
                    "DATA_VISUAL": st.column_config.TextColumn("Vencimento", disabled=True), # Edição de data é complexa, melhor bloquear visual
                    "CHAVE_PIX_OU_COD_BARRAS": st.column_config.TextColumn("Chave/Código", width="medium"),
                    "DATA_PAGAMENTO": None # Oculta a coluna original datetime
                }
            )
            
            # Atualiza estado se houver edição
            if not edited_df.equals(df_display):
                # Recupera as colunas originais e ignora as auxiliares (Tipo, Data Visual)
                colunas_reais = [c for c in st.session_state['df_pagamentos'].columns]
                st.session_state['df_pagamentos'].update(edited_df[colunas_reais])
                # Nota: update funciona bem se o índice não mudou. Se adicionar linhas, melhor recarregar.

        except Exception as e:
            st.error(f"Erro ao renderizar tabela: {e}")
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
                total = df_pagar['VALOR_PAGAMENTO'].sum()
                st.metric("Total a Pagar", formatar_real(total))
                st.caption(f"Pix: {len(lote_pix)} | Boletos: {len(lote_boleto)}")
            
            with col_botoes:
                st.write("### 🚀 Gerar Remessa (CNAB 240)")
                c_btn1, c_btn2 = st.columns(2)
                
                # Prepara data para string DD/MM/AAAA para o motor CNAB
                if not lote_pix.empty:
                    lote_pix['DATA_PAGAMENTO'] = lote_pix['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')
                    arquivo_pix = gerar_cnab_pix(lote_pix)
                    if arquivo_pix:
                        c_btn1.download_button(
                            label=f"📥 Baixar PIX ({len(lote_pix)})", 
                            data=arquivo_pix, 
                            file_name=f"CB{datetime.now().strftime('%d%m')}_PIX.txt",
                            mime="text/plain"
                        )
                
                if not lote_boleto.empty:
                    lote_boleto['DATA_PAGAMENTO'] = lote_boleto['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')
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
    if st.button("💾 Salvar na Planilha Google Sheets"):
        # Converte Data de volta para string para o Sheets não quebrar
        df_to_save = st.session_state['df_pagamentos'].copy()
        df_to_save['DATA_PAGAMENTO'] = df_to_save['DATA_PAGAMENTO'].dt.strftime('%d/%m/%Y')
        conectar_sheets().update(worksheet="Pagamentos_Dia", data=df_to_save)
        st.toast("Dados salvos no Google Sheets!", icon="✅")

# ==============================================================================
# ABA 2: VISÃO CFO (ESTRATÉGIA)
# ==============================================================================
with tab_cfo:
    df_dash = st.session_state['df_pagamentos'].copy()
    if df_dash.empty:
        st.info("Sem dados para análise financeira.")
    else:
        # Garante datas
        df_dash['DATA_PAGAMENTO'] = pd.to_datetime(df_dash['DATA_PAGAMENTO'])
        
        st.subheader("1. Visão de Liquidez & Pressão de Caixa")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        hoje = pd.Timestamp.now().normalize()
        total_hoje = df_dash[df_dash['DATA_PAGAMENTO'] == hoje]['VALOR_PAGAMENTO'].sum()
        total_semana = df_dash[(df_dash['DATA_PAGAMENTO'] >= hoje) & (df_dash['DATA_PAGAMENTO'] <= hoje + timedelta(days=7))]['VALOR_PAGAMENTO'].sum()
        ticket_medio = df_dash['VALOR_PAGAMENTO'].mean()
        maior_boleto = df_dash['VALOR_PAGAMENTO'].max()
        
        kpi1.metric("A Pagar Hoje", formatar_real(total_hoje), delta="Pressão Imediata", delta_color="inverse")
        kpi2.metric("Projeção 7 Dias", formatar_real(total_semana))
        kpi3.metric("Ticket Médio", formatar_real(ticket_medio))
        kpi4.metric("Maior Exposição", formatar_real(maior_boleto))
        
        st.divider()

        # Gráficos
        g1, g2 = st.columns([2, 1])
        with g1:
            st.markdown("#### 📅 Cronograma de Desembolso")
            df_fluxo = df_dash.groupby('DATA_PAGAMENTO')['VALOR_PAGAMENTO'].sum().reset_index()
            fig_fluxo = px.bar(df_fluxo, x='DATA_PAGAMENTO', y='VALOR_PAGAMENTO', text_auto='.2s', color_discrete_sequence=['#CD5C5C'])
            st.plotly_chart(fig_fluxo, use_container_width=True)
            
        with g2:
            st.markdown("#### 🏦 Pareto (Top 5)")
            df_conc = df_dash.groupby('NOME_FAVORECIDO')['VALOR_PAGAMENTO'].sum().reset_index().sort_values('VALOR_PAGAMENTO', ascending=False).head(5)
            fig_conc = px.bar(df_conc, x='VALOR_PAGAMENTO', y='NOME_FAVORECIDO', orientation='h', color='VALOR_PAGAMENTO', color_continuous_scale='Reds')
            st.plotly_chart(fig_conc, use_container_width=True)

# ==============================================================================
# ABA 3: PROCESSAR RETORNO (Conciliação)
# ==============================================================================
with tab_retorno:
    st.header("🔄 Leitura de Retorno Bancário")
    st.markdown("Faça upload do arquivo `.RET` enviado pela Unicred para conferir os pagamentos.")
    
    uploaded_file = st.file_uploader("Escolha o arquivo de retorno", type=['ret', 'txt'])
    
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            df_retorno = parse_cnab_retorno(bytes_data)
            
            if not df_retorno.empty:
                total_pago = df_retorno[df_retorno['Status'].str.contains("Liquidado|Processado", case=False)]['Valor Pago'].sum()
                qtd_erros = df_retorno[df_retorno['Status'].str.contains("Rejeitado", case=False)].shape[0]
                
                m1, m2 = st.columns(2)
                m1.metric("Total Confirmado", formatar_real(total_pago))
                m2.metric("Rejeições/Erros", qtd_erros, delta_color="inverse")
                
                st.dataframe(df_retorno, use_container_width=True)
            else:
                st.warning("Nenhum registro encontrado.")
                
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
