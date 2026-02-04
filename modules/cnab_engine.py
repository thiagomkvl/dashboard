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
    """Retorna 'BOLETO' ou 'PIX'"""
    limpo = limpar_numero(dado)
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
    linha = limpar_numero(linha)
    if len(linha) == 44: return linha 
    return linha[:44] 

# =============================================================================
# GERADORES DE SEGMENTO (COM BLINDAGEM DE TAMANHO [:N])
# =============================================================================

def gerar_segmento_j(row, seq_lote):
    """Gera Segmento J (Boletos)"""
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
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'J':<1}{'000':<3}" # 01-17
        f"{cod_barras[:44]:0>44}"       # 18-61: Barras
        f"{nome_fav[:30]:<30}"          # 62-91: Nome
        f"{dt_str:<8}"                  # 92-101
        f"{valor_str:0>15}"             # 102-116
        f"{'0':0>15}"                   # 117-131
        f"{'0':0>15}"                   # 132-146
        f"{dt_str:<8}"                  # 147-154
        f"{valor_str:0>15}"             # 155-169
        f"{'0':0>15}"                   # 170-184
        f"{'':<20}"                     # 185-204
        f"{'':<20}"                     # 205-224
        f"{'09':<2}"                    # 225-226
        f"{'':<6}"                      # 227-232
        f"{'':<8}"                      # 233-240
    )
    return seg_j[:240] + "\r\n", 1

def gerar_segmentos_pix_a_b(row, seq_lote, data_arq):
    """Gera Segmentos A + B para PIX (BLINDADO & COM FALLBACK DUMMY ROBUSTO)"""
    try: valor = float(row['VALOR_PAGAMENTO'])
    except: valor = 0.0
    valor_str = f"{int(valor * 100):0>15}"
    
    chave_pix_raw = str(row.get('CHAVE_PIX_OU_COD_BARRAS', '')).strip()
    if chave_pix_raw.lower() in ['nan', 'none']: chave_pix_raw = ''
    if chave_pix_raw.endswith('.0'): chave_pix_raw = chave_pix_raw[:-2]
    tipo_chave_code = detectar_tipo_chave(chave_pix_raw)
    
    # Extrai dados do DF
    banco_fav = limpar_numero(row.get('BANCO_FAVORECIDO', ''))
    agencia_fav = limpar_numero(row.get('AGENCIA_FAVORECIDA', ''))
    conta_fav = limpar_numero(row.get('CONTA_FAVORECIDA', ''))
    dv_conta_fav = str(row.get('DIGITO_CONTA_FAVORECIDA', '')).strip()
    
    # --- LÓGICA DE FALLBACK BLINDADA ---
    # Verifica matematicamente se é zero (pega 0, 00, 000, 0000...)
    eh_conta_zerada = False
    try:
        if not conta_fav:
            eh_conta_zerada = True
        elif int(conta_fav) == 0:
            eh_conta_zerada = True
    except:
        eh_conta_zerada = True # Se não for número, força dummy

    if not banco_fav or int(banco_fav) == 0: banco_fav = "000"
    if not agencia_fav: agencia_fav = "0"
    
    # APLICAR DUMMY SE CONTA FOR ZERADA
    if eh_conta_zerada:
        conta_fav = "1"
    
    if not dv_conta_fav: dv_conta_fav = "0"

    try:
        dt_obj = datetime.strptime(str(row['DATA_PAGAMENTO']), '%d/%m/%Y')
        dt_str = dt_obj.strftime('%d%m%Y')
    except: dt_str = data_arq

    nome_fav = str(row['NOME_FAVORECIDO'])

    # --- SEGMENTO A ---
    seg_a = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote:0>5}{'A':<1}{'000':<3}{'009':<3}"
        f"{banco_fav[:3]:0>3}"                  # 21-23
        f"{agencia_fav[:5]:0>5}"                # 24-28
        f"{' ':1}"                              # 29-29
        f"{conta_fav[:12]:0>12}"                # 30-41 (AGORA VAI 1 COM CERTEZA)
        f"{dv_conta_fav[:1]:<1}"                # 42-42
        f"{' ':1}"                              # 43-43
        f"{nome_fav[:30]:<30}"                  # 44-73
        f"{chave_pix_raw[:20]:<20}"             # 74-93
        f"{dt_str:<8}{'BRL':<3}"
        f"{'0':0>15}{valor_str:<15}{'':<20}{dt_str:<8}{valor_str:<15}"
        f"{'':<40}{'00':<2}{'':<5}{'':<2}{'':<3}{'0':<1}{'':<10}"
    )
    seg_a = seg_a[:240] + "\r\n"

    # --- SEGMENTO B ---
    doc_fav = limpar_numero(row.get('cnpj_beneficiario', ''))
    if not doc_fav: doc_fav = "00000000000"
    tipo_insc = "1" if len(doc_fav) <= 11 else "2"
    
    seq_lote_b = seq_lote + 1
    
    seg_b = (
        f"{'136':<3}{'0001':0>4}{'3':<1}{seq_lote_b:0>5}{'B':<1}"
        f"{tipo_chave_code[:3]:<3}"             # 15-17
        f"{tipo_insc[:1]:<1}"                   # 18-18
        f"{doc_fav[:14]:0>14}"                  # 19-32
        f"{'':<30}{'0':0>5}{'':<15}{'':<15}{'':<20}{'00000':0>5}{'000':0>3}{'SC':<2}"
        f"{chave_pix_raw[:99]:<99}"             # 128-226
        f"{'':<6}{'':<8}"                       # 227-240
    )
    seg_b = seg_b[:240] + "\r\n"
    
    return seg_a + seg_b, 2

