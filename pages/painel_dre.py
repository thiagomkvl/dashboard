import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE Gerencial Executivo", layout="wide", page_icon="📈")

# ==============================================================================
# CUSTOM CSS — IDENTIDADE EXECUTIVA
# ==============================================================================
# Nota: O CSS está compactado à esquerda para evitar que o Streamlit o leia como bloco de código
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f2f5f9;
    --surface: #ffffff;
    --primary-dark: #002b66;
    --primary: #2970d4;
    --success: #02b05c;
    --danger: #fc4e51;
    --text-main: #1a2332;
    --text-muted: #6b7785;
    --border: #d2dbe3;
    --shadow: 0 4px 10px rgba(0, 43, 102, 0.05);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 1.5rem; }
header[data-testid="stHeader"] { display: none !important; }

/* CABEÇALHO AZUL MARINHO */
.top-header { background: var(--primary-dark); color: #fff; padding: 12px 25px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.top-header .title-box h1 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 0.5px; }
.top-header .title-box p { margin: 0; font-size: 11px; font-weight: 400; color: #a4c2f4; letter-spacing: 0.5px; }
.top-header .filters { display: flex; gap: 20px; align-items: center; }
.filter-item { display: flex; flex-direction: column; }
.filter-item label { font-size: 9px; font-weight: 600; color: #a4c2f4; margin-bottom: 2px; }
.filter-item .val { background: #fff; color: var(--primary-dark); padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; min-width: 100px; display: flex; justify-content: space-between; }
.update-badge { background: rgba(255,255,255,0.1); padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; gap: 8px; border: 1px solid rgba(255,255,255,0.2); }
.update-badge div { display: flex; flex-direction: column; }
.update-badge span { font-size: 8px; color: #a4c2f4; text-transform: uppercase;}
.update-badge b { font-size: 11px; font-weight: 700; }

/* KPI CARDS */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 20px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; position: relative; box-shadow: var(--shadow); display: flex; flex-direction: column; justify-content: center; }
.kpi-card::after { content: ""; position: absolute; bottom: 12px; left: 20px; right: 20px; height: 5px; border-radius: 3px; }
.kpi-card.c-blue::after { background: var(--primary); }
.kpi-card.c-green::after { background: var(--success); }
.kpi-content { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.kpi-icon { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.kpi-card.c-blue .kpi-icon { background: #e8f0fe; color: var(--primary); }
.kpi-card.c-green .kpi-icon { background: #e6f6ee; color: var(--success); }
.kpi-text { flex: 1; }
.kpi-title { font-size: 11px; font-weight: 700; color: var(--primary-dark); text-transform: uppercase; margin-bottom: 2px; }
.kpi-val { font-size: 22px; font-weight: 800; color: var(--text-main); letter-spacing: -0.5px; line-height: 1.1; }
.kpi-meta { font-size: 10px; color: var(--text-muted); margin-bottom: 2px; }
.kpi-var { font-size: 11px; font-weight: 700; }
.var-up { color: var(--success); }
.var-down { color: var(--danger); }

/* GRÁFICOS CONTAINERS */
.chart-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 15px 15px 5px 15px; box-shadow: var(--shadow); height: 100%; }
.chart-title { font-size: 15px; font-weight: 800; color: var(--primary-dark); margin-bottom: 2px; }
.chart-subtitle { font-size: 11px; color: var(--primary); font-weight: 500; margin-bottom: 15px; }

/* TABELAS E ANÁLISE GERENCIAL */
.bottom-grid { display: grid; grid-template-columns: 2.5fr 1fr; gap: 15px; margin-top: 20px; }
.table-container { background: var(--surface); border: 1px solid var(--primary-dark); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); }
.table-header { background: var(--primary-dark); color: #fff; padding: 10px 15px; display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 700; }
.dre-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.dre-table th { background: var(--primary); color: #fff; font-weight: 600; text-align: right; padding: 8px 10px; border-left: 1px solid rgba(255,255,255,0.2); }
.dre-table th:first-child { text-align: left; border-left: none; }
.dre-table td { padding: 8px 10px; text-align: right; border-bottom: 1px solid var(--border); font-weight: 600; color: var(--text-main); }
.dre-table td:first-child { text-align: left; }
.dre-table tr:nth-child(even) td { background-color: #f8fafc; }
.row-highlight td { font-weight: 800; background-color: #eef2f6 !important; color: var(--primary-dark); }

/* Box Análise Gerencial */
.insights-container { background: var(--surface); border: 1px solid var(--primary-dark); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); }
.insight-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px 15px; border-bottom: 1px solid var(--border); }
.insight-item:last-child { border-bottom: none; }
.insight-icon { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; font-weight:bold; }
.i-green { background: #e6f6ee; color: var(--success); }
.i-blue { background: #e8f0fe; color: var(--primary); }
.insight-text h4 { margin: 0 0 2px 0; font-size: 11px; font-weight: 700; color: var(--primary-dark); }
.insight-text p { margin: 0; font-size: 10px; color: var(--text-muted); line-height: 1.3; }
</style>
""", unsafe_allow_html=True)

# Função para garantir que o HTML seja injetado limpo sem quebrar no Streamlit
def injetar_html(codigo_html):
    st.markdown(codigo_html.replace('\n', ''), unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÕES UTILITÁRIAS
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
    return f"{valor:.1f}%".replace('.', ',')

def calc_var(atual, anterior):
    if anterior == 0: return 0
    return ((atual - anterior) / abs(anterior)) * 100

# ==============================================================================
# 2. MAPEAMENTO DRE CLÁSSICA
# ==============================================================================
def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "CASACARESC", "CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "CAPESAUDE", "SIM SAÚDE"]
    if any(c in conta for c in convênios) or "PARTICULAR" in conta or "CARTÃO" in conta: 
        return "Receita Bruta", "Receitas Operacionais", conta

    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "INSS", "HONORÁRIOS", "MÉDICO", "FORNECEDORES", "CUSTO", "MEDICAMENTOS", "OPME"]): 
        return "CPV / CSP", "Custos Variáveis e Serviços", conta
        
    if any(c in conta for c in ["IMPOSTOS", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): 
        return "Deduções", "Impostos Correntes", conta
        
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "INTERNET", "CONTABILIDADE"]): 
        return "OPEX", "Despesas Operacionais Fixas", conta
    
    if any(c in conta for c in ["JUROS", "TARIFAS", "PMT", "FINANCEIRAS", "APLICAÇÕES", "RENDIMENTO", "RESGATE", "OBRAS"]): 
        return "Depreciação e Outros", "Movimentações Financeiras", conta
    
    return "Depreciação e Outros", "Outros", conta

# ==============================================================================
# 3. CARGA DE DADOS
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

        df['Macro'], df['Subgrupo'], df['Conta'] = zip(*df[col_conta].apply(classificar_conta))
        return df[df['Data'].notna()]
    except Exception as e:
        st.error(f"Erro ao gerar DRE: {e}")
        return pd.DataFrame()

df_base = preparar_dados_dre()
if df_base.empty: st.stop()

meses_disponiveis = sorted(df_base['Mês_Ano'].unique())
mes_atual = meses_disponiveis[-1]
mes_anterior = meses_disponiveis[-2] if len(meses_disponiveis) > 1 else mes_atual

meses_str = [str(m) for m in meses_disponiveis]

def get_val(macro, mes):
    return df_base[(df_base['Macro'] == macro) & (df_base['Mês_Ano'] == mes)]['Valor Líquido'].sum()

# ==============================================================================
# 4. MOTOR DRE (MÊS ATUAL E ANTERIOR)
# ==============================================================================
rec_bruta = get_val("Receita Bruta", mes_atual)
deducoes = get_val("Deduções", mes_atual)
rec_liq = rec_bruta + deducoes
cpv = get_val("CPV / CSP", mes_atual)
lucro_bruto = rec_liq + cpv
opex = get_val("OPEX", mes_atual)
ebitda = lucro_bruto + opex
outros = get_val("Depreciação e Outros", mes_atual)
lucro_liq = ebitda + outros

ant_rec_bruta = get_val("Receita Bruta", mes_anterior)
ant_deducoes = get_val("Deduções", mes_anterior)
ant_rec_liq = ant_rec_bruta + ant_deducoes
ant_cpv = get_val("CPV / CSP", mes_anterior)
ant_lucro_bruto = ant_rec_liq + ant_cpv
ant_opex = get_val("OPEX", mes_anterior)
ant_ebitda = ant_lucro_bruto + ant_opex
ant_outros = get_val("Depreciação e Outros", mes_anterior)
ant_lucro_liq = ant_ebitda + ant_outros

mg_bruta = (lucro_bruto / rec_bruta * 100) if rec_bruta else 0
mg_ebitda = (ebitda / rec_bruta * 100) if rec_bruta else 0
ant_mg_bruta = (ant_lucro_bruto / ant_rec_bruta * 100) if ant_rec_bruta else 0
ant_mg_ebitda = (ant_ebitda / ant_rec_bruta * 100) if ant_rec_bruta else 0

# ==============================================================================
# 5. CABEÇALHO
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
nome_mes_atual = pd.Period(mes_atual).strftime('%B/%Y').capitalize()

header_html = f"""<div class='top-header'>
<div class='title-box'><h1>DRE GERENCIAL EXECUTIVO</h1><p>Análise de Resultados • Performance • Tomada de Decisão</p></div>
<div class='filters'>
<div class='filter-item'><label>Período</label><div class='val'>{nome_mes_atual} <span>▼</span></div></div>
<div class='filter-item'><label>Unidade</label><div class='val'>Todas <span>▼</span></div></div>
<div class='filter-item'><label>Centro de Custo</label><div class='val'>Todos <span>▼</span></div></div>
<div class='update-badge'><span style='font-size:16px;'>📅</span><div><span>Última Atualização</span><b>{data_hoje}</b></div></div>
</div></div>"""

injetar_html(header_html)

# ==============================================================================
# 6. KPI CARDS
# ==============================================================================
def var_html(atual, ant, is_margin=False):
    val = (atual - ant) if is_margin else calc_var(abs(atual), abs(ant))
    cor = "var-up" if val >= 0 else "var-down"
    seta = "▲" if val >= 0 else "▼"
    sufixo = " p.p." if is_margin else "%"
    return f"<div class='kpi-var {cor}'>{seta} {abs(val):.1f}{sufixo} vs. Mês Ant.</div>"

kpis_html = f"""<div class='kpi-row'>
<div class='kpi-card c-blue'><div class='kpi-content'><div class='kpi-icon'>💰</div><div class='kpi-text'><div class='kpi-title'>Receita Bruta</div><div class='kpi-val'>R$ {formata_kpi(rec_bruta)}</div></div></div><div class='kpi-meta'>Mês Ant.: R$ {formata_kpi(ant_rec_bruta)}</div>{var_html(rec_bruta, ant_rec_bruta)}</div>
<div class='kpi-card c-green'><div class='kpi-content'><div class='kpi-icon'>%</div><div class='kpi-text'><div class='kpi-title'>Margem Bruta</div><div class='kpi-val'>{formata_pct(mg_bruta)}</div></div></div><div class='kpi-meta'>Mês Ant.: {formata_pct(ant_mg_bruta)}</div>{var_html(mg_bruta, ant_mg_bruta, True)}</div>
<div class='kpi-card c-green'><div class='kpi-content'><div class='kpi-icon'>📊</div><div class='kpi-text'><div class='kpi-title'>EBITDA</div><div class='kpi-val'>R$ {formata_kpi(ebitda)}</div></div></div><div class='kpi-meta'>Mês Ant.: R$ {formata_kpi(ant_ebitda)}</div>{var_html(ebitda, ant_ebitda)}</div>
<div class='kpi-card c-green'><div class='kpi-content'><div class='kpi-icon'>📈</div><div class='kpi-text'><div class='kpi-title'>Margem EBITDA</div><div class='kpi-val'>{formata_pct(mg_ebitda)}</div></div></div><div class='kpi-meta'>Mês Ant.: {formata_pct(ant_mg_ebitda)}</div>{var_html(mg_ebitda, ant_mg_ebitda, True)}</div>
<div class='kpi-card c-blue'><div class='kpi-content'><div class='kpi-icon'>$</div><div class='kpi-text'><div class='kpi-title'>Lucro Líquido</div><div class='kpi-val'>R$ {formata_kpi(lucro_liq)}</div></div></div><div class='kpi-meta'>Mês Ant.: R$ {formata_kpi(ant_lucro_liq)}</div>{var_html(lucro_liq, ant_lucro_liq)}</div>
</div>"""

injetar_html(kpis_html)

# ==============================================================================
# 7. GRÁFICOS
# ==============================================================================
col_g1, col_g2 = st.columns([1.7, 1])

with col_g1:
    injetar_html("<div class='chart-box'><div class='chart-title'>Decomposição do Resultado</div><div class='chart-subtitle'>Como a Receita Bruta se transforma em Lucro Líquido</div>")
    
    x_water = ["Receita Bruta", "Deduções", "Receita Líquida", "CPV / CSP", "Lucro Bruto", "OPEX", "EBITDA", "Depreciação/Outros", "Lucro Líquido"]
    y_water = [rec_bruta, deducoes, rec_liq, cpv, lucro_bruto, opex, ebitda, outros, lucro_liq]
    medidas = ["relative", "relative", "total", "relative", "total", "relative", "total", "relative", "total"]
    
    textos = [f"R$ {formata_num(v)}" if v >= 0 else f"-R$ {formata_num(abs(v))}" for v in y_water]

    fig_w = go.Figure(go.Waterfall(
        x=x_water, y=y_water, measure=medidas, text=textos, textposition="outside",
        textfont=dict(color="#002b66", size=11, weight="bold"),
        connector={"line": {"color": "rgba(0,0,0,0.1)", "width": 1}},
        increasing={"marker": {"color": "#002b66"}},
        decreasing={"marker": {"color": "#ff4d4d"}},
        totals={"marker": {"color": "#002b66"}}
    ))
    fig_w.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#1a2332", weight="bold")), yaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont=dict(size=10)), margin=dict(t=20, b=10, l=10, r=10), height=300)
    st.plotly_chart(fig_w, use_container_width=True, config={'displayModeBar': False})
    injetar_html("</div>")

with col_g2:
    injetar_html("<div class='chart-box'><div class='chart-title'>Tendência Mensal</div><div class='chart-subtitle'>Evolução dos Principais Indicadores</div>")
    
    hist_meses = [pd.Period(m).strftime('%b').capitalize() for m in meses_str[-6:]]
    hist_rec = [get_val("Receita Bruta", m) for m in meses_str[-6:]]
    hist_ebitda = [get_val("Receita Bruta", m) + get_val("Deduções", m) + get_val("CPV / CSP", m) + get_val("OPEX", m) for m in meses_str[-6:]]
    hist_mg = [(e/r*100) if r!=0 else 0 for e, r in zip(hist_ebitda, hist_rec)]

    fig_c = make_subplots(specs=[[{"secondary_y": True}]])
    fig_c.add_trace(go.Bar(x=hist_meses, y=hist_rec, name="Receita Bruta", marker_color="#002b66"), secondary_y=False)
    fig_c.add_trace(go.Bar(x=hist_meses, y=hist_ebitda, name="EBITDA", marker_color="#70a1ff"), secondary_y=False)
    fig_c.add_trace(go.Scatter(x=hist_meses, y=hist_mg, name="Margem EBITDA (%)", mode="lines+markers", line=dict(color="#fc4e51", width=3)), secondary_y=True)
    
    fig_c.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e2e8f0", showticklabels=False), yaxis2=dict(showgrid=False, showticklabels=False), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=9)), margin=dict(t=20, b=10, l=0, r=0), height=300, barmode='group')
    st.plotly_chart(fig_c, use_container_width=True, config={'displayModeBar': False})
    injetar_html("</div>")

# ==============================================================================
# 8. MATRIZ DRE & ANÁLISE GERENCIAL
# ==============================================================================
injetar_html("<div class='bottom-grid'>")

# TABELA DRE
html_tabela = f"""<div class='table-container'><div class='table-header'><span>🧮</span> Matriz DRE Gerencial</div><table class='dre-table'><thead><tr><th>Descrição</th><th style='text-align:center;'>Realizado<br>{nome_mes_atual}<br>(R$)</th><th style='text-align:center;'>Realizado<br>{pd.Period(mes_anterior).strftime('%B/%Y').capitalize()}<br>(R$)</th><th style='text-align:center;'>Var. %<br>(MoM)</th><th style='text-align:center;'>AV %<br>(Receita Líq.)</th></tr></thead><tbody>"""

linhas_dre = [
    ("Receita Bruta", rec_bruta, ant_rec_bruta, False),
    ("Deduções da Receita", deducoes, ant_deducoes, False),
    ("Receita Líquida", rec_liq, ant_rec_liq, True),
    ("Custo dos Serviços (CPV/CSP)", cpv, ant_cpv, False),
    ("Lucro Bruto", lucro_bruto, ant_lucro_bruto, True),
    ("Despesas Operacionais (OPEX)", opex, ant_opex, False),
    ("EBITDA", ebitda, ant_ebitda, True),
    ("Depreciação e Amortização", outros, ant_outros, False),
    ("Lucro Líquido", lucro_liq, ant_lucro_liq, True)
]

base_av = rec_liq if rec_liq != 0 else 1

for nome, val_at, val_ant, destaque in linhas_dre:
    # Usando o valor absoluto para a variação percentual para que aumento de despesa apareça como % positivo vermelho
    var_pct = calc_var(abs(val_at), abs(val_ant))
    av_pct = (val_at / base_av) * 100
    
    cor_var = "color: #02b05c;" if var_pct > 0 else "color: #fc4e51;"
    if "Custo" in nome or "Deduções" in nome or "Despesas" in nome or "Depreciação" in nome:
        cor_var = "color: #fc4e51;" if var_pct > 0 else "color: #02b05c;"
        
    sinal = "+" if var_pct > 0 else ""
    classe = "row-highlight" if destaque else ""
    val_at_str = f"({formata_num(abs(val_at))})" if val_at < 0 else formata_num(val_at)
    val_ant_str = f"({formata_num(abs(val_ant))})" if val_ant < 0 else formata_num(val_ant)
    
    html_tabela += f"<tr class='{classe}'><td>{nome}</td><td style='text-align:center;'>{val_at_str}</td><td style='text-align:center;'>{val_ant_str}</td><td style='text-align:center; font-weight:800; {cor_var}'>{sinal}{var_pct:.1f}%</td><td style='text-align:center;'>{av_pct:.1f}%</td></tr>"

html_tabela += "</tbody></table></div>"
injetar_html(html_tabela)

# ANÁLISE GERENCIAL
txt_rec = "acima" if rec_bruta > ant_rec_bruta else "abaixo"
txt_lucro = "em destaque" if lucro_liq > ant_lucro_liq else "em atenção"

html_insights = f"""<div class='insights-container'><div class='table-header'><span>🎯</span> Análise Gerencial</div>
<div class='insight-item'><div class='insight-icon i-green'>📈</div><div class='insight-text'><h4>Receita Bruta {txt_rec} do mês anterior</h4><p>Variação de {calc_var(rec_bruta, ant_rec_bruta):.1f}% vs. mês anterior, indicando o ritmo de crescimento sustentável das operações.</p></div></div>
<div class='insight-item'><div class='insight-icon i-green'>%</div><div class='insight-text'><h4>Margens Operacionais</h4><p>A Margem EBITDA fechou em {mg_ebitda:.1f}%, refletindo a eficiência da operação perante os custos variáveis e despesas fixas.</p></div></div>
<div class='insight-item'><div class='insight-icon i-green'>$</div><div class='insight-text'><h4>Lucro Líquido {txt_lucro}</h4><p>Resultado de R$ {formata_kpi(lucro_liq)} no período, com variação de {calc_var(lucro_liq, ant_lucro_liq):.1f}% vs. último mês.</p></div></div>
<div class='insight-item'><div class='insight-icon i-blue'>🔍</div><div class='insight-text'><h4>Foco para o próximo período</h4><p>Manter disciplina de custos operacionais (OPEX) e seguir com a estratégia de otimização de serviços prestados.</p></div></div>
</div></div>"""

injetar_html(html_insights)
