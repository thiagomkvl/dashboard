import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io  # <--- Adicionado para manipulação de bytes na memória para download
from datetime import datetime, timedelta
from database import conectar_sheets

# --- IMPORTAÇÃO SEGURA ---
try:
    from modules.utils import formatar_real, identificar_tipo_pagamento
    # 🔴 EVOLUÇÃO: Importando a função do motor do cnab_engine atualizado
    from modules.cnab_engine import gerar_cnab_pix 
except ImportError as e:
    st.error(f"Erro crítico nos módulos: {e}")
    st.stop()

# ==============================================================================
# LEITURA DE PROTESTOS: certidões e recibos são tratados separadamente.
# Estas funções atendem somente à ferramenta de PDFs da aba de protestos.
# ==============================================================================
def _protesto_match(padrao, texto, grupo=1):
    import re
    m = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
    return m.group(grupo).strip() if m else ""


def _protesto_valor(rotulo, texto):
    from decimal import Decimal
    numero = _protesto_match(
        r"(?:^|\s)(?:" + rotulo + r")\s*:\s*(?:R\$\s*)?((?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})(?!\d)",
        texto,
    )
    return float(Decimal(numero.replace(".", "").replace(",", "."))) if numero else None


def _protesto_data(rotulo, texto):
    valor = _protesto_match(r"(?:" + rotulo + r")\s*:\s*(\d{2}/\d{2}/\d{4})", texto)
    if valor:
        try:
            datetime.strptime(valor, "%d/%m/%Y")
            return valor
        except ValueError:
            pass
    return ""


def _protesto_nome_documento(texto):
    import re
    documento = _protesto_match(
        r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})", texto
    )
    nome = re.split(r"\s+Documento(?:\s+(?:Sacador|Cedente|Credor))?\s*:", texto, flags=re.I)[0]
    if documento:
        nome = nome.split(documento, 1)[0]
    nome = re.sub(r"\s+(?:CNPJ|CPF)(?:/CNPJ)?\s*:?\s*$", "", nome, flags=re.I)
    return nome.strip(" \t-"), documento


