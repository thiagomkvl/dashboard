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
    
    # --- HEADER ARQUIVO ---
    header_arq = (
        f"13600000       2{DADOS_HOSPITAL['cnpj']:0>14}{DADOS_HOSPITAL['convenio']:0>20}"
        f"{DADOS_HOSPITAL['agencia']:0>5}0{DADOS_HOSPITAL['conta']:0>12}{DADOS_HOSPITAL['dv_conta']:0>1}0"
        f"{DADOS_HOSPITAL['nome']:<30}{'UNICRED':<30}  1{data_arq}{hora_arq}{nsa:0>6}08300000{'':<69}\r\n"
    )

    # --- HEADER LOTE ---
    header_lote = (
        f"13600011C2045040 2{DADOS_HOSPITAL['cnpj']:0>14}{DADOS_HOSPITAL['convenio']:0>20}"
        f"{DADOS_HOSPITAL['agencia']:0>5}0{DADOS_HOSPITAL['conta']:0>12}{DADOS_HOSPITAL['dv_conta']:0>1}0"
        f"{DADOS_HOSPITAL['nome']:<30}{'':<40}{'':<40}{'':<8}{'':<15}{'':<20}{'00000000'}{'SC'}{'':<5}\r\n"
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

        # --- SEGMENTO A ---
        seg_a = (
            f"13600013{seq_lote:0>5}A000009136{'0':>5} {'0':>12}  {str(row['NOME_FAVORECIDO'])[:30]:<30}"
            f"{chave_pix_raw:<20}{dt_str}BRL{'0':>15}{valor_str}{'':<20}{dt_str}{valor_str}"
            f"{'':<40}00{'':<10}00045      \r\n"
        )
        seq_lote += 1

        # --- SEGMENTO B (CORREÇÃO DO ERRO AQUI) ---
        # 1. Converte para string forçada
        raw_doc = str(row.get('cnpj_beneficiario', '')).strip()
        # 2. Remove '.0' se o pandas leu como float
        if raw_doc.endswith('.0'): raw_doc = raw_doc[:-2]
        # 3. Mantém apenas números
        doc_fav = ''.join(filter(str.isdigit, raw_doc))
        # 4. Define tipo (CPF=1, CNPJ=2) baseado no tamanho LIMPO
        tipo_insc = "1" if len(doc_fav) <= 11 else "2"

        seg_b = (
            f"13600013{seq_lote:0>5}B   {tipo_insc}{doc_fav:0>14}{'':<30}{'0':<5}{'':<15}{'':<15}"
            f"{'':<20}{'00000000'}SC{'':<99}{'':<6}{'':<8}\r\n"
        )
        
        seq_lote += 1
        qtd_registros += 2
        detalhes += seg_a + seg_b

    # --- TRAILERS ---
    qtd_lote_total = qtd_registros + 2
    valor_total_str = f"{int(total_valor * 100):0>18}"
    
    trailer_lote = f"13600015         {qtd_lote_total:0>6}{valor_total_str}{'0':>18}{'0':>6}{'':<165}{'':<10}\r\n"
    trailer_arq = f"13699999         {1:0>6}{qtd_lote_total+2:0>6}{'0':>6}{'':<205}\r\n"

    return header_arq + header_lote + detalhes + trailer_lote + trailer_arq
