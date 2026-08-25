import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE e Fluxo de Caixa", layout="wide", page_icon="📈")

# ==============================================================================
# CUSTOM CSS — IDENTIDADE CORPORATIVA + TABELA EXPANSÍVEL
# ==============================================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    :root {
        --bg: #f4f6f8;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --border: #dfe4ea;
        --border-strong: #cbd3dc;
        --text: #17212b;
        --text-secondary: #44515f;
        --muted: #6b7785;
        --primary: #234a78;
        --primary-dark: #193754;
        --success: #157a5b;
        --danger: #b74242;
        --warning: #996b10;
        --info: #2f657a;
        --shadow: 0 2px 6px rgba(16, 24, 40, 0.04);
    }
    
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .main { background: var(--bg); }
    .main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 1rem; }
    
    /* Cabeçalho */
    .dashboard-header { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; min-height: 64px; padding: 5px 0 11px; margin-bottom: 15px; border-bottom: 1px solid var(--border-strong); }
    .header-period { min-width: 210px; text-align: left; }
    .header-period .date { font-size: 16px; font-weight: 800; color: var(--text); letter-spacing: -0.15px; }
    .header-period .label { margin-top: 3px; font-size: 9px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.75px; }
    .header-center { text-align: center; padding: 0 25px; }
    .header-center h1 { margin: 0; color: var(--primary-dark); font-size: 20px; line-height: 1.2; font-weight: 850; letter-spacing: 0.4px; text-transform: uppercase; }
    .header-center p { margin: 4px 0 0; color: var(--muted); font-size: 9px; font-weight: 600; letter-spacing: 0.45px; text-transform: uppercase; }
    
    .update-wrapper { display: flex; justify-content: flex-end; }
    .update-badge { min-width: 122px; padding: 6px 11px; text-align: left; border-left: 3px solid var(--primary); background: #f8fafc; }
    .update-badge span { display: block; font-size: 8px; font-weight: 800; color: var(--muted); text-transform: uppercase; }
    .update-badge b { display: block; margin-top: 2px; font-size: 11px; font-weight: 800; color: var(--text); }
    
    /* KPI Cards no Topo */
    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 20px; }
    .kpi-card { position: relative; min-height: 92px; padding: 13px 16px 12px 17px; background: var(--surface); border: 1px solid var(--border); border-radius: 4px; box-shadow: var(--shadow); overflow: hidden; }
    .kpi-card::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--primary); }
    .kpi-card.receita::before { background: var(--success); }
    .kpi-card.despesa::before { background: var(--danger); }
    .kpi-card.ebitda::before { background: var(--info); }
    
    .kpi-title { font-size: 10px; font-weight: 800; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
    .kpi-value { font-size: 22px; font-weight: 850; color: var(--text); letter-spacing: -0.4px; white-space: nowrap; font-variant-numeric: tabular-nums; }
    
    /* Tabela DRE Estilo Grid (HTML5 Details) */
    .dre-container { background: var(--surface); border: 1px solid var(--border-strong); border-radius: 4px; box-shadow: var(--shadow); font-size: 12px; margin-bottom: 20px; overflow-x: auto; }
    
    .dre-row { display: grid; border-bottom: 1px solid var(--border); align-items: center; transition: background 0.2s; }
    .dre-row:hover { background-color: var(--surface-soft); }
    
    .dre-col-name { padding: 8px 15px; font-weight: 600; color: var(--text); white-space: nowrap; }
    .dre-col-val { padding: 8px 10px; text-align: right; font-variant-numeric: tabular-nums; color: #2d3742; font-weight: 600; }
    
    /* Cabeçalhos */
    .dre-header { background: #edf1f5; border-bottom: 2px solid var(--border-strong); font-weight: 800; color: #46525f; text-transform: uppercase; font-size: 11px; }
    .dre-header .dre-col-val { text-align: center; font-weight: 800; }
    
    /* Hierarquia */
    .lvl-macro { background-color: #eef2f6; font-size: 13px; }
    .lvl-macro .dre-col-name { font-weight: 850; color: var(--primary-dark); text-transform: uppercase; }
    .lvl-macro .dre-col-val { font-weight: 850; color: var(--primary-dark); }
    
    .lvl-grupo { background-color: #f8fafc; border-bottom: 1px solid var(--border); }
    .lvl-grupo .dre-col-name { padding-left: 20px; color: var(--text); font-weight: 700; font-size: 11px; }
    
    .lvl-subgrupo .dre-col-name { padding-left: 35px; color: var(--text-secondary); font-size: 11px; font-weight: 600; }
    
    .lvl-item .dre-col-name { padding-left: 55px; color: var(--muted); font-size: 10px; font-weight: 500; }
    .lvl-item .dre-col-val { font-weight: 500; font-size: 11px; color: var(--muted); }
    
    /* Expansão com Details/Summary */
    details { width: 100%; display: block; }
    details summary { list-style: none; cursor: pointer; outline: none; }
    details summary::-webkit-details-marker { display: none; }
    
    /* Ícones de [+] e [-] */
    .icon-expand { font-family: monospace; font-weight: 800; color: var(--primary); margin-right: 6px; font-size: 12px; }
    details:not([open]) > summary .icon-expand::before { content: "[+]"; }
    details[open] > summary .icon-expand::before { content: "[-]"; }
    
    /* Gráficos Containers */
    .chart-box { background: var(--surface); border: 1px solid var(--border-strong); border-radius: 4px; padding: 15px 10px 5px; box-shadow: var(--shadow); }
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

def formata_num(valor):
    if pd.isna(valor) or valor == 0: return "-"
    # Formata número com separador de milhar
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_kpi(valor):
    if pd.isna(valor): return "R$ 0"
    abs_val = abs(valor)
    prefix = "-" if valor < 0 else ""
    if abs_val >= 1_000_000: return f"{prefix}R$ {abs_val/1_000_000:.1f} M".replace('.', ',')
    elif abs_val >= 1_000: return f"{prefix}R$ {abs_val/1_000:.1f} K".replace('.', ',')
    else: return f"{prefix}R$ {abs_val:.0f}"

def formata_pct(valor):
    if pd.isna(valor) or valor == 0: return "0,0%"
    return f"{valor:.1f}%".replace('.', ',')

# ==============================================================================
# 2. MAPEAMENTO HIERÁRQUICO DA DRE
# ==============================================================================
def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    
    # ENTRADAS
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "POSTAL", "CASACARESC", "CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "SEGURADORAS", "CAPESAUDE", "SIM SAÚDE", "EMBRATEL", "SAUDES", "CONAB"]
    if any(c in conta for c in convênios): return "(+) RECEITAS OPERACIONAIS", "Receitas Convênios", conta
    
    particulares = ["CARTÃO", "DINHEIRO", "PARTICULAR", "DEVOLUÇÃO"]
    if any(c in conta for c in particulares): return "(+) RECEITAS OPERACIONAIS", "Receitas Particulares", conta
    
    outras_receitas = ["ALUGUÉIS", "UNIVERSIDADE", "OUTRAS RECEITAS"]
    if any(c in conta for c in outras_receitas): return "(+) RECEITAS OPERACIONAIS", "Outras Receitas Operacionais", conta

    # SAÍDAS
    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "FÉRIAS", "INSS", "FGTS"]): return "(-) DESPESAS OPERACIONAIS", "Despesas Pessoal", conta
    if any(c in conta for c in ["HONORÁRIOS MÉDICOS", "MÉDICO"]): return "(-) DESPESAS OPERACIONAIS", "Honorários Médicos", conta
    if any(c in conta for c in ["FORNECEDORES", "CUSTO", "MEDICAMENTOS", "OPME", "ESTOQUE"]): return "(-) DESPESAS OPERACIONAIS", "Fornecedores Assistenciais", conta
    if any(c in conta for c in ["IMPOSTOS", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): return "(-) DESPESAS OPERACIONAIS", "Impostos Correntes", conta
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "ÁGUA", "INTERNET", "CONTABILIDADE"]): return "(-) DESPESAS OPERACIONAIS", "Despesas Administrativas", conta
    
    # INVESTIMENTOS E FINANCIAMENTOS (Agrupados em "Outras Despesas e Receitas" para simplificar DRE Clássica)
    if any(c in conta for c in ["APLICAÇÕES", "RENDIMENTO", "RESGATE"]): return "(+) RECEITAS FINANCEIRAS", "Rendimentos e Aplicações", conta
    if any(c in conta for c in ["JUROS", "TARIFAS", "IOF", "TAXA"]): return "(-) DESPESAS FINANCEIRAS", "Juros e Tarifas Bancárias", conta
    
    # Restante (Obras, PMT, Captações)
    return "(=) OUTRAS DESPESAS E RECEITAS", "Outras Movimentações (Capex/Financ)", conta

# ==============================================================================
# 3. PREPARAR DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def preparar_dados_dre():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()

    try:
        df = conn.read(worksheet="Extratos_Bancos", ttl=0)
        col_data = df.columns[1]
        col_deb = df.columns[4] if len(df.columns) > 4 else df.columns[-3]
        col_cred = df.columns[5] if len(df.columns) > 5 else df.columns[-2]
        col_conta = df.columns[8] if len(df.columns) > 8 else df.columns[-1]

        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Débito'] = df[col_deb].apply(limpa_valor)
        df['Crédito'] = df[col_cred].apply(limpa_valor)
        
        df['Valor Líquido'] = df['Crédito'] - df['Débito']
        df['Mês_Ano'] = df['Data'].dt.to_period('M')

        df['Grupo'], df['Subgrupo'], df['Conta'] = zip(*df[col_conta].apply(classificar_conta))
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
    mes_padrao_ini = meses_disponiveis[0] if len(meses_disponiveis) <= 6 else meses_disponiveis[-6]
    mes_padrao_fim = meses_disponiveis[-1] if meses_disponiveis else pd.Period.now('M')

    periodo_selecionado = st.select_slider(
        "Horizonte de Análise:",
        options=meses_disponiveis,
        value=(mes_padrao_ini, mes_padrao_fim)
    )

meses_filtrados = [m for m in meses_disponiveis if periodo_selecionado[0] <= m <= periodo_selecionado[1]]
df_filtro = df_base[df_base['Mês_Ano'].isin(meses_filtrados)].copy()
meses_str = [str(m) for m in meses_filtrados]

# ==============================================================================
# 4. MOTOR MATEMÁTICO
# ==============================================================================
def buscar_soma(grupo=None, subgrupo=None, conta=None):
    df_temp = df_filtro.copy()
    if grupo: df_temp = df_temp[df_temp['Grupo'] == grupo]
    if subgrupo: df_temp = df_temp[df_temp['Subgrupo'] == subgrupo]
    if conta: df_temp = df_temp[df_temp['Conta'] == conta]
    somas = df_temp.groupby('Mês_Ano')['Valor Líquido'].sum()
    return {str(m): somas.get(m, 0.0) for m in meses_filtrados}

# Totais das Linhas Macros
rec_op = buscar_soma(grupo="(+) RECEITAS OPERACIONAIS")
desp_op = buscar_soma(grupo="(-) DESPESAS OPERACIONAIS")
ebitda = {m: rec_op.get(m,0) + desp_op.get(m,0) for m in meses_str}

rec_fin = buscar_soma(grupo="(+) RECEITAS FINANCEIRAS")
desp_fin = buscar_soma(grupo="(-) DESPESAS FINANCEIRAS")
outros = buscar_soma(grupo="(=) OUTRAS DESPESAS E RECEITAS")

geracao_liquida = {m: ebitda.get(m,0) + rec_fin.get(m,0) + desp_fin.get(m,0) + outros.get(m,0) for m in meses_str}

# ==============================================================================
# 5. CABEÇALHO E KPIs (TOPO)
# ==============================================================================
mes_atual = meses_str[-1]
val_receitas = rec_op.get(mes_atual, 0)
val_despesas = desp_op.get(mes_atual, 0)
val_ebitda = ebitda.get(mes_atual, 0)
val_superavit = geracao_liquida.get(mes_atual, 0)
val_margem = (val_superavit / val_receitas * 100) if val_receitas != 0 else 0

periodo_str = f"{pd.Period(meses_str[0]).strftime('%m/%Y')} - {pd.Period(mes_atual).strftime('%m/%Y')}"

st.markdown(f"""
<div class="dashboard-header">
    <div class="header-period">
        <div class="date">{periodo_str}</div>
        <div class="label">Período de Análise</div>
    </div>
    <div class="header-center">
        <h1>DRE GERENCIAL E RESULTADO</h1>
        <p>Acompanhamento de Receitas, Custos e Superávit Líquido</p>
    </div>
    <div class="update-wrapper">
        <div class="update-badge">
            <span>Mês Referência</span>
            <b>{pd.Period(mes_atual).strftime('%B %Y').upper()}</b>
        </div>
    </div>
</div>

<div class="kpi-grid">
    <div class="kpi-card receita">
        <div class="kpi-title">Receitas Operacionais</div>
        <div class="kpi-value" style="color: var(--success);">{formata_kpi(val_receitas)}</div>
    </div>
    <div class="kpi-card despesa">
        <div class="kpi-title">Despesas Operacionais</div>
        <div class="kpi-value" style="color: var(--danger);">{formata_kpi(val_despesas)}</div>
    </div>
    <div class="kpi-card ebitda">
        <div class="kpi-title">EBITDA (Ger. Caixa)</div>
        <div class="kpi-value" style="color: var(--info);">{formata_kpi(val_ebitda)}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">Superávit/Déficit Líquido</div>
        <div class="kpi-value" style="color: var(--primary-dark);">{formata_kpi(val_superavit)}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">Margem Superávit</div>
        <div class="kpi-value" style="color: var(--primary);">{formata_pct(val_margem)}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 6. TABELA DRE HTML5 (ACORDEÃO CORPORATIVO)
# ==============================================================================
grid_template = f"minmax(300px, 1.5fr) repeat({len(meses_str)}, minmax(100px, 1fr))"

def render_linha(nome, classe, valores, icone=""):
    cor_texto = ""
    if "RECEITAS" in nome: cor_texto = "color: var(--success);"
    elif "DESPESAS" in nome: cor_texto = "color: var(--danger);"
    
    html = f"<div class='dre-row {classe}' style='grid-template-columns: {grid_template};'>"
    html += f"<div class='dre-col-name'>{icone}{nome}</div>"
    
    for m in meses_str:
        val = valores.get(m, 0)
        # Aplica cor no valor das linhas MACRO
        cor_val = cor_texto if classe == 'lvl-macro' else ""
        html += f"<div class='dre-col-val' style='{cor_val}'>{formata_num(val)}</div>"
    
    html += "</div>"
    return html

def render_bloco(nome_grupo, func_soma):
    somas_grupo = func_soma(grupo=nome_grupo)
    if all(v == 0 for v in somas_grupo.values()): return ""
    
    block = "<details><summary>" + render_linha(nome_grupo, "lvl-grupo", somas_grupo, "<span class='icon-expand'></span>") + "</summary>"
    
    df_g = df_filtro[df_filtro['Grupo'] == nome_grupo]
    for subg in sorted(df_g['Subgrupo'].unique()):
        somas_sub = func_soma(grupo=nome_grupo, subgrupo=subg)
        if any(v != 0 for v in somas_sub.values()):
            
            # Se for linha de receita ou despesa, formata o texto sutilmente
            prefixo = "(+) " if "RECEITA" in nome_grupo else "(-) " if "DESPESA" in nome_grupo else ""
            block += "<details><summary>" + render_linha(f"{prefixo}{subg}", "lvl-subgrupo", somas_sub, "<span class='icon-expand'></span>") + "</summary>"
            
            # Contas finais
            df_s = df_g[df_g['Subgrupo'] == subg]
            for conta in sorted(df_s['Conta'].unique()):
                somas_c = func_soma(grupo=nome_grupo, subgrupo=subg, conta=conta)
                if any(v != 0 for v in somas_c.values()):
                    block += render_linha(conta, "lvl-item", somas_c)
            
            block += "</details>"
    block += "</details>"
    return block

# Construção do Quadro DRE
html_dre = f"<div class='dre-container'>"
html_dre += f"<div class='dre-row dre-header' style='grid-template-columns: {grid_template};'>"
html_dre += "<div class='dre-col-name'>CONTA GERENCIAL / GRUPO</div>"
for m in meses_str:
    html_dre += f"<div class='dre-col-val'>{pd.Period(m).strftime('%b/%Y').lower()}</div>"
html_dre += "</div>"

# Anexando os blocos
html_dre += render_bloco("(+) RECEITAS OPERACIONAIS", buscar_soma)
html_dre += render_bloco("(-) DESPESAS OPERACIONAIS", buscar_soma)
html_dre += render_linha("(=) RESULTADO OPERACIONAL (EBITDA)", "lvl-macro", ebitda)
html_dre += render_bloco("(+) RECEITAS FINANCEIRAS", buscar_soma)
html_dre += render_bloco("(-) DESPESAS FINANCEIRAS", buscar_soma)
html_dre += render_bloco("(=) OUTRAS DESPESAS E RECEITAS", buscar_soma)
html_dre += render_linha("(=) SUPERÁVIT / DÉFICIT LÍQUIDO", "lvl-macro", geracao_liquida)

html_dre += "</div>"

st.markdown(html_dre, unsafe_allow_html=True)
st.markdown("<p style='text-align:right; font-size:10px; color:#6b7785; margin-top:-10px;'>*Clique no <b>[+]</b> para expandir o detalhamento das contas.</p>", unsafe_allow_html=True)

# ==============================================================================
# 7. GRÁFICOS NO RODAPÉ
# ==============================================================================
c_graf1, c_graf2 = st.columns(2)

eixos_x = [pd.Period(m).strftime('%b/%Y').lower() for m in meses_str]
y_superavit = [geracao_liquida.get(m, 0) for m in meses_str]
y_margem = [(geracao_liquida.get(m,0)/rec_op.get(m,1))*100 if rec_op.get(m,0) != 0 else 0 for m in meses_str]

cores_barra = ['#157a5b' if v >= 0 else '#b74242' for v in y_superavit]

# Gráfico 1: Barras de Superávit
fig1 = go.Figure(data=[
    go.Bar(
        x=eixos_x, y=y_superavit, 
        marker_color=cores_barra,
        text=[formata_kpi(v) for v in y_superavit],
        textposition='outside',
        textfont=dict(color='#17212b', size=11, weight='bold')
    )
])
fig1.update_layout(
    title=dict(text="Evolução do Superávit/Déficit (R$)", font=dict(color='#193754', size=14, weight='bold')),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(showgrid=False, tickfont=dict(color='#6b7785')),
    yaxis=dict(showgrid=True, gridcolor='#edf0f3', showticklabels=False, zeroline=True, zerolinecolor='#cbd3dc'),
    margin=dict(t=35, b=10, l=10, r=10),
    height=240,
    bargap=0.3
)

with c_graf1:
    st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
    st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

# Gráfico 2: Linha de Margem
cores_texto_margem = ['#157a5b' if v >= 0 else '#b74242' for v in y_margem]
fig2 = go.Figure(data=[
    go.Scatter(
        x=eixos_x, y=y_margem, 
        mode='lines+markers+text',
        line=dict(color='#234a78', width=3),
        marker=dict(size=8, color='#234a78'),
        text=[formata_pct(v) for v in y_margem],
        textposition='top center',
        textfont=dict(color=cores_texto_margem, size=11, weight='bold')
    )
])
fig2.update_layout(
    title=dict(text="Margem de Superávit (%)", font=dict(color='#193754', size=14, weight='bold')),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(showgrid=False, tickfont=dict(color='#6b7785')),
    yaxis=dict(showgrid=True, gridcolor='#edf0f3', showticklabels=False, zeroline=True, zerolinecolor='#cbd3dc'),
    margin=dict(t=35, b=10, l=10, r=10),
    height=240
)

with c_graf2:
    st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)