def extrair_dados_protesto_pdf(uploaded_files):
    """Retorna os títulos; recibos e diagnóstico ficam em DataFrame.attrs.

    Não transforma a taxa de emissão de uma certidão em dívida protestada.
    O protocolo é a âncora de cada título, inclusive entre páginas.
    """
    import bisect
    import hashlib
    import re
    import pdfplumber

    colunas = [
        "Cartório/Arquivo", "Protocolo", "Credor/Sacador", "CNPJ/CPF Credor",
        "Valor/Saldo", "Custas/Taxas", "Emissão", "Vencimento", "Data do Protesto",
        "Título/Número", "Espécie", "Credor atual", "Credor original",
        "Apresentante", "Valor Original", "Valor Declarado", "Saldo", "Página", "Observações",
    ]
    colunas_recibos = [
        "Cartório/Arquivo", "Recibo", "Ordem de serviço", "Favorecido",
        "CPF/CNPJ Referência", "Data pagamento", "Valor total", "Descrição", "Páginas",
    ]
    registros, recibos, diagnosticos = [], [], []
    documentos_lidos = set()
    for arquivo in uploaded_files:
        nome = str(getattr(arquivo, "name", "Arquivo.pdf"))
        diag = {"Arquivo": nome, "Tipo": "", "Páginas": 0, "Títulos declarados": None,
                "Títulos extraídos": 0, "Recibos": 0, "Situação": "", "Observação": ""}
        try:
            if hasattr(arquivo, "getvalue"):
                conteudo = arquivo.getvalue()
            else:
                posicao = arquivo.tell() if hasattr(arquivo, "tell") else None
                if hasattr(arquivo, "seek"):
                    arquivo.seek(0)
                conteudo = arquivo.read()
                if posicao is not None:
                    arquivo.seek(posicao)
            assinatura = hashlib.sha256(conteudo).hexdigest()
            if assinatura in documentos_lidos:
                diag.update({"Tipo": "Arquivo repetido", "Situação": "Ignorado",
                             "Observação": "O mesmo conteúdo PDF já foi processado neste lote."})
                diagnosticos.append(diag)
                continue
            with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
                paginas = [(p.extract_text(x_tolerance=2, y_tolerance=3) or "").replace("\xa0", " ")
                           for p in pdf.pages]
            documentos_lidos.add(assinatura)
            diag["Páginas"] = len(paginas)
            offsets, partes, tamanho = [], [], 0
            for pagina in paginas:
                offsets.append(tamanho)
                partes.append(pagina + "\n")
                tamanho += len(pagina) + 1
            texto = "".join(partes)
            if not texto.strip():
                diag.update({"Tipo": "Sem texto extraível", "Situação": "Revisar",
                             "Observação": "PDF sem camada de texto. É necessário OCR antes da leitura."})
                diagnosticos.append(diag)
                continue

            # Recibos podem estar anexados à certidão e ter duas vias idênticas.
            recibos_arquivo = {}
            for numero_pagina, pagina in enumerate(paginas, 1):
                numero_recibo = _protesto_match(r"\bRECIBO\s*N[º°o.]?\s*:?\s*(\d+)", pagina)
                if not numero_recibo:
                    continue
                ordem = _protesto_match(r"O\.?\s*S\.?\s*N[º°o.]?\s*:?\s*(\d+)", pagina)
                chave = (numero_recibo, ordem)
                if chave in recibos_arquivo:
                    recibos_arquivo[chave]["Páginas"] += ", " + str(numero_pagina)
                    continue
                favorecido = _protesto_match(r"Favorecido\s*:\s*([\s\S]*?)(?=\n\s*Referente)", pagina)
                documento = _protesto_match(r"CPF/CNPJ\s*:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})", pagina)
                data = _protesto_data(r"Pago\s+em", pagina) or _protesto_data(r"DATA", pagina)
                if not data:
                    data = _protesto_match(r"\bem\s+(\d{2}/\d{2}/\d{4})", pagina)
                recibos_arquivo[chave] = {
                    "Cartório/Arquivo": nome, "Recibo": numero_recibo, "Ordem de serviço": ordem,
                    "Favorecido": re.sub(r"\s+", " ", favorecido), "CPF/CNPJ Referência": documento,
                    "Data pagamento": data, "Valor total": _protesto_valor(r"Valor\s+total", pagina),
                    "Descrição": "Recibo da emissão de certidão; não é relação de títulos protestados.",
                    "Páginas": str(numero_pagina),
                }
            recibos.extend(recibos_arquivo.values())
            diag["Recibos"] = len(recibos_arquivo)

            declarados = set(re.findall(r"(\d+)\s+t[ií]tulo(?:s|\(s\))?\s+protestad", texto, flags=re.I))
            declarados.update(re.findall(r"Total\s+de\s+T[ií]tulos\s+Protestados\s*:\s*(\d+)", texto, flags=re.I))
            if len(declarados) == 1:
                diag["Títulos declarados"] = int(next(iter(declarados)))
            inicios = list(re.finditer(r"(?im)^\s*Protocolo\s*:\s*(\d[\d./-]*)", texto))
            chaves_extraidas = set()
            incompletos = 0
            for i, inicio in enumerate(inicios):
                bloco = texto[inicio.start():inicios[i + 1].start() if i + 1 < len(inicios) else len(texto)]
                # Rodapé da certidão não integra o último título (emolumentos são da emissão).
                bloco = re.split(r"(?im)^\s*(?:Total\s+de\s+\d+\s+t[ií]tulos?|Total\s+de\s+T[ií]tulos\s+Protestados|O\s+referido|Nada\s+mais\s+consta|Emolumentos\s*:)", bloco)[0]
                atual = _protesto_match(r"^\s*Credor\s+atual\s*:\s*([^\n]+)", bloco)
                original = _protesto_match(r"^\s*Credor\s+original\s*:\s*([^\n]+)", bloco)
                sacador = _protesto_match(r"^\s*Sacador\s*:\s*([^\n]+)", bloco)
                cedente = _protesto_match(r"^\s*Cedente\s*:\s*([^\n]+)", bloco)
                apresentante = _protesto_match(r"^\s*Apresentante\s*:\s*([^\n]+)", bloco)
                escolhido = original or sacador or atual or cedente
                credor, documento_credor = _protesto_nome_documento(escolhido)
                observacoes = []
                if not credor:
                    credor = "Não identificado"
                    observacoes.append("Credor não identificado; confira a página de origem.")
                valor_original = _protesto_valor(r"Valor\s+Original", bloco)
                valor_declarado = _protesto_valor(r"Valor\s+Declarado", bloco)
                saldo = _protesto_valor(r"Saldo", bloco)
                valor = _protesto_valor(r"Valor", bloco)
                valor_principal = next((v for v in (saldo, valor_declarado, valor_original, valor) if v is not None), None)
                if valor_principal is None:
                    observacoes.append("Valor não identificado; título preservado para revisão.")
                titulo = _protesto_match(r"n[º°o]\s*(?:do\s*)?T[ií]tulo\s*:\s*(.*?)(?=\s*-\s*Endosso|$)", bloco)
                if not titulo:
                    titulo = _protesto_match(r"^\s*N[uú]mero\s*:\s*(.*?)(?=\s+Nosso\s*N[uú]mero\s*:|$)", bloco)
                especie = _protesto_match(r"Esp[ée]cie(?:\s+do\s+T[ií]tulo)?\s*:\s*(.*?)(?=\s*-\s*n[º°o]|$)", bloco)
                record = {
                    "Cartório/Arquivo": nome, "Protocolo": inicio.group(1),
                    "Credor/Sacador": credor, "CNPJ/CPF Credor": documento_credor,
                    "Valor/Saldo": valor_principal, "Custas/Taxas": _protesto_valor(r"Custas(?:\s+do\s+protesto)?|Taxas", bloco),
                    "Emissão": _protesto_data(r"Emiss[ãa]o|Data\s+Emiss[ãa]o", bloco),
                    "Vencimento": _protesto_data(r"Vencimento|Venc\.", bloco),
                    "Data do Protesto": _protesto_data(r"Data(?:\s+do)?\s+Protesto|Protestado\s+em|Protesto\s+em", bloco),
                    "Título/Número": titulo, "Espécie": especie,
                    "Credor atual": _protesto_nome_documento(atual)[0],
                    "Credor original": _protesto_nome_documento(original or sacador)[0],
                    "Apresentante": apresentante, "Valor Original": valor_original,
                    "Valor Declarado": valor_declarado, "Saldo": saldo,
                    "Página": bisect.bisect_right(offsets, inicio.start(1)),
                    "Observações": " ".join(observacoes),
                }
                chave = tuple(record[c] for c in colunas if c != "Página")
                if chave in chaves_extraidas:
                    continue
                chaves_extraidas.add(chave)
                registros.append(record)
                diag["Títulos extraídos"] += 1
                incompletos += bool(observacoes)
            if inicios:
                diag["Tipo"] = "Certidão com títulos" + (" e recibo" if recibos_arquivo else "")
                diag["Situação"] = "Revisar" if incompletos else "Lido"
                if incompletos:
                    diag["Observação"] = f"{incompletos} título(s) com campos pendentes de revisão."
                if diag["Títulos declarados"] is not None and diag["Títulos declarados"] != diag["Títulos extraídos"]:
                    diag["Situação"] = "Revisar"
                    diag["Observação"] += " Quantidade extraída difere da quantidade declarada na certidão."
            elif recibos_arquivo:
                diag.update({"Tipo": "Somente recibo", "Situação": "Relação não anexada",
                             "Observação": "Este PDF contém recibo de emissão. Envie a certidão com os títulos para extrair protocolos, credores, valores e vencimentos."})
            else:
                diag.update({"Tipo": "Layout não reconhecido", "Situação": "Revisar",
                             "Observação": "Há texto, mas não foi localizada uma relação de títulos com protocolo."})
        except Exception as erro:
            diag.update({"Tipo": "Erro de leitura", "Situação": "Revisar", "Observação": str(erro)})
        diagnosticos.append(diag)
    resultado = pd.DataFrame(registros, columns=colunas)
    resultado.attrs["recibos"] = pd.DataFrame(recibos, columns=colunas_recibos)
    resultado.attrs["diagnosticos"] = pd.DataFrame(diagnosticos)
    return resultado


