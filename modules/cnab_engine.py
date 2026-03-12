import os
import re
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES GERAIS ---
DADOS_HOSPITAL = {
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'cnpj': '85307098000187', 
    'banco': '136', 
    'agencia': '1214',
    'dv_agencia': '0',
    'conta': '5886', 
    'dv_conta': '6', 
    'convenio': '985597',
    'logradouro': 'RODOVIA SC 401',
    'numero': '123', 
    'complemento': 'SALA 01',
    'cidade': 'FLORIANOPOLIS',
    'cep': '88000',
    'cep_sufixo': '000',
    'uf': 'SC'
}

# --- FUNÇÕES UTILITÁRIAS ---

def obter_proximo_sequencial():
    try:
        arquivo_nsa = "nsa_counter.txt"
        if not os.path.exists(arquivo_nsa):
            with open(arquivo_nsa, "w") as f: f.write("1")
            return 1
        with open(arquivo_nsa, "r") as f: atual = int(f.read().strip())
        novo = atual + 1
        with open(arquivo_nsa, "w") as f: f.write(str(novo))
        return novo
    except:
        return int(datetime.now().strftime('%H%M%S'))

def get_val(row, possible_names, default=''):
    """
    Buscador Inteligente: Procura o valor na linha do dataframe ignorando espaços, 
    letras maiúsculas ou minúsculas no nome da coluna vinda do Excel/Tasy.
    """
    for key in row.keys():
        key_clean = str(key).strip().upper()
        for name in possible_names:
            if key_clean == name.upper():
                val = row[key]
                if pd.notna(val) and str(val).strip() != '':
                    return val
    return default

def limpar_numero(valor):
    if pd.isna(valor) or valor == '' or valor is None: 
        return ""
    s_val = str(valor).strip()
    if s_val.endswith('.0'):
        s_val = s_val[:-2]
    return ''.join(filter(str.isdigit, s_val))

def converter_linha_digitavel_para_barras(linha):
    linha = limpar_numero(linha) 
    if len(linha) == 44: return linha 
    
    if len(linha) == 47: 
        c1 = linha[0:9]
        c2 = linha[10:20]
        c3 = linha[21:31]
        dv_geral = linha[32]
        fator_valor = linha[33:]
        return c1[0:3] + c1[3:4] + dv_geral + fator_valor + c1[4:9] + c2 + c3
        
    if len(linha) == 48: 
        return linha[0:11] + linha[12:23] + linha[24:35] + linha[36:47]

    return linha[:44]

def detectar_tipo_chave_pix_interno(chave_raw):
    chave = str(chave_raw).strip()
    if not chave or str(chave).lower() in ['nan', 'none']: 
        return '005' # Dados bancários (Ag/Conta)
        
    if '@' in chave: return '002' # Email
    if len(chave) > 30 and '-' in chave: return '004' # Aleatória
    
    nums = limpar_numero(chave)
    if len(nums) == 11:
        if chave.startswith('(') or chave.startswith('+'):
            return '001' # Telefone
        return '003' # CPF
    if len(nums) == 14: 
        return '003' # CNPJ
        
    return '001' # Fallback para telefone

def classificar_transacao_real(dado):
    limpo = limpar_numero(dado)
    if len(limpo) >= 44:
        return 'BOLETO'
    return 'PIX'

# =============================================================================
# GERADORES DE SEGMENTO
# =============================================================================

def gerar_segmento_j_combo(row, seq_lote_interno, num_lote):
    chave_bruta = get_val(row, ['CHAVE_PIX_OU_COD_BARRAS', 'COD_BARRAS', 'CHAVE_PIX'])
    cod_barras = converter_linha_digitavel_para_barras(chave_bruta)
    
    try: valor = float(get_val(row, ['VALOR_PAGAMENTO', 'VALOR'], 0.0))
    except: valor = 0.0
    valor_str = f"{int(valor * 100):0>15}"
    
    try:
        dt_obj = datetime.strptime(str(get_val(row, ['DATA_PAGAMENTO', 'DATA'])), '%d/%m/%Y')
        dt_str = dt_obj.strftime('%d%m%Y')
    except: dt_str = datetime.now().strftime('%d%m%Y')
    
    nome_fav = str(get_val(row, ['NOME_FAVORECIDO', 'NOME', 'FAVORECIDO']))

    seg_j = (
        f"{'136':<3}{num_lote:0>4}{'3':<1}{seq_lote_interno:0>5}{'J':<1}{'000':<3}" 
        f"{cod_barras[:44]:0>44}"       
        f"{nome_fav[:30]:<30}"          
        f"{dt_str:<8}"                  
        f"{valor_str:0>15}"             
        f"{'0':0>15}{'0':0>15}"         
        f"{dt_str:<8}"                  
        f"{valor_str:0>15}"             
        f"{'0':0>15}"                   
        f"{'':<20}{'':<20}{'09':<2}"    
        f"{'':<6}{'':<10}"              
    )[:240] + "\r\n"
    
    seq_lote_interno += 1
    doc_fav = limpar_numero(get_val(row, ['cnpj_beneficiario', 'CNPJ']))
    if not doc_fav: doc_fav = "00000000000"
    tipo_insc_cedente = "1" if len(doc_fav) <= 11 else "2"
    
    seg_j52 = (
        f"{'136':<3}{num_lote:0>4}{'3':<1}{seq_lote_interno:0>5}{'J':<1}{'   ':<3}"
        f"{'52':<2}"                    
        f"{tipo_insc_cedente:<1}"       
        f"{doc_fav[:14]:0>15}"          
        f"{nome_fav[:40]:<40}"          
        f"{tipo_insc_cedente:<1}"       
        f"{doc_fav[:14]:0>15}"          
        f"{nome_fav[:40]:<40}"          
        f"{'2':<1}"                     
        f"{DADOS_HOSPITAL['cnpj']:0>15}"
        f"{DADOS_HOSPITAL['nome']:<40}" 
        f"{'':<53}"                     
    )[:240] + "\r\n"
    
    return seg_j + seg_j52, 2

