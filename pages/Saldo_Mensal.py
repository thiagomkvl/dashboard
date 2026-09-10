import streamlit as st

# O set_page_config OBRIGATORIAMENTE tem que ser a primeira coisa do arquivo
st.set_page_config(page_title="Análise Mensal Tasy", layout="wide", page_icon="📊", initial_sidebar_state="expanded")

import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime
import textwrap

# BLINDAGEM MÁXIMA DE CONEXÃO
try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# --- CUSTOM CSS (IDENTIDADE VISUAL IDÊNTICA AO DASHBOARD_SALDO) ---
css = """
<style>
    :root {
        --bg: #f5f7fb;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --border: #d0e3e4;
        --text: #172033;
        --muted: #6b7280;
        --primary: #008A8C;
        --success: #1cc88a;
        --danger: #e74a3b;
        --warning: #c58a16;
        --shadow: 0 4px 15px rgba(0, 138, 140, 0.15);
    }
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    .main { background: var(--bg); }
    .main .block-container { padding-top: 0.8rem; padding-bottom: 0.7rem; max-width: 97%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.38rem !important; }
    .stPlotlyChart { background: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }
    /* Cabeçalho */
    .dashboard-header { display: flex; justify-content: space-between; align-items: center; min-height: 64px; padding: 8px 4px 10px; margin-bottom: 10px; border-bottom: 1px solid var(--border); }
    .header-period { min-width: 200px; }
    .header-period .date { font-size: 18px; font-weight: 900; color: var(--text); letter-spacing: -0.25px; }
    .header-period .label { margin-top: 2px; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
    .header-center { text-align: center; }
    .header-center h1 { margin: 0; color: var(--text); font-size: 21px; line-height: 1.2; font-weight: 800; letter-spacing: 0.35px; }
    .header-center p { margin: 3px 0 0; color: var(--muted); font-size: 10px; font-weight: 500; letter-spacing: 0.3px; }
    /* KPIs */
    .kpi-card { position: relative; overflow: hidden; min-height: 90px; padding: 18px 20px; border-radius: 10px; box-shadow: var(--shadow); text-align: left; border: none; display: flex; flex-direction: column; justify-content: center; }
    .kpi-card.total { background: linear-gradient(135deg, #004D4E, #003334); }
    .kpi-card.corrente { background: linear-gradient(135deg, #006E6F, #004b4c); }
    .kpi-card.aplicado { background: linear-gradient(135deg, #008A8C, #006869); }
    .kpi-card.inicial { background: linear-gradient(135deg, #1CB0B2, #148b8d); }
    .kpi-title { font-size: 11px; line-height: 1.2; font-weight: 750; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); }
    .kpi-value { font-size: 26px; line-height: 1.15; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; white-space: nowrap; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); margin-top: 6px; }
    .kpi-var { font-size: 11px; font-weight: 800; padding: 2px 7px; border-radius: 5px; display: inline-flex; align-items: center; letter-spacing: 0.5px;}
    .kpi-var.up { background: rgba(74, 222, 128, 0.2); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
    .kpi-var.down { background: rgba(248, 113, 113, 0.2); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }
    .kpi-var.neutral { background: rgba(255, 255, 255, 0.15); color: #e2e8f0; border: 1px solid rgba(255, 255, 255, 0.2); }
    .section-title { display: flex; align-items: center; min-height: 25px; margin-bottom: 5px; padding: 0 0 5px; border-bottom: 1px solid var(--border); color: var(--text); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.75px; }
    .section-title::before { content: ""; width: 3px; height: 12px; margin-right: 7px; border-radius: 4px; background: var(--primary); }
    .section-title-inline { font-size: 9px; font-weight: 750; color: var(--muted); text-transform: uppercase; letter-spacing: 0.45px; }
    .movement-card { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; background: #f4fafa; }
    .tabela-container { overflow-x: auto; overflow-y: hidden; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); box-shadow: 0 2px 8px rgba(0, 138, 140, 0.04); font-size: 12px; width: 100%; margin-bottom: 8px; }
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; margin: 0; }
    .tabela-financeira th { background: #eaf4f4; color: #596274; font-size: 10px; font-weight: 800; text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.35px; position: sticky; top: 0; z-index: 2; }
    .tabela-financeira td { padding: 10px 8px; border-bottom: 1px solid #ebf2f2; font-size: 13px; font-weight: 550; color: #273043; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #f0f7f7; }
    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: left !important; font-weight: 750; font-variant-numeric: tabular-nums; font-size: 14px; }
    hr { border: 0 !important; border-top: 1px solid var(--border) !important; margin: 15px 0 !important; }
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .main .block-container { max-width: 100% !important; padding: 10px !important; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; color-adjust: exact !important; }
        .kpi-card, .tabela-container, .movement-card { break-inside: avoid; max-height: none !important; overflow: visible !important; }
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÕES DE TRATAMENTO DE DADOS DO TASY
# ==============================================================================
def limpa_valor_bruto(valor):
    try:
        if isinstance(valor, pd.Series): 
            valor = valor.iloc[0] if not valor.empty else 0.0
            
        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan", "NaN", "None"]:
            return 0.0
        if isinstance(valor, (int, float)):
            return float(valor)
            
        v_str = str(valor).strip()
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        v_str = v_str.replace('R$', '').strip()
        
        if '.' in v_str and ',' in v_str:
            v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
            
        return float(v_str)
    except Exception:
        return 0.0

def formatar_moeda(valor):
    try:
        val = float(valor)
        if val == 0: return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "-"

def formatar_abreviado(valor):
    try:
        val = float(valor)
        if abs(val) >= 1_000_000:
            return f"R$ {val/1_000_000:.1f}M".replace('.', ',')
        elif abs(val) >= 1_000:
            return f"R$ {val/1_000:.1f}K".replace('.', ',')
        else:
            return f"R$ {val:.0f}"
    except Exception:
        return ""

# ==============================================================================
# 2. CARGA E CONSOLIDAÇÃO DE DADOS BANCÁRIOS (TASY)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_tasy():
    conn = conectar_sheets()
    if conn is None:
        return pd.DataFrame(), pd.DataFrame(), []

    try:
        # 2.1 Carrega Saldo Inicial por Conta
        df_saldo = conn.read(worksheet="Saldo_Inicial_Ano", ttl=0)
        df_saldo.columns = [str(c).strip() for c in df_saldo.columns]
        
        col_conta_s = next((c for c in df_saldo.columns if 'conta' in c.lower() or 'banco' in c.lower() or 'ds_conta' in c.lower()), df_saldo.columns[0])
        col_val_s = next((c for c in df_saldo.columns if 'saldo' in c.lower() or 'valor' in c.lower() or 'inicial' in c.lower()), df_saldo.columns[1])
        
        df_saldo_clean = pd.DataFrame()
        df_saldo_clean['Conta'] = df_saldo[col_conta_s].astype(str).str.strip()
        df_saldo_clean['Saldo_Inicial'] = df_saldo[col_val_s].apply(limpa_valor_bruto)

        # 2.2 Carrega Extratos do Tasy
        df_extrato = conn.read(worksheet="Extratos_Tasy", ttl=0)
        if df_extrato.empty:
            return df_saldo_clean, pd.DataFrame(), list(df_saldo_clean['Conta'].unique())

        df_extrato.columns = [str(c).strip() for c in df_extrato.columns]

        # Mapeamento flexível das colunas no padrão Tasy / Conciliação
        col_data = next((c for c in df_extrato.columns if 'data' in c.lower() or 'dt_' in c.lower()), df_extrato.columns[0])
        col_conta = next((c for c in df_extrato.columns if 'conta' in c.lower() or 'banco' in c.lower() or 'ds_conta' in c.lower()), None)
        col_valor = next((c for c in df_extrato.columns if 'valor' in c.lower() or 'vl_' in c.lower() or 'lançamento' in c.lower() or 'movimento' in c.lower()), None)
        col_tipo = next((c for c in df_extrato.columns if 'tipo' in c.lower() or 'ie_tipo' in c.lower() or 'd/c' in c.lower() or 'natureza' in c.lower()), None)
        col_debito = next((c for c in df_extrato.columns if 'debito' in c.lower() or 'débito' in c.lower() or 'saida' in c.lower()), None)
        col_credito = next((c for c in df_extrato.columns if 'credito' in c.lower() or 'crédito' in c.lower() or 'entrada' in c.lower()), None)

        df_process = pd.DataFrame()
        df_process['Data'] = pd.to_datetime(df_extrato[col_data], dayfirst=True, errors='coerce').dt.normalize()
        df_process = df_process.dropna(subset=['Data'])
        
        if col_conta:
            df_process['Conta'] = df_extrato[col_conta].astype(str).str.strip()
        else:
            df_process['Conta'] = "CONTA PRINCIPAL"

        # Regras do Tasy para apurar o valor líquido e sinal (+/ -)
        if col_credito and col_debito:
            v_cred = df_extrato[col_credito].apply(limpa_valor_bruto)
            v_deb = df_extrato[col_debito].apply(limpa_valor_bruto)
            df_process['Valor_Liquido'] = v_cred - v_deb
            df_process['Entrada'] = v_cred
            df_process['Saida'] = -v_deb
        elif col_valor:
            vals = df_extrato[col_valor].apply(limpa_valor_bruto)
            if col_tipo:
                tipos = df_extrato[col_tipo].astype(str).str.upper()
                # Tratamento para 'D' (Débito/Saída) vs 'C' (Crédito/Entrada)
                is_debito = tipos.str.contains('D') | tipos.str.contains('DEB') | tipos.str.contains('SAI') | tipos.str.contains('PAG')
                vals = vals.index.map(lambda i: -abs(vals[i]) if is_debito[i] else abs(vals[i]))
            
            df_process['Valor_Liquido'] = vals
            df_process['Entrada'] = df_process['Valor_Liquido'].apply(lambda x: x if x > 0 else 0.0)
            df_process['Saida'] = df_process['Valor_Liquido'].apply(lambda x: x if x < 0 else 0.0)

        df_process['AnoMes_Sort'] = df_process['Data'].dt.to_period('M')

        # Lista unificada de contas
        todas_contas = sorted(list(set(df_saldo_clean['Conta'].unique()).union(set(df_process['Conta'].unique()))))

        return df_saldo_clean, df_process, todas_contas

    except Exception as e:
        st.error(f"Erro ao processar abas do Tasy: {e}")
        return pd.DataFrame(), pd.DataFrame(), []

# Carga inicial para popular a barra lateral
df_saldo_base, df_extrato_base, lista_contas = carregar_dados_tasy()

# ==============================================================================
# 3. BARRA LATERAL (FILTROS)
# ==============================================================================
hoje = datetime.now().date()
inicio_ano = hoje.replace(month=1, day=1)

with st.sidebar:
    st.markdown("### Filtros do Painel")
    
    data_selecionada = st.date_input(
        "Selecione o Período:",
        value=(inicio_ano, hoje),
        min_value=datetime(2020, 1, 1).date(),
        max_value=hoje,
        format="DD/MM/YYYY"
    )

    contas_filtradas = st.multiselect(
        "Contas Bancárias / Tasy:",
        options=lista_contas,
        default=lista_contas
    )
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    st.markdown("### Relatório")
    st.info("💡 Para um relatório de alta qualidade, gere um PDF. Escolha a orientação **Paisagem** e desmarque 'Cabeçalhos/Rodapés'.", icon="ℹ️")
    
    components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }" 
        style="width:100%; background:linear-gradient(135deg, #008A8C, #004D4E); color:white; border:none; padding:12px; border-radius:8px; font-family:sans-serif; font-weight:bold; font-size:14px; cursor:pointer; box-shadow: 0 4px 6px rgba(0, 138, 140, 0.2); transition: transform 0.2s;">
        🖨️ Salvar Dashboard (PDF)
        </button>
    """, height=55)

