import streamlit as st
import pandas as pd
import re
from datetime import datetime
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DRE Gerencial Executivo", layout="wide", page_icon="📈")

# ==============================================================================
# 1. CUSTOM CSS — IDENTIDADE EXECUTIVA
# ==============================================================================
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f4f6f9;
    --surface: #ffffff;
    --primary-dark: #1e40af;
    --primary: #3b82f6;
    --success: #10b981;
    --danger: #ef4444;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow: 0 4px 12px rgba(30, 64, 175, 0.08);
}

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 98%; padding-top: 1rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }

/* HEADER PRINCIPAL */
.exec-header { background: var(--primary-dark); color: #fff; padding: 15px 25px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: var(--shadow); }
.exec-header h1 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 0.5px; }
.exec-header p { margin: 0; font-size: 12px; font-weight: 400; color: #bfdbfe; }
.exec-filters { display: flex; gap: 20px; align-items: center; }
.exec-filter-item { display: flex; flex-direction: column; }
.exec-filter-item label { font-size: 10px; font-weight: 600; color: #bfdbfe; margin-bottom: 4px; }
.exec-filter-item .val { background: #fff; color: var(--primary-dark); padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; min-width: 120px; display: flex; justify-content: space-between; }
.exec-update { border-left: 1px solid rgba(255,255,255,0.2); padding-left: 20px; display: flex; align-items: center; gap: 10px; }
.exec-update span { font-size: 10px; color: #bfdbfe; display:block; }
.exec-update b { font-size: 12px; font-weight: 700; display:block;}

/* KPI CARDS */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 25px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px 22px 20px; position: relative; box-shadow: var(--shadow); }
.kpi-card::after { content: ""; position: absolute; bottom: 0; left: 20px; right: 20px; height: 5px; border-radius: 5px 5px 0 0; }
.kpi-card.c-blue::after { background: var(--primary); }
.kpi-card.c-green::after { background: var(--success); }
.kpi-top { display: flex; gap: 15px; align-items: flex-start; margin-bottom: 12px;}
.kpi-icon { width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; font-weight: bold;}
.c-blue .kpi-icon { background: #eff6ff; color: var(--primary); }
.c-green .kpi-icon { background: #ecfdf5; color: var(--success); }
.kpi-info { flex: 1; }
.kpi-title { font-size: 11px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px; }
.kpi-val { font-size: 24px; font-weight: 800; color: var(--text-main); letter-spacing: -0.5px; line-height: 1.1; }
.kpi-meta-box { border-top: 1px solid var(--border); padding-top: 10px; display: flex; justify-content: space-between; align-items: center; }
.kpi-meta-box span { font-size: 11px; color: var(--text-muted); font-weight: 600;}
.kpi-var { font-size: 12px; font-weight: 800; display:flex; align-items:center; gap:3px;}
.var-up { color: var(--success); }
.var-down { color: var(--danger); }

/* MATRIZ DRE EXECUTIVA */
.matrix-container { background: var(--surface); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); border: 1px solid var(--border);}
.matrix-header { background: var(--primary-dark); color: #fff; padding: 12px 20px; font-size: 15px; font-weight: 800; display:flex; align-items:center; gap:8px;}
.dre-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.dre-table th { background: #f8fafc; color: var(--primary-dark); font-weight: 700; text-align: right; padding: 12px 15px; border-bottom: 2px solid var(--border); border-left: 1px solid var(--border); }
.dre-table th:first-child { text-align: left; border-left: none; }
.dre-table td { padding: 12px 15px; text-align: right; border-bottom: 1px solid var(--border); font-weight: 600; color: var(--text-main); }
.dre-table td:first-child { text-align: left; }
.dre-table tr:nth-child(even) td { background-color: #f8fafc; }
.dre-table tr:hover td { background-color: #f1f5f9; }
.row-macro td { font-weight: 800 !important; background-color: #eff6ff !important; color: var(--primary-dark) !important; font-size: 14px;}
</style>
"""
st.markdown(textwrap.dedent(css), unsafe_allow_html=True)

def injetar_html(codigo_html):
    st.markdown(codigo_html.replace('\n', ''), unsafe_allow_html=True)

# ==============================================================================
# 2. LÓGICA E MATEMÁTICA
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
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_kpi(valor):
    if pd.isna(valor): return "0"
    return f"{valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formata_pct(valor):
    if pd.isna(valor) or valor == 0: return "0%"
    return f"{valor:.1f}%".replace('.', ',')

def calc_var(atual, anterior):
    if anterior == 0: return 0
    return ((atual - anterior) / abs(anterior)) * 100

def classificar_conta(nome_conta):
    conta = str(nome_conta).upper().strip()
    convênios = ["UNIMED", "SC SAÚDE", "TEMPOMED", "CASSI", "BRADESCO SAÚDE", "GEAP", "CORREIOS", "CASACARESC", "CAIXA", "FUNCEF", "CELOS", "AMIL", "FUSEX", "SULAMÉRICA", "MARINHA", "PETROBRÁS", "CAPESAUDE", "SIM SAÚDE"]
    if any(c in conta for c in convênios) or "PARTICULAR" in conta or "CARTÃO" in conta: return "Receita Bruta"
    if any(c in conta for c in ["PESSOAL", "SALÁRIO", "INSS", "HONORÁRIOS", "MÉDICO", "FORNECEDORES", "CUSTO", "MEDICAMENTOS", "OPME"]): return "CPV/CSP"
    if any(c in conta for c in ["IMPOSTOS", "DAS", "COFINS", "PIS", "IRPJ", "CSLL"]): return "Deduções"
    if any(c in conta for c in ["ADMINISTRATIV", "INFRAESTRUTURA", "ALUGUEL", "ENERGIA", "INTERNET", "CONTABILIDADE"]): return "OPEX"
    return "Outros"

@st.cache_data(ttl=60)
def preparar_dados_dre():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()
    try:
        df = conn.read(worksheet="Extratos_Bancos", ttl=0)
        col_data, col_deb, col_cred, col_conta = df.columns[1], df.columns[4], df.columns[5], df.columns[8]
        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Débito'] = df[col_deb].apply(limpa_valor)
        df['Crédito'] = df[col_cred].apply(limpa_valor)
        df['Valor Líquido'] = df['Crédito'] - df['Débito']
        df['Mês_Ano'] = df['Data'].dt.to_period('M')
        df['Macro'] = df[col_conta].apply(classificar_conta)
        return df[df['Data'].notna()]
    except Exception as e:
        return pd.DataFrame()

df_base = preparar_dados_dre()
if df_base.empty: st.stop()

meses_disponiveis = sorted(df_base['Mês_Ano'].unique())
mes_atual = meses_disponiveis[-1]
mes_anterior = meses_disponiveis[-2] if len(meses_disponiveis) > 1 else mes_atual

def get_val(macro, mes):
    return df_base[(df_base['Macro'] == macro) & (df_base['Mês_Ano'] == mes)]['Valor Líquido'].sum()

# Matemática Mês Atual
rec_bruta = get_val("Receita Bruta", mes_atual)
deducoes = get_val("Deduções", mes_atual)
rec_liq = rec_bruta + deducoes
cpv = get_val("CPV/CSP", mes_atual)
lucro_bruto = rec_liq + cpv
opex = get_val("OPEX", mes_atual)
ebitda = lucro_bruto + opex
outros = get_val("Outros", mes_atual)
lucro_liq = ebitda + outros

# Matemática Mês Anterior
ant_rec_bruta = get_val("Receita Bruta", mes_anterior)
ant_deducoes = get_val("Deduções", mes_anterior)
ant_rec_liq = ant_rec_bruta + ant_deducoes
ant_cpv = get_val("CPV/CSP", mes_anterior)
ant_lucro_bruto = ant_rec_liq + ant_cpv
ant_opex = get_val("OPEX", mes_anterior)
ant_ebitda = ant_lucro_bruto + ant_opex
ant_outros = get_val("Outros", mes_anterior)
ant_lucro_liq = ant_ebitda + ant_outros

mg_bruta = (lucro_bruto / rec_bruta * 100) if rec_bruta else 0
mg_ebitda = (ebitda / rec_bruta * 100) if rec_bruta else 0
ant_mg_bruta = (ant_lucro_bruto / ant_rec_bruta * 100) if ant_rec_bruta else 0
ant_mg_ebitda = (ant_ebitda / ant_rec_bruta * 100) if ant_rec_bruta else 0

# ==============================================================================
# 3. CONSTRUÇÃO DO HTML (HEADER E KPIs)
# ==============================================================================
nome_mes_atual = pd.Period(mes_atual).strftime('%B/%Y').capitalize()
nome_mes_anterior = pd.Period(mes_anterior).strftime('%B/%Y').capitalize()
data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')

st.markdown(f"<div class='exec-header'><div><h1>DRE GERENCIAL EXECUTIVO</h1><p>Análise de Resultados • Performance • Tomada de Decisão</p></div><div class='exec-filters'><div class='exec-filter-item'><label>Período</label><div class='val'>{nome_mes_atual} <span>▼</span></div></div><div class='exec-filter-item'><label>Unidade</label><div class='val'>Todas <span>▼</span></div></div><div class='exec-filter-item'><label>Centro de Custo</label><div class='val'>Todos <span>▼</span></div></div><div class='exec-update'><span style='font-size:20px;'>📅</span><div><span>Última Atualização</span><b>{data_hoje}</b></div></div></div></div>", unsafe_allow_html=True)

def html_var(atual, ant, is_margin=False):
    val = (atual - ant) if is_margin else calc_var(abs(atual), abs(ant))
    cor = "var-up" if val >= 0 else "var-down"
    seta = "▲" if val >= 0 else "▼"
    suf = "p.p." if is_margin else "%"
    return f"<div class='kpi-var {cor}'><span>{seta}</span> {abs(val):.1f}{suf}</div>"

st.markdown(f"<div class='kpi-row'><div class='kpi-card c-blue'><div class='kpi-top'><div class='kpi-icon'>💰</div><div class='kpi-info'><div class='kpi-title'>Receita Bruta</div><div class='kpi-val'>R$ {formata_kpi(rec_bruta)}</div></div></div><div class='kpi-meta-box'><span>Mês Anterior: R$ {formata_kpi(ant_rec_bruta)}</span>{html_var(rec_bruta, ant_rec_bruta)}</div></div><div class='kpi-card c-green'><div class='kpi-top'><div class='kpi-icon'>%</div><div class='kpi-info'><div class='kpi-title'>Margem Bruta</div><div class='kpi-val'>{mg_bruta:.1f}%</div></div></div><div class='kpi-meta-box'><span>Mês Anterior: {ant_mg_bruta:.1f}%</span>{html_var(mg_bruta, ant_mg_bruta, True)}</div></div><div class='kpi-card c-green'><div class='kpi-top'><div class='kpi-icon'>📊</div><div class='kpi-info'><div class='kpi-title'>EBITDA</div><div class='kpi-val'>R$ {formata_kpi(ebitda)}</div></div></div><div class='kpi-meta-box'><span>Mês Anterior: R$ {formata_kpi(ant_ebitda)}</span>{html_var(ebitda, ant_ebitda)}</div></div><div class='kpi-card c-green'><div class='kpi-top'><div class='kpi-icon'>📈</div><div class='kpi-info'><div class='kpi-title'>Margem EBITDA</div><div class='kpi-val'>{mg_ebitda:.1f}%</div></div></div><div class='kpi-meta-box'><span>Mês Anterior: {ant_mg_ebitda:.1f}%</span>{html_var(mg_ebitda, ant_mg_ebitda, True)}</div></div><div class='kpi-card c-blue'><div class='kpi-top'><div class='kpi-icon'>$</div><div class='kpi-info'><div class='kpi-title'>Lucro Líquido</div><div class='kpi-val'>R$ {formata_kpi(lucro_liq)}</div></div></div><div class='kpi-meta-box'><span>Mês Anterior: R$ {formata_kpi(ant_lucro_liq)}</span>{html_var(lucro_liq, ant_lucro_liq)}</div></div></div>", unsafe_allow_html=True)

# ==============================================================================
# 4. MATRIZ DRE FULL WIDTH
# ==============================================================================
html_tabela = f"<div class='matrix-container'><div class='matrix-header'><span>🗂️</span> Matriz DRE Gerencial</div><table class='dre-table'><thead><tr><th>Descrição</th><th style='text-align:center;'>Realizado<br>{nome_mes_atual}<br>(R$)</th><th style='text-align:center;'>Realizado<br>{nome_mes_anterior}<br>(R$)</th><th style='text-align:center;'>Var. %<br>(MoM)</th><th style='text-align:center;'>AV %<br>(Rec. Líquida)</th></tr></thead><tbody>"

linhas_dre = [
    ("Receita Bruta", rec_bruta, ant_rec_bruta, False),
    ("Deduções da Receita", deducoes, ant_deducoes, False),
    ("Receita Líquida", rec_liq, ant_rec_liq, True),
    ("Custo dos Serviços (CPV/CSP)", cpv, ant_cpv, False),
    ("Lucro Bruto", lucro_bruto, ant_lucro_bruto, True),
    ("Despesas Operacionais (OPEX)", opex, ant_opex, False),
    ("EBITDA", ebitda, ant_ebitda, True),
    ("Depreciação e Outros", outros, ant_outros, False),
    ("Lucro Líquido", lucro_liq, ant_lucro_liq, True)
]

base_av = rec_liq if rec_liq != 0 else 1

for nome, val_at, val_ant, destaque in linhas_dre:
    var_pct = calc_var(abs(val_at), abs(val_ant))
    av_pct = (val_at / base_av) * 100
    cor_var = "color: #10b981;" if var_pct > 0 else "color: #ef4444;"
    
    if "Custo" in nome or "Deduções" in nome or "Despesas" in nome or "Depreciação" in nome:
        cor_var = "color: #ef4444;" if var_pct > 0 else "color: #10b981;"
        
    sinal = "+" if var_pct > 0 else ""
    classe = "row-macro" if destaque else ""
    val_at_str = f"({formata_num(abs(val_at))})" if val_at < 0 else formata_num(val_at)
    val_ant_str = f"({formata_num(abs(val_ant))})" if val_ant < 0 else formata_num(val_ant)
    
    html_tabela += f"<tr class='{classe}'><td>{nome}</td><td style='text-align:center;'>{val_at_str}</td><td style='text-align:center;'>{val_ant_str}</td><td style='text-align:center; font-weight:800; {cor_var}'>{sinal}{var_pct:.1f}%</td><td style='text-align:center;'>{av_pct:.1f}%</td></tr>"

html_tabela += "</tbody></table></div>"
injetar_html(html_tabela)
