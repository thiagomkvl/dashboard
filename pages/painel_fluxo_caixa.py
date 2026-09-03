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
# 1. CUSTOM CSS — IDENTIDADE VISUAL E COLUNA CONGELADA (STICKY)
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

    /* MATRIZ CSS GRID EXPANSÍVEL */
    .matrix-wrapper { overflow-x: auto; width: 100%; border: 1px solid var(--border); border-radius: 8px; box-shadow: var(--shadow); background: var(--surface); margin-bottom: 30px; position: relative;}
    .matrix-grid { min-width: 2200px; display: flex; flex-direction: column; }
    
    .grid-row { display: grid; grid-template-columns: minmax(300px, 2fr) repeat(13, minmax(160px, 1fr)); border-bottom: 1px solid #ebf2f2; transition: background 0.1s; align-items: stretch;}
    
    /* Hover SOMENTE nas linhas comuns */
    .grid-row:not(.lvl-macro):not(.res-r6):hover { background-color: #f0f7f7; }
    .grid-row:not(.lvl-macro):not(.res-r6):hover .col-name { background-color: #f0f7f7; }
    
    /* Configuração Colunas Duplas */
    .col-val { padding: 0; display: flex; flex-direction: column; justify-content: center; border-right: 2px solid #cbd5e1; }
    .dual-col { display: flex; width: 100%; height: 100%; align-items: stretch; }
    
    /* ALINHAMENTO À ESQUERDA PARA OS VALORES */
    .dual-cell { flex: 1; text-align: left; padding: 10px 8px; font-size: 11px; font-variant-numeric: tabular-nums; display: flex; align-items: center; justify-content: flex-start; }
    
    /* Cores das células (Previsão vs Realizado) */
    .dual-cell.prev { color: #94a3b8; border-right: 1px dashed #e2e8f0; background: rgba(248, 250, 252, 0.4); }
    .dual-cell.real { color: #000000; font-weight: 600; }
    
    /* Header Personalizado Padrão Foto */
    .grid-header { background-color: #eaf4f4; border-bottom: 2px solid var(--primary); }
    .grid-header .col-name { font-weight: 800; font-size: 11px; color: #172033; display: flex; align-items: center; background-color: #eaf4f4; z-index: 3;}
    .dual-cell.prev.header { font-size: 10px; font-weight: 800; color: #b91c1c; background: #fef2f2; border-bottom: 2px solid #ef4444; justify-content: flex-start; }
    .dual-cell.real.header { font-size: 10px; font-weight: 800; color: #15803d; background: #f0fdf4; border-bottom: 2px solid #22c55e; justify-content: flex-start; }
    
    /* =============== COLUNA CONGELADA (STICKY) =============== */
    .col-name { 
        position: sticky; 
        left: 0; 
        z-index: 2; 
        padding: 10px 15px; 
        font-size: 11px; 
        font-weight: 600; 
        color: var(--text); 
        border-right: 2px solid #cbd5e1; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        box-shadow: 3px 0 5px -2px rgba(0,0,0,0.1); 
    }
    
    .total-col { background-color: #f8fafc; border-right: none; }
    .total-col .dual-cell.real { color: #000000; font-weight: 800; }

    /* Níveis Hierárquicos (Macro, Subgrupo, Transação) - FUNDOS SÓLIDOS PRO STICKY FUNCIONAR */
    .lvl-macro { background-color: #e0efef; border-top: 2px solid var(--primary); border-bottom: 2px solid var(--primary); }
    .lvl-macro .col-name { background-color: #e0efef; color: #000000 !important; font-weight: 800 !important; font-size: 12px; border-right: 2px solid #cbd5e1; }
    .lvl-macro .dual-cell.prev { color: #4b5563 !important; font-weight: 800; background: transparent; border-right: 1px dashed #cbd5e1;}
    .lvl-macro .dual-cell.real { color: #000000 !important; font-weight: 900; background: transparent;}
    
    .lvl-subgrupo { background-color: #ffffff; }
    .lvl-subgrupo .col-name { background-color: #ffffff; font-weight: 700; color: #000000; } 
    
    .lvl-item { background-color: #fbfcfd; }
    .lvl-item .col-name { background-color: #fbfcfd; padding-left: 35px; font-size: 10px; color: #000000; font-weight: 500; } 
    .lvl-item .dual-cell.real { font-size: 11px; font-weight: 500; color: #000000; } 

    /* Linhas de Resultado */
    .res-r1 { background-color: #f8fafc; }
    .res-r1 .col-name { background-color: #f8fafc; font-weight: 800; color: #172033; }
    .res-r1 .dual-cell.real { font-weight: 800; color: #000000; }
    
    .res-r2 { background-color: #ffffff; }
    .res-r2 .col-name { background-color: #ffffff; font-weight: 800; color: var(--primary); }
    .res-r2 .dual-cell.real { font-weight: 800; color: var(--primary); }
    
    .res-r6 { background-color: #ccebdc; border-top: 2px solid #1cc88a; border-bottom: 2px solid #1cc88a;}
    .res-r6 .col-name { background-color: #ccebdc; font-weight: 900; color: #000000 !important; border-right: 2px solid #cbd5e1;}
    .res-r6 .dual-cell.prev { font-weight: 800; color: #4b5563 !important; background: transparent; border-right: 1px dashed #cbd5e1;}
    .res-r6 .dual-cell.real { font-weight: 900; color: #000000 !important; background: transparent;}

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

def formatar_moeda(valor):
    try:
        val = float(valor)
        if val == 0: return "-"
        return f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception: return "-"

# Função para identificar exatamente o tipo de conta igual ao Dashboard Saldo
def definir_tipo(nome): 
    n_norm = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('utf-8').lower()
    if 'getnet' in n_norm: return 'Limite'
    return 'Aplicação' if ('aplicacao' in n_norm or 'investimento' in n_norm) else 'Disponível'

# ==============================================================================
# 3. FILTRO LATERAL
# ==============================================================================
ano_atual = datetime.now().year
mes_atual = datetime.now().month
anos_disponiveis = [ano_atual - 2, ano_atual - 1, ano_atual, ano_atual + 1]

with st.sidebar:
    st.markdown("### Filtros de Análise")
    ano_selecionado = st.selectbox("Ano de Referência:", anos_disponiveis, index=2)
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    st.markdown("### Relatório")
    st.info("💡 Role para os lados para ver os meses. A primeira coluna é fixa.", icon="ℹ️")
    components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }" 
        style="width:100%; background:linear-gradient(135deg, #008A8C, #004D4E); color:white; border:none; padding:12px; border-radius:8px; font-family:sans-serif; font-weight:bold; font-size:14px; cursor:pointer; box-shadow: 0 4px 6px rgba(0, 138, 140, 0.2); transition: transform 0.2s;">
        🖨️ Salvar Matriz (PDF)
        </button>
    """, height=55)

# ==============================================================================
# 4. CARGA DE DADOS (V9: MATEMÁTICA IDÊNTICA AO SALDO)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_matriz_fluxo_v9(ano):
    conn = conectar_sheets()
    if not conn: return pd.DataFrame(), 0.0, 0.0
    
    saldo_base = 0.0
    try:
        df_si = conn.read(worksheet="Saldo_Inicial", ttl=0)
        if not df_si.empty:
            col_banco_si = df_si.columns[0]
            col_valor_si = df_si.columns[1] if len(df_si.columns) > 1 else df_si.columns[0]
            df_si['Vl'] = df_si[col_valor_si].apply(limpa_valor_bruto)
            df_si['Tipo'] = df_si[col_banco_si].apply(definir_tipo)
            # Saldos apenas de Disponível e Aplicação (Sem Getnet/Limites)
            saldo_base = df_si[df_si['Tipo'].isin(['Disponível', 'Aplicação'])]['Vl'].sum()
    except Exception: pass

    try:
        df_ext = conn.read(worksheet="Extratos_Bancos", ttl=0)
        if df_ext.empty: return pd.DataFrame(), saldo_base, 0.0
        
        while len(df_ext.columns) < 13: df_ext[f"Col_Extra_{len(df_ext.columns)}"] = ""
        
        col_banco = df_ext.columns[0]     # (A)
        col_data = df_ext.columns[1]      # (B)
        col_deb = df_ext.columns[4]       # (E)
        col_cred = df_ext.columns[5]      # (F)
        col_tipo = df_ext.columns[7]      # (H)
        col_classif = df_ext.columns[9]   # (J) CLASSIFICAÇÃO FINANCEIRA
        col_operac = df_ext.columns[10]   # (K) OPERACIONALIDADE
        col_fornecedor = df_ext.columns[12] # (M) RESUMO FORNECEDOR

        # Tratamento da Data e Valores
        df_ext['Data'] = pd.to_datetime(df_ext[col_data], dayfirst=True, errors='coerce')
        df_ext = df_ext.dropna(subset=['Data']).copy()
        df_ext['Ano'] = df_ext['Data'].dt.year
        df_ext['Mes'] = df_ext['Data'].dt.month
        df_ext['Vl_Deb'] = df_ext[col_deb].apply(limpa_valor_bruto)
        df_ext['Vl_Cred'] = df_ext[col_cred].apply(limpa_valor_bruto)
        
        # Identificação de Contas (Igual Painel Saldo)
        df_ext['Banco'] = df_ext[col_banco].astype(str)
        df_ext['Tipo_Conta'] = df_ext['Banco'].apply(definir_tipo)
        
        # Filtra Transferências
        def norm_txt(txt): return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower() if pd.notna(txt) else ""
        serie_tipo = df_ext[col_tipo].apply(norm_txt)
        is_transf = serie_tipo.str.contains('transferencia') & serie_tipo.str.contains('interna')
        
        # ---------------------------------------------------------------------
        # PASSO 1: CALCULAR SALDOS GLOBAIS ABSOLUTOS (INCLUINDO NÃO-OP)
        # ---------------------------------------------------------------------
        # Apenas transferências são excluídas do cálculo do saldo global
        df_valid_balance = df_ext[(~is_transf) & (df_ext['Tipo_Conta'].isin(['Disponível', 'Aplicação']))].copy()

        df_before = df_valid_balance[df_valid_balance['Data'] < f"{ano}-01-01"]
        saldo_inicio_ano = saldo_base + df_before['Vl_Cred'].sum() - df_before['Vl_Deb'].sum()

        df_up_to_now = df_valid_balance[df_valid_balance['Data'] <= pd.to_datetime(datetime.now().date())]
        saldo_atual_caixa = saldo_base + df_up_to_now['Vl_Cred'].sum() - df_up_to_now['Vl_Deb'].sum()

        # ---------------------------------------------------------------------
        # PASSO 2: FILTRAR DADOS APENAS DA MATRIZ OPERACIONAL (ANO SELECIONADO)
        # ---------------------------------------------------------------------
        df_op = df_ext[(~is_transf)].copy()
        df_op['Operacional'] = df_op[col_operac].fillna('').astype(str).str.strip().str.upper()
        df_op = df_op[df_op['Operacional'] == 'OPERACIONAL'].copy()
        
        df_op['Classificacao'] = df_op[col_classif].fillna('NÃO CLASSIFICADO').astype(str).str.strip().str.upper()
        df_op.loc[df_op['Classificacao'] == '', 'Classificacao'] = 'NÃO CLASSIFICADO'
        
        df_op['Descricao_Trans'] = df_op[col_fornecedor].fillna('SEM DESCRIÇÃO').astype(str).str.strip().str.upper()
        df_op.loc[df_op['Descricao_Trans'] == '', 'Descricao_Trans'] = 'SEM DESCRIÇÃO'
        
        df_ano = df_op[df_op['Ano'] == ano].copy()
            
        return df_ano, saldo_inicio_ano, saldo_atual_caixa
    
    except Exception as e:
        st.error(f"Erro interno: {e}")
        return pd.DataFrame(), 0.0, 0.0

df_ano, saldo_inicio_ano, saldo_atual = pd.DataFrame(), 0.0, 0.0

try:
    res = carregar_dados_matriz_fluxo_v9(ano_selecionado)
    if len(res) == 3:
        df_ano, saldo_inicio_ano, saldo_atual = res
except Exception as e:
    st.error(f"Erro ao extrair pacote de dados: {e}")

if df_ano.empty:
    st.warning(f"⚠️ Nenhuma movimentação operacional encontrada para o ano de {ano_selecionado}.")
    st.stop()

# ==============================================================================
# 5. CONSTRUÇÃO DA LÓGICA DE DADOS (JAN A DEZ)
# ==============================================================================
df_entradas = df_ano[df_ano['Vl_Cred'] > 0].copy()
df_entradas['Valor_Op'] = df_entradas['Vl_Cred']

df_saidas = df_ano[df_ano['Vl_Deb'] > 0].copy()
df_saidas['Valor_Op'] = df_saidas['Vl_Deb']

tot_ent = [0]*12
tot_sai = [0]*12
dummy_prev = [0]*12

for m in range(1, 13):
    idx = m - 1
    tot_ent[idx] = df_entradas[df_entradas['Mes'] == m]['Valor_Op'].sum()
    tot_sai[idx] = df_saidas[df_saidas['Mes'] == m]['Valor_Op'].sum()

# Calcula Resultados Finais da Matriz Operacional
l1_resultado = [tot_ent[i] - tot_sai[i] for i in range(12)]
l2_saldo_ant = [0]*12
l3_acumulado = [0]*12

# O saldo de Jan utiliza a variável que tem exata mesma matemática do Dash de Saldos
l2_saldo_ant[0] = saldo_inicio_ano
for i in range(12):
    if i > 0: l2_saldo_ant[i] = l3_acumulado[i-1]
    l3_acumulado[i] = l1_resultado[i] + l2_saldo_ant[i]

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
        <p>Visão Consolidada de Operações</p>
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
# 7. RENDERIZAÇÃO DA MATRIZ CSS GRID (AGRUPAMENTO POR NOMENCLATURA)
# ==============================================================================
meses_labels = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

def render_linha(nome, nivel, arr_prev, arr_real):
    tot_p = sum(arr_prev)
    tot_r = sum(arr_real)
    html = f"<div class='grid-row {nivel}'>"
    html += f"<div class='col-name'>{nome}</div>"
    
    for p, r in zip(arr_prev, arr_real):
        html += "<div class='col-val'>"
        html += "<div class='dual-col'>"
        # Sem cifra monetária para ficar limpo e alinhado
        html += f"<div class='dual-cell prev'>{formatar_moeda(p)}</div>"
        html += f"<div class='dual-cell real'>{formatar_moeda(r)}</div>"
        html += "</div></div>"
        
    html += "<div class='col-val total-col'>"
    html += "<div class='dual-col'>"
    html += f"<div class='dual-cell prev'>{formatar_moeda(tot_p)}</div>"
    html += f"<div class='dual-cell real'>{formatar_moeda(tot_r)}</div>"
    html += "</div></div></div>"
    return html

def build_drilldown(df_dados):
    html = ""
    classificacoes = sorted(df_dados['Classificacao'].unique())
    
    for classif in classificacoes:
        df_classif = df_dados[df_dados['Classificacao'] == classif]
        arr_real = [0]*12
        for m in range(1, 13):
            arr_real[m-1] = df_classif[df_classif['Mes'] == m]['Valor_Op'].sum()
            
        if sum(arr_real) > 0:
            html += "<details><summary>"
            html += render_linha(f"<span class='icon-expand'></span>{classif}", "lvl-subgrupo", dummy_prev, arr_real)
            html += "</summary>"
            
            forn_totais = df_classif.groupby('Descricao_Trans')['Valor_Op'].sum().sort_values(ascending=False)
            
            for trans_name in forn_totais.index:
                df_trans = df_classif[df_classif['Descricao_Trans'] == trans_name]
                arr_trans_real = [0]*12
                for m in range(1, 13):
                    arr_trans_real[m-1] = df_trans[df_trans['Mes'] == m]['Valor_Op'].sum()
                
                desc = trans_name[:65] + ("..." if len(trans_name) > 65 else "")
                html += render_linha(f"↳ {desc}", "lvl-item", dummy_prev, arr_trans_real)
                
            html += "</details>"
            
    return html

# Inicia montagem da estrutura HTML
html_matriz = "<div class='matrix-wrapper'><div class='matrix-grid'>"

# Header Dinâmico de Meses e Colunas Duplas (C/ ID DE MÊS PARA O SCROLL INTELIGENTE)
html_matriz += "<div class='grid-row grid-header'>"
html_matriz += "<div class='col-name' style='padding-left: 15px;'>DESCRIÇÃO DOS LANÇAMENTOS</div>"

for idx, m in enumerate(meses_labels): 
    html_matriz += f'''
    <div class='col-val' id='mes-{idx + 1}' style='padding:0;'>
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
html_matriz += build_drilldown(df_entradas)

html_matriz += "<div style='height: 15px; background: #f5f7fb;'></div>"

# BLOCO SAÍDAS
html_matriz += render_linha("SAÍDAS OPERACIONAIS", "lvl-macro", dummy_prev, tot_sai)
html_matriz += build_drilldown(df_saidas)

html_matriz += "<div style='height: 15px; background: #f5f7fb;'></div>"

# BLOCO DE RESULTADO SIMPLIFICADO
html_matriz += render_linha("(ENTRADAS - SAÍDAS)", "res-r1", dummy_prev, l1_resultado)
html_matriz += render_linha("SALDO ANTERIOR", "res-r2", dummy_prev, l2_saldo_ant)
html_matriz += render_linha("RESULTADO CAIXA", "res-r6", dummy_prev, l3_acumulado)

html_matriz += "</div></div>"

injetar_html(html_matriz)
st.markdown(f"<div style='font-size:9px; color:gray; text-align:right; margin-top:5px;'>Valores em Reais (R$) | Estrutura de previsão aguardando conexão de dados | Referência: {ano_selecionado}</div>", unsafe_allow_html=True)

# ==============================================================================
# 8. SCRIPT DE AUTOSCROLL (ROLA PARA O MÊS ATUAL AUTOMATICAMENTE)
# ==============================================================================
if ano_selecionado == ano_atual:
    js_scroll = f"""
    <script>
        setTimeout(function() {{
            var docs = window.parent.document;
            var wrapper = docs.querySelector('.matrix-wrapper');
            var targetCol = docs.getElementById('mes-{mes_atual}');
            
            if (wrapper && targetCol) {{
                var offset = targetCol.offsetLeft - 300; 
                wrapper.scrollTo({{left: offset, behavior: 'smooth'}});
            }}
        }}, 800);
    </script>
    """
    components.html(js_scroll, height=0, width=0)
