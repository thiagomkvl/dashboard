import streamlit as st
import pandas as pd
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata
import re

# ==========================================
# 0. DADOS CADASTRAIS (SOS CARDIO)
# CNPJ JÁ ATUALIZADO
# ==========================================
DADOS_HOSPITAL = {
    'cnpj': '85307098000187',      # CNPJ REAL ATUALIZADO
    'convenio': '000000000985597', # SEU CONVÊNIO
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
# 1. CONFIGURAÇÃO E FUNÇÕES
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Cockpit Financeiro", layout="wide")

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
    if len(dado_limpo) >= 44:
        return 'BOLETO'
    else:
        return 'PIX'

# ==========================================
# 2. MOTOR CNAB - PIX (Layout 045)
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
    
    # Header Lote (Pix = 45)
    # Nota: Pix usa '01' nas posições 223-224 (Forma Lancamento/Servico) e espaços no final
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
        
    # Trailer Lote (Pix)
    reg_lote += 1
    v_total = int(round(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100))
    # Ajuste preciso de espaços para fechar 240
    # 41 chars fixos iniciais + 199 de finalização (18 zeros + 6 zeros + 165 brancos + 10 brancos)
    t5 = (f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total,18,'0','r')}"
          f"{'0'*18}{'0'*6}{' '*165}{' '*10}")
    linhas.append(t5[:240].ljust(240))
    
    t9 = f"{BCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    
    return "\r\n".join(linhas)

# ==========================================
# 3. MOTOR CNAB - BOLETOS (Layout 031 - Seg J)
# ==========================================
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
    
    # Header Lote (31 = Pagamento Títulos Outros Bancos)
    # CORREÇÃO CRÍTICA: Fim da linha com espaços (Pos 223-240) em vez de '01'
    h1 = (f"{BCO}00011C2031030 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{' '*40}"
          f"{formatar_campo(h['endereco'],30)}{formatar_campo(h['num_end'],5,'0','r')}"
          f"{formatar_campo(h.get('complemento',' '),15)}{formatar_campo(h['cidade'],20)}"
          f"{formatar_campo(h['cep'],8,'0','r')}{formatar_campo(h['uf'],2)}"
          f"{' '*18}") # FIX: 223-240 (Espaços em branco, remove o '01')
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
                f"{'0'*15}"
                f"{' '*20}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}"
                f"09" # Moeda Real (223-224)
                f"{' '*6}{' '*10}") # Espaços finais (225-240)
        linhas.append(segJ[:240].ljust(240))

    # Trailer Lote (Boleto)
    # CORREÇÃO CRÍTICA: Ajuste exato dos campos CNAB (espaços) e Zeros
    reg_lote += 1
    v_total = int(round(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100))
    t5 = (f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total,18,'0','r')}"
          f"{'0'*18}{'0'*6}{' '*165}{' '*10}") # 18(QtdMoeda)+6(Aviso)+165(CNAB)+10(Ocorrencias)
    linhas.append(t5[:240].ljust(240))
    
    t9 = f"{BCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    
    return "\r\n".join(linhas)

# ==========================================
# 4. INTERFACE COCKPIT
# ==========================================
if 'df_pagamentos' not in st.session_state:
    try:
        df_p = conectar_sheets().read(worksheet="Pagamentos_Dia", ttl=0)
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

aba = st.sidebar.radio("Navegação:", ["Cockpit Financeiro", "Upload de Base"])

if aba == "Cockpit Financeiro":
    st.title("🎛️ Cockpit de Pagamentos - SOS CARDIO")
    
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
        col_resumo, col_botoes = st.columns([1, 2])
        df_pagar = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True].copy()
        
        if not df_pagar.empty:
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
                    c_btn1.download_button(f"Baixar Lote PIX ({len(lote_pix)})", gerar_cnab_pix(lote_pix, DADOS_HOSPITAL), f"REM_PIX_{datetime.now().strftime('%d%m')}.txt")
                if not lote_boleto.empty:
                    c_btn2.download_button(f"Baixar Lote BOLETOS ({len(lote_boleto)})", gerar_cnab_boleto(lote_boleto, DADOS_HOSPITAL), f"REM_BOLETO_{datetime.now().strftime('%d%m')}.txt")
        else: st.info("Selecione itens na tabela.")

    st.divider()
    if st.button("💾 Salvar Alterações"):
        conectar_sheets().update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
        st.toast("Salvo!", icon="✅")

elif aba == "Upload de Base":
    st.title("📂 Upload"); up = st.file_uploader("Arquivo .xlsx", type=["xlsx"])
    if up and st.button("Processar"):
        if salvar_no_historico(pd.read_excel(up)): st.success("Atualizado!"); st.rerun()
