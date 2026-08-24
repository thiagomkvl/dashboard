import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE e Fluxo de Caixa Gerencial", layout="wide", page_icon="📈")

# --- CUSTOM CSS (Visual Baseado na Imagem) ---
st.markdown("""
    <style>
    :root {
        --bg-color: #f0f2f6;
        --card-bg: #0a4b78; /* Azul escuro igual da imagem */
        --text-light: #ffffff;
        --table-header-bg: #0a4b78;
        --table-row-alt: #f8f9fa;
        --table-border: #dee2e6;
        --up-color: #198754;
        --down-color: #dc3545;
    }
    
    .main { background-color: var(--bg-color); }
    
    /* Top Header */
    .top-header { background-color: #0d82c2; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; color: white; margin-bottom: 20px; border-radius: 5px;}
    .top-header h1 { margin: 0; font-size: 24px; font-weight: 300; letter-spacing: 1px; }
    
    /* KPI Cards */
    .kpi-container { display: flex; gap: 15px; margin-bottom: 20px; }
    .kpi-card { flex: 1; background-color: var(--card-bg); border-radius: 8px; padding: 20px 15px; text-align: center; color: var(--text-light); box-shadow: 0 4px 6px rgba(0,0,0,0.1); position: relative; overflow: hidden; }
    .kpi-value { font-size: 26px; font-weight: 700; margin-bottom: 5px; }
    .kpi-label { font-size: 12px; font-weight: 400; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-sparkline { margin-top: 15px; height: 30px; border-bottom: 2px solid rgba(255,255,255,0.3); position: relative; }
    .kpi-sparkline::after { content: ''; position: absolute; bottom: -4px; right: 0; width: 8px; height: 8px; background-color: #f87171; border-radius: 50%; }
    
    /* Tabela DRE */
    .dre-container { background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow-x: auto; }
    .dre-table { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 13px; }
    
    /* Cabeçalhos da Tabela */
    .dre-table th { border: 1px solid var(--table-border); text-align: center; padding: 10px; font-weight: 600; color: #333; }
    .dre-table th.month-header { background-color: #ffffff; border-bottom: none; font-size: 14px; }
    .dre-table th.sub-header { background-color: #ffffff; color: #555; font-size: 11px; }
    
    /* Linhas e Células */
    .dre-table td { border: 1px solid var(--table-border); padding: 8px 10px; color: #212529; }
    .dre-table tr.macro-row td { background-color: var(--table-header-bg); color: white; font-weight: bold; }
    .dre-table tr.group-row td { background-color: #e9ecef; font-weight: bold; }
    .dre-table tr.item-row:hover td { background-color: #f1f3f5; }
    
    /* Alinhamentos */
    .text-left { text-align: left; }
    .text-right { text-align: right; font-variant-numeric: tabular-nums; }
    .indent-1 { padding-left: 20px !important; }
    .indent-2 { padding-left: 40px !important; }
    
    /* Setas e Cores AH/AV */
    .val-up { color: var(--up-color); font-weight: bold; }
    .val-down { color: var(--down-color); font-weight: bold; }
    .arrow-up::before { content: '↑ '; color: var(--up-color); }
    .arrow-down::before { content: '↓ '; color: var(--down-color); }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÕES UTILITÁRIAS E DE LEITURA
# ==============================================================================
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

def limpa_valor(valor):
    try:
        if pd.isna(valor): return 0.0
        v = str(valor).replace('R$', '').strip()
        if '.' in v and ',' in v: v = v.replace('.', '').replace(',', '.')
        elif ',' in v: v = v.replace(',', '.')
        return float(v)
    except: return 0.0

def formata_moeda(valor):
    if pd.isna(valor): return "-"
    prefixo = "-" if valor < 0 else ""
    return f"{prefixo}R$ {abs(valor):,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_pct(valor):
    if pd.isna(valor) or valor == 0: return "-"
    return f"{valor:.1f}%".replace('.', ',')

# ==============================================================================
# 2. MAPEAMENTO HIERÁRQUICO DE CONTAS CONTÁBEIS (CLASSIFICAÇÃO DRE)
# ==============================================================================
def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    
    # ---------------- ENTRADAS OPERACIONAIS ----------------
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "CASACARESC", "SAÚDE CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SELECT SAÚDE", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "ELO SAÚDE", "SEGURADORAS", "CAPESAUDE", "CAPESESP", "SIM SAÚDE", "EMBRATEL", "AMAP", "OMINT", "WORLD MEDICAL CARE", "SAUDES", "LIFE", "CLINCARD", "CONAB", "PRÉVIDA", "BRADESCO OPERADORA"]
    if any(c in conta for c in convênios): return "FCO", "ENTRADAS OPERACIONAIS", "CONVÊNIOS", conta
    
    particulares = ["CARTÃO", "DINHEIRO", "COBRANÇA PARTICULAR", "DEVOLUÇÃO PACIENTE"]
    if any(c in conta for c in particulares): return "FCO", "ENTRADAS OPERACIONAIS", "PARTICULARES", conta
    
    outras_receitas = ["ALUGUÉIS RECEBIDOS", "UNIVERSIDADE", "OUTRAS RECEITAS"]
    if any(c in conta for c in outras_receitas): return "FCO", "ENTRADAS OPERACIONAIS", "OUTRAS ENTRADAS OPERACIONAIS", conta

    # ---------------- SAÍDAS OPERACIONAIS ----------------
    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "FÉRIAS", "INSS", "FGTS"]): return "FCO", "SAÍDAS OPERACIONAIS", "Pessoal", conta
    if any(c in conta for c in ["HONORÁRIOS MÉDICOS", "MÉDICO"]): return "FCO", "SAÍDAS OPERACIONAIS", "Honorários Médicos", conta
    if any(c in conta for c in ["FORNECEDORES ASSISTENCIAIS", "CUSTO MATERIAIS", "MEDICAMENTOS", "OPME", "ESTOQUE"]): return "FCO", "SAÍDAS OPERACIONAIS", "Fornecedores assistenciais", conta
    if any(c in conta for c in ["IMPOSTOS CORRENTES", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): return "FCO", "SAÍDAS OPERACIONAIS", "Impostos correntes", conta
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "ÁGUA", "INTERNET", "CONTABILIDADE"]): return "FCO", "SAÍDAS OPERACIONAIS", "Despesas administrativas e de infraestrutura", conta
    
    # ---------------- FLUXO DE CAIXA DE INVESTIMENTO (FCI) ----------------
    if any(c in conta for c in ["OBRAS", "REFORMAS", "MÁQUINAS", "EQUIPAMENTOS"]): return "FCI", "FLUXO DE CAIXA DE INVESTIMENTO", "Obras e reformas", conta
    if any(c in conta for c in ["APLICAÇÕES", "RENDIMENTO", "RESGATE"]): return "FCI", "FLUXO DE CAIXA DE INVESTIMENTO", "Movimentação aplicações", conta

    # ---------------- FLUXO DE CAIXA DE FINANCIAMENTO (FCF) ----------------
    if any(c in conta for c in ["CAPTAÇÕES", "EMPRÉSTIMO"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "Captações", conta
    if any(c in conta for c in ["PMT", "PARCELA FINANCIAMENTO"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "PMT por banco", conta
    if any(c in conta for c in ["IMPOSTOS PARCELADOS", "PARCELAMENTO"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "Saídas – Impostos parcelados", conta
    if any(c in conta for c in ["JUROS", "TARIFAS", "IOF", "TAXA"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "Despesas financeiras - Juros e Tarifas", conta

    # Fallback genérico baseado no débito/crédito (resolvido depois na soma)
    return "OUTROS", "OUTROS", "Não Classificado", conta

# ==============================================================================
# 3. CARREGAR E PROCESSAR DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def preparar_dados_dre():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()

    try:
        df = conn.read(worksheet="Extratos_Bancos", ttl=0)
        # Identificar colunas dinamicamente
        col_data = df.columns[1]
        col_deb = next((c for c in df.columns if 'débito' in str(c).lower()), df.columns[4])
        col_cred = next((c for c in df.columns if 'crédito' in str(c).lower()), df.columns[5])
        col_conta = df.columns[8] if len(df.columns) >= 9 else df.columns[-1] # Tenta pegar a Coluna I ou a última

        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Débito'] = df[col_deb].apply(limpa_valor)
        df['Crédito'] = df[col_cred].apply(limpa_valor)
        
        # Fluxo de Caixa = Créditos - Débitos
        df['Valor Líquido'] = df['Crédito'] - df['Débito']
        df['Mês_Ano'] = df['Data'].dt.to_period('M')

        # Aplicar classificação
        df['Macro'], df['Grupo'], df['Subgrupo'], df['Conta'] = zip(*df[col_conta].apply(classificar_conta))
        
        return df[df['Data'].notna()]
    except Exception as e:
        st.error(f"Erro ao gerar DRE: {e}")
        return pd.DataFrame()

df_base = preparar_dados_dre()

if df_base.empty:
    st.stop()

# ==============================================================================
# BARRA LATERAL (FILTROS)
# ==============================================================================
with st.sidebar:
    st.markdown("### Filtros da DRE")
    meses_disponiveis = sorted(df_base['Mês_Ano'].unique())
    if len(meses_disponiveis) >= 2:
        mes_padrao_fim = meses_disponiveis[-1]
        mes_padrao_ini = meses_disponiveis[0] if len(meses_disponiveis) <= 4 else meses_disponiveis[-4]
    else:
        mes_padrao_fim = mes_padrao_ini = meses_disponiveis[0] if meses_disponiveis else pd.Period.now('M')

    periodo_selecionado = st.select_slider(
        "Selecione o Horizonte de Análise:",
        options=meses_disponiveis,
        value=(mes_padrao_ini, mes_padrao_fim)
    )

# Filtrar o DataFrame pelos meses selecionados
meses_filtrados = [m for m in meses_disponiveis if periodo_selecionado[0] <= m <= periodo_selecionado[1]]
df_filtro = df_base[df_base['Mês_Ano'].isin(meses_filtrados)].copy()

# ==============================================================================
# 4. MOTOR DA DRE (AGRUPAMENTOS E MATEMÁTICA)
# ==============================================================================
# Tabela Pivotada base
pivot = df_filtro.groupby(['Macro', 'Grupo', 'Subgrupo', 'Conta', 'Mês_Ano'])['Valor Líquido'].sum().unstack(fill_value=0)

# Estrutura do Relatório
relatorio = []
meses_str = [str(m) for m in meses_filtrados]

def buscar_soma(macro=None, grupo=None, subgrupo=None):
    df_temp = df_filtro.copy()
    if macro: df_temp = df_temp[df_temp['Macro'] == macro]
    if grupo: df_temp = df_temp[df_temp['Grupo'] == grupo]
    if subgrupo: df_temp = df_temp[df_temp['Subgrupo'] == subgrupo]
    somas = df_temp.groupby('Mês_Ano')['Valor Líquido'].sum()
    return {str(m): somas.get(m, 0.0) for m in meses_filtrados}

# Cálculos Macro
entradas_op = buscar_soma(grupo="ENTRADAS OPERACIONAIS")
saidas_op = buscar_soma(grupo="SAÍDAS OPERACIONAIS")
fco = buscar_soma(macro="FCO")
fci = buscar_soma(macro="FCI")
fcf = buscar_soma(macro="FCF")

geracao_liquida = {m: fco.get(m, 0) + fci.get(m, 0) + fcf.get(m, 0) for m in meses_str}

# Construindo as linhas da tabela
def adicionar_linha(nome, tipo, valores, pai=None):
    linha = {'Conta Gerencial': nome, 'Tipo': tipo}
    for i, m in enumerate(meses_str):
        val = valores.get(m, 0)
        # Análise Vertical (AV) = % sobre as Entradas Operacionais
        av = (val / entradas_op.get(m, 1)) * 100 if entradas_op.get(m, 0) != 0 else 0
        
        # Análise Horizontal (AH) = Variação em relação ao mês anterior
        ah = 0
        if i > 0:
            m_ant = meses_str[i-1]
            val_ant = valores.get(m_ant, 0)
            if val_ant != 0:
                ah = ((val / val_ant) - 1) * 100
        
        linha[f"{m}_Realizado"] = val
        linha[f"{m}_AV"] = av
        linha[f"{m}_AH"] = ah
    relatorio.append(linha)

# === MONTAGEM DA HIERARQUIA ===
adicionar_linha("FLUXO DE CAIXA OPERACIONAL (FCO)", "macro", fco)

# ENTRADAS
adicionar_linha("ENTRADAS OPERACIONAIS", "grupo", entradas_op)
for subg in ["CONVÊNIOS", "PARTICULARES", "OUTRAS ENTRADAS OPERACIONAIS"]:
    somas_sub = buscar_soma(grupo="ENTRADAS OPERACIONAIS", subgrupo=subg)
    if any(v != 0 for v in somas_sub.values()):
        adicionar_linha(subg, "subgrupo", somas_sub)
        # Contas filhas
        df_contas = df_filtro[(df_filtro['Grupo'] == 'ENTRADAS OPERACIONAIS') & (df_filtro['Subgrupo'] == subg)]
        for conta in df_contas['Conta'].unique():
            soma_conta = buscar_soma(grupo="ENTRADAS OPERACIONAIS", subgrupo=subg, conta=conta) # Nota: requer ajuste no buscar_soma
            soma_c = df_contas[df_contas['Conta'] == conta].groupby('Mês_Ano')['Valor Líquido'].sum()
            dict_soma = {str(m): soma_c.get(m, 0) for m in meses_filtrados}
            adicionar_linha(conta, "item", dict_soma)

# SAÍDAS
adicionar_linha("SAÍDAS OPERACIONAIS", "grupo", saidas_op)
for subg in ["Pessoal", "Honorários Médicos", "Fornecedores assistenciais", "Impostos correntes", "Despesas administrativas e de infraestrutura", "Compras para estoque"]:
    somas_sub = buscar_soma(grupo="SAÍDAS OPERACIONAIS", subgrupo=subg)
    if any(v != 0 for v in somas_sub.values()):
        adicionar_linha(subg, "subgrupo", somas_sub)

# FCI e FCF
adicionar_linha("FLUXO DE CAIXA DE INVESTIMENTO (FCI)", "macro", fci)
adicionar_linha("FLUXO DE CAIXA DE FINANCIAMENTO (FCF)", "macro", fcf)

# RESULTADO FINAL
adicionar_linha("GERAÇÃO LÍQUIDA DE CAIXA", "macro", geracao_liquida)

# ==============================================================================
# 5. HEADER & KPIs (ESTILO IMAGEM)
# ==============================================================================
# Calcula métricas para o último mês selecionado
mes_atual = meses_str[-1]
receita_bruta_atual = entradas_op.get(mes_atual, 0)
custos_atual = saidas_op.get(mes_atual, 0)
pct_custos = (abs(custos_atual) / receita_bruta_atual * 100) if receita_bruta_atual != 0 else 0
ebitda_atual = fco.get(mes_atual, 0)
lucro_atual = geracao_liquida.get(mes_atual, 0)
pct_lucro = (lucro_atual / receita_bruta_atual * 100) if receita_bruta_atual != 0 else 0

st.markdown("""
<div class="top-header">
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="font-size:24px;">☰</span>
        <h1>DRE VERTICAL E FLUXO DE CAIXA</h1>
    </div>
    <div style="font-size:12px; color:#e0e0e0;">
        INICIO &nbsp;&nbsp;|&nbsp;&nbsp; <b>DRE VERTICAL</b> &nbsp;&nbsp;|&nbsp;&nbsp; EVOLUÇÃO
    </div>
</div>
""", unsafe_allow_html=True)

# Geração dos Cards via HTML
html_kpis = f"""
<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-value">{formata_moeda(receita_bruta_atual)}</div>
        <div class="kpi-label">Entradas Operacionais</div>
        <div class="kpi-sparkline"></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-value" style="color: #f87171;">{formata_moeda(custos_atual)}</div>
        <div class="kpi-label">Saídas Operacionais</div>
        <div class="kpi-sparkline"></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-value" style="color: #f87171;">-{formata_pct(pct_custos)}</div>
        <div class="kpi-label">% Custos e Despesas</div>
        <div class="kpi-sparkline"></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-value">{formata_moeda(ebitda_atual)}</div>
        <div class="kpi-label">EBITDA (F.C.O)</div>
        <div class="kpi-sparkline"></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-value">{formata_moeda(lucro_atual)}</div>
        <div class="kpi-label">Geração Líquida (Caixa)</div>
        <div class="kpi-sparkline"></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-value">{formata_pct(pct_lucro)}</div>
        <div class="kpi-label">% Margem Líquida</div>
        <div class="kpi-sparkline"></div>
    </div>
</div>
"""
st.markdown(html_kpis, unsafe_allow_html=True)

# ==============================================================================
# 6. RENDERIZAÇÃO DA TABELA HTML CUSTOMIZADA
# ==============================================================================
# Montando o cabeçalho
html_table = "<div class='dre-container'><table class='dre-table'><thead><tr>"
html_table += "<th rowspan='2' class='text-left' style='min-width: 280px; font-size:14px;'>Conta Gerencial</th>"

for m in meses_str:
    nome_mes = pd.Period(m).strftime('%B/%Y').capitalize()
    html_table += f"<th colspan='3' class='month-header'>{nome_mes}</th>"
html_table += "</tr><tr>"

for m in meses_str:
    html_table += "<th class='sub-header'>Realizado</th>"
    html_table += "<th class='sub-header'>AV</th>"
    html_table += "<th class='sub-header'>AH</th>"
html_table += "</tr></thead><tbody>"

# Montando as linhas
for row in relatorio:
    tipo = row['Tipo']
    class_name = ""
    indent = ""
    
    if tipo == "macro": class_name = "macro-row"
    elif tipo == "grupo": class_name = "group-row"; indent = "indent-1"
    elif tipo == "subgrupo": class_name = "subgroup-row"; indent = "indent-2"
    else: class_name = "item-row"; indent = "indent-2 text-muted"

    html_table += f"<tr class='{class_name}'><td class='text-left {indent}'>{row['Conta Gerencial']}</td>"
    
    for m in meses_str:
        # Coluna Realizado
        bg_realizado = "background-color: var(--table-header-bg); color: white;" if tipo == "macro" else ""
        html_table += f"<td class='text-right' style='{bg_realizado}'>{formata_moeda(row[f'{m}_Realizado'])}</td>"
        
        # Coluna AV
        bg_av = "background-color: #0d82c2; color: white;" if tipo == "macro" else ""
        html_table += f"<td class='text-right' style='{bg_av}'>{formata_pct(row[f'{m}_AV'])}</td>"
        
        # Coluna AH (Com setas)
        ah_val = row[f'{m}_AH']
        if tipo == "macro":
            bg_ah = "background-color: #1a5f8f; color: white;"
            html_table += f"<td class='text-right' style='{bg_ah}'>{formata_pct(ah_val)}</td>"
        else:
            if ah_val > 0:
                html_table += f"<td class='text-right val-up arrow-up'>{formata_pct(ah_val)}</td>"
            elif ah_val < 0:
                html_table += f"<td class='text-right val-down arrow-down'>{formata_pct(ah_val)}</td>"
            else:
                html_table += f"<td class='text-right'>{formata_pct(ah_val)}</td>"

    html_table += "</tr>"

html_table += "</tbody></table></div>"

# Renderiza a tabela na tela
st.markdown(html_table, unsafe_allow_html=True)
st.markdown("<br><p style='text-align:right; font-size:10px; color:#888;'>*AV = Análise Vertical (Base: Entradas Op.) | AH = Análise Horizontal (Crescimento MoM)</p>", unsafe_allow_html=True)
