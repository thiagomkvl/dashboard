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
# 1. CUSTOM CSS (VISUAL EXECUTIVO CLARO)
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg-main: #f9f9fb;
        --card-bg: #ffffff;
        --text-dark: #111827;
        --text-muted: #6b7280;
        --border-color: #e5e7eb;
        --blue-main: #3b82f6;
        --blue-soft: #eff6ff;
        --green-main: #10b981;
        --yellow-main: #f59e0b;
        --red-main: #ef4444;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .main { background: var(--bg-main); }
    .main .block-container { padding-top: 1rem; max-width: 98%; }
    
    /* HEADER E TÍTULOS */
    .dash-header { margin-bottom: 25px; }
    .dash-header h1 { font-size: 24px; font-weight: 800; color: var(--text-dark); margin: 0; }
    .dash-header p { font-size: 13px; color: var(--text-muted); margin: 2px 0 0 0; font-weight: 500; }
    
    /* CARDS GERAIS */
    .base-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        box-shadow: var(--shadow-sm);
        padding: 20px;
        height: 100%;
        margin-bottom: 20px;
    }
    .card-header { font-size: 13px; font-weight: 800; color: var(--text-dark); text-transform: uppercase; margin-bottom: 15px; display: flex; align-items: center; }
    
    /* KPIs NO TOPO */
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
    .kpi-item { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 18px 20px; box-shadow: var(--shadow-sm); position: relative; }
    .kpi-title { font-size: 11px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 24px; font-weight: 800; color: var(--text-dark); margin: 8px 0 4px 0; }
    .kpi-subtitle { font-size: 12px; font-weight: 500; color: var(--text-muted); }
    .kpi-subtitle.green { color: var(--green-main); font-weight: 600; }
    .kpi-icon { position: absolute; right: 20px; top: 50%; transform: translateY(-50%); width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold;}
    .icon-red { background: #fee2e2; color: var(--red-main); }
    .icon-green { background: #d1fae5; color: var(--green-main); }
    .icon-blue { background: #dbeafe; color: var(--blue-main); }
    
    /* TABELA STATUS DAS OBRAS */
    .status-table { width: 100%; border-collapse: collapse; }
    .status-table th { text-align: left; padding: 10px 8px; font-size: 10px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border-color); }
    .status-table td { padding: 15px 8px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
    .obra-name { font-size: 13px; font-weight: 700; color: var(--text-dark); display: flex; align-items: center; gap: 10px; }
    
    /* BARRA DE PROGRESSO (ORÇAMENTO) */
    .prog-container { display: flex; align-items: center; gap: 10px; }
    .prog-text { font-size: 13px; font-weight: 800; color: var(--text-dark); width: 45px; }
    .prog-bar-bg { flex-grow: 1; background: #e5e7eb; height: 6px; border-radius: 4px; overflow: hidden; position: relative; }
    .prog-bar-fill { height: 100%; border-radius: 4px; }
    
    /* CHIPS DE STATUS */
    .status-chip { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; text-align: center; display: inline-block; white-space: nowrap; }
    .chip-andamento { background: var(--blue-soft); color: var(--blue-main); }
    .chip-atencao { background: #fef3c7; color: var(--yellow-main); }
    .chip-estourado { background: #fee2e2; color: var(--red-main); }
    
    .inv-text-main { font-size: 13px; font-weight: 800; color: var(--text-dark); }
    .inv-text-sub { font-size: 11px; font-weight: 500; color: var(--text-muted); }

    /* DETALHAMENTO DE FORNECEDORES (DRILL-DOWN) */
    .forn-group { margin-bottom: 15px; }
    .forn-obra-title { font-size: 14px; font-weight: 800; color: var(--blue-main); margin-bottom: 10px; padding-bottom: 5px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 8px;}
    details.forn-details { background: #f9fafb; border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 8px; overflow: hidden; }
    details.forn-details > summary { padding: 12px 15px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: 700; color: var(--text-dark); list-style: none; outline: none; transition: background 0.2s; }
    details.forn-details > summary::-webkit-details-marker { display: none; }
    details.forn-details > summary:hover { background: #f3f4f6; }
    details.forn-details[open] > summary { border-bottom: 1px solid var(--border-color); background: var(--card-bg); }
    
    .transacao-table { width: 100%; border-collapse: collapse; font-size: 12px; background: var(--card-bg); }
    .transacao-table th { text-align: left; padding: 8px 15px; color: var(--text-muted); font-weight: 700; border-bottom: 1px solid var(--border-color); background: #f9fafb;}
    .transacao-table td { padding: 8px 15px; color: var(--text-dark); border-bottom: 1px solid #f3f4f6; }
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
        
        # Tratamento de colunas de detalhamento
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
    mes_selecionado = st.selectbox("Mês de Análise (Acumulado)", options=["Todos"] + list(range(1, 13)), format_func=lambda x: f"Até Mês {x:02d}" if isinstance(x, int) else x)
    obra_selecionada = st.selectbox("Empreendimento / Obra", ["Todas"] + lista_obras)
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    if st.button("Limpar Filtros Aplicados", use_container_width=True):
        st.rerun()

# Aplicação de Filtros
df_orc_filtrado = df_orcado.copy()
df_real_filtrado = df_realizado.copy()

if mes_selecionado != "Todos":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Mes'] <= mes_selecionado]
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Mes'] <= mes_selecionado]

if obra_selecionada != "Todas":
    df_orc_filtrado = df_orc_filtrado[df_orc_filtrado['Obra'] == obra_selecionada]
    df_real_filtrado = df_real_filtrado[df_real_filtrado['Obra'] == obra_selecionada]

# ==============================================================================
# 5. CÁLCULOS GERAIS
# ==============================================================================
total_orcado = df_orc_filtrado['Valor_Orcado'].sum()
total_realizado = df_real_filtrado['Valor_Realizado'].sum()
consumo_geral_perc = (total_realizado / total_orcado * 100) if total_orcado > 0 else 0
qtd_obras_ativas = len([o for o in lista_obras if (obra_selecionada == "Todas" or o == obra_selecionada)])

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
kpi_html = f"""
<div class='kpi-grid'>
    <div class='kpi-item'>
        <div class='kpi-title'>Obras em Execução</div>
        <div class='kpi-value'>{qtd_obras_ativas}</div>
        <div class='kpi-subtitle'>Projetos ativos</div>
        <div class='kpi-icon icon-red'>O</div>
    </div>
    <div class='kpi-item'>
        <div class='kpi-title'>Orçamento Total</div>
        <div class='kpi-value'>{formatar_moeda(total_orcado)}</div>
        <div class='kpi-subtitle'>Valor planejado acumulado</div>
        <div class='kpi-icon icon-red'>$</div>
    </div>
    <div class='kpi-item'>
        <div class='kpi-title'>Investimento Realizado</div>
        <div class='kpi-value'>{formatar_moeda(total_realizado)}</div>
        <div class='kpi-subtitle green'>{consumo_geral_perc:.1f}% do orçado</div>
        <div class='kpi-icon icon-green'>%</div>
    </div>
    <div class='kpi-item'>
        <div class='kpi-title'>Consumo Médio</div>
        <div class='kpi-value'>{consumo_geral_perc:.1f}%</div>
        <div class='kpi-subtitle'>Média financeira global</div>
        <div class='kpi-icon icon-blue'>M</div>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# --- LINHA 2: Tabela de Status e Gráfico Donut ---
c1, c2 = st.columns([2.2, 1])

with c1:
    html_status = """
    <div class='base-card'>
        <div class='card-header'>STATUS DAS OBRAS (ORÇAMENTO VS REALIZADO)</div>
        <table class='status-table'>
            <thead>
                <tr>
                    <th>Obra</th>
                    <th>Orçamento Consumido</th>
                    <th style='text-align:center;'>Status</th>
                    <th>Investimento Realizado</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, row in df_matriz.sort_values('Valor_Orcado', ascending=False).iterrows():
        cons = row['Consumo (%)']
        
        # Lógica de Cores e Status baseada no Consumo
        if cons < 80:
            status_txt = "Em Andamento"
            chip_class = "chip-andamento"
            bar_color = "var(--blue-main)"
        elif cons <= 100:
            status_txt = "Atenção"
            chip_class = "chip-atencao"
            bar_color = "var(--yellow-main)"
        else:
            status_txt = "Estourado"
            chip_class = "chip-estourado"
            bar_color = "var(--red-main)"
            
        html_status += f"""
            <tr>
                <td>
                    <div class='obra-name'>{row['Obra']}</div>
                </td>
                <td>
                    <div class='prog-container'>
                        <div class='prog-text'>{cons:.0f}%</div>
                        <div class='prog-bar-bg'>
                            <div class='prog-bar-fill' style='width: {min(cons, 100):.1f}%; background-color: {bar_color};'></div>
                        </div>
                    </div>
                </td>
                <td style='text-align:center;'>
                    <span class='status-chip {chip_class}'>{status_txt}</span>
                </td>
                <td>
                    <div class='inv-text-main'>{formatar_moeda(row['Valor_Realizado'])}</div>
                    <div class='inv-text-sub'>de {formatar_moeda(row['Valor_Orcado'])}</div>
                </td>
            </tr>
        """
        
    html_status += "</tbody></table></div>"
    st.markdown(html_status, unsafe_allow_html=True)

with c2:
    st.markdown("<div class='base-card' style='padding-bottom: 0;'><div class='card-header'>DISTRIBUIÇÃO DO INVESTIMENTO</div>", unsafe_allow_html=True)
    df_donut = df_matriz[df_matriz['Valor_Realizado'] > 0]
    
    if not df_donut.empty:
        fig_donut = go.Figure(data=[go.Pie(
            values=df_donut['Valor_Realizado'], 
            labels=df_donut['Obra'], 
            hole=0.6,
            textinfo='none',
            hoverinfo='label+percent'
        )])
        fig_donut.update_layout(
            showlegend=True, 
            legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
            margin=dict(t=0, b=0, l=0, r=0), 
            height=300,
            annotations=[dict(text=f"<b>R$ {total_realizado/1000000:.1f} mi</b><br>Total Realizado", x=0.5, y=0.5, font_size=12, showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Sem dados de investimento para plotar.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- LINHA 3: Pagamentos por Fornecedor (Expansível / Drill-Down) ---
st.markdown("""
<div class='base-card'>
    <div class='card-header'>TOTAL DE PAGAMENTOS REALIZADOS POR FORNECEDOR</div>
""", unsafe_allow_html=True)

df_drill = df_real_filtrado[df_real_filtrado['Obra'].isin(lista_obras)].copy()

if not df_drill.empty:
    html_forn = ""
    # Agrupa primeiro por obra para ficar organizado
    for obra in sorted(df_drill['Obra'].unique()):
        df_obra = df_drill[df_drill['Obra'] == obra]
        
        html_forn += f"<div class='forn-group'>"
        html_forn += f"<div class='forn-obra-title'>{obra}</div>"
        
        # Agrupa os fornecedores dessa obra e ordena pelo maior valor pago
        fornecedores_soma = df_obra.groupby('Fornecedor')['Valor_Realizado'].sum().sort_values(ascending=False)
        
        for forn, tot_pago in fornecedores_soma.items():
            df_forn_transacoes = df_obra[df_obra['Fornecedor'] == forn].sort_values('Mes')
            
            html_forn += f"""
            <details class='forn-details'>
                <summary>
                    <div style='display:flex; align-items:center; gap:8px;'>
                        <span style='color:var(--blue-main); font-size:16px;'>+</span>
                        <span>{forn}</span>
                    </div>
                    <span>{formatar_moeda(tot_pago)}</span>
                </summary>
                <table class='transacao-table'>
                    <thead>
                        <tr>
                            <th style='width: 20%;'>Data Pagamento</th>
                            <th style='width: 30%;'>Nota Fiscal / Doc.</th>
                            <th style='width: 20%;'>Mês Ref.</th>
                            <th style='width: 30%; text-align:right;'>Valor (R$)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for _, tr in df_forn_transacoes.iterrows():
                html_forn += f"""
                    <tr>
                        <td>{tr['Data_Pgto']}</td>
                        <td>{tr['NF']}</td>
                        <td>Mês {tr['Mes']:02d}</td>
                        <td style='text-align:right; font-weight:600;'>{formatar_moeda(tr['Valor_Realizado'])}</td>
                    </tr>
                """
            html_forn += "</tbody></table></details>"
            
        html_forn += "</div>"
    st.markdown(html_forn, unsafe_allow_html=True)
else:
    st.info("Não há pagamentos realizados para os filtros selecionados.")

st.markdown("</div>", unsafe_allow_html=True)
