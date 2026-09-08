import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import textwrap

# ==============================================================================
# 0. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Acompanhamento de Obras", layout="wide", initial_sidebar_state="expanded")

# BLINDAGEM MÁXIMA DE CONEXÃO
try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# ==============================================================================
# 1. CUSTOM CSS (ESTILO CLEAN COM LARGURAS FIXAS PARA ALINHAMENTO)
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg-main: #f4f6f9;
        --card-bg: #ffffff;
        --text-dark: #1e293b;
        --text-muted: #64748b;
        --border-color: #e2e8f0;
        --blue-main: #0284c7;
        --green-main: #10b981;
        --yellow-main: #f59e0b;
        --red-main: #ef4444;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
    }
    
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .main { background: var(--bg-main); }
    .main .block-container { padding-top: 1rem; max-width: 98%; }
    
    /* HEADER E TÍTULOS */
    .dash-header { margin-bottom: 20px; }
    .dash-header h1 { font-size: 22px; font-weight: 800; color: var(--text-dark); margin: 0; }
    .dash-header p { font-size: 12px; color: var(--text-muted); margin: 2px 0 0 0; font-weight: 500; }
    
    .section-title {
        font-size: 13px;
        font-weight: 800;
        color: var(--text-dark);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 25px 0 12px 0;
        padding-left: 10px;
        border-left: 4px solid var(--blue-main);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    /* KPIS COM CORES PASTEL */
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
    .kpi-item { border: 1px solid var(--border-color); border-radius: 8px; padding: 16px 18px; box-shadow: var(--shadow-sm); background: #ffffff; }
    .kpi-item.bg-blue { background: #f0f9ff; border-color: #bae6fd; }
    .kpi-item.bg-green { background: #f0fdf4; border-color: #bbf7d0; }
    .kpi-item.bg-yellow { background: #fefce8; border-color: #fef08a; }
    
    .kpi-title { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 22px; font-weight: 800; color: var(--text-dark); margin: 6px 0 2px 0; }
    .kpi-subtitle { font-size: 11px; font-weight: 500; color: var(--text-muted); }
    .kpi-subtitle.green { color: var(--green-main); font-weight: 600; }
    
    /* TABELA UNIFICADA DE TOTALIZADORES MÊS A MÊS */
    .unified-summary-box {
        background: #ffffff;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-shadow: var(--shadow-sm);
        margin-top: 10px;
        margin-bottom: 20px;
        overflow: hidden;
    }
    .unified-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11px;
        text-align: center;
    }
    .unified-table th {
        background: #ffffff;
        color: var(--text-dark);
        font-weight: 800;
        text-transform: uppercase;
        padding: 10px 4px;
        border-bottom: 2px solid var(--border-color);
        border-right: 1px solid var(--border-color);
    }
    .unified-table th:last-child { border-right: none; }
    .unified-table td {
        padding: 10px 4px;
        border-bottom: 1px solid var(--border-color);
        border-right: 1px solid var(--border-color);
        background: #ffffff;
    }
    .unified-table td:last-child { border-right: none; }
    .row-label {
        text-align: left;
        padding-left: 15px !important;
        font-weight: 700;
        color: var(--text-muted);
        background: #ffffff;
        width: 130px;
        border-right: 2px solid var(--border-color) !important;
    }
    .val-real { font-weight: 800; color: var(--green-main); }
    .val-orc { font-weight: 800; color: var(--blue-main); }

    /* TABELAS COM ALINHAMENTO FIXO (PERFECT SYNC) */
    .fases-table-container {
        max-height: 500px;
        overflow-y: auto;
        overflow-x: auto;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        background: #ffffff;
        box-shadow: var(--shadow-sm);
    }
    .fases-table { 
        min-width: 100%; 
        border-collapse: collapse; 
        font-size: 11px; 
        white-space: nowrap;
        background: #ffffff;
        table-layout: fixed; /* Força as larguras das colunas a serem exatas */
    }
    
    .fases-table thead { position: sticky; top: 0; z-index: 15; }
    .fases-table th { 
        background: #ffffff; 
        color: var(--text-muted); 
        font-weight: 800; 
        text-transform: uppercase; 
        padding: 12px 10px; 
        border-bottom: 2px solid var(--border-color); 
        text-align: left;
        position: sticky;
        top: 0;
        z-index: 15;
    }
    .fases-table td { 
        padding: 10px; 
        border-bottom: 1px solid var(--border-color); 
        color: var(--text-dark); 
        background: #ffffff;
    }
    
    /* Larguras cravadas para manter as duas tabelas 100% idênticas */
    .fases-table th:nth-child(1), .fases-table td:nth-child(1) { 
        width: 290px; min-width: 290px; max-width: 290px;
        position: sticky; left: 0; z-index: 10; background: #ffffff; border-right: 2px solid var(--border-color); 
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .fases-table th:nth-child(1) { z-index: 20; background: #ffffff; }

    .fases-table th:nth-child(2), .fases-table td:nth-child(2) { 
        width: 120px; min-width: 120px; max-width: 120px;
    }
    
    .fases-table th:nth-child(n+3), .fases-table td:nth-child(n+3) { 
        width: 100px; min-width: 100px; max-width: 100px;
    }

    .fases-table tr:hover td { background: #fafaf9; }
    .total-geral-row td { 
        font-weight: 900; 
        background: #ffffff !important; 
        border-top: 2px solid var(--text-dark); 
        color: var(--text-dark); 
    }

    /* COMPORTAMENTO INTERATIVO DO DRILL-DOWN (SEM JS) */
    .drilldown-label { cursor: pointer; display: flex; align-items: center; margin: 0; width: 100%; height: 100%; }
    .toggle-checkbox { display: none; }
    .indicator { margin-right: 8px; font-size: 11px; transition: transform 0.2s; display: inline-block; color: var(--blue-main); }
    
    .obra-group .sub-row { display: none; }
    .obra-group:has(.toggle-checkbox:checked) .sub-row { display: table-row; }
    .obra-group:has(.toggle-checkbox:checked) .indicator { transform: rotate(90deg); }
    
    /* INDICADOR DE ORÇAMENTO (PAGAMENTOS REALIZADOS) */
    .orcado-indicator {
        display: block;
        font-size: 9px;
        color: var(--text-muted);
        margin-top: 3px;
        font-weight: 600;
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
# ==============================================================================
def limpa_valor(valor):
    try:
        if pd.isna(valor):
            return 0.0

        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return float(valor)

        v_str = str(valor).strip()

        if v_str in ["", "-", "nan", "None", "NaN"]:
            return 0.0

        v_str = v_str.replace("R$", "").replace(" ", "")
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)

        if "," in v_str:
            v_str = v_str.replace(".", "").replace(",", ".")
        else:
            v_str = v_str.replace(",", "")

        return float(v_str)

    except (ValueError, TypeError):
        return 0.0

def formatar_moeda(valor):
    try:
        val = float(valor)
        if val == 0: 
            return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "-"

def formatar_moeda_curta(valor):
    try:
        val = float(valor)
        if val == 0:
            return "-"
        if abs(val) >= 1_000_000:
            return f"R$ {val/1_000_000:.1f}M".replace('.', ',')
        elif abs(val) >= 1_000:
            return f"R$ {val/1_000:.0f}K".replace('.', ',')
        return f"R$ {val:.0f}"
    except:
        return "-"

def extract_month(m):
    try:
        s = str(m).strip()
        if '.' in s: 
            return int(float(s.split('.')[-1]))
        return int(float(s))
    except: 
        return 0

# ==============================================================================
# 3. CARGA DOS DADOS E TRATAMENTO
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_obras_detalhado():
    conn = conectar_sheets()
    if not conn: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    try:
        # --- ORÇADO ---
        df_orc = conn.read(worksheet="Orçamento_Obra", ttl=0)
        df_orc = df_orc[df_orc['RESUMO OBRAS'].astype(str).str.upper() != 'TOTAL'].copy()
        df_orc['Obra'] = df_orc['RESUMO OBRAS'].astype(str).str.upper().str.strip()
        
        meses_cols = ['Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        meses_existentes = [m for m in meses_cols if m in df_orc.columns]
        
        df_orc_melt = df_orc.melt(id_vars=['Obra'], value_vars=meses_existentes, var_name='Mes_Nome', value_name='Valor_Orcado')
        map_meses = {'Fevereiro': 2, 'Março': 3, 'Abril': 4, 'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8, 'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12}
        df_orc_melt['Mes'] = df_orc_melt['Mes_Nome'].map(map_meses)
        df_orc_melt['Valor_Orcado'] = df_orc_melt['Valor_Orcado'].apply(limpa_valor)
        
        # --- FASES DA OBRA ---
        df_fases = pd.DataFrame()
        try:
            df_fases_raw = conn.read(worksheet="Fases_Obra", ttl=0)
            valid_cols = [c for c in df_fases_raw.columns if str(c).strip() and not str(c).strip().lower().startswith('unnamed')]
            df_fases = df_fases_raw[valid_cols].copy()
            df_fases = df_fases.replace(r'^\s*$', pd.NA, regex=True).dropna(axis=1, how='all')
        except Exception:
            df_fases = pd.DataFrame()

        # --- REALIZADO ---
        df_real = conn.read(worksheet="Realizado_Obra", ttl=0)
        df_real['Obra'] = df_real['Categoria'].astype(str).str.upper().str.strip()
        df_real['Mes'] = df_real['MÊS'].apply(extract_month)
        df_real['Valor_Realizado'] = df_real['Valor'].apply(limpa_valor)
        
        col_forn = next((c for c in df_real.columns if 'forn' in c.lower()), 'Fornecedor')
        col_nf = next((c for c in df_real.columns if 'nf' in c.lower()), 'NF')
        col_data = next((c for c in df_real.columns if 'data' in c.lower()), 'DATA PGTO')
        
        df_real['Fornecedor'] = df_real[col_forn].fillna('NÃO INFORMADO').astype(str).str.upper()
        df_real['NF'] = df_real[col_nf].fillna('-').astype(str)
        df_real['Data_Pgto'] = df_real[col_data].fillna('-').astype(str).str.replace('00:00:00', '').str.strip()
        
        return df_orc_melt, df_real, df_fases
        
    except Exception as e:
        st.error(f"Erro ao processar dados de obras: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_orcado, df_realizado, df_fases = carregar_dados_obras_detalhado()

if df_orcado.empty and df_realizado.empty:
    st.warning("Nenhum dado encontrado nas abas do banco de dados.")
    st.stop()

obras_orcadas = df_orcado['Obra'].dropna().astype(str).unique().tolist() if not df_orcado.empty else []
obras_realizadas = df_realizado['Obra'].dropna().astype(str).unique().tolist() if not df_realizado.empty else []
todas_obras = set(obras_orcadas) | set(obras_realizadas)
lista_obras = sorted([o for o in todas_obras if o.strip() not in ['NAN', '0', '', 'DIVERSAS', 'SEGUROS']])

# ==============================================================================
# 4. BARRA LATERAL 
# ==============================================================================
with st.sidebar:
    st.markdown("### Filtros do Painel")
    mes_selecionado = st.selectbox("Mês de Análise (Acumulado)", options=["Todos"] + list(range(2, 13)), format_func=lambda x: f"Até Mês {x:02d}" if isinstance(x, int) else x)
    obra_selecionada = st.selectbox("Empreendimento / Obra", ["Todas"] + lista_obras)
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    if st.button("Limpar Filtros Aplicados", use_container_width=True):
        st.rerun()

# Aplicação de Filtros Globais
df_orc_filtrado = df_orcado.copy()
df_real_filtrado = df_realizado.copy()
df_fases_filtrado = df_fases.copy()

if mes_selecionado != "Todos":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Mes'] <= mes_selecionado]
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Mes'] <= mes_selecionado]

if obra_selecionada != "Todas":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Obra'] == obra_selecionada]
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Obra'] == obra_selecionada]
    if not df_fases_filtrado.empty:
        col_o_f = df_fases_filtrado.columns[0]
        df_fases_filtrado = df_fases_filtrado[df_fases_filtrado[col_o_f].astype(str).str.upper().str.strip() == obra_selecionada]

# ==============================================================================
# 5. CÁLCULOS E ANÁLISE MÊS A MÊS (MoM)
# ==============================================================================
total_orcado = df_orc_filtrado['Valor_Orcado'].sum()
total_realizado = df_real_filtrado['Valor_Realizado'].sum()
saldo_orcamento = total_orcado - total_realizado
consumo_geral_perc = (total_realizado / total_orcado * 100) if total_orcado > 0 else 0

mes_atual = int(mes_selecionado) if mes_selecionado != "Todos" else (df_realizado['Mes'].max() if not df_realizado.empty else 0)
mes_anterior = mes_atual - 1

df_real_mom = df_realizado.copy()
if obra_selecionada != "Todas":
    df_real_mom = df_real_mom[df_real_mom['Obra'] == obra_selecionada]

realizado_atual = df_real_mom[df_real_mom['Mes'] == mes_atual]['Valor_Realizado'].sum()
realizado_anterior = df_real_mom[df_real_mom['Mes'] == mes_anterior]['Valor_Realizado'].sum()

if realizado_anterior > 0:
    mom_pct = ((realizado_atual / realizado_anterior) - 1) * 100
else:
    mom_pct = 100 if realizado_atual > 0 else 0

if mom_pct > 0:
    mom_str = f"↗ +{mom_pct:.1f}% vs Mês {mes_anterior:02d}"
    mom_color = "var(--red-main)"
elif mom_pct < 0:
    mom_str = f"↘ {mom_pct:.1f}% vs Mês {mes_anterior:02d}"
    mom_color = "var(--green-main)"
else:
    mom_str = f"→ 0.0% vs Mês {mes_anterior:02d}"
    mom_color = "var(--text-muted)"

# ==============================================================================
# 6. MONTAGEM DO LAYOUT DO DASHBOARD
# ==============================================================================
st.markdown("""
<div class='dash-header'>
    <h1>Acompanhamento de Obras</h1>
    <p>Visão geral do andamento financeiro e detalhamento de fases</p>
</div>
""", unsafe_allow_html=True)

# --- LINHA 1: KPIs COM CORES PASTEL ---
kpi_html = (
    "<div class='kpi-grid'>"
    "<div class='kpi-item bg-blue'><div class='kpi-title'>Orçamento Total do Ano</div>" + f"<div class='kpi-value'>{formatar_moeda(total_orcado)}</div><div class='kpi-subtitle'>Valor planejado</div></div>"
    "<div class='kpi-item bg-green'><div class='kpi-title'>Investimento Realizado</div>" + f"<div class='kpi-value'>{formatar_moeda(total_realizado)}</div><div class='kpi-subtitle green'>{consumo_geral_perc:.1f}% do orçado</div></div>"
    "<div class='kpi-item bg-yellow'><div class='kpi-title'>Orçamento Disponível</div>" + f"<div class='kpi-value' style='color: {'var(--red-main)' if saldo_orcamento < 0 else 'var(--text-dark)'};'>{formatar_moeda(saldo_orcamento)}</div><div class='kpi-subtitle'>Saldo disponível</div></div>"
    "<div class='kpi-item bg-blue'><div class='kpi-title'>Pagamento Mês (" + f"{mes_atual:02d}" + ")</div>" + f"<div class='kpi-value'>{formatar_moeda(realizado_atual)}</div><div class='kpi-subtitle' style='color: {mom_color}; font-weight: 600;'>{mom_str}</div></div>"
    "</div>"
)
st.markdown(kpi_html, unsafe_allow_html=True)

# ==============================================================================
# LINHA 2: GRÁFICO DE LINHA MENSAL E TABELA UNIFICADA 3 LINHAS
# ==============================================================================
df_orc_m_base = df_orcado.copy()
df_real_m_base = df_realizado[df_realizado['Mes'] > 0].copy()
if obra_selecionada != "Todas":
    df_orc_m_base = df_orc_m_base[df_orc_m_base['Obra'] == obra_selecionada]
    df_real_m_base = df_real_m_base[df_real_m_base['Obra'] == obra_selecionada]
    
df_orc_mensal = df_orc_m_base.groupby('Mes')['Valor_Orcado'].sum().reset_index()
df_real_mensal = df_real_m_base.groupby('Mes')['Valor_Realizado'].sum().reset_index()

df_linha = pd.merge(pd.DataFrame({'Mes': range(2, 13)}), df_orc_mensal, on='Mes', how='left').fillna(0)
df_linha = pd.merge(df_linha, df_real_mensal, on='Mes', how='left')

ultimo_mes_com_real = df_real_m_base['Mes'].max() if not df_real_m_base.empty else 0
df_linha.loc[df_linha['Mes'] > ultimo_mes_com_real, 'Valor_Realizado'] = None

meses_nomes = {2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
df_linha['Mes_Nome'] = df_linha['Mes'].map(meses_nomes)

st.markdown("<div class='section-title'>Evolução Mensal: Orçado vs Realizado</div>", unsafe_allow_html=True)

fig_linha = go.Figure()
fig_linha.add_trace(go.Scatter(
    x=df_linha['Mes_Nome'], y=df_linha['Valor_Orcado'],
    mode='lines+markers', name='Orçado Mensal',
    line=dict(color='#0284c7', width=3), marker=dict(size=6)
))
fig_linha.add_trace(go.Scatter(
    x=df_linha['Mes_Nome'], y=df_linha['Valor_Realizado'],
    mode='lines+markers', name='Realizado Mensal',
    line=dict(color='#10b981', width=3), marker=dict(size=6),
    connectgaps=False
))
fig_linha.update_layout(
    height=250,
    margin=dict(l=20, r=20, t=10, b=0),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
    yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickprefix="R$ ", showline=False),
    xaxis=dict(showgrid=False, showline=False, showticklabels=False, range=[-0.2, 10.2])
)
st.plotly_chart(fig_linha, use_container_width=True, config={'displayModeBar': False})

# TABELA UNIFICADA 3 LINHAS
html_unified = "<div class='unified-summary-box'><table class='unified-table'><thead><tr>"
html_unified += "<th class='row-label' style='background:#ffffff;'>Mês</th>"
for _, r in df_linha.iterrows():
    html_unified += f"<th>{r['Mes_Nome']}</th>"
html_unified += "</tr></thead><tbody>"

html_unified += "<tr><td class='row-label'>Realizado</td>"
for _, r in df_linha.iterrows():
    v_real = r['Valor_Realizado']
    val_real_str = formatar_moeda_curta(v_real) if pd.notna(v_real) else "-"
    html_unified += f"<td class='val-real'>{val_real_str}</td>"
html_unified += "</tr>"

html_unified += "<tr><td class='row-label'>Orçado</td>"
for _, r in df_linha.iterrows():
    v_orc = r['Valor_Orcado']
    html_unified += f"<td class='val-orc'>{formatar_moeda_curta(v_orc)}</td>"
html_unified += "</tr>"

html_unified += "</tbody></table></div>"
st.markdown(html_unified, unsafe_allow_html=True)

# ==============================================================================
# 7. TABELA DETALHADA DE ORÇADO X REALIZADO (FASES DA OBRA) - DRILL-DOWN NATIVO
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento do Orçado x Realizado - Fases da Obra</div>", unsafe_allow_html=True)

if not df_fases.empty:
    df_fases_view = df_fases.copy()

    if obra_selecionada != "Todas":
        col_o = df_fases_view.columns[0]
        df_fases_view = df_fases_view[df_fases_view[col_o].astype(str).str.upper().str.strip() == obra_selecionada]

    col_obra = df_fases_view.columns[0]
    col_fase = df_fases_view.columns[1]
    obras_unicas = df_fases_view[col_obra].dropna().unique()

    # Filtra colunas para não mostrar '%' e renomeia 'Custo R$' para 'ORÇAMENTO R$'
    cols_to_show = []
    for col in df_fases_view.columns[2:]:
        if '%' in str(col) or 'perc' in str(col).lower():
            continue
        cols_to_show.append(col)

    # Inicia a Tabela Master 
    html_fases = "<div class='fases-table-container'><table class='fases-table'><thead><tr>"
    html_fases += f"<th>OBRA / CATEGORIA</th>"
    for col in cols_to_show:
        nome_col = "ORÇAMENTO R$" if 'custo' in str(col).lower() else col
        html_fases += f"<th style='text-align:right;'>{nome_col}</th>"
    html_fases += "</tr></thead>"
    
    totais_mensais_fases = {c: 0.0 for c in cols_to_show}

    for obra_name in obras_unicas:
        group = df_fases_view[df_fases_view[col_obra] == obra_name]
        total_row = group[group[col_fase].astype(str).str.lower().str.contains('total', na=False)]
        detail_rows = group[~group[col_fase].astype(str).str.lower().str.contains('total', na=False)]

        if not total_row.empty:
            tot_r = total_row.iloc[0]
        else:
            tot_r = group.iloc[0].copy()
            tot_r[col_fase] = "Total"
            for c in cols_to_show:
                tot_r[c] = detail_rows[c].apply(limpa_valor).sum()

        html_fases += "<tbody class='obra-group'>"

        # 1. Imprime a Linha Master (TOTAL da Obra)
        html_fases += "<tr>"
        html_fases += f"<td><label class='drilldown-label'><input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> <b>{obra_name}</b></label></td>"

        for col_name in cols_to_show:
            val = tot_r[col_name]
            try:
                num_v = limpa_valor(val)
                val_str = formatar_moeda(num_v) if num_v != 0 else "-"
                totais_mensais_fases[col_name] += num_v
            except:
                val_str = "-"
            html_fases += f"<td style='text-align:right; font-weight:800; color: var(--text-dark);'>{val_str}</td>"
        html_fases += "</tr>"

        # 2. Imprime as linhas detalhadas (Fases)
        for _, d_row in detail_rows.iterrows():
            fase_nome = d_row[col_fase]
            html_fases += "<tr class='sub-row'>"
            html_fases += f"<td title='↳ {fase_nome}' style='padding-left: 30px; font-size: 11px; color: var(--text-muted); border-right: 2px solid var(--border-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>↳ {fase_nome}</td>" 
            
            for col_name in cols_to_show:
                val = d_row[col_name]
                try:
                    num_v = limpa_valor(val)
                    val_str = formatar_moeda(num_v) if num_v != 0 else "-"
                except:
                    val_str = "-"
                html_fases += f"<td style='text-align:right; font-size: 11px; color: var(--text-muted);'>{val_str}</td>"
            html_fases += "</tr>"

        html_fases += "</tbody>"
        
    # TOTAL GERAL DO ORÇADO NO FINAL DA TABELA
    html_fases += "<tbody><tr class='total-geral-row'>"
    html_fases += "<td><b>TOTAL GERAL</b></td>"
    for col_name in cols_to_show:
        html_fases += f"<td style='text-align:right;'>{formatar_moeda(totais_mensais_fases[col_name])}</td>"
    html_fases += "</tr></tbody>"

    html_fases += "</table></div>"
    st.markdown(html_fases, unsafe_allow_html=True)
else:
    st.info("⚠️ A aba 'Fases_Obra' não foi encontrada ou está vazia no Google Sheets.")

# ==============================================================================
# 8. TABELA DE DETALHAMENTO DE PAGAMENTOS REALIZADOS COM DRILL-DOWN MENSAL NATIVO
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento de Pagamentos Realizados</div>", unsafe_allow_html=True)

df_real_detalhe = df_real_filtrado.copy()
if not df_real_detalhe.empty:
    df_real_detalhe['Valor_Realizado'] = df_real_detalhe['Valor_Realizado'].apply(limpa_valor)
    df_real_detalhe['Fornecedor'] = df_real_detalhe['Fornecedor'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
    df_real_detalhe['NF'] = df_real_detalhe['NF'].fillna('-').astype(str).str.strip()
    df_real_detalhe['Data_Pgto'] = df_real_detalhe['Data_Pgto'].fillna('-').astype(str).str.replace('00:00:00', '', regex=False).str.strip()

    map_m_inv = {2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    meses_tabela = list(map_m_inv.values())

    # Agrupa Realizado
    df_group = df_real_detalhe.groupby(['Obra', 'Mes'], as_index=False)['Valor_Realizado'].sum()
    df_matrix = df_group.pivot_table(index='Obra', columns='Mes', values='Valor_Realizado', fill_value=0)

    for m in range(2, 13):
        if m not in df_matrix.columns:
            df_matrix[m] = 0.0

    df_matrix = df_matrix[list(range(2, 13))]
    df_matrix.columns = [map_m_inv[m] for m in range(2, 13)]
    df_matrix['TOTAL'] = df_matrix.sum(axis=1)
    df_matrix = df_matrix.reset_index()

    # Tabela de Orçamento para o comparativo
    df_orc_group = df_orc_filtrado.groupby(['Obra', 'Mes'], as_index=False)['Valor_Orcado'].sum()
    df_orc_pivot = df_orc_group.pivot_table(index='Obra', columns='Mes', values='Valor_Orcado', fill_value=0)
    for m in range(2, 13):
        if m not in df_orc_pivot.columns:
            df_orc_pivot[m] = 0.0
    df_orc_pivot = df_orc_pivot[list(range(2, 13))]
    df_orc_pivot['TOTAL'] = df_orc_pivot.sum(axis=1)

    html_real = "<div class='fases-table-container'><table class='fases-table'><thead><tr>"
    html_real += "<th>OBRA / CATEGORIA</th><th style='text-align:right;'>TOTAL</th>"
    for col_m in meses_tabela:
        html_real += f"<th style='text-align:right;'>{col_m}</th>"
    html_real += "</tr></thead>"
    
    for _, row in df_matrix.iterrows():
        obra_r = row['Obra']
        tot_r = limpa_valor(row['TOTAL'])

        orc_row = df_orc_pivot.loc[obra_r] if obra_r in df_orc_pivot.index else None
        tot_orc = orc_row['TOTAL'] if orc_row is not None else 0.0

        html_real += "<tbody class='obra-group'>"
        
        # 1. Linha Master (TOTAL da Obra)
        html_real += "<tr>"
        html_real += f"<td><label class='drilldown-label'><input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> <b>{obra_r}</b></label></td>"
        html_real += f"<td style='text-align:right;'><span style='font-weight:800; color: var(--text-dark);'>{formatar_moeda(tot_r)}</span><span class='orcado-indicator'>Orç: {formatar_moeda_curta(tot_orc)}</span></td>"
        
        for m_num, col_m in zip(range(2, 13), meses_tabela):
            val_m = limpa_valor(row[col_m])
            val_orc_m = orc_row[m_num] if orc_row is not None else 0.0
            html_real += f"<td style='text-align:right;'><span style='font-weight:800; color: var(--text-dark);'>{formatar_moeda(val_m)}</span><span class='orcado-indicator'>Orç: {formatar_moeda_curta(val_orc_m)}</span></td>"
        html_real += "</tr>"

        # 2. Transações (Ocultas até o clique - alinhadas pelo Mês correspondente)
        df_trans_esp = df_real_detalhe[df_real_detalhe['Obra'] == obra_r].sort_values(['Mes', 'Fornecedor', 'Data_Pgto'])
        if not df_trans_esp.empty:
            for _, tr in df_trans_esp.iterrows():
                valor_pagamento = limpa_valor(tr['Valor_Realizado'])
                mes_ref = int(tr['Mes']) if pd.notna(tr['Mes']) else 0
                
                html_real += "<tr class='sub-row'>"
                
                # Detalhes da transação na primeira coluna
                detalhe_str = f"↳ {tr['Data_Pgto']} | {tr['Fornecedor']} | NF: {tr['NF']}"
                html_real += f"<td title='{detalhe_str}' style='padding-left: 30px; font-size: 10px; color: var(--text-muted); border-right: 2px solid var(--border-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{detalhe_str}</td>"
                
                # Coluna do TOTAL (em branco para a transação individual para não poluir)
                html_real += f"<td style='text-align:right; font-size: 10px; color: var(--text-muted);'>-</td>"
                
                # Alocação exata na coluna do mês correto
                for m_num in range(2, 13):
                    if m_num == mes_ref:
                        html_real += f"<td style='text-align:right; font-size: 10px; font-weight:600; color: var(--text-dark);'>{formatar_moeda(valor_pagamento)}</td>"
                    else:
                        html_real += f"<td style='text-align:right; font-size: 10px; color: #cbd5e1;'>-</td>"
                html_real += "</tr>"
            
        html_real += "</tbody>"
        
    # TOTAL GERAL NO RODAPÉ
    tot_geral = limpa_valor(df_matrix['TOTAL'].sum())
    tot_geral_orc = df_orc_pivot['TOTAL'].sum() if not df_orc_pivot.empty else 0.0
    
    html_real += "<tbody><tr class='total-geral-row'>"
    html_real += f"<td><b>TOTAL GERAL</b></td><td style='text-align:right;'><span style='font-weight:900;'>{formatar_moeda(tot_geral)}</span><span class='orcado-indicator'>Orç: {formatar_moeda_curta(tot_geral_orc)}</span></td>"
    
    for m_num, col_m in zip(range(2, 13), meses_tabela):
        tot_col_m = limpa_valor(df_matrix[col_m].sum())
        tot_col_orc_m = df_orc_pivot[m_num].sum() if not df_orc_pivot.empty else 0.0
        html_real += f"<td style='text-align:right;'><span style='font-weight:900;'>{formatar_moeda(tot_col_m)}</span><span class='orcado-indicator'>Orç: {formatar_moeda_curta(tot_col_orc_m)}</span></td>"
        
    html_real += "</tr></tbody></table></div>"
    
    st.markdown(html_real, unsafe_allow_html=True)
else:
    st.info("Nenhum pagamento realizado encontrado para os filtros selecionados.")
