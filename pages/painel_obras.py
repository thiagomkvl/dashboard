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
# 1. CUSTOM CSS (ESTILO EXECUTIVO MODERNO - INSPIRADO NA FOTO)
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
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.04);
    }
    
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .main { background: var(--bg-main); }
    .main .block-container { padding-top: 1rem; max-width: 98%; }
    
    /* HEADER E TÍTULOS ESTILO PAINEL EXECUTIVO */
    .dash-header { margin-bottom: 20px; }
    .dash-header h1 { font-size: 22px; font-weight: 800; color: var(--text-dark); margin: 0; }
    .dash-header p { font-size: 12px; color: var(--text-muted); margin: 2px 0 0 0; font-weight: 500; }
    
    .section-title {
        font-size: 13px;
        font-weight: 800;
        color: var(--text-dark);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 15px;
        padding-left: 10px;
        border-left: 4px solid var(--blue-main);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    /* CARDS GERAIS */
    .base-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-shadow: var(--shadow-sm);
        padding: 18px;
        height: 100%;
        margin-bottom: 15px;
    }
    
    /* KPIs NO TOPO */
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
    .kpi-item { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
    .kpi-title { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 22px; font-weight: 800; color: var(--text-dark); margin: 6px 0 2px 0; }
    .kpi-subtitle { font-size: 11px; font-weight: 500; color: var(--text-muted); }
    .kpi-subtitle.green { color: var(--green-main); font-weight: 600; }
    
    /* TABELA STATUS DAS OBRAS */
    .status-table { width: 100%; border-collapse: collapse; }
    .status-table th { text-align: left; padding: 10px 8px; font-size: 10px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; border-bottom: 2px solid var(--border-color); background: #f8fafc; }
    .status-table td { padding: 12px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    .obra-name { font-size: 12px; font-weight: 700; color: var(--text-dark); }
    .linha-total-tabela td { font-weight: 800; background: #f8fafc; border-top: 2px solid var(--border-color); border-bottom: none; color: var(--text-dark); }
    
    /* BARRA DE PROGRESSO */
    .prog-container { display: flex; align-items: center; gap: 8px; }
    .prog-text { font-size: 12px; font-weight: 800; color: var(--text-dark); width: 40px; }
    .prog-bar-bg { flex-grow: 1; background: #e2e8f0; height: 6px; border-radius: 4px; overflow: hidden; }
    .prog-bar-fill { height: 100%; border-radius: 4px; }
    
    .inv-text-main { font-size: 12px; font-weight: 800; color: var(--text-dark); }
    .inv-text-sub { font-size: 10px; font-weight: 500; color: var(--text-muted); }

    /* DRILL-DOWN FORNECEDORES (DRYWALL SCROLL) */
    .scrollable-container {
        max-height: 380px;
        overflow-y: auto;
        padding-right: 5px;
    }
    .scrollable-container::-webkit-scrollbar { width: 5px; }
    .scrollable-container::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 4px; }
    
    .forn-group { margin-bottom: 12px; }
    details.forn-details { background: #f8fafc; border: 1px solid var(--border-color); border-radius: 6px; margin-bottom: 6px; overflow: hidden; }
    details.forn-details > summary { padding: 10px 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 12px; font-weight: 700; color: var(--text-dark); list-style: none; outline: none; transition: background 0.2s; }
    details.forn-details > summary::-webkit-details-marker { display: none; }
    details.forn-details > summary:hover { background: #f1f5f9; }
    details.forn-details[open] > summary { border-bottom: 1px solid var(--border-color); background: var(--card-bg); }
    
    .transacao-table { width: 100%; border-collapse: collapse; font-size: 11px; background: var(--card-bg); }
    .transacao-table th { text-align: left; padding: 6px 12px; color: var(--text-muted); font-weight: 700; border-bottom: 1px solid var(--border-color); background: #f8fafc;}
    .transacao-table td { padding: 6px 12px; color: var(--text-dark); border-bottom: 1px solid #f1f5f9; }
    .transacao-table tr:last-child td { border-bottom: none; }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
# ==============================================================================
def limpa_valor(valor):
    try:
        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan", "None"]: return 0.0
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

def formatar_moeda_curta(valor):
    return f"R$ {valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def extract_month(m):
    try:
        s = str(m).strip()
        if '.' in s: return int(float(s.split('.')[-1]))
        return int(float(s))
    except: return 0

# ==============================================================================
# 3. CARGA DOS DADOS E TRATAMENTO
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_obras_detalhado():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    
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
        
        return df_orc_melt, df_real
        
    except Exception as e:
        st.error(f"Erro ao processar dados de obras: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_orcado, df_realizado = carregar_dados_obras_detalhado()

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

if mes_selecionado != "Todos":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Mes'] <= mes_selecionado]
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Mes'] <= mes_selecionado]

if obra_selecionada != "Todas":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Obra'] == obra_selecionada]
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Obra'] == obra_selecionada]

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

# Tabela Matriz
df_orc_grp = df_orc_filtrado.groupby('Obra')['Valor_Orcado'].sum().reset_index()
df_real_grp = df_real_filtrado.groupby('Obra')['Valor_Realizado'].sum().reset_index()
df_matriz = pd.merge(df_orc_grp, df_real_grp, on='Obra', how='outer').fillna(0)
df_matriz = df_matriz[df_matriz['Obra'].isin(lista_obras)]
df_matriz['Consumo (%)'] = (df_matriz['Valor_Realizado'] / df_matriz['Valor_Orcado'] * 100).fillna(0).replace([float('inf'), float('-inf')], 0)

# ==============================================================================
# 6. MONTAGEM DO LAYOUT DO DASHBOARD
# ==============================================================================
st.markdown("""
<div class='dash-header'>
    <h1>Acompanhamento de Obras</h1>
    <p>Visão geral do andamento financeiro e controle de fornecedores</p>
</div>
""", unsafe_allow_html=True)

# --- LINHA 1: KPIs ---
kpi_html = (
    "<div class='kpi-grid'>"
    f"<div class='kpi-item'><div class='kpi-title'>Orçamento Total</div><div class='kpi-value'>{formatar_moeda(total_orcado)}</div><div class='kpi-subtitle'>Valor planejado</div></div>"
    f"<div class='kpi-item'><div class='kpi-title'>Investimento Realizado</div><div class='kpi-value'>{formatar_moeda(total_realizado)}</div><div class='kpi-subtitle green'>{consumo_geral_perc:.1f}% do orçado</div></div>"
    f"<div class='kpi-item'><div class='kpi-title'>Restante Orçamento Obra</div><div class='kpi-value' style='color: {'var(--red-main)' if saldo_orcamento < 0 else 'var(--text-dark)'};'>{formatar_moeda(saldo_orcamento)}</div><div class='kpi-subtitle'>Saldo disponível</div></div>"
    f"<div class='kpi-item'><div class='kpi-title'>Pagamento Mês ({mes_atual:02d})</div><div class='kpi-value'>{formatar_moeda(realizado_atual)}</div><div class='kpi-subtitle' style='color: {mom_color}; font-weight: 600;'>{mom_str}</div></div>"
    "</div>"
)
st.markdown(kpi_html, unsafe_allow_html=True)

# --- LINHA 2: Tabela de Status e Gráfico Donut ---
c1, c2 = st.columns([2.2, 1])

with c1:
    st.markdown("<div class='section-title'>STATUS DAS OBRAS (ORÇAMENTO VS REALIZADO)</div>", unsafe_allow_html=True)
    html_status = (
        "<div class='base-card' style='padding: 0; overflow: hidden;'>"
        "<table class='status-table'>"
        "<thead><tr><th>Obra</th><th>Orçamento Consumido</th><th>Investimento Realizado</th></tr></thead>"
        "<tbody>"
    )
    
    tot_orc_tab = df_matriz['Valor_Orcado'].sum()
    tot_real_tab = df_matriz['Valor_Realizado'].sum()
    
    for _, row in df_matriz.sort_values('Valor_Orcado', ascending=False).iterrows():
        cons = row['Consumo (%)']
        if cons < 80: bar_color = "var(--blue-main)"
        elif cons <= 100: bar_color = "var(--yellow-main)"
        else: bar_color = "var(--red-main)"
            
        html_status += (
            "<tr>"
            f"<td><div class='obra-name'>{row['Obra']}</div></td>"
            f"<td><div class='prog-container'><div class='prog-text'>{cons:.0f}%</div>"
            f"<div class='prog-bar-bg'><div class='prog-bar-fill' style='width: {min(cons, 100):.1f}%; background-color: {bar_color};'></div></div></div></td>"
            f"<td><div class='inv-text-main'>{formatar_moeda(row['Valor_Realizado'])}</div><div class='inv-text-sub'>de {formatar_moeda(row['Valor_Orcado'])}</div></td>"
            "</tr>"
        )
    
    # Linha de Total na Tabela
    cons_tot = (tot_real_tab / tot_orc_tab * 100) if tot_orc_tab > 0 else 0
    html_status += (
        f"<tr class='linha-total-tabela'>"
        f"<td>TOTAL GERAL</td>"
        f"<td><div class='prog-container'><div class='prog-text'>{cons_tot:.0f}%</div>"
        f"<div class='prog-bar-bg'><div class='prog-bar-fill' style='width: {min(cons_tot, 100):.1f}%; background-color: var(--blue-main);'></div></div></div></td>"
        f"<td><div class='inv-text-main'>{formatar_moeda(tot_real_tab)}</div><div class='inv-text-sub'>de {formatar_moeda(tot_orc_tab)}</div></td>"
        f"</tr>"
    )
    
    html_status += "</tbody></table></div>"
    st.markdown(html_status, unsafe_allow_html=True)

with c2:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO INVESTIMENTO</div>", unsafe_allow_html=True)
    st.markdown("<div class='base-card' style='padding-bottom: 0;'>", unsafe_allow_html=True)
    df_donut = df_matriz[df_matriz['Valor_Realizado'] > 0].copy()
    
    if not df_donut.empty:
        text_labels = [formatar_moeda_curta(v) for v in df_donut['Valor_Realizado']]
        fig_donut = go.Figure(data=[go.Pie(
            values=df_donut['Valor_Realizado'], 
            labels=df_donut['Obra'], 
            hole=0.6,
            textinfo='text',
            text=text_labels,
            hoverinfo='label+percent'
        )])
        fig_donut.update_layout(
            showlegend=True, 
            legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=9)),
            margin=dict(t=0, b=0, l=0, r=0), 
            height=280,
            annotations=[dict(text=f"<b>R$ {total_realizado/1000000:.1f} mi</b><br>Total", x=0.5, y=0.5, font_size=11, showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Sem dados de investimento para plotar.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- LINHA 3: Gráfico de Linha Mensal (Respeitando Filtro de Obra) & Fornecedores Lado a Lado ---
col_graf, col_forn_card = st.columns([1.5, 1])

with col_graf:
    st.markdown("<div class='section-title'>EVOLUÇÃO MENSAL: ORÇADO VS REALIZADO</div>", unsafe_allow_html=True)
    st.markdown("<div class='base-card'>", unsafe_allow_html=True)
    
    # Filtra os dataframes mensais respeitando a obra selecionada na barra lateral
    df_orc_m_base = df_orcado.copy()
    df_real_m_base = df_realizado[df_realizado['Mes'] > 0].copy()
    if obra_selecionada != "Todas":
        df_orc_m_base = df_orc_m_base[df_orc_m_base['Obra'] == obra_selecionada]
        df_real_m_base = df_real_m_base[df_real_m_base['Obra'] == obra_selecionada]
        
    df_orc_mensal = df_orc_m_base.groupby('Mes')['Valor_Orcado'].sum().reset_index()
    df_real_mensal = df_real_m_base.groupby('Mes')['Valor_Realizado'].sum().reset_index()
    
    df_linha = pd.merge(pd.DataFrame({'Mes': range(2, 13)}), df_orc_mensal, on='Mes', how='left').fillna(0)
    df_linha = pd.merge(df_linha, df_real_mensal, on='Mes', how='left')
    
    # Remove o zero do realizado nos meses futuros onde não houve transações para evitar distorção na linha
    ultimo_mes_com_real = df_real_m_base['Mes'].max() if not df_real_m_base.empty else 0
    df_linha.loc[df_linha['Mes'] > ultimo_mes_com_real, 'Valor_Realizado'] = None
    
    meses_nomes = {2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df_linha['Mes_Nome'] = df_linha['Mes'].map(meses_nomes)
    
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
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickprefix="R$ ")
    )
    st.plotly_chart(fig_linha, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_forn_card:
    st.markdown("<div class='section-title'><span>TOTAL DE PAGAMENTOS POR FORNECEDOR</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='base-card'>", unsafe_allow_html=True)
    
    # Filtro interno opcional pré-selecionado para a tabela de fornecedores
    obras_disponiveis_forn = ["Todas"] + lista_obras
    default_idx = obras_disponiveis_forn.index(obra_selecionada) if obra_selecionada in obras_disponiveis_forn else 0
    obra_filtro_forn = st.selectbox("Filtrar Fornecedores por Obra:", options=obras_disponiveis_forn, index=default_idx, key="select_obra_forn")
    
    df_drill = df_real_filtrado.copy()
    if obra_filtro_forn != "Todas":
        df_drill = df_drill[df_drill['Obra'] == obra_filtro_forn]
        
    df_drill = df_drill[df_drill['Obra'].isin(lista_obras)]
    
    if not df_drill.empty:
        html_forn = "<div class='scrollable-container'>"
        for obra in sorted(df_drill['Obra'].unique()):
            df_obra = df_drill[df_drill['Obra'] == obra]
            html_forn += f"<div class='forn-group'><div style='font-size:11px; font-weight:800; color:var(--blue-main); margin-bottom:6px;'>{obra}</div>"
            
            fornecedores_soma = df_obra.groupby('Fornecedor')['Valor_Realizado'].sum().sort_values(ascending=False)
            for forn, tot_pago in fornecedores_soma.items():
                df_forn_transacoes = df_obra[df_obra['Fornecedor'] == forn].sort_values('Mes')
                html_forn += (
                    f"<details class='forn-details'>"
                    f"<summary><span>{forn}</span><span>{formatar_moeda(tot_pago)}</span></summary>"
                    "<table class='transacao-table'><thead><tr><th>Data</th><th>NF</th><th>Mês</th><th style='text-align:right;'>Valor</th></tr></thead><tbody>"
                )
                for _, tr in df_forn_transacoes.iterrows():
                    html_forn += f"<tr><td>{tr['Data_Pgto']}</td><td>{tr['NF']}</td><td>Mês {tr['Mes']:02d}</td><td style='text-align:right; font-weight:600;'>{formatar_moeda(tr['Valor_Realizado'])}</td></tr>"
                html_forn += "</tbody></table></details>"
            html_forn += "</div>"
        html_forn += "</div>"
        st.markdown(html_forn, unsafe_allow_html=True)
    else:
        st.info("Nenhum pagamento registrado para o filtro selecionado.")
    
    st.markdown("</div>", unsafe_allow_html=True)
