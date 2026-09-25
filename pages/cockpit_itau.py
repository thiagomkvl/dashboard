import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# FUNÇÕES DE FORMATAÇÃO (PADRÃO CNAB 240 ITAÚ)
# ==========================================
def format_num(valor, tamanho):
    """Formata números com zeros à esquerda."""
    return str(valor if valor is not None else "").zfill(tamanho)[:tamanho]

def format_str(valor, tamanho):
    """Formata strings com espaços à direita e em maiúsculas."""
    return str(valor if valor is not None else "").upper().ljust(tamanho)[:tamanho]

def format_moeda(valor, tamanho):
    """Remove vírgula/ponto e preenche com zeros à esquerda (2 casas decimais)."""
    valor_float = round(float(valor), 2)
    valor_str = f"{valor_float:.2f}".replace('.', '')
    return format_num(valor_str, tamanho)

def validar_tamanho(linha, nome_registro):
    """Garante que todas as linhas possuam rigorosamente 240 caracteres."""
    if len(linha) != 240:
        raise ValueError(f"Erro no registro '{nome_registro}': gerado com {len(linha)} caracteres (esperado: 240).")
    return linha

# ==========================================
# GERADORES DE REGISTRO - ITAÚ SISPAG
# ==========================================
def gerar_header_arquivo(empresa, seq_arquivo=1):
    data_hoje = datetime.now().strftime("%d%m%Y")
    hora_hoje = datetime.now().strftime("%H%M%S")
    
    linha = (
        "341" +                             # 001-003: Código do Banco Itaú
        "0000" +                            # 004-007: Lote Padrão (0000)
        "0" +                               # 008-008: Tipo de Registro (0)
        format_str("", 6) +                 # 009-014: Brancos
        "080" +                             # 015-017: Layout Arquivo
        "2" +                               # 018-018: Inscrição da Empresa (2=CNPJ)
        format_num(empresa['cnpj'], 14) +   # 019-032: CNPJ
        format_str("", 20) +                # 033-052: Brancos
        format_num(empresa['agencia'], 5) + # 053-057: Agência
        " " +                               # 058-058: Branco
        format_num(empresa['conta'], 12) +  # 059-070: Conta
        " " +                               # 071-071: Branco
        format_num(empresa['dac'], 1) +     # 072-072: DAC
        format_str(empresa['nome'], 30) +   # 073-102: Nome da Empresa
        format_str("BANCO ITAU SA", 30) +   # 103-132: Nome do Banco
        format_str("", 10) +                # 133-142: Brancos
        "1" +                               # 143-143: 1=Remessa
        data_hoje +                         # 144-151: Data de Geração (DDMMAAAA)
        hora_hoje +                         # 152-157: Hora de Geração (HHMMSS)
        format_num("", 9) +                 # 158-166: Zeros
        format_num("1600", 5) +             # 167-171: Densidade
        format_str("", 69)                  # 172-240: Brancos
    )
    return validar_tamanho(linha, "Header de Arquivo")

def gerar_header_lote(empresa):
    linha = (
        "341" +                             # 001-003: Banco Itaú
        "0001" +                            # 004-007: Lote Serviço (0001)
        "1" +                               # 008-008: Tipo de Registro (1)
        "C" +                               # 009-009: C=Crédito
        "20" +                              # 010-011: Tipo de Pagto (20 = Fornecedores)
        "41" +                              # 012-013: Forma de Pagto (41 = PIX Transferência)
        "040" +                             # 014-016: Layout do Lote
        " " +                               # 017-017: Branco
        "2" +                               # 018-018: 2=CNPJ
        format_num(empresa['cnpj'], 14) +   # 019-032: CNPJ
        format_str("", 4) +                 # 033-036: Identificação Lançamento
        format_str("", 16) +                # 037-052: Brancos
        format_num(empresa['agencia'], 5) + # 053-057: Agência
        " " +                               # 058-058: Branco
        format_num(empresa['conta'], 12) +  # 059-070: Conta
        " " +                               # 071-071: Branco
        format_num(empresa['dac'], 1) +     # 072-072: DAC
        format_str(empresa['nome'], 30) +   # 073-102: Nome Empresa
        format_str("PAGAMENTO PIX", 30) +   # 103-132: Finalidade Lote
        format_str("", 10) +                # 133-142: Histórico Conta
        format_str(empresa['endereco'], 30)+# 143-172: Endereço
        format_num(empresa['numero'], 5) +  # 173-177: Número
        format_str("", 15) +                # 178-192: Complemento
        format_str(empresa['cidade'], 20) + # 193-212: Cidade
        format_num(empresa['cep'], 8) +     # 213-220: CEP
        format_str(empresa['uf'], 2) +      # 221-222: Estado
        format_str("", 8) +                 # 223-230: Brancos
        format_str("", 10)                  # 231-240: Ocorrências
    )
    return validar_tamanho(linha, "Header de Lote")

