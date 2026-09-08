import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import textwrap
import io

# ==============================================================================
# 0. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Acompanhamento de Obras", layout="wide", initial_sidebar_state="expanded")

try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# ==============================================================================
# 1. CUSTOM CSS (ESTILO CLEAN + BARRA DE PROGRESSO E HEATMAP)
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
    
    /* KPIS COM 5 COLUNAS */
    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }
    .kpi-item { border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; box-shadow: var(--shadow-sm); background: #ffffff; }
    .kpi-item.bg-blue { background: #f0f9ff; border-color: #bae6fd; }
    .kpi-item.bg-green { background: #f0fdf4; border-color: #bbf7d0; }
    .kpi-item.bg-yellow { background: #fefce8; border-color: #fef08a; }
    .kpi-item.bg-purple { background: #faf5ff; border-color: #e9d5ff; }
    
    .kpi-title { font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 19px; font-weight: 800; color: var(--text-dark); margin: 5px 0 2px 0; }
    .kpi-subtitle { font-size: 10px; font-weight: 500; color: var(--text-muted); }
    
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
    .unified-table { width: 100%; border-collapse: collapse; font-size: 11px; text-align: center; }
    .unified-table th { background: #ffffff; color: var(--text-dark); font-weight: 800; text-transform: uppercase; padding: 10px 4px; border-bottom: 2px solid var(--border-color); border-right: 1px solid var(--border-color); }
    .unified-table th:last-child { border-right: none; }
    .unified-table td { padding: 10px 4px; border-bottom: 1px solid var(--border-color); border-right: 1px solid var(--border-color); background: #ffffff; }
    .unified-table td:last-child { border-right: none; }
    .row-label { text-align: left; padding-left: 15px !important; font-weight: 700; color: var(--text-muted); background: #ffffff; width: 170px; border-right: 2px solid var(--border-color) !important; }
    .val-real { font-weight: 800; color: var(--green-main); }
    .val-orc { font-weight: 800; color: var(--blue-main); }

    /* TABELAS COM ALINHAMENTO FIXO */
    .fases-table-container {
        max-height: 500px; overflow-y: auto; overflow-x: auto;
        border: 1px solid var(--border-color); border-radius: 8px; background: #ffffff; box-shadow: var(--shadow-sm);
    }
    .fases-table { 
        width: 100%; border-collapse: collapse; font-size: 11px; white-space: nowrap; background: #ffffff; table-layout: fixed; 
    }
    .fases-table thead { position: sticky; top: 0; z-index: 15; }
    .fases-table th { 
        background: #ffffff; color: var(--text-muted); font-weight: 800; text-transform: uppercase; padding: 12px 10px; border-bottom: 2px solid var(--border-color); text-align: left; position: sticky; top: 0; z-index: 15; 
    }
    .fases-table td { padding: 10px; border-bottom: 1px solid var(--border-color); color: var(--text-dark); background: #ffffff; }
    
    .fases-table th:nth-child(1), .fases-table td:nth-child(1) { 
        width: 300px; min-width: 300px; max-width: 300px; position: sticky; left: 0; z-index: 10; background: #ffffff; border-right: 2px solid var(--border-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .fases-table th:nth-child(1) { z-index: 20; background: #ffffff; }
    .fases-table th:nth-child(2), .fases-table td:nth-child(2) { width: 140px; min-width: 140px; max-width: 140px; }
    .fases-table th:nth-child(n+3), .fases-table td:nth-child(n+3) { width: 110px; min-width: 110px; max-width: 110px; }
    .fases-table tr:hover td { background: #fafaf9; }
    .total-geral-row td { font-weight: 900; background: #ffffff !important; border-top: 2px solid var(--text-dark); color: var(--text-dark); }

    /* DRILL-DOWN */
    .drilldown-label { cursor: pointer; display: flex; align-items: center; margin: 0; width: 100%; height: 100%; }
    .toggle-checkbox { display: none; }
    .indicator { margin-right: 8px; font-size: 11px; transition: transform 0.2s; display: inline-block; color: var(--blue-main); }
    .obra-group .sub-row { display: none; }
    .obra-group:has(.toggle-checkbox:checked) .sub-row { display: table-row; }
    .obra-group:has(.toggle-checkbox:checked) .indicator { transform: rotate(90deg); }
    .orcado-indicator { display: block; font-size: 9px; color: var(--text-muted); margin-top: 3px; font-weight: 600; }
    
    /* BOTÃO DOWNLOAD */
    [data-testid="stDownloadButton"] button { height: 32px; padding: 0 12px; font-size: 11px; }
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
    except Exception:
        return 0.0

def formatar_moeda(valor):
    try:
        val = float(valor)
        if val == 0:
            return "-"
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
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
    except Exception:
        return "-"

def extract_month(m):
    try:
        s = str(m).strip()
        if '.' in s:
            return int(float(s.split('.')[-1]))
        return int(float(s))
    except Exception:
        return 0

# ==============================================================================
# 3. CARGA DOS DADOS E TRATAMENTO
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_obras_detalhado():
    conn = conectar_sheets()
    if not conn:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
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

        # --- RECURSOS DA OBRA ---
        df_recursos = pd.DataFrame()
        try:
            df_recursos_raw = conn.read(worksheet="Recursos_Obra", ttl=0)
            valid_cols_rec = [c for c in df_recursos_raw.columns if str(c).strip() and not str(c).strip().lower().startswith('unnamed')]
            df_recursos = df_recursos_raw[valid_cols_rec].copy()
        except Exception:
            df_recursos = pd.DataFrame()

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
        return df_orc_melt, df_real, df_fases, df_recursos
    except Exception as e:
        st.error(f"Erro ao processar dados de obras: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_orcado, df_realizado, df_fases, df_recursos = carregar_dados_obras_detalhado()
if df_orcado.empty and df_realizado.empty:
    st.warning("Nenhum dado encontrado nas abas do banco de dados.")
    st.stop()

obras_orcadas = df_orcado['Obra'].dropna().astype(str).unique().tolist() if not df_orcado.empty else []
obras_realizadas = df_realizado['Obra'].dropna().astype(str).unique().tolist() if not df_realizado.empty else []
todas_obras = set(obras_orcadas) | set(obras_realizadas)
lista_obras = sorted([o for o in todas_obras if o.strip() not in ['NAN', '0', '', 'DIVERSAS', 'SEGUROS']])

# ==============================================================================
# 4. BARRA LATERAL E FILTROS
# ==============================================================================
df_orc_filtrado = df_orcado.copy()
df_real_filtrado = df_realizado.copy()
df_fases_filtrado = df_fases.copy()

with st.sidebar:
    st.markdown("### Filtros do Painel")
    mes_selecionado = st.selectbox("Mês de Análise (Acumulado)", options=["Todos"] + list(range(2, 13)), format_func=lambda x: f"Até Mês {x:02d}" if isinstance(x, int) else x)
    obra_selecionada = st.selectbox("Empreendimento / Obra", ["Todas"] + lista_obras)
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    if st.button("Limpar Filtros Aplicados", use_container_width=True):
        st.rerun()

    if mes_selecionado != "Todos":
        df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Mes'] <= mes_selecionado]
        df_real_filtrado = df_real_filtrado[df_real_filtrado['Mes'] <= mes_selecionado]
    if obra_selecionada != "Todas":
        df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Obra'] == obra_selecionada]
        df_real_filtrado = df_real_filtrado[df_real_filtrado['Obra'] == obra_selecionada]
        if not df_fases_filtrado.empty:
            col_o_f = df_fases_filtrado.columns[0]
            df_fases_filtrado = df_fases_filtrado[df_fases_filtrado[col_o_f].astype(str).str.upper().str.strip() == obra_selecionada]

    st.markdown("### Relatórios")
    df_real_detalhe_exp = df_real_filtrado.copy()
    if not df_real_detalhe_exp.empty:
        df_real_detalhe_exp['Valor_Realizado'] = df_real_detalhe_exp['Valor_Realizado'].apply(limpa_valor)
        df_real_detalhe_exp['Fornecedor'] = df_real_detalhe_exp['Fornecedor'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
        df_real_detalhe_exp['NF'] = df_real_detalhe_exp['NF'].fillna('-').astype(str).str.strip()
        df_real_detalhe_exp['Data_Pgto'] = df_real_detalhe_exp['Data_Pgto'].fillna('-').astype(str).str.replace('00:00:00', '', regex=False).str.strip()

    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        if not df_fases_filtrado.empty:
            df_fases_filtrado.to_excel(writer, sheet_name='Fases_Obra', index=False)
        if not df_real_detalhe_exp.empty:
            df_real_detalhe_exp.to_excel(writer, sheet_name='Transacoes_Realizadas', index=False)
        if not df_orc_filtrado.empty:
            df_orc_filtrado.to_excel(writer, sheet_name='Orcado_Mensal', index=False)
        if not df_recursos.empty:
            df_recursos.to_excel(writer, sheet_name='Recursos_Obra', index=False)
    relatorio_bytes = output_excel.getvalue()

    st.download_button(
        label="📥 Baixar Relatório Completo",
        data=relatorio_bytes,
        file_name="relatorio_detalhado_obras.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ==============================================================================
# 5. CÁLCULOS E ANÁLISE (MoM) E BARRA DE PROGRESSO
# ==============================================================================
total_orcado = df_orc_filtrado['Valor_Orcado'].sum()
total_realizado = df_real_filtrado['Valor_Realizado'].sum()
saldo_orcamento = total_orcado - total_realizado
consumo_geral_perc = (total_realizado / total_orcado * 100) if total_orcado > 0 else 0

caixa_inicial_base = 10_000_000.0
if not df_recursos.empty:
    col_rec = next((c for c in df_recursos.columns if 'recurso' in c.lower() or 'alocado' in c.lower()), None)
    if col_rec:
        val_rec = df_recursos[col_rec].apply(limpa_valor).sum()
        if val_rec > 0:
            caixa_inicial_base = val_rec

caixa_disponivel = caixa_inicial_base - total_realizado

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

pb_width = min(consumo_geral_perc, 100)
pb_color = "var(--red-main)" if consumo_geral_perc > 100 else "var(--green-main)"
html_pb = f"<div style='width: 100%; background: #e2e8f0; height: 6px; border-radius: 3px; margin-top: 6px; overflow: hidden;'><div style='width: {pb_width}%; background: {pb_color}; height: 100%; border-radius: 3px;'></div></div>"

saldo_color = "var(--red-main)" if saldo_orcamento < 0 else "var(--text-dark)"
caixa_disp_color = "var(--red-main)" if caixa_disponivel < 0 else "var(--green-main)"

# ==============================================================================
# 6. MONTAGEM DO LAYOUT (KPIs E GRÁFICOS ANALÍTICOS)
# ==============================================================================
st.markdown("""
<div class='dash-header'>
    <h1>Acompanhamento de Obras</h1>
    <p>Painel de Gestão Analítica e Execução Orçamentária</p>
</div>
""", unsafe_allow_html=True)

kpi_html = f"""
<div class='kpi-grid'>
    <div class='kpi-item bg-blue'>
        <div class='kpi-title'>Orçamento Total Obra</div>
        <div class='kpi-value'>{formatar_moeda(total_orcado)}</div>
        <div class='kpi-subtitle'>Valor planejado atualizado</div>
    </div>
    <div class='kpi-item bg-purple'>
        <div class='kpi-title'>Recursos Alocados</div>
        <div class='kpi-value'>{formatar_moeda(caixa_inicial_base)}</div>
        <div class='kpi-subtitle'>Capital alocado inicial</div>
    </div>
    <div class='kpi-item bg-green'>
        <div class='kpi-title'>Orçamento Utilizado</div>
        <div class='kpi-value'>{formatar_moeda(total_realizado)}</div>
        <div class='kpi-subtitle' style='color:{pb_color}; font-weight:600;'>{consumo_geral_perc:.1f}% do orçado</div>
        {html_pb}
    </div>
    <div class='kpi-item bg-yellow'>
        <div class='kpi-title'>Orçamento Restante</div>
        <div class='kpi-value' style='color: {saldo_color};'>{formatar_moeda(saldo_orcamento)}</div>
        <div class='kpi-subtitle'>Para finalização da obra</div>
    </div>
    <div class='kpi-item bg-blue'>
        <div class='kpi-title'>Caixa Disponível</div>
        <div class='kpi-value' style='color: {caixa_disp_color};'>{formatar_moeda(caixa_disponivel)}</div>
        <div class='kpi-subtitle'>Saldo atual em caixa</div>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

df_orc_m_base = df_orcado.copy()
df_real_m_base = df_realizado[df_realizado['Mes'] > 0].copy()
if obra_selecionada != "Todas":
    df_orc_m_base = df_orc_m_base[df_orc_m_base['Obra'] == obra_selecionada]
    df_real_m_base = df_real_m_base[df_real_m_base['Obra'] == obra_selecionada]
    
df_orc_mensal = df_orc_m_base.groupby('Mes')['Valor_Orcado'].sum().reset_index()
df_real_mensal = df_real_m_base.groupby('Mes')['Valor_Realizado'].sum().reset_index()

df_linha = pd.merge(pd.DataFrame({'Mes': range(2, 13)}), df_orc_mensal, on='Mes', how='left').fillna(0)
df_linha = pd.merge(df_linha, df_real_mensal, on='Mes', how='left')
df_linha.loc[df_linha['Mes'] > (df_real_m_base['Mes'].max() if not df_real_m_base.empty else 0), 'Valor_Realizado'] = None
meses_nomes = {2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
df_linha['Mes_Nome'] = df_linha['Mes'].map(meses_nomes)

st.markdown("<div class='section-title'>Evolução Mensal: Orçado vs Realizado</div>", unsafe_allow_html=True)
fig_linha = go.Figure()
fig_linha.add_trace(go.Scatter(x=df_linha['Mes_Nome'], y=df_linha['Valor_Orcado'], mode='lines+markers', name='Orçado Mensal', line=dict(color='#0284c7', width=3), marker=dict(size=6)))
fig_linha.add_trace(go.Scatter(x=df_linha['Mes_Nome'], y=df_linha['Valor_Realizado'], mode='lines+markers', name='Realizado Mensal', line=dict(color='#10b981', width=3), marker=dict(size=6), connectgaps=False))
fig_linha.update_layout(height=250, margin=dict(l=20, r=20, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)), yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickprefix="R$ ", showline=False), xaxis=dict(showgrid=False, showline=False, showticklabels=False, range=[-0.2, 10.2]))
st.plotly_chart(fig_linha, use_container_width=True, config={'displayModeBar': False})

html_unified = "<div class='unified-summary-box'><table class='unified-table'><thead><tr><th class='row-label' style='background:#ffffff;'>Mês</th>"
for _, r in df_linha.iterrows():
    html_unified += f"<th>{r['Mes_Nome']}</th>"
html_unified += "</tr></thead><tbody><tr><td class='row-label'>Realizado</td>"
for _, r in df_linha.iterrows():
    val_disp = formatar_moeda_curta(r['Valor_Realizado']) if pd.notna(r['Valor_Realizado']) else '-'
    html_unified += f"<td class='val-real'>{val_disp}</td>"
html_unified += "</tr><tr><td class='row-label'>Orçado</td>"
for _, r in df_linha.iterrows():
    html_unified += f"<td class='val-orc'>{formatar_moeda_curta(r['Valor_Orcado'])}</td>"
html_unified += "</tr></tbody></table></div>"
st.markdown(html_unified, unsafe_allow_html=True)

col_g1, col_g2 = st.columns(2)
with col_g1:
    st.markdown("<div style='font-size:12px; font-weight:700; color:var(--text-dark); margin-bottom:10px;'>DISTRIBUIÇÃO DE CUSTO POR OBRA (TOTAL REALIZADO)</div>", unsafe_allow_html=True)
    df_donut = df_real_filtrado.groupby('Obra')['Valor_Realizado'].sum().reset_index()
    if not df_donut.empty:
        fig_donut = px.pie(df_donut, names='Obra', values='Valor_Realizado', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_donut.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=280, showlegend=True, legend=dict(orientation="v", yanchor="auto", y=0.5, xanchor="left", x=1.0))
        st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
with col_g2:
    st.markdown("<div style='font-size:12px; font-weight:700; color:var(--text-dark); margin-bottom:10px;'>CONSUMO DE CAIXA MENSAL POR OBRA</div>", unsafe_allow_html=True)
    df_stack = df_real_filtrado.groupby(['Mes', 'Obra'])['Valor_Realizado'].sum().reset_index()
    if not df_stack.empty:
        df_stack['Mes_Nome'] = df_stack['Mes'].map(meses_nomes)
        df_stack = df_stack.sort_values('Mes')
        
        df_stack_tot = df_stack.groupby(['Mes', 'Mes_Nome'])['Valor_Realizado'].sum().reset_index()
        
        fig_stack = px.bar(df_stack, x='Mes_Nome', y='Valor_Realizado', color='Obra', color_discrete_sequence=px.colors.qualitative.Pastel)
        
        fig_stack.add_trace(go.Scatter(
            x=df_stack_tot['Mes_Nome'],
            y=df_stack_tot['Valor_Realizado'],
            text=df_stack_tot['Valor_Realizado'].apply(formatar_moeda_curta),
            mode='text',
            textposition='top center',
            showlegend=False,
            textfont=dict(size=10, color='#1e293b', family='Inter')
        ))
        
        fig_stack.update_layout(margin=dict(l=0, r=0, t=20, b=10), height=280, showlegend=False, plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickprefix="R$ "), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_stack, use_container_width=True, config={'displayModeBar': False})

# ==============================================================================
# 6.1 FLUXO DE CAIXA DA OBRA (COM DRILLDOWN NAS SAÍDAS E PROJEÇÃO INTELIGENTE)
# ==============================================================================
st.markdown("<div class='section-title'>Fluxo de Caixa da Obra (Realizado vs Projetado)</div>", unsafe_allow_html=True)

saidas_real_dict = df_real_m_base.groupby('Mes')['Valor_Realizado'].sum().to_dict()
saidas_orc_dict = df_orc_m_base.groupby('Mes')['Valor_Orcado'].sum().to_dict()
max_mes_realizado = df_real_m_base['Mes'].max() if not df_real_m_base.empty else 0

obras_fluxo = sorted(df_real_m_base['Obra'].unique().tolist() if not df_real_m_base.empty else list(todas_obras))
if obra_selecionada != "Todas":
    obras_fluxo = [obra_selecionada]

real_por_obra_mes = df_real_m_base.groupby(['Mes', 'Obra'])['Valor_Realizado'].sum().to_dict()
orc_por_obra_mes = df_orc_m_base.groupby(['Mes', 'Obra'])['Valor_Orcado'].sum().to_dict()

s_ini_list = []
saidas_tot_list = []
s_fim_list = []

curr_saldo = caixa_inicial_base
for m in range(2, 13):
    s_ini_list.append(curr_saldo)
    if m <= max_mes_realizado:
        saida_m = saidas_real_dict.get(m, 0.0)
    else:
        saida_m = saidas_orc_dict.get(m, 0.0)
    saidas_tot_list.append(saida_m)
    curr_saldo = curr_saldo - saida_m
    s_fim_list.append(curr_saldo)

html_fluxo = "<div class='unified-summary-box'><table class='unified-table'><thead><tr><th class='row-label' style='background:#ffffff;'>Fluxo de Caixa</th>"
for m_num in range(2, 13):
    html_fluxo += f"<th>{meses_nomes[m_num]}</th>"
html_fluxo += "</tr></thead><tbody>"

html_fluxo += "<tr><td class='row-label'>Saldo Inicial</td>"
for val in s_ini_list:
    html_fluxo += f"<td>{formatar_moeda_curta(val)}</td>"
html_fluxo += "</tr>"

html_fluxo += "<tbody class='obra-group'><tr>"
html_fluxo += f"<td class='row-label'><label class='drilldown-label' style='padding-left:0;'><input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> <b>(-) Saídas Totais</b></label></td>"
for val in saidas_tot_list:
    html_fluxo += f"<td style='color: var(--red-main); font-weight:800;'>{formatar_moeda_curta(val)}</td>"
html_fluxo += "</tr>"

for obra_name in obras_fluxo:
    html_fluxo += f"<tr class='sub-row'><td class='row-label' style='padding-left: 28px; font-size: 10px; font-weight: normal; color: var(--text-muted); border-right: 2px solid var(--border-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>↳ {obra_name}</td>"
    for m_num in range(2, 13):
        if m_num <= max_mes_realizado:
            v_obra = real_por_obra_mes.get((m_num, obra_name), 0.0)
        else:
            v_obra = orc_por_obra_mes.get((m_num, obra_name), 0.0)
        
        v_str = formatar_moeda_curta(v_obra) if v_obra > 0 else "-"
        html_fluxo += f"<td style='text-align:right; font-size: 10px; color: var(--text-muted);'>{v_str}</td>"
    html_fluxo += "</tr>"
html_fluxo += "</tbody>"

html_fluxo += "<tr><td class='row-label' style='font-weight: 800;'>(=) Saldo Final</td>"
for m_num, val in enumerate(s_fim_list, start=2):
    css_class = "val-real" if m_num <= max_mes_realizado else "val-orc"
    html_fluxo += f"<td class='{css_class}'><b>{formatar_moeda_curta(val)}</b></td>"
html_fluxo += "</tr>"

html_fluxo += "</tbody></table></div>"
st.markdown(html_fluxo, unsafe_allow_html=True)

st.markdown("<hr style='border: none; border-top: 2px dashed var(--border-color); margin: 30px 0;'>", unsafe_allow_html=True)

# ==============================================================================
# 7. TABELA DETALHADA DE FASES DA OBRA
# ==============================================================================
st.markdown("<div class='section-title' style='margin-top:0;'>Detalhamento do Orçado x Realizado - Fases da Obra</div>", unsafe_allow_html=True)

if not df_fases.empty:
    df_fases_view = df_fases.copy()
    if obra_selecionada != "Todas":
        col_o = df_fases_view.columns[0]
        df_fases_view = df_fases_view[df_fases_view[col_o].astype(str).str.upper().str.strip() == obra_selecionada]

    col_obra, col_fase = df_fases_view.columns[0], df_fases_view.columns[1]
    obras_unicas = df_fases_view[col_obra].dropna().unique()

    cols_to_show = [c for c in df_fases_view.columns[2:] if not ('%' in str(c) or 'perc' in str(c).lower() or str(c).strip().upper() == 'TOTAL')]
    col_orcamento_principal = cols_to_show[0] if cols_to_show else df_fases_view.columns[2]

    obra_totals_calc = []
    totais_mensais_fases = {c: 0.0 for c in cols_to_show}
    fases_group_data = {}

    for obra_name in obras_unicas:
        group = df_fases_view[df_fases_view[col_obra] == obra_name]
        total_row = group[group[col_fase].astype(str).str.lower().str.contains('total', na=False)]
        detail_rows = group[~group[col_fase].astype(str).str.lower().str.contains('total', na=False)]
        
        if not total_row.empty:
            tot_r = total_row.iloc[0]
            val_total_obra = limpa_valor(tot_r[col_orcamento_principal])
        else:
            tot_r = group.iloc[0].copy()
            tot_r[col_fase] = "Total"
            val_total_obra = 0.0
            for c in cols_to_show:
                soma_col = detail_rows[c].apply(limpa_valor).sum()
                tot_r[c] = soma_col
                if c == col_orcamento_principal:
                    val_total_obra = soma_col
                    
        obra_totals_calc.append((obra_name, val_total_obra))
        fases_group_data[obra_name] = {'tot_r': tot_r, 'detail_rows': detail_rows}

    obra_totals_calc.sort(key=lambda x: x[1], reverse=True)
    obras_unicas_sorted = [x[0] for x in obra_totals_calc]

    html_fases = "<div class='fases-table-container'><table class='fases-table'><thead><tr><th>OBRA / CATEGORIA</th>"
    for col in cols_to_show:
        col_lbl = 'ORÇAMENTO R$' if 'custo' in str(col).lower() else col
        html_fases += f"<th style='text-align:right;'>{col_lbl}</th>"
    html_fases += "</tr></thead>"

    for obra_name in obras_unicas_sorted:
        data = fases_group_data[obra_name]
        tot_r, detail_rows = data['tot_r'], data['detail_rows']
        html_fases += "<tbody class='obra-group'><tr>"
        html_fases += f"<td><label class='drilldown-label'><input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> <b>{obra_name}</b></label></td>"
        for col_name in cols_to_show:
            val = tot_r[col_name]
            try:
                num_v = limpa_valor(val)
                val_str = formatar_moeda(num_v) if num_v != 0 else "-"
                totais_mensais_fases[col_name] += num_v
            except Exception:
                val_str = "-"
            html_fases += f"<td style='text-align:right; font-weight:800; color: var(--text-dark);'>{val_str}</td>"
        html_fases += "</tr>"

        for _, d_row in detail_rows.iterrows():
            fase_nome = d_row[col_fase]
            html_fases += "<tr class='sub-row'>"
            html_fases += f"<td title='↳ {fase_nome}' style='padding-left: 30px; font-size: 11px; color: var(--text-muted); border-right: 2px solid var(--border-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>↳ {fase_nome}</td>" 
            for col_name in cols_to_show:
                val = d_row[col_name]
                try:
                    num_v = limpa_valor(val)
                    val_str = formatar_moeda(num_v) if num_v != 0 else "-"
                except Exception:
                    val_str = "-"
                html_fases += f"<td style='text-align:right; font-size: 11px; color: var(--text-muted);'>{val_str}</td>"
            html_fases += "</tr>"
        html_fases += "</tbody>"
        
    html_fases += "<tbody><tr class='total-geral-row'><td><b>TOTAL GERAL</b></td>"
    for col_name in cols_to_show:
        html_fases += f"<td style='text-align:right;'>{formatar_moeda(totais_mensais_fases[col_name])}</td>"
    html_fases += "</tr></tbody></table></div>"
    st.markdown(html_fases, unsafe_allow_html=True)
else:
    st.info("⚠️ A aba 'Fases_Obra' não foi encontrada ou está vazia no Google Sheets.")

# ==============================================================================
# 8. TABELA PAGAMENTOS (HEATMAP + ORDENAÇÃO DE PESO)
# ==============================================================================
st.write("") 
st.markdown("<div class='section-title' style='margin-top:0;'>Detalhamento de Pagamentos Realizados</div>", unsafe_allow_html=True)

df_real_detalhe = df_real_filtrado.copy()
if not df_real_detalhe.empty:
    df_real_detalhe['Valor_Realizado'] = df_real_detalhe['Valor_Realizado'].apply(limpa_valor)
    df_real_detalhe['Fornecedor'] = df_real_detalhe['Fornecedor'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
    df_real_detalhe['NF'] = df_real_detalhe['NF'].fillna('-').astype(str).str.strip()
    df_real_detalhe['Data_Pgto'] = df_real_detalhe['Data_Pgto'].fillna('-').astype(str).str.replace('00:00:00', '', regex=False).str.strip()

    map_m_inv = {2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    meses_tabela = list(map_m_inv.values())

    df_group = df_real_detalhe.groupby(['Obra', 'Mes'], as_index=False)['Valor_Realizado'].sum()
    df_matrix = df_group.pivot_table(index='Obra', columns='Mes', values='Valor_Realizado', fill_value=0)
    for m in range(2, 13):
        if m not in df_matrix.columns:
            df_matrix[m] = 0.0
    df_matrix = df_matrix[list(range(2, 13))]
    df_matrix.columns = [map_m_inv[m] for m in range(2, 13)]
    df_matrix['TOTAL'] = df_matrix.sum(axis=1)
    df_matrix = df_matrix.reset_index()
    
    df_matrix = df_matrix.sort_values(by='TOTAL', ascending=False).reset_index(drop=True)

    df_orc_group = df_orc_filtrado.groupby(['Obra', 'Mes'], as_index=False)['Valor_Orcado'].sum()
    df_orc_pivot = df_orc_group.pivot_table(index='Obra', columns='Mes', values='Valor_Orcado', fill_value=0)
    for m in range(2, 13):
        if m not in df_orc_pivot.columns:
            df_orc_pivot[m] = 0.0
    df_orc_pivot = df_orc_pivot[list(range(2, 13))]
    df_orc_pivot['TOTAL'] = df_orc_pivot.sum(axis=1)

    html_real = "<div class='fases-table-container'><table class='fases-table'><thead><tr><th>OBRA / CATEGORIA</th><th style='text-align:right;'>TOTAL</th>"
    for col_m in meses_tabela:
        html_real += f"<th style='text-align:right;'>{col_m}</th>"
    html_real += "</tr></thead>"
    
    for _, row in df_matrix.iterrows():
        obra_r = row['Obra']
        tot_r = limpa_valor(row['TOTAL'])
        orc_row = df_orc_pivot.loc[obra_r] if obra_r in df_orc_pivot.index else None
        tot_orc = orc_row['TOTAL'] if orc_row is not None else 0.0

        if tot_r > tot_orc and tot_orc > 0:
            color_tot = "#ef4444"
        elif tot_r > 0 and tot_r <= tot_orc:
            color_tot = "#10b981"
        else:
            color_tot = "var(--text-dark)"

        html_real += "<tbody class='obra-group'><tr>"
        html_real += f"<td><label class='drilldown-label'><input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> <b>{obra_r}</b></label></td>"
        html_real += f"<td style='text-align:right;'><span style='font-weight:800; color: {color_tot};'>{formatar_moeda(tot_r)}</span><span class='orcado-indicator'>Orç: {formatar_moeda_curta(tot_orc)}</span></td>"
        
        for m_num, col_m in zip(range(2, 13), meses_tabela):
            val_m = limpa_valor(row[col_m])
            val_orc_m = orc_row[m_num] if orc_row is not None else 0.0
            
            if val_m > val_orc_m and val_orc_m > 0:
                color_val = "#ef4444"
            elif val_m > 0 and val_m <= val_orc_m:
                color_val = "#10b981"
            else:
                color_val = "var(--text-dark)"
                
            html_real += f"<td style='text-align:right;'><span style='font-weight:800; color: {color_val};'>{formatar_moeda(val_m)}</span><span class='orcado-indicator'>Orç: {formatar_moeda_curta(val_orc_m)}</span></td>"
        html_real += "</tr>"

        df_trans_esp = df_real_detalhe[df_real_detalhe['Obra'] == obra_r].sort_values(['Mes', 'Fornecedor', 'Data_Pgto'])
        if not df_trans_esp.empty:
            for _, tr in df_trans_esp.iterrows():
                valor_pagamento = limpa_valor(tr['Valor_Realizado'])
                mes_ref = int(tr['Mes']) if pd.notna(tr['Mes']) else 0
                html_real += "<tr class='sub-row'>"
                detalhe_str = f"↳ {tr['Data_Pgto']} | {tr['Fornecedor']} | NF: {tr['NF']}"
                html_real += f"<td title='{detalhe_str}' style='padding-left: 30px; font-size: 10px; color: var(--text-muted); border-right: 2px solid var(--border-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{detalhe_str}</td>"
                html_real += "<td style='text-align:right; font-size: 10px; color: var(--text-muted);'>-</td>"
                for m_num in range(2, 13):
                    if m_num == mes_ref:
                        html_real += f"<td style='text-align:right; font-size: 10px; font-weight:600; color: var(--text-dark);'>{formatar_moeda(valor_pagamento)}</td>"
                    else:
                        html_real += "<td style='text-align:right; font-size: 10px; color: #cbd5e1;'>-</td>"
                html_real += "</tr>"
        html_real += "</tbody>"
        
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
