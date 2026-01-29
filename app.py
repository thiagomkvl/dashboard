import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata
import re

# ==========================================
# 0. CONFIGURAÇÃO E DADOS CADASTRAIS
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Sistema Financeiro", layout="wide", page_icon="🏥")

DADOS_HOSPITAL = {
    'cnpj': '85307098000187',      # CNPJ REAL ATUALIZADO
    'convenio': '000000000985597', # CONVÊNIO
    'ag': '1214',                  # AGÊNCIA
    'ag_dv': '0',
    'cc': '5886',                  # CONTA
    'cc_dv': '6',
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'endereco': 'RODOVIA SC 401',
    'num_end': '123',
    'complemento': 'SALA 01',
    'cidade': 'FLORIANOPOLIS',
    'cep': '88000000',
    'uf': 'SC'
}

# ==========================================
# 1. SISTEMA DE LOGIN
# ==========================================
def check_password():
    """Retorna True se o usuário logar corretamente."""
    def password_entered():
        if "password" in st.session_state:
            if st.session_state["password"] == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # Não manter senha na memória
            else:
                st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # Layout da Tela de Login
    st.markdown("<br><br><h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Gestão de Passivo & Pagamentos</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Senha de Acesso:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Senha incorreta")
    
    return False

# ==========================================
# 2. FUNÇÕES AUXILIARES E FORMATADORES
# ==========================================
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def limpar_ids(valor):
    if pd.isna(valor) or str(valor).strip() == "": return ""
    return "".join(filter(str.isalnum, str(valor).split('.')[0]))

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='l'):
    texto_str = remover_acentos(str(texto))
    if alinhar == 'r':
        texto_limpo = "".join(filter(str.isdigit, texto_str))
        if texto_limpo == "": texto_limpo = "0"
        res = texto_limpo[:tamanho].rjust(tamanho, '0')
    else:
        res = texto_str[:tamanho].ljust(tamanho, preenchimento)
    return res[:tamanho]

def identificar_tipo_pagamento(linha):
    dado = str(linha.get('CHAVE_PIX_OU_COD_BARRAS', ''))
    dado_limpo = "".join(filter(str.isdigit, dado))
    if len(dado_limpo) >= 44: return 'BOLETO'
    else: return 'PIX'

# ==========================================
# 3. MOTORES CNAB (PIX E BOLETO)
# ==========================================
def gerar_cnab_pix(df_sel, h):
    linhas = []
    hoje = datetime.now()
    BCO = "136"

    # Header Arquivo
    h0 = (f"{BCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000")
    linhas.append(h0[:240].ljust(240))
    
    # Header Lote (Pix)
    h1 = (f"{BCO}00011C2045046 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{' '*40}"
          f"{formatar_campo(h['endereco'],30)}{formatar_campo(h['num_end'],5,'0','r')}"
          f"{formatar_campo(h.get('complemento',' '),15)}{formatar_campo(h['cidade'],20)}"
          f"{formatar_campo(h['cep'],8,'0','r')}{formatar_campo(h['uf'],2)}01{' '*10}")
    linhas.append(h1[:240].ljust(240))
    
    reg_lote = 0
    for _, r in df_sel.reset_index(drop=True).iterrows():
        v_int = int(round(float(str(r['VALOR_PAGAMENTO']).replace(',','.')) * 100))
        try: data_pagto = pd.to_datetime(r['DATA_PAGAMENTO'], dayfirst=True).strftime('%d%m%Y')
        except: data_pagto = hoje.strftime('%d%m%Y')

        chave_pix = limpar_ids(r.get('CHAVE_PIX_OU_COD_BARRAS', ''))
        raw_pix = str(r.get('CHAVE_PIX_OU_COD_BARRAS', ''))
        tipo_chave = "05"
        if chave_pix or raw_pix:
            if "@" in raw_pix: tipo_chave = "02"
            elif len(chave_pix) == 11: tipo_chave = "03"
            elif len(chave_pix) == 14: tipo_chave = "03"
            elif len(chave_pix) > 20: tipo_chave = "04"
            else: tipo_chave = "01"

        banco_fav = r.get('BANCO_FAVORECIDO', '') or "000"
        ag_fav = r.get('AGENCIA_FAVORECIDA', '') or "0"
        cc_fav = r.get('CONTA_FAVORECIDA', '')
        dv_cc_fav = r.get('DIGITO_CONTA_FAVORECIDA', '') or "0"
        if not cc_fav or cc_fav == "" or int(limpar_ids(cc_fav) or 0) == 0: cc_fav = "1"

        # Segmento A
        reg_lote += 1
        segA = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}A000009{formatar_campo(banco_fav,3,'0','r')}"
                f"{formatar_campo(ag_fav,5,'0','r')}{formatar_campo(' ',1)}"
                f"{formatar_campo(cc_fav,12,'0','r')}{formatar_campo(dv_cc_fav,1,'0','r')}"
                f"{formatar_campo(' ',1)}{formatar_campo(r['NOME_FAVORECIDO'],30)}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}{data_pagto}BRL{'0'*15}{formatar_campo(v_int,15,'0','r')}"
                f"{' '*20}{'0'*8}{'0'*15}{' '*40}{' '*2}{' '*10}0{' '*10}")
        linhas.append(segA[:240].ljust(240))
        
        # Segmento B
        reg_lote += 1
        doc_fav = limpar_ids(r.get('cnpj_beneficiario', ''))
        tipo_insc = "1" if len(doc_fav) == 11 else "2"
        segB = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{formatar_campo(tipo_chave,3,'0','r')}" 
                f"{tipo_insc}{formatar_campo(doc_fav,14,'0','r')}"
                f"{formatar_campo('ENDERECO NAO INFORMADO',35)}{' '*60}"
                f"{formatar_campo(chave_pix,99)}{' '*6}{'0'*8}")
        linhas.append(segB[:240].ljust(240))
        
    reg_lote += 1
    v_total = int(round(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100))
    t5 = (f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total,18,'0','r')}"
          f"{'0'*18}{'0'*6}{' '*165}{' '*10}")
    linhas.append(t5[:240].ljust(240))
    t9 = f"{BCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    return "\r\n".join(linhas)