def gerar_segmento_a(pagamento, num_registro):
    # Formatação zerada de Agência/Conta para pagamento via Chave PIX (Pos 024 a 043)
    dados_bancarios_fav = "00000 000000000000 0" 
    
    linha = (
        "341" +                             # 001-003: Banco
        "0001" +                            # 004-007: Lote
        "3" +                               # 008-008: Tipo de Registro (3 = Detalhe)
        format_num(num_registro, 5) +       # 009-013: Número do Registro no Lote
        "A" +                               # 014-014: Segmento A
        "000" +                             # 015-017: Tipo de Movimentação (000 = Inclusão)
        "000" +                             # 018-020: Câmara (000 para PIX)
        format_num(pagamento['banco_fav'], 3) + # 021-023: Banco Favorecido (000 p/ PIX Chave)
        dados_bancarios_fav +               # 024-043: Agência e Conta Zeradas (20 posições)
        format_str(pagamento['nome_fav'], 30) + # 044-073: Nome Favorecido
        format_str(pagamento['seu_numero'], 20) + # 074-093: Seu Número / ID Doc
        format_num(pagamento['data_pagto'], 8) +  # 094-101: Data de Pagto (DDMMAAAA)
        "009" +                             # 102-104: Moeda (009 p/ PIX)
        format_num(0, 15) +                 # 105-119: ISPB (8), Complemento (2) e Zeros (5) -> Total 15 Zeros numéricos
        format_moeda(pagamento['valor'], 15) + # 120-134: Valor Pagto
        format_str("", 15) +                # 135-149: Nosso Número (Banco)
        format_str("", 5) +                 # 150-154: Brancos
        format_num("", 8) +                 # 155-162: Data Efetiva
        format_moeda(0, 15) +               # 163-177: Valor Efetivo
        format_str("", 20) +                # 178-197: Finalidade (Histórico)
        format_num("", 6) +                 # 198-203: Zeros (Retorno)
        format_num(pagamento['cnpj_cpf_fav'], 14) + # 204-217: CPF/CNPJ Favorecido
        format_str("", 2) +                 # 218-219: Status
        format_str("", 5) +                 # 220-224: Finalidade TED
        format_str("", 5) +                 # 225-229: Brancos
        "0" +                               # 230-230: Aviso
        format_str("", 10)                  # 231-240: Ocorrências
    )
    return validar_tamanho(linha, f"Segmento A (Registro {num_registro})")

def gerar_segmento_b_pix(pagamento, num_registro):
    linha = (
        "341" +                             # 001-003: Banco
        "0001" +                            # 004-007: Lote
        "3" +                               # 008-008: Tipo de Registro (3)
        format_num(num_registro, 5) +       # 009-013: Número do Registro no Lote
        "B" +                               # 014-014: Segmento B
        "   " +                             # 015-017: Uso Exclusivo (Brancos obrigatórios)
        str(pagamento['tipo_doc_fav']) +    # 018-018: Inscrição Fav (1=CPF, 2=CNPJ)
        format_num(pagamento['cnpj_cpf_fav'], 14) + # 019-032: CNPJ/CPF (14 posições)
        format_str("", 30) +                # 033-062: Logradouro (30 brancos)
        "00000" +                           # 063-067: Número do local (5 ZEROS)
        format_str("", 15) +                # 068-082: Complemento (15 brancos)
        format_str("", 15) +                # 083-097: Bairro (15 brancos)
        format_str("", 20) +                # 098-117: Cidade (20 brancos)
        "00000000" +                        # 118-125: CEP (8 ZEROS)
        "  " +                              # 126-127: UF (2 brancos)
        format_str(pagamento['chave_pix'], 100) + # 128-227: Chave PIX (100 posições)
        format_str("", 13)                  # 228-240: Brancos finais (13 posições)
    )
    return validar_tamanho(linha, f"Segmento B (Registro {num_registro})")

def gerar_trailer_lote(qtd_registros, valor_total):
    linha = (
        "341" +                             # 001-003: Banco
        "0001" +                            # 004-007: Lote
        "5" +                               # 008-008: Trailer de Lote
        format_str("", 9) +                 # 009-017: Brancos
        format_num(qtd_registros, 6) +      # 018-023: Qtd Registros no Lote
        format_moeda(valor_total, 18) +     # 024-041: Somatório dos Valores
        format_num("", 18) +                # 042-059: Zeros
        format_str("", 171) +               # 060-230: Brancos
        format_str("", 10)                  # 231-240: Ocorrências
    )
    return validar_tamanho(linha, "Trailer de Lote")