if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
    data_inicio_filtro, data_fim_filtro = data_selecionada
else:
    data_inicio_filtro = data_selecionada[0] if isinstance(data_selecionada, tuple) else data_selecionada
    data_fim_filtro = data_inicio_filtro

# ==============================================================================
# 4. CONSOLIDAÇÃO E CÁLCULO DA CASCATA MENSAL
# ==============================================================================
def processar_mensal_cascata(df_saldo, df_extrato, contas_sel, dt_inicio, dt_fim):
    if not contas_sel:
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0

    # 1. Saldo Inicial Acumulado das contas selecionadas
    df_saldo_sel = df_saldo[df_saldo['Conta'].isin(contas_sel)]
    saldo_inicial_base = df_saldo_sel['Saldo_Inicial'].sum() if not df_saldo_sel.empty else 0.0

    # 2. Filtrar movimentações das contas selecionadas
    df_ext_sel = df_extrato[df_extrato['Conta'].isin(contas_sel)].copy() if not df_extrato.empty else pd.DataFrame()

    if df_ext_sel.empty:
        return pd.DataFrame(), saldo_inicial_base, 0.0, 0.0, saldo_inicial_base

    # Agrupamento Mensal Global do ano para manter a integridade da cascata
    df_mensal = df_ext_sel.groupby('AnoMes_Sort').agg({
        'Entrada': 'sum',
        'Saida': 'sum',
        'Valor_Liquido': 'sum'
    }).reset_index().sort_values('AnoMes_Sort')

    # Efeito Cascata de Saldo mês a mês
    df_mensal['Saldo Final'] = saldo_inicial_base + df_mensal['Valor_Liquido'].cumsum()
    df_mensal['Saldo Inicial Mês'] = df_mensal['Saldo Final'] - df_mensal['Valor_Liquido']
    df_mensal['Mês'] = df_mensal['AnoMes_Sort'].dt.strftime('%m/%Y')

    # Filtrar para o período visualizado no painel
    dt_ini_pd = pd.to_datetime(dt_inicio).to_period('M')
    dt_fim_pd = pd.to_datetime(dt_fim).to_period('M')

    df_periodo = df_mensal[(df_mensal['AnoMes_Sort'] >= dt_ini_pd) & (df_mensal['AnoMes_Sort'] <= dt_fim_pd)].copy()

    if not df_periodo.empty:
        s_ini_periodo = df_periodo.iloc[0]['Saldo Inicial Mês']
        s_fim_periodo = df_periodo.iloc[-1]['Saldo Final']
        tot_ent = df_periodo['Entrada'].sum()
        tot_sai = df_periodo['Saida'].sum()
    else:
        s_ini_periodo = saldo_inicial_base
        s_fim_periodo = saldo_inicial_base
        tot_ent = 0.0
        tot_sai = 0.0

    return df_periodo, s_ini_periodo, tot_ent, tot_sai, s_fim_periodo