def gerar_cnab_boleto(df_sel, h):
    linhas = []
    hoje = datetime.now()
    BCO = "136"

    # Header Arquivo
    h0 = (f"{BCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000")
    linhas.append(h0[:240].ljust(240))
    
    # Header Lote (Boleto)
    h1 = (f"{BCO}00011C2031030 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{' '*40}"
          f"{formatar_campo(h['endereco'],30)}{formatar_campo(h['num_end'],5,'0','r')}"
          f"{formatar_campo(h.get('complemento',' '),15)}{formatar_campo(h['cidade'],20)}"
          f"{formatar_campo(h['cep'],8,'0','r')}{formatar_campo(h['uf'],2)}{' '*18}")
    linhas.append(h1[:240].ljust(240))
    
    reg_lote = 0
    for _, r in df_sel.reset_index(drop=True).iterrows():
        v_int = int(round(float(str(r['VALOR_PAGAMENTO']).replace(',','.')) * 100))
        try: data_pagto = pd.to_datetime(r['DATA_PAGAMENTO'], dayfirst=True).strftime('%d%m%Y')
        except: data_pagto = hoje.strftime('%d%m%Y')

        cod_barras = "".join(filter(str.isdigit, str(r.get('CHAVE_PIX_OU_COD_BARRAS', ''))))
        if len(cod_barras) > 44: cod_barras = cod_barras[:44]

        # Segmento J
        reg_lote += 1
        segJ = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}J000"
                f"{formatar_campo(cod_barras,44,'0','r')}"
                f"{formatar_campo(r['NOME_FAVORECIDO'],30)}"
                f"{data_pagto}"
                f"{formatar_campo(v_int,15,'0','r')}"
                f"{formatar_campo(0,15,'0','r')}"
                f"{formatar_campo(0,15,'0','r')}"
                f"{data_pagto}"
                f"{formatar_campo(v_int,15,'0','r')}"
                f"{'0'*15}{' '*20}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}"
                f"09{' '*6}{' '*10}")
        linhas.append(segJ[:240].ljust(240))

    reg_lote += 1
    v_total = int(round(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100))
    t5 = (f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total,18,'0','r')}"
          f"{'0'*18}{'0'*6}{' '*165}{' '*10}")
    linhas.append(t5[:240].ljust(240))
    t9 = f"{BCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    return "\r\n".join(linhas)

