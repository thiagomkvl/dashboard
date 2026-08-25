import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE e Fluxo de Caixa", layout="wide", page_icon="📈")

# ==============================================================================
# CUSTOM CSS — LIGHT MODE CORPORATIVO SUTIL
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
        --shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
    }
    
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; color: var(--text); }
    .stApp { background-color: var(--bg); }
    .main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 1rem; }
    header[data-testid="stHeader"] { display: none !important; }
    
    /* =========================================================
       KPIs TOP (Minimalista, fundo branco, linha sutil)
       ========================================================= */
    .kpi-container { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; box-shadow: var(--shadow); padding: 20px; display: flex; justify-content: space-between; margin-bottom: 20px; }
    .kpi-box { flex: 1; border-left: 3px solid var(--primary); padding-left: 15px; margin-right: 15px; }
    .kpi-box:last-child { margin-right: 0; }
    .kpi-val { font-size: 26px; font-weight: 800; color: var(--text); letter-spacing: -0.5px; line-height: 1.1; }
    .kpi-title { font-size: 11px; color: var(--muted); font-weight: 700; text-transform: uppercase; margin-top: 4px; letter-spacing: 0.5px; }
    
    /* =========================================================
       GRÁFICO CONTAINER
       ========================================================= */
    .chart-container { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 15px 15px 5px 15px; margin-bottom: 20px; box-shadow: var(--shadow); }
    .chart-title { font-size: 14px; font-weight: 800; color: var(--text); margin-bottom: -10px; text-transform: uppercase; letter-spacing: 0.5px; }

    /* =========================================================
       TABELA DRE CORPORATIVA
       ========================================================= */
    .dre-container { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; box-shadow: var(--shadow); font-size: 11px; overflow-x: auto; margin-bottom: 30px;}
    
    .dre-row { display: grid; border-bottom: 1px solid var(--border); align-items: center; transition: background 0.2s; }
    .dre-row:hover { background-color: var(--surface-soft); }
    
    .dre-col-name { padding: 10px 12px; font-weight: 600; color: var(--text); white-space: nowrap; }
    .dre-col-val { padding: 10px 6px; text-align: right; font-variant-numeric: tabular-nums; color: var(--text-secondary); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    
    /* Cabeçalhos */
    .dre-header { background: #edf1f5; font-weight: 800; color: var(--primary-dark); }
    .dre-subheader { background: var(--surface); border-bottom: 2px solid var(--border-strong); }
    .dre-subheader .dre-col-name { color: var(--muted); font-weight: 800; text-transform: uppercase; font-size: 10px; }
    .dre-subheader .dre-col-val { color: var(--primary); font-size: 10px; text-transform: uppercase; font-weight: 800; }
    .border-left { border-left: 1px solid var(--border); }
    
    /* Hierarquia */
    .lvl-macro { background-color: #f8fafc; font-size: 12px; border-top: 1px solid var(--border-strong); }
    .lvl-macro .dre-col-name { font-weight: 850; color: var(--primary-dark); text-transform: uppercase; }
    .lvl-macro .dre-col-val { font-weight: 850; color: var(--text); }
    
    .lvl-grupo .dre-col-name { padding-left: 12px; color: var(--text); font-weight: 700; }
    .lvl-subgrupo .dre-col-name { padding-left: 30px; color: var(--text-secondary); font-size: 10px; font-weight: 600; }
    .lvl-item .dre-col-name { padding-left: 45px; color: var(--muted); font-size: 10px; font-weight: 500; }
    .lvl-item .dre-col-val { font-weight: 500; color: var(--muted); }
    
    /* Expansão com Details/Summary */
    details { width: 100%; display: block; }
    details summary { list-style: none; cursor: pointer; outline: none; }
    details summary::-webkit-details-marker { display: none; }
    
    /* Ícones de [+] e [-] */
    .icon-expand { font-family: monospace; font-weight: 800; color: var(--primary); margin-right: 6px; font-size: 13px; }
    details:not([open]) > summary .icon-expand::before { content: "[+]"; }
    details[open] > summary .icon-expand::before { content: "[-]"; }
    
    /* Cores Setas */
    .txt-up { color: var(--success) !important; font-weight: 700; }
    .txt-down { color: var(--danger) !important; font-weight: 700; }
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
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_kpi(valor):
    if pd.isna(valor): return "0"
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_pct(valor):
    if pd.isna(valor) or valor == 0: return "0%"
    return f"{valor:.0f}%"

# ==============================================================================
# 2. MAPEAMENTO HIERÁRQUICO DA DRE
# ==============================================================================
def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    
    # ENTRADAS
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "POSTAL", "CASACARESC", "CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "SEGURADORAS", "CAPESAUDE", "SIM SAÚDE", "EMBRATEL", "SAUDES", "CONAB"]
    if any(c in conta for c in convênios): return "RECEITA OPERACIONAL", "Receitas Convênios", conta
    particulares = ["CARTÃO", "DINHEIRO", "PARTICULAR", "DEVOLUÇÃO"]
    if any(c in conta for c in particulares): return "RECEITA OPERACIONAL", "Receitas Particulares", conta
    outras_receitas = ["ALUGUÉIS", "UNIVERSIDADE", "OUTRAS RECEITAS"]
    if any(c in conta for c in outras_receitas): return "RECEITA OPERACIONAL", "Outras Receitas Operacionais", conta

    # SAÍDAS
    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "FÉRIAS", "INSS", "FGTS"]): return "(-) DESPESAS FIXAS", "Despesas Pessoal", conta
    if any(c in conta for c in ["HONORÁRIOS MÉDICOS", "MÉDICO"]): return "(-) CUSTOS VARIÁVEIS", "Honorários Médicos", conta
    if any(c in conta for c in ["FORNECEDORES", "CUSTO", "MEDICAMENTOS", "OPME", "ESTOQUE"]): return "(-) CUSTOS VARIÁVEIS", "Fornecedores Assistenciais", conta
    if any(c in conta for c in ["IMPOSTOS", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): return "(-) DEDUÇÕES SOBRE VENDAS", "Impostos Correntes", conta
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "ÁGUA", "INTERNET", "CONTABILIDADE"]): return "(-) DESPESAS FIXAS", "Despesas Administrativas", conta
    
    if any(c in conta for c in ["APLICAÇÕES", "RENDIMENTO", "RESGATE"]): return "(+) RECEITAS FINANCEIRAS", "Rendimentos e Aplicações", conta
    if any(c in conta for c in ["JUROS", "TARIFAS", "IOF", "TAXA", "PMT", "PARCELAMENTO"]): return "(-) DESPESAS FINANCEIRAS", "Financeiro e Empréstimos", conta
    
    return "(=) OUTRAS DESPESAS E RECEITAS", "Outras Movimentações", conta

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
    st.markdown("### Configurações")
    meses_disponiveis = sorted(df_base['Mês_Ano'].unique())
    mes_padrao_ini = meses_disponiveis[0] if len(meses_disponiveis) <= 8 else meses_disponiveis[-8]
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
# 4. MOTOR MATEMÁTICO (DRE STRUCTURE)
# ==============================================================================
def buscar_soma(grupo=None, subgrupo=None, conta=None):
    df_temp = df_filtro.copy()
    if grupo: df_temp = df_temp[df_temp['Grupo'] == grupo]
    if subgrupo: df_temp = df_temp[df_temp['Subgrupo'] == subgrupo]
    if conta: df_temp = df_temp[df_temp['Conta'] == conta]
    somas = df_temp.groupby('Mês_Ano')['Valor Líquido'].sum()
    return {str(m): somas.get(m, 0.0) for m in meses_filtrados}

