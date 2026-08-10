import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Diário", layout="wide", page_icon="📊")

# --- CUSTOM CSS (FONTE MAIOR E MAIS ESCURA NAS TABELAS) ---
st.markdown("""
    <style>
    .main .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 95%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
    
    .stPlotlyChart { background-color: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }
    
    .kpi-card { background: white; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 10px; text-align: center; }
    .kpi-card.total { border-top: 4px solid #4e73df; background: #f8faff; }
    .kpi-card.disponivel { border-top: 4px solid #1cc88a; background: #f4fdf6; }
    .kpi-card.limites { border-top: 4px solid #36b9cc; background: #f4fcfe; }
    .kpi-card.aplicacoes { border-top: 4px solid #6f42c1; background: #fbf8ff; }
    
    .kpi-title { font-size: 11px; font-weight: bold; color: #858796; text-transform: uppercase; }
    .kpi-value { font-size: 20px; font-weight: bold; color: #3a3b45; }
    
    .section-title { font-size: 13px; font-weight: bold; color: #1a2035; text-transform: uppercase; margin-bottom: 6px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
    .section-title-inline { font-size: 10px; font-weight: bold; color: #858796; text-transform: uppercase; }

    /* Tabela Padrão (FONTE MAIOR: 14px) */
    .tabela-container { border: 1px solid #e3e6f0; border-radius: 4px; background: white; font-size: 14px; width: 100%; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .tabela-financeira { width: 100%; border-collapse: collapse; }
    .tabela-financeira th { background-color: #4e73df; color: white; font-weight: bold; text-align: left; padding: 10px 12px; border-bottom: 1px solid #e3e6f0; }
    .tabela-financeira td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; font-weight: 500; color: #1a202c; }
    .tabela-financeira .linha-total { background-color: #e2e6ea; font-weight: bold; border-top: 2px solid #ccc; }
    
    .tabela-financeira .valores { text-align: right; font-family: 'Courier New', monospace; font-weight: bold; color: #2d3748; }
    .tabela-financeira .col-destaque { background-color: #eef2ff; color: #1a3b7c; font-weight: 900; }
    
    .ind-item { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; }
    .box-total-blue { background: #f8f9fc; border: 1px solid #4e73df; border-radius: 4px; padding: 6px; text-align: center; margin: 4px 0; }
    .box-total-grey { background: #e2e6ea; border: 1px solid #d1d3e2; border-radius: 4px; padding: 6px; text-align: center; margin: 4px 0; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÃO DE LEITURA E LIMPEZA
# ==============================================================================
def limpa_valor_bruto(valor):
    if pd.isna(valor) or str(valor).strip() == "" or str(valor).strip() == "-":
        return 0.0
    try:
        return float(str(valor).strip())
    except ValueError:
        return 0.0

def formatar_moeda(valor):
    if valor == 0: return "-"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_porcentagem(valor):
    return f"{valor:.2f}%"

# ==============================================================================
# 2. CARGA DE DADOS REAIS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    conn = conectar_sheets()
    if conn is None: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        df = conn.read(worksheet="Historico_Saldos", ttl=0)
        
        if df.empty:
            st.warning("A aba 'Historico_Saldos' está vazia.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        df.columns = [c.strip() for c in df.columns]
        col_conta = 'Contas Bancárias' if 'Contas Bancárias' in df.columns else 'Conta Bancária'
        col_data = 'Data'
        
        df[col_data] = pd.to_datetime(df[col_data], format='%d/%m/%Y', errors='coerce')
        ultima_data = df[col_data].max()
        
        for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']:
            if col in df.columns:
                df[col] = df[col].apply(limpa_valor_bruto)

        # Dados de hoje
        df_hoje = df[df[col_data] == ultima_data].copy()
        
        def definir_tipo(nome): 
            if 'getnet' in str(nome).lower():
                return 'Limite'
            return 'Aplicação' if ('aplicação' in str(nome).lower() or 'investimentos' in str(nome).lower()) else 'Disponível'
        
        df_hoje['Tipo'] = df_hoje[col_conta].apply(definir_tipo)
        df_hoje = df_hoje.sort_values(by=col_conta)

        # Dados Históricos Consolidados
        df_historico_consolidado = df.groupby(col_data)['Saldo Final'].sum().reset_index().sort_values(col_data)
        df_historico_consolidado['Variação %'] = df_historico_consolidado['Saldo Final'].pct_change() * 100
        df_historico_consolidado['Variação %'] = df_historico_consolidado['Variação %'].fillna(0)
        
        df_historico_consolidado['Data'] = df_historico_consolidado[col_data].dt.strftime('%d/%m/%Y')
        df_historico_consolidado['Saldo Final'] = df_historico_consolidado['Saldo Final'].apply(formatar_moeda)
        df_historico_consolidado['Variação %'] = df_historico_consolidado['Variação %'].apply(formatar_porcentagem)
        
        df_historico_consolidado = df_historico_consolidado.sort_values(by=col_data, ascending=False).head(10)

        return df_hoje, df_historico_consolidado, col_conta
        
    except Exception as e:
        st.error(f"Erro fatal: {e}")
        return pd.DataFrame(), pd.DataFrame(), ""

df_hoje, df_historico_consolidado, col_conta = carregar_dados()
if df_hoje.empty: st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs
# ==============================================================================
saldo_aplicado = df_hoje[df_hoje['Tipo'] == 'Aplicação']['Saldo Final'].sum()
saldo_disponivel = df_hoje[df_hoje['Tipo'] == 'Disponível']['Saldo Final'].sum()

limite_getnet = df_hoje[df_hoje['Tipo'] == 'Limite']['Disponível'].sum()
limites_garantidos = df_hoje['Conta Garantida'].sum()
limites_totais = limite_getnet + limites_garantidos

saldo_total = saldo_disponivel + limites_totais + saldo_aplicado
saldo_com_limites = saldo_total + limites_totais
entradas_dia = df_hoje['Entrada'].sum()
saidas_dia = df_hoje['Saída'].sum()
resultado_liquido = entradas_dia + saidas_dia

# ==============================================================================
# 4. GRÁFICO DONUT (Ajustado para nunca cortar)
# ==============================================================================
fig_donut = go.Figure(data=[go.Pie(
    values=[saldo_aplicado, saldo_disponivel], 
    labels=['Aplicado', 'Disponível'], 
    hole=0.6, 
    marker=dict(colors=['#4e73df', '#1cc88a']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+percent'
)])
# Aumentei a altura e adicionei b=40 (margem inferior) para garantir que a legenda nunca seja cortada
fig_donut.update_layout(
    showlegend=True, 
    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=10, b=40, l=0, r=0), 
    height=320,
    annotations=[dict(text=f"<b>R$ {saldo_total:,.2f}</b><br>Saldo Total", x=0.5, y=0.48, font_size=12, showarrow=False)]
)

# ==============================================================================
# 5. GRÁFICO DE LINHA (Evolução)
# ==============================================================================
conn = conectar_sheets()
df_full = conn.read(worksheet="Historico_Saldos", ttl=0)
df_full.columns = [c.strip() for c in df_full.columns]
df_full['Data'] = pd.to_datetime(df_full['Data'], format='%d/%m/%Y', errors='coerce')
df_full['Saldo Final'] = df_full['Saldo Final'].apply(limpa_valor_bruto)
df_grouped_line = df_full.groupby('Data')['Saldo Final'].sum().reset_index().sort_values('Data')
df_graficos = df_grouped_line.tail(10).copy()
df_graficos['Data_Label'] = df_graficos['Data'].dt.strftime('%d/%m')

fig_linha = go.Figure()
fig_linha.add_trace(go.Scatter(
    x=df_graficos['Data_Label'], 
    y=df_graficos['Saldo Final'], 
    mode='lines+markers',
    line=dict(color='#4e73df', width=3),
    marker=dict(size=8, color='#4e73df'),
    showlegend=False
))
fig_linha.update_layout(
    margin=dict(t=10, b=15, l=5, r=5), height=140, 
    xaxis=dict(tickfont=dict(size=10), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False, range=[0, df_graficos['Saldo Final'].max() * 1.1]),
    plot_bgcolor='#f1f5f9', 
    paper_bgcolor='#f1f5f9'
)

# ==============================================================================
# 6. MONTAGEM DO PAINEL
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')

# Header
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; margin-bottom: 5px; border-bottom: 1px solid #e3e6f0;">
    <div><b style="font-size:18px;">📅 {data_hoje}</b><br><span style="font-size:10px; color:gray;">Data de referência</span></div>
    <div style="text-align:center;"><h2 style="margin:0; color:#1a2035; font-size:22px;">PAINEL FINANCEIRO DIÁRIO</h2><p style="margin:0; font-size:11px; color:gray;">Controle Consolidado de Bancos</p></div>
    <div style="display:flex; gap:10px;">
        <div style="background:#d4edda; border-radius:12px; padding:1px 15px; text-align:center;"><span style="font-size:10px;">Transferências Entrada</span><br><b style="font-size:14px;">R$ 0,00</b></div>
        <div style="background:#f8d7da; border-radius:12px; padding:1px 15px; text-align:center;"><span style="font-size:10px;">Transferências Saída</span><br><b style="font-size:14px;">R$ 0,00</b></div>
    </div>
</div>
""", unsafe_allow_html=True)

