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
# 1. CUSTOM CSS — IDENTIDADE VISUAL E MATRIZ
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
    
    /* KPIs Idênticos ao Dashboard Saldo */
    .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
    .kpi-card { position: relative; overflow: hidden; min-height: 90px; padding: 18px 20px; border-radius: 10px; box-shadow: var(--shadow); text-align: left; border: none; display: flex; flex-direction: column; justify-content: center; }
    .kpi-card.inicial { background: linear-gradient(135deg, #1CB0B2, #148b8d); }
    .kpi-card.total { background: linear-gradient(135deg, #008A8C, #006869); }
    .kpi-card.corrente { background: linear-gradient(135deg, #006E6F, #004b4c); }
    .kpi-card.aplicado { background: linear-gradient(135deg, #004D4E, #003334); }
    .kpi-title { font-size: 11px; line-height: 1.2; font-weight: 750; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); }
    .kpi-value { font-size: 26px; line-height: 1.15; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; white-space: nowrap; text-shadow: 0px 1px 2px rgba(0,0,0,0.1); margin-top: 6px; }

    /* TABELA MATRIZ DO FLUXO (ESTILO FOTO) */
    .tabela-container-scroll { overflow-x: auto; overflow-y: hidden; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); box-shadow: var(--shadow); width: 100%; margin-bottom: 20px; }
    .fluxo-table { width: 100%; border-collapse: collapse; font-size: 11px; min-width: 1200px; }
    .fluxo-table th, .fluxo-table td { border: 1px solid #ebf2f2; padding: 8px 10px; white-space: nowrap; }
    
    /* Cabeçalho dos Meses */
    .fluxo-table thead th { background-color: #eaf4f4; color: #172033; font-weight: 800; text-align: center; text-transform: uppercase; border-bottom: 2px solid var(--primary); font-size: 10px; letter-spacing: 0.5px;}
    .fluxo-table thead th.desc-col { text-align: left; width: 280px; position: sticky; left: 0; z-index: 2; background-color: #eaf4f4; border-right: 2px solid var(--primary);}
    
    /* Linhas Fixas */
    .fluxo-table tbody td.desc-col { position: sticky; left: 0; background-color: #ffffff; font-weight: 600; color: #273043; border-right: 2px solid var(--primary); z-index: 1; }
    .fluxo-table tbody td.num { text-align: right; font-variant-numeric: tabular-nums; font-weight: 550; color: #4b5563; }
    
    /* Agrupadores e Totais */
    .fluxo-table .group-title td { background-color: var(--primary); color: #ffffff; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; font-size: 12px; }
    .fluxo-table .group-title td.desc-col { background-color: var(--primary); }
    .fluxo-table .total-row td { background-color: #e0efef; font-weight: 800; color: #172033; }
    .fluxo-table .total-row td.desc-col { background-color: #e0efef; }
    .fluxo-table .total-row td.num { color: #172033; }
    
    /* Linhas de Resultado (1 a 6) */
    .fluxo-table .res-row td { font-weight: 800; font-size: 12px; }
    .fluxo-table .res-row td.desc-col { background-color: #f8fafc; }
    .fluxo-table .res-row td.num { background-color: #f8fafc; }
    
    /* Cores Específicas do Resultado */
    .fluxo-table .res-row.r1 td { color: #172033; }
    .fluxo-table .res-row.r2 td { color: #008A8C; }
    .fluxo-table .res-row.r3 td { color: #172033; background-color: #eaf4f4; }
    .fluxo-table .res-row.r4 td.desc-col { color: var(--danger); }
    .fluxo-table .res-row.r5 td.desc-col { color: var(--primary); }
    .fluxo-table .res-row.r6 td { color: #ffffff; background-color: #004D4E; }
    .fluxo-table .res-row.r6 td.desc-col { background-color: #004D4E; }
    
    /* Efeitos */
    .fluxo-table tbody tr:not(.group-title):not(.total-row):not(.res-row):hover td { background-color: #f0f7f7; }
    
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .main .block-container { max-width: 100% !important; padding: 10px !important; }
    }
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DE LIMPEZA E CÁLCULO
# ==============================================================================
def limpa_valor_bruto(valor):
    try:
        if isinstance(valor, pd.Series): 
            valor = valor.iloc[0] if not valor.empty else 0.0
        if pd.isna(valor) or str(valor).strip() in ["", "-", "nan", "NaN", "None"]: return 0.0
        if isinstance(valor, (int, float)): return float(valor)
        v_str = str(valor).strip()
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        v_str = v_str.replace('R$', '').strip()
        if '.' in v_str and ',' in v_str: v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str: v_str = v_str.replace(',', '.')
        return float(v_str)
    except Exception: return 0.0

def formatar_moeda(valor):
    try:
        val = float(valor)
        if val == 0: return "-"
        return f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception: return "-"

# ==============================================================================
# 3. FILTRO LATERAL E CARGA DE DADOS (POR ANO)
# ==============================================================================
ano_atual = datetime.now().year
anos_disponiveis = [ano_atual - 2, ano_atual - 1, ano_atual, ano_atual + 1]

with st.sidebar:
    st.markdown("### Filtros de Análise")
    ano_selecionado = st.selectbox("Ano de Referência:", anos_disponiveis, index=2)
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    st.markdown("### Relatório")
    st.info("💡 Este painel exibe a visão matricial consolidada de Jan a Dez.", icon="ℹ️")
    components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }" 
        style="width:100%; background:linear-gradient(135deg, #008A8C, #004D4E); color:white; border:none; padding:12px; border-radius:8px; font-family:sans-serif; font-weight:bold; font-size:14px; cursor:pointer; box-shadow: 0 4px 6px rgba(0, 138, 140, 0.2); transition: transform 0.2s;">
        🖨️ Salvar Matriz (PDF)
        </button>
    """, height=55)

@st.cache_data(ttl=60)
def preparar_dados_matriz(ano):
    conn = conectar_sheets()
    if not conn: return pd.DataFrame(), pd.DataFrame(), [], 0.0, 0.0
    
    # 1. Busca Regras (Linhas Fixas da Coluna B)
    linhas_fixas = []
    try:
        df_regras = conn.read(worksheet="Regras_Fluxo", ttl=0)
        if not df_regras.empty and len(df_regras.columns) > 1:
            # Coluna B = index 1
            linhas_fixas = df_regras.iloc[:, 1].dropna().astype(str).str.strip().str.upper().unique().tolist()
    except Exception as e:
        print("Erro ao ler Regras_Fluxo:", e)

    # 2. Busca Saldo Inicial Base
    saldo_base = 0.0
    try:
        df_si = conn.read(worksheet="Saldo_Inicial", ttl=0)
        if not df_si.empty:
            col_si_valor = df_si.columns[1] if len(df_si.columns) > 1 else df_si.columns[0]
            saldo_base = df_si[col_si_valor].apply(limpa_valor_bruto).sum()
    except Exception as e: pass

    # 3. Busca Extratos
    try:
        df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
        if df_ext.empty: return pd.DataFrame(), pd.DataFrame(), linhas_fixas, saldo_base, 0.0
        
        while len(df_ext.columns) < 12: df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""
        col_data = df_ext.columns[1]; col_deb = df_ext.columns[4]; col_cred = df_ext.columns[5]
        col_subgrupo = df_ext.columns[11]; col_tipo = df_ext.columns[7]

        df_ext['Data'] = pd.to_datetime(df_ext[col_data], dayfirst=True, errors='coerce')
        df_ext = df_ext.dropna(subset=['Data']).copy()
        df_ext['Ano'] = df_ext['Data'].dt.year
        df_ext['Mes'] = df_ext['Data'].dt.month
        df_ext['Vl_Deb'] = df_ext[col_deb].apply(limpa_valor_bruto)
        df_ext['Vl_Cred'] = df_ext[col_cred].apply(limpa_valor_bruto)
        df_ext['SubGrupo'] = df_ext[col_subgrupo].fillna('OUTROS').astype(str).str.strip().str.upper()
        
        # Filtra Transferências
        serie_tipo = df_ext[col_tipo].astype(str).str.lower().apply(lambda x: unicodedata.normalize('NFKD', x).encode('ASCII', 'ignore').decode('utf-8'))
        is_transf = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')
        df_ext = df_ext[~is_transf]

        # 4. Calcula Saldo Inicial do Ano Solicitado (Saldo Base + Movimentações de anos anteriores)
        df_before = df_ext[df_ext['Data'] < f"{ano}-01-01"]
        mov_before = df_before['Vl_Cred'].sum() - df_before['Vl_Deb'].sum()
        saldo_inicio_ano = saldo_base + mov_before

        # 5. Calcula Saldo Atual (Até a data de hoje)
        df_up_to_now = df_ext[df_ext['Data'] <= pd.to_datetime(datetime.now().date())]
        saldo_atual_todas_contas = saldo_base + df_up_to_now['Vl_Cred'].sum() - df_up_to_now['Vl_Deb'].sum()

        # 6. Dados do Ano Selecionado
        df_ano = df_ext[df_ext['Ano'] == ano].copy()
        
        # Separar Empréstimos (Necessidade e Pagamento)
        mask_emp = df_ano['SubGrupo'].str.contains("EMPRESTIMO|EMPRÉSTIMO|FINANCIAMENTO")
        df_emprestimos = df_ano[mask_emp].copy()
        df_operacional = df_ano[~mask_emp].copy()
        
        # Se as regras não vieram da planilha, cria dinamicamente
        if not linhas_fixas:
            linhas_fixas = df_operacional['SubGrupo'].unique().tolist()
            
        return df_operacional, df_emprestimos, linhas_fixas, saldo_inicio_ano, saldo_atual_todas_contas
    except Exception as e:
        st.error(f"Erro ao processar extratos: {e}")
        return pd.DataFrame(), pd.DataFrame(), [], 0.0, 0.0

df_op, df_emp, linhas_regras, saldo_inicio_ano, saldo_atual = preparar_dados_matriz(ano_selecionado)

if df_op.empty and df_emp.empty:
    st.warning(f"⚠️ Nenhuma movimentação encontrada para o ano de {ano_selecionado}.")
    st.stop()

# ==============================================================================
# 4. PROCESSAMENTO DA MATRIZ (JAN A DEZ)
# ==============================================================================
# Entradas = Operacional com Crédito > 0
# Saídas = Operacional com Débito > 0
df_entradas = df_op[df_op['Vl_Cred'] > 0]
df_saidas = df_op[df_op['Vl_Deb'] > 0]

# Filtra as linhas de regras para saber quem entra onde
linhas_entradas = [r for r in linhas_regras if r in df_entradas['SubGrupo'].values]
linhas_saidas = [r for r in linhas_regras if r in df_saidas['SubGrupo'].values]

# Estruturas de dados (Arrays de 12 posições)
matriz_ent = {l: [0]*12 for l in linhas_entradas}
matriz_sai = {l: [0]*12 for l in linhas_saidas}
matriz_ent["OUTRAS ENTRADAS"] = [0]*12
matriz_sai["OUTRAS SAÍDAS"] = [0]*12

tot_ent = [0]*12
tot_sai = [0]*12
nec_emp = [0]*12
pag_emp = [0]*12

# Preenche os dados mês a mês
for m in range(1, 13):
    idx = m - 1
    
    # ENTRADAS
    df_m_ent = df_entradas[df_entradas['Mes'] == m]
    for linha in linhas_entradas:
        v = df_m_ent[df_m_ent['SubGrupo'] == linha]['Vl_Cred'].sum()
        matriz_ent[linha][idx] = v
        tot_ent[idx] += v
    
    v_outros_ent = df_m_ent[~df_m_ent['SubGrupo'].isin(linhas_entradas)]['Vl_Cred'].sum()
    matriz_ent["OUTRAS ENTRADAS"][idx] += v_outros_ent
    tot_ent[idx] += v_outros_ent
    
    # SAÍDAS
    df_m_sai = df_saidas[df_saidas['Mes'] == m]
    for linha in linhas_saidas:
        v = df_m_sai[df_m_sai['SubGrupo'] == linha]['Vl_Deb'].sum()
        matriz_sai[linha][idx] = v
        tot_sai[idx] += v
        
    v_outros_sai = df_m_sai[~df_m_sai['SubGrupo'].isin(linhas_saidas)]['Vl_Deb'].sum()
    matriz_sai["OUTRAS SAÍDAS"][idx] += v_outros_sai
    tot_sai[idx] += v_outros_sai
    
    # EMPRÉSTIMOS
    df_m_emp = df_emp[df_emp['Mes'] == m]
    nec_emp[idx] = df_m_emp['Vl_Cred'].sum() # Empréstimo Entrando (Necessidade)
    pag_emp[idx] = df_m_emp['Vl_Deb'].sum()  # Empréstimo Saindo (Pagamento)

# Calcula as 6 linhas de Resultado Dinamicamente
l1_resultado = [tot_ent[i] - tot_sai[i] for i in range(12)]
l2_saldo_ant = [0]*12
l3_acumulado = [0]*12
l6_saldo_fim = [0]*12

l2_saldo_ant[0] = saldo_inicio_ano

for i in range(12):
    if i > 0:
        l2_saldo_ant[i] = l6_saldo_fim[i-1]
        
    l3_acumulado[i] = l1_resultado[i] + l2_saldo_ant[i]
    # Linha 6 = Acumulado + Emprestimos que Entraram - Emprestimos que Saíram
    l6_saldo_fim[i] = l3_acumulado[i] + nec_emp[i] - pag_emp[i]

# ==============================================================================
# 5. HEADER E KPIS
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
# 6. RENDERIZAÇÃO DA TABELA HTML
# ==============================================================================
meses_labels = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

def render_tds(array_valores):
    return "".join([f"<td class='num'>{formatar_moeda(v)}</td>" for v in array_valores])

html_matriz = f"""
<div class="tabela-container-scroll">
    <table class="fluxo-table">
        <thead>
            <tr>
                <th class="desc-col">DESCRIÇÃO DOS LANÇAMENTOS</th>
"""
for m in meses_labels: html_matriz += f"<th>{m}/{str(ano_selecionado)[-2:]}</th>"
html_matriz += "<th>TOTAL</th></tr></thead><tbody>"

# --- BLOCO ENTRADAS ---
html_matriz += "<tr class='group-title'><td class='desc-col'>ENTRADAS OPERACIONAIS</td>" + ("<td></td>"*13) + "</tr>"

for linha in linhas_entradas:
    if sum(matriz_ent[linha]) > 0:
        html_matriz += f"<tr><td class='desc-col'>{linha}</td>{render_tds(matriz_ent[linha])}<td class='num' style='font-weight:800;'>{formatar_moeda(sum(matriz_ent[linha]))}</td></tr>"

if sum(matriz_ent["OUTRAS ENTRADAS"]) > 0:
    html_matriz += f"<tr><td class='desc-col'>OUTRAS ENTRADAS</td>{render_tds(matriz_ent['OUTRAS ENTRADAS'])}<td class='num' style='font-weight:800;'>{formatar_moeda(sum(matriz_ent['OUTRAS ENTRADAS']))}</td></tr>"

html_matriz += f"<tr class='total-row'><td class='desc-col'>TOTAL DAS ENTRADAS</td>{render_tds(tot_ent)}<td class='num'>{formatar_moeda(sum(tot_ent))}</td></tr>"

# --- ESPAÇO ---
html_matriz += "<tr><td colspan='14' style='height: 15px; border:none; background-color:#f5f7fb;'></td></tr>"

# --- BLOCO SAÍDAS ---
html_matriz += "<tr class='group-title'><td class='desc-col'>SAÍDAS OPERACIONAIS</td>" + ("<td></td>"*13) + "</tr>"

for linha in linhas_saidas:
    if sum(matriz_sai[linha]) > 0:
        html_matriz += f"<tr><td class='desc-col'>{linha}</td>{render_tds(matriz_sai[linha])}<td class='num' style='font-weight:800;'>{formatar_moeda(sum(matriz_sai[linha]))}</td></tr>"

if sum(matriz_sai["OUTRAS SAÍDAS"]) > 0:
    html_matriz += f"<tr><td class='desc-col'>OUTRAS SAÍDAS</td>{render_tds(matriz_sai['OUTRAS SAÍDAS'])}<td class='num' style='font-weight:800;'>{formatar_moeda(sum(matriz_sai['OUTRAS SAÍDAS']))}</td></tr>"

html_matriz += f"<tr class='total-row'><td class='desc-col'>TOTAL DAS SAÍDAS</td>{render_tds(tot_sai)}<td class='num'>{formatar_moeda(sum(tot_sai))}</td></tr>"

# --- ESPAÇO ---
html_matriz += "<tr><td colspan='14' style='height: 15px; border:none; background-color:#f5f7fb;'></td></tr>"

# --- LINHAS DE RESULTADO MENSAL ---
html_matriz += f"<tr class='res-row r1'><td class='desc-col'>1 (ENTRADAS - SAÍDAS)</td>{render_tds(l1_resultado)}<td class='num'>{formatar_moeda(sum(l1_resultado))}</td></tr>"
html_matriz += f"<tr class='res-row r2'><td class='desc-col'>2 SALDO ANTERIOR</td>{render_tds(l2_saldo_ant)}<td class='num'>-</td></tr>"
html_matriz += f"<tr class='res-row r3'><td class='desc-col'>3 SALDO ACUMULADO (1 + 2)</td>{render_tds(l3_acumulado)}<td class='num'>-</td></tr>"
html_matriz += f"<tr class='res-row r4'><td class='desc-col'>4 NECESSIDADE DE EMPRÉSTIMOS</td>{render_tds(nec_emp)}<td class='num'>{formatar_moeda(sum(nec_emp))}</td></tr>"
html_matriz += f"<tr class='res-row r5'><td class='desc-col'>5 PAGAMENTO DE EMPRÉSTIMOS</td>{render_tds(pag_emp)}<td class='num'>{formatar_moeda(sum(pag_emp))}</td></tr>"
html_matriz += f"<tr class='res-row r6'><td class='desc-col'>6 SALDO FINAL (3 + 4 - 5)</td>{render_tds(l6_saldo_fim)}<td class='num'>-</td></tr>"

html_matriz += "</tbody></table></div>"

injetar_html(html_matriz)
st.markdown(f"<div style='font-size:9px; color:gray; text-align:right;'>Valores em Reais (R$) | Referência: Jan a Dez de {ano_selecionado}</div>", unsafe_allow_html=True)
