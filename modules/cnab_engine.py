from datetime import datetime
import pandas as pd
from modules.utils import formatar_campo, limpar_ids, identificar_tipo_pagamento

# ==========================================
# DADOS CADASTRAIS (SOS CARDIO)
# ==========================================
DADOS_HOSPITAL = {
    'cnpj': '85307098000187',       
    'convenio': '000000000985597', 
    'ag': '1214',                   
    'ag_dv': '0',
    'cc': '5886',                   
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
# MOTOR PIX (DINÂMICO COM SEQUENCIAL)
# ==========================================
# ADICIONADO O PARÂMETRO nsa=1
def gerar_cnab_pix(df_input, h=DADOS_HOSPITAL, nsa=1):
    # 1. FILTRO: Processa apenas PIX
    df_sel = df_input.copy()
    df_sel['TIPO_TEMP'] = df_sel.apply(identificar_tipo_pagamento, axis=1)
    df_sel = df_sel[df_sel['TIPO_TEMP'] == 'PIX'] 
    
    if df_sel.empty: return None

    linhas = []
    hoje = datetime.now()
    BCO = "136" # Unicred

    # ------------------------------------------------------------------
    # HEADER DE ARQUIVO (AGORA USA O nsa DINÂMICO)
    # ------------------------------------------------------------------
    h0 = (f"{BCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1"
          f"{hoje.strftime('%d%m%Y%H%M%S')}"
          f"{formatar_campo(nsa, 6, '0', 'r')}" # <--- AQUI MUDOU: Usa o número sequencial informado
          f"10300000")
    linhas.append(h0[:240].ljust(240))
    
    # Header Lote (Pix = 45)
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

        raw_pix = str(r.get('CHAVE_PIX_OU_COD_BARRAS', '')).strip()
        
        # Detecção Tipo Chave
        tipo_chave_pix = "05" 
        if "@" in raw_pix: tipo_chave_pix = "04"
        elif raw_pix.isdigit() and len(raw_pix) == 11: tipo_chave_pix = "01"
        elif raw_pix.isdigit() and len(raw_pix) == 14: tipo_chave_pix = "02"
        elif "+" in raw_pix or (raw_pix.isdigit() and len(raw_pix) in [12, 13]): tipo_chave_pix = "03"

        # FORÇA DADOS BANCÁRIOS ZERADOS (Segurança Anti-TED)
        banco_fav = "000"; ag_fav = "0"; cc_fav = "0"; dv_cc_fav = "0"

        # SEGMENTO A
        reg_lote += 1
        segA = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}A000009{formatar_campo(banco_fav,3,'0','r')}"
                f"{formatar_campo(ag_fav,5,'0','r')}{formatar_campo(' ',1)}"
                f"{formatar_campo(cc_fav,12,'0','r')}{formatar_campo(dv_cc_fav,1,'0','r')}"
                f"{formatar_campo(' ',1)}{formatar_campo(r['NOME_FAVORECIDO'],30)}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}{data_pagto}BRL{'0'*15}{formatar_campo(v_int,15,'0','r')}"
                f"{' '*20}{'0'*8}{'0'*15}{' '*40}{' '*2}{' '*10}0{' '*10}")
        linhas.append(segA[:240].ljust(240))
        
        # SEGMENTO B
        reg_lote += 1
        tipo_insc = "0"; doc_fav_final = "0" * 14
        
        segB = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{' '*3}"  
                f"{tipo_insc}{formatar_campo(doc_fav_final,14,'0','r')}"   
                f"{formatar_campo('ENDERECO NAO INFORMADO',30)}"           
                f"{' '*5}{' '*15}{' '*20}{' '*20}{'0'*8}{' '*2}"           
                f"{' '*93}"                                                
                f"{tipo_chave_pix}"                                        # 226-227
                f"{formatar_campo(raw_pix, 77, ' ', 'l')}"                 # 228-304
                f"{' '*10}")                                               
        linhas.append(segB) # Sem corte para permitir chave estendida
        
    reg_lote += 1
    v_total = int(round(df_sel['VALOR_PAGAMENTO'].astype(float).sum() * 100))
    t5 = (f"{BCO}00015{' '*9}{formatar_campo(reg_lote,6,'0','r')}{formatar_campo(v_total,18,'0','r')}"
          f"{'0'*18}{'0'*6}{' '*165}{' '*10}")
    linhas.append(t5[:240].ljust(240))
    
    t9 = f"{BCO}99999{' '*9}000001{formatar_campo(len(linhas)+1,6,'0','r')}{' '*205}"
    linhas.append(t9[:240].ljust(240))
    return "\r\n".join(linhas)

# ==========================================
# MOTOR BOLETO (TAMBÉM ATUALIZADO COM NSA)
# ==========================================
def gerar_cnab_boleto(df_input, h=DADOS_HOSPITAL, nsa=1):
    df_sel = df_input.copy()
    df_sel['TIPO_TEMP'] = df_sel.apply(identificar_tipo_pagamento, axis=1)
    df_sel = df_sel[df_sel['TIPO_TEMP'] == 'BOLETO'] 
    
    if df_sel.empty: return None

    linhas = []
    hoje = datetime.now()
    BCO = "136"

    # Header Arquivo com NSA Dinâmico
    h0 = (f"{BCO}00000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{formatar_campo('UNICRED',30)}{' '*10}1"
          f"{hoje.strftime('%d%m%Y%H%M%S')}"
          f"{formatar_campo(nsa, 6, '0', 'r')}" # <--- NSA AQUI TAMBÉM
          f"10300000")
    linhas.append(h0[:240].ljust(240))
    
    # ... (Restante do código de boleto continua igual, sem alterações lógicas)
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