def gerar_segmentos_pix_a_b(row, seq_lote_interno, data_arq, num_lote):
    try: valor = float(get_val(row, ['VALOR_PAGAMENTO', 'VALOR'], 0.0))
    except: valor = 0.0
    valor_str = f"{int(valor * 100):0>15}"
    
    chave_pix_raw = str(get_val(row, ['CHAVE_PIX_OU_COD_BARRAS', 'CHAVE_PIX', 'CHAVE'])).strip()
    if chave_pix_raw.lower() in ['nan', 'none']: chave_pix_raw = ''
    
    tipo_chave_code = detectar_tipo_chave_pix_interno(chave_pix_raw)
    
    # Busca blindada dos Dados Bancários (Imune a erros de nome de coluna no Excel)
    banco_fav = limpar_numero(get_val(row, ['BANCO_FAVORECIDO', 'BANCO'], '000')) or "000"
    agencia_fav = limpar_numero(get_val(row, ['AGENCIA_FAVORECIDA', 'AGENCIA'], '0')) or "0"
    dv_agencia_fav = str(get_val(row, ['DIGITO_AGENCIA_FAVORECIDA', 'DV_AGENCIA'], ' ')).strip() or " "
    conta_fav = limpar_numero(get_val(row, ['CONTA_FAVORECIDA', 'CONTA'], '0')) or "0"
    dv_conta_fav = str(get_val(row, ['DIGITO_CONTA_FAVORECIDA', 'DV_CONTA'], '0')).strip() or "0"
    
    if conta_fav == "0" or not conta_fav: conta_fav = "1"
    
    try:
        dt_obj = datetime.strptime(str(get_val(row, ['DATA_PAGAMENTO', 'DATA'])), '%d/%m/%Y')
        dt_str = dt_obj.strftime('%d%m%Y')
    except: dt_str = data_arq
    
    nome_fav = str(get_val(row, ['NOME_FAVORECIDO', 'NOME', 'FAVORECIDO']))

    seg_a = (
        f"{'136':<3}{num_lote:0>4}{'3':<1}{seq_lote_interno:0>5}{'A':<1}{'000':<3}{'009':<3}"
        f"{banco_fav[:3]:0>3}{agencia_fav[:5]:0>5}{dv_agencia_fav[:1]:<1}"
        f"{conta_fav[:12]:0>12}{dv_conta_fav[:1]:<1}{' ':1}"
        f"{nome_fav[:30]:<30}{chave_pix_raw[:20]:<20}{dt_str:<8}{'BRL':<3}"
        f"{'0':0>15}{valor_str:0>15}{'':<20}{dt_str:<8}{valor_str:0>15}"
        f"{'':<40}{'00':<2}{'':<5}{'':<2}{'':<3}{'0':<1}{'':<10}"
    )[:240] + "\r\n"

    seq_lote_interno += 1
    doc_fav = limpar_numero(get_val(row, ['cnpj_beneficiario', 'CNPJ']))
    if not doc_fav: doc_fav = "00000000000"
    tipo_insc = "1" if len(doc_fav) <= 11 else "2"
    
    info_10 = "NAO INFORMADO".ljust(35)[:35]
    
    # --- LÓGICA DO TIPO DE CONTA PARA DADOS BANCÁRIOS (05) ---
    if tipo_chave_code == '005':
        tipo_conta = "01" # Default para Conta Corrente
        tc_raw = str(get_val(row, ['TIPO_CONTA'])).upper()
        if 'POUPANCA' in tc_raw or 'POUPANÇA' in tc_raw:
            tipo_conta = "03"
        elif 'PAGAMENTO' in tc_raw:
            tipo_conta = "02"
        # O manual exige que se envie o tipo da conta na informação 11 (60 posições)
        info_11 = tipo_conta.ljust(60)[:60]
    else:
        info_11 = f"{'0':0>5}{'':<15}{'BAIRRO':<15}{'CIDADE':<15}{'00000':0>5}{'000':0>3}{'SC':<2}"

    seg_b = (
        f"{'136':<3}{num_lote:0>4}{'3':<1}{seq_lote_interno:0>5}{'B':<1}"
        f"{tipo_chave_code[:3]:0>3}{tipo_insc[:1]:<1}{doc_fav[:14]:0>14}"
        f"{info_10}"
        f"{info_11}"
        f"{chave_pix_raw[:99]:<99}"
        f"{'':<6}{'':<8}"
    )[:240] + "\r\n"
    
    return seg_a + seg_b, 2

