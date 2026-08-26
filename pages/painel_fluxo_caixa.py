import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Fluxo de Caixa Analítico", layout="wide", page_icon="💸")

# ==============================================================================
# 1. CUSTOM CSS — IDENTIDADE EXECUTIVA (BLINDADO CONTRA BUGS DO STREAMLIT)
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
.exec-update { border-left: 1px solid rgba(255,255,255,0.2); padding-left: 20px; display: flex; align-items: center; gap: 10px; }
.exec-update span { font-size: 10px; color: #bfdbfe; display:block; text-transform: uppercase;}
.exec-update b { font-size: 12px; font-weight: 700; display:block;}

/* KPI CARDS */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px 22px 20px; position: relative; box-shadow: var(--shadow); }
.kpi-card::after { content: ""; position: absolute; bottom: 0; left: 20px; right: 20px; height: 5px; border-radius: 5px 5px 0 0; }
.kpi-card.c-blue::after { background: var(--primary); }
.kpi-card.c-green::after { background: var(--success); }
.kpi-card.c-red::after { background: var(--danger); }
.kpi-top { display: flex; gap: 15px; align-items: flex-start; margin-bottom: 12px;}
.kpi-icon { width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; font-weight: bold;}
.c-blue .kpi-icon { background: #eff6ff; color: var(--primary); }
.c-green .kpi-icon { background: #ecfdf5; color: var(--success); }
.c-red .kpi-icon { background: #fef2f2; color: var(--danger); }
.kpi-info { flex: 1; }
.kpi-title { font-size: 11px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px; }
.kpi-val { font-size: 24px; font-weight: 800; color: var(--text-main); letter-spacing: -0.5px; line-height: 1.1; }
.kpi-meta-box { border-top: 1px solid var(--border); padding-top: 10px; display: flex; justify-content: space-between; align-items: center; }
.kpi-meta-box span { font-size: 11px; color: var(--text-muted); font-weight: 600;}
.kpi-var { font-size: 12px; font-weight: 800; display:flex; align-items:center; gap:3px;}
.var-up { color: var(--success); }
.var-down { color: var(--danger); }

/* GRÁFICOS BOX */
.chart-box { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; box-shadow: var(--shadow); margin-bottom: 25px;}
.chart-title { font-size: 16px; font-weight: 800; color: var(--primary-dark); margin-bottom: 2px; }
.chart-subtitle { font-size: 12px; color: var(--text-muted); font-weight: 500; margin-bottom: 15px; }

/* MATRIZ FLUXO DE CAIXA */
.matrix-container { background: var(--surface); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); border: 1px solid var(--border);}
.matrix-header { background: var(--primary-dark); color: #fff; padding: 12px 20px; font-size: 15px; font-weight: 800; display:flex; align-items:center; gap:8px;}
.dre-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.dre-table th { background: #f8fafc; color: var(--primary-dark); font-weight: 700; text-align: right; padding: 10px 15px; border-bottom: 2px solid var(--border); border-left: 1px solid var(--border); }
.dre-table th:first-child { text-align: left; border-left: none; }
.dre-table td { padding: 10px 15px; text-align: right; border-bottom: 1px solid var(--border); font-weight: 600; color: var(--text-main); }
.dre-table td:first-child { text-align: left; }
.dre-table tr:hover td { background-color: #f1f5f9; }
.row-macro td { font-weight: 800 !important; background-color: #eff6ff !important; color: var(--primary-dark) !important; font-size: 13px;}
.row-item td { color: var(--text-secondary); font-weight: 500; }
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

def formata_kpi(valor):
    if pd.isna(valor): return "0,00"
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
        
        # Mapeamento de Colunas Exatas:
        # B = Data (1), E = Débito/Saída (4), F = Crédito/Entrada (5), J = Classificação Financeira (9)
        col_data = df.columns[1]
        col_deb = df.columns[4]
        col_cred = df.columns[5]
        # Garantir que a coluna J existe (índice 9), senão pega a última
        col_classificacao = df.columns[9] if len(df.columns) > 9 else df.columns[-1]

        df['Data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df['Saída'] = df[col_deb].apply(limpa_valor)
        df['Entrada'] = df[col_cred].apply(limpa_valor)
        
        # Preenche vazios na classificação
        df['Classificação'] = df[col_classificacao].fillna('Não Classificado').astype(str).str.strip()
        df.loc[df['Classificação'] == '', 'Classificação'] = 'Não Classificado'
        
        return df[df['Data'].notna()]
    except Exception as e:
        st.error(f"Erro ao ler os dados: {e}")
        return pd.DataFrame()

df_base = preparar_dados_fluxo()
if df_base.empty: st.stop()

# ==============================================================================
# 3. FILTROS LATERAIS (PERÍODO DE ANÁLISE)
# ==============================================================================
hoje = datetime.now().date()
primeiro_dia_mes = hoje.replace(day=1)

with st.sidebar:
    st.markdown("### Configurações de Fluxo")
    data_selecionada = st.date_input("Selecione o Período:", value=(primeiro_dia_mes, hoje), format="DD/MM/YYYY")

if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
    dt_ini, dt_fim = data_selecionada
else:
    dt_ini = data_selecionada[0] if isinstance(data_selecionada, tuple) else data_selecionada
    dt_fim = dt_ini

# Filtro Atual
mask_atual = (df_base['Data'].dt.date >= dt_ini) & (df_base['Data'].dt.date <= dt_fim)
df_atual = df_base[mask_atual].copy()

# Filtro Período Anterior (mesma quantidade de dias para trás)
dias_periodo = (dt_fim - dt_ini).days + 1
dt_fim_ant = dt_ini - timedelta(days=1)
dt_ini_ant = dt_fim_ant - timedelta(days=dias_periodo - 1)
mask_ant = (df_base['Data'].dt.date >= dt_ini_ant) & (df_base['Data'].dt.date <= dt_fim_ant)
df_ant = df_base[mask_ant].copy()

# ==============================================================================
# 4. CÁLCULOS DOS KPIs
# ==============================================================================
tot_entrada_at = df_atual['Entrada'].sum()
tot_saida_at = df_atual['Saída'].sum()
geracao_liq_at = tot_entrada_at - tot_saida_at
eficiencia_at = (tot_saida_at / tot_entrada_at * 100) if tot_entrada_at > 0 else 0

tot_entrada_ant = df_ant['Entrada'].sum()
tot_saida_ant = df_ant['Saída'].sum()
geracao_liq_ant = tot_entrada_ant - tot_saida_ant
eficiencia_ant = (tot_saida_ant / tot_entrada_ant * 100) if tot_entrada_ant > 0 else 0

# ==============================================================================
# 5. HTML HEADER E KPIs
# ==============================================================================
data_hoje_str = datetime.now().strftime('%d/%m/%Y %H:%M')
periodo_str = f"{dt_ini.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}"

st.markdown(f"<div class='exec-header'><div><h1>FLUXO DE CAIXA ANALÍTICO</h1><p>Origem, Destino e Geração Líquida (Regime de Caixa)</p></div><div class='exec-filters'><div class='exec-filter-item'><label>Período Selecionado</label><div class='val'>{periodo_str}</div></div><div class='exec-update'><span style='font-size:22px;'>⏱️</span><div><span>Última Atualização</span><b>{data_hoje_str}</b></div></div></div></div>", unsafe_allow_html=True)

def html_var(atual, ant, is_invertido=False):
    val = calc_var(abs(atual), abs(ant))
    # Para saídas, aumento é ruim (vermelho). Para entradas, aumento é bom (verde).
    if is_invertido:
        cor = "var-down" if val >= 0 else "var-up"
    else:
        cor = "var-up" if val >= 0 else "var-down"
    
    seta = "▲" if val >= 0 else "▼"
    return f"<div class='kpi-var {cor}'><span>{seta}</span> {abs(val):.1f}%</div>"

kpis_html = f"""<div class='kpi-row'>
<div class='kpi-card c-green'><div class='kpi-top'><div class='kpi-icon'>📥</div><div class='kpi-info'><div class='kpi-title'>Total de Entradas</div><div class='kpi-val'>R$ {formata_kpi(tot_entrada_at)}</div></div></div><div class='kpi-meta-box'><span>Período Ant: R$ {formata_kpi(tot_entrada_ant)}</span>{html_var(tot_entrada_at, tot_entrada_ant)}</div></div>
<div class='kpi-card c-red'><div class='kpi-top'><div class='kpi-icon'>📤</div><div class='kpi-info'><div class='kpi-title'>Total de Saídas</div><div class='kpi-val'>R$ {formata_kpi(tot_saida_at)}</div></div></div><div class='kpi-meta-box'><span>Período Ant: R$ {formata_kpi(tot_saida_ant)}</span>{html_var(tot_saida_at, tot_saida_ant, True)}</div></div>
<div class='kpi-card c-blue'><div class='kpi-top'><div class='kpi-icon'>⚖️</div><div class='kpi-info'><div class='kpi-title'>Geração Líquida (Cash Flow)</div><div class='kpi-val'>R$ {formata_kpi(geracao_liq_at)}</div></div></div><div class='kpi-meta-box'><span>Período Ant: R$ {formata_kpi(geracao_liq_ant)}</span>{html_var(geracao_liq_at, geracao_liq_ant)}</div></div>
<div class='kpi-card c-blue'><div class='kpi-top'><div class='kpi-icon'>🔥</div><div class='kpi-info'><div class='kpi-title'>Taxa de Consumo (Saída/Entrada)</div><div class='kpi-val'>{eficiencia_at:.1f}%</div></div></div><div class='kpi-meta-box'><span>Período Ant: {eficiencia_ant:.1f}%</span></div></div>
</div>"""

injetar_html(kpis_html)

# ==============================================================================
# 6. GRÁFICOS ANALÍTICOS (TODAS AS CLASSIFICAÇÕES)
# ==============================================================================
col_g1, col_g2 = st.columns(2)

# Agrupamentos Atuais
df_entradas = df_atual[df_atual['Entrada'] > 0].groupby('Classificação')['Entrada'].sum().reset_index().sort_values('Entrada', ascending=True)
df_saidas = df_atual[df_atual['Saída'] > 0].groupby('Classificação')['Saída'].sum().reset_index().sort_values('Saída', ascending=True)

with col_g1:
    st.markdown("<div class='chart-box'><div class='chart-title'>Origem do Dinheiro (Entradas)</div><div class='chart-subtitle'>Composição 100% das receitas classificadas</div>", unsafe_allow_html=True)
    if not df_entradas.empty:
        fig_in = go.Figure(data=[go.Pie(
            labels=df_entradas['Classificação'], values=df_entradas['Entrada'], hole=0.6,
            textinfo='percent', hoverinfo='label+value',
            marker=dict(colors=pd.options.display.chop_threshold) # Deixa o plotly gerenciar as cores corporativas suavemente
        )])
        fig_in.update_layout(margin=dict(t=10, b=10, l=0, r=0), height=350, showlegend=True, legend=dict(orientation="v", y=0.5, x=1.05))
        st.plotly_chart(fig_in, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Nenhuma entrada classificada no período.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_g2:
    st.markdown("<div class='chart-box'><div class='chart-title'>Destino do Dinheiro (Saídas)</div><div class='chart-subtitle'>Composição 100% dos custos e despesas classificadas</div>", unsafe_allow_html=True)
    if not df_saidas.empty:
        # Altura dinâmica baseada na quantidade de classificações para nunca amassar
        altura_dinamica = max(350, len(df_saidas) * 35)
        
        fig_out = go.Figure(go.Bar(
            x=df_saidas['Saída'], y=df_saidas['Classificação'], orientation='h',
            marker_color='#ef4444', text=[f"R$ {formata_kpi(v)}" for v in df_saidas['Saída']],
            textposition='outside', textfont=dict(size=11, color='#1e293b')
        ))
        fig_out.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9", showticklabels=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=11, color="#1e293b", weight="bold")),
            margin=dict(t=10, b=10, l=10, r=40), height=altura_dinamica
        )
        st.plotly_chart(fig_out, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Nenhuma saída classificada no período.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 7. MATRIZ DETALHADA DO FLUXO DE CAIXA
# ==============================================================================
html_tabela = f"<div class='matrix-container'><div class='matrix-header'><span>🗂️</span> Detalhamento do Fluxo de Caixa por Classificação</div><table class='dre-table'><thead><tr><th>Classificação Financeira</th><th style='text-align:center;'>Valor Realizado (R$)</th><th style='text-align:center;'>% Representatividade</th><th style='text-align:center;'>Período Anterior (R$)</th><th style='text-align:center;'>Variação (%)</th></tr></thead><tbody>"

def renderizar_linhas(df_atual_filtro, df_ant_filtro, coluna_valor, total_periodo, is_saida=False):
    linhas = ""
    # Agrupa o período atual e anterior
    grupo_atual = df_atual_filtro.groupby('Classificação')[coluna_valor].sum().to_dict()
    grupo_ant = df_ant_filtro.groupby('Classificação')[coluna_valor].sum().to_dict()
    
    todas_chaves = set(list(grupo_atual.keys()) + list(grupo_ant.keys()))
    
    # Ordena do maior para o menor
    chaves_ordenadas = sorted(todas_chaves, key=lambda k: grupo_atual.get(k, 0), reverse=True)
    
    for chave in chaves_ordenadas:
        val_at = grupo_atual.get(chave, 0)
        val_ant = grupo_ant.get(chave, 0)
        
        rep_pct = (val_at / total_periodo * 100) if total_periodo > 0 else 0
        var_pct = calc_var(val_at, val_ant)
        
        # Cor da variação
        if is_saida:
            cor_var = "color: #ef4444;" if var_pct > 0 else "color: #10b981;" # Aumento de saída = ruim (vermelho)
        else:
            cor_var = "color: #10b981;" if var_pct > 0 else "color: #ef4444;" # Aumento de entrada = bom (verde)
            
        sinal = "+" if var_pct > 0 else ""
        
        linhas += f"<tr class='row-item'><td>{chave}</td><td style='text-align:center;'>R$ {formata_num(val_at)}</td><td style='text-align:center;'>{rep_pct:.1f}%</td><td style='text-align:center; color: #64748b;'>R$ {formata_num(val_ant)}</td><td style='text-align:center; font-weight:800; {cor_var}'>{sinal}{var_pct:.1f}%</td></tr>"
    return linhas

# Bloco ENTRADAS
var_tot_ent = calc_var(tot_entrada_at, tot_entrada_ant)
cor_tot_ent = "color: #10b981;" if var_tot_ent >= 0 else "color: #ef4444;"
sinal_ent = "+" if var_tot_ent > 0 else ""

html_tabela += f"<tr class='row-macro'><td>[+] ENTRADAS DE CAIXA</td><td style='text-align:center;'>R$ {formata_num(tot_entrada_at)}</td><td style='text-align:center;'>100.0%</td><td style='text-align:center;'>R$ {formata_num(tot_entrada_ant)}</td><td style='text-align:center; {cor_tot_ent}'>{sinal_ent}{var_tot_ent:.1f}%</td></tr>"
html_tabela += renderizar_linhas(df_atual[df_atual['Entrada'] > 0], df_ant[df_ant['Entrada'] > 0], 'Entrada', tot_entrada_at, is_saida=False)

# Bloco SAÍDAS
var_tot_sai = calc_var(tot_saida_at, tot_saida_ant)
cor_tot_sai = "color: #ef4444;" if var_tot_sai >= 0 else "color: #10b981;"
sinal_sai = "+" if var_tot_sai > 0 else ""

html_tabela += f"<tr class='row-macro'><td>[-] SAÍDAS DE CAIXA</td><td style='text-align:center;'>R$ {formata_num(tot_saida_at)}</td><td style='text-align:center;'>100.0%</td><td style='text-align:center;'>R$ {formata_num(tot_saida_ant)}</td><td style='text-align:center; {cor_tot_sai}'>{sinal_sai}{var_tot_sai:.1f}%</td></tr>"
html_tabela += renderizar_linhas(df_atual[df_atual['Saída'] > 0], df_ant[df_ant['Saída'] > 0], 'Saída', tot_saida_at, is_saida=True)

html_tabela += "</tbody></table></div>"
injetar_html(html_tabela)
