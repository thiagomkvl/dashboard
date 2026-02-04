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
    if not valor: return ""
    return ''.join(filter(str.isdigit, str(valor)))

def detectar_tipo_transacao(dado):
    """
    Analisa o dado e retorna:
    - 'PIX': Se for chave Pix
    - 'BOLETO_PROPRIO': Se for boleto Unicred (Inicia com 136)
    - 'BOLETO_EXTERNO': Se for boleto de outros bancos
    """
    limpo = limpar_numero(dado)
    
    # Lógica de Boleto (44 a 48 dígitos)
    if len(limpo) >= 44 and len(limpo) <= 48:
        cod_barras = converter_linha_digitavel_para_barras(limpo)
        if cod_barras.startswith('136'):
            return 'BOLETO_PROPRIO'
        return 'BOLETO_EXTERNO'
        
    return 'PIX'

def detectar_tipo_chave(chave):
    chave = str(chave).strip()
    if '@' in chave: return '02 '
    if len(chave) > 30 and '-' in chave: return '04 '
    nums = limpar_numero(chave)
    if len(nums) == 11 or len(nums) == 14: return '03 '
    return '01 '

def converter_linha_digitavel_para_barras(linha):
    linha = limpar_numero(linha)
    if len(linha) == 44: return linha 
    
    # Boleto Bancário (47 dígitos)
    if len(linha) == 47:
        c1 = linha[0:9]
        c2 = linha[10:20]
        c3 = linha[21:31]
        dv_geral = linha[32]
        fator_valor = linha[33:]
        return c1[0:3] + c1[3:4] + dv_geral + fator_valor + c1[4:9] + c2 + c3
        
    # Boleto Concessionária (48 dígitos)
    if len(linha) == 48:
        return linha[0:11] + linha[12:23] + linha[24:35] + linha[36:47]

    return linha[:44]

# =============================================================================
# GERADORES DE SEGMENTO
# =============================================================================

def gerar_segmento_j(row, seq_lote_interno):
    """Gera Segmento J (Dados do Título)"""
    cod_barras = converter_linha_digitavel_para_barras(row.get('CHAVE_PIX_OU_COD_BARRAS', ''))
    
    try: valor = float(row['VALOR_PAGAMENTO'])
    except: valor = 0.0
    valor_str = f"{int(valor * 100):0>15}"
    
    try:
        dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
        dt_str = dt_obj.strftime('%d%m%Y')
    except: dt_str = datetime.now().strftime('%d%m%Y')

    nome_fav = str(row['NOME_FAVORECIDO'])

    seg_j = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote_interno:0>5}{'J':<1}{'000':<3}"
        f"{cod_barras[:44]:0>44}"       # 18-61
        f"{nome_fav[:30]:<30}"          # 62-91
        f"{dt_str:<8}"                  # 92-101: Vencimento
        f"{valor_str:0>15}"             # 102-116: Valor Nominal
        f"{'0':0>15}"                   # 117-131: Desconto
        f"{'0':0>15}"                   # 132-146: Juros
        f"{dt_str:<8}"                  # 147-154: Data Pagamento
        f"{valor_str:0>15}"             # 155-169: Valor Pagamento
        f"{'0':0>15}"                   # 170-184: Qtd Moeda
        f"{'':<20}"                     # 185-204
        f"{'':<20}"                     # 205-224
        f"{'09':<2}"                    # 225-226: Real
        f"{'':<6}"                      # 227-232
        f"{'':<8}"                      # 233-240
    )
    return seg_j[:240] + "\r\n"

