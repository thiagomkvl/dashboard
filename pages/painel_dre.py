import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE Gerencial Executivo", layout="wide", page_icon="📈")

# ==============================================================================
# 1. CUSTOM CSS — IDENTIDADE EXECUTIVA (SEM ESPAÇOS PARA NÃO QUEBRAR O STREAMLIT)
# ==============================================================================
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f4f6f9;
    --surface: #ffffff;
    --primary-dark: #002b66;
    --primary: #2970d4;
    --success: #02b05c;
    --danger: #fc4e51;
    --text-main: #1a2332;
    --text-muted: #6b7785;
    --border: #d2dbe3;
    --shadow: 0 4px 12px rgba(0, 43, 102, 0.08);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }

/* HEADER PRINCIPAL */
.exec-header { background: var(--primary-dark); color: #fff; padding: 15px 25px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: var(--shadow); }
.exec-header h1 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 0.5px; }
.exec-header p { margin: 0; font-size: 12px; font-weight: 400; color: #a4c2f4; }
.exec-filters { display: flex; gap: 20px; align-items: center; }
.exec-filter-item { display: flex; flex-direction: column; }
.exec-filter-item label { font-size: 10px; font-weight: 600; color: #a4c2f4; margin-bottom: 4px; }
.exec-filter-item .val { background: #fff; color: var(--primary-dark); padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; min-width: 120px; display: flex; justify-content: space-between; }
.exec-update { border-left: 1px solid rgba(255,255,255,0.2); padding-left: 20px; display: flex; align-items: center; gap: 10px; }
.exec-update span { font-size: 10px; color: #a4c2f4; display:block; }
.exec-update b { font-size: 12px; font-weight: 700; display:block;}

/* KPI CARDS */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 25px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px 22px 20px; position: relative; box-shadow: var(--shadow); }
.kpi-card::after { content: ""; position: absolute; bottom: 0; left: 20px; right: 20px; height: 5px; border-radius: 5px 5px 0 0; }
.kpi-card.c-blue::after { background: var(--primary); }
.kpi-card.c-green::after { background: var(--success); }
.kpi-card.c-red::after { background: var(--danger); }
.kpi-top { display: flex; gap: 15px; align-items: flex-start; margin-bottom: 12px;}
.kpi-icon { width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; font-weight: bold;}
.c-blue .kpi-icon { background: #e8f0fe; color: var(--primary); }
.c-green .kpi-icon { background: #e6f6ee; color: var(--success); }
.kpi-info { flex: 1; }
.kpi-title { font-size: 12px; font-weight: 800; color: var(--primary-dark); text-transform: uppercase; margin-bottom: 4px; }
.kpi-val { font-size: 26px; font-weight: 800; color: var(--text-main); letter-spacing: -0.5px; line-height: 1.1; }
.kpi-meta-box { border-top: 1px solid var(--border); padding-top: 10px; display: flex; justify-content: space-between; align-items: center; }
.kpi-meta-box span { font-size: 11px; color: var(--text-muted); font-weight: 600;}
.kpi-var { font-size: 12px; font-weight: 800; display:flex; align-items:center; gap:3px;}
.var-up { color: var(--success); }
.var-down { color: var(--danger); }

/* GRÁFICOS BOX */
.chart-box { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; box-shadow: var(--shadow); height: 100%; margin-bottom: 25px;}
.chart-title { font-size: 18px; font-weight: 800; color: var(--primary-dark); margin-bottom: 2px; }
.chart-subtitle { font-size: 12px; color: var(--primary); font-weight: 600; margin-bottom: 15px; }

/* MATRIZ DRE EXECUTIVA */
.matrix-container { background: var(--surface); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); border: 1px solid var(--border);}
.matrix-header { background: var(--primary-dark); color: #fff; padding: 12px 20px; font-size: 16px; font-weight: 800; display:flex; align-items:center; gap:8px;}
.dre-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.dre-table th { background: var(--primary); color: #fff; font-weight: 700; text-align: right; padding: 10px 15px; border-left: 1px solid rgba(255,255,255,0.2); }
.dre-table th:first-child { text-align: left; border-left: none; }
.dre-table td { padding: 10px 15px; text-align: right; border-bottom: 1px solid var(--border); font-weight: 600; color: var(--text-main); }
.dre-table td:first-child { text-align: left; }
.dre-table tr:nth-child(even) td { background-color: #f8fafc; }
.dre-table tr:hover td { background-color: #f1f5f9; }
.row-macro td { font-weight: 800 !important; background-color: #eef2f6 !important; color: var(--primary-dark) !important; font-size: 13px;}

/* ANÁLISE GERENCIAL */
.insight-box { background: var(--surface); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); border: 1px solid var(--border);}
.insight-header { background: var(--primary-dark); color: #fff; padding: 12px 20px; font-size: 16px; font-weight: 800; display:flex; align-items:center; gap:8px;}
.insight-item { display: flex; gap: 15px; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.insight-item:last-child { border-bottom: none; }
.insight-icon { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; font-weight: bold;}
.i-green { background: #e6f6ee; color: var(--success); }
.i-blue { background: #e8f0fe; color: var(--primary); }
.insight-text h4 { margin: 0 0 4px 0; font-size: 13px; font-weight: 800; color: var(--text-main); }
.insight-text p { margin: 0; font-size: 11px; color: var(--text-muted); line-height: 1.4; font-weight:500;}
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 2. LÓGICA E MATEMÁTICA
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

def calc_var(atual, anterior):
    if anterior == 0: return 0
    return ((atual - anterior) / abs(anterior)) * 100

def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "CASACARESC", "CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "CAPESAUDE", "SIM SAÚDE"]
    if any(c in conta for c in convênios) or "PARTICULAR" in conta or "CARTÃO" in conta: 
        return "Receita Bruta"
    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "INSS", "HONORÁRIOS", "MÉDICO", "FORNECEDORES", "CUSTO", "MEDICAMENTOS", "OPME"]): 
        return "CPV/CSP"
    if any(c in conta for c in ["IMPOSTOS", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): 
        return "Deduções"
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "INTERNET", "CONTABILIDADE"]): 
        return "OPEX"
    return "Outros"

@st.cache_data(ttl=60)
def preparar_dados_dre():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()
    try:
        df = conn.read(worksheet="Extratos_Bancos", ttl=0)
        col_data, col_deb, col_cred, col_conta = df.columns[1], df.columns[4], df.columns[5], df.columns[8]
        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Débito'] = df[col_deb].apply(limpa_valor)
        df['Crédito'] = df[col_cred].apply(limpa_valor)
        df['Valor Líquido'] = df['Crédito'] - df['Débito']
        df['Mês_Ano'] = df['Data'].dt.to_period('M')
        df['Macro'] = df[col_conta].apply(classificar_conta)
        return df[df['Data'].notna()]
    except Exception as e:
        return pd.DataFrame()

df_base = preparar_dados_dre()
if df_base.empty: st.stop()

meses_disponiveis = sorted(df_base['Mês_Ano'].unique())
mes_atual = meses_disponiveis[-1]
mes_anterior = meses_disponiveis[-2] if len(meses_disponiveis) > 1 else mes_atual
meses_str = [str(m) for m in meses_disponiveis]

def get_val(macro, mes):
    return df_base[(df_base['Macro'] == macro) & (df_base['Mês_Ano'] == mes)]['Valor Líquido'].sum()

# Matemática Mês Atual
rec_bruta = get_val("Receita Bruta", mes_atual)
deducoes = get_val("Deduções", mes_atual)
rec_liq = rec_bruta + deducoes
cpv = get_val("CPV/CSP", mes_atual)
lucro_bruto = rec_liq + cpv
opex = get_val("OPEX", mes_atual)
ebitda = lucro_bruto + opex
outros = get_val("Outros", mes_atual)
lucro_liq = ebitda + outros

# Matemática Mês Anterior
ant_rec_bruta = get_val("Receita Bruta", mes_anterior)
ant_deducoes = get_val("Deduções", mes_anterior)
ant_rec_liq = ant_rec_bruta + ant_deducoes
ant_cpv = get_val("CPV/CSP", mes_anterior)
ant_lucro_bruto = ant_rec_liq + ant_cpv
ant_opex = get_val("OPEX", mes_anterior)
ant_ebitda = ant_lucro_bruto + ant_opex
ant_outros = get_val("Outros", mes_anterior)
ant_lucro_liq = ant_ebitda + ant_outros

mg_bruta = (lucro_bruto / rec_bruta * 100) if rec_bruta else 0
mg_ebitda = (ebitda / rec_bruta * 100) if rec_bruta else 0
ant_mg_bruta = (ant_lucro_bruto / ant_rec_bruta * 100) if ant_rec_bruta else 0
ant_mg_ebitda = (ant_ebitda / ant_rec_bruta * 100) if ant_rec_bruta else 0

# ==============================================================================
# 3. CONSTRUÇÃO DO HTML (HEADER E KPIs)
# ==============================================================================
def html_var(atual, ant, is_margin=False):
    val = (atual - ant) if is_margin else calc_var(abs(atual), abs(ant))
    cor = "var-up" if val >= 0 else "var-down"
    seta = "▲" if val >= 0 else "▼"
    suf = "p.p." if is_margin else "%"
    return f"<div class='kpi-var {cor}'><span>{seta}</span> {abs(val):.1f}{suf}</div>"

nome_mes_atual = pd.Period(mes_atual).strftime('%B/%Y').capitalize()
data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')

st.markdown(textwrap.dedent(f"""
<div class="exec-header">
    <div>
        <h1>DRE GERENCIAL EXECUTIVO</h1>
        <p>Análise de Resultados • Performance • Tomada de Decisão</p>
    </div>
    <div class="exec-filters">
        <div class="exec-filter-item"><label>Período</label><div class="val">{nome_mes_atual} <span>▼</span></div></div>
        <div class="exec-filter-item"><label>Unidade</label><div class="val">Todas <span>▼</span></div></div>
        <div class="exec-filter-item"><label>Centro de Custo</label><div class="val">Todos <span>▼</span></div></div>
        <div class="exec-update">
            <span style="font-size:20px;">📅</span>
            <div><span>Última Atualização</span><b>{data_hoje}</b></div>
        </div>
    </div>
</div>
"""), unsafe_allow_html=True)

st.markdown(textwrap.dedent(f"""
<div class="kpi-row">
    <div class="kpi-card c-blue">
        <div class="kpi-top">
            <div class="kpi-icon">💰</div>
            <div class="kpi-info"><div class="kpi-title">Receita Bruta</div><div class="kpi-val">R$ {formata_kpi(rec_bruta)}</div></div>
        </div>
        <div class="kpi-meta-box"><span>Mês Anterior: R$ {formata_kpi(ant_rec_bruta)}</span>{html_var(rec_bruta, ant_rec_bruta)}</div>
    </div>
    <div class="kpi-card c-green">
        <div class="kpi-top">
            <div class="kpi-icon">%</div>
            <div class="kpi-info"><div class="kpi-title">Margem Bruta</div><div class="kpi-val">{mg_bruta:.1f}%</div></div>
        </div>
        <div class="kpi-meta-box"><span>Mês Anterior: {ant_mg_bruta:.1f}%</span>{html_var(mg_bruta, ant_mg_bruta, True)}</div>
    </div>
    <div class="kpi-card c-green">
        <div class="kpi-top">
            <div class="kpi-icon">📊</div>
            <div class="kpi-info"><div class="kpi-title">EBITDA</div><div class="kpi-val">R$ {formata_kpi(ebitda)}</div></div>
        </div>
        <div class="kpi-meta-box"><span>Mês Anterior: R$ {formata_kpi(ant_ebitda)}</span>{html_var(ebitda, ant_ebitda)}</div>
    </div>
    <div class="kpi-card c-green">
        <div class="kpi-top">
            <div class="kpi-icon">📈</div>
            <div class="kpi-info"><div class="kpi-title">Margem EBITDA</div><div class="kpi-val">{mg_ebitda:.1f}%</div></div>
        </div>
        <div class="kpi-meta-box"><span>Mês Anterior: {ant_mg_ebitda:.1f}%</span>{html_var(mg_ebitda, ant_mg_ebitda, True)}</div>
    </div>
    <div class="kpi-card c-blue">
        <div class="kpi-top">
            <div class="kpi-icon">$</div>
            <div class="kpi-info"><div class="kpi-title">Lucro Líquido</div><div class="kpi-val">R$ {formata_kpi(lucro_liq)}</div></div>
        </div>
        <div class="kpi-meta-box"><span>Mês Anterior: R$ {formata_kpi(ant_lucro_liq)}</span>{html_var(lucro_liq, ant_lucro_liq)}</div>
    </div>
</div>
"""), unsafe_allow_html=True)

# ==============================================================================
# 4. GRÁFICOS (WATERFALL BLINDADO E TENDÊNCIA)
# ==============================================================================
col_g1, col_g2 = st.columns([1.6, 1])

with col_g1:
    st.markdown("<div class='chart-box'><div class='chart-title'>Decomposição do Resultado</div><div class='chart-subtitle'>Como a Receita Bruta se transforma em Lucro Líquido</div>", unsafe_allow_html=True)
    
    # WATERFALL MATEMÁTICA CORRETA
    x_water = ["Receita Bruta", "Deduções", "Receita Líquida", "CPV / CSP", "Lucro Bruto", "OPEX", "EBITDA", "Depreciação/Outros", "Lucro Líquido"]
    
    # IMPORTANTE: Nos "totals", passamos 0 para o Plotly não somar valor extra.
    y_water = [rec_bruta, deducoes, 0, cpv, 0, opex, 0, outros, 0]
    medidas = ["relative", "relative", "total", "relative", "total", "relative", "total", "relative", "total"]
    
    # Textos exatos dos subtotais para mostrar na tela
    textos = [
        f"R$ {formata_num(rec_bruta)}", f"-R$ {formata_num(abs(deducoes))}", f"R$ {formata_num(rec_liq)}",
        f"-R$ {formata_num(abs(cpv))}", f"R$ {formata_num(lucro_bruto)}", f"-R$ {formata_num(abs(opex))}",
        f"R$ {formata_num(ebitda)}", f"-R$ {formata_num(abs(outros))}", f"R$ {formata_num(lucro_liq)}"
    ]

    fig_w = go.Figure(go.Waterfall(
        x=x_water, y=y_water, measure=medidas, text=textos, textposition="outside",
        textfont=dict(color="#002b66", size=11, weight="bold"),
        connector={"line": {"color": "#d2dbe3", "width": 1, "dash": "dot"}},
        increasing={"marker": {"color": "#002b66"}},
        decreasing={"marker": {"color": "#fc4e51"}},
        totals={"marker": {"color": "#002b66"}}
    ))
    fig_w.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#1a2332", weight="bold")), yaxis=dict(showgrid=True, gridcolor="#eef2f6", tickfont=dict(size=10)), margin=dict(t=20, b=10, l=0, r=0), height=300)
    st.plotly_chart(fig_w, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_g2:
    st.markdown("<div class='chart-box'><div class='chart-title'>Tendência Mensal</div><div class='chart-subtitle'>Evolução dos Principais Indicadores</div>", unsafe_allow_html=True)
    
    hist_meses = [pd.Period(m).strftime('%b').capitalize() for m in meses_str[-6:]]
    hist_rec = [get_val("Receita Bruta", m) for m in meses_str[-6:]]
    hist_ebitda = [get_val("Receita Bruta", m) + get_val("Deduções", m) + get_val("CPV/CSP", m) + get_val("OPEX", m) for m in meses_str[-6:]]
    hist_mg = [(e/r*100) if r!=0 else 0 for e, r in zip(hist_ebitda, hist_rec)]

    fig_c = make_subplots(specs=[[{"secondary_y": True}]])
    fig_c.add_trace(go.Bar(x=hist_meses, y=hist_rec, name="Receita Bruta", marker_color="#002b66"), secondary_y=False)
    fig_c.add_trace(go.Bar(x=hist_meses, y=hist_ebitda, name="EBITDA", marker_color="#2970d4"), secondary_y=False)
    fig_c.add_trace(go.Scatter(x=hist_meses, y=hist_mg, name="Margem EBITDA (%)", mode="lines+markers", line=dict(color="#fc4e51", width=3)), secondary_y=True)
    
    fig_c.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, tickfont=dict(size=10, weight="bold")), yaxis=dict(showgrid=True, gridcolor="#eef2f6", showticklabels=False), yaxis2=dict(showgrid=False, showticklabels=False), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)), margin=dict(t=20, b=10, l=0, r=0), height=300, barmode='group')
    st.plotly_chart(fig_c, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 5. MATRIZ DRE E ANÁLISE GERENCIAL
# ==============================================================================
col_t1, col_t2 = st.columns([2.3, 1])

with col_t1:
    html_tabela = f"""
    <div class="matrix-container">
        <div class="matrix-header"><span>🗂️</span> Matriz DRE Gerencial</div>
        <table class="dre-table">
            <thead>
                <tr>
                    <th>Descrição</th>
                    <th style="text-align:center;">Realizado<br>{nome_mes_atual}<br>(R$)</th>
                    <th style="text-align:center;">Realizado<br>{pd.Period(mes_anterior).strftime('%B/%Y').capitalize()}<br>(R$)</th>
                    <th style="text-align:center;">Var. %<br>(MoM)</th>
                    <th style="text-align:center;">AV %<br>(Rec. Líquida)</th>
                </tr>
            </thead>
            <tbody>
    """

    linhas_dre = [
        ("Receita Bruta", rec_bruta, ant_rec_bruta, False),
        ("Deduções da Receita", deducoes, ant_deducoes, False),
        ("Receita Líquida", rec_liq, ant_rec_liq, True),
        ("Custo dos Serviços (CPV/CSP)", cpv, ant_cpv, False),
        ("Lucro Bruto", lucro_bruto, ant_lucro_bruto, True),
        ("Despesas Operacionais (OPEX)", opex, ant_opex, False),
        ("EBITDA", ebitda, ant_ebitda, True),
        ("Depreciação e Outros", outros, ant_outros, False),
        ("Lucro Líquido", lucro_liq, ant_lucro_liq, True)
    ]

    base_av = rec_liq if rec_liq != 0 else 1

    for nome, val_at, val_ant, destaque in linhas_dre:
        var_pct = calc_var(abs(val_at), abs(val_ant))
        av_pct = (val_at / base_av) * 100
        
        cor_var = "color: #02b05c;" if var_pct > 0 else "color: #fc4e51;"
        if "Custo" in nome or "Deduções" in nome or "Despesas" in nome or "Depreciação" in nome:
            cor_var = "color: #fc4e51;" if var_pct > 0 else "color: #02b05c;"
            
        sinal = "+" if var_pct > 0 else ""
        classe = "row-macro" if destaque else ""
        
        val_at_str = f"({formata_num(abs(val_at))})" if val_at < 0 else formata_num(val_at)
        val_ant_str = f"({formata_num(abs(val_ant))})" if val_ant < 0 else formata_num(val_ant)
        
        html_tabela += f"""
            <tr class="{classe}">
                <td>{nome}</td>
                <td style="text-align:center;">{val_at_str}</td>
                <td style="text-align:center;">{val_ant_str}</td>
                <td style="text-align:center; font-weight:800; {cor_var}">{sinal}{var_pct:.1f}%</td>
                <td style="text-align:center;">{av_pct:.1f}%</td>
            </tr>
        """
    html_tabela += "</tbody></table></div>"
    st.markdown(textwrap.dedent(html_tabela), unsafe_allow_html=True)

with col_t2:
    txt_rec = "acima" if rec_bruta > ant_rec_bruta else "abaixo"
    txt_lucro = "em destaque" if lucro_liq > ant_lucro_liq else "em atenção"

    html_insights = f"""
    <div class="insight-box">
        <div class="insight-header"><span>🎯</span> Análise Gerencial</div>
        <div class="insight-item">
            <div class="insight-icon i-green">📈</div>
            <div class="insight-text">
                <h4>Receita Bruta {txt_rec}</h4>
                <p>Variação de {calc_var(rec_bruta, ant_rec_bruta):.1f}% vs. mês anterior, monitorando o crescimento das operações.</p>
            </div>
        </div>
        <div class="insight-item">
            <div class="insight-icon i-green">%</div>
            <div class="insight-text">
                <h4>Margens Operacionais</h4>
                <p>A Margem EBITDA fechou em {mg_ebitda:.1f}%, refletindo a eficiência da operação.</p>
            </div>
        </div>
        <div class="insight-item">
            <div class="insight-icon i-green">$</div>
            <div class="insight-text">
                <h4>Lucro Líquido {txt_lucro}</h4>
                <p>Resultado de R$ {formata_kpi(lucro_liq)} no período, com variação de {calc_var(lucro_liq, ant_lucro_liq):.1f}%.</p>
            </div>
        </div>
        <div class="insight-item">
            <div class="insight-icon i-blue">🔍</div>
            <div class="insight-text">
                <h4>Foco de Ação</h4>
                <p>Manter disciplina de custos operacionais e preservar a evolução das margens.</p>
            </div>
        </div>
    </div>
    """
    st.markdown(textwrap.dedent(html_insights), unsafe_allow_html=True)