df_mensal, saldo_inicio, tot_entradas, tot_saidas, saldo_fim = processar_mensal_cascata(
    df_saldo_base, df_extrato_base, contas_filtradas, data_inicio_filtro, data_fim_filtro
)

if df_mensal.empty:
    st.warning("⚠️ Nenhuma movimentação do Tasy encontrada para os filtros selecionados.")
    st.stop()

# ==============================================================================
# 5. KPIS E GRÁFICOS
# ==============================================================================
movimento_liquido = tot_entradas + tot_saidas

def get_var_html(valor):
    if valor > 0: return f"<div class='kpi-var up'>↗ Positivo</div>"
    elif valor < 0: return f"<div class='kpi-var down'>↘ Negativo</div>"
    else: return f"<div class='kpi-var neutral'>→ Zero</div>"

periodo_str = f"{data_inicio_filtro.strftime('%m/%Y')} a {data_fim_filtro.strftime('%m/%Y')}"

# Donut Entradas vs Saídas
fig_donut = go.Figure(data=[go.Pie(
    values=[tot_entradas, abs(tot_saidas)], 
    labels=['Entradas', 'Saídas'], 
    hole=0.6, 
    marker=dict(colors=['#1cc88a', '#e74a3b']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+value'
)])
fig_donut.update_layout(
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=10, b=10, l=0, r=0), height=315,
    annotations=[dict(text=f"<b>Fluxo Tasy</b><br>Mensal", x=0.5, y=0.5, font_size=13, font_color="#172033", showarrow=False)]
)