# ==========================================
# 4. APLICAÇÃO PRINCIPAL (Fluxo de Navegação)
# ==========================================
if check_password():
    conn = conectar_sheets()
    
    # Menu Lateral
    st.sidebar.title("Navegação")
    aba = st.sidebar.radio(
        "Selecione o módulo:", 
        ["📊 Dashboard Gerencial", "🎛️ Cockpit Operacional", "📂 Upload da Base"]
    )
    st.sidebar.divider()
    if st.sidebar.button("🔒 Sair do Sistema"):
        st.session_state["password_correct"] = False
        st.rerun()

    # ----------------------------------------
    # MÓDULO 1: DASHBOARD GERENCIAL
    # ----------------------------------------
    if aba == "📊 Dashboard Gerencial":
        try:
            df_hist = conn.read(worksheet="Historico", ttl=300)
            if not df_hist.empty:
                # Tratamento de dados
                df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
                ultima_data = df_hist['data_processamento'].max()
                df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()
                
                # Cálculos ABC
                df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
                total_hoje = df_abc['Saldo_Limpo'].sum()
                df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
                df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A (80%)' if x <= 0.8 else ('Classe B (15%)' if x <= 0.95 else 'Classe C (5%)'))
                df_hoje = df_hoje.merge(df_abc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

                # Cabeçalho do Dashboard
                st.title("📊 Dashboard Gerencial")
                st.caption(f"Visão analítica do passivo em {ultima_data}")
                
                m1, m2, m3, m4 = st.columns(4)
                total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
                m1.metric("Dívida Total", formatar_real(total_hoje))
                m2.metric("Total Vencido", formatar_real(total_vencido), delta_color="inverse")
                m3.metric("Fornecedores Ativos", len(df_hoje['Beneficiario'].unique()))
                m4.metric("Processamento", ultima_data)

                st.divider()
                
                # Gráficos
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Curva ABC de Fornecedores")
                    fig_abc = px.pie(df_hoje, values='Saldo_Limpo', names='Classe ABC', hole=0.4, 
                                     color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
                    st.plotly_chart(fig_abc, use_container_width=True)
                with c2:
                    st.subheader("Ageing List (Vencimentos)")
                    ordem_ageing = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                    df_bar = df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem_ageing).reset_index().fillna(0)
                    fig_bar = px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s')
                    st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()
                st.subheader("📅 Radar de Pagamentos Futuros")
                df_hoje['Venc_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
                df_futuro = df_hoje[df_hoje['Venc_DT'] >= pd.Timestamp.now().normalize()].copy()
                
                if not df_futuro.empty:
                    df_futuro['Mes_Ref'] = df_futuro['Venc_DT'].dt.strftime('%m/%Y')
                    meses_disponiveis = sorted(df_futuro['Mes_Ref'].unique())
                    mes_sel = st.selectbox("Filtrar Mês de Vencimento:", meses_disponiveis)
                    
                    df_mes = df_futuro[df_futuro['Mes_Ref'] == mes_sel].sort_values('Venc_DT')
                    df_mes['Data_F'] = df_mes['Venc_DT'].dt.strftime('%d/%m/%Y')
                    
                    fig_radar = px.bar(df_mes, x='Data_F', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=500)
                    # Anotações de totais
                    df_totais = df_mes.groupby('Data_F')['Saldo_Limpo'].sum().reset_index()
                    for i, row in df_totais.iterrows():
                        fig_radar.add_annotation(x=row['Data_F'], y=row['Saldo_Limpo'], text=f"<b>{formatar_real(row['Saldo_Limpo'])}</b>", showarrow=False, yshift=10)
                    
                    st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.info("A base de histórico está vazia. Faça o upload na aba correspondente.")
        except Exception as e:
            st.error(f"Erro ao carregar Dashboard: {e}")

    # ----------------------------------------
    # MÓDULO 2: COCKPIT OPERACIONAL
    # ----------------------------------------
    elif aba == "🎛️ Cockpit Operacional":
        st.title("🎛️ Cockpit de Pagamentos")
        st.caption("Central de geração de remessas CNAB 240 (Pix e Boletos)")

        # Carregar/Inicializar Sessão
        if 'df_pagamentos' not in st.session_state:
            try:
                df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
                if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                # Garante colunas
                req_cols = ['CHAVE_PIX_OU_COD_BARRAS', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA']
                for c in req_cols:
                    if c not in df_p.columns: df_p[c] = ""
                # Migração legado
                if 'CHAVE_PIX' in df_p.columns and df_p['CHAVE_PIX_OU_COD_BARRAS'].all() == "":
                    df_p['CHAVE_PIX_OU_COD_BARRAS'] = df_p['CHAVE_PIX']
                
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                st.session_state['df_pagamentos'] = df_p
            except: 
                st.session_state['df_pagamentos'] = pd.DataFrame()

        # Formulário de Inserção
        with st.expander("➕ Adicionar Pagamento Manualmente", expanded=False):
            with st.form("form_novo", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                fn = c1.text_input("Fornecedor / Beneficiário")
                fv = c2.number_input("Valor (R$)", min_value=0.01, format="%.2f")
                fd = c3.date_input("Vencimento", datetime.now())
                
                c4, c5 = st.columns([2, 1])
                cod = c4.text_input("Chave PIX ou Código de Barras (Boleto)", help="Cole aqui a Chave Pix ou o Código de Barras")
                fc = c5.text_input("CNPJ/CPF Beneficiário")
                
                st.markdown("**Dados Bancários (Opcional se tiver Chave Pix/Boleto):**")
                cb1, cb2, cb3, cb4 = st.columns(4)
                fb = cb1.text_input("Banco")
                fa = cb2.text_input("Agência")
                fcc = cb3.text_input("Conta")
                fdg = cb4.text_input("DV")
                
                if st.form_submit_button("Adicionar à Lista"):
                    novo = pd.DataFrame([{
                        'Pagar?': True, 'NOME_FAVORECIDO': fn, 'VALOR_PAGAMENTO': fv, 
                        'DATA_PAGAMENTO': fd.strftime('%d/%m/%Y'), 'cnpj_beneficiario': fc,
                        'CHAVE_PIX_OU_COD_BARRAS': cod, 'BANCO_FAVORECIDO': fb, 
                        'AGENCIA_FAVORECIDA': fa, 'CONTA_FAVORECIDA': fcc, 'DIGITO_CONTA_FAVORECIDA': fdg
                    }])
                    st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], novo], ignore_index=True)
                    st.rerun()

        # Tabela Principal
        if not st.session_state['df_pagamentos'].empty:
            df_display = st.session_state['df_pagamentos'].copy()
            df_display['Tipo'] = df_display.apply(identificar_tipo_pagamento, axis=1)
            
            st.write("### 📋 Checklist de Pagamentos")
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
            
            # Painel de Geração
            df_pagar = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True].copy()
            
            if not df_pagar.empty:
                df_pagar['TIPO_DETECTADO'] = df_pagar.apply(identificar_tipo_pagamento, axis=1)
                lote_pix = df_pagar[df_pagar['TIPO_DETECTADO'] == 'PIX']
                lote_boleto = df_pagar[df_pagar['TIPO_DETECTADO'] == 'BOLETO']
                
                col_info, col_download = st.columns([1, 1])
                
                with col_info:
                    st.info(f"""
                    **Resumo do Lote:**
                    \n💰 Total Selecionado: **{formatar_real(df_pagar['VALOR_PAGAMENTO'].sum())}**
                    \n⚡ Pix: {len(lote_pix)} itens | 📄 Boletos: {len(lote_boleto)} itens
                    """)
                
                with col_download:
                    if not lote_pix.empty:
                        st.download_button(
                            label=f"⬇️ Baixar Remessa PIX ({len(lote_pix)})",
                            data=gerar_cnab_pix(lote_pix, DADOS_HOSPITAL),
                            file_name=f"REM_PIX_{datetime.now().strftime('%d%m_%H%M')}.txt",
                            mime="text/plain"
                        )
                    
                    if not lote_boleto.empty:
                        st.download_button(
                            label=f"⬇️ Baixar Remessa BOLETOS ({len(lote_boleto)})",
                            data=gerar_cnab_boleto(lote_boleto, DADOS_HOSPITAL),
                            file_name=f"REM_BOLETO_{datetime.now().strftime('%d%m_%H%M')}.txt",
                            mime="text/plain"
                        )
            else:
                st.warning("Selecione pelo menos um item na tabela para gerar a remessa.")

            st.divider()
            c_save, c_refresh = st.columns(2)
            if c_save.button("💾 Salvar Estado na Planilha"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.toast("Dados salvos com sucesso!", icon="✅")
            
            if c_refresh.button("🔄 Recarregar Tabela"):
                del st.session_state['df_pagamentos']
                st.rerun()
        else:
            st.info("Nenhum pagamento pendente na lista.")

    # ----------------------------------------
    # MÓDULO 3: UPLOAD
    # ----------------------------------------
    elif aba == "📂 Upload da Base":
        st.title("📂 Upload de Dados")
        st.markdown("Atualize a base histórica de contas a pagar aqui.")
        
        up = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])
        if up and st.button("Processar Arquivo"):
            with st.spinner("Processando..."):
                try:
                    df_new = pd.read_excel(up)
                    if salvar_no_historico(df_new): 
                        st.success("✅ Base de dados atualizada com sucesso!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar arquivo: {e}")
