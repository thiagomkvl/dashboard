import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE e Fluxo de Caixa Gerencial", layout="wide", page_icon="📈")

# ==============================================================================
# CUSTOM CSS — THEMA DARK GREEN (Baseado na imagem de referência)
# ==============================================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;600;700;800&display=swap');
    
    /* Configuração Global de Cores */
    :root {
        --bg-dark: #12382f; /* Verde escuro do fundo */
        --card-bg: rgba(0, 0, 0, 0.25);
        --text-light: #ffffff;
        --kpi-receita: #2ed16b; /* Verde neon */
        --kpi-despesa: #e94235; /* Vermelho */
        --kpi-ebitda: #2baddd; /* Azul claro */
        --border-color: rgba(255, 255, 255, 0.15);
    }
    
    /* Fundo da Aplicação */
    .stApp { background-color: var(--bg-dark); }
    html, body, [class*="css"] { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: var(--text-light); }
    .main .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 98%; }
    
    /* Esconder elementos padrões para dar visual de sistema fullscreen */
    header[data-testid="stHeader"] { display: none !important; }
    
    /* =========================================================
       KPI CARDS LATERAIS
       ========================================================= */
    .kpi-container { display: flex; flex-direction: column; gap: 18px; margin-top: 40px;}
    
    .kpi-box { border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); background: var(--card-bg); box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center; }
    
    .kpi-top { padding: 5px; font-weight: 700; font-size: 16px; color: #fff; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
    .kpi-top.receita { background-color: var(--kpi-receita); }
    .kpi-top.despesa { background-color: var(--kpi-despesa); }
    .kpi-top.ebitda { background-color: var(--kpi-ebitda); }
    
    .kpi-val { padding: 15px 10px; font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }
    
    /* =========================================================
       TABELA DRE ESTILO TERMINAL
       ========================================================= */
    .table-container { background: rgba(0,0,0,0.1); border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; margin-bottom: 20px; overflow-x: auto;}
    .table-title { text-align: center; font-size: 18px; font-weight: 700; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;}
    
    .dre-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .dre-table th { border-bottom: 1px solid var(--border-color); padding: 6px 8px; font-weight: 700; text-align: right; }
    .dre-table th:first-child { text-align: left; }
    
    .dre-table td { padding: 5px 8px; text-align: right; border-bottom: 1px solid rgba(255,255,255,0.05); font-variant-numeric: tabular-nums; }
    .dre-table td:first-child { text-align: left; }
    
    .dre-table tbody tr:hover td { background-color: rgba(255,255,255,0.05); }
    
    /* Níveis Hierárquicos */
    .lvl-macro td { font-weight: 700; color: #fff; }
    .lvl-grupo td { font-weight: 600; padding-left: 15px !important; }
    .lvl-subgrupo td { padding-left: 30px !important; }
    .lvl-item td { padding-left: 50px !important; font-size: 12px; opacity: 0.85; }
    
    /* Mágica do [+] e [-] com Details/Summary */
    details { margin: 0; padding: 0; display: contents; }
    details summary { list-style: none; cursor: pointer; display: table-row; outline: none; }
    details summary::-webkit-details-marker { display: none; }
    
    .expandable::before { content: '[+] '; font-family: monospace; font-weight: bold; margin-right: 5px; color: #fff; }
    details[open] > summary .expandable::before { content: '[-] '; }
    
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
    # Formata número padrão com separador de milhar (sem decimais para ficar limpo igual a foto)
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_kpi(valor):
    if pd.isna(valor): return "R$ 0"
    abs_val = abs(valor)
    prefix = "-" if valor < 0 else ""
    if abs_val >= 1_000_000:
        return f"{prefix}R$ {abs_val/1_000_000:.1f} Mi".replace('.', ',')
    elif abs_val >= 1_000:
        return f"{prefix}R$ {abs_val/1_000:.1f} Mil".replace('.', ',')
    else:
        return f"{prefix}R$ {abs_val:.0f}"

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
    if any(c in conta for c in convênios): return "FCO", "(+) RECEITAS OPERACIONAIS", "Receitas Convênios", conta
    
    particulares = ["CARTÃO", "DINHEIRO", "PARTICULAR", "DEVOLUÇÃO"]
    if any(c in conta for c in particulares): return "FCO", "(+) RECEITAS OPERACIONAIS", "Receitas Particulares", conta
    
    outras_receitas = ["ALUGUÉIS", "UNIVERSIDADE", "OUTRAS RECEITAS"]
    if any(c in conta for c in outras_receitas): return "FCO", "(+) RECEITAS OPERACIONAIS", "Outras Receitas Operacionais", conta

    # SAÍDAS
    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "FÉRIAS", "INSS", "FGTS"]): return "FCO", "(-) DESPESAS OPERACIONAIS", "Despesas Pessoal", conta
    if any(c in conta for c in ["HONORÁRIOS MÉDICOS", "MÉDICO"]): return "FCO", "(-) DESPESAS OPERACIONAIS", "Honorários Médicos", conta
    if any(c in conta for c in ["FORNECEDORES", "CUSTO", "MEDICAMENTOS", "OPME", "ESTOQUE"]): return "FCO", "(-) DESPESAS OPERACIONAIS", "Fornecedores Assistenciais", conta
    if any(c in conta for c in ["IMPOSTOS", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): return "FCO", "(-) DESPESAS OPERACIONAIS", "Impostos Correntes", conta
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "ÁGUA", "INTERNET", "CONTABILIDADE"]): return "FCO", "(-) DESPESAS OPERACIONAIS", "Despesas Administrativas", conta
    
    # INVESTIMENTOS E FINANCIAMENTOS
    if any(c in conta for c in ["OBRAS", "REFORMAS", "MÁQUINAS"]): return "FCI", "(-) DESPESAS DE INVESTIMENTO", "Obras e Reformas", conta
    if any(c in conta for c in ["APLICAÇÕES", "RENDIMENTO", "RESGATE"]): return "FCI", "(+) RECEITAS FINANCEIRAS / INVESTIMENTOS", "Rendimentos e Aplicações", conta
    if any(c in conta for c in ["CAPTAÇÕES", "EMPRÉSTIMO"]): return "FCF", "(+) CAPTAÇÕES", "Empréstimos", conta
    if any(c in conta for c in ["PMT", "PARCELAMENTO"]): return "FCF", "(-) DESPESAS FINANCEIRAS E AMORTIZAÇÕES", "Amortização de Dívidas", conta
    if any(c in conta for c in ["JUROS", "TARIFAS", "IOF", "TAXA"]): return "FCF", "(-) DESPESAS FINANCEIRAS E AMORTIZAÇÕES", "Juros e Tarifas", conta

    return "OUTROS", "(=) OUTRAS DESPESAS E RECEITAS", "Não Classificado", conta

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
    st.markdown("<h3 style='color:white;'>Filtros da DRE</h3>", unsafe_allow_html=True)
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

