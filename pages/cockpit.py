import os
from datetime import datetime

# DADOS DO HOSPITAL (Mantenha atualizado)
DADOS_HOSPITAL = {
    'nome': 'SOS CARDIO SERVICOS HOSP',
    'cnpj': '85307098000187', # Apenas números
    'banco': '136', # Unicred
    'agencia': '1214',
    'conta': '58866',
    'dv_conta': '6',
    'convenio': '985597' # Código do convênio Unicred
}

def obter_proximo_sequencial():
    """Lê e incrementa o Número Sequencial do Arquivo (NSA) automaticamente."""
    arquivo_nsa = "nsa_counter.txt"
    
    if not os.path.exists(arquivo_nsa):
        with open(arquivo_nsa, "w") as f:
            f.write("1")
        return 1
    
    try:
        with open(arquivo_nsa, "r") as f:
            atual = int(f.read().strip())
    except:
        atual = 0
        
    novo = atual + 1
    
    with open(arquivo_nsa, "w") as f:
        f.write(str(novo))
        
    return novo

def gerar_cnab_pix(df_pagamentos):
    """
    Gera CNAB 240 para PIX UNICRED.
    Layout: Forma de Lançamento 45 (PIX), Ag/Conta Zeradas no Seg A.
    """
    if df_pagamentos.empty:
        return None

    # 1. Obter Sequencial Automático
    nsa = obter_proximo_sequencial()
    
    # TIMESTAMP
    now = datetime.now()
    data_arq = now.strftime('%d%m%Y')
    hora_arq = now.strftime('%H%M%S')
    
    # --- HEADER DE ARQUIVO ---
    header_arq = (
        f"13600000"                                 # 01-08: Banco + Lote + Tipo Reg
        f"       "                                  # 09-17: CNAB (Branco)
        f"2"                                        # 18-18: Tipo Inscrição (2=CNPJ)
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32: CNPJ Empresa
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52: Convênio
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57: Agência
        f"0"                                        # 58-58: DV Ag
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70: Conta
        f"{DADOS_HOSPITAL['dv_conta']:0>1}"         # 71-71: DV Conta
        f"0"                                        # 72-72: DV Ag/Conta
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102: Nome Empresa
        f"{'UNICRED':<30}"                          # 103-132: Nome Banco
        f"  "                                       # 133-142: Branco
        f"1"                                        # 143-143: Cod Remessa (1)
        f"{data_arq}"                               # 144-151: Data
        f"{hora_arq}"                               # 152-157: Hora
        f"{nsa:0>6}"                                # 158-163: Sequencial (NSA)
        f"083"                                      # 164-166: Versão Layout (083)
        f"00000"                                    # 167-171: Densidade
        f"{'':<69}"                                 # 172-240: Reservado
        f"\r\n"
    )

    # --- HEADER DE LOTE (PIX - Pagamento Fornecedor) ---
    header_lote = (
        f"13600011"                                 # 01-08: Banco + Lote (0001) + Tipo (1)
        f"C"                                        # 09-09: Operação (C=Crédito)
        f"20"                                       # 10-11: Tipo Pagamento (20=Fornecedor)
        f"45"                                       # 12-13: Forma Pagamento (45=PIX)
        f"040"                                      # 14-16: Layout Lote
        f" "                                        # 17-17: CNAB
        f"2"                                        # 18-18: Tipo Inscrição (2=CNPJ)
        f"{DADOS_HOSPITAL['cnpj']:0>14}"            # 19-32: CNPJ
        f"{DADOS_HOSPITAL['convenio']:0>20}"        # 33-52: Convênio
        f"{DADOS_HOSPITAL['agencia']:0>5}"          # 53-57: Agência
        f"0"                                        # 58-58: DV Ag
        f"{DADOS_HOSPITAL['conta']:0>12}"           # 59-70: Conta
        f"{DADOS_HOSPITAL['dv_conta']:0>1}"         # 71-71: DV Conta
        f"0"                                        # 72-72: DV Ag/Conta
        f"{DADOS_HOSPITAL['nome']:<30}"             # 73-102: Nome
        f"{'':<40}"                                 # 103-142: Mensagem 1
        f"{'':<40}"                                 # 143-182: Endereço (Opcional no header)
        f"{'':<8}"                                  # 183-190: Numero
        f"{'':<15}"                                 # 191-205: Comp
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
        valor = float(row['VALOR_PAGAMENTO'])
        valor_str = f"{int(valor * 100):0>15}"
        total_valor += valor
        
        # Tratamento da Chave PIX (Limpeza)
        chave_pix_raw = str(row['CHAVE_PIX_OU_COD_BARRAS']).strip()
        
        # Tratamento Data
        try:
            dt_obj = datetime.strptime(row['DATA_PAGAMENTO'], '%d/%m/%Y')
            dt_str = dt_obj.strftime('%d%m%Y')
        except:
            dt_str = data_arq

        # --- SEGMENTO A (Dados Bancários = ZERADOS PARA PIX) ---
        seg_a = (
            f"13600013"                             # 01-08: Banco + Lote + Tipo (3)
            f"{seq_lote:0>5}"                       # 09-13: Num Sequencial Reg
            f"A"                                    # 14-14: Segmento A
            f"000"                                  # 15-17: Tipo Movimento (000=Inclusão)
            f"009"                                  # 18-20: Câmara (009=PIX)
            f"136"                                  # 21-23: Banco Favorecido (Opcional, mas 136 ou 000)
            f"{'0':>5}"                             # 24-28: Agência (ZERADO P/ PIX)
            f" "                                    # 29-29: DV Ag
            f"{'0':>12}"                            # 30-41: Conta (ZERADO P/ PIX)
            f" "                                    # 42-42: DV Conta
            f" "                                    # 43-43: DV Ag/Conta
            f"{row['NOME_FAVORECIDO'][:30]:<30}"    # 44-73: Nome Favorecido
            f"{chave_pix_raw:<20}"                  # 74-93: Seu Nro (Uso da Empresa - Botamos a chave aqui p/ controle)
            f"{dt_str}"                             # 94-101: Data Pagamento
            f"BRL"                                  # 102-104: Moeda
            f"{'0':>15}"                            # 105-119: Qtd Moeda
            f"{valor_str}"                          # 120-134: Valor Pagamento
            f"{'':<20}"                             # 135-154: Nosso Numero Banco (Branco)
            f"{dt_str}"                             # 155-162: Data Real (Efetiva)
            f"{valor_str}"                          # 163-177: Valor Real
            f"{'':<40}"                             # 178-217: Info Comp
            f"00"                                   # 218-219: Tipo Aviso
            f"{'':<10}"                             # 220-229: Ocorrencias
            f"00"                                   # 230-231: Ocorrencias (cont)
            f"045"                                  # 232-234: DDA (Opcional)
            f"      "                               # 235-240: CNAB
            f"\r\n"
        )
        
        seq_lote += 1

        # --- SEGMENTO B (Chave PIX e Identificação) ---
        # Identifica se é CPF ou CNPJ pelo tamanho da chave
        # Para chaves aleatórias/email, usamos 0 (Outros) ou assumimos o CPF/CNPJ do cadastro
        
        tipo_insc = "1" if len(row.get('cnpj_beneficiario', '')) <= 11 else "2"
        doc_fav = ''.join(filter(str.isdigit, str(row.get('cnpj_beneficiario', ''))))

        seg_b = (
            f"13600013"                             # 01-08: Banco + Lote + Tipo
            f"{seq_lote:0>5}"                       # 09-13: Sequencial
            f"B"                                    # 14-14: Segmento B
            f"   "                                  # 15-17: CNAB
            f"{tipo_insc}"                          # 18-18: Tipo Inscrição Fav (1=CPF, 2=CNPJ)
            f"{doc_fav:0>14}"                       # 19-32: Numero Inscrição (Onde o Banco valida a chave se for CPF/CNPJ)
            f"{'':<30}"                             # 33-62: Logradouro
            f"{'0':<5}"                             # 63-67: Numero
            f"{'':<15}"                             # 68-82: Complemento
            f"{'':<15}"                             # 83-97: Bairro
            f"{'':<20}"                             # 98-117: Cidade
            f"{'00000000'}"                         # 118-125: CEP
            f"SC"                                   # 126-127: UF
            f"{'':<99}"                             # 128-226: Dados Complem (Poderia ir a chave aqui, mas Unicred lê o campo 19-32)
            f"{'':<6}"                              # 227-232: CNAB
            f"{'':<8}"                              # 233-240: CNAB
            f"\r\n"
        )
        
        seq_lote += 1
        qtd_registros += 2 # Seg A + Seg B
        detalhes += seg_a + seg_b

    # --- TRAILER DE LOTE ---
    qtd_lote_total = qtd_registros + 2 # +Header Lote +Trailer Lote
    valor_total_str = f"{int(total_valor * 100):0>18}"
    
    trailer_lote = (
        f"13600015"                                 # 01-08: Banco...
        f"         "                                # 09-17: CNAB
        f"{qtd_lote_total:0>6}"                     # 18-23: Qtd Registros Lote
        f"{valor_total_str}"                        # 24-41: Soma Valores
        f"{'0':>18}"                                # 42-59: Soma Qtd Moeda
        f"{'0':>6}"                                 # 60-65: Num Aviso Débito
        f"{'':<165}"                                # 66-230: CNAB
        f"{'':<10}"                                 # 231-240: Ocorrencias
        f"\r\n"
    )

    # --- TRAILER DE ARQUIVO ---
    qtd_arq_total = qtd_lote_total + 2 # +Header Arq +Trailer Arq
    
    trailer_arq = (
        f"13699999"                                 # 01-08: Banco...
        f"         "                                # 09-17: CNAB
        f"{1:0>6}"                                  # 18-23: Qtd Lotes
        f"{qtd_arq_total:0>6}"                      # 24-29: Qtd Registros Arq
        f"{'0':>6}"                                 # 30-35: Qtd Contas Concil
        f"{'':<205}"                                # 36-240: CNAB
        f"\r\n"
    )

    conteudo = header_arq + header_lote + detalhes + trailer_lote + trailer_arq
    return conteudo