def _protesto_excel(protestos, recibos, diagnosticos):
    """Gera o mesmo download Excel, com títulos, recibos e conferência por arquivo."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter", engine_kwargs={
        "options": {"strings_to_formulas": False, "strings_to_urls": False}
    }) as writer:
        dinheiro = writer.book.add_format({"num_format": '"R$ "#,##0.00;[Red]-"R$ "#,##0.00'})
        cabecalho = writer.book.add_format({"bold": True, "bg_color": "#E9ECEF", "text_wrap": True, "valign": "vcenter"})
        for nome, tabela in (("Protestos", protestos), ("Recibos", recibos), ("Conferencia", diagnosticos)):
            tabela.to_excel(writer, index=False, sheet_name=nome)
            sheet = writer.sheets[nome]
            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, len(tabela), max(len(tabela.columns) - 1, 0))
            sheet.set_row(0, 32)
            for j, coluna in enumerate(tabela.columns):
                sheet.write(0, j, coluna, cabecalho)
                largura = 52 if coluna in ("Cartório/Arquivo", "Arquivo", "Credor/Sacador", "Credor atual", "Credor original", "Apresentante", "Favorecido", "Observações", "Observação", "Descrição") else 21
                sheet.set_column(j, j, largura, dinheiro if coluna in ("Valor/Saldo", "Custas/Taxas", "Valor Original", "Valor Declarado", "Saldo", "Valor total") else None)
    return output.getvalue()


# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Cockpit Financeiro - SOS Cardio", page_icon="🎛️", layout="wide")

# ==============================================================================
# 0. TELA DE LOGIN (AUTENTICAÇÃO)
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    # Layout centralizado para a tela de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #1e40af;'>🔒 Acesso Restrito</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>Insira a credencial de segurança para acessar o Cockpit Financeiro.</p>", unsafe_allow_html=True)
        
        senha_input = st.text_input("Senha", type="password", placeholder="Digite a senha...")
        
        if st.button("Entrar no Sistema", type="primary", use_container_width=True):
            if senha_input == "@SOS2025":
                st.session_state["autenticado"] = True
                st.rerun() # Recarrega a página para liberar o dashboard
            else:
                st.error("❌ Senha incorreta. Acesso negado.")
    
    # st.stop() trava a execução do código aqui. Nada abaixo desta linha será renderizado sem a senha.
    st.stop() 


# --- CUSTOM CSS (Magia do UI/UX) ---
st.markdown("""
    <style>
    /* Status Bar Header */
    .status-dot { height: 12px; width: 12px; background-color: #00C851; border-radius: 50%; display: inline-block; margin-left: 5px; margin-right: 20px;}
    .status-text { font-size: 16px; font-weight: bold; color: #4F4F4F; display: inline-block; }
    
    /* Estilo dos Cards de KPI Superiores */
    .kpi-card {
        background-color: #F8F9FA; 
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .kpi-title { font-size: 16px; color: #6c757d; text-align: center; margin-bottom: 5px;}
    .kpi-value { font-size: 32px; font-weight: bold; color: #343a40; text-align: center; margin-bottom: 15px;}
    .kpi-perc-text { font-size: 13px; color: #6c757d; margin-top: 5px; display: flex; justify-content: space-between;}
    
    /* Destaque do Topo da Tabela (Workaround para Canvas) */
    [data-testid="stDataFrame"] > div:first-child {
        border-top: 4px solid #212529 !important;
        border-radius: 4px 4px 0 0;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. HEADER (STATUS DE CONEXÕES)
# ==============================================================================
st.markdown("""
    <div style='display: flex; align-items: center; margin-bottom: 20px;'>
        <div class='status-text'>Dashboard Financeiro</div><span class='status-dot'></span>
        <div class='status-text'>Banco de dados Tasy</div><span class='status-dot'></span>
        <div class='status-text'>API Santander</div><span class='status-dot'></span>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CARGA DE DADOS (REAL + FICTÍCIO)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_reais():
    try:
        conn = conectar_sheets()
        df = conn.read(worksheet="Pagamentos_Dia", ttl=0)
        if df.empty: return pd.DataFrame()
        
        if 'Pagar?' not in df.columns: df.insert(0, 'Pagar?', True)
        df['Pagar?'] = df['Pagar?'].astype(bool)
        
        if 'VALOR_PAGAMENTO' in df.columns:
            df['VALOR_PAGAMENTO'] = pd.to_numeric(df['VALOR_PAGAMENTO'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        
        # Mockups de colunas faltantes para bater com a imagem
        if 'Categoria' not in df.columns: df['Categoria'] = 'Estoque Medicamentos'
        if 'OC' not in df.columns: df['OC'] = np.random.randint(100000, 999999, df.shape[0])
        if 'NF' not in df.columns: df['NF'] = np.random.randint(1000, 9999, df.shape[0])
        if 'Observação' not in df.columns: df['Observação'] = '-x-'
        if 'Banco_Origem' not in df.columns: df['Banco_Origem'] = 'Unicred - C.C'
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar Sheets: {e}")
        return pd.DataFrame()

df_real = carregar_dados_reais()

# ==============================================================================
# 3. MÓDULO DE KPIs SUPERIORES
# ==============================================================================
total_saidas = df_real['VALOR_PAGAMENTO'].sum() if not df_real.empty else 457590.90
saldo_disponivel = 957590.90
saldo_resgate = 20457590.90
saldo_final = saldo_disponivel - total_saidas

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

def gerar_html_kpi(titulo, valor, pct_progress, cor_barra, texto_rodape):
    return f"""
    <div class='kpi-card'>
        <div class='kpi-title'>{titulo}</div>
        <div class='kpi-value'>{valor}</div>
        <div class='kpi-perc-text'>
            <span>% Comprometido: {pct_progress}%</span>
            <span>{pct_progress}%</span>
        </div>
        <div style='width: 100%; background-color: #E0E0E0; border-radius: 4px; height: 8px; margin-top: 5px;'>
            <div style='width: {pct_progress}%; background-color: {cor_barra}; height: 8px; border-radius: 4px;'></div>
        </div>
    </div>
    """

kpi1.markdown(gerar_html_kpi("Saldo disponível", formatar_real(saldo_disponivel), 50, "#1cc88a", "50%"), unsafe_allow_html=True)
kpi2.markdown(gerar_html_kpi("Saldo Resgate", formatar_real(saldo_resgate), 56, "#e74a3b", "56%"), unsafe_allow_html=True)
kpi3.markdown(gerar_html_kpi("Saídas Previstas", formatar_real(total_saidas), 100, "#f6c23e", "100%"), unsafe_allow_html=True)
kpi4.markdown(gerar_html_kpi("Saldo Final Previsto", formatar_real(saldo_final), 26, "#5a5c69", "26%"), unsafe_allow_html=True)

st.divider()

# ==============================================================================
# 4. CORPO PRINCIPAL (TABELA À ESQUERDA, GRÁFICOS À DIREITA)
# ==============================================================================
col_left, col_right = st.columns([1.3, 1])

# --- ESQUERDA: TABELA E GERAÇÃO CNAB ---
with col_left:
    # 🔴 EVOLUÇÃO: Expandido para criar a terceira aba nativa do painel
    tab1, tab2, tab3 = st.tabs(["Enviar Remessa de Pagamentos", "Títulos Vencidos", "📄 Auditoria de Protestos (PDF)"])
    
    with tab1:
        if not df_real.empty:
            colunas_visuais = ['Pagar?', 'NOME_FAVORECIDO', 'Categoria', 'OC', 'NF', 'Observação', 'DATA_PAGAMENTO', 'VALOR_PAGAMENTO', 'Banco_Origem', 'CHAVE_PIX_OU_COD_BARRAS', 'cnpj_beneficiario']
            for col in colunas_visuais:
                if col not in df_real.columns: df_real[col] = ""
                
            df_display = df_real[colunas_visuais].copy()
            
            # Altura cravada em 760 para alinhar com o bloco de HTML + os 2 gráficos da direita
            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                height=760, 
                column_config={
                    "Pagar?": st.column_config.CheckboxColumn("Pagar", default=True),
                    "NOME_FAVORECIDO": "Pagamento",
                    "DATA_PAGAMENTO": "Venc. original",
                    "VALOR_PAGAMENTO": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Banco_Origem": "Banco",
                    "CHAVE_PIX_OU_COD_BARRAS": None, 
                    "cnpj_beneficiario": None
                }
            )
            
            st.write("")
            
            # --- CORREÇÃO DEFINITIVA DO MATCH DE ÍNDICE ---
            linhas_selecionadas = edited_df[edited_df['Pagar?'] == True].index
            
            if st.button("🚀 Gerar Arquivo de Remessa (CNAB 240)", type="primary"):
                if len(linhas_selecionadas) > 0:
                    df_pagar_completo = df_real.loc[linhas_selecionadas].copy()
                    
                    # BALA DE PRATA: Força o arredondamento comercial NA HORA DO CLIQUE, ignorando o cache
                    df_pagar_completo['VALOR_PAGAMENTO'] = np.floor(df_pagar_completo['VALOR_PAGAMENTO'] * 100 + 0.5) / 100
                    
                    arquivo_cnab = gerar_cnab_pix(df_pagar_completo)
                    
                    if arquivo_cnab:
                        st.download_button(
                            label="📥 Baixar CNAB", 
                            data=arquivo_cnab, 
                            file_name=f"REM_{datetime.now().strftime('%d%m')}.txt",
                            mime="text/plain"
                        )
                else:
                    st.warning("Nenhum título selecionado para pagamento.")
        else:
            st.info("Nenhum dado encontrado na planilha.")

    with tab2:
        st.info("Aqui entrará a query direta do banco de dados do Tasy listando os títulos vencidos.")

    # Conversão de PDFs de protesto (sem alterar os demais módulos do Cockpit).
    with tab3:
        st.subheader("Conversor Inteligente de Certidões de Protesto")
        st.markdown("Envie as certidões com a relação de títulos. Recibos de emissão são identificados e exportados separadamente.")
        arquivos_pdf = st.file_uploader("Selecione os PDFs de Protesto", type=["pdf"], accept_multiple_files=True, key="uploader_protestos")
        if arquivos_pdf:
            import hashlib
            assinatura_lote = hashlib.sha256()
            for arquivo in arquivos_pdf:
                assinatura_lote.update(arquivo.name.encode("utf-8"))
                assinatura_lote.update(hashlib.sha256(arquivo.getvalue()).digest())
            chave_lote = assinatura_lote.hexdigest()
            if st.button("📊 Processar PDFs e Estruturar Planilha", type="primary"):
                with st.spinner("Lendo certidões, identificando recibos e conferindo os títulos…"):
                    protestos = extrair_dados_protesto_pdf(arquivos_pdf)
                    recibos = protestos.attrs["recibos"]
                    diagnosticos = protestos.attrs["diagnosticos"]
                    excel = _protesto_excel(protestos, recibos, diagnosticos)
                    st.session_state["protestos_resultado_pdf"] = {
                        "assinatura": chave_lote, "protestos": protestos,
                        "recibos": recibos, "diagnosticos": diagnosticos, "excel": excel,
                    }
            resultado = st.session_state.get("protestos_resultado_pdf", {})
            if resultado.get("assinatura") == chave_lote:
                df_protestos = resultado["protestos"]
                df_recibos = resultado["recibos"]
                df_diagnosticos = resultado["diagnosticos"]
                if not df_protestos.empty:
                    st.success(f"{len(df_protestos)} títulos de protesto extraídos.")
                st.dataframe(df_diagnosticos, use_container_width=True, hide_index=True)
                for _, diagnostico in df_diagnosticos.iterrows():
                    if diagnostico["Situação"] in ("Relação não anexada", "Revisar"):
                        st.warning(f"{diagnostico['Arquivo']}: {diagnostico['Observação']}")
                if not df_protestos.empty:
                    st.dataframe(df_protestos, use_container_width=True, hide_index=True, height=450,
                        column_config={"Valor/Saldo": st.column_config.NumberColumn(format="R$ %.2f"),
                                       "Custas/Taxas": st.column_config.NumberColumn(format="R$ %.2f")})
                if not df_recibos.empty:
                    with st.expander("Recibos de emissão de certidão"):
                        st.caption("Estes valores são taxas da certidão e não compõem o total dos títulos protestados. Duas vias do mesmo recibo são agrupadas.")
                        st.dataframe(df_recibos, use_container_width=True, hide_index=True)
                if not df_protestos.empty or not df_recibos.empty:
                    st.download_button(
                        label="📥 Baixar Planilha Pronta para Auditoria (.xlsx)",
                        data=resultado["excel"],
                        file_name=f"Protestos_Processados_{datetime.now().strftime('%d%m')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                elif not df_diagnosticos.empty:
                    st.info("Confira o diagnóstico acima antes de enviar novamente os documentos.")

# --- DIREITA: GRÁFICOS ALINHADOS À REALIDADE DO HOSPITAL ---
with col_right:
    st.markdown("""
    <div style="display: flex; gap: 15px; margin-top: 48px; margin-bottom: 20px;">
        <div style="flex: 1; background-color: #F8F9FA; padding: 15px; border-radius: 8px; border: 1px solid #E9ECEF; border-left: 5px solid #36b9cc;">
            <div style="font-size: 14px; color: #6c757d; font-weight: 600;">Total Acordos</div>
            <div style="font-size: 22px; color: #343a40; font-weight: bold;">R$ 45.320,00</div>
        </div>
        <div style="flex: 1; background-color: #F8F9FA; padding: 15px; border-radius: 8px; border: 1px solid #E9ECEF; border-left: 5px solid #f6c23e;">
            <div style="font-size: 14px; color: #6c757d; font-weight: 600;">Total Ordem de Compras</div>
            <div style="font-size: 22px; color: #343a40; font-weight: bold;">R$ 128.450,00</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    def form_k(valor):
        return f"{valor/1000:.0f}k" if valor >= 1000 else str(valor)

    chart_config = {'scrollZoom': False, 'displayModeBar': False}

    # Gráfico 1: Total a Pagar x Total Pago
    dias = [(datetime.now() - timedelta(days=i)).strftime('%d/%m') for i in range(13, -1, -1)]
    a_pagar = [100000, 95000, 120000, 150000, 110000, 180000, 90000, 130000, 250000, 140000, 160000, 110000, 190000, 145000]
    pago =    [80000,  90000, 90000,  110000, 110000, 130000, 80000, 100000, 150000, 100000, 150000, 100000, 180000, 120000]
    
    text_pagar = [form_k(v) for v in a_pagar]
    text_pago = [form_k(v) for v in pago]

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=dias, y=a_pagar, name='A Pagar', marker_color='#e74a3b', text=text_pagar, textposition='outside', textfont=dict(size=11))) 
    fig1.add_trace(go.Bar(x=dias, y=pago, name='Pago', marker_color='#1cc88a', text=text_pago, textposition='outside', textfont=dict(size=11)))    
    fig1.add_trace(go.Scatter(x=dias, y=a_pagar, name='Tend. (A Pagar)', mode='lines', line=dict(color='#e74a3b', width=2, dash='dash')))
    fig1.add_trace(go.Scatter(x=dias, y=pago, name='Tend. (Pago)', mode='lines', line=dict(color='#1cc88a', width=2, dash='dash')))

    fig1.update_layout(
        title=dict(text="Total a Pagar x Total Pago", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='group', margin=dict(l=20, r=20, t=50, b=20), height=300, paper_bgcolor='#F8F9FA', plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5), dragmode='pan'
    )
    fig1.update_xaxes(fixedrange=False, range=[len(dias)-6.5, len(dias)-0.5]) 
    fig1.update_yaxes(fixedrange=True, range=[0, max(a_pagar)*1.2])
    
    st.plotly_chart(fig1, use_container_width=True, config=chart_config)
    
    # Gráfico 2: Categorias das Despesas Diarizadas
    cat_med = [40000, 50000, 30000, 60000, 35000, 40000, 70000, 40000, 50000, 30000, 60000, 35000, 40000, 70000]
    cat_hon = [30000, 40000, 50000, 40000, 25000, 30000, 50000, 30000, 40000, 50000, 40000, 25000, 30000, 50000]
    cat_man = [10000, 10000, 15000, 20000, 10000, 20000, 15000, 10000, 10000, 15000, 20000, 10000, 20000, 15000]
    cat_imp = [10000, 10000, 15000, 10000, 10000, 10000, 15000, 10000, 10000, 15000, 10000, 10000, 10000, 15000]
    
    totais = [m+h+ma+i for m, h, ma, i in zip(cat_med, cat_hon, cat_man, cat_imp)]
    text_totais = [f"<b>{form_k(v)}</b>" for v in totais]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=dias, y=cat_med, name='Insumos', marker_color='#4e73df')) 
    fig2.add_trace(go.Bar(x=dias, y=cat_hon, name='Médicos', marker_color='#36b9cc'))   
    fig2.add_trace(go.Bar(x=dias, y=cat_man, name='Geral', marker_color='#f6c23e'))     
    fig2.add_trace(go.Bar(x=dias, y=cat_imp, name='Impostos', marker_color='#858796'))              
    fig2.add_trace(go.Scatter(x=dias, y=totais, name='Tendência (Geral)', mode='lines+text', text=text_totais, textposition='top center', textfont=dict(size=12, color='#343a40'), line=dict(color='#858796', width=2)))

    fig2.update_layout(
        title=dict(text="Despesas por Categoria (Visão Diária)", font=dict(color="#4F4F4F", size=16), x=0.5),
        barmode='stack', margin=dict(l=20, r=20, t=50, b=20), height=300, paper_bgcolor='#F8F9FA', plot_bgcolor='#F8F9FA',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5), dragmode='pan'
    )
    fig2.update_xaxes(fixedrange=False, range=[len(dias)-6.5, len(dias)-0.5]) 
    fig2.update_yaxes(fixedrange=True, range=[0, max(totais)*1.2])
    
    st.plotly_chart(fig2, use_container_width=True, config=chart_config)
