import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# ==============================================================================
# 0. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Acompanhamento de Obras", layout="wide", page_icon="🏗️", initial_sidebar_state="expanded")

# BLINDAGEM MÁXIMA DE CONEXÃO
try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# ==============================================================================
# 1. CUSTOM CSS (MANTENDO O MENU PADRÃO E APENAS CARDS CUSTOMIZADOS)
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg-color: #f5f7fb;
        --card-bg: #ffffff;
        --text-dark: #2c3e50;
        --accent: #1ab394;
        --danger: #e74a3b;
        --warning: #f6c23e;
        --shadow: 0 4px 15px rgba(0, 138, 140, 0.15);
    }
    
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .main { background: var(--bg-color); }
    .main .block-container { padding-top: 1rem; max-width: 98%; }
    
    /* HEADER E TÍTULOS */
    .dash-header { display: flex; align-items: center; margin-bottom: 20px; color: var(--text-dark); }
    .dash-header h1 { font-size: 24px; font-weight: 800; margin: 0; text-transform: uppercase; }
    .card-title { font-size: 13px; font-weight: 800; color: #5a6b7c; margin-bottom: 15px; text-transform: uppercase; }
    
    /* CARDS DE KPI (Estilo Cinza da Foto com Borda Verde) */
    .kpi-box {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 20px;
        box-shadow: var(--shadow);
        border-left: 8px solid var(--accent);
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 100%;
    }
    .kpi-box.danger-border { border-left-color: var(--danger); }
    .kpi-title-top { font-size: 14px; font-weight: 700; color: #5a6b7c; text-transform: uppercase; }
    .kpi-value-main { font-size: 30px; font-weight: 900; color: var(--text-dark); margin: 5px 0; }
    .kpi-subtitle { font-size: 11px; font-weight: 600; color: #7b8a99; text-transform: uppercase; }
    
    /* TABELA ESTILO CARD */
    .table-container {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 15px;
        box-shadow: var(--shadow);
        height: 100%;
        overflow-x: auto;
    }
    .table-custom { width: 100%; border-collapse: collapse; font-size: 12px; }
    .table-custom th { text-align: left; padding: 8px; color: #5a6b7c; font-weight: 800; border-bottom: 2px solid #cbd5e1; }
    .table-custom td { padding: 8px; border-bottom: 1px solid #cbd5e1; color: var(--text-dark); font-weight: 600; }
    .table-custom tr:last-child td { font-weight: 800; border-bottom: none; background: rgba(0,0,0,0.03); }
    
    /* PLOTLY CONTAINERS */
    .chart-container {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 15px;
        box-shadow: var(--shadow);
        margin-bottom: 20px;
    }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
# ==============================================================================
def limpa_valor(valor):
    try:
        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan"]: return 0.0
        v_str = str(valor).strip().replace('R$', '')
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        if '.' in v_str and ',' in v_str:
            v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
        return float(v_str)
    except: return 0.0

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def extract_month(m):
    """Extrai o mês da coluna MÊS (ex: 2026.01 -> 1)"""
    try:
        s = str(m).strip()
        if '.' in s: return int(float(s.split('.')[-1]))
        return int(float(s))
    except: return 0

# ==============================================================================
# 3. CARGA E TRATAMENTO DOS DADOS DO SHEETS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_obras():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    
    try:
        # --- ORÇADO ---
        df_orc = conn.read(worksheet="Orçamento_Obra", ttl=0)
        # Filtra a linha de Total e limpa nome da obra
        df_orc = df_orc[df_orc['RESUMO OBRAS'].astype(str).str.upper() != 'TOTAL'].copy()
        df_orc['Obra'] = df_orc['RESUMO OBRAS'].astype(str).str.upper().str.strip()
        
        # Melt dos meses para formato longo
        meses_cols = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        meses_existentes = [m for m in meses_cols if m in df_orc.columns]
        
        df_orc_melt = df_orc.melt(id_vars=['Obra'], value_vars=meses_existentes, var_name='Mes_Nome', value_name='Valor_Orcado')
        map_meses = {'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4, 'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8, 'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12}
        df_orc_melt['Mes'] = df_orc_melt['Mes_Nome'].map(map_meses)
        df_orc_melt['Valor_Orcado'] = df_orc_melt['Valor_Orcado'].apply(limpa_valor)
        
        # --- REALIZADO ---
        df_real = conn.read(worksheet="Realizado_Obra", ttl=0)
        df_real['Obra'] = df_real['Categoria'].astype(str).str.upper().str.strip()
        df_real['Mes'] = df_real['MÊS'].apply(extract_month)
        df_real['Valor_Realizado'] = df_real['Valor'].apply(limpa_valor)
        
        return df_orc_melt, df_real
        
    except Exception as e:
        st.error(f"Erro ao processar dados de obras: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_orcado, df_realizado = carregar_dados_obras()

if df_orcado.empty and df_realizado.empty:
    st.warning("Nenhum dado encontrado nas abas 'Orçamento_Obra' ou 'Realizado_Obra'.")
    st.stop()

# ==============================================================================
# TRATAMENTO SEGURO DA LISTA DE OBRAS (Evitando o TypeError)
# ==============================================================================
obras_orcadas = df_orcado['Obra'].dropna().astype(str).unique().tolist() if not df_orcado.empty and 'Obra' in df_orcado.columns else []
obras_realizadas = df_realizado['Obra'].dropna().astype(str).unique().tolist() if not df_realizado.empty and 'Obra' in df_realizado.columns else []

todas_obras = set(obras_orcadas) | set(obras_realizadas)
# Filtra qualquer campo vazio, nulo ou que não devesse estar no filtro da obra
lista_obras = sorted([o for o in todas_obras if o.strip().upper() not in ['NAN', '0', '', 'DIVERSAS', 'SEGUROS']])

# ==============================================================================
# 4. BARRA LATERAL 
# ==============================================================================
with st.sidebar:
    st.markdown("## FILTROS")
    
    mes_selecionado = st.selectbox("Mês de Análise", options=["Todos"] + list(range(1, 13)), format_func=lambda x: f"Mês {x:02d}" if isinstance(x, int) else x)
    obra_selecionada = st.selectbox("Empreendimento / Etapa", ["Todas"] + lista_obras)
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("Limpar Filtros Aplicados", use_container_width=True):
        st.rerun()

# Aplicação de Filtros
df_orc_filtrado = df_orcado.copy()
df_real_filtrado = df_realizado.copy()

if mes_selecionado != "Todos":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Mes'] <= mes_selecionado] # Acumulado até o mês para orçamento
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Mes'] <= mes_selecionado]

if obra_selecionada != "Todas":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Obra'] == obra_selecionada]
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Obra'] == obra_selecionada]

# ==============================================================================
# 5. CÁLCULOS GERAIS
# ==============================================================================
total_orcado = df_orc_filtrado['Valor_Orcado'].sum()
total_realizado = df_real_filtrado['Valor_Realizado'].sum()
saldo_obra = total_orcado - total_realizado
perc_concluido = (total_realizado / total_orcado * 100) if total_orcado > 0 else 0

# Tabela Cruzada Obra x Valores
df_orc_grp = df_orc_filtrado.groupby('Obra')['Valor_Orcado'].sum().reset_index()
df_real_grp = df_real_filtrado.groupby('Obra')['Valor_Realizado'].sum().reset_index()
df_matriz = pd.merge(df_orc_grp, df_real_grp, on='Obra', how='outer').fillna(0)

# Filtra sujeiras do banco de dados na matriz final
df_matriz = df_matriz[~df_matriz['Obra'].isin(['0', '', 'NAN'])]
df_matriz['Saldo (R$)'] = df_matriz['Valor_Orcado'] - df_matriz['Valor_Realizado']
df_matriz['Consumo (%)'] = (df_matriz['Valor_Realizado'] / df_matriz['Valor_Orcado'] * 100).fillna(0).replace([float('inf'), float('-inf')], 0)

# ==============================================================================
# 6. MONTAGEM DO LAYOUT DO DASHBOARD
# ==============================================================================
st.markdown("<div class='dash-header'><h1>Análise de Custos da Obra</h1></div>", unsafe_allow_html=True)

# --- LINHA 1: KPIs e Tabela Resumo ---
c1, c2, c3 = st.columns([1, 1, 2.5])

with c1:
    st.markdown(f"""
    <div class='kpi-box'>
        <div class='kpi-title-top'>Custo Realizado</div>
        <div class='kpi-value-main' style='color: #1ab394;'>{formatar_moeda(total_realizado)}</div>
        <div class='kpi-subtitle'>Valor Executado (Acumulado)</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    cor_saldo = "danger-border" if saldo_obra < 0 else ""
    cor_texto = "color: #e74a3b;" if saldo_obra < 0 else "color: #1ab394;"
    st.markdown(f"""
    <div class='kpi-box {cor_saldo}'>
        <div class='kpi-title-top'>Saldo do Orçamento</div>
        <div class='kpi-value-main' style='{cor_texto}'>{formatar_moeda(saldo_obra)}</div>
        <div class='kpi-subtitle'>Orçado vs Realizado</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    # Tabela Resumo
    html_tab = "<div class='table-container'><table class='table-custom'><thead><tr><th>Empreendimento / Etapa</th><th>Orçamento (R$)</th><th>Realizado (R$)</th><th>Consumo (%)</th></tr></thead><tbody>"
    for _, row in df_matriz.sort_values('Valor_Orcado', ascending=False).iterrows():
        cor_perc = "#e74a3b" if row['Consumo (%)'] > 100 else "#1ab394"
        html_tab += f"<tr><td>{row['Obra']}</td><td>{formatar_moeda(row['Valor_Orcado'])}</td><td>{formatar_moeda(row['Valor_Realizado'])}</td><td style='color: {cor_perc};'>{row['Consumo (%)']:.1f}%</td></tr>"
    html_tab += f"<tr><td>TOTAL GERAL</td><td>{formatar_moeda(total_orcado)}</td><td>{formatar_moeda(total_realizado)}</td><td>{perc_concluido:.1f}%</td></tr>"
    html_tab += "</tbody></table></div>"
    st.markdown(html_tab, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- LINHA 2: Gráficos de Barras ---
col_bar1, col_bar2 = st.columns(2)

df_barras = df_matriz.sort_values('Valor_Orcado', ascending=True)

with col_bar1:
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Orçamento por Empreendimento (R$)</div>", unsafe_allow_html=True)
    fig_orc = px.bar(df_barras, x='Valor_Orcado', y='Obra', orientation='h', text='Valor_Orcado')
    fig_orc.update_traces(marker_color='#1ab394', texttemplate='%{text:,.0f}', textposition='outside', textfont=dict(color='#2c3e50', size=11))
    fig_orc.update_layout(height=280, margin=dict(l=0, r=40, t=10, b=0), xaxis=dict(visible=False), yaxis=dict(title=""), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_orc, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_bar2:
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Custo Realizado por Empreendimento (R$)</div>", unsafe_allow_html=True)
    df_barras_real = df_matriz.sort_values('Valor_Realizado', ascending=True)
    fig_real = px.bar(df_barras_real, x='Valor_Realizado', y='Obra', orientation='h', text='Valor_Realizado')
    fig_real.update_traces(marker_color='#1ab394', texttemplate='%{text:,.0f}', textposition='outside', textfont=dict(color='#2c3e50', size=11))
    fig_real.update_layout(height=280, margin=dict(l=0, r=40, t=10, b=0), xaxis=dict(visible=False), yaxis=dict(title=""), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_real, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

# --- LINHA 3: Curva S (Evolução Tempo) ---
st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
st.markdown("<div class='card-title'>Curva S - Orçado Acumulado vs Realizado Acumulado</div>", unsafe_allow_html=True)

# Preparando dados temporais
df_orc_temp = df_orcado.groupby('Mes')['Valor_Orcado'].sum().reset_index()
df_real_temp = df_realizado[df_realizado['Mes'] > 0].groupby('Mes')['Valor_Realizado'].sum().reset_index()

df_curva = pd.merge(pd.DataFrame({'Mes': range(1, 13)}), df_orc_temp, on='Mes', how='left')
df_curva = pd.merge(df_curva, df_real_temp, on='Mes', how='left').fillna(0)

# Calcula o Acumulado
df_curva['Orcado_Acum'] = df_curva['Valor_Orcado'].cumsum()
df_curva['Realizado_Acum'] = df_curva['Valor_Realizado'].cumsum()

# Limpa zeros nos meses futuros se não tiver realizado nada
ultimo_mes_real = df_real_temp['Mes'].max() if not df_real_temp.empty else 0
df_curva.loc[df_curva['Mes'] > ultimo_mes_real, 'Realizado_Acum'] = None

meses_str = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
df_curva['Mes_Nome'] = meses_str

fig_curva = go.Figure()
fig_curva.add_trace(go.Scatter(
    x=df_curva['Mes_Nome'], y=df_curva['Orcado_Acum'],
    mode='lines+markers', name='Orçado Acumulado',
    line=dict(color='#f6c23e', width=4),
    marker=dict(size=8)
))
fig_curva.add_trace(go.Scatter(
    x=df_curva['Mes_Nome'], y=df_curva['Realizado_Acum'],
    mode='lines+markers', name='Realizado Acumulado',
    line=dict(color='#e74a3b', width=4),
    marker=dict(size=8)
))

fig_curva.update_layout(
    height=320, 
    margin=dict(l=20, r=20, t=10, b=10),
    plot_bgcolor='rgba(0,0,0,0)', 
    paper_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    yaxis=dict(showgrid=True, gridcolor='#cbd5e1', tickprefix="R$ ")
)

st.plotly_chart(fig_curva, use_container_width=True, config={'displayModeBar': False})
st.markdown("</div>", unsafe_allow_html=True)