# Blocos
rec_op = buscar_soma(grupo="RECEITA OPERACIONAL")
deducoes = buscar_soma(grupo="(-) DEDUÇÕES SOBRE VENDAS")
rec_liq = {m: rec_op.get(m,0) + deducoes.get(m,0) for m in meses_str}

custos_var = buscar_soma(grupo="(-) CUSTOS VARIÁVEIS")
margem_contrib = {m: rec_liq.get(m,0) + custos_var.get(m,0) for m in meses_str}

desp_fixas = buscar_soma(grupo="(-) DESPESAS FIXAS")
lucro_operacional = {m: margem_contrib.get(m,0) + desp_fixas.get(m,0) for m in meses_str}

# ==============================================================================
# 5. KPIs SUPERIORES
# ==============================================================================
mes_atual = meses_str[-1]
val_rec = rec_op.get(mes_atual, 0)
val_cv = abs(custos_var.get(mes_atual, 0))
val_df = abs(desp_fixas.get(mes_atual, 0))
val_lucro = lucro_operacional.get(mes_atual, 0)
pct_lucro = (val_lucro / val_rec * 100) if val_rec != 0 else 0

st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-box">
        <div class="kpi-val">{formata_kpi(val_rec)}</div>
        <div class="kpi-title">Receita operacional</div>
    </div>
    <div class="kpi-box">
        <div class="kpi-val" style="color:var(--danger);">{formata_kpi(val_cv)}</div>
        <div class="kpi-title">Custos Variáveis</div>
    </div>
    <div class="kpi-box">
        <div class="kpi-val" style="color:var(--danger);">{formata_kpi(val_df)}</div>
        <div class="kpi-title">Despesas fixas</div>
    </div>
    <div class="kpi-box">
        <div class="kpi-val" style="color:var(--primary);">{formata_kpi(val_lucro)}</div>
        <div class="kpi-title">Lucro operacional</div>
    </div>
    <div class="kpi-box">
        <div class="kpi-val" style="color:var(--primary);">{formata_pct(pct_lucro)}</div>
        <div class="kpi-title">% do lucro</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 6. GRÁFICO CASCATA (WATERFALL) SUTIL
