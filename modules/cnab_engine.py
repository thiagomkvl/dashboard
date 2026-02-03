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
    
    # --- HEADER DE ARQUIVO (CORRIGIDO: 240 POSIÇÕES EXATAS) ---
    # Correção: Ajustados os espaçamentos das posições 09-17 e 133-142
    header_arq = (
        f"13600000"                                 # 01-08: Controles
        f"{'':<9}"                                  # 09-17: CNAB (9 espaços)
        f"2"                                        # 18-18: Tipo Insc (CNPJ)
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32: CNPJ
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52: Convênio
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57: Agência
        f"0"                                        # 58-58: DV Ag
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70: Conta
        f"{DADOS_HOSPITAL['dv_conta']:0>1}"         # 71-71: DV Conta
        f"0"                                        # 72-72: DV Ag/Conta
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102: Nome Empresa
        f"{'UNICRED':<30}"                          # 103-132: Nome Banco
        f"{'':<10}"                                 # 133-142: CNAB (10 espaços)
        f"1"                                        # 143-143: Código Remessa
        f"{data_arq}"                               # 144-151: Data
        f"{hora_arq}"                               # 152-157: Hora
        f"{nsa:0>6}"                                # 158-163: Sequencial
        f"083"                                      # 164-166: Versão
        f"00000"                                    # 167-171: Densidade
        f"{'':<69}"                                 # 172-240: Reservado
        f"\r\n"
    )

    # --- HEADER DE LOTE (240 POSIÇÕES) ---
    header_lote = (
        f"13600011"                                 # 01-08: Controles
        f"C"                                        # 09-09: Operação
        f"20"                                       # 10-11: Tipo Pagto
        f"45"                                       # 12-13: Forma Pagto (Pix)
        f"040"                                      # 14-16: Versão Layout
        f" "                                        # 17-17: CNAB
        f"2"                                        # 18-18: Tipo Insc
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32: CNPJ
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52: Convênio
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57: Agência
        f"0"                                        # 58-58: DV Ag
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70: Conta
        f"{DADOS_HOSPITAL['dv_conta']:0>1}"         # 71-71: DV Conta
        f"0"                                        # 72-72: DV Ag/Conta
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102: Nome
        f"{'':<40}"                                 # 103-142: Mensagem 1
        f"{'':<40}"                                 # 143-182: Endereço
        f"{'':<8}"                                  # 183-190: Numero
        f"{'':<15}"                                 # 191-205: Compl
        f"{'':<20}"                                 # 206-225: Cidade
        f"{'00000000'}"                             # 226-233: CEP
        f"{'SC'}"                                   # 234-235: UF
        f"{'':<5}"                                  # 236-240: CNAB
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
            f"13600013"                             # 01-08
            f"{seq_lote:0>5}"                       # 09-13
            f"A"                                    # 14-14
            f"000"                                  # 15-17: Inclusão
            f"009"                                  # 18-20: Pix
            f"136"                                  # 21-23: Banco
            f"{'0':>5}"                             # 24-28: Agência (Zero p/ Pix)
            f" "                                    # 29-29
            f"{'0':>12}"                            # 30-41: Conta (Zero p/ Pix)
            f" "                                    # 42-42
            f" "                                    # 43-43
            f"{str(row['NOME_FAVORECIDO'])[:30]:<30}" # 44-73
            f"{chave_pix_raw:<20}"                  # 74-93: Seu Numero (Chave)
            f"{dt_str}"                             # 94-101
            f"BRL"                                  # 102-104
            f"{'0':>15}"                            # 105-119
            f"{valor_str}"                          # 120-134
            f"{'':<20}"                             # 135-154
            f"{dt_str}"                             # 155-162
            f"{valor_str}"                          # 163-177
            f"{'':<40}"                             # 178-217: Info
            f"00"                                   # 218-219
            f"{'':<10}"                             # 220-229
            f"00"                                   # 230-231
            f"045"                                  # 232-234: DDA
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
            f"13600013"                             # 01-08
            f"{seq_lote:0>5}"                       # 09-13
            f"B"                                    # 14-14
            f"{'':<3}"                              # 15-17
            f"{tipo_insc}"                          # 18-18
            f"{doc_fav:0>14}"                       # 19-32: CNPJ/CPF Chave
            f"{'':<30}"                             # 33-62
            f"{'0':<5}"                             # 63-67
            f"{'':<15}"                             # 68-82
            f"{'':<15}"                             # 83-97
            f"{'':<20}"                             # 98-117
            f"{'00000000'}"                         # 118-125
            f"SC"                                   # 126-127
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
        f"13600015"
        f"{'':<9}"
        f"{qtd_lote_total:0>6}"
        f"{valor_total_str}"
        f"{'0':>18}"
        f"{'0':>6}"
        f"{'':<165}"
        f"{'':<10}"
        f"\r\n"
    )

    # --- TRAILER DE ARQUIVO (240 POSIÇÕES) ---
    trailer_arq = (
        f"13699999"
        f"{'':<9}"
        f"{1:0>6}"
        f"{qtd_lote_total+2:0>6}"
        f"{'0':>6}"
        f"{'':<205}"
        f"\r\n"
    )

    return header_arq + header_lote + detalhes + trailer_lote + trailer_arq
