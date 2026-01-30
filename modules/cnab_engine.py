from datetime import datetime
import pandas as pd
from modules.utils import formatar_campo, limpar_ids

# DADOS CADASTRAIS (Confirme se o CNPJ está correto)
DADOS_HOSPITAL = {
    'cnpj': '85307098000187',
    'convenio': '000000000985597',
    'ag': '1214', 'ag_dv': '0',
    'cc': '5886', 'cc_dv': '6',
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'endereco': 'RODOVIA SC 401', 'num_end': '123',
    'complemento': 'SALA 01', 'cidade': 'FLORIANOPOLIS',
    'cep': '88000000', 'uf': 'SC'
}

def gerar_cnab_pix(df_sel, h=DADOS_HOSPITAL):
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

        banco_fav = limpar_ids(r.get('BANCO_FAVORECIDO', '')) or "000"
        ag_fav = limpar_ids(r.get('AGENCIA_FAVORECIDA', '')) or "0"
        cc_fav = limpar_ids(r.get('CONTA_FAVORECIDA', ''))
        dv_cc_fav = limpar_ids(r.get('DIGITO_CONTA_FAVORECIDA', '')) or "0"
        if not cc_fav or cc_fav == "0": cc_fav = "1"

        # SEGMENTO A
        reg_lote += 1
        segA = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}A000009{formatar_campo(banco_fav,3,'0','r')}"
                f"{formatar_campo(ag_fav,5,'0','r')}{formatar_campo(' ',1)}"
                f"{formatar_campo(cc_fav,12,'0','r')}{formatar_campo(dv_cc_fav,1,'0','r')}"
                f"{formatar_campo(' ',1)}{formatar_campo(r['NOME_FAVORECIDO'],30)}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}{data_pagto}BRL{'0'*15}{formatar_campo(v_int,15,'0','r')}"
                f"{' '*20}{'0'*8}{'0'*15}{' '*40}{' '*2}{' '*10}0{' '*10}")
        linhas.append(segA[:240].ljust(240))
        
        # SEGMENTO B (CORREÇÃO DO ERRO DE VALIDAÇÃO)
        reg_lote += 1
        
        # Limpa o documento. Se vier vazio, coloca Zeros (não coloque 1)
        doc_fav = limpar_ids(r.get('cnpj_beneficiario', ''))
        if not doc_fav: doc_fav = "00000000000"
        
        tipo_insc = "2" # CNPJ
        if len(doc_fav) <= 11: tipo_insc = "1" # CPF
        
        segB = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{formatar_campo(tipo_chave,3,'0','r')}" 
                f"{tipo_insc}{formatar_campo(doc_fav,14,'0','r')}" # <-- CORREÇÃO AQUI
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

def gerar_cnab_boleto(df_sel, h=DADOS_HOSPITAL):
    linhas = []
    hoje = datetime.now()
    BCO = "136"

    h0 = (f"{BCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000")
    linhas.append(h0[:240].ljust(240))
    
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

        # Limpeza agressiva para garantir que só fiquem números
        cod_barras = "".join(filter(str.isdigit, str(r.get('CHAVE_PIX_OU_COD_BARRAS', ''))))
        if len(cod_barras) > 44: cod_barras = cod_barras[:44]

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