# KPIs (4 Blocos)
kpi_row = st.columns(4)
kp_data = [
    (kpi_row[0], "🏛️", "SALDO TOTAL", f"R$ {saldo_total:,.2f}", "total"),
    (kpi_row[1], "💳", "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "disponivel"),
    (kpi_row[2], "🛡️", "LIMITES TOTAIS", f"R$ {limites_totais:,.2f}", "limites"),
    (kpi_row[3], "📊", "APLICAÇÕES", f"R$ {saldo_aplicado:,.2f}", "aplicacoes")
]
for col, icon, title, val, color in kp_data:
    col.markdown(f"<div class='kpi-card {color}'><div style='font-size:12px;'>{icon}</div><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.1, 1.4, 1])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown("<div class='section-title'>MOVIMENTAÇÃO DO DIA</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div style='padding:6px;'><div class='section-title-inline' style='color:#1cc88a;'>⬇ ENTRADAS</div><div style='font-size:16px; font-weight:bold;'>R$ {entradas_dia:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div style='padding:6px;'><div class='section-title-inline' style='color:#e74a3b;'>⬆ SAÍDAS</div><div style='font-size:16px; font-weight:bold;'>R$ {abs(saidas_dia):,.2f}</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div style='padding:6px;'><div class='section-title-inline' style='color:#f6c23e;'>RESULTADO LÍQUIDO</div><div style='font-size:16px; font-weight:bold;'>R$ {resultado_liquido:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_linha, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown("<div class='section-title'>LIQUIDEZ BANCÁRIA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Caixa Disponível:</span> <b>R$ {saldo_disponivel:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Limites Bancários:</span> <b>R$ {limites_totais:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-total-blue'><b>LIQUIDEZ TOTAL</b><br><span style='font-size:15px;'>R$ {saldo_com_limites:,.2f}</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:12px;'>INDICADORES DE TESOURARIA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos monitorados</span> <b>{len(df_hoje)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Aplicação</span> <b>{len(df_hoje[df_hoje['Tipo'] == 'Aplicação'])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Limite</span> <b>{len(df_hoje[df_hoje['Conta Garantida']>0]) + (1 if limite_getnet > 0 else 0)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span style='color:#e74a3b;'>Mov. Saída</span> <b style='color:#e74a3b;'>{len(df_hoje[df_hoje['Saída'] != 0])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-total-grey'><b>SALDO CONSOLIDADO</b><br><span style='font-size:14px;'>R$ {saldo_total:,.2f}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

col_tab, col_hist = st.columns([1.6, 1])

with col_tab:
    st.markdown("<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    df_view = df_hoje[['Tipo', col_conta, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']].copy()
    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']}
    
    html_tabela = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th>SALDO INICIAL</th><th>ENTRADA</th><th>SAÍDA</th><th class="valores">SALDO FINAL</th><th>CONTA GARANTIDA</th><th>DISPONÍVEL</th></tr></thead><tbody>'
    for idx, row in df_view.iterrows():
        html_tabela += f'<tr><td>{idx+1}</td><td>{row[col_conta]}</td><td style="font-size:12px; font-weight:bold; color:#555;">{row["Tipo"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(row["Entrada"])}</td><td class="valores">{formatar_moeda(row["Saída"])}</td><td class="valores col-destaque">{formatar_moeda(row["Saldo Final"])}</td><td class="valores">{formatar_moeda(row["Conta Garantida"])}</td><td class="valores">{formatar_moeda(row["Disponível"])}</td></tr>'
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada"])}</td><td class="valores">{formatar_moeda(totais["Saída"])}</td><td class="valores col-destaque">{formatar_moeda(totais["Saldo Final"])}</td><td class="valores">{formatar_moeda(totais["Conta Garantida"])}</td><td class="valores">{formatar_moeda(totais["Disponível"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; color:gray; margin-top:2px;'><span style='display:inline-block; width:10px; height:10px; background:#1cc88a; border-radius:2px; margin-right:4px;'></span> Disponível <span style='display:inline-block; width:10px; height:10px; background:#4e73df; border-radius:2px; margin-left:15px; margin-right:4px;'></span> Aplicação</div>", unsafe_allow_html=True)

with col_hist:
    st.markdown("<div class='section-title'>HISTÓRICO CONSOLIDADO</div>", unsafe_allow_html=True)
    if not df_historico_consolidado.empty:
        html_hist = '<div class="tabela-container" style="font-size:14px;"><table class="tabela-financeira"><thead><tr><th>DATA</th><th class="valores">SALDO FINAL</th><th class="valores">VARIAÇÃO</th></tr></thead><tbody>'
        for _, row in df_historico_consolidado.iterrows():
            variacao = row['Variação %']
            cor = "#1cc88a" if float(variacao.replace('%', '').replace(',', '.')) >= 0 else "#e74a3b"
            html_hist += f'<tr><td style="font-weight:bold; color:#333;">{row["Data"]}</td><td class="valores col-destaque">{row["Saldo Final"]}</td><td class="valores" style="color:{cor}; font-weight:bold;">{variacao}</td></tr>'
        html_hist += '</tbody></table></div>'
        st.markdown(html_hist, unsafe_allow_html=True)
        st.markdown("<div style='font-size:10px; color:gray; margin-top:2px;'>Últimos 10 registros disponíveis.</div>", unsafe_allow_html=True)
    else:
        st.info("Sem dados históricos suficientes.")

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em {data_hoje}</div>", unsafe_allow_html=True)