# Gráfico de Barras (Entradas/Saídas) + Linha de Saldo Acumulado
fig_combinado = go.Figure()

fig_combinado.add_trace(go.Bar(
    x=df_mensal['Mês'], y=df_mensal['Entrada'], name='Entradas',
    marker_color='#1cc88a', text=[formatar_abreviado(v) for v in df_mensal['Entrada']],
    textposition='outside', textfont=dict(size=10)
))
fig_combinado.add_trace(go.Bar(
    x=df_mensal['Mês'], y=abs(df_mensal['Saida']), name='Saídas',
    marker_color='#e74a3b', text=[formatar_abreviado(abs(v)) for v in df_mensal['Saida']],
    textposition='outside', textfont=dict(size=10)
))
fig_combinado.add_trace(go.Scatter(
    x=df_mensal['Mês'], y=df_mensal['Saldo Final'], name='Saldo Final',
    mode='lines+markers', line=dict(color='#008A8C', width=3),
    marker=dict(size=6, color='#004D4E')
))

fig_combinado.update_layout(
    margin=dict(t=10, b=10, l=5, r=5), height=230,
    xaxis=dict(tickfont=dict(size=10), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False),
    barmode='group',
    showlegend=False,
    plot_bgcolor='#f1f5f9', paper_bgcolor='#f1f5f9',
    hovermode='x unified'
)

