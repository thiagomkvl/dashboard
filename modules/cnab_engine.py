from datetime import datetime
import pandas as pd
from modules.utils import formatar_campo, limpar_ids, identificar_tipo_pagamento

# ==========================================
# DADOS CADASTRAIS (MANTIDO)
# ==========================================
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

# ==========================================
# MOTOR PIX (CORRIGIDO PARA ERROS DE VALIDAÇÃO)
# ==========================================
def gerar_cnab_pix(df_input, h=DADOS_HOSPITAL):
    # 1. FILTRO: Processa apenas PIX
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
        
        # Identificação Chave Pix (Apenas para uso interno ou Log, não vai no Header do Seg B)
        # O banco lê a chave no campo específico do Segmento B (pos 227+ ou info complementar)
        # Mas aqui focamos em limpar os dados.
        
        # Dados Bancários
        banco_fav = limpar_ids(r.get('BANCO_FAVORECIDO', '')) or "000"
        ag_fav = limpar_ids(r.get('AGENCIA_FAVORECIDA', '')) or "0"
        cc_fav = limpar_ids(r.get('CONTA_FAVORECIDA', ''))
        dv_cc_fav = limpar_ids(r.get('DIGITO_CONTA_FAVORECIDA', '')) or "0"
        
        # Vacina da Conta: Pix exige conta > 0 para passar no validador Seg A, mesmo que use Chave
        if not cc_fav or cc_fav == "" or int(limpar_ids(cc_fav) or 0) == 0: cc_fav = "1"

        # SEGMENTO A (Pix = Câmara 009)
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
        
        # --- CORREÇÃO CRÍTICA DO ERRO DE VALIDAÇÃO ---
        doc_fav = limpar_ids(r.get('cnpj_beneficiario', ''))
        
        # Lógica: Se vazio -> Manda ZEROS e Tipo 0 (Evita erro de digito verificador do "1")
        # Se preenchido -> Manda Tipo 1 (CPF) ou 2 (CNPJ)
        if not doc_fav or doc_fav == "0":
            doc_fav = "00000000000000" # 14 Zeros
            tipo_insc = "0" # 0 = Isento / Não Informado
        else:
            if len(doc_fav) <= 11:
                tipo_insc = "1" # CPF
                doc_fav = doc_fav.rjust(14, '0') # Ajusta para 14 posições
            else:
                tipo_insc = "2" # CNPJ
                # doc_fav já tem 14 ou será cortado pelo formatar_campo
        
        # Ajuste Pos 15-17: Deve ser BRANCOS no padrão (estava indo tipo_chave)
        segB = (f"{BCO}00013{formatar_campo(reg_lote,5,'0','r')}B{' '*3}"  # 15-17: Reservado (Brancos)
                f"{tipo_insc}{formatar_campo(doc_fav,14,'0','r')}" # 18: Tipo, 19-32: Documento (CORRIGIDO)
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
# MOTOR BOLETO (HOMOLOGADO - NÃO ALTERAR)
# ==========================================
def gerar_cnab_boleto(df_input, h=DADOS_HOSPITAL):
    # 1. FILTRO: Processa apenas BOLETO
    df_sel = df_input.copy()
    df_sel['TIPO_TEMP'] = df_sel.apply(identificar_tipo_pagamento, axis=1)
    df_sel = df_sel[df_sel['TIPO_TEMP'] == 'BOLETO'] 
    
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
    
    # Header Lote (31)
    h1 = (f"{BCO}00011C2031030 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h['convenio'],20,' ','l')}"
          f"{formatar_campo(h['ag'],5,'0','r')}{formatar_campo(h['ag_dv'],1,' ','l')}"
          f"{formatar_campo(h['cc'],12,'0','r')}{formatar_campo(h['cc_dv'],1,' ','l')}"
          f"{formatar_campo(' ',1)}{formatar_campo(h['nome'],30)}{' '*40}"
          f"{formatar_campo(h['endereco'],30)}{formatar_campo(h['num_end'],5,'0','r')}"
          f"{formatar_campo(h.get('complemento',' '),15)}{formatar_campo(h['cidade'],20)}"
          f"{formatar_campo(h['cep'],8,'0','r')}{formatar_campo(h['uf'],2)}"
          f"{' '*18}") 
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