# ==============================================================================
x_grafico = [pd.Period(m).strftime('%b').capitalize() for m in meses_str] + ["Total"]
y_grafico = [lucro_operacional.get(m, 0) for m in meses_str] + [0]
medidas = ["relative"] * len(meses_str) + ["total"]

textos_grafico = [formata_num(v) for v in y_grafico[:-1]] + [formata_num(sum(y_grafico[:-1]))]

# Calcula a largura das barras baseado em quantos meses tem (evita barras gigantes se tiver 1 mês)
width_bar = 0.4 if len(meses_str) <= 3 else None

fig_waterfall = go.Figure(go.Waterfall(
    orientation="v",
    measure=medidas,
    x=x_grafico,
    textposition="outside",
    text=textos_grafico,
    textfont=dict(color="#44515f", size=10, weight="bold"),
    y=y_grafico,
    width=width_bar,
    connector={"line": {"color": "#cbd3dc", "width": 1, "dash": "dot"}},
    increasing={"marker": {"color": "#157a5b"}},
    decreasing={"marker": {"color": "#b74242"}},
    totals={"marker": {"color": "#234a78"}}
))

fig_waterfall.update_layout(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(showgrid=False, tickfont=dict(color='#6b7785', weight='bold')),
    yaxis=dict(showgrid=True, gridcolor='#edf0f3', showticklabels=False, zeroline=True, zerolinecolor='#cbd3dc'),
    margin=dict(t=10, b=20, l=10, r=10),
    height=240,
    bargap=0.3
)

st.markdown("<div class='chart-container'><div class='chart-title'>Evolução do Lucro Operacional</div>", unsafe_allow_html=True)
st.plotly_chart(fig_waterfall, use_container_width=True, config={'displayModeBar': False})
st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 7. TABELA DRE HTML5 (ACORDEÃO E COLUNAS AV/AH - AJUSTE DE LARGURAS)
# ==============================================================================
# Ajustamos o minmax para garantir que as colunas da DRE tenham espaço suficiente para os números e não quebrem
grid_template = f"minmax(250px, 1.5fr) repeat({len(meses_str)}, minmax(85px, 1fr) 50px 55px)"

