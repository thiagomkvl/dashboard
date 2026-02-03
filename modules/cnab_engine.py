import os
from datetime import datetime

# --- CONFIGURAÇÃO CORRIGIDA PELO LOG DE ERRO ---
# O erro mostrou que a conta 58866 deve ser separada em Corpo (5886) e DV (6)
DADOS_HOSPITAL = {
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'cnpj': '85307098000187', 
    'banco': '136', 
    'agencia': '1214',
    'dv_agencia': '0', # Geralmente 0 ou vazio na Unicred
    'conta': '5886',   # CORRIGIDO: Removido o último dígito
    'dv_conta': '6',   # CORRIGIDO: O dígito vem aqui
    'convenio': '985597',
    # NOVOS DADOS OBRIGATÓRIOS (Header de Lote)
    'logradouro': 'RODOVIA SC 401',
    'numero': '123', # Coloque o número correto
    'complemento': 'SALA 01',
    'cidade': 'FLORIANOPOLIS',
    'cep': '88000',
    'cep_sufixo': '000',
    'uf': 'SC'
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
    if df_pagamentos.empty: return None

    nsa = obter_proximo_sequencial()
    now = datetime.now()
    data_arq = now.strftime('%d%m%Y')
    hora_arq = now.strftime('%H%M%S')
    
    # =========================================================================
    # HEADER DE ARQUIVO (240 POSIÇÕES)
    # =========================================================================
    header_arq = (
        f"{'136':<3}"                               # 01-03: Banco
        f"{'0000':<4}"                              # 04-07: Lote
        f"{'0':<1}"                                 # 08-08: Registro
        f"{'':<9}"                                  # 09-17: Brancos
        f"{'2':<1}"                                 # 18-18: Tipo Insc (2=CNPJ)
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32: CNPJ
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52: Convênio
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57: Agência
        f"{DADOS_HOSPITAL['dv_agencia']:<1}"        # 58-58: DV Ag
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70: Conta (SEM O DÍGITO)
        f"{DADOS_HOSPITAL['dv_conta']:<1}"          # 71-71: DV Conta (SÓ O DÍGITO)
        f"{'0':<1}"                                 # 72-72: DV Ag/Conta
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102: Nome Emp
        f"{'UNICRED':<30}"                          # 103-132: Nome Banco
        f"{'':<10}"                                 # 133-142: Brancos
        f"{'1':<1}"                                 # 143-143: Cod Remessa
        f"{data_arq:<8}"                            # 144-151: Data
        f"{hora_arq:<6}"                            # 152-157: Hora
        f"{nsa:0>6}"                                # 158-163: Sequencial
        f"{'083':<3}"                               # 164-166: Versão
        f"{'00000':<5}"                             # 167-171: Densidade
        f"{'':<69}"                                 # 172-240: Reservado
        f"\r\n"
    )

    # =========================================================================
    # HEADER DE LOTE (240 POSIÇÕES) - CORRIGIDO COM ENDEREÇO
    # =========================================================================
    header_lote = (
        f"{'136':<3}"                               # 01-03
        f"{'0001':<4}"                              # 04-07
        f"{'1':<1}"                                 # 08-08
        f"{'C':<1}"                                 # 09-09
        f"{'20':<2}"                                # 10-11: Pagto Fornecedor
        f"{'45':<2}"                                # 12-13: Forma Pagto (45=PIX)
        f"{'040':<3}"                               # 14-16: Layout
        f"{'':<1}"                                  # 17-17
        f"{'2':<1}"                                 # 18-18
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57
        f"{DADOS_HOSPITAL['dv_agencia']:<1}"        # 58-58
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70
        f"{DADOS_HOSPITAL['dv_conta']:<1}"          # 71-71
        f"{'0':<1}"                                 # 72-72
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102
        f"{'PAGAMENTO FORNECEDORES':<40}"           # 103-142: Msg 1
        # --- ENDEREÇO OBRIGATÓRIO (CORREÇÃO DE ERRO) ---
        f"{DADOS_HOSPITAL['logradouro']:<30}"       # 143-172: Logradouro
        f"{DADOS_HOSPITAL['numero']:0>5}"           # 173-177: Numero
        f"{DADOS_HOSPITAL['complemento']:<15}"      # 178-192: Compl
        f"{DADOS_HOSPITAL['cidade']:<20}"           # 193-212: Cidade
        f"{DADOS_HOSPITAL['cep']:0>5}"              # 213-217: CEP
        f"{DADOS_HOSPITAL['cep_sufixo']:0>3}"       # 218-220: Sufixo CEP
        f"{DADOS_HOSPITAL['uf']:<2}"                # 221-222: UF
        f"{'':<8}"                                  # 223-230: CNAB
        f"{'':<10}"                                 # 231-240: Ocorrências
        f"\r\n"
    )

    detalhes = ""
    qtd_registros = 0
    total_valor = 0
    seq_lote = 1

    for _, row in df_pagamentos.iterrows():
        # --- TRATAMENTOS ---
        try: valor = float(row['VALOR_PAGAMENTO'])
        except: valor = 0.0
        valor_str = f"{int(valor * 100):0>15}"
        total_valor += valor
        
        chave_pix_raw = str(row.get('CHAVE_PIX_OU_COD_BARRAS', '')).strip()
        if chave_pix_raw.lower() in ['nan', 'none']: chave_pix_raw = ''
        if chave_pix_raw.endswith('.0'): chave_pix_raw = chave_pix_raw[:-2]

        try:
            dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
            dt_str = dt_obj.strftime('%d%m%Y')
        except: dt_str = data_arq

        # =====================================================================
        # SEGMENTO A (240 POSIÇÕES)
        # TRUQUE PIX: Banco Fav = 000 e Contas Zeradas para forçar leitura da Chave
        # =====================================================================
        seg_a = (
            f"{'136':<3}"                           # 01-03
            f"{'0001':<4}"                          # 04-07: Lote
            f"{'3':<1}"                             # 08-08: Detalhe
            f"{seq_lote:0>5}"                       # 09-13
            f"{'A':<1}"                             # 14-14
            f"{'000':<3}"                           # 15-17: Inclusão
            f"{'009':<3}"                           # 18-20: Câmera 009 (PIX)
            f"{'000':<3}"                           # 21-23: Banco Fav (000 = Externo/Chave)
            f"{'00000':<5}"                         # 24-28: Ag Fav (ZEROS)
            f"{' ':1}"                              # 29-29
            f"{'000000000000':<12}"                 # 30-41: Conta Fav (ZEROS)
            f"{' ':1}"                              # 42-42
            f"{' ':1}"                              # 43-43
            f"{str(row['NOME_FAVORECIDO'])[:30]:<30}" # 44-73
            f"{chave_pix_raw:<20}"                  # 74-93: Seu Numero (Chave Pix aqui)
            f"{dt_str:<8}"                          # 94-101
            f"{'BRL':<3}"                           # 102-104
            f"{'0':>15}"                            # 105-119
            f"{valor_str:<15}"                      # 120-134
            f"{'':<20}"                             # 135-154
            f"{dt_str:<8}"                          # 155-162
            f"{valor_str:<15}"                      # 163-177
            f"{'':<40}"                             # 178-217: Info Comp
            f"{'00':<2}"                            # 218-219
            f"{'':<10}"                             # 220-229
            f"{'00':<2}"                            # 230-231
            f"{'045':<3}"                           # 232-234: DDA/PIX
            f"{'':<6}"                              # 235-240
            f"\r\n"
        )
        seq_lote += 1

        # =====================================================================
        # SEGMENTO B (240 POSIÇÕES)
        # =====================================================================
        # Limpeza agressiva do documento para garantir que não vá vazio
        raw_doc = str(row.get('cnpj_beneficiario', '')).strip()
        if raw_doc.endswith('.0'): raw_doc = raw_doc[:-2]
        doc_fav = ''.join(filter(str.isdigit, raw_doc))
        
        # Se vazio, usa zeros para não quebrar o layout, mas avisa no log visual
        if not doc_fav: doc_fav = "00000000000"
        
        tipo_insc = "1" if len(doc_fav) <= 11 else "2"

        seg_b = (
            f"{'136':<3}"                           # 01-03
            f"{'0001':<4}"                          # 04-07
            f"{'3':<1}"                             # 08-08
            f"{seq_lote:0>5}"                       # 09-13
            f"{'B':<1}"                             # 14-14
            f"{'':<3}"                              # 15-17
            f"{tipo_insc:<1}"                       # 18-18: Tipo Insc Fav
            f"{doc_fav:0>14}"                       # 19-32: CNPJ/CPF Chave
            f"{'':<30}"                             # 33-62: Logradouro Fav
            f"{'0':<5}"                             # 63-67: Num
            f"{'':<15}"                             # 68-82: Compl
            f"{'':<15}"                             # 83-97: Bairro
            f"{'':<20}"                             # 98-117: Cidade
            f"{'00000':<5}"                         # 118-122: CEP
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

    # =========================================================================
    # TRAILER DE LOTE (240 POSIÇÕES)
    # =========================================================================
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

    # =========================================================================
    # TRAILER DE ARQUIVO (240 POSIÇÕES)
    # =========================================================================
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
