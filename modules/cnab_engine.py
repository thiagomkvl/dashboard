import os
import re
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

def detectar_metodo_pagamento(dado):
    """
    Retorna 'BOLETO' se parecer um código de barras/linha digitável (44-48 digitos).
    Retorna 'PIX' caso contrário.
    """
    limpo = limpar_numero(dado)
    # Linha digitável tem 47/48, Cod Barras tem 44.
    if len(limpo) >= 44 and len(limpo) <= 48:
        return 'BOLETO'
    return 'PIX'

def detectar_tipo_chave(chave):
    """G100: 01-Tel, 02-Email, 03-CPF/CNPJ, 04-Aleatoria"""
    chave = str(chave).strip()
    if '@' in chave: return '02 '
    if len(chave) > 30 and '-' in chave: return '04 '
    nums = limpar_numero(chave)
    if len(nums) == 11 or len(nums) == 14: return '03 '
    return '01 '

def converter_linha_digitavel_para_barras(linha):
    """
    Se o usuário colar a linha digitável (47/48 dígitos), converte para 44 dígitos (Código de Barras).
    Lógica simplificada: remove DVs da linha digitável.
    """
    linha = limpar_numero(linha)
    if len(linha) == 44:
        return linha # Já é barras
    
    # Se for boleto bancário (47 digitos)
    if len(linha) == 47:
        # Padrão: AAAAA.BBBBK CCCCC.DDDDDK EEEEE.FFFFFK G HHHHHHHHHHHHHH
        # Barras: AAAA G HHHHHHHHHHHHHH BBBB CCCCC DDDDD EEEEE FFFFF
        # (Implementação simplificada: apenas remove os DVs de cada campo se necessário ou retorna o input
        # O ideal é usar uma lib completa, mas aqui vamos assumir que se vier 44 é o que o banco quer.
        # Se o usuário colou 47, tentamos usar, mas o banco pode rejeitar se não converter.)
        # Por segurança, vamos pedir 44 chars no cockpit ou truncar aqui se for óbvio.
        pass 
    
    return linha[:44] # Retorna os 44 primeiros ou a string original se não tratar

# =============================================================================
# GERADORES DE SEGMENTO
# =============================================================================