def render_linha(nome, classe, valores, icone=""):
    html = f"<div class='dre-row {classe}' style='grid-template-columns: {grid_template};'>"
    html += f"<div class='dre-col-name'>{icone}{nome}</div>"
    
    for i, m in enumerate(meses_str):
        val = valores.get(m, 0)
        
        # Base de cálculo para Análise Vertical (AV)
        base_av = rec_op.get(m, 1)
        base_av = base_av if base_av != 0 else 1
        av = (val / base_av) * 100
        
        # Análise Horizontal (AH)
        ah = 0
        if i > 0:
            val_ant = valores.get(meses_str[i-1], 0)
            if val_ant != 0: ah = ((val / val_ant) - 1) * 100
            
        # Cor AH (Seta e Classe)
        seta = ""
        cor_ah = ""
        if ah > 0:
            seta = "↗"
            cor_ah = "txt-up" if "DESPESA" not in nome and "CUSTO" not in nome and "DEDUÇÕES" not in nome else "txt-down"
        elif ah < 0:
            seta = "↘"
            cor_ah = "txt-down" if "DESPESA" not in nome and "CUSTO" not in nome and "DEDUÇÕES" not in nome else "txt-up"
            
        html += f"<div class='dre-col-val border-left' style='color:var(--text);'>{formata_num(val)}</div>"
        html += f"<div class='dre-col-val' style='color:var(--muted); font-size:10px;'>{formata_pct(av)}</div>"
        
        if i == 0 or classe == 'lvl-macro': # Esconde seta no primeiro mês e na linha totalizadora Macro
            html += f"<div class='dre-col-val'>-</div>"
        else:
            html += f"<div class='dre-col-val {cor_ah}' style='font-size:10px;'><span style='margin-right:2px;'>{seta}</span>{formata_pct(abs(ah))}</div>"
            
    html += "</div>"
    return html

def render_bloco(nome_grupo, dict_valores, func_soma):
    if all(v == 0 for v in dict_valores.values()): return ""
    
    block = "<details><summary>" + render_linha(nome_grupo, "lvl-grupo", dict_valores, "<span class='icon-expand'></span>") + "</summary>"
    
    df_g = df_filtro[df_filtro['Grupo'] == nome_grupo]
    for subg in sorted(df_g['Subgrupo'].unique()):
        somas_sub = func_soma(grupo=nome_grupo, subgrupo=subg)
        if any(v != 0 for v in somas_sub.values()):
            
            block += "<details><summary>" + render_linha(f"{subg}", "lvl-subgrupo", somas_sub, "<span class='icon-expand'></span>") + "</summary>"
            
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

# Header Mês
html_dre += f"<div class='dre-row dre-header' style='grid-template-columns: {grid_template};'>"
html_dre += "<div class='dre-col-name' style='text-align:center;'>Mês / Ano</div>"
for m in meses_str:
    html_dre += f"<div class='dre-col-val border-left' style='grid-column: span 3; text-align:center; font-weight:800; color:var(--primary-dark);'>{pd.Period(m).strftime('%b/%Y').capitalize()}</div>"
html_dre += "</div>"

# Header Colunas
html_dre += f"<div class='dre-row dre-subheader' style='grid-template-columns: {grid_template};'>"
html_dre += "<div class='dre-col-name'>Conta Superior</div>"
for m in meses_str:
    html_dre += "<div class='dre-col-val border-left' style='text-align:center;'>DRE</div><div class='dre-col-val' style='text-align:center;'>% AV</div><div class='dre-col-val' style='text-align:center;'>AH</div>"
html_dre += "</div>"

# Anexando os blocos
html_dre += render_bloco("RECEITA OPERACIONAL", rec_op, buscar_soma)
html_dre += render_bloco("(-) DEDUÇÕES SOBRE VENDAS", deducoes, buscar_soma)
html_dre += render_linha("(=) RECEITA LÍQUIDA", "lvl-macro", rec_liq)

html_dre += render_bloco("(-) CUSTOS VARIÁVEIS", custos_var, buscar_soma)
html_dre += render_linha("(=) MARGEM DE CONTRIBUIÇÃO", "lvl-macro", margem_contrib)

html_dre += render_bloco("(-) DESPESAS FIXAS", desp_fixas, buscar_soma)
html_dre += render_linha("(=) LUCRO OPERACIONAL", "lvl-macro", lucro_operacional)

html_dre += "</div>"

st.markdown(html_dre, unsafe_allow_html=True)