def gerar_trailer_arquivo(qtd_lotes, qtd_registros_arq):
    linha = (
        "341" +                             # 001-003: Banco
        "9999" +                            # 004-007: Lote 9999
        "9" +                               # 008-008: Trailer de Arquivo
        format_str("", 9) +                 # 009-017: Brancos
        format_num(qtd_lotes, 6) +          # 018-023: Qtd Lotes
        format_num(qtd_registros_arq, 6) +  # 024-029: Qtd Registros Arquivo
        format_str("", 211)                 # 030-240: Brancos
    )
    return validar_tamanho(linha, "Trailer de Arquivo")

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerador CNAB 240 - Itaú PIX", layout="wide")

st.title("Motor CNAB 240 - Itaú SISPAG (Foco PIX)")
st.markdown("Interface para geração de lotes de pagamento PIX (Transferência por Chave) no padrão Itaú SISPAG.")

st.sidebar.header("Dados do Hospital (Pagador)")
empresa = {
    'cnpj': st.sidebar.text_input("CNPJ (Apenas números)", "04238968000101"), 
    'agencia': st.sidebar.text_input("Agência", "6305"),
    'conta': st.sidebar.text_input("Conta", "01566"),
    'dac': st.sidebar.text_input("Dígito Conta (DAC)", "8"),
    'nome': st.sidebar.text_input("Razão Social", "HOSPITAL SOS CARDIO SA"),
    'endereco': st.sidebar.text_input("Endereço", "RODOVIA SC 401 KM 1"),
    'numero': st.sidebar.text_input("Número", "121"),
    'cidade': st.sidebar.text_input("Cidade", "FLORIANOPOLIS"),
    'cep': st.sidebar.text_input("CEP", "88032005"),
    'uf': st.sidebar.text_input("UF", "SC")
}

st.header("Lançamentos de Pagamento PIX")

data_inicial = {
    "Seu Número": ["DOC001", "DOC002"],
    "Nome Favorecido": ["FORNECEDOR MEDICAMENTOS LTDA", "SERVICOS MEDICOS LTDA"],
    "CPF/CNPJ Favorecido": ["11111111000191", "22222222000191"],
    "Tipo Doc (1=CPF, 2=CNPJ)": ["2", "2"],
    "Chave PIX": ["11111111000191", "22222222000191"],
    "Valor": [1500.50, 3400.00],
    "Data Pagto (DDMMAAAA)": [datetime.now().strftime("%d%m%Y"), datetime.now().strftime("%d%m%Y")]
}

df_pagamentos = pd.DataFrame(data_inicial)
df_editado = st.data_editor(df_pagamentos, num_rows="dynamic")

if st.button("Gerar Remessa CNAB 240 (PIX)"):
    try:
        linhas_cnab = []
        
        # 1. Header do Arquivo
        linhas_cnab.append(gerar_header_arquivo(empresa, 1))
        
        # 2. Header do Lote (Lote 1)
        linhas_cnab.append(gerar_header_lote(empresa))
        
        num_registro_lote = 1
        valor_total_lote = 0.0
        
        # 3. Lançamentos PIX (Segmentos A e B)
        for index, row in df_editado.iterrows():
            pagamento = {
                'seu_numero': str(row["Seu Número"]),
                'nome_fav': str(row["Nome Favorecido"]),
                'cnpj_cpf_fav': str(row["CPF/CNPJ Favorecido"]),
                'tipo_doc_fav': str(row["Tipo Doc (1=CPF, 2=CNPJ)"]),
                'banco_fav': "000",
                'data_pagto': str(row["Data Pagto (DDMMAAAA)"]),
                'valor': float(row["Valor"]),
                'chave_pix': str(row["Chave PIX"])
            }
            
            # Segmento A
            linhas_cnab.append(gerar_segmento_a(pagamento, num_registro_lote))
            num_registro_lote += 1
            
            # Segmento B (Informa a Chave PIX)
            linhas_cnab.append(gerar_segmento_b_pix(pagamento, num_registro_lote))
            num_registro_lote += 1
            
            valor_total_lote += pagamento['valor']
            
        # 4. Trailer do Lote
        qtd_registros_lote = num_registro_lote + 1 
        linhas_cnab.append(gerar_trailer_lote(qtd_registros_lote, valor_total_lote))
        
        # 5. Trailer do Arquivo
        qtd_lotes = 1
        qtd_registros_arq = len(linhas_cnab) + 1
        linhas_cnab.append(gerar_trailer_arquivo(qtd_lotes, qtd_registros_arq))
        
        # Concatenação com quebra CRLF (\r\n) em todas as linhas
        cnab_texto = "\r\n".join(linhas_cnab) + "\r\n"
        
        st.success("Remessa Gerada com Sucesso! Ajustes de preenchimento numérico aplicados no Segmento B.")
        st.text_area("Pré-visualização CNAB 240", cnab_texto, height=300)
        
        st.download_button(
            label="Download Arquivo de Remessa (.REM)",
            data=cnab_texto,
            file_name=f"ITAU_PIX_{datetime.now().strftime('%d%m%Y_%H%M%S')}.REM",
            mime="text/plain"
        )
    except Exception as e:
        st.error(f"Erro na geração do arquivo: {str(e)}")
