import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
# initial_sidebar_state="expanded" garante que ela sempre carregue aberta
st.set_page_config(page_title="Fluxo de Caixa Analítico", layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# 1. CUSTOM CSS — MINIMALISTA, GRID EXPANSÍVEL, MENU FIXO E IMPRESSÃO (PDF)
# ==============================================================================
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f8fafc;
    --surface: #ffffff;
    --primary-dark: #0f172a;
    --primary: #3b82f6;
    --success: #10b981;
    --danger: #ef4444;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 2rem; }

/* 🔴 LIMPEZA DO TOPO E TRAVA DO MENU LATERAL (FIXO) */
header[data-testid="stHeader"] { display: none !important; }
/* Remove o botão de fechar dentro do menu lateral */
[data-testid="stSidebarCollapseButton"] { display: none !important; }
/* Remove qualquer controle de colapso residual */
[data-testid="collapsedControl"] { display: none !important; }

/* HEADER PRINCIPAL MINIMALISTA */
.exec-header { background: transparent; padding: 10px 0 20px 0; border-bottom: 2px solid var(--border); display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
.exec-header h1 { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: 0.5px; color: var(--primary-dark); text-transform: uppercase;}
.exec-header p { margin: 2px 0 0 0; font-size: 12px; font-weight: 500; color: var(--text-muted); }
.exec-filters { display: flex; gap: 20px; align-items: center; }
.exec-filter-item { display: flex; flex-direction: column; }
.exec-filter-item label { font-size: 10px; font-weight: 700; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase; }
.exec-filter-item .val { background: var(--surface); color: var(--text-main); border: 1px solid var(--border); padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; min-width: 130px; display: flex; justify-content: space-between; box-shadow: var(--shadow); }
.exec-update { border-left: 1px solid var(--border); padding-left: 20px; display: flex; flex-direction: column; justify-content: center; }
.exec-update span { font-size: 10px; color: var(--text-muted); display:block; text-transform: uppercase; font-weight: 700; }
.exec-update b { font-size: 12px; font-weight: 700; color: var(--primary-dark); display:block;}

/* KPI CARDS */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 20px; position: relative; box-shadow: var(--shadow); }
.kpi-card::after { content: ""; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; border-radius: 0 0 6px 6px; }
.kpi-card.c-blue::after { background: var(--primary); }
.kpi-card.c-green::after { background: var(--success); }
.kpi-card.c-red::after { background: var(--danger); }
.kpi-top { display: flex; align-items: flex-start; margin-bottom: 12px;}
.kpi-info { flex: 1; }
.kpi-title { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;}
.kpi-val { font-size: 26px; font-weight: 800; color: var(--primary-dark); letter-spacing: -0.5px; line-height: 1.1; }
.kpi-meta-box { border-top: 1px dashed var(--border); padding-top: 12px; display: flex; justify-content: space-between; align-items: center; }
.kpi-meta-box span { font-size: 11px; color: var(--text-muted); font-weight: 600;}
.kpi-var { font-size: 12px; font-weight: 800; display:flex; align-items:center; gap:3px;}
.var-up { color: var(--success); }
.var-down { color: var(--danger); }

/* MATRIZ CSS GRID EXPANSÍVEL */
.matrix-container { background: var(--surface); border-radius: 6px; overflow: hidden; box-shadow: var(--shadow); border: 1px solid var(--border); margin-bottom: 30px;}
.matrix-header { background: #f8fafc; color: var(--primary-dark); padding: 15px 20px; font-size: 14px; font-weight: 800; text-transform: uppercase; border-bottom: 2px solid var(--border); letter-spacing: 0.5px;}
.grid-row { display: grid; border-bottom: 1px solid var(--border); align-items: center; transition: background 0.1s; }
.grid-row:hover { background-color: #f1f5f9; }

.col-name { padding: 10px 15px; font-weight: 600; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.col-val { padding: 10px 15px; text-align: right; font-variant-numeric: tabular-nums; color: var(--text-main); font-weight: 600; white-space: nowrap; }

/* Cabeçalhos da Matriz */
.grid-header { background: var(--surface); font-weight: 800; color: var(--text-muted); font-size: 10px; text-transform: uppercase; border-bottom: 2px solid var(--border); }
.grid-header .col-val { text-align: center; }
.border-left { border-left: 1px solid var(--border); }

/* Níveis da Matriz */
.lvl-macro { background-color: #f8fafc; font-size: 13px; }
.lvl-macro .col-name { font-weight: 800; color: var(--primary-dark); text-transform: uppercase; }
.lvl-macro .col-val { font-weight: 800; color: var(--primary-dark); }

.lvl-grupo .col-name { padding-left: 15px; font-size: 12px; font-weight: 700; color: var(--primary-dark); }
.lvl-subgrupo .col-name { padding-left: 40px; font-size: 11px; font-weight: 600; color: var(--text-secondary); }

/* Linha de Transação Final */
.lvl-item { background-color: #ffffff; }
.lvl-item:hover { background-color: #fefefe; }
.lvl-item .col-name { padding-left: 65px; font-size: 10px; font-weight: 500; color: var(--text-muted); }
.lvl-item .col-val { font-size: 11px; font-weight: 500; color: var(--text-muted); }

/* Details e Summary */
details { width: 100%; display: block; margin: 0; padding: 0; }
details summary { list-style: none; cursor: pointer; outline: none; margin: 0; padding: 0; }
details summary::-webkit-details-marker { display: none; }
.icon-expand { font-family: monospace; font-weight: 800; color: var(--primary); margin-right: 8px; font-size: 14px; display: inline-block; width: 12px; text-align: center;}
details:not([open]) > summary .icon-expand::before { content: "+"; }
details[open] > summary .icon-expand::before { content: "-"; }

/* =========================================================
   MODO IMPRESSÃO (PDF DE ALTA QUALIDADE VETORIAL)
   ========================================================= */
@media print {
    [data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .main .block-container { max-width: 100% !important; padding: 10px !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; color-adjust: exact !important; }
    .kpi-card, .matrix-container { break-inside: avoid; }
    details[open] summary ~ * { display: block; }
    details summary { list-style: none; }
}
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

def injetar_html(codigo_html):
    st.markdown(codigo_html.replace('\n', ''), unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES E LEITURA DE DADOS
# ==============================================================================
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

def limpa_valor(valor):
    try:
        if pd.isna(valor): return 0.0
        v = str(valor).replace('R$', '').strip()
        if '.' in v and ',' in v: v = v.replace('.', '').replace(',', '.')
        elif ',' in v: v = v.replace(',', '.')
        return float(v)
    except: return 0.0

def formata_num(valor):
    if pd.isna(valor) or valor == 0: return "-"
    return f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def calc_var(atual, anterior):
    if anterior == 0: return 0
    return ((atual - anterior) / abs(anterior)) * 100

@st.cache_data(ttl=60)
def preparar_dados_fluxo():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()
    try:
        df = conn.read(worksheet="Extratos_Bancos", ttl=0)
        
        # Mapeamento Estrito das Colunas Solicitadas
        col_data = df.columns[1]     # B
        col_desc = df.columns[2]     # C
        col_deb = df.columns[4]      # E
        col_cred = df.columns[5]     # F
        col_conta = df.columns[8]    # I (Conta Contábil)
        col_classif = df.columns[9]  # J (Classificação Financeira)
        col_operac = df.columns[10]  # K (Operacionalidade)

        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Saída'] = df[col_deb].apply(limpa_valor)
        df['Entrada'] = df[col_cred].apply(limpa_valor)
        df['Valor Líquido'] = df['Entrada'] - df['Saída']
        
        df['Conta_Str'] = df[col_conta].astype(str).str.strip().str.upper()
        df = df[~df['Conta_Str'].str.contains("TRANSFERÊNCIA INTERNA", na=False)]
        
        df['Conta'] = df[col_conta].fillna('Não Informado').astype(str).str.strip()
        df['Classificacao'] = df[col_classif].fillna('Não Classificado').astype(str).str.strip()
        df['Descricao'] = df[col_desc].fillna('Lançamento S/ Descrição').astype(str).str.strip()
        df['Operacionalidade'] = df[col_operac].fillna('OPERACIONAL').astype(str).str.strip().str.upper()
        
        df.loc[df['Conta'] == '', 'Conta'] = 'Não Informado'
        df.loc[df['Classificacao'] == '', 'Classificacao'] = 'Não Classificado'
        
        return df[df['Data'].notna()]
    except Exception as e:
        st.error(f"Erro ao ler os dados: {e}")
        return pd.DataFrame()

df_base = preparar_dados_fluxo()
if df_base.empty: st.stop()

# ==============================================================================
# 3. FILTROS LATERAIS E NAVEGAÇÃO FIXA
# ==============================================================================
hoje = datetime.now().date()
primeiro_dia_mes = hoje.replace(day=1)

with st.sidebar:
    st.markdown("### Filtros de Análise")
    data_selecionada = st.date_input("Selecione o Período:", value=(primeiro_dia_mes, hoje), format="DD/MM/YYYY")
    
    st.markdown("<hr style='margin: 15px 0 10px;'>", unsafe_allow_html=True)
    st.markdown("### Relatório")
    st.info("💡 Para um relatório de alta qualidade, gere um PDF. Escolha a orientação **Retrato** ou **Paisagem** e desmarque 'Cabeçalhos/Rodapés'.", icon="ℹ️")
    components.html("""
        <button onclick="try { window.parent.print(); } catch(e) { window.print(); }" 
        style="width:100%; background:linear-gradient(135deg, #3b82f6, #1e40af); color:white; border:none; padding:12px; border-radius:8px; font-family:sans-serif; font-weight:bold; font-size:14px; cursor:pointer; box-shadow: 0 4px 6px rgba(30, 64, 175, 0.2); transition: transform 0.2s;">
        🖨️ Salvar Dashboard (PDF)
        </button>
    """, height=55)

if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
    dt_ini, dt_fim = data_selecionada
else:
    dt_ini = data_selecionada[0] if isinstance(data_selecionada, tuple) else data_selecionada
    dt_fim = dt_ini

mask_atual = (df_base['Data'].dt.date >= dt_ini) & (df_base['Data'].dt.date <= dt_fim)
dias_periodo = (dt_fim - dt_ini).days + 1
dt_fim_ant = dt_ini - timedelta(days=1)
dt_ini_ant = dt_fim_ant - timedelta(days=dias_periodo - 1)
mask_ant = (df_base['Data'].dt.date >= dt_ini_ant) & (df_base['Data'].dt.date <= dt_fim_ant)

df_op_atual = df_base[mask_atual & (df_base['Operacionalidade'] == 'OPERACIONAL')].copy()
df_op_ant = df_base[mask_ant & (df_base['Operacionalidade'] == 'OPERACIONAL')].copy()

df_nop_atual = df_base[mask_atual & (df_base['Operacionalidade'] == 'NÃO OPERACIONAL')].copy()
df_nop_ant = df_base[mask_ant & (df_base['Operacionalidade'] == 'NÃO OPERACIONAL')].copy()

# ==============================================================================
# 4. KPIs (BASEADOS APENAS NO OPERACIONAL)
# ==============================================================================
tot_entrada_at = df_op_atual['Entrada'].sum()
tot_saida_at = df_op_atual['Saída'].sum()
geracao_liq_at = tot_entrada_at - tot_saida_at
eficiencia_at = (tot_saida_at / tot_entrada_at * 100) if tot_entrada_at > 0 else 0

tot_entrada_ant = df_op_ant['Entrada'].sum()
tot_saida_ant = df_op_ant['Saída'].sum()
geracao_liq_ant = tot_entrada_ant - tot_saida_ant
eficiencia_ant = (tot_saida_ant / tot_entrada_ant * 100) if tot_entrada_ant > 0 else 0

periodo_str = f"{dt_ini.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}"
header_html = f"""
<div class='exec-header'>
    <div>
        <h1>Fluxo de Caixa Analítico</h1>
        <p>Visão Exclusiva de Entradas e Saídas Operacionais (Regime de Caixa)</p>
    </div>
    <div class='exec-filters'>
        <div class='exec-filter-item'><label>Período Selecionado</label><div class='val'>{periodo_str}</div></div>
        <div class='exec-update'><span>Última Atualização</span><b>{datetime.now().strftime('%d/%m/%Y %H:%M')}</b></div>
    </div>
</div>
"""
injetar_html(header_html)

def html_var(atual, ant, is_invertido=False):
    val = calc_var(abs(atual), abs(ant))
    if is_invertido: cor = "var-down" if val >= 0 else "var-up"
    else: cor = "var-up" if val >= 0 else "var-down"
    seta = "▲" if val >= 0 else "▼"
    return f"<div class='kpi-var {cor}'><span>{seta}</span> {abs(val):.1f}%</div>"

kpis_html = f"""<div class='kpi-row'>
<div class='kpi-card c-green'><div class='kpi-top'><div class='kpi-info'><div class='kpi-title'>Entradas Operacionais</div><div class='kpi-val'>R$ {formata_num(tot_entrada_at)}</div></div></div><div class='kpi-meta-box'><span>Anterior: R$ {formata_num(tot_entrada_ant)}</span>{html_var(tot_entrada_at, tot_entrada_ant)}</div></div>
<div class='kpi-card c-red'><div class='kpi-top'><div class='kpi-info'><div class='kpi-title'>Saídas Operacionais</div><div class='kpi-val'>R$ {formata_num(tot_saida_at)}</div></div></div><div class='kpi-meta-box'><span>Anterior: R$ {formata_num(tot_saida_ant)}</span>{html_var(tot_saida_at, tot_saida_ant, True)}</div></div>
<div class='kpi-card c-blue'><div class='kpi-top'><div class='kpi-info'><div class='kpi-title'>Geração Líquida (Cash Flow)</div><div class='kpi-val'>R$ {formata_num(geracao_liq_at)}</div></div></div><div class='kpi-meta-box'><span>Anterior: R$ {formata_num(geracao_liq_ant)}</span>{html_var(geracao_liq_at, geracao_liq_ant)}</div></div>
<div class='kpi-card c-blue'><div class='kpi-top'><div class='kpi-info'><div class='kpi-title'>Taxa de Consumo</div><div class='kpi-val'>{eficiencia_at:.1f}%</div></div></div><div class='kpi-meta-box'><span>Anterior: {eficiencia_ant:.1f}%</span></div></div>
</div>"""
injetar_html(kpis_html)

# ==============================================================================
# 5. MATRIZ EXPANSÍVEL (GRID HTML5)
# ==============================================================================
grid_cols = "minmax(350px, 2fr) 130px 100px 130px 90px"

def render_linha(nome, classe, val_at, rep_pct, val_ant, var_pct, cor_var, is_item=False):
    html = f"<div class='grid-row {classe}' style='grid-template-columns: {grid_cols};'>"
    html += f"<div class='col-name'>{nome}</div>"
    
    if is_item:
        html += f"<div class='col-val'>R$ {formata_num(val_at)}</div>"
        html += f"<div class='col-val'>-</div><div class='col-val'>-</div><div class='col-val'>-</div>"
    else:
        sinal = "+" if var_pct > 0 else ""
        html += f"<div class='col-val border-left'>R$ {formata_num(val_at)}</div>"
        html += f"<div class='col-val border-left' style='font-size:11px; color:var(--text-muted); text-align:center;'>{rep_pct:.1f}%</div>"
        html += f"<div class='col-val border-left' style='color:var(--text-muted);'>R$ {formata_num(val_ant)}</div>"
        html += f"<div class='col-val border-left' style='color:{cor_var}; font-size:11px; font-weight:800; text-align:center;'>{sinal}{var_pct:.1f}%</div>"
        
    html += "</div>"
    return html

def renderizar_estrutura(df_at, df_ant, col_valor, total_periodo, is_saida=False):
    html = ""
    if df_at.empty and df_ant.empty: return html
    
    contas_at = df_at.groupby('Conta')[col_valor].sum().to_dict()
    contas_ant = df_ant.groupby('Conta')[col_valor].sum().to_dict()
    chaves_conta = sorted(set(list(contas_at.keys()) + list(contas_ant.keys())), key=lambda k: contas_at.get(k, 0), reverse=True)
    
    for conta in chaves_conta:
        v_conta_at = contas_at.get(conta, 0)
        v_conta_ant = contas_ant.get(conta, 0)
        rep_conta = (v_conta_at / total_periodo * 100) if total_periodo > 0 else 0
        var_conta = calc_var(v_conta_at, v_conta_ant)
        
        if is_saida: cor_conta = "var(--danger)" if var_conta > 0 else "var(--success)"
        else: cor_conta = "var(--success)" if var_conta > 0 else "var(--danger)"
            
        html += "<details><summary>"
        html += render_linha(f"<span class='icon-expand'></span>{conta}", "lvl-grupo", v_conta_at, rep_conta, v_conta_ant, var_conta, cor_conta)
        html += "</summary>"
        
        df_at_c = df_at[df_at['Conta'] == conta]
        df_ant_c = df_ant[df_ant['Conta'] == conta]
        
        classif_at = df_at_c.groupby('Classificacao')[col_valor].sum().to_dict()
        classif_ant = df_ant_c.groupby('Classificacao')[col_valor].sum().to_dict()
        chaves_classif = sorted(set(list(classif_at.keys()) + list(classif_ant.keys())), key=lambda k: classif_at.get(k, 0), reverse=True)
        
        for classif in chaves_classif:
            v_classif_at = classif_at.get(classif, 0)
            v_classif_ant = classif_ant.get(classif, 0)
            rep_classif = (v_classif_at / total_periodo * 100) if total_periodo > 0 else 0
            var_classif = calc_var(v_classif_at, v_classif_ant)
            
            if is_saida: cor_classif = "var(--danger)" if var_classif > 0 else "var(--success)"
            else: cor_classif = "var(--success)" if var_classif > 0 else "var(--danger)"
                
            html += "<details><summary>"
            html += render_linha(f"<span class='icon-expand'></span>{classif}", "lvl-subgrupo", v_classif_at, rep_classif, v_classif_ant, var_classif, cor_classif)
            html += "</summary>"
            
            df_trans = df_at_c[df_at_c['Classificacao'] == classif].sort_values('Data')
            for _, row in df_trans.iterrows():
                dt_str = row['Data'].strftime('%d/%m')
                desc = row['Descricao'][:50] + ("..." if len(row['Descricao']) > 50 else "")
                html += render_linha(f"↳ {dt_str} - {desc}", "lvl-item", row[col_valor], 0, 0, 0, "", is_item=True)
                
            html += "</details>"
        html += "</details>"
        
    return html

# ----------------- TABELA OPERACIONAL -----------------
html_tab = f"""
<div class='matrix-container'>
    <div class='matrix-header'>Fluxo Operacional</div>
    <div class='grid-row grid-header' style='grid-template-columns: {grid_cols};'>
        <div class='col-name'>Nível (Conta ➔ Classificação ➔ Transação)</div>
        <div class='col-val border-left'>Realizado ({dt_fim.strftime('%b').capitalize()})</div>
        <div class='col-val border-left'>% Rep.</div>
        <div class='col-val border-left'>Período Anterior</div>
        <div class='col-val border-left'>Var. (MoM)</div>
    </div>
"""

var_tot_ent = calc_var(tot_entrada_at, tot_entrada_ant)
cor_tot_ent = "var(--success)" if var_tot_ent >= 0 else "var(--danger)"
html_tab += render_linha("[+] ENTRADAS OPERACIONAIS", "lvl-macro", tot_entrada_at, 100, tot_entrada_ant, var_tot_ent, cor_tot_ent)
html_tab += renderizar_estrutura(df_op_atual[df_op_atual['Entrada'] > 0], df_op_ant[df_op_ant['Entrada'] > 0], 'Entrada', tot_entrada_at, is_saida=False)

var_tot_sai = calc_var(tot_saida_at, tot_saida_ant)
cor_tot_sai = "var(--danger)" if var_tot_sai >= 0 else "var(--success)"
html_tab += render_linha("[-] SAÍDAS OPERACIONAIS", "lvl-macro", tot_saida_at, 100, tot_saida_ant, var_tot_sai, cor_tot_sai)
html_tab += renderizar_estrutura(df_op_atual[df_op_atual['Saída'] > 0], df_op_ant[df_op_ant['Saída'] > 0], 'Saída', tot_saida_at, is_saida=True)

html_tab += "</div>"
injetar_html(html_tab)

# ----------------- TABELA NÃO OPERACIONAL -----------------
tot_nop_ent_at = df_nop_atual['Entrada'].sum()
tot_nop_sai_at = df_nop_atual['Saída'].sum()

if tot_nop_ent_at > 0 or tot_nop_sai_at > 0:
    tot_nop_ent_ant = df_nop_ant['Entrada'].sum()
    tot_nop_sai_ant = df_nop_ant['Saída'].sum()
    
    html_nop = f"""
    <div class='matrix-container'>
        <div class='matrix-header' style='background: #f1f5f9; color: var(--text-muted); border-bottom: 2px solid var(--border);'>Fluxo Não Operacional (Financeiro/Investimentos)</div>
    """
    
    if tot_nop_ent_at > 0 or tot_nop_ent_ant > 0:
        var_nop_ent = calc_var(tot_nop_ent_at, tot_nop_ent_ant)
        cor_nop_ent = "var(--success)" if var_nop_ent >= 0 else "var(--danger)"
        html_nop += render_linha("[+] ENTRADAS NÃO OPERACIONAIS", "lvl-macro", tot_nop_ent_at, 100, tot_nop_ent_ant, var_nop_ent, cor_nop_ent)
        html_nop += renderizar_estrutura(df_nop_atual[df_nop_atual['Entrada'] > 0], df_nop_ant[df_nop_ant['Entrada'] > 0], 'Entrada', tot_nop_ent_at, is_saida=False)
        
    if tot_nop_sai_at > 0 or tot_nop_sai_ant > 0:
        var_nop_sai = calc_var(tot_nop_sai_at, tot_nop_sai_ant)
        cor_nop_sai = "var(--danger)" if var_nop_sai >= 0 else "var(--success)"
        html_nop += render_linha("[-] SAÍDAS NÃO OPERACIONAIS", "lvl-macro", tot_nop_sai_at, 100, tot_nop_sai_ant, var_nop_sai, cor_nop_sai)
        html_nop += renderizar_estrutura(df_nop_atual[df_nop_atual['Saída'] > 0], df_nop_ant[df_nop_ant['Saída'] > 0], 'Saída', tot_nop_sai_at, is_saida=True)

    html_nop += "</div>"
    injetar_html(html_nop)