def gerar_header_lote(num_lote, forma_lancamento, versao_layout):
    return (
        f"{'136':<3}{num_lote:0>4}{'1':<1}{'C':<1}{'20':<2}{forma_lancamento:<2}{versao_layout:<3}{'':<1}{'2':<1}"
        f"{DADOS_HOSPITAL['cnpj']:0>14}{DADOS_HOSPITAL['convenio']:0>20}"
        f"{DADOS_HOSPITAL['agencia']:0>5}{DADOS_HOSPITAL['dv_agencia']:<1}"
        f"{DADOS_HOSPITAL['conta']:0>12}{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}"
        f"{DADOS_HOSPITAL['nome']:<30}{'':<40}" 
        f"{DADOS_HOSPITAL['logradouro']:<30}{DADOS_HOSPITAL['numero']:0>5}"
        f"{DADOS_HOSPITAL['complemento']:<15}{DADOS_HOSPITAL['cidade']:<20}"
        f"{DADOS_HOSPITAL['cep']:0>5}{DADOS_HOSPITAL['cep_sufixo']:0>3}"
        f"{DADOS_HOSPITAL['uf']:<2}{'':<8}{'':<10}\r\n"
    )[:242]

def gerar_trailer_lote(num_lote, qtd_registros, total_valor):
    valor_total_str = f"{int(total_valor * 100):0>18}"
    qtd_total_lote = qtd_registros + 2 
    return (
        f"{'136':<3}{num_lote:0>4}{'5':<1}{'':<9}{qtd_total_lote:0>6}"
        f"{valor_total_str:<18}{'0':0>18}{'0':0>6}{'':<165}{'':<10}\r\n"
    )[:242]

# =============================================================================
# MOTOR PRINCIPAL
# =============================================================================

def gerar_cnab_remessa(df_pagamentos):
    if df_pagamentos.empty: return None

    nsa = obter_proximo_sequencial()
    now = datetime.now()
    data_arq = now.strftime('%d%m%Y')
    hora_arq = now.strftime('%H%M%S')
    
    header_arq = (
        f"{'136':<3}{'0000':0>4}{'0':<1}{'':<9}{'2':<1}{DADOS_HOSPITAL['cnpj']:0>14}"
        f"{DADOS_HOSPITAL['convenio']:0>20}{DADOS_HOSPITAL['agencia']:0>5}"
        f"{DADOS_HOSPITAL['dv_agencia']:<1}{DADOS_HOSPITAL['conta']:0>12}"
        f"{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}{DADOS_HOSPITAL['nome']:<30}"
        f"{'UNICRED':<30}{'':<10}{'1':<1}{data_arq:<8}{hora_arq:<6}{nsa:0>6}"
        f"{'083':<3}{'00000':0>5}{'':<69}\r\n"
    )[:242]

    lotes = {'PIX': [], 'BOLETO': []}
    
    for _, row in df_pagamentos.iterrows():
        chave_bruta = get_val(row, ['CHAVE_PIX_OU_COD_BARRAS', 'COD_BARRAS', 'CHAVE_PIX'])
        tipo_real = classificar_transacao_real(chave_bruta)
        lotes[tipo_real].append(row)
            
    content = header_arq
    num_lote_arq = 1
    total_registros_arquivo = 0

    config = [('BOLETO', '31', '040'), ('PIX', '45', '046')]

    for tipo, forma, layout in config:
        itens = lotes[tipo]
        if not itens: continue

        content += gerar_header_lote(num_lote_arq, forma, layout)
        
        seq_lote_interno = 1
        qtd_regs_lote = 0
        total_valor_lote = 0
        
        for row in itens:
            if tipo == 'PIX':
                seg_str, qtd = gerar_segmentos_pix_a_b(row, seq_lote_interno, data_arq, num_lote_arq)
            else:
                seg_str, qtd = gerar_segmento_j_combo(row, seq_lote_interno, num_lote_arq)
            
            content += seg_str
            seq_lote_interno += qtd
            qtd_regs_lote += qtd
            try: total_valor_lote += float(get_val(row, ['VALOR_PAGAMENTO', 'VALOR'], 0.0))
            except: pass
            
        content += gerar_trailer_lote(num_lote_arq, qtd_regs_lote, total_valor_lote)
        total_registros_arquivo += (qtd_regs_lote + 2)
        num_lote_arq += 1

    trailer_arq = (
        f"{'136':<3}{'9999':<4}{'9':<1}{'':<9}{'000001':0>6}"
        f"{total_registros_arquivo+2:0>6}{'000000':0>6}{'':<205}\r\n"
    )[:242]
    
    return content + trailer_arq

# Alias
gerar_cnab_pix = gerar_cnab_remessa
