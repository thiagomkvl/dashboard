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
# MOTOR PIX (CORRIGIDO E BLINDADO)
# ==========================================
def gerar_cnab_pix(df_input, h=DADOS_HOSPITAL):
    # 1. FILTRO: Processa apenas o que NÃO for Boleto
    df_sel = df_input.copy()
    df_sel['TIPO_TEMP'] = df_sel.apply(identificar_tipo_pagamento, axis=1)
    df_sel = df_sel[df_sel['TIPO_TEMP'] == 'PIX'] 
    
    if df_sel.empty: return None

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
        
        # Identificação Tipo Chave (Apenas logico)
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
        
        # VACINA DE CONTA (Obrigatória para Pix passar no Segmento A)
        if not cc_fav or cc_fav == "" or int(limpar_ids(cc_fav) or 0) == 0: cc_fav = "1"

        # ------------------------------------------------------------------
        # SEGMENTO A (Detalhe do Pagamento)
        # ------------------------------------------------------------------
        reg_lote += 1
        segA = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}A000009{formatar_campo(banco_fav,3,'0','r')}"
                f"{formatar_campo(ag_fav,5,'0','r')}{formatar_campo(' ',1)}"
                f"{formatar_campo(cc_fav,12,'0','r')}{formatar_campo(dv_cc_fav,1,'0','r')}"
                f"{formatar_campo(' ',1)}{formatar_campo(r['NOME_FAVORECIDO'],30)}"
                f"{formatar_campo(r.get('Nr. Titulo',''),20)}{data_pagto}BRL{'0'*15}{formatar_campo(v_int,15,'0','r')}"
                f"{' '*20}{'0'*8}{'0'*15}{' '*40}{' '*2}{' '*10}0{' '*10}")
        linhas.append(segA[:240].ljust(240))
        
        # ------------------------------------------------------------------
        # SEGMENTO B (Dados Complementares - ONDE OCORRIA O ERRO)
        # ------------------------------------------------------------------
        reg_lote += 1
        
        raw_doc = limpar_ids(r.get('cnpj_beneficiario', ''))
        
        # LÓGICA DE OURO PARA CORRIGIR ERRO UNICRED:
        # 1. Se for vazio, ou "1", ou muito pequeno -> TIPO 0 (Isento) e ZEROS.
        if not raw_doc or raw_doc == "1" or raw_doc == "0" or len(raw_doc) < 5:
            tipo_insc = "0"              # 0 = Isento / Não Validar
            doc_fav_final = "0" * 14     # Zeros
        else:
            # 2. Se for CPF (até 11 dígitos)
            if len(raw_doc) <= 11:
                tipo_insc = "1"
                doc_fav_final = raw_doc.rjust(14, '0')
            # 3. Se for CNPJ (> 11 dígitos)
            else:
                tipo_insc = "2"
                doc_fav_final = raw_doc.rjust(14, '0')

        # Montagem do Segmento B
        # Pos 001-003: Banco
        # Pos 004-007: Lote
        # Pos 008: Tipo Reg (3)
        # Pos 009-013: N Sequencial
        # Pos 014: Cod Seg (B)
        # Pos 015-017: Uso Exclusivo (DEVEM SER ESPAÇOS - AQUI DAVA ERRO ANTES)
        # Pos 018: Tipo Inscrição (0, 1 ou 2)
        # Pos 19-32: Numero Inscrição
        
        segB = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{' '*3}"  # 15-17 = BRANCOS
                f"{tipo_insc}{formatar_campo(doc_fav_final,14,'0','r')}"   # 18-32 = DOC TRATADO
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

# ==========================================
# MOTOR BOLETO (MANTIDO INTACTO - HOMOLOGADO)
# ==========================================
def gerar_cnab_boleto(df_input, h=DADOS_HOSPITAL):
    df_sel = df_input.copy()
    df_sel['TIPO_TEMP'] = df_sel.apply(identificar_tipo_pagamento, axis=1)
    df_sel = df_sel[df_sel['TIPO_TEMP'] == 'BOLETO'] 
    
    if df_sel.empty: return None

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
