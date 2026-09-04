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
# 1. CUSTOM CSS (ESTILO EXECUTIVO COM Z-INDEX E STICKY CORRIGIDOS)
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
    .kpi-item { border: 1px solid var(--border-color); border-radius: 8px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
    .kpi-item.bg-blue { background: #f0f9ff; border-color: #bae6fd; }
    .kpi-item.bg-green { background: #f0fdf4; border-color: #bbf7d0; }
    .kpi-item.bg-yellow { background: #fefce8; border-color: #fef08a; }
    
    .kpi-title { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 22px; font-weight: 800; color: var(--text-dark); margin: 6px 0 2px 0; }
    .kpi-subtitle { font-size: 11px; font-weight: 500; color: var(--text-muted); }
    .kpi-subtitle.green { color: var(--green-main); font-weight: 600; }
    
    /* GRÁFICO CONTAINER */
    .chart-container {
        background: #ffffff;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 18px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 20px;
    }
    
    .monthly-total-card {
        background: #f8fafc;
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 8px 2px;
        text-align: center;
    }
    .m-title { font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px; }
    .m-orc { font-size: 10px; font-weight: 800; color: var(--blue-main); }
    .m-real { font-size: 10px; font-weight: 800; color: var(--green-main); }
    
    /* TABELA DE FASES COM STICKY CORRIGIDO */
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
        width: 100%; 
        border-collapse: collapse; 
        font-size: 11px; 
        white-space: nowrap;
        background: #ffffff;
    }
    
    .fases-table thead { position: sticky; top: 0; z-index: 15; }
    .fases-table th { 
        background: #f8fafc; 
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
        border-bottom: 1px solid #f1f5f9; 
        color: var(--text-dark); 
        background: #ffffff;
    }
    
    .fases-table th:nth-child(1), .fases-table td:nth-child(1) { position: sticky; left: 0; z-index: 10; background: #ffffff; border-right: 2px solid var(--border-color); }
    .fases-table th:nth-child(1) { z-index: 20; background: #f8fafc; }
    .fases-table td:nth-child(1) { background: #ffffff; }

    .fases-table th:nth-child(2), .fases-table td:nth-child(2) { position: sticky; left: 150px; z-index: 10; background: #ffffff; border-right: 1px solid var(--border-color); }
    .fases-table th:nth-child(2) { z-index: 20; background: #f8fafc; }
    .fases-table td:nth-child(2) { background: #ffffff; }

    .fases-table th:nth-child(3), .fases-table td:nth-child(3) { position: sticky; left: 320px; z-index: 10; background: #ffffff; border-right: 1px solid var(--border-color); }
    .fases-table th:nth-child(3) { z-index: 20; background: #f8fafc; }
    .fases-table td:nth-child(3) { background: #ffffff; }

    .fases-table th:nth-child(4), .fases-table td:nth-child(4) { position: sticky; left: 440px; z-index: 10; background: #ffffff; border-right: 2px solid var(--border-color); }
    .fases-table th:nth-child(4) { z-index: 20; background: #f8fafc; }
    .fases-table td:nth-child(4) { background: #ffffff; }

    .fases-table tr:hover td { background: #f8fafc; }
    .total-geral-row td { 
        font-weight: 900; 
        background: #e2e8f0 !important; 
        border-top: 2px solid var(--border-color); 
        color: var(--text-dark); 
    }

    /* TABELA DE PAGAMENTOS REALIZADOS */
    .realizado-container {
        max-height: 450px;
        overflow-y: auto;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        background: #ffffff;
        box-shadow: var(--shadow-sm);
    }
    .realizado-table { 
        width: 100%; 
        border-collapse: collapse; 
        font-size: 11px; 
        background: #ffffff;
    }
    .realizado-table thead { position: sticky; top: 0; z-index: 15; }
    .realizado-table th { 
        background: #f8fafc; 
        color: var(--text-muted); 
        font-weight: 800; 
        text-transform: uppercase; 
        padding: 11px 10px; 
        border-bottom: 2px solid var(--border-color); 
        text-align: left;
    }
    .realizado-table td { 
        padding: 9px 10px; 
        border-bottom: 1px solid #f1f5f9; 
        color: var(--text-dark);
    }
    .realizado-table tr:hover td { background: #f8fafc; }
    .realizado-total-row {
        font-weight: 900;
        background: #f8fafc !important;
        border-top: 2px solid var(--border-color);
        color: var(--text-dark);
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
# ==============================================================================
def limpa_valor(valor):
    try:
        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan", "None"]: 
            return 0.0
        v_str = str(valor).strip().replace('R$', '')
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        if '.' in v_str and ',' in v_str:
            v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
        return float(v_str)
    except: 
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
            df_fases = conn.read(worksheet="Fases_Obra", ttl=0)
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
# LINHA 2: GRÁFICO DE LINHA MENSAL COM TOTALIZADORES MÊS A MÊS ABAIXO (VIA ST.COLUMNS)
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
st.markdown("<div class='chart-container'>", unsafe_allow_html=True)

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
    height=280,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
    yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickprefix="R$ ", showline=False),
    xaxis=dict(showgrid=False, showline=False)
)
st.plotly_chart(fig_linha, use_container_width=True, config={'displayModeBar': False})

# GRID DE TOTALIZADORES MÊS A MÊS COM ST.COLUMNS (ESTÁVEL)
cols_meses = st.columns(11)
for idx, r in df_linha.iterrows():
    m_nome = r['Mes_Nome']
    v_orc = r['Valor_Orcado']
    v_real = r['Valor_Realizado']
    val_real_str = formatar_moeda_curta(v_real) if pd.notna(v_real) else "-"
    
    with cols_meses[idx]:
        st.markdown(f"""
        <div class='monthly-total-card'>
            <div class='m-title'>{m_nome}</div>
            <div class='m-orc'>{formatar_moeda_curta(v_orc)}</div>
            <div class='m-real'>{val_real_str}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 7. TABELA DETALHADA DE ORÇADO X REALIZADO (FASES DA OBRA)
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento do Orçado x Realizado - Fases da Obra</div>", unsafe_allow_html=True)

if not df_fases.empty:
    df_fases_view = df_fases.copy()
    if obra_selecionada != "Todas":
        col_o = df_fases_view.columns[0]
        df_fases_view = df_fases_view[df_fases_view[col_o].astype(str).str.upper().str.strip() == obra_selecionada]
        
    html_fases = "<div class='fases-table-container'><table class='fases-table'><thead><tr>"
    for col in df_fases_view.columns:
        html_fases += f"<th>{col}</th>"
    html_fases += "</tr></thead><tbody>"
    
    for _, row in df_fases_view.iterrows():
        is_total = any('total' in str(val).lower() for val in row.values)
        tr_class = "total-geral-row" if is_total else ""
        html_fases += f"<tr class='{tr_class}'>"
        for i, val in enumerate(row.values):
            val_str = str(val) if pd.notna(val) else "-"
            try:
                num_v = float(val_str.replace('.', '').replace(',', '.'))
                if i != 3 and num_v > 99:
                    val_str = formatar_moeda(num_v)
                elif i == 3 and num_v <= 1:
                    val_str = f"{num_v*100:.2f}%"
            except:
                pass
            html_fases += f"<td>{val_str}</td>"
        html_fases += "</tr>"
    html_fases += "</tbody></table></div>"
    st.markdown(html_fases, unsafe_allow_html=True)
else:
    st.info("⚠️ A aba 'Fases_Obra' não foi encontrada ou está vazia no Google Sheets.")

# ==============================================================================
# 8. TABELA DE DETALHAMENTO DE PAGAMENTOS REALIZADOS
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento de Pagamentos Realizados</div>", unsafe_allow_html=True)

df_real_detalhe = df_real_filtrado.copy()
if not df_real_detalhe.empty:
    tot_real_detalhe = df_real_detalhe['Valor_Realizado'].sum()
    
    html_real = "<div class='realizado-container'><table class='realizado-table'><thead><tr>"
    html_real += "<th>Data Pgto</th><th>Obra / Categoria</th><th>Fornecedor</th><th>NF / Doc</th><th style='text-align:right;'>Valor Realizado</th>"
    html_real += "</tr></thead><tbody>"
    
    df_sorted = df_real_detalhe.sort_values(['Mes', 'Obra'], ascending=[False, True])
    
    for _, tr in df_sorted.iterrows():
        html_real += "<tr>"
        html_real += f"<td>{tr['Data_Pgto']}</td>"
        html_real += f"<td><b>{tr['Obra']}</b></td>"
        html_real += f"<td>{tr['Fornecedor']}</td>"
        html_real += f"<td>{tr['NF']}</td>"
        html_real += f"<td style='text-align:right; font-weight:600;'>{formatar_moeda(tr['Valor_Realizado'])}</td>"
        html_real += "</tr>"
    
    html_real += f"<tr class='realizado-total-row'>"
    html_real += f"<td colspan='4'>TOTAL DOS PAGAMENTOS LISTADOS</td>"
    html_real += f"<td style='text-align:right;'>{formatar_moeda(tot_real_detalhe)}</td>"
    html_real += "</tr>"
    
    html_real += "</tbody></table></div>"
    st.markdown(html_real, unsafe_allow_html=True)
else:
    st.info("Nenhum pagamento realizado encontrado para os filtros selecionados.")
