import streamlit as st

# O set_page_config OBRIGATORIAMENTE tem que ser a primeira coisa do arquivo
st.set_page_config(page_title="Acompanhamento da Obra", layout="wide", page_icon="🏗️", initial_sidebar_state="expanded")

import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import unicodedata
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
    .tabela-container-scroll { overflow-x: hidden; overflow-y: auto; max-height: 815px; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); box-shadow: 0 2px 8px rgba(0, 138, 140, 0.04); font-size: 11px; width: 100%; margin-bottom: 8px; }
    .tabela-financeira { width: 100%; border-collapse: separate; border-spacing: 0; margin: 0; }
    .tabela-financeira th { background: #eaf4f4; color: #596274; font-size: 10px; font-weight: 800; text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.35px; position: sticky; top: 0; z-index: 2; }
    .tabela-financeira td { padding: 10px 8px; border-bottom: 1px solid #ebf2f2; font-size: 13px; font-weight: 550; color: #273043; white-space: nowrap; }
    .tabela-financeira tbody tr:hover td { background: #f0f7f7; }
    .tabela-financeira .linha-total { background: #e0efef; border-top: 2px solid #008A8C; }
    .tabela-financeira .linha-total td { color: var(--text); font-weight: 800; }
    .tabela-financeira th.valores, .tabela-financeira td.valores { text-align: left !important; font-weight: 750; font-variant-numeric: tabular-nums; font-size: 14px; }
    hr { border: 0 !important; border-top: 1px solid var(--border) !important; margin: 15px 0 !important; }
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .main .block-container { max-width: 100% !important; padding: 10px !important; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; color-adjust: exact !important; }
        .kpi-card, .tabela-container, .tabela-container-scroll, .movement-card { break-inside: avoid; max-height: none !important; overflow: visible !important; }
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 0. CONFIGURAÇÃO DA BARRA LATERAL
# ==============================================================================
hoje = datetime.now().date()
primeiro_dia_mes = hoje.replace(day=1)

with st.sidebar:
    st.markdown("### Filtros do Painel")
    
    data_selecionada = st.date_input(
        "Selecione o Período:",
        value=(primeiro_dia_mes, hoje),
        min_value=datetime(2020, 1, 1).date(),
        max_value=hoje,
        format="DD/MM/YYYY"
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
# 1. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
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
# 2. CARGA E PROCESSAMENTO DOS DADOS DA OBRA
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_obra(data_inicio, data_fim):
    conn = conectar_sheets()
    if conn is None: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, 0.0, 0.0, data_inicio, data_fim

    try:
        df_obra = conn.read(worksheet="Obra_Lancamentos", ttl=0)
        if df_obra.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, 0.0, 0.0, data_inicio, data_fim

        df_obra.columns = [str(c).strip() for c in df_obra.columns]

        # Identificação flexível das colunas
        col_data = next((c for c in df_obra.columns if 'data' in c.lower()), df_obra.columns[0])
        col_cat = next((c for c in df_obra.columns if 'etapa' in c.lower() or 'categoria' in c.lower()), df_obra.columns[1])
        col_orcado = next((c for c in df_obra.columns if 'orçado' in c.lower() or 'orcado' in c.lower() or 'previsto' in c.lower()), None)
        col_pago = next((c for c in df_obra.columns if 'pago' in c.lower() or 'realizado' in c.lower() or 'valor' in c.lower()), None)

        df_process = pd.DataFrame()
        df_process['Data'] = pd.to_datetime(df_obra[col_data], dayfirst=True, errors='coerce').dt.normalize()
        df_process['Categoria'] = df_obra[col_cat].astype(str).str.strip()
        df_process['Vl Orçado'] = df_obra[col_orcado].apply(limpa_valor_bruto) if col_orcado else 0.0
        df_process['Vl Pago'] = df_obra[col_pago].apply(limpa_valor_bruto) if col_pago else 0.0

        dt_ini_pd = pd.to_datetime(data_inicio)
        dt_fim_pd = pd.to_datetime(data_fim)

        # Filtragem por período selecinado
        df_period = df_process[(df_process['Data'] >= dt_ini_pd) & (df_process['Data'] <= dt_fim_pd)].copy()

        # Resumo por Categoria
        if not df_period.empty:
            df_resumo_cat = df_period.groupby('Categoria').agg({'Vl Orçado': 'sum', 'Vl Pago': 'sum'}).reset_index()
        else:
            df_resumo_cat = pd.DataFrame(columns=['Categoria', 'Vl Orçado', 'Vl Pago'])

        df_resumo_cat['Saldo Restante'] = df_resumo_cat['Vl Orçado'] - df_resumo_cat['Vl Pago']

        # Evolução Diária para o gráfico combinado
        if not df_period.empty:
            df_graficos = df_period.groupby('Data').agg({'Vl Orçado': 'sum', 'Vl Pago': 'sum'}).reset_index().sort_values('Data')
            df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%d/%m')
            df_graficos['Acumulado Pago'] = df_graficos['Vl Pago'].cumsum()
        else:
            df_graficos = pd.DataFrame(columns=['Data', 'Vl Orçado', 'Vl Pago', 'Data_Label', 'Acumulado Pago'])

        orcado_total = df_resumo_cat['Vl Orçado'].sum()
        pago_total = df_resumo_cat['Vl Pago'].sum()
        saldo_restante_total = orcado_total - pago_total

        return df_resumo_cat, df_graficos, df_period, orcado_total, pago_total, saldo_restante_total, data_inicio, data_fim

    except Exception as e:
        st.error(f"Erro ao processar dados da obra: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, 0.0, data_inicio, data_fim

# ==============================================================================
# CHAMADA PRINCIPAL
# ==============================================================================
df_resumo_cat, df_graficos, df_period, orcado_total, pago_total, saldo_restante_total, data_ini_painel, data_fim_painel = carregar_dados_obra(data_inicio_filtro, data_fim_filtro)

if df_resumo_cat.empty and df_period.empty:
    st.warning("⚠️ Nenhum lançamento encontrado para o período selecionado.")
    st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs E VARIAÇÕES (%)
# ==============================================================================
pct_executado = (pago_total / orcado_total * 100) if orcado_total > 0 else 0.0

def get_var_html(pct):
    if pct > 100: return f"<div class='kpi-var down'>↗ {pct:.1f}%</div>"
    elif pct > 0: return f"<div class='kpi-var up'>↗ {pct:.1f}%</div>"
    else: return f"<div class='kpi-var neutral'>→ 0.0%</div>"

# ==============================================================================
# 4. MONTAGEM DOS GRÁFICOS
# ==============================================================================
periodo_str = f"{data_ini_painel.strftime('%d/%m/%Y')} - {data_fim_painel.strftime('%d/%m/%Y')}"
dt_ini_short = data_ini_painel.strftime('%d/%m')
dt_fim_short = data_fim_painel.strftime('%d/%m')

# Donut executado vs restante
fig_donut = go.Figure(data=[go.Pie(
    values=[pago_total, max(0, saldo_restante_total)], 
    labels=['Pago', 'Saldo Restante'], 
    hole=0.6, 
    marker=dict(colors=['#008A8C', '#004D4E']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+percent'
)])
fig_donut.update_layout(
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=10, b=10, l=0, r=0), height=315,
    annotations=[dict(text=f"<b>{pct_executado:.1f}%</b><br>Executado", x=0.5, y=0.48, font_size=13, font_color="#004D4E", showarrow=False)]
)

# Gráfico da evolução dos desembolsos
fig_combinado = go.Figure()
fig_combinado.add_trace(go.Bar(
    x=df_graficos['Data_Label'],
    y=df_graficos['Vl Pago'],
    name='Gasto Diário',
    marker_color='#004D4E', 
    text=[formatar_abreviado(v) for v in df_graficos['Vl Pago']],
    textposition='outside',
    textfont=dict(size=11, color="#1a2035", weight="bold"),
    opacity=0.9,
    width=0.45
))

fig_combinado.update_layout(
    margin=dict(t=10, b=10, l=5, r=5), height=230,
    xaxis=dict(tickfont=dict(size=10), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False),
    barmode='overlay',
    showlegend=False,
    plot_bgcolor='#f1f5f9', paper_bgcolor='#f1f5f9',
    hovermode='x unified'
)

# ==============================================================================
# 5. MONTAGEM DO PAINEL (LAYOUT IDENTICO AO DASHBOARD_SALDO)
# ==============================================================================
st.markdown(f"""
<div class="dashboard-header">
    <div class="header-period">
        <div class="date"> {periodo_str}</div>
        <div class="label">Período Selecionado</div>
    </div>
    <div class="header-center">
        <h1>ACOMPANHAMENTO DE OBRA</h1>
        <p>Controle Consolidado de Custos e Etapas</p>
    </div>
    <div style="min-width: 200px;"></div>
</div>
""", unsafe_allow_html=True)

kpi_row = st.columns(4)

kp_data = [
    (kpi_row[0], "ORÇAMENTO TOTAL", f"R$ {orcado_total:,.2f}", "total", "<div class='kpi-var neutral'>→ Total</div>"),
    (kpi_row[1], "TOTAL REALIZADO (PAGO)", f"R$ {pago_total:,.2f}", "corrente", get_var_html(pct_executado)),
    (kpi_row[2], "SALDO A EXECUTAR", f"R$ {saldo_restante_total:,.2f}", "aplicado", "<div class='kpi-var neutral'>→ Saldo</div>"),
    (kpi_row[3], "% EXECUTADO DA OBRA", f"{pct_executado:.1f}%", "inicial", "<div class='kpi-var neutral'>→ Status</div>")
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
    st.markdown("<div class='section-title'>EXECUÇÃO FINANCEIRA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown(f"<div class='section-title'>RESUMO DE GASTOS <span style='margin-left:auto; font-size:11px; color:#000000; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    
    m1.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#008A8C;'> ORÇADO</div><div style='font-size:18px; font-weight:800;'>R$ {orcado_total:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:#e74a3b;'> REALIZADO</div><div style='font-size:18px; font-weight:800;'>R$ {pago_total:,.2f}</div></div>", unsafe_allow_html=True)
    
    color_saldo = "#1cc88a" if saldo_restante_total >= 0 else "#e74a3b"
    m3.markdown(f"<div class='movement-card'><div class='section-title-inline' style='color:{color_saldo};'> SALDO</div><div style='font-size:18px; font-weight:800; color:{color_saldo};'>R$ {saldo_restante_total:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO DIÁRIA DE DESEMBOLSO</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown(f"<div class='section-title'>DETALHAMENTO POR ETAPA/CATEGORIA <span style='margin-left:auto; font-size:11px; color:#000000; font-weight:900; text-transform:uppercase;'>Ref: {periodo_str}</span></div>", unsafe_allow_html=True)
    
    if not df_resumo_cat.empty:
        html_tabela = f'<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>CATEGORIA / ETAPA</th><th class="valores">ORÇADO</th><th class="valores">REALIZADO</th><th class="valores">SALDO</th></tr></thead><tbody>'
        
        tot_orc = 0; tot_pago = 0; tot_saldo = 0
        
        for _, row in df_resumo_cat.iterrows():
            cat = row['Categoria']
            orc = row['Vl Orçado']
            pago = row['Vl Pago']
            saldo = row['Saldo Restante']
            
            tot_orc += orc
            tot_pago += pago
            tot_saldo += saldo
            
            html_tabela += f'<tr><td>{cat}</td><td class="valores">{formatar_moeda(orc)}</td><td class="valores">{formatar_moeda(pago)}</td><td class="valores">{formatar_moeda(saldo)}</td></tr>'
            
        html_tabela += f'<tr class="linha-total"><td>TOTAL GERAL</td><td class="valores">{formatar_moeda(tot_orc)}</td><td class="valores">{formatar_moeda(tot_pago)}</td><td class="valores">{formatar_moeda(tot_saldo)}</td></tr>'
        html_tabela += '</tbody></table></div>'
        
        st.markdown(html_tabela, unsafe_allow_html=True)
    else:
        st.info("Nenhuma categoria encontrada no período.")
