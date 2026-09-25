import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# FUNÇÕES DE FORMATAÇÃO (PADRÃO CNAB 240)
# ==========================================
def format_num(valor, tamanho):
    """Formata números com zeros à esquerda."""
    return str(valor).zfill(tamanho)[:tamanho]

def format_str(valor, tamanho):
    """Formata strings com espaços à direita e em maiúsculas."""
    return str(valor).upper().ljust(tamanho)[:tamanho]

def format_moeda(valor, tamanho):
    """Remove vírgula/ponto e preenche com zeros à esquerda (2 casas decimais)."""
    valor_float = round(float(valor), 2)
    valor_str = f"{valor_float:.2f}".replace('.', '')
    return format_num(valor_str, tamanho)

# ==========================================
# GERADORES DE REGISTRO - ITAÚ SISPAG
# ==========================================
def gerar_header_arquivo(empresa, seq_arquivo):
    data_hoje = datetime.now().strftime("%d%m%Y")
    hora_hoje = datetime.now().strftime("%H%M%S")
    
    linha = (
        "341" +                         # 001-003: Código do Banco Itaú
        "0000" +                        # 004-007: Lote Padrão (0000)
        "0" +                           # 008-008: Tipo de Registro (0)
        format_str("", 6) +             # 009-014: Brancos
        "080" +                         # 015-017: Layout Arquivo[cite: 4]
        "2" +                           # 018-018: Inscrição da Empresa (1=CPF, 2=CNPJ)[cite: 4]
        format_num(empresa['cnpj'], 14) + # 019-032: CNPJ[cite: 4]
        format_str("", 20) +            # 033-052: Brancos[cite: 4]
        format_num(empresa['agencia'], 5) + # 053-057: Agência[cite: 4]
        " " +                           # 058-058: Branco[cite: 4]
        format_num(empresa['conta'], 12) +  # 059-070: Conta[cite: 4]
        " " +                           # 071-071: Branco[cite: 4]
        format_num(empresa['dac'], 1) +     # 072-072: DAC[cite: 4]
        format_str(empresa['nome'], 30) +   # 073-102: Nome da Empresa[cite: 4]
        format_str("BANCO ITAU SA", 30) +   # 103-132: Nome do Banco[cite: 4]
        format_str("", 10) +            # 133-142: Brancos[cite: 4]
        "1" +                           # 143-143: 1=Remessa[cite: 4]
        data_hoje +                     # 144-151: Data de Geração[cite: 4]
        hora_hoje +                     # 152-157: Hora de Geração[cite: 4]
        format_num("", 9) +             # 158-166: Zeros[cite: 4]
        format_num("1600", 5) +         # 167-171: Densidade[cite: 4]
        format_str("", 69)              # 172-240: Brancos[cite: 4]
    )
    return linha

def gerar_header_lote(empresa):
    linha = (
        "341" +                         # 001-003: Banco Itaú[cite: 4]
        "0001" +                        # 004-007: Lote Serviço (0001)[cite: 4]
        "1" +                           # 008-008: Tipo de Registro (1)[cite: 4]
        "C" +                           # 009-009: C=Crédito[cite: 4]
        "20" +                          # 010-011: Tipo de Pagto (20 = Fornecedores)[cite: 4]
        "41" +                          # 012-013: Forma de Pagto (41 = PIX Transferência)
        "040" +                         # 014-016: Layout do Lote[cite: 4]
        " " +                           # 017-017: Branco[cite: 4]
        "2" +                           # 018-018: 2=CNPJ[cite: 4]
        format_num(empresa['cnpj'], 14) + # 019-032: CNPJ[cite: 4]
        format_str("", 4) +             # 033-036: Identificação Lançamento[cite: 4]
        format_str("", 16) +            # 037-052: Brancos[cite: 4]
        format_num(empresa['agencia'], 5) + # 053-057: Agência[cite: 4]
        " " +                           # 058-058: Branco[cite: 4]
        format_num(empresa['conta'], 12) +  # 059-070: Conta[cite: 4]
        " " +                           # 071-071: Branco[cite: 4]
        format_num(empresa['dac'], 1) +     # 072-072: DAC[cite: 4]
        format_str(empresa['nome'], 30) +   # 073-102: Nome Empresa[cite: 4]
        format_str("PAGAMENTO PIX", 30) +   # 103-132: Finalidade Lote[cite: 4]
        format_str("", 10) +            # 133-142: Histórico Conta[cite: 4]
        format_str(empresa['endereco'], 30)+# 143-172: Endereço[cite: 4]
        format_num(empresa['numero'], 5) +  # 173-177: Número[cite: 4]
        format_str("", 15) +            # 178-192: Complemento[cite: 4]
        format_str(empresa['cidade'], 20) + # 193-212: Cidade[cite: 4]
        format_num(empresa['cep'], 8) +     # 213-220: CEP[cite: 4]
        format_str(empresa['uf'], 2) +      # 221-222: Estado[cite: 4]
        format_str("", 8) +             # 223-230: Brancos[cite: 4]
        format_str("", 10)              # 231-240: Ocorrências[cite: 4]
    )
    return linha

