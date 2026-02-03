import os
import re
from datetime import datetime

# DADOS DO HOSPITAL
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

def obter_proximo_sequencial():
    arquivo_nsa = "nsa_counter.txt"
    if not os.path.exists(arquivo_nsa):
        with open(arquivo_nsa, "w") as f: f.write("1")
        return 1
    try:
        with open(arquivo_nsa, "r") as f: atual = int(f.read().strip())
    except: atual = 0
    novo = atual + 1
    with open(arquivo_nsa, "w") as f: f.write(str(novo))
    return novo

def limpar_numero(valor):
    """Remove tudo que não for dígito"""
    if not valor: return ""
    return ''.join(filter(str.isdigit, str(valor)))

def detectar_tipo_chave(chave):
    """Define o código G100 (01-Tel, 02-Email, 03-CPF/CNPJ, 04-Aleatoria)"""
    chave = str(chave).strip()
    if '@' in chave: return '02 '
    if len(chave) > 30 and '-' in chave: return '04 '
    nums = limpar_numero(chave)
    if len(nums) == 11 or len(nums) == 14: return '03 '
    return '01 '

def gerar_cnab_pix(df_pagamentos):
    if df_pagamentos.empty: return None

    nsa = obter_proximo_sequencial()
    now = datetime.now()
    data_arq = now.strftime('%d%m%Y')
    hora_arq = now.strftime('%H%M%S')
    
    # --- HEADER DE ARQUIVO ---
    header_arq = (
        f"{'136':<3}{'0000':0>4}{'0':<1}{'':<9}{'2':<1}{DADOS_HOSPITAL['cnpj']:0>14}"
        f"{DADOS_HOSPITAL['convenio']:0>20}{DADOS_HOSPITAL['agencia']:0>5}"
        f"{DADOS_HOSPITAL['dv_agencia']:<1}{DADOS_HOSPITAL['conta']:0>12}"
        f"{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}{DADOS_HOSPITAL['nome']:<30}"
        f"{'UNICRED':<30}{'':<10}{'1':<1}{data_arq:<8}{hora_arq:<6}{nsa:0>6}"
        f"{'083':<3}{'00000':0>5}{'':<69}\r\n"
    )

    # --- HEADER DE LOTE ---
    header_lote = (
        f"{'136':<3}{'0001':0>4}{'1':<1}{'C':<1}{'20':<2}{'45':<2}{'046':<3}{'':<1}{'2':<1}"
        f"{DADOS_HOSPITAL['cnpj']:0>14}{DADOS_HOSPITAL['convenio']:0>20}"
        f"{DADOS_HOSPITAL['agencia']:0>5}{DADOS_HOSPITAL['dv_agencia']:<1}"
        f"{DADOS_HOSPITAL['conta']:0>12}{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}"
        f"{DADOS_HOSPITAL['nome']:<30}{'PAGAMENTO FORNECEDORES':<40}"
        f"{DADOS_HOSPITAL['logradouro']:<30}{DADOS_HOSPITAL['numero']:0>5}"
        f"{DADOS_HOSPITAL['complemento']:<15}{DADOS_HOSPITAL['cidade']:<20}"
        f"{DADOS_HOSPITAL['cep']:0>5}{DADOS_HOSPITAL['cep_sufixo']:0>3}"
        f"{DADOS_HOSPITAL['uf']:<2}{'':<8}{'':<10}\r\n"
    )

    detalhes = ""
    qtd_registros = 0
    total_valor = 0
    seq_lote = 1

    for _, row in df_pagamentos.iterrows():
        # --- PREPARAÇÃO DE DADOS ---
        try: valor = float(row['VALOR_PAGAMENTO'])
        except: valor = 0.0
        valor_str = f"{int(valor * 100):0>15}"
        total_valor += valor
        
        # Chave PIX
        chave_pix_raw = str(row.get('CHAVE_PIX_OU_COD_BARRAS', '')).strip()
        if chave_pix_raw.lower() in ['nan', 'none']: chave_pix_raw = ''
        if chave_pix_raw.endswith('.0'): chave_pix_raw = chave_pix_raw[:-2]
        tipo_chave_code = detectar_tipo_chave(chave_pix_raw)
        
        # Dados Bancários do Favorecido (EXTRAÍDOS DO DATAFRAME AGORA)
        banco_fav = limpar_numero(row.get('BANCO_FAVORECIDO', ''))
        agencia_fav = limpar_numero(row.get('AGENCIA_FAVORECIDA', ''))
        conta_fav = limpar_numero(row.get('CONTA_FAVORECIDA', ''))
        dv_conta_fav = str(row.get('DIGITO_CONTA_FAVORECIDA', '')).strip()
        
        # Fallback se vazio (mas usuário deve preencher)
        if not banco_fav: banco_fav = "000" 
        if not agencia_fav: agencia_fav = "0"
        if not conta_fav: conta_fav = "0"
        if not dv_conta_fav: dv_conta_fav = "0"

        try:
            dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
            dt_str = dt_obj.strftime('%d%m%Y')
        except: dt_str = data_arq

        # --- SEGMENTO A (COM DADOS BANCÁRIOS REAIS) ---
        seg_a = (
            f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'A':<1}{'000':<3}{'009':<3}"
            f"{banco_fav[:3]:0>3}"                  # 21-23: Banco Real
            f"{agencia_fav[:5]:0>5}"                # 24-28: Agência Real
            f"{' ':1}"                              # 29-29: DV Ag
            f"{conta_fav[:12]:0>12}"                # 30-41: Conta Real
            f"{dv_conta_fav[:1]:<1}"                # 42-42: DV Conta Real
            f"{' ':1}"                              # 43-43: DV Ag/Conta
            f"{str(row['NOME_FAVORECIDO'])[:30]:<30}"
            f"{chave_pix_raw:<20}"                  # 74-93: Seu Numero
            f"{dt_str:<8}{'BRL':<3}"
            f"{'0':0>15}{valor_str:<15}{'':<20}{dt_str:<8}{valor_str:<15}"
            f"{'':<40}{'00':<2}{'':<5}{'':<2}{'':<3}{'0':<1}{'':<10}\r\n"
        )
        seq_lote += 1

        # --- SEGMENTO B ---
        doc_fav = limpar_numero(row.get('cnpj_beneficiario', ''))
        if not doc_fav: doc_fav = "00000000000"
        tipo_insc = "1" if len(doc_fav) <= 11 else "2"

        seg_b = (
            f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'B':<1}"
            f"{tipo_chave_code:<3}"                 # 15-17: G100
            f"{tipo_insc:<1}"                       # 18-18
            f"{doc_fav:0>14}"                       # 19-32
            f"{'':<30}{'0':0>5}{'':<15}{'':<15}{'':<20}{'00000':0>5}{'000':0>3}{'SC':<2}"
            f"{chave_pix_raw:<99}"                  # 128-226: CHAVE PIX
            f"{'':<6}{'':<8}\r\n"
        )
        seq_lote += 1
        qtd_registros += 2
        detalhes += seg_a + seg_b

    # --- TRAILERS ---
    qtd_lote_total = qtd_registros + 2
    valor_total_str = f"{int(total_valor * 100):0>18}"
    
    trailer_lote = (
        f"{'136':<3}{'0001':0>4}{'5':<1}{'':<9}{qtd_lote_total:0>6}"
        f"{valor_total_str:<18}{'0':0>18}{'0':0>6}{'':<165}{'':<10}\r\n"
    )
    trailer_arq = (
        f"{'136':<3}{'9999':<4}{'9':<1}{'':<9}{'000001':0>6}"
        f"{qtd_lote_total+2:0>6}{'000000':0>6}{'':<205}\r\n"
    )

    return header_arq + header_lote + detalhes + trailer_lote + trailer_arq
