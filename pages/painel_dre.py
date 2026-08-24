import streamlit as st
import pandas as pd
import re
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE e Fluxo de Caixa Gerencial", layout="wide", page_icon="📈")

# --- CUSTOM CSS (Design Moderno & Tabela Expansível) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    :root {
        --bg-color: #f4f7f9;
        --card-bg: #ffffff;
        --border-color: #e2e8f0;
        --text-main: #1e293b;
        --text-muted: #64748b;
        --primary: #2563eb;
        --success: #10b981;
        --danger: #ef4444;
    }
    
    .main .block-container { max-width: 98%; padding-top: 1.5rem; font-family: 'Inter', sans-serif; }
    
    /* Top Header */
    .dash-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; padding: 15px 25px; background: var(--card-bg); border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid var(--border-color); }
    .dash-header h1 { margin: 0; font-size: 22px; font-weight: 700; color: var(--text-main); }
    .dash-header p { margin: 0; font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    
    /* KPI Cards Modernos */
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
    .kpi-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); transition: transform 0.2s; }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); }
    .kpi-title { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .kpi-val { font-size: 24px; font-weight: 700; color: var(--text-main); line-height: 1.2; }
    
    /* Tabela DRE Grid Customizada */
    .dre-wrapper { background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border-color); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); overflow: hidden; font-size: 13px; }
    .dre-row { display: grid; border-bottom: 1px solid #f1f5f9; align-items: center; }
    .dre-row:hover { background-color: #f8fafc; }
    .col-name { padding: 12px 15px; font-weight: 600; color: var(--text-main); }
    .col-val { padding: 12px 10px; text-align: right; font-variant-numeric: tabular-nums; }
    
    /* Cabeçalhos da Tabela */
    .dre-header { background: #f8fafc; border-bottom: 2px solid var(--border-color); font-weight: 700; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
    .dre-subheader { background: #ffffff; border-bottom: 1px solid var(--border-color); font-weight: 700; color: #94a3b8; font-size: 10px; text-transform: uppercase; }
    .month-title { text-align: center; border-left: 1px solid #f1f5f9; padding: 8px; font-size: 12px; color: var(--text-main); }
    
    /* Hierarquia e Cores de Linha */
    .row-macro { background-color: #e0e7ff; color: #1e3a8a !important; border-bottom: 2px solid #c7d2fe; font-size: 14px; }
    .row-macro .col-name { font-weight: 800; color: #1e3a8a; text-transform: uppercase; }
    .row-grupo { background-color: #f1f5f9; }
    .row-grupo .col-name { padding-left: 25px; color: #334155; }
    
    /* Mágica do Expandir/Recolher (HTML5 Details) */
    details { margin: 0; padding: 0; }
    details summary { list-style: none; cursor: pointer; outline: none; }
    details summary::-webkit-details-marker { display: none; }
    
    .row-subgrupo .col-name { padding-left: 45px; position: relative; color: #475569; }
    .row-subgrupo .col-name::before { content: '▶'; position: absolute; left: 25px; font-size: 9px; top: 15px; color: #94a3b8; transition: transform 0.2s; }
    details[open] > summary .row-subgrupo .col-name::before { transform: rotate(90deg); color: var(--primary); }
    
    .details-content { border-left: 3px solid #e2e8f0; margin-left: 15px; background: #ffffff; }
    .row-item .col-name { padding-left: 65px; font-weight: 400; color: #64748b; font-size: 12px; }
    
    /* Setas e Cores AH/AV */
    .val-up { color: var(--success); font-weight: 600; }
    .val-down { color: var(--danger); font-weight: 600; }
    .arrow-up::before { content: '↑ '; }
    .arrow-down::before { content: '↓ '; }
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
    return f"{prefixo}R$ {abs(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_pct(valor):
    if pd.isna(valor) or valor == 0: return "-"
    return f"{valor:.1f}%".replace('.', ',')

# ==============================================================================
# 2. MAPEAMENTO HIERÁRQUICO DE CONTAS CONTÁBEIS (CLASSIFICAÇÃO DRE)
# ==============================================================================
def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    
    # ENTRADAS OPERACIONAIS
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "POSTAL SAÚDE", "CASACARESC", "SAÚDE CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SELECT SAÚDE", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "PETRÓLEO", "ELO SAÚDE", "SEGURADORAS", "CAPESAUDE", "CAPESESP", "SIM SAÚDE", "EMBRATEL", "AMAP", "OMINT", "WORLD MEDICAL CARE", "SAUDES", "LIFE", "CLINCARD", "CONAB", "PRÉVIDA", "BRADESCO OPERADORA"]
    if any(c in conta for c in convênios): return "FCO", "ENTRADAS OPERACIONAIS", "CONVÊNIOS", conta
    
    particulares = ["CARTÃO", "DINHEIRO", "COBRANÇA PARTICULAR", "DEVOLUÇÃO PACIENTE"]
    if any(c in conta for c in particulares): return "FCO", "ENTRADAS OPERACIONAIS", "PARTICULARES", conta
    
    outras_receitas = ["ALUGUÉIS RECEBIDOS", "UNIVERSIDADE", "OUTRAS RECEITAS"]
    if any(c in conta for c in outras_receitas): return "FCO", "ENTRADAS OPERACIONAIS", "OUTRAS ENTRADAS OPERACIONAIS", conta

    # SAÍDAS OPERACIONAIS
    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "FÉRIAS", "INSS", "FGTS"]): return "FCO", "SAÍDAS OPERACIONAIS", "Pessoal", conta
    if any(c in conta for c in ["HONORÁRIOS MÉDICOS", "MÉDICO"]): return "FCO", "SAÍDAS OPERACIONAIS", "Honorários Médicos", conta
    if any(c in conta for c in ["FORNECEDORES ASSISTENCIAIS", "CUSTO MATERIAIS", "MEDICAMENTOS", "OPME", "ESTOQUE"]): return "FCO", "SAÍDAS OPERACIONAIS", "Fornecedores assistenciais", conta
    if any(c in conta for c in ["IMPOSTOS CORRENTES", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): return "FCO", "SAÍDAS OPERACIONAIS", "Impostos correntes", conta
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "ÁGUA", "INTERNET", "CONTABILIDADE"]): return "FCO", "SAÍDAS OPERACIONAIS", "Despesas administrativas e de infraestrutura", conta
    
    # FCI E FCF
    if any(c in conta for c in ["OBRAS", "REFORMAS", "MÁQUINAS", "EQUIPAMENTOS"]): return "FCI", "FLUXO DE CAIXA DE INVESTIMENTO", "Obras e reformas", conta
    if any(c in conta for c in ["APLICAÇÕES", "RENDIMENTO", "RESGATE"]): return "FCI", "FLUXO DE CAIXA DE INVESTIMENTO", "Movimentação aplicações", conta
    if any(c in conta for c in ["CAPTAÇÕES", "EMPRÉSTIMO"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "Captações", conta
    if any(c in conta for c in ["PMT", "PARCELA FINANCIAMENTO"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "PMT por banco", conta
    if any(c in conta for c in ["IMPOSTOS PARCELADOS", "PARCELAMENTO"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "Saídas – Impostos parcelados", conta
    if any(c in conta for c in ["JUROS", "TARIFAS", "IOF", "TAXA"]): return "FCF", "FLUXO DE CAIXA DE FINANCIAMENTO", "Despesas financeiras - Juros e Tarifas", conta

    return "OUTROS", "OUTROS", "Não Classificado", conta

# ==============================================================================
# 3. CARREGAR E PROCESSAR DADOS COM COLUNAS ESPECÍFICAS
# ==============================================================================
@st.cache_data(ttl=60)
def preparar_dados_dre():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()

    try:
        df = conn.read(worksheet="Extratos_Bancos", ttl=0)
        
        # Mapeamento estrito das colunas conforme solicitado
        # B = Data (1), E = Débito (4), F = Crédito (5), I = Conta Contábil (8)
        col_data = df.columns[1]
        col_deb = df.columns[4] if len(df.columns) > 4 else df.columns[-3]
        col_cred = df.columns[5] if len(df.columns) > 5 else df.columns[-2]
        col_conta = df.columns[8] if len(df.columns) > 8 else df.columns[-1]

        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Débito'] = df[col_deb].apply(limpa_valor)
        df['Crédito'] = df[col_cred].apply(limpa_valor)
        
        # Matemática Correta: Valor Líquido = Entrada (Crédito) - Saída (Débito)
        df['Valor Líquido'] = df['Crédito'] - df['Débito']
        df['Mês_Ano'] = df['Data'].dt.to_period('M')

        # Aplicar classificação da DRE
        df['Macro'], df['Grupo'], df['Subgrupo'], df['Conta'] = zip(*df[col_conta].apply(classificar_conta))
        
        return df[df['Data'].notna()]
    except Exception as e:
        st.error(f"Erro ao gerar DRE: {e}")
        return pd.DataFrame()

df_base = preparar_dados_dre()
if df_base.empty: st.stop()

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

meses_filtrados = [m for m in meses_disponiveis if periodo_selecionado[0] <= m <= periodo_selecionado[1]]
df_filtro = df_base[df_base['Mês_Ano'].isin(meses_filtrados)].copy()
meses_str = [str(m) for m in meses_filtrados]

# ==============================================================================
# 4. MOTOR DA DRE (AGRUPAMENTOS E MATEMÁTICA)
# ==============================================================================
def buscar_soma(macro=None, grupo=None, subgrupo=None, conta=None):
    df_temp = df_filtro.copy()
    if macro: df_temp = df_temp[df_temp['Macro'] == macro]
    if grupo: df_temp = df_temp[df_temp['Grupo'] == grupo]
    if subgrupo: df_temp = df_temp[df_temp['Subgrupo'] == subgrupo]
    if conta: df_temp = df_temp[df_temp['Conta'] == conta]
    somas = df_temp.groupby('Mês_Ano')['Valor Líquido'].sum()
    return {str(m): somas.get(m, 0.0) for m in meses_filtrados}

entradas_op = buscar_soma(grupo="ENTRADAS OPERACIONAIS")
saidas_op = buscar_soma(grupo="SAÍDAS OPERACIONAIS")
fco = buscar_soma(macro="FCO")
fci = buscar_soma(macro="FCI")
fcf = buscar_soma(macro="FCF")
geracao_liquida = {m: fco.get(m, 0) + fci.get(m, 0) + fcf.get(m, 0) for m in meses_str}

# ==============================================================================
# 5. HEADER & KPIs MODERNOS
# ==============================================================================
mes_atual = meses_str[-1]
receita_atual = entradas_op.get(mes_atual, 0)
custos_atual = saidas_op.get(mes_atual, 0)
ebitda_atual = fco.get(mes_atual, 0)
lucro_atual = geracao_liquida.get(mes_atual, 0)

pct_custos = (abs(custos_atual) / receita_atual * 100) if receita_atual != 0 else 0
pct_lucro = (lucro_atual / receita_atual * 100) if receita_atual != 0 else 0

st.markdown(f"""
<div class="dash-header">
    <div>
        <h1>DRE & Fluxo de Caixa Gerencial</h1>
        <p>Análise Vertical, Horizontal e Detalhamento de Contas</p>
    </div>
    <div style="text-align: right;">
        <span style="background: #eff6ff; color: #2563eb; padding: 6px 12px; border-radius: 20px; font-weight: 700; font-size: 13px; border: 1px solid #bfdbfe;">
            Referência: {pd.Period(mes_atual).strftime('%B %Y').capitalize()}
        </span>
    </div>
</div>

<div class="kpi-grid">
    <div class="kpi-card" style="border-top: 4px solid #10b981;">
        <div class="kpi-title">Entradas Operacionais</div>
        <div class="kpi-val" style="color: #059669;">{formata_moeda(receita_atual)}</div>
    </div>
    <div class="kpi-card" style="border-top: 4px solid #ef4444;">
        <div class="kpi-title">Saídas Operacionais</div>
        <div class="kpi-val" style="color: #dc2626;">{formata_moeda(custos_atual)}</div>
    </div>
    <div class="kpi-card" style="border-top: 4px solid #f59e0b;">
        <div class="kpi-title">% Custos e Despesas</div>
        <div class="kpi-val" style="color: #d97706;">-{formata_pct(pct_custos)}</div>
    </div>
    <div class="kpi-card" style="border-top: 4px solid #3b82f6;">
        <div class="kpi-title">EBITDA (Geração Operacional)</div>
        <div class="kpi-val" style="color: #2563eb;">{formata_moeda(ebitda_atual)}</div>
    </div>
    <div class="kpi-card" style="border-top: 4px solid #6366f1;">
        <div class="kpi-title">Geração Líquida (Caixa)</div>
        <div class="kpi-val" style="color: #4f46e5;">{formata_moeda(lucro_atual)}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 6. MOTOR DE RENDERIZAÇÃO DA TABELA HTML COM SANFONA (EXPAND/COLLAPSE)
# ==============================================================================
grid_template = f"280px repeat({len(meses_str)*3}, minmax(75px, 1fr))"

def gerar_linha_html(nome, tipo, valores):
    css_class = f"row-{tipo}"
    html = f"<div class='dre-row {css_class}' style='grid-template-columns: {grid_template};'>"
    html += f"<div class='col-name'>{nome}</div>"
    
    for i, m in enumerate(meses_str):
        val = valores.get(m, 0)
        av = (val / entradas_op.get(m, 1)) * 100 if entradas_op.get(m, 0) != 0 else 0
        
        ah = 0
        if i > 0:
            val_ant = valores.get(meses_str[i-1], 0)
            if val_ant != 0: ah = ((val / val_ant) - 1) * 100
        
        # Realizado
        html += f"<div class='col-val'>{formata_moeda(val)}</div>"
        # AV
        html += f"<div class='col-val' style='color:#64748b;'>{formata_pct(av)}</div>"
        # AH com setas
        ah_class = "val-up arrow-up" if ah > 0 else ("val-down arrow-down" if ah < 0 else "")
        if tipo == "macro": ah_class = "" # Não põe seta vermelha/verde na linha Macro
        html += f"<div class='col-val {ah_class}'>{formata_pct(ah)}</div>"
        
    html += "</div>"
    return html

# Inicia a tabela Grid
html_grid = f"<div class='dre-wrapper'>"
html_grid += f"<div class='dre-row dre-header' style='grid-template-columns: {grid_template};'>"
html_grid += "<div class='col-name' style='padding-top:15px; padding-bottom:15px;'>CONTA GERENCIAL</div>"
for m in meses_str:
    nome_mes = pd.Period(m).strftime('%B/%Y').upper()
    html_grid += f"<div class='month-title' style='grid-column: span 3;'>{nome_mes}</div>"
html_grid += "</div>"

html_grid += f"<div class='dre-row dre-subheader' style='grid-template-columns: {grid_template};'>"
html_grid += "<div></div>"
for m in meses_str:
    html_grid += "<div style='text-align:right; padding:8px 10px;'>Realizado</div><div style='text-align:right; padding:8px 10px;'>AV</div><div style='text-align:right; padding:8px 10px;'>AH</div>"
html_grid += "</div>"

# === MONTAGEM DA HIERARQUIA COM <DETAILS> ===

html_grid += gerar_linha_html("FLUXO DE CAIXA OPERACIONAL (FCO)", "macro", fco)

# ENTRADAS
html_grid += gerar_linha_html("ENTRADAS OPERACIONAIS", "grupo", entradas_op)
for subg in ["CONVÊNIOS", "PARTICULARES", "OUTRAS ENTRADAS OPERACIONAIS"]:
    somas_sub = buscar_soma(grupo="ENTRADAS OPERACIONAIS", subgrupo=subg)
    if any(v != 0 for v in somas_sub.values()):
        # Acordeão do Subgrupo
        html_grid += "<details>"
        html_grid += f"<summary>{gerar_linha_html(subg, 'subgrupo', somas_sub)}</summary>"
        html_grid += "<div class='details-content'>"
        
        df_contas = df_filtro[(df_filtro['Grupo'] == 'ENTRADAS OPERACIONAIS') & (df_filtro['Subgrupo'] == subg)]
        for conta in sorted(df_contas['Conta'].unique()):
            soma_conta = buscar_soma(grupo="ENTRADAS OPERACIONAIS", subgrupo=subg, conta=conta)
            if any(v != 0 for v in soma_conta.values()):
                html_grid += gerar_linha_html(conta, "item", soma_conta)
                
        html_grid += "</div></details>"

# SAÍDAS
html_grid += gerar_linha_html("SAÍDAS OPERACIONAIS", "grupo", saidas_op)
for subg in ["Pessoal", "Honorários Médicos", "Fornecedores assistenciais", "Impostos correntes", "Despesas administrativas e de infraestrutura", "Compras para estoque"]:
    somas_sub = buscar_soma(grupo="SAÍDAS OPERACIONAIS", subgrupo=subg)
    if any(v != 0 for v in somas_sub.values()):
        # Acordeão do Subgrupo
        html_grid += "<details>"
        html_grid += f"<summary>{gerar_linha_html(subg, 'subgrupo', somas_sub)}</summary>"
        html_grid += "<div class='details-content'>"
        
        df_contas = df_filtro[(df_filtro['Grupo'] == 'SAÍDAS OPERACIONAIS') & (df_filtro['Subgrupo'] == subg)]
        for conta in sorted(df_contas['Conta'].unique()):
            soma_conta = buscar_soma(grupo="SAÍDAS OPERACIONAIS", subgrupo=subg, conta=conta)
            if any(v != 0 for v in soma_conta.values()):
                html_grid += gerar_linha_html(conta, "item", soma_conta)
                
        html_grid += "</div></details>"

html_grid += gerar_linha_html("FLUXO DE INVESTIMENTO (FCI)", "macro", fci)
html_grid += gerar_linha_html("FLUXO DE FINANCIAMENTO (FCF)", "macro", fcf)
html_grid += gerar_linha_html("GERAÇÃO LÍQUIDA DE CAIXA", "macro", geracao_liquida)

html_grid += "</div>" # Fecha o dre-wrapper

# Renderiza a tabela sanfona
st.markdown(html_grid, unsafe_allow_html=True)
st.markdown("<br><p style='text-align:right; font-size:11px; color:#94a3b8;'>*Clique nas setas (▶) nas linhas de convênios/despesas para abrir o detalhamento das contas.<br>AV = Análise Vertical (Base: Entradas Op.) | AH = Análise Horizontal (Var. Mês a Mês)</p>", unsafe_allow_html=True)