# Cálculos Totais
rec_op = buscar_soma(grupo="(+) RECEITAS OPERACIONAIS")
desp_op = buscar_soma(grupo="(-) DESPESAS OPERACIONAIS")
ebitda = {m: rec_op.get(m,0) + desp_op.get(m,0) for m in meses_str}

rec_fin = buscar_soma(grupo="(+) RECEITAS FINANCEIRAS / INVESTIMENTOS")
desp_fin = buscar_soma(grupo="(-) DESPESAS FINANCEIRAS E AMORTIZAÇÕES")
outros = buscar_soma(grupo="(=) OUTRAS DESPESAS E RECEITAS")

geracao_liquida = {m: ebitda.get(m,0) + rec_fin.get(m,0) + desp_fin.get(m,0) + outros.get(m,0) for m in meses_str}

# ==============================================================================
# 5. LAYOUT PRINCIPAL (COLUNA ESQUERDA KPIs | COLUNA DIREITA TABELA E GRÁFICOS)
# ==============================================================================
col_kpi, col_main = st.columns([1.5, 8.5])

# -------- COLUNA ESQUERDA (KPIs) --------
with col_kpi:
    mes_atual = meses_str[-1]
    
    val_receitas = rec_op.get(mes_atual, 0)
    val_despesas = desp_op.get(mes_atual, 0)
    val_ebitda = ebitda.get(mes_atual, 0)
    val_superavit = geracao_liquida.get(mes_atual, 0)
    val_margem = (val_superavit / val_receitas * 100) if val_receitas != 0 else 0

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-box">
            <div class="kpi-top receita">Receitas</div>
            <div class="kpi-val">{formata_kpi(val_receitas)}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-top despesa">Despesas</div>
            <div class="kpi-val" style="color:var(--kpi-despesa);">{formata_kpi(val_despesas)}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-top ebitda">EBITDA</div>
            <div class="kpi-val">{formata_kpi(val_ebitda)}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-top ebitda">Superávit/Déficit</div>
            <div class="kpi-val">{formata_kpi(val_superavit)}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-top ebitda">Margem Superávit</div>
            <div class="kpi-val">{formata_pct(val_margem)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------- COLUNA DIREITA (TABELA E GRÁFICOS) --------
with col_main:
    
    # ---------------- TABELA DRE ----------------
    html_table = f"""
    <div class="table-container">
        <div class="table-title">DEMONSTRATIVO DO RESULTADO</div>
        <table class="dre-table">
            <thead>
                <tr>
                    <th>Grupo</th>
    """
    for m in meses_str:
        html_table += f"<th>{pd.Period(m).strftime('%b/%Y').lower()}</th>"
    html_table += "</tr></thead><tbody>"

    def render_linha(nome, classe, valores, icon=""):
        row = f"<tr class='{classe}'><td>{icon}{nome}</td>"
        for m in meses_str:
            row += f"<td>{formata_num(valores.get(m,0))}</td>"
        row += "</tr>"
        return row

    # Função para renderizar blocos sanfona
    def render_bloco(nome_grupo, func_soma):
        somas_grupo = func_soma(grupo=nome_grupo)
        if all(v == 0 for v in somas_grupo.values()): return ""
        
        block = "<details><summary>" + render_linha(nome_grupo, "lvl-grupo", somas_grupo, "<span class='expandable'></span>") + "</summary>"
        
        # Pega subgrupos
        df_g = df_filtro[df_filtro['Grupo'] == nome_grupo]
        for subg in df_g['Subgrupo'].unique():
            somas_sub = func_soma(grupo=nome_grupo, subgrupo=subg)
            if any(v != 0 for v in somas_sub.values()):
                block += "<details><summary>" + render_linha(f"(+) {subg}" if "RECEITA" in nome_grupo else f"(-) {subg}", "lvl-subgrupo", somas_sub, "<span class='expandable'></span>") + "</summary>"
                
                # Pega contas
                df_s = df_g[df_g['Subgrupo'] == subg]
                for conta in sorted(df_s['Conta'].unique()):
                    somas_c = func_soma(grupo=nome_grupo, subgrupo=subg, conta=conta)
                    if any(v != 0 for v in somas_c.values()):
                        block += render_linha(conta, "lvl-item", somas_c)
                
                block += "</details>"
        block += "</details>"
        return block

    # Montagem das linhas na ordem correta
    html_table += render_bloco("(+) RECEITAS OPERACIONAIS", buscar_soma)
    html_table += render_bloco("(-) DESPESAS OPERACIONAIS", buscar_soma)
    html_table += render_linha("(=) RESULTADO OPERACIONAL (EBITDA)", "lvl-macro", ebitda)
    html_table += render_bloco("(+) RECEITAS FINANCEIRAS / INVESTIMENTOS", buscar_soma)
    html_table += render_bloco("(-) DESPESAS FINANCEIRAS E AMORTIZAÇÕES", buscar_soma)
    html_table += render_bloco("(=) OUTRAS DESPESAS E RECEITAS", buscar_soma)
    html_table += render_linha("(=) SUPERÁVIT / DÉFICIT LÍQUIDO", "lvl-macro", geracao_liquida)

    html_table += "</tbody></table></div>"
    st.markdown(html_table, unsafe_allow_html=True)

    # ---------------- GRÁFICOS ----------------
    c_graf1, c_graf2 = st.columns(2)
    
    # Preparar dados pros gráficos
    eixos_x = [pd.Period(m).strftime('%b/%Y').lower() for m in meses_str]
    y_superavit = [geracao_liquida.get(m, 0) for m in meses_str]
    y_margem = [(geracao_liquida.get(m,0)/rec_op.get(m,1))*100 if rec_op.get(m,0) != 0 else 0 for m in meses_str]
    cores_barra = ['#2ed16b' if v >= 0 else '#e94235' for v in y_superavit]
    
    # Grafico 1: Barras de Superávit
    fig1 = go.Figure(data=[
        go.Bar(
            x=eixos_x, y=y_superavit, 
            marker_color=cores_barra,
            text=[formata_kpi(v) for v in y_superavit],
            textposition='outside',
            textfont=dict(color='white')
        )
    ])
    fig1.update_layout(
        title=dict(text="Superávit/Déficit", font=dict(color='white', size=18), x=0.5),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, tickfont=dict(color='white')),
        yaxis=dict(showgrid=False, tickfont=dict(color='white'), zeroline=True, zerolinecolor='rgba(255,255,255,0.2)'),
        margin=dict(t=40, b=10, l=10, r=10),
        height=250
    )
    
    with c_graf1:
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

    # Grafico 2: Linha de Margem
    cores_texto_margem = ['#2ed16b' if v >= 0 else '#e94235' for v in y_margem]
    fig2 = go.Figure(data=[
        go.Scatter(
            x=eixos_x, y=y_margem, 
            mode='lines+markers+text',
            line=dict(color='#00d2ff', width=3),
            marker=dict(size=8, color='#00d2ff'),
            text=[formata_pct(v) for v in y_margem],
            textposition='top center',
            textfont=dict(color=cores_texto_margem, size=11)
        )
    ])
    fig2.update_layout(
        title=dict(text="Margem", font=dict(color='white', size=18), x=0.5),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, tickfont=dict(color='white')),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', tickfont=dict(color='white'), zeroline=True, zerolinecolor='rgba(255,255,255,0.2)'),
        margin=dict(t=40, b=10, l=10, r=10),
        height=250
    )

    with c_graf2:
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