def gerar_segmento_a(pagamento, num_registro):
    linha = (
        "341" +                         # 001-003: Banco[cite: 4]
        "0001" +                        # 004-007: Lote[cite: 4]
        "3" +                           # 008-008: Tipo de Registro (3 = Detalhe)[cite: 4]
        format_num(num_registro, 5) +   # 009-013: Número do Registro[cite: 4]
        "A" +                           # 014-014: Segmento A[cite: 4]
        "000" +                         # 015-017: Tipo de Mov (000 = Inclusão)[cite: 4]
        "000" +                         # 018-020: Câmara (000 para PIX)[cite: 4]
        format_num(pagamento['banco_fav'], 3) + # 021-023: Banco Favorecido[cite: 4]
        format_str("", 20) +            # 024-043: Ag/Conta (Em branco para PIX Chave)[cite: 4]
        format_str(pagamento['nome_fav'], 30) + # 044-073: Nome Favorecido[cite: 4]
        format_str(pagamento['seu_numero'], 20) + # 074-093: Seu Número[cite: 4]
        format_num(pagamento['data_pagto'], 8) +  # 094-101: Data de Pagto (DDMMAAAA)[cite: 4]
        "009" +                         # 102-104: Moeda (009 p/ PIX ou REA)[cite: 4]
        format_str("", 8) +             # 105-112: ISPB[cite: 4]
        "  " +                          # 113-114: Ident. Transf[cite: 4]
        format_num("", 5) +             # 115-119: Zeros[cite: 4]
        format_moeda(pagamento['valor'], 15) + # 120-134: Valor Pagto[cite: 4]
        format_str("", 15) +            # 135-149: Nosso Número (Banco)[cite: 4]
        format_str("", 5) +             # 150-154: Brancos[cite: 4]
        format_num("", 8) +             # 155-162: Data Efetiva[cite: 4]
        format_moeda(0, 15) +           # 163-177: Valor Efetivo[cite: 4]
        format_str("", 20) +            # 178-197: Finalidade (Histórico)[cite: 4]
        format_num("", 6) +             # 198-203: Zeros (Retorno)[cite: 4]
        format_num(pagamento['cnpj_cpf_fav'], 14) + # 204-217: CPF/CNPJ Favorecido[cite: 4]
        format_str("", 2) +             # 218-219: Status[cite: 4]
        format_str("", 5) +             # 220-224: Finalidade TED[cite: 4]
        format_str("", 5) +             # 225-229: Brancos[cite: 4]
        "0" +                           # 230-230: Aviso[cite: 4]
        format_str("", 10)              # 231-240: Ocorrências[cite: 4]
    )
    return linha

def gerar_segmento_b_pix(pagamento, num_registro):
    linha = (
        "341" +                         # 001-003: Banco[cite: 4]
        "0001" +                        # 004-007: Lote[cite: 4]
        "3" +                           # 008-008: Tipo de Registro (3)[cite: 4]
        format_num(num_registro, 5) +   # 009-013: Número do Registro[cite: 4]
        "B" +                           # 014-014: Segmento B[cite: 4]
        format_str(pagamento['tipo_chave'], 2) + # 015-016: Tipo Chave (01=CPF,02=CNPJ,03=Cel,04=E-mail,05=Aleatória)[cite: 4]
        " " +                           # 017-017: Branco[cite: 4]
        pagamento['tipo_doc_fav'] +     # 018-018: Inscrição Fav (1=CPF, 2=CNPJ)[cite: 4]
        format_num(pagamento['cnpj_cpf_fav'], 14) + # 019-032: CNPJ/CPF[cite: 4]
        format_str("", 65) +            # 033-127: Zeros/Brancos para Info entre Usuários[cite: 4]
        format_str(pagamento['chave_pix'], 100) + # 128-227: Chave PIX[cite: 4]
        format_str("", 3) +             # 228-230: Brancos[cite: 4]
        format_str("", 10)              # 231-240: Ocorrências[cite: 4]
    )
    return linha

def gerar_trailer_lote(qtd_registros, valor_total):
    linha = (
        "341" +                         # 001-003: Banco[cite: 4]
        "0001" +                        # 004-007: Lote[cite: 4]
        "5" +                           # 008-008: Trailer de Lote[cite: 4]
        format_str("", 9) +             # 009-017: Brancos[cite: 4]
        format_num(qtd_registros, 6) +  # 018-023: Qtd Registros no Lote (Inclui Headers e Trailers do Lote)[cite: 4]
        format_moeda(valor_total, 18) + # 024-041: Somatório dos Valores[cite: 4]
        format_num("", 18) +            # 042-059: Zeros[cite: 4]
        format_str("", 171) +           # 060-230: Brancos[cite: 4]
        format_str("", 10)              # 231-240: Ocorrências[cite: 4]
    )
    return linha