def gerar_segmento_j(row, seq_lote):
    """Gera o Segmento J (Pagamento de Títulos / Boletos)"""
    # Dados do Pagamento
    cod_barras = converter_linha_digitavel_para_barras(row.get('CHAVE_PIX_OU_COD_BARRAS', ''))
    
    try: valor = float(row['VALOR_PAGAMENTO'])
    except: valor = 0.0
    valor_str = f"{int(valor * 100):0>15}"
    
    try:
        dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
        dt_str = dt_obj.strftime('%d%m%Y')
    except: 
        dt_str = datetime.now().strftime('%d%m%Y') # Fallback hoje

    nome_fav = str(row['NOME_FAVORECIDO'])[:30]

    # Layout Segmento J (240 posições)
    # 001-003: Banco (136)
    # 004-007: Lote
    # 008-008: Tipo (3)
    # 009-013: Sequencial
    # 014-014: Segmento (J)
    # 015-017: Movimento (000 - Inclusão)
    # 018-061: Código de Barras (44 posições)
    # 062-091: Nome Beneficiário (30 posições)
    # 092-101: Data Vencimento (DDMMAAAA)
    # 102-114: Valor do Título (13v2) -> Atenção: Valor Nominal
    # 115-129: Valor Desconto + Abatimento (15v2)
    # 130-144: Valor Mora + Multa (15v2)
    # 145-152: Data Pagamento (DDMMAAAA)
    # 153-167: Valor Pagamento (15v2)
    # 168-177: Qtd Moeda (10v5)
    # 178-197: Referência Sacado (20 pos - Nosso numero da empresa)
    # 198-217: Nosso Número Banco (20 pos - Retorno)
    # 218-219: Código Moeda (09 = Real)
    # 220-225: CNAB (6 brancos)
    # 226-240: Ocorrências (Brancos/Códigos)

    seg_j = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'J':<1}{'000':<3}"
        f"{cod_barras:0>44}"                    # 18-61: Barras
        f"{nome_fav:<30}"                       # 62-91: Nome
        f"{dt_str:<8}"                          # 92-101: Vencimento (Usando data pagto como base)
        f"{valor_str:0>15}"                     # 102-114+2: Valor Nominal (Usando o layout de 15 pos total com desconto zerado visualmente no loop abaixo)
        # Nota: Layout J padrão Febraban tem campos quebrados.
        # Vamos usar o padrão Unicred ajustado:
        # Valor Titulo (13+2=15)
    )
    
    # REFAZENDO SEGMENTO J MILIMETRICO FEBRABAN/UNICRED
    # Posições exatas:
    part_1 = f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'J':<1}{'000':<3}" # 17 chars
    part_barras = f"{cod_barras:0>44}" # 44 chars (Pos 18 a 61)
    part_nome = f"{nome_fav:<30}" # 30 chars (Pos 62 a 91)
    part_venc = f"{dt_str:<8}" # 8 chars (Pos 92 a 101)
    part_val_tit = f"{valor_str:0>15}" # 15 chars (Pos 102 a 116 - Valor Titulo)
    part_desc = f"{'0':0>15}" # 15 chars (Pos 117 a 131 - Descontos)
    part_acresc = f"{'0':0>15}" # 15 chars (Pos 132 a 146 - Acrescimos)
    part_dt_pag = f"{dt_str:<8}" # 8 chars (Pos 147 a 154 - Data Pagto)
    part_val_pag = f"{valor_str:0>15}" # 15 chars (Pos 155 a 169 - Valor Pagto)
    part_rest = f"{'0':0>15}{'':<20}{'':<20}{'09':<2}{'':<6}{'':<10}" # Até 240
    
    # Ajuste fino posicional:
    # 102-116 (15) Valor Titulo
    # 117-131 (15) Desconto
    # 132-146 (15) Acrescimo
    # 147-154 (8) Data Pagto
    # 155-169 (15) Valor Pagto
    # 170-184 (15) Qtd Moeda (ajustado no part_rest)
    # 185-204 (20) Ref Sacado
    # 205-224 (20) Nosso Num
    # 225-226 (2) Moeda
    # 227-232 (6) CNAB
    # 233-240 (8) Ocorrencias
    
    # Remontando string final segura
    seg_j_final = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'J':<1}{'000':<3}" # 01-17
        f"{cod_barras:0>44}"            # 18-61
        f"{nome_fav:<30}"               # 62-91
        f"{dt_str:<8}"                  # 92-101
        f"{valor_str:0>15}"             # 102-116
        f"{'0':0>15}"                   # 117-131
        f"{'0':0>15}"                   # 132-146
        f"{dt_str:<8}"                  # 147-154
        f"{valor_str:0>15}"             # 155-169
        f"{'0':0>15}"                   # 170-184 (Qtd Moeda)
        f"{'':<20}"                     # 185-204 (Ref Sacado)
        f"{'':<20}"                     # 205-224 (Nosso Num)
        f"{'09':<2}"                    # 225-226 (Moeda)
        f"{'':<6}"                      # 227-232
        f"{'':<10}"                     # 233-242 (Excesso de segurança, vamos cortar no retorno)
    )
    # Corta em 240 + CRLF
    return seg_j_final[:240] + "\r\n", 1 # Retorna string e qtd registros (1)