# =============================================================================
# MOTOR PRINCIPAL
# =============================================================================

def gerar_cnab_remessa(df_pagamentos):
    """Gera CNAB Unificado"""
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
        f"{'083':<3}{'00000':0>5}{'':<69}"
    )
    header_arq = header_arq[:240] + "\r\n"

    # --- HEADER LOTE ---
    header_lote = (
        f"{'136':<3}{'0001':0>4}{'1':<1}{'C':<1}{'20':<2}{'45':<2}{'046':<3}{'':<1}{'2':<1}"
        f"{DADOS_HOSPITAL['cnpj']:0>14}{DADOS_HOSPITAL['convenio']:0>20}"
        f"{DADOS_HOSPITAL['agencia']:0>5}{DADOS_HOSPITAL['dv_agencia']:<1}"
        f"{DADOS_HOSPITAL['conta']:0>12}{DADOS_HOSPITAL['dv_conta']:<1}{' ':1}"
        f"{DADOS_HOSPITAL['nome']:<30}{'PAGAMENTO FORNECEDORES':<40}"
        f"{DADOS_HOSPITAL['logradouro']:<30}{DADOS_HOSPITAL['numero']:0>5}"
        f"{DADOS_HOSPITAL['complemento']:<15}{DADOS_HOSPITAL['cidade']:<20}"
        f"{DADOS_HOSPITAL['cep']:0>5}{DADOS_HOSPITAL['cep_sufixo']:0>3}"
        f"{DADOS_HOSPITAL['uf']:<2}{'':<8}{'':<10}"
    )
    header_lote = header_lote[:240] + "\r\n"

    detalhes = ""
    qtd_registros = 0
    total_valor = 0
    seq_lote = 1

    for _, row in df_pagamentos.iterrows():
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
        f"{valor_total_str:<18}{'0':0>18}{'0':0>6}{'':<165}{'':<10}"
    )
    trailer_lote = trailer_lote[:240] + "\r\n"

    trailer_arq = (
        f"{'136':<3}{'9999':<4}{'9':<1}{'':<9}{'000001':0>6}"
        f"{qtd_lote_total+2:0>6}{'000000':0>6}{'':<205}"
    )
    trailer_arq = trailer_arq[:240] + "\r\n"

    return header_arq + header_lote + detalhes + trailer_lote + trailer_arq

gerar_cnab_pix = gerar_cnab_remessa
