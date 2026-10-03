import streamlit as st
import pandas as pd
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Leitura de Varredura DDA", layout="wide", page_icon="🧾")

# ==============================================================================
# 1. CUSTOM CSS — IDENTIDADE CORPORATIVA MINIMALISTA
# ==============================================================================
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f4f6f9;
    --surface: #ffffff;
    --primary-dark: #1e40af;
    --primary: #3b82f6;
    --success: #10b981;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }

/* HEADER PRINCIPAL */
.exec-header { background: transparent; padding: 10px 0 20px 0; border-bottom: 2px solid var(--border); display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
.exec-header h1 { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: 0.5px; color: var(--primary-dark); text-transform: uppercase;}
.exec-header p { margin: 2px 0 0 0; font-size: 12px; font-weight: 500; color: var(--text-muted); }

/* KPI CARDS */
.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; position: relative; box-shadow: var(--shadow); }
.kpi-card::after { content: ""; position: absolute; bottom: 0; left: 20px; right: 20px; height: 4px; border-radius: 4px 4px 0 0; background: var(--primary); }
.kpi-card.c-green::after { background: var(--success); }
.kpi-title { font-size: 11px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; }
.kpi-val { font-size: 28px; font-weight: 800; color: var(--primary-dark); letter-spacing: -0.5px; }

/* TABELA CUSTOMIZADA */
.table-container { background: var(--surface); border-radius: 8px; overflow: hidden; box-shadow: var(--shadow); border: 1px solid var(--border); margin-top: 20px;}
.table-header { background: var(--primary-dark); color: #fff; padding: 14px 20px; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;}
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 2. MOTOR DE PARSING DO ARQUIVO CNAB 240 (ITAÚ / SISPAG)
# ==============================================================================
def formata_documento(raw_doc):
    doc_clean = raw_doc.lstrip('0')
    if len(doc_clean) > 11:
        doc_str = doc_clean.zfill(14)
        return f"{doc_str[:2]}.{doc_str[2:5]}.{doc_str[5:8]}/{doc_str[8:12]}-{doc_str[12:]}"
    else:
        doc_str = doc_clean.zfill(11)
        return f"{doc_str[:3]}.{doc_str[3:6]}.{doc_str[6:9]}-{doc_str[9:]}"

def processar_varredura(conteudo_arquivo):
    registros = []
    linhas = conteudo_arquivo.split('\n')
    
    for linha in linhas:
        if len(linha) < 150:  # Ignora linhas curtas (headers/trailers de lote simples)
            continue
            
        # O Segmento fica na posição 14 (índice 13)
        segmento = linha[13:14]
        
        # Filtra apenas o Segmento G (Detalhe de Pagamento / Varredura)
        if segmento == 'G':
            try:
                # Mapeamento Posicional CNAB 240
                raw_doc = linha[56:71].strip()
                cnpj_cpf = formata_documento(raw_doc)
                
                nome_sacado = linha[71:101].strip()
                
                raw_data = linha[101:109]
                data_venc = f"{raw_data[:2]}/{raw_data[2:4]}/{raw_data[4:]}"
                
                raw_valor = linha[109:124]
                valor = float(raw_valor) / 100.0
                
                registros.append({
                    "Sacado / Beneficiário": nome_sacado,
                    "CNPJ / CPF": cnpj_cpf,
                    "Data de Vencimento": data_venc,
                    "Valor Documento (R$)": valor
                })
            except Exception as e:
                continue # Ignora linhas mal formatadas silenciosamente

    return pd.DataFrame(registros)

# ==============================================================================
# 3. INTERFACE DE USUÁRIO
# ==============================================================================
st.markdown("""
<div class='exec-header'>
    <div>
        <h1>Varredura de Sacado (DDA)</h1>
        <p>Leitura e conciliação automática de arquivos de retorno bancário</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Área de Upload
st.markdown("### 1. Inserir Arquivo de Varredura")
col_upload, col_paste = st.columns(2)

with col_upload:
    arquivo_upload = st.file_uploader("Faça o upload do arquivo (.TXT / .RET)", type=['txt', 'ret'])

with col_paste:
    texto_colado = st.text_area("Ou cole o conteúdo do arquivo aqui:", height=100, placeholder="3410001300001G 01756...")

# Processamento
conteudo_processar = ""

if arquivo_upload is not None:
    conteudo_processar = arquivo_upload.getvalue().decode('utf-8')
elif texto_colado:
    conteudo_processar = texto_colado

if conteudo_processar:
    df_varredura = processar_varredura(conteudo_processar)
    
    if not df_varredura.empty:
        # ==============================================================================
        # 4. EXIBIÇÃO DOS KPIs
        # ==============================================================================
        total_titulos = len(df_varredura)
        valor_total = df_varredura["Valor Documento (R$)"].sum()
        ticket_medio = valor_total / total_titulos if total_titulos > 0 else 0
        
        st.markdown(f"""
        <div class='kpi-row'>
            <div class='kpi-card'>
                <div class='kpi-title'>Títulos Encontrados</div>
                <div class='kpi-val'>{total_titulos}</div>
            </div>
            <div class='kpi-card c-green'>
                <div class='kpi-title'>Volume Financeiro Total</div>
                <div class='kpi-val'>R$ {valor_total:,.2f}</div>
            </div>
            <div class='kpi-card'>
                <div class='kpi-title'>Ticket Médio por Título</div>
                <div class='kpi-val'>R$ {ticket_medio:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ==============================================================================
        # 5. MATRIZ DE RESULTADOS (DATAFRAME)
        # ==============================================================================
        st.markdown("<div class='table-container'><div class='table-header'>Títulos Processados do Arquivo</div>", unsafe_allow_html=True)
        
        # Formatação do dataframe nativo do Streamlit para visualização limpa
        st.dataframe(
            df_varredura.style.format({"Valor Documento (R$)": "R$ {:,.2f}"}),
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
    else:
        st.warning("Não foram encontrados registros do Segmento G válidos neste arquivo.")
else:
    st.info("Aguardando inserção do arquivo CNAB 240 para realizar a leitura.")