def gerar_trailer_arquivo(qtd_lotes, qtd_registros_arq):
    linha = (
        "341" +                         # 001-003: Banco[cite: 4]
        "9999" +                        # 004-007: Lote 9999[cite: 4]
        "9" +                           # 008-008: Trailer de Arquivo[cite: 4]
        format_str("", 9) +             # 009-017: Brancos[cite: 4]
        format_num(qtd_lotes, 6) +      # 018-023: Qtd Lotes[cite: 4]
        format_num(qtd_registros_arq, 6) + # 024-029: Qtd Registros Arquivo[cite: 4]
        format_str("", 211)             # 030-240: Brancos[cite: 4]
    )
    return linha

# ==========================================
# PAINEL STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerador CNAB 240 - Itaú PIX", layout="wide")

st.title("Motor CNAB 240 - Itaú SISPAG (Foco PIX)")
st.markdown("Interface adaptada para geração exclusiva de lotes de pagamento PIX (Transferência por Chave) conforme regras do Itaú SISPAG.")

st.sidebar.header("Dados da Empresa (Pagador)")
empresa = {
    'cnpj': st.sidebar.text_input("CNPJ (Apenas números)", "00000000000100"),
    'agencia': st.sidebar.text_input("Agência", "1234"),
    'conta': st.sidebar.text_input("Conta", "12345"),
    'dac': st.sidebar.text_input("Dígito Conta (DAC)", "6"),
    'nome': st.sidebar.text_input("Nome da Empresa", "HOSPITAL SOS CARDIO"),
    'endereco': st.sidebar.text_input("Rua/Av", "RODOVIA SC 401"),
    'numero': st.sidebar.text_input("Número", "123"),
    'cidade': st.sidebar.text_input("Cidade", "FLORIANOPOLIS"),
    'cep': st.sidebar.text_input("CEP", "88000000"),
    'uf': st.sidebar.text_input("UF", "SC")
}

st.header("Lançamentos PIX")
# Interface simplificada de entrada de dados (podendo ser substituída por pd.read_excel do ERP Tasy/Oracle)
data = {
    "Seu Número": ["DOC001", "DOC002"],
    "Nome Favorecido": ["FORNECEDOR A", "FORNECEDOR B"],
    "CPF/CNPJ Favorecido": ["11111111111", "22222222000122"],
    "Tipo Doc (1=CPF, 2=CNPJ)": ["1", "2"],
    "Tipo Chave": ["01", "02"], # 01=CPF, 02=CNPJ, 03=E-mail, 04=Telefone
    "Chave PIX": ["11111111111", "22222222000122"],
    "Valor": [1500.50, 3400.00],
    "Data Pagto (DDMMAAAA)": ["15092026", "15092026"]
}

df_pagamentos = pd.DataFrame(data)
df_editado = st.data_editor(df_pagamentos, num_rows="dynamic")

if st.button("Gerar Remessa CNAB 240 (PIX)"):
    linhas_cnab = []
    
    # Header do Arquivo
    linhas_cnab.append(gerar_header_arquivo(empresa, 1))
    
    # Header do Lote (Lote 1)
    linhas_cnab.append(gerar_header_lote(empresa))
    
    num_registro_lote = 1 # Header de Lote conta como um registro, mas a sequência de detalhes zera/reinicia.
    valor_total_lote = 0.0
    
    # Lançamentos PIX
    for index, row in df_editado.iterrows():
        pagamento = {
            'seu_numero': row["Seu Número"],
            'nome_fav': row["Nome Favorecido"],
            'cnpj_cpf_fav': row["CPF/CNPJ Favorecido"],
            'tipo_doc_fav': row["Tipo Doc (1=CPF, 2=CNPJ)"],
            'banco_fav': "000", # No PIX via Chave, o ISPB/Banco é recuperado pela Chave na liquidação
            'data_pagto': row["Data Pagto (DDMMAAAA)"],
            'valor': row["Valor"],
            'tipo_chave': row["Tipo Chave"],
            'chave_pix': row["Chave PIX"]
        }
        
        # Segmento A
        linhas_cnab.append(gerar_segmento_a(pagamento, num_registro_lote))
        num_registro_lote += 1
        
        # Segmento B (Obrigatório para PIX)
        linhas_cnab.append(gerar_segmento_b_pix(pagamento, num_registro_lote))
        num_registro_lote += 1
        
        valor_total_lote += pagamento['valor']
        
    # Trailer Lote
    # Quantidade = Header(1) + Segmentos A e B + Trailer(1)
    qtd_registros_lote = num_registro_lote + 1 
    linhas_cnab.append(gerar_trailer_lote(qtd_registros_lote, valor_total_lote))
    
    # Trailer Arquivo
    qtd_lotes = 1
    qtd_registros_arq = qtd_registros_lote + 2 # Lotes + Header(1) + Trailer Arq(1)
    linhas_cnab.append(gerar_trailer_arquivo(qtd_lotes, qtd_registros_arq))
    
    cnab_texto = "\n".join(linhas_cnab)
    
    st.success("Remessa Gerada com Sucesso!")
    st.text_area("Pré-visualização CNAB", cnab_texto, height=300)
    
    st.download_button(
        label="Download Remessa PIX Itaú (.REM)",
        data=cnab_texto,
        file_name=f"ITAU_PIX_{datetime.now().strftime('%d%m%Y')}.REM",
        mime="text/plain"
    )