def gerar_segmento_j52(row, seq_lote_interno):
    """Gera Segmento J-52 (Dados do Cedente/Sacado)"""
    doc_fav = limpar_numero(row.get('cnpj_beneficiario', ''))
    if not doc_fav: doc_fav = "00000000000"
    tipo_insc_cedente = "1" if len(doc_fav) <= 11 else "2"
    nome_fav = str(row['NOME_FAVORECIDO'])
    
    doc_pagador = DADOS_HOSPITAL['cnpj']
    tipo_insc_pagador = "2" # CNPJ
    nome_pagador = DADOS_HOSPITAL['nome']

    seg_j52 = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote_interno:0>5}{'J':<1}{'   ':<3}"
        f"{'52':<2}"                    # 18-19: Opcional 52
        f"{tipo_insc_cedente:<1}"       # 20-20
        f"{doc_fav[:14]:0>15}"          # 21-35
        f"{nome_fav[:40]:<40}"          # 36-75
        f"{tipo_insc_pagador:<1}"       # 76-76
        f"{doc_pagador[:14]:0>15}"      # 77-91
        f"{nome_pagador[:40]:<40}"      # 92-131
        f"{'':<53}"                     # 132-184
        f"{'':<56}"                     # 185-240
    )
    return seg_j52[:240] + "\r\n"

def gerar_segmentos_pix_a_b(row, seq_lote_interno, data_arq):
    """Gera Segmentos A + B para PIX"""
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
    
    eh_conta_zerada = False
    try:
        if not conta_fav or int(conta_fav) == 0: eh_conta_zerada = True
    except: eh_conta_zerada = True

    if not banco_fav or int(banco_fav) == 0: banco_fav = "000"
    if not agencia_fav: agencia_fav = "0"
    if eh_conta_zerada: conta_fav = "1"
    if not dv_conta_fav: dv_conta_fav = "0"

    try:
        dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
        dt_str = dt_obj.strftime('%d%m%Y')
    except: dt_str = data_arq

    nome_fav = str(row['NOME_FAVORECIDO'])

    seg_a = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote_interno:0>5}{'A':<1}{'000':<3}{'009':<3}"
        f"{banco_fav[:3]:0>3}{agencia_fav[:5]:0>5}{' ':1}"
        f"{conta_fav[:12]:0>12}{dv_conta_fav[:1]:<1}{' ':1}"
        f"{nome_fav[:30]:<30}{chave_pix_raw[:20]:<20}"
        f"{dt_str:<8}{'BRL':<3}"
        f"{'0':0>15}{valor_str:<15}{'':<20}{dt_str:<8}{valor_str:<15}"
        f"{'':<40}{'00':<2}{'':<5}{'':<2}{'':<3}{'0':<1}{'':<10}"
    )
    seg_a = seg_a[:240] + "\r\n"

    doc_fav = limpar_numero(row.get('cnpj_beneficiario', ''))
    if not doc_fav: doc_fav = "00000000000"
    tipo_insc = "1" if len(doc_fav) <= 11 else "2"
    
    seq_lote_b = seq_lote_interno + 1
    
    seg_b = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote_b:0>5}{'B':<1}"
        f"{tipo_chave_code[:3]:<3}{tipo_insc[:1]:<1}{doc_fav[:14]:0>14}"
        f"{'':<30}{'0':0>5}{'':<15}{'':<15}{'':<20}{'00000':0>5}{'000':0>3}{'SC':<2}"
        f"{chave_pix_raw[:99]:<99}{'':<6}{'':<8}"
    )
    seg_b = seg_b[:240] + "\r\n"
    
    return seg_a + seg_b, 2