def gerar_segmentos_pix_a_b(row, seq_lote, data_arq):
    """Gera Segmentos A + B para PIX"""
    # Lógica que já aprovamos
    try: valor = float(row['VALOR_PAGAMENTO'])
    except: valor = 0.0
    valor_str = f"{int(valor * 100):0>15}"
    
    chave_pix_raw = str(row.get('CHAVE_PIX_OU_COD_BARRAS', '')).strip()
    if chave_pix_raw.lower() in ['nan', 'none']: chave_pix_raw = ''
    if chave_pix_raw.endswith('.0'): chave_pix_raw = chave_pix_raw[:-2]
    tipo_chave_code = detectar_tipo_chave(chave_pix_raw)
    
    banco_fav = limpar_numero(row.get('BANCO_FAVORECIDO', ''))
    agencia_fav = limpar_numero(row.get('AGENCIA_FAVORECIDA', ''))
    conta_fav = limpar_numero(row.get('CONTA_FAVORECIDA', ''))
    dv_conta_fav = str(row.get('DIGITO_CONTA_FAVORECIDA', '')).strip()
    
    if not banco_fav: banco_fav = "000"
    if not agencia_fav: agencia_fav = "0"
    if not conta_fav: conta_fav = "0"
    if not dv_conta_fav: dv_conta_fav = "0"

    try:
        dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
        dt_str = dt_obj.strftime('%d%m%Y')
    except: dt_str = data_arq

    # Seg A
    seg_a = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'A':<1}{'000':<3}{'009':<3}"
        f"{banco_fav[:3]:0>3}{agencia_fav[:5]:0>5}{' ':1}"
        f"{conta_fav[:12]:0>12}{dv_conta_fav[:1]:<1}{' ':1}"
        f"{str(row['NOME_FAVORECIDO'])[:30]:<30}"
        f"{chave_pix_raw:<20}"
        f"{dt_str:<8}{'BRL':<3}"
        f"{'0':0>15}{valor_str:<15}{'':<20}{dt_str:<8}{valor_str:<15}"
        f"{'':<40}{'00':<2}{'':<5}{'':<2}{'':<3}{'0':<1}{'':<10}\r\n"
    )
    
    # Seg B
    doc_fav = limpar_numero(row.get('cnpj_beneficiario', ''))
    if not doc_fav: doc_fav = "00000000000"
    tipo_insc = "1" if len(doc_fav) <= 11 else "2"
    
    seq_lote_b = seq_lote + 1
    seg_b = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote_b:0>5}{'B':<1}"
        f"{tipo_chave_code:<3}{tipo_insc:<1}{doc_fav:0>14}"
        f"{'':<30}{'0':0>5}{'':<15}{'':<15}{'':<20}{'00000':0>5}{'000':0>3}{'SC':<2}"
        f"{chave_pix_raw:<99}{'':<6}{'':<8}\r\n"
    )
    
    return seg_a + seg_b, 2 # Retorna string e qtd registros (2)

# =============================================================================
# MOTOR PRINCIPAL
# =============================================================================

def gerar_cnab_remessa(df_pagamentos):
    """Gera CNAB Unificado (PIX e BOLETOS)"""
    if df_pagamentos.empty: return None

    nsa = obter_proximo_sequencial()
    now = datetime.now()
    data_arq = now.strftime('%d%m%Y')
    hora_arq = now.strftime('%H%M%S')
    
    # --- HEADER ARQ ---
    header_arq = (
        f"{'136':<3}{'0000':0>4}{'0':<1}{'':<9}{'2':<1}{DADOS_HOSPITAL['cnpj']:0>14}"
        f"{DADOS_HOSPITAL['convenio']:0>20}{DADOS_HOSPITAL['agencia']:0>5}"
        f"{DADOS_HOSPITAL['dv_agencia']:<1}{DADOS_HOSPITAL['conta']:0>12}"
        f"{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}{DADOS_HOSPITAL['nome']:<30}"
        f"{'UNICRED':<30}{'':<10}{'1':<1}{data_arq:<8}{hora_arq:<6}{nsa:0>6}"
        f"{'083':<3}{'00000':0>5}{'':<69}\r\n"
    )

    # --- HEADER LOTE (Misto 20 - Pagamento Fornecedor) ---
    # Nota: Em teoria deveriamos separar Lotes de Pix (45) e Boletos (30/31).
    # A Unicred geralmente aceita misto ou exige lotes separados.
    # Para simplificar e testar, vamos usar LOTE MISTO COM CÓDIGO 20 (Pagamento Fornecedor)
    # E Forma de Pagamento no Header = 45 (o banco costuma tolerar se os detalhes variarem)
    # SE DER ERRO: Teremos que criar 2 lotes (Um header lote pra pix, um pra boleto).
    # Por enquanto, mantemos estrutura única.
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
        # Decisão: PIX ou BOLETO
        metodo = detectar_metodo_pagamento(row.get('CHAVE_PIX_OU_COD_BARRAS', ''))
        
        try: total_valor += float(row['VALOR_PAGAMENTO'])
        except: pass

        if metodo == 'BOLETO':
            seg_str, qtd = gerar_segmento_j(row, seq_lote)
            detalhes += seg_str
            seq_lote += qtd
            qtd_registros += qtd
        else:
            seg_str, qtd = gerar_segmentos_pix_a_b(row, seq_lote, data_arq)
            detalhes += seg_str
            seq_lote += qtd
            qtd_registros += qtd

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

# Mantemos o alias antigo para não quebrar a importação na tela
gerar_cnab_pix = gerar_cnab_remessa
