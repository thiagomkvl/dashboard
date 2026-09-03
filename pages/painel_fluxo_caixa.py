import streamlit as st

# O set_page_config OBRIGATORIAMENTE tem que ser a primeira coisa do arquivo
st.set_page_config(page_title="Fluxo de Caixa Analítico", layout="wide", page_icon="💰", initial_sidebar_state="expanded")

import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
import textwrap
import unicodedata
import re

# BLINDAGEM MÁXIMA DE CONEXÃO
try:
    from database import conectar_sheets
except Exception as e:
    def conectar_sheets():
        st.error(f"⚠️ Erro ao carregar 'database.py'. Detalhe: {e}")
        return None

# ==============================================================================
# 1. CUSTOM CSS — IDENTIDADE VISUAL E MATRIZ DUPLA (PREV x REAL)
# ==============================================================================
css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

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
    .main .block-container { padding-top: 0.8rem; padding-bottom: 2rem; max-width: 98%; }
    
    /* Cabeçalho */
    .dashboard-header { display: flex; justify-content: space-between; align-items: center; min-height: 64px; padding: 8px 4px 10px; margin-bottom: 20px; border-bottom: 1px solid var(--border); }
    .header-period { min-width: 200px; }
    .header-period .date { font-size: 18px; font-weight: 900; color: var(--text); letter-spacing: -0.25px; }
    .header-period .label { margin-top: 2px; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
    .header-center { text-align: center; }
    .header-center h1 { margin: 0; color: var(--text); font-size: 21px; line-height: 1.2; font-weight: 800; letter-spacing: 0.35px; text-transform: uppercase; }
    .header-center p { margin: 3px 0 0; color: var(--muted); font-size: 10px; font-weight: 500; letter-spacing: 0.3px; }
    
    /* KPIs */
    .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }
    .kpi-card { position: relative; overflow: hidden; min-height: 80px; padding: 18px 20px; border-radius: 10px; box-shadow: var(--shadow); text-align: left; border: none; display: flex; flex-direction: column; justify-content: center; }
    .kpi-card.inicial { background: linear-gradient(135deg, #1CB0B2, #148b8d); }
    .kpi-card.total { background: linear-gradient(135deg, #008A8C, #006869); }
    .kpi-card.corrente { background: linear-gradient(135deg, #006E6F, #004b4c); }
    .kpi-card.aplicado { background: linear-gradient(135deg, #004D4E, #003334); }
    .kpi-title { font-size: 11px; line-height: 1.2; font-weight: 750; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); }
    .kpi-value { font-size: 26px; line-height: 1.15; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; white-space: nowrap; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); margin-top: 6px; }

    /* MATRIZ CSS GRID EXPANSÍVEL (PREV x REAL) */
    .matrix-wrapper { overflow-x: auto; width: 100%; border: 1px solid var(--border); border-radius: 8px; box-shadow: var(--shadow); background: var(--surface); margin-bottom: 30px;}
    .matrix-grid { min-width: 2200px; display: flex; flex-direction: column; } /* Espaço para 26 colunas */
    
    .grid-row { display: grid; grid-template-columns: minmax(280px, 2fr) repeat(13, minmax(160px, 1fr)); border-bottom: 1px solid #ebf2f2; transition: background 0.1s; align-items: stretch;}
    .grid-row:hover { background-color: #f0f7f7; }
    
    /* Configuração Colunas Duplas */
    .col-val { padding: 0; display: flex; flex-direction: column; justify-content: center; border-right: 2px solid #cbd5e1; }
    .dual-col { display: flex; width: 100%; height: 100%; align-items: stretch; }
    .dual-cell { flex: 1; text-align: right; padding: 10px 8px; font-size: 11px; font-variant-numeric: tabular-nums; display: flex; align-items: center; justify-content: flex-end; }
    .dual-cell.prev { color: #94a3b8; border-right: 1px dashed #e2e8f0; background: rgba(248, 250, 252, 0.4); }
    .dual-cell.real { color: #4b5563; font-weight: 600; }
    
    /* Header Personalizado Padrão Foto */
    .grid-header { background-color: #eaf4f4; border-bottom: 2px solid var(--primary); }
    .grid-header .col-name { font-weight: 800; font-size: 11px; color: #172033; display: flex; align-items: center;}
    .dual-cell.prev.header { font-size: 10px; font-weight: 800; color: #b91c1c; background: #fef2f2; border-bottom: 2px solid #ef4444; justify-content: center; }
    .dual-cell.real.header { font-size: 10px; font-weight: 800; color: #15803d; background: #f0fdf4; border-bottom: 2px solid #22c55e; justify-content: center; }
    
    .col-name { padding: 10px 15px; font-size: 11px; font-weight: 600; color: var(--text); border-right: 2px solid #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .total-col { background-color: #f8fafc; border-right: none; }
    .total-col .dual-cell.real { color: #172033; font-weight: 800; }

    /* Níveis Hierárquicos */
    .lvl-macro { background-color: var(--primary); color: #ffffff; }
    .lvl-macro .col-name { color: #ffffff !important; font-weight: 800 !important; font-size: 12px; border-right: none; background: transparent !important;}
    .lvl-macro .dual-cell.prev, .lvl-macro .dual-cell.real { color: #ffffff; font-weight: 800; border-color: rgba(255,255,255,0.2); background: transparent;}
    
    .lvl-subgrupo { background-color: #ffffff; }
    .lvl-subgrupo .col-name { font-weight: 700; color: #172033; }
    
    .lvl-fornecedor { background-color: #fbfcfd; }
    .lvl-fornecedor .col-name { padding-left: 35px; font-weight: 600; color: #4b5563; }
    
    .lvl-item { background-color: #ffffff; }
    .lvl-item .col-name { padding-left: 60px; font-size: 10px; color: #6b7280; font-weight: 500; }
    .lvl-item .dual-cell.real { font-size: 11px; font-weight: 500; color: #6b7280; }

    /* Linhas de Resultado (Sem Números Iniciais) */
    .res-r1 { background-color: #f8fafc; }
    .res-r1 .col-name, .res-r1 .dual-cell.real { font-weight: 800; color: #172033; }
    .res-r2 { background-color: #ffffff; }
    .res-r2 .col-name, .res-r2 .dual-cell.real { font-weight: 800; color: var(--primary); }
    .res-r3 { background-color: #eaf4f4; }
    .res-r3 .col-name, .res-r3 .dual-cell.real { font-weight: 800; color: #172033; }
    .res-r4 { background-color: #ffffff; }
    .res-r4 .col-name, .res-r4 .dual-cell.real { font-weight: 800; color: var(--danger); }
    .res-r5 { background-color: #ffffff; }
    .res-r5 .col-name, .res-r5 .dual-cell.real { font-weight: 800; color: #3b82f6; }
    .res-r6 { background-color: #004D4E; }
    .res-r6 .col-name, .res-r6 .dual-cell.prev, .res-r6 .dual-cell.real { font-weight: 800; color: #ffffff !important; background: transparent; border-color: rgba(255,255,255,0.2);}

    /* Interatividade Details/Summary */
    details { width: 100%; display: block; margin: 0; padding: 0; }
    details > summary { list-style: none; cursor: pointer; outline: none; margin: 0; padding: 0; }
    details > summary::-webkit-details-marker { display: none; }
    .icon-expand { font-family: monospace; font-weight: 800; color: var(--primary); margin-right: 8px; font-size: 14px; display: inline-block; width: 12px; text-align: center;}
    details:not([open]) > summary .icon-expand::before { content: "+"; }
    details[open] > summary .icon-expand::before { content: "-"; }
    
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .main .block-container { max-width: 100% !important; padding: 10px !important; }
        details[open] summary ~ * { display: block; }
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

def injetar_html(codigo_html):
    st.markdown(codigo_html.replace('\n', ''), unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DE LIMPEZA E CÁLCULO
# ==============================================================================
def limpa_valor_bruto(valor):
    try:
        if isinstance(valor, pd.Series): valor = valor.iloc[0] if not valor.empty else 0.0
        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan", "NaN", "None"]: return 0.0
        if isinstance(valor, (int, float)): return float(valor)
        v_str = str(valor).strip()
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        v_str = v_str.replace('R$', '').strip()
        if '.' in v_str and ',' in v_str: v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str: v_str = v_str.replace(',', '.')
        return float(v_str)
    except Exception: return 0.0

def formata_num(valor):
    try:
        val = float(valor)
        if val == 0: return "-"
        return f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception: return "-"

# ==============================================================================
# 3. FILTRO LATERAL
# ==============================================================================
ano_atual = datetime.now().year
anos_disponiveis = [ano_atual - 2, ano_atual - 1, ano_atual, ano_atual + 1]

with st.sidebar:
    st.markdown("### Filtros de Análise")
    ano_selecionado = st.selectbox("Ano de Referência:", anos_disponiveis, index=2)
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    st.markdown("### Relatório")
    st.info("💡 Visão matricial atualizada com colunas lado a lado (Previsão vs Realizado).", icon="ℹ️")
    components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }" 
        style="width:100%; background:linear-gradient(135deg, #008A8C, #004D4E); color:white; border:none; padding:12px; border-radius:8px; font-family:sans-serif; font-weight:bold; font-size:14px; cursor:pointer; box-shadow: 0 4px 6px rgba(0, 138, 140, 0.2); transition: transform 0.2s;">
        🖨️ Salvar Matriz (PDF)
        </button>
    """, height=55)

# ==============================================================================
# 4. CARGA DE DADOS COM BLINDAGEM DE CACHE (NOVO NOME PARA FORÇAR LIMPEZA)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_matriz_fluxo_v2(ano):
    conn = conectar_sheets()
    if not conn: return pd.DataFrame(), pd.DataFrame(), [], [], [], 0.0, 0.0
    
    linhas_fixas = []
    try:
        df_regras = conn.read(worksheet="Regras_Fluxo", ttl=0)
        if not df_regras.empty and len(df_regras.columns) > 1:
            linhas_fixas = df_regras.iloc[:, 1].dropna().astype(str).str.strip().str.upper().unique().tolist()
    except Exception as e: print("Aviso Regras_Fluxo:", e)

    saldo_base = 0.0
    try:
        df_si = conn.read(worksheet="Saldo_Inicial", ttl=0)
        if not df_si.empty:
            col_si_valor = df_si.columns[1] if len(df_si.columns) > 1 else df_si.columns[0]
            saldo_base = df_si[col_si_valor].apply(limpa_valor_bruto).sum()
    except Exception as e: pass

    try:
        df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
        if df_ext.empty: return pd.DataFrame(), pd.DataFrame(), linhas_fixas, [], [], saldo_base, 0.0
        
        while len(df_ext.columns) < 13: df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""
        col_data = df_ext.columns[1]; col_desc = df_ext.columns[2]
        col_deb = df_ext.columns[4]; col_cred = df_ext.columns[5]
        col_tipo = df_ext.columns[7]; col_subgrupo = df_ext.columns[11]
        col_fornecedor = df_ext.columns[12]

        df_ext['Data'] = pd.to_datetime(df_ext[col_data], dayfirst=True, errors='coerce')
        df_ext = df_ext.dropna(subset=['Data']).copy()
        df_ext['Ano'] = df_ext['Data'].dt.year
        df_ext['Mes'] = df_ext['Data'].dt.month
        df_ext['Vl_Deb'] = df_ext[col_deb].apply(limpa_valor_bruto)
        df_ext['Vl_Cred'] = df_ext[col_cred].apply(limpa_valor_bruto)
        df_ext['SubGrupo'] = df_ext[col_subgrupo].fillna('OUTROS').astype(str).str.strip().str.upper()
        df_ext['Fornecedor'] = df_ext[col_fornecedor].fillna('NÃO IDENTIFICADO').astype(str).str.strip().str.upper()
        df_ext['Descricao'] = df_ext[col_desc].fillna('').astype(str).str.strip()
        
        def norm_txt(txt): return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower() if pd.notna(txt) else ""
        serie_tipo = df_ext[col_tipo].apply(norm_txt)
        is_transf = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')
        df_ext = df_ext[~is_transf]

        regras_entradas = []
        regras_saidas = []
        for r in linhas_fixas:
            tc = df_ext[df_ext['SubGrupo'] == r]['Vl_Cred'].sum()
            td = df_ext[df_ext['SubGrupo'] == r]['Vl_Deb'].sum()
            if tc > 0 or td > 0:
                if tc >= td: regras_entradas.append(r)
                else: regras_saidas.append(r)
            else:
                regras_saidas.append(r)

        df_before = df_ext[df_ext['Data'] < f"{ano}-01-01"]
        saldo_inicio_ano = saldo_base + df_before['Vl_Cred'].sum() - df_before['Vl_Deb'].sum()

        df_up_to_now = df_ext[df_ext['Data'] <= pd.to_datetime(datetime.now().date())]
        saldo_atual_todas = saldo_base + df_up_to_now['Vl_Cred'].sum() - df_up_to_now['Vl_Deb'].sum()

        df_ano = df_ext[df_ext['Ano'] == ano].copy()
        mask_emp = df_ano['SubGrupo'].str.contains("EMPRESTIMO|EMPRÉSTIMO|FINANCIAMENTO")
        df_emprestimos = df_ano[mask_emp].copy()
        df_operacional = df_ano[~mask_emp].copy()
            
        return df_operacional, df_emprestimos, linhas_fixas, regras_entradas, regras_saidas, saldo_inicio_ano, saldo_atual_todas
    except Exception as e:
        st.error(f"Erro interno: {e}")
        return pd.DataFrame(), pd.DataFrame(), [], [], [], 0.0, 0.0

# Inicialização segura para garantir que as variáveis existam
df_op, df_emp = pd.DataFrame(), pd.DataFrame()
linhas_fixas, regras_entradas, regras_saidas = [], [], []
saldo_inicio_ano, saldo_atual = 0.0, 0.0

try:
    res = carregar_dados_matriz_fluxo_v2(ano_selecionado)
    if len(res) == 7:
        df_op, df_emp, linhas_fixas, regras_entradas, regras_saidas, saldo_inicio_ano, saldo_atual = res
except Exception as e:
    st.error(f"Erro ao extrair pacote de dados: {e}")

if df_op.empty and df_emp.empty:
    st.warning(f"⚠️ Nenhuma movimentação encontrada para o ano de {ano_selecionado}.")
    st.stop()

# ==============================================================================
# 5. CONSTRUÇÃO DA LÓGICA DE DADOS (JAN A DEZ)
# ==============================================================================
df_entradas = df_op[df_op['Vl_Cred'] > 0].copy()
df_entradas['Valor_Op'] = df_entradas['Vl_Cred']

df_saidas = df_op[df_op['Vl_Deb'] > 0].copy()
df_saidas['Valor_Op'] = df_saidas['Vl_Deb']

tot_ent = [0]*12
tot_sai = [0]*12
nec_emp = [0]*12
pag_emp = [0]*12

# Array auxiliar para PREVISÕES (Zerado até conectarmos com a base de previsão)
dummy_prev = [0]*12

for m in range(1, 13):
    idx = m - 1
    tot_ent[idx] = df_entradas[df_entradas['Mes'] == m]['Valor_Op'].sum()
    tot_sai[idx] = df_saidas[df_saidas['Mes'] == m]['Valor_Op'].sum()
    
    df_m_emp = df_emp[df_emp['Mes'] == m]
    nec_emp[idx] = df_m_emp['Vl_Cred'].sum()
    pag_emp[idx] = df_m_emp['Vl_Deb'].sum()

l1_resultado = [tot_ent[i] - tot_sai[i] for i in range(12)]
l2_saldo_ant = [0]*12
l3_acumulado = [0]*12
l6_saldo_fim = [0]*12

l2_saldo_ant[0] = saldo_inicio_ano
for i in range(12):
    if i > 0: l2_saldo_ant[i] = l6_saldo_fim[i-1]
    l3_acumulado[i] = l1_resultado[i] + l2_saldo_ant[i]
    l6_saldo_fim[i] = l3_acumulado[i] + nec_emp[i] - pag_emp[i]

# ==============================================================================
# 6. HEADER E KPIS
# ==============================================================================
injetar_html(f"""
<div class="dashboard-header">
    <div class="header-period">
        <div class="date">Ano: {ano_selecionado}</div>
        <div class="label">Período de Referência</div>
    </div>
    <div class="header-center">
        <h1>MATRIZ DE FLUXO DE CAIXA</h1>
        <p>Visão Consolidada de Recebimentos e Pagamentos</p>
    </div>
    <div style="min-width: 200px;"></div>
</div>
""")

total_ano_ent = sum(tot_ent)
total_ano_sai = sum(tot_sai)

injetar_html(f"""
<div class='kpi-row'>
    <div class='kpi-card inicial'>
        <div class='kpi-title'>SALDO INICIAL ({ano_selecionado})</div>
        <div class='kpi-value'>R$ {formatar_moeda(saldo_inicio_ano)}</div>
    </div>
    <div class='kpi-card total'>
        <div class='kpi-title'>TOTAL ENTRADAS (ANO)</div>
        <div class='kpi-value'>R$ {formatar_moeda(total_ano_ent)}</div>
    </div>
    <div class='kpi-card corrente'>
        <div class='kpi-title'>TOTAL SAÍDAS (ANO)</div>
        <div class='kpi-value'>R$ {formatar_moeda(total_ano_sai)}</div>
    </div>
    <div class='kpi-card aplicado'>
        <div class='kpi-title'>SALDO ATUAL DO CAIXA</div>
        <div class='kpi-value'>R$ {formatar_moeda(saldo_atual)}</div>
    </div>
</div>
""")

# ==============================================================================
# 7. RENDERIZAÇÃO DA MATRIZ CSS GRID (DUAL COLUMN)
# ==============================================================================
meses_labels = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

def render_linha(nome, nivel, arr_prev, arr_real, is_item=False):
    tot_p = sum(arr_prev)
    tot_r = sum(arr_real)
    html = f"<div class='grid-row {nivel}'>"
    html += f"<div class='col-name'>{nome}</div>"
    
    for p, r in zip(arr_prev, arr_real):
        html += "<div class='col-val'>"
        html += "<div class='dual-col'>"
        html += f"<div class='dual-cell prev'>{'R$ ' if is_item and p != 0 else ''}{formatar_moeda(p)}</div>"
        html += f"<div class='dual-cell real'>{'R$ ' if is_item and r != 0 else ''}{formatar_moeda(r)}</div>"
        html += "</div></div>"
        
    html += "<div class='col-val total-col'>"
    html += "<div class='dual-col'>"
    html += f"<div class='dual-cell prev'>{'R$ ' if is_item and tot_p != 0 else ''}{formatar_moeda(tot_p)}</div>"
    html += f"<div class='dual-cell real'>{'R$ ' if is_item and tot_r != 0 else ''}{formatar_moeda(tot_r)}</div>"
    html += "</div></div></div>"
    return html

def build_drilldown(lista_regras, df_dados, titulo_outros):
    html = ""
    for regra in lista_regras:
        df_regra = df_dados[df_dados['SubGrupo'] == regra]
        arr_real = [0]*12
        for m in range(1, 13):
            arr_real[m-1] = df_regra[df_regra['Mes'] == m]['Valor_Op'].sum()
            
        if sum(arr_real) == 0:
            html += render_linha(regra, "lvl-subgrupo", dummy_prev, arr_real)
        else:
            html += "<details><summary>"
            html += render_linha(f"<span class='icon-expand'></span>{regra}", "lvl-subgrupo", dummy_prev, arr_real)
            html += "</summary>"
            
            forn_tot = df_regra.groupby('Fornecedor')['Valor_Op'].sum().sort_values(ascending=False)
            for forn in forn_tot.index:
                df_forn = df_regra[df_regra['Fornecedor'] == forn]
                arr_forn_real = [0]*12
                for m in range(1, 13):
                    arr_forn_real[m-1] = df_forn[df_forn['Mes'] == m]['Valor_Op'].sum()
                    
                html += "<details><summary>"
                html += render_linha(f"<span class='icon-expand'></span>{forn}", "lvl-fornecedor", dummy_prev, arr_forn_real)
                html += "</summary>"
                
                df_forn_sorted = df_forn.sort_values('Data')
                for _, row in df_forn_sorted.iterrows():
                    arr_trans_real = [0]*12
                    arr_trans_real[row['Mes'] - 1] = row['Valor_Op']
                    dt_s = row['Data'].strftime('%d/%m')
                    desc = row['Descricao'][:45] + ("..." if len(row['Descricao']) > 45 else "")
                    html += render_linha(f"↳ {dt_s} | {desc}", "lvl-item", dummy_prev, arr_trans_real, is_item=True)
                html += "</details>"
            html += "</details>"
            
    # Processa "OUTRAS" (Lançamentos que não estão nas regras fixas)
    df_outros = df_dados[~df_dados['SubGrupo'].isin(lista_regras)]
    if not df_outros.empty:
        arr_out = [0]*12
        for m in range(1, 13):
            arr_out[m-1] = df_outros[df_outros['Mes'] == m]['Valor_Op'].sum()
            
        if sum(arr_out) > 0:
            html += "<details><summary>"
            html += render_linha(f"<span class='icon-expand'></span>{titulo_outros}", "lvl-subgrupo", dummy_prev, arr_out)
            html += "</summary>"
            
            sub_tot = df_outros.groupby('SubGrupo')['Valor_Op'].sum().sort_values(ascending=False)
            for sub in sub_tot.index:
                df_sub = df_outros[df_outros['SubGrupo'] == sub]
                arr_sub = [0]*12
                for m in range(1, 13):
                    arr_sub[m-1] = df_sub[df_sub['Mes'] == m]['Valor_Op'].sum()
                    
                html += "<details><summary>"
                html += render_linha(f"<span class='icon-expand'></span>{sub}", "lvl-fornecedor", dummy_prev, arr_sub)
                html += "</summary>"
                
                df_sub_sorted = df_sub.sort_values('Data')
                for _, row in df_sub_sorted.iterrows():
                    arr_trans = [0]*12
                    arr_trans[row['Mes'] - 1] = row['Valor_Op']
                    dt_s = row['Data'].strftime('%d/%m')
                    desc = row['Descricao'][:40] + ("..." if len(row['Descricao']) > 40 else "")
                    forn_s = row['Fornecedor'][:15]
                    html += render_linha(f"↳ {dt_s} | {forn_s} | {desc}", "lvl-item", dummy_prev, arr_trans, is_item=True)
                html += "</details>"
            html += "</details>"
    return html

# Inicia montagem da estrutura HTML
html_matriz = "<div class='matrix-wrapper'><div class='matrix-grid'>"

# Header Dinâmico de Meses e Colunas Duplas
html_matriz += "<div class='grid-row grid-header'>"
html_matriz += "<div class='col-name' style='padding-left: 15px;'>DESCRIÇÃO DOS LANÇAMENTOS</div>"

for m in meses_labels: 
    html_matriz += f'''
    <div class='col-val' style='padding:0;'>
        <div style='text-align:center; padding: 5px 0; border-bottom: 1px solid var(--border); font-size: 11px;'>{m.upper()}/{str(ano_selecionado)[-2:]}</div>
        <div class='dual-col'>
            <div class='dual-cell prev header'>PREVISÃO</div>
            <div class='dual-cell real header'>REALIZADO</div>
        </div>
    </div>
    '''
html_matriz += f'''
    <div class='col-val total-col' style='padding:0;'>
        <div style='text-align:center; padding: 5px 0; border-bottom: 1px solid var(--border); font-size: 11px;'>TOTAL ANUAL</div>
        <div class='dual-col'>
            <div class='dual-cell prev header'>PREVISÃO</div>
            <div class='dual-cell real header'>REALIZADO</div>
        </div>
    </div>
</div>
'''

# BLOCO ENTRADAS
html_matriz += render_linha("ENTRADAS OPERACIONAIS", "lvl-macro", dummy_prev, tot_ent)
html_matriz += build_drilldown(regras_entradas, df_entradas, "OUTRAS ENTRADAS")

html_matriz += "<div style='height: 15px; background: #f5f7fb;'></div>"

# BLOCO SAÍDAS
html_matriz += render_linha("SAÍDAS OPERACIONAIS", "lvl-macro", dummy_prev, tot_sai)
html_matriz += build_drilldown(regras_saidas, df_saidas, "OUTRAS SAÍDAS")

html_matriz += "<div style='height: 15px; background: #f5f7fb;'></div>"

# BLOCO DE RESULTADO (Sem os números iniciais)
html_matriz += render_linha("(ENTRADAS - SAÍDAS)", "res-r1", dummy_prev, l1_resultado)
html_matriz += render_linha("SALDO ANTERIOR", "res-r2", dummy_prev, l2_saldo_ant)
html_matriz += render_linha("SALDO ACUMULADO", "res-r3", dummy_prev, l3_acumulado)
html_matriz += render_linha("NECESSIDADE DE EMPRÉSTIMOS", "res-r4", dummy_prev, nec_emp)
html_matriz += render_linha("PAGAMENTO DE EMPRÉSTIMOS", "res-r5", dummy_prev, pag_emp)
html_matriz += render_linha("SALDO FINAL", "res-r6", dummy_prev, l6_saldo_fim)

html_matriz += "</div></div>"

injetar_html(html_matriz)
st.markdown(f"<div style='font-size:9px; color:gray; text-align:right; margin-top:5px;'>Valores em Reais (R$) | Estrutura de previsão aguardando conexão de dados | Referência: {ano_selecionado}</div>", unsafe_allow_html=True)
