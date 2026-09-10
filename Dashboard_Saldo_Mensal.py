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
st.set_page_config(page_title="Gestão de Saldo Mensal", layout="wide", initial_sidebar_state="expanded")

try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# ==============================================================================
# 1. CUSTOM CSS (ESTILO CLEAN + DRILLDOWN)
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
    }
    
    /* KPIS GRID */
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
    .kpi-item { border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; box-shadow: var(--shadow-sm); background: #ffffff; }
    .kpi-item.bg-blue { background: #f0f9ff; border-color: #bae6fd; }
    .kpi-item.bg-green { background: #f0fdf4; border-color: #bbf7d0; }
    .kpi-item.bg-red { background: #fef2f2; border-color: #fecaca; }
    .kpi-item.bg-purple { background: #faf5ff; border-color: #e9d5ff; }
    
    .kpi-title { font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 19px; font-weight: 800; color: var(--text-dark); margin: 5px 0 2px 0; }
    .kpi-subtitle { font-size: 10px; font-weight: 500; color: var(--text-muted); }

    /* TABELA RESUMO UNIFICADA */
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

    /* TABELAS COM DRILLDOWN (FASES/CONTAS) */
    .fases-table-container {
        max-height: 500px; overflow-y: auto; overflow-x: auto;
        border: 1px solid var(--border-color); border-radius: 8px; background: #ffffff; box-shadow: var(--shadow-sm);
    }
    .fases-table { width: 100%; border-collapse: collapse; font-size: 11px; white-space: nowrap; background: #ffffff; table-layout: fixed; }
    .fases-table thead { position: sticky; top: 0; z-index: 15; }
    .fases-table th { background: #ffffff; color: var(--text-muted); font-weight: 800; text-transform: uppercase; padding: 12px 10px; border-bottom: 2px solid var(--border-color); text-align: left; position: sticky; top: 0; z-index: 15; }
    .fases-table td { padding: 10px; border-bottom: 1px solid var(--border-color); color: var(--text-dark); background: #ffffff; }
    
    .fases-table th:nth-child(1), .fases-table td:nth-child(1) { width: 280px; min-width: 280px; position: sticky; left: 0; z-index: 10; background: #ffffff; border-right: 2px solid var(--border-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .fases-table th:nth-child(1) { z-index: 20; background: #ffffff; }
    .fases-table th:nth-child(n+2), .fases-table td:nth-child(n+2) { width: 110px; min-width: 110px; }

    /* DRILLDOWN SCRIPT/TOGGLE */
    .drilldown-label { cursor: pointer; display: flex; align-items: center; margin: 0; width: 100%; height: 100%; }
    .toggle-checkbox { display: none; }
    .indicator { margin-right: 8px; font-size: 11px; transition: transform 0.2s; display: inline-block; color: var(--blue-main); }
    .obra-group .sub-row { display: none; }
    .obra-group:has(.toggle-checkbox:checked) .sub-row { display: table-row; }
    .obra-group:has(.toggle-checkbox:checked) .indicator { transform: rotate(90deg); }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES AUXILIARES DE TRATAMENTO
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

meses_nomes = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}

# ==============================================================================
# 3. CARGA DE DADOS (EXTRATOS_TASY & SALDO_INICIAL_ANO)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_saldo_mensal():
    conn = conectar_sheets()
    if not conn:
        return pd.DataFrame(), pd.DataFrame()
    try:
        # --- 1. SALDO INICIAL DO ANO ---
        df_ini = conn.read(worksheet="Saldo_Inicial_Ano", ttl=0)
        df_ini.columns = [str(c).strip() for c in df_ini.columns]
        
        col_conta_ini = next((c for c in df_ini.columns if 'CONTA' in c.upper() or 'BANCO' in c.upper()), df_ini.columns[0])
        col_saldo_ini = next((c for c in df_ini.columns if 'SALDO' in c.upper() or 'VALOR' in c.upper()), df_ini.columns[1])
        
        df_ini['Conta'] = df_ini[col_conta_ini].fillna('DIVERSAS').astype(str).str.strip().str.upper()
        df_ini['Saldo_Inicial'] = df_ini[col_saldo_ini].apply(limpa_valor)

        # --- 2. EXTRATOS TASY (MOVIMENTAÇÕES) ---
        df_ext = conn.read(worksheet="Extratos_Tasy", ttl=0)
        df_ext.columns = [str(c).strip() for c in df_ext.columns]
        
        col_conta_ext = next((c for c in df_ext.columns if 'CONTA' in c.upper() or 'BANCO' in c.upper()), df_ext.columns[0])
        col_mes_ext = next((c for c in df_ext.columns if 'MÊS' in c.upper() or 'MES' in c.upper() or 'DATA' in c.upper()), None)
        col_ent_ext = next((c for c in df_ext.columns if 'ENTRADA' in c.upper() or 'CREDITO' in c.upper() or 'CRÉDITO' in c.upper()), None)
        col_sai_ext = next((c for c in df_ext.columns if 'SAIDA' in c.upper() or 'SAÍDA' in c.upper() or 'DEBITO' in c.upper() or 'DÉBITO' in c.upper()), None)
        col_val_ext = next((c for c in df_ext.columns if 'VALOR' in c.upper() and c not in [col_ent_ext, col_sai_ext]), None)

        df_ext['Conta'] = df_ext[col_conta_ext].fillna('DIVERSAS').astype(str).str.strip().str.upper()
        
        # Trata identificação do Mês (Caso venha data inteira ou número de mês)
        if col_mes_ext:
            def extrai_mes_num(v):
                try:
                    dt = pd.to_datetime(v, errors='coerce')
                    if pd.notna(dt):
                        return dt.month
                    return int(float(v))
                except:
                    return 0
            df_ext['Mes'] = df_ext[col_mes_ext].apply(extrai_mes_num)
        else:
            df_ext['Mes'] = 0

        # Trata Entradas e Saídas
        if col_ent_ext and col_sai_ext:
            df_ext['Entradas'] = df_ext[col_ent_ext].apply(limpa_valor)
            df_ext['Saidas'] = df_ext[col_sai_ext].apply(limpa_valor)
        elif col_val_ext:
            val_raw = df_ext[col_val_ext].apply(limpa_valor)
            df_ext['Entradas'] = val_raw.apply(lambda x: x if x > 0 else 0.0)
            df_ext['Saidas'] = val_raw.apply(lambda x: abs(x) if x < 0 else 0.0)
        else:
            df_ext['Entradas'] = 0.0
            df_ext['Saidas'] = 0.0

        return df_ini, df_ext
    except Exception as e:
        st.error(f"Erro ao processar abas de Saldo/Extratos Tasy: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_saldo_ini, df_extratos = carregar_dados_saldo_mensal()

if df_saldo_ini.empty and df_extratos.empty:
    st.warning("Nenhum dado encontrado nas abas 'Extratos_Tasy' e 'Saldo_Inicial_Ano'.")
    st.stop()

# ==============================================================================
# 4. BARRA LATERAL E FILTROS
# ==============================================================================
lista_contas = sorted(list(set(df_saldo_ini['Conta'].unique()) | set(df_extratos['Conta'].unique())))

with st.sidebar:
    st.markdown("### Filtros de Movimentação")
    mes_filtro = st.selectbox("Mês Limite (Acumulado)", options=["Todos"] + list(range(1, 13)), format_func=lambda x: f"Até Mês {x:02d} ({meses_nomes.get(x, '')})" if isinstance(x, int) else x)
    conta_filtro = st.selectbox("Conta BANCÁRIA / TASY", options=["Todas"] + lista_contas)
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    if st.button("Limpar Filtros Aplicados", use_container_width=True):
        st.rerun()

    # Aplicação de filtros
    df_ini_filt = df_saldo_ini.copy()
    df_ext_filt = df_extratos.copy()

    if conta_filtro != "Todas":
        df_ini_filt = df_ini_filt[df_ini_filt['Conta'] == conta_filtro]
        df_ext_filt = df_ext_filt[df_ext_filt['Conta'] == conta_filtro]

    if mes_filtro != "Todos":
        df_ext_filt = df_ext_filt[df_ext_filt['Mes'] <= mes_filtro]

    # Exportação
    buffer_out = io.BytesIO()
    with pd.ExcelWriter(buffer_out, engine='openpyxl') as writer:
        df_ext_filt.to_excel(writer, sheet_name='Extrato_Filtrado', index=False)
        df_ini_filt.to_excel(writer, sheet_name='Saldo_Inicial', index=False)
    
    st.download_button(
        label="📥 Baixar Movimentação Mensal",
        data=buffer_out.getvalue(),
        file_name="extrato_mensal_tasy.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ==============================================================================
# 5. CÁLCULOS DA FLUXO DE CAIXA MENSAL
# ==============================================================================
saldo_inicial_total = df_ini_filt['Saldo_Inicial'].sum()
total_entradas = df_ext_filt['Entradas'].sum()
total_saidas = df_ext_filt['Saidas'].sum()
resultado_periodo = total_entradas - total_saidas
saldo_final_atual = saldo_inicial_total + resultado_periodo

# Consolidado Mês a Mês
entradas_m = df_ext_filt.groupby('Mes')['Entradas'].sum().to_dict()
saidas_m = df_ext_filt.groupby('Mes')['Saidas'].sum().to_dict()

df_mensal = pd.DataFrame({'Mes': range(1, 13)})
df_mensal['Entradas'] = df_mensal['Mes'].map(entradas_m).fillna(0.0)
df_mensal['Saidas'] = df_mensal['Mes'].map(saidas_m).fillna(0.0)

s_ini_acc = []
s_fim_acc = []
curr = saldo_inicial_total

for idx, r in df_mensal.iterrows():
    s_ini_acc.append(curr)
    curr = curr + r['Entradas'] - r['Saidas']
    s_fim_acc.append(curr)

df_mensal['Saldo_Inicial'] = s_ini_acc
df_mensal['Saldo_Final'] = s_fim_acc
df_mensal['Mes_Nome'] = df_mensal['Mes'].map(meses_nomes)

# ==============================================================================
# 6. EXIBIÇÃO DO PAINEL (KPIS + GRÁFICO + TABELAS)
# ==============================================================================
st.markdown("""
<div class='dash-header'>
    <h1>Painel de Saldo Mensal (Tasy)</h1>
    <p>Acompanhamento de fluxo de caixa, aportes e saídas consolidadas mês a mês</p>
</div>
""", unsafe_allow_html=True)

kpi_html = f"""
<div class='kpi-grid'>
    <div class='kpi-item bg-purple'>
        <div class='kpi-title'>Saldo Inicial do Ano</div>
        <div class='kpi-value'>{formatar_moeda(saldo_inicial_total)}</div>
        <div class='kpi-subtitle'>Base da aba Saldo_Inicial_Ano</div>
    </div>
    <div class='kpi-item bg-green'>
        <div class='kpi-title'>Total Entradas Acumuladas</div>
        <div class='kpi-value' style='color:var(--green-main);'>{formatar_moeda(total_entradas)}</div>
        <div class='kpi-subtitle'>Entradas no período</div>
    </div>
    <div class='kpi-item bg-red'>
        <div class='kpi-title'>Total Saídas Acumuladas</div>
        <div class='kpi-value' style='color:var(--red-main);'>{formatar_moeda(total_saidas)}</div>
        <div class='kpi-subtitle'>Saídas no período</div>
    </div>
    <div class='kpi-item bg-blue'>
        <div class='kpi-title'>Saldo Final Consolidado</div>
        <div class='kpi-value' style='color:var(--blue-main);'>{formatar_moeda(saldo_final_atual)}</div>
        <div class='kpi-subtitle'>Resultado acumulado</div>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# --- GRÁFICO DE EVOLUÇÃO ---
st.markdown("<div class='section-title'>Evolução Mensal: Entradas vs Saídas & Saldo Final</div>", unsafe_allow_html=True)

fig_mov = go.Figure()
fig_mov.add_trace(go.Bar(x=df_mensal['Mes_Nome'], y=df_mensal['Entradas'], name='Entradas', marker_color='#10b981'))
fig_mov.add_trace(go.Bar(x=df_mensal['Mes_Nome'], y=df_mensal['Saidas'], name='Saídas', marker_color='#ef4444'))
fig_mov.add_trace(go.Scatter(x=df_mensal['Mes_Nome'], y=df_mensal['Saldo_Final'], name='Saldo Final', mode='lines+markers', line=dict(color='#0284c7', width=3)))

fig_mov.update_layout(
    height=280,
    margin=dict(l=20, r=20, t=10, b=0),
    barmode='group',
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickprefix="R$ ")
)
st.plotly_chart(fig_mov, use_container_width=True, config={'displayModeBar': False})

# --- TABELA UNIFICADA RESUMO MÊS A MÊS ---
html_uni = "<div class='unified-summary-box'><table class='unified-table'><thead><tr><th class='row-label'>Fluxo Mensal</th>"
for m in df_mensal['Mes_Nome']:
    html_uni += f"<th>{m}</th>"
html_uni += "</tr></thead><tbody>"

html_uni += "<tr><td class='row-label'>Saldo Inicial</td>"
for v in df_mensal['Saldo_Inicial']:
    html_uni += f"<td>{formatar_moeda_curta(v)}</td>"
html_uni += "</tr>"

html_uni += "<tr><td class='row-label' style='color:var(--green-main);'>(+) Entradas</td>"
for v in df_mensal['Entradas']:
    html_uni += f"<td style='color:var(--green-main); font-weight:700;'>{formatar_moeda_curta(v)}</td>"
html_uni += "</tr>"

html_uni += "<tr><td class='row-label' style='color:var(--red-main);'>(-) Saídas</td>"
for v in df_mensal['Saidas']:
    html_uni += f"<td style='color:var(--red-main); font-weight:700;'>{formatar_moeda_curta(v)}</td>"
html_uni += "</tr>"

html_uni += "<tr><td class='row-label' style='font-weight:800;'>(=) Saldo Final</td>"
for v in df_mensal['Saldo_Final']:
    html_uni += f"<td style='font-weight:800; color:var(--blue-main);'>{formatar_moeda_curta(v)}</td>"
html_uni += "</tr>"

html_uni += "</tbody></table></div>"
st.markdown(html_uni, unsafe_allow_html=True)

# ==============================================================================
# 7. TABELA DETALHADA COM DRILLDOWN POR CONTA
# ==============================================================================
st.markdown("<div class='section-title'>Detalhamento por Conta Bancária / Tasy</div>", unsafe_allow_html=True)

# Cruzamento por conta mês a mês
piv_ent = pd.pivot_table(df_ext_filt, index='Conta', columns='Mes', values='Entradas', aggfunc='sum', fill_value=0.0)
piv_sai = pd.pivot_table(df_ext_filt, index='Conta', columns='Mes', values='Saidas', aggfunc='sum', fill_value=0.0)

for m in range(1, 13):
    if m not in piv_ent.columns: piv_ent[m] = 0.0
    if m not in piv_sai.columns: piv_sai[m] = 0.0

todas_contas_tabela = sorted(list(set(piv_ent.index) | set(piv_sai.index) | set(df_ini_filt['Conta'].unique())))

html_det = "<div class='fases-table-container'><table class='fases-table'><thead><tr><th>CONTA / TIPO DE FLUXO</th>"
html_det += "<th style='text-align:right;'>SALDO INICIAL</th>"
for m in range(1, 13):
    html_det += f"<th style='text-align:right;'>{meses_nomes[m].upper()}</th>"
html_det += "<th style='text-align:right;'>SALDO FINAL</th></tr></thead>"

totais_mes_ent = {m: 0.0 for m in range(1, 13)}
totais_mes_sai = {m: 0.0 for m in range(1, 13)}

for c_name in todas_contas_tabela:
    s_ini_c = df_ini_filt[df_ini_filt['Conta'] == c_name]['Saldo_Inicial'].sum()
    
    ent_m_c = [piv_ent.loc[c_name, m] if c_name in piv_ent.index else 0.0 for m in range(1, 13)]
    sai_m_c = [piv_sai.loc[c_name, m] if c_name in piv_sai.index else 0.0 for m in range(1, 13)]
    
    for idx, m in enumerate(range(1, 13)):
        totais_mes_ent[m] += ent_m_c[idx]
        totais_mes_sai[m] += sai_m_c[idx]
        
    s_fim_c = s_ini_c + sum(ent_m_c) - sum(sai_m_c)

    html_det += "<tbody class='obra-group'><tr>"
    html_det += f"<td><label class='drilldown-label'><input type='checkbox' class='toggle-checkbox'><span class='indicator'>▶</span> <b>{c_name}</b></label></td>"
    html_det += f"<td style='text-align:right; font-weight:700;'>{formatar_moeda(s_ini_c)}</td>"

    # Mês a Mês Líquido (Entradas - Saídas) por Conta
    curr_s = s_ini_c
    for idx, m in enumerate(range(1, 13)):
        liq = ent_m_c[idx] - sai_m_c[idx]
        cor_liq = "var(--green-main)" if liq > 0 else ("var(--red-main)" if liq < 0 else "var(--text-dark)")
        html_det += f"<td style='text-align:right; font-weight:700; color:{cor_liq};'>{formatar_moeda(liq)}</td>"
    
    html_det += f"<td style='text-align:right; font-weight:800; color:var(--blue-main);'>{formatar_moeda(s_fim_c)}</td>"
    html_det += "</tr>"

    # SUB-ROW: ENTRADAS
    html_det += "<tr class='sub-row'>"
    html_det += "<td style='padding-left:30px; font-size:11px; color:var(--green-main);'>↳ (+) Entradas</td><td>-</td>"
    for idx in range(12):
        html_det += f"<td style='text-align:right; font-size:11px; color:var(--green-main);'>{formatar_moeda(ent_m_c[idx])}</td>"
    html_det += f"<td style='text-align:right; font-size:11px; font-weight:700; color:var(--green-main);'>{formatar_moeda(sum(ent_m_c))}</td></tr>"

    # SUB-ROW: SAÍDAS
    html_det += "<tr class='sub-row'>"
    html_det += "<td style='padding-left:30px; font-size:11px; color:var(--red-main);'>↳ (-) Saídas</td><td>-</td>"
    for idx in range(12):
        html_det += f"<td style='text-align:right; font-size:11px; color:var(--red-main);'>{formatar_moeda(sai_m_c[idx])}</td>"
    html_det += f"<td style='text-align:right; font-size:11px; font-weight:700; color:var(--red-main);'>{formatar_moeda(sum(sai_m_c))}</td></tr>"

    html_det += "</tbody>"

# LINHA TOTALIZADORA GERAL
html_det += "<tr class='total-geral-row'><td>TOTAL CONSOLIDADO</td>"
html_det += f"<td style='text-align:right; font-weight:900;'>{formatar_moeda(saldo_inicial_total)}</td>"

for m in range(1, 13):
    liq_tot = totais_mes_ent[m] - totais_mes_sai[m]
    html_det += f"<td style='text-align:right; font-weight:900;'>{formatar_moeda(liq_tot)}</td>"

html_det += f"<td style='text-align:right; font-weight:900; color:var(--blue-main);'>{formatar_moeda(saldo_final_atual)}</td>"
html_det += "</tr></table></div>"

st.markdown(html_det, unsafe_allow_html=True)
