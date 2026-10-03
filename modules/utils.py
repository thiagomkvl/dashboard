import pandas as pd
import unicodedata

def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def limpar_ids(valor):
    if pd.isna(valor) or str(valor).strip() == "": return ""
    return "".join(filter(str.isalnum, str(valor).split('.')[0]))

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='l'):
    texto_str = remover_acentos(str(texto))
    if alinhar == 'r':
        texto_limpo = "".join(filter(str.isdigit, texto_str))
        if texto_limpo == "": texto_limpo = "0"
        res = texto_limpo[:tamanho].rjust(tamanho, '0')
    else:
        res = texto_str[:tamanho].ljust(tamanho, preenchimento)
    return res[:tamanho]

def identificar_tipo_pagamento(linha):
    dado = str(linha.get('CHAVE_PIX_OU_COD_BARRAS', ''))
    dado_limpo = "".join(filter(str.isdigit, dado))
    if len(dado_limpo) >= 44:
        return 'BOLETO'
    else:
        return 'PIX'