# ==============================================================================
# 6. LAYOUT PRINCIPAL DO PAINEL
# ==============================================================================
st.markdown(f"""
<div class="dashboard-header">
    <div class="header-period">
        <div class="date"> {periodo_str}</div>
        <div class="label">Período Selecionado</div>
    </div>
    <div class="header-center">
        <h1>ANÁLISE DE MOVIMENTAÇÃO MENSAL (TASY)</h1>
        <p>Consolidação de Extratos e Fluxo Bancário</p>
    </div>
    <div style="min-width: 200px;"></div>
</div>
""", unsafe_allow_html=True)

kpi_row = st.columns(4)

kp_data = [
    (kpi_row[0], "SALDO INICIAL DO PERÍODO", f"R$ {saldo_inicio:,.2f}", "total", "<div class='kpi-var neutral'>→ Início</div>"),
    (kpi_row[1], "TOTAL ENTRADAS", f"R$ {tot_entradas:,.2f}", "aplicado", "<div class='kpi-var up'>↗ Receitas</div>"),
    (kpi_row[2], "TOTAL SAÍDAS", f"R$ {tot_saidas:,.2f}", "corrente", "<div class='kpi-var down'>↘ Despesas</div>"),
    (kpi_row[3], "SALDO ATUAL ACUMULADO", f"R$ {saldo_fim:,.2f}", "inicial", get_var_html(movimento_liquido))
]

for col, title, val, color, var_html in kp_data:
    card_html = f"""
    <div class='kpi-card {color}'>
        <div style='display: flex; align-items: center;'>
            {var_html}
            <div class='kpi-title' style='margin-left: 10px;'>{title}</div>
        </div>
        <div class='kpi-value'>{val}</div>
    </div>
    """
    col.markdown(card_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([0.85, 1.25, 1.6])

with c1:
    st.markdown("<div class='section-title'>COMPOSIÇÃO DO FLUXO MENSAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(f"<div class='section-title'>RESUMO LÍQUIDO <span style='margin-left:auto; font-size:11px; color:#000000; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    
    m1.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#1cc88a;'> ENTRADAS</div><div style='font-size:18px; font-weight:800;'>R$ {tot_entradas:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#e74a3b;'> SAÍDAS</div><div style='font-size:18px; font-weight:800;'>R$ {abs(tot_saidas):,.2f}</div></div>", unsafe_allow_html=True)
    
    color_liq = "#1cc88a" if movimento_liquido >= 0 else "#e74a3b"
    m3.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:{color_liq};'> RESULTADO</div><div style='font-size:18px; font-weight:800; color:{color_liq};'>R$ {movimento_liquido:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO MENSAL (ENTRADAS x SAÍDAS x SALDO)</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown(f"<div class='section-title'>DETALHAMENTO MÊS A MÊS <span style='margin-left:auto; font-size:11px; color:#000000; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    
    html_tabela = f'<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>MÊS</th><th class="valores">SALDO INICIAL</th><th class="valores">ENTRADAS</th><th class="valores">SAÍDAS</th><th class="valores">SALDO FINAL</th></tr></thead><tbody>'
    
    for _, row in df_mensal.iterrows():
        mes = row['Mês']
        s_ini = row['Saldo Inicial Mês']
        ent = row['Entrada']
        sai = row['Saida']
        s_fin = row['Saldo Final']
        
        html_tabela += f'<tr><td>{mes}</td><td class="valores">{formatar_moeda(s_ini)}</td><td class="valores" style="color:#1cc88a;">{formatar_moeda(ent)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(sai)}</td><td class="valores">{formatar_moeda(s_fin)}</td></tr>'
        
    html_tabela += f'<tr class="linha-total"><td>TOTAIS (PERÍODO)</td><td class="valores">-</td><td class="valores" style="color:#1cc88a;">{formatar_moeda(tot_entradas)}</td><td class="valores" style="color:#e74a3b;">{formatar_moeda(tot_saidas)}</td><td class="valores">{formatar_moeda(saldo_fim)}</td></tr>'
    html_tabela += '</tbody></table></div>'
    
    st.markdown(html_tabela, unsafe_allow_html=True)
