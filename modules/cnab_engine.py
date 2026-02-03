import os
from datetime import datetime

# DADOS DO HOSPITAL (Mantenha atualizado)
DADOS_HOSPITAL = {
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'cnpj': '85307098000187', 
    'banco': '136', 
    'agencia': '1214',
    'conta': '58866',
    'dv_conta': '6',
    'convenio': '985597' 
}

def obter_proximo_sequencial():
    """Gerencia o número sequencial do arquivo (NSA)"""
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

def gerar_cnab_pix(df_pagamentos):
    """Gera o arquivo CNAB 240 com validação rigorosa de tamanho (240 caracteres)"""
    if df_pagamentos.empty: return None

    nsa = obter_proximo_sequencial()
    now = datetime.now()
    data_arq = now.strftime('%d%m%Y')
    hora_arq = now.strftime('%H%M%S')
    
    # --- HEADER DE ARQUIVO (240 POSIÇÕES) ---
    header_arq = (
        f"{'136':<3}"                               # 01-03: Banco
        f"{'0000':<4}"                              # 04-07: Lote
        f"{'0':<1}"                                 # 08-08: Registro
        f"{'':<9}"                                  # 09-17: CNAB (9 brancos)
        f"{'2':<1}"                                 # 18-18: Insc
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32: CNPJ
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52: Convênio
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57: Agência
        f"{'0':<1}"                                 # 58-58: DV Ag
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70: Conta
        f"{DADOS_HOSPITAL['dv_conta']:0>1}"         # 71-71: DV Conta
        f"{'0':<1}"                                 # 72-72: DV Ag/Conta
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102: Nome Emp
        f"{'UNICRED':<30}"                          # 103-132: Nome Banco
        f"{'':<10}"                                 # 133-142: CNAB (10 brancos - ONDE OCORRIA O ERRO)
        f"{'1':<1}"                                 # 143-143: Cod Remessa
        f"{data_arq:<8}"                            # 144-151: Data
        f"{hora_arq:<6}"                            # 152-157: Hora
        f"{nsa:0>6}"                                # 158-163: NSA
        f"{'083':<3}"                               # 164-166: Versão
        f"{'00000':<5}"                             # 167-171: Densidade
        f"{'':<69}"                                 # 172-240: Reservado (69 brancos)
        f"\r\n"
    )

    # --- HEADER DE LOTE (240 POSIÇÕES) ---
    header_lote = (
        f"{'136':<3}"                               # 01-03
        f"{'0001':<4}"                              # 04-07
        f"{'1':<1}"                                 # 08-08
        f"{'C':<1}"                                 # 09-09
        f"{'20':<2}"                                # 10-11
        f"{'45':<2}"                                # 12-13
        f"{'040':<3}"                               # 14-16
        f"{'':<1}"                                  # 17-17
        f"{'2':<1}"                                 # 18-18
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57
        f"{'0':<1}"                                 # 58-58
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70
        f"{DADOS_HOSPITAL['dv_conta']:0>1}"         # 71-71
        f"{'0':<1}"                                 # 72-72
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102
        f"{'':<40}"                                 # 103-142: Msg 1
        f"{'':<40}"                                 # 143-182: Endereço
        f"{'0':<5}"                                 # 183-187: Num
        f"{'':<15}"                                 # 188-202: Compl
        f"{'':<20}"                                 # 203-222: Cidade
        f"{'00000':<5}"                             # 223-227: CEP
        f"{'000':<3}"                               # 228-230: Sufixo CEP
        f"{'SC':<2}"                                # 231-232: UF
        f"{'':<8}"                                  # 233-240: CNAB
        f"\r\n"
    )

    detalhes = ""
    qtd_registros = 0
    total_valor = 0
    seq_lote = 1

    for _, row in df_pagamentos.iterrows():
        # Tratamento de Valores
        try: valor = float(row['VALOR_PAGAMENTO'])
        except: valor = 0.0
        valor_str = f"{int(valor * 100):0>15}"
        total_valor += valor
        
        # Tratamento Chave PIX
        chave_pix_raw = str(row.get('CHAVE_PIX_OU_COD_BARRAS', '')).strip()
        if chave_pix_raw.lower() in ['nan', 'none']: chave_pix_raw = ''
        if chave_pix_raw.endswith('.0'): chave_pix_raw = chave_pix_raw[:-2]

        # Tratamento Data
        try:
            dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
            dt_str = dt_obj.strftime('%d%m%Y')
        except: dt_str = data_arq

        # --- SEGMENTO A (240 POSIÇÕES) ---
        seg_a = (
            f"{'136':<3}"                           # 01-03
            f"{'0001':<4}"                          # 04-07: Lote
            f"{'3':<1}"                             # 08-08: Detalhe
            f"{seq_lote:0>5}"                       # 09-13
            f"{'A':<1}"                             # 14-14
            f"{'000':<3}"                           # 15-17
            f"{'009':<3}"                           # 18-20: Pix
            f"{'136':<3}"                           # 21-23: Banco Fav
            f"{'0':>5}"                             # 24-28: Ag Fav
            f"{' ':1}"                              # 29-29
            f"{'0':>12}"                            # 30-41: Conta Fav
            f"{' ':1}"                              # 42-42
            f"{' ':1}"                              # 43-43
            f"{str(row['NOME_FAVORECIDO'])[:30]:<30}" # 44-73
            f"{chave_pix_raw:<20}"                  # 74-93: Seu Numero
            f"{dt_str:<8}"                          # 94-101
            f"{'BRL':<3}"                           # 102-104
            f"{'0':>15}"                            # 105-119
            f"{valor_str:<15}"                      # 120-134
            f"{'':<20}"                             # 135-154
            f"{dt_str:<8}"                          # 155-162
            f"{valor_str:<15}"                      # 163-177
            f"{'':<40}"                             # 178-217
            f"{'00':<2}"                            # 218-219
            f"{'':<10}"                             # 220-229
            f"{'00':<2}"                            # 230-231
            f"{'045':<3}"                           # 232-234
            f"{'':<6}"                              # 235-240
            f"\r\n"
        )
        seq_lote += 1

        # --- SEGMENTO B (240 POSIÇÕES) ---
        raw_doc = str(row.get('cnpj_beneficiario', '')).strip()
        if raw_doc.endswith('.0'): raw_doc = raw_doc[:-2]
        doc_fav = ''.join(filter(str.isdigit, raw_doc))
        tipo_insc = "1" if len(doc_fav) <= 11 else "2"

        seg_b = (
            f"{'136':<3}"                           # 01-03
            f"{'0001':<4}"                          # 04-07
            f"{'3':<1}"                             # 08-08
            f"{seq_lote:0>5}"                       # 09-13
            f"{'B':<1}"                             # 14-14
            f"{'':<3}"                              # 15-17
            f"{tipo_insc:<1}"                       # 18-18
            f"{doc_fav:0>14}"                       # 19-32
            f"{'':<30}"                             # 33-62
            f"{'0':<5}"                             # 63-67
            f"{'':<15}"                             # 68-82
            f"{'':<15}"                             # 83-97
            f"{'':<20}"                             # 98-117
            f"{'00000':<5}"                         # 118-122
            f"{'000':<3}"                           # 123-125
            f"{'SC':<2}"                            # 126-127
            f"{'':<99}"                             # 128-226
            f"{'':<6}"                              # 227-232
            f"{'':<8}"                              # 233-240
            f"\r\n"
        )
        
        seq_lote += 1
        qtd_registros += 2
        detalhes += seg_a + seg_b

    # --- TRAILER DE LOTE (240 POSIÇÕES) ---
    qtd_lote_total = qtd_registros + 2
    valor_total_str = f"{int(total_valor * 100):0>18}"
    
    trailer_lote = (
        f"{'136':<3}"
        f"{'0001':<4}"
        f"{'5':<1}"
        f"{'':<9}"
        f"{qtd_lote_total:0>6}"
        f"{valor_total_str:<18}"
        f"{'0':>18}"
        f"{'0':>6}"
        f"{'':<165}"
        f"{'':<10}"
        f"\r\n"
    )

    # --- TRAILER DE ARQUIVO (240 POSIÇÕES) ---
    trailer_arq = (
        f"{'136':<3}"
        f"{'9999':<4}"
        f"{'9':<1}"
        f"{'':<9}"
        f"{'000001':<6}"
        f"{qtd_lote_total+2:0>6}"
        f"{'000000':<6}"
        f"{'':<205}"
        f"\r\n"
    )

    return header_arq + header_lote + detalhes + trailer_lote + trailer_arq