def gerar_header_lote(num_lote, forma_lancamento, versao_layout='046'):
    """Gera Header de Lote (Padrão 046 para tudo)"""
    return (
        f"{'136':<3}{num_lote:0>4}{'1':<1}{'C':<1}{'20':<2}{forma_lancamento:<2}{versao_layout:<3}{'':<1}{'2':<1}"
        f"{DADOS_HOSPITAL['cnpj']:0>14}{DADOS_HOSPITAL['convenio']:0>20}"
        f"{DADOS_HOSPITAL['agencia']:0>5}{DADOS_HOSPITAL['dv_agencia']:<1}"
        f"{DADOS_HOSPITAL['conta']:0>12}{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}"
        f"{DADOS_HOSPITAL['nome']:<30}{'PAGAMENTO FORNECEDORES':<40}"
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
# MOTOR PRINCIPAL (MULTI-LOTE ESTRUTURADO)
# =============================================================================

def gerar_cnab_remessa(df_pagamentos):
    """Gera CNAB com separação total de lotes e versões atualizadas"""
    if df_pagamentos.empty: return None

    nsa = obter_proximo_sequencial()
    now = datetime.now()
    data_arq = now.strftime('%d%m%Y')
    hora_arq = now.strftime('%H%M%S')
    
    # Header Arquivo
    content = (
        f"{'136':<3}{'0000':0>4}{'0':<1}{'':<9}{'2':<1}{DADOS_HOSPITAL['cnpj']:0>14}"
        f"{DADOS_HOSPITAL['convenio']:0>20}{DADOS_HOSPITAL['agencia']:0>5}"
        f"{DADOS_HOSPITAL['dv_agencia']:<1}{DADOS_HOSPITAL['conta']:0>12}"
        f"{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}{DADOS_HOSPITAL['nome']:<30}"
        f"{'UNICRED':<30}{'':<10}{'1':<1}{data_arq:<8}{hora_arq:<6}{nsa:0>6}"
        f"{'083':<3}{'00000':0>5}{'':<69}\r\n"
    )[:242]

    # SEPARAÇÃO EM 3 GRUPOS
    lotes = {
        'PIX': [],              # Forma 45
        'BOLETO_PROPRIO': [],   # Forma 30
        'BOLETO_EXTERNO': []    # Forma 31
    }
    
    for _, row in df_pagamentos.iterrows():
        tipo = detectar_tipo_transacao(row.get('CHAVE_PIX_OU_COD_BARRAS', ''))
        lotes[tipo].append(row)
            
    num_lote_arq = 1
    total_registros_arquivo = 0

    # --- PROCESSADOR DE LOTES ---
    # Definição das Formas de Lançamento
    config_lotes = [
        ('BOLETO_PROPRIO', '30'), # Títulos do Próprio Banco
        ('BOLETO_EXTERNO', '31'), # Títulos de Outros Bancos
        ('PIX', '45')             # Pix Transferência
    ]

    for chave_lote, forma_lancamento in config_lotes:
        itens = lotes[chave_lote]
        if not itens: continue # Pula se vazio

        # Gera Header do Lote (Versão 046 para todos para evitar "Manutenção" em legado)
        content += gerar_header_lote(num_lote_arq, forma_lancamento, '046')
        
        seq_lote_interno = 1
        qtd_regs_lote = 0
        total_valor_lote = 0
        
        for row in itens:
            if chave_lote == 'PIX':
                # Gera PIX (A + B)
                seg_str, qtd = gerar_segmentos_pix_a_b(row, seq_lote_interno, data_arq)
            else:
                # Gera BOLETO (J + J52)
                seg_j = gerar_segmento_j(row, seq_lote_interno)
                seq_lote_interno += 1
                seg_j52 = gerar_segmento_j52(row, seq_lote_interno)
                seg_str = seg_j + seg_j52
                qtd = 2

            # Patch do Número do Lote nas linhas geradas
            lines = seg_str.split('\r\n')
            seg_ajustado = ""
            for line in lines:
                if len(line) > 10:
                    # Posições 04-07 é o lote
                    line_ajustada = line[:3] + f"{num_lote_arq:0>4}" + line[7:]
                    seg_ajustado += line_ajustada + "\r\n"
            
            content += seg_ajustado
            
            # Incrementadores
            if chave_lote == 'PIX': 
                seq_lote_interno += 2 # Já incrementei internamente no pix? Não, a func pix retorna 2 linhas mas pede seq inicial
            else:
                pass # J e J52 já incrementaram a variavel seq_lote_interno manualmente acima
                
            qtd_regs_lote += qtd
            try: total_valor_lote += float(row['VALOR_PAGAMENTO'])
            except: pass
            
        content += gerar_trailer_lote(num_lote_arq, qtd_regs_lote, total_valor_lote)
        total_registros_arquivo += (qtd_regs_lote + 2)
        num_lote_arq += 1

    # Trailer Arquivo
    trailer_arq = (
        f"{'136':<3}{'9999':<4}{'9':<1}{'':<9}{'000001':0>6}"
        f"{total_registros_arquivo+2:0>6}{'000000':0>6}{'':<205}\r\n"
    )[:242]
    
    content += trailer_arq

    return content

gerar_cnab_pix = gerar_cnab_remessa
