import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
import base64
import io

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Diário", layout="wide", page_icon="📊")

# --- CUSTOM CSS (ESTILO COMPACTO) ---
st.markdown("""
    <style>
    .main .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 95%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
    
    .box-card { background: white; border: 1px solid #e3e6f0; border-radius: 6px; padding: 10px 15px; height: 100%; }
    .kpi-card { background: white; border-radius: 6px; border-top: 4px solid #4e73df; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 10px; text-align: center; }
    .kpi-card.green { border-top-color: #1cc88a; }
    .kpi-card.purple { border-top-color: #6f42c1; }
    .kpi-card.cyan { border-top-color: #36b9cc; }
    .kpi-card.red { border-top-color: #e74a3b; }
    .kpi-card.orange { border-top-color: #f6c23e; }
    .kpi-title { font-size: 10px; font-weight: bold; color: #858796; text-transform: uppercase; }
    .kpi-value { font-size: 20px; font-weight: bold; color: #3a3b45; }
    
    .section-title { font-size: 13px; font-weight: bold; color: #1a2035; text-transform: uppercase; margin-bottom: 6px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
    .section-title-inline { font-size: 10px; font-weight: bold; color: #858796; text-transform: uppercase; }

    /* Tabela */
    .tabela-container { border: 1px solid #e3e6f0; border-radius: 4px; background: white; font-size: 11px; width: 100%; }
    .tabela-financeira { width: 100%; border-collapse: collapse; }
    .tabela-financeira th { background-color: #f8f9fc; color: #858796; font-weight: bold; text-align: left; padding: 4px 6px; border-bottom: 1px solid #e3e6f0; }
    .tabela-financeira td { padding: 4px 6px; border-bottom: 1px solid #f6f6f6; }
    .tabela-financeira .linha-total { background-color: #e2e6ea; font-weight: bold; border-top: 2px solid #ccc; }
    .tabela-financeira .valores { text-align: right; font-family: 'Courier New', monospace; }
    
    /* Gráficos HTML */
    .chart-img-container { width: 100%; display: flex; justify-content: center; align-items: center; }
    .chart-img-container img { max-width: 100%; height: auto; }

    /* Alertas */
    .alert-red { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 8px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .mov-row { display: flex; justify-content: space-between; font-size: 11px; padding: 2px 0; border-bottom: 1px solid #f1f1f1; }
    
    /* Caixas de Indicadores */
    .ind-item { display: flex; justify-content: space-between; font-size: 11px; padding: 2px 0; }
    .box-total-blue { background: #f8f9fc; border: 1px solid #4e73df; border-radius: 4px; padding: 6px; text-align: center; margin: 4px 0; }
    .box-total-grey { background: #e2e6ea; border: 1px solid #d1d3e2; border-radius: 4px; padding: 6px; text-align: center; margin: 4px 0; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÕES AUXILIARES
# ==============================================================================
def limpa_moeda_br(valor_str):
    if pd.isna(valor_str): return 0.0
    valor_str = str(valor_str).strip()
    if valor_str in ["", "-", ".", ","]: return 0.0
    valor_str = re.sub(r'[R$\s]', '', valor_str)
    valor_str = valor_str.replace('.', '').replace(',', '.')
    try: return float(valor_str)
    except ValueError: return 0.0

def formatar_moeda(valor):
    if valor == 0: return "-"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def fig_to_base64(fig):
    """Converte figura do plotly para base64 para exibição estática perfeita"""
    img_bytes = fig.to_image(format="png", engine="kaleido")
    return base64.b64encode(img_bytes).decode("utf-8")

# ==============================================================================
# 2. CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    conn = conectar_sheets()
    if conn is None: return pd.DataFrame(), pd.DataFrame()
    try:
        df_bancos = conn.read(worksheet="Saldos_Bancos", ttl=0)
        df_historico = conn.read(worksheet="Historico_Saldos", ttl=0)
        if df_bancos.empty: return pd.DataFrame(), pd.DataFrame()
        
        df_bancos.columns = [c.strip() for c in df_bancos.columns]
        col_conta = 'Contas Bancárias' if 'Contas Bancárias' in df_bancos.columns else 'Conta Bancária'
        col_data = 'Data'
        
        for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível', 'Pendentes de aprovação']:
            if col in df_bancos.columns: df_bancos[col] = df_bancos[col].apply(limpa_moeda_br)
            else: df_bancos[col] = 0.0

        df_bancos['Saída'] = df_bancos['Saída'].apply(lambda x: -abs(x) if x != 0 else 0)
        df_bancos['Entrada'] = df_bancos['Entrada'].apply(lambda x: abs(x))
        
        def definir_tipo(nome): return 'Aplicação' if ('aplicação' in str(nome).lower() or 'investimentos' in str(nome).lower()) else 'Disponível'
        df_bancos['Tipo'] = df_bancos[col_conta].apply(definir_tipo)

        df_bancos[col_data] = pd.to_datetime(df_bancos[col_data], format='%d/%m/%Y', errors='coerce')
        hoje = datetime.now().date()
        df_hoje = df_bancos[df_bancos[col_data].dt.date == hoje]
        if df_hoje.empty:
            ultima_data = df_bancos[col_data].max()
            df_hoje = df_bancos[df_bancos[col_data] == ultima_data]
            
        df_hoje = df_hoje.sort_values(by='Contas Bancárias')

        if not df_historico.empty:
            df_historico.columns = [c.strip() for c in df_historico.columns]
            for col in df_historico.columns:
                if 'saldo' in col.lower():
                    df_historico.rename(columns={col: 'Saldo'}, inplace=True)
                    df_historico['Saldo'] = df_historico['Saldo'].apply(limpa_moeda_br)
                    break
            if 'Data' in df_historico.columns:
                df_historico = df_historico.sort_values('Data')
        else:
            dias = [(datetime.now() - timedelta(days=i)).strftime('%d/%m') for i in range(6, -1, -1)]
            df_historico = pd.DataFrame({'Data': dias, 'Saldo': [0]*7})

        return df_bancos, df_historico, df_hoje, col_conta
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), ""

df_bancos, df_historico, df_hoje, col_conta = carregar_dados()
if df_bancos.empty: st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs & DADOS
# ==============================================================================
saldo_aplicado = df_hoje[df_hoje['Tipo'] == 'Aplicação']['Saldo Final'].sum()
saldo_disponivel = df_hoje[df_hoje['Tipo'] == 'Disponível']['Saldo Final'].sum()
saldo_total = saldo_aplicado + saldo_disponivel
limites = df_hoje['Conta Garantida'].sum()
saldo_com_limites = saldo_total + limites
entradas_dia = df_hoje['Entrada'].sum()
saidas_dia = df_hoje['Saída'].sum()
resultado_liquido = entradas_dia + saidas_dia
pendencias_aprovacao = df_hoje['Pendentes de aprovação'].sum()

# ==============================================================================
# 4. GERAÇÃO DOS GRÁFICOS ESTÁTICOS (PLOTLY -> BASE64)
# ==============================================================================
# Gráfico 1: Distribuição do Caixa (Donut) - Usado na Esquerda
fig_donut = go.Figure(data=[go.Pie(
    values=[saldo_aplicado, saldo_disponivel], 
    labels=['Aplicado', 'Disponível'], 
    hole=0.6, 
    marker=dict(colors=['#4e73df', '#1cc88a']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+percent'
)])
fig_donut.update_layout(
    showlegend=True, 
    legend=dict(orientation="h", yanchor="bottom", y=-0.05, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=5, b=5, l=5, r=5), 
    height=180,
    annotations=[dict(text=f"<b>R$ {saldo_total:,.2f}</b><br>Saldo Total", x=0.5, y=0.48, font_size=12, showarrow=False)]
)
img_donut = fig_to_base64(fig_donut)

# Gráfico 2: Evolução Diária (Linha) - Meio
fig_linha = px.line(df_historico, x='Data', y='Saldo', markers=True)
fig_linha.update_traces(line_color='#4e73df', marker=dict(size=6, color='#4e73df'))
fig_linha.update_layout(
    margin=dict(t=5, b=5, l=5, r=5), height=120, 
    xaxis=dict(tickfont=dict(size=9), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False),
    showlegend=False
)
img_linha = fig_to_base64(fig_linha)

# Gráfico 3: Top 5 Bancos (Barras) - Inferior Direita
top5 = df_hoje.nlargest(5, 'Saldo Final')[[col_conta, 'Saldo Final']]
if not top5.empty and top5['Saldo Final'].sum() > 0:
    fig_bar = px.bar(top5, x='Saldo Final', y=col_conta, orientation='h')
    fig_bar.update_traces(marker_color='#4e73df', width=0.5)
    fig_bar.update_layout(
        margin=dict(t=5, b=5, l=5, r=5), height=180, 
        xaxis=dict(showticklabels=False, showgrid=False), 
        yaxis=dict(tickfont=dict(size=10), showgrid=False), 
        showlegend=False
    )
    img_bar = fig_to_base64(fig_bar)
else:
    img_bar = None

# ==============================================================================
# 5. MONTAGEM DO PAINEL HTML
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')

# Cabeçalho
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

# KPIs
kpi_row = st.columns(7)
kp_data = [
    (kpi_row[0], "🏛️", "SALDO TOTAL", f"R$ {saldo_total:,.2f}", "green"),
    (kpi_row[1], "💳", "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "green"),
    (kpi_row[2], "📊", "SALDO APLICADO", f"R$ {saldo_aplicado:,.2f}", "purple"),
    (kpi_row[3], "🛡️", "SALDO + LIMITES", f"R$ {saldo_com_limites:,.2f}", "cyan"),
    (kpi_row[4], "⬇️", "ENTRADAS DO DIA", f"R$ {entradas_dia:,.2f}", "green"),
    (kpi_row[5], "⬆️", "SAÍDAS DO DIA", f"R$ {abs(saidas_dia):,.2f}", "red"),
    (kpi_row[6], "⏰", "PENDÊNCIAS APROVAÇÃO", f"R$ {abs(pendencias_aprovacao):,.2f}", "orange")
]
for col, icon, title, val, color in kp_data:
    col.markdown(f"<div class='kpi-card {color}'><div style='font-size:12px;'>{icon}</div><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Corpo Principal (3 Colunas)
c1, c2, c3 = st.columns([1.1, 1.2, 1.1])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-card' style='padding:5px;'><div class='chart-img-container'><img src='data:image/png;base64,{img_donut}'/></div></div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='section-title'>MOVIMENTAÇÃO DO DIA</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div style='background:#d4edda; border-radius:4px; padding:6px; text-align:center;'><span class='section-title-inline'>⬇ ENTRADAS</span><br><b>R$ {entradas_dia:,.2f}</b></div>", unsafe_allow_html=True)
    m2.markdown(f"<div style='background:#f8d7da; border-radius:4px; padding:6px; text-align:center;'><span class='section-title-inline'>⬆ SAÍDAS</span><br><b>R$ {abs(saidas_dia):,.2f}</b></div>", unsafe_allow_html=True)
    m3.markdown(f"<div style='background:#fff3cd; border-radius:4px; padding:6px; text-align:center;'><span class='section-title-inline'>RESULTADO LÍQUIDO</span><br><b>R$ {resultado_liquido:,.2f}</b></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-card' style='padding:5px;'><div class='chart-img-container'><img src='data:image/png;base64,{img_linha}'/></div></div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='section-title'>LIQUIDEZ BANCÁRIA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Caixa Disponível:</span> <b>R$ {saldo_disponivel:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Limites Bancários:</span> <b>R$ {limites:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-total-blue'><b>LIQUIDEZ TOTAL</b><br><span style='font-size:15px;'>R$ {saldo_com_limites:,.2f}</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:12px;'>INDICADORES DE TESOURARIA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos monitorados</span> <b>{len(df_hoje)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Aplicação</span> <b>{len(df_hoje[df_hoje['Tipo'] == 'Aplicação'])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Limite</span> <b>{len(df_hoje[df_hoje['Conta Garantida']>0])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Pendências</span> <b>{len(df_hoje[df_hoje['Saída'] != 0])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-total-grey'><b>SALDO CONSOLIDADO</b><br><span style='font-size:14px;'>R$ {saldo_total:,.2f}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# Parte Inferior (Tabela e Alertas)
col_tab, col_inf = st.columns([1.5, 1])

# Tabela Completa
with col_tab:
    st.markdown("<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    df_view = df_hoje[['Tipo', col_conta, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']].copy()
    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']}
    
    html_tabela = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th>SALDO INICIAL</th><th>ENTRADA</th><th>SAÍDA</th><th>SALDO FINAL</th><th>CONTA GARANTIDA</th><th>DISPONÍVEL</th></tr></thead><tbody>'
    for idx, row in df_view.iterrows():
        html_tabela += f'<tr><td>{idx+1}</td><td>{row[col_conta]}</td><td style="font-size:10px;">{row["Tipo"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(row["Entrada"])}</td><td class="valores">{formatar_moeda(row["Saída"])}</td><td class="valores">{formatar_moeda(row["Saldo Final"])}</td><td class="valores">{formatar_moeda(row["Conta Garantida"])}</td><td class="valores">{formatar_moeda(row["Disponível"])}</td></tr>'
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada"])}</td><td class="valores">{formatar_moeda(totais["Saída"])}</td><td class="valores">{formatar_moeda(totais["Saldo Final"])}</td><td class="valores">{formatar_moeda(totais["Conta Garantida"])}</td><td class="valores">{formatar_moeda(totais["Disponível"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; color:gray; margin-top:2px;'><span style='display:inline-block; width:10px; height:10px; background:#1cc88a; border-radius:2px; margin-right:4px;'></span> Disponível <span style='display:inline-block; width:10px; height:10px; background:#4e73df; border-radius:2px; margin-left:15px; margin-right:4px;'></span> Aplicação</div>", unsafe_allow_html=True)

# Inferior Direita (TOP 5 e ALERTAS)
with col_inf:
    # Dividimos a coluna direita em duas para TOP 5 e ALERTAS
    g1, g2 = st.columns([1.2, 1])
    
    with g1:
        st.markdown("<div class='section-title'>TOP 5 BANCOS POR SALDO FINAL</div>", unsafe_allow_html=True)
        if img_bar:
            st.markdown(f"<div class='box-card' style='padding:5px;'><div class='chart-img-container'><img src='data:image/png;base64,{img_bar}'/></div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='box-card' style='text-align:center; padding:20px; color:gray;'>Sem dados para rankear.</div>", unsafe_allow_html=True)

    with g2:
        st.markdown("<div class='section-title'>ALERTAS E OBSERVAÇÕES</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="alert-red" style="margin-bottom:8px;">
            <div style="display:flex; gap:8px; align-items:center;">
                <span style="font-size:16px;">🚨</span>
                <div><span style="font-size:11px; font-weight:normal;">PENDÊNCIAS DE APROVAÇÃO</span><br><span style="font-size:14px;">R$ {abs(pendencias_aprovacao):,.2f}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        mov_neg = df_hoje[df_hoje['Saída'] != 0][[col_conta, 'Saída']]
        if not mov_neg.empty:
            st.markdown("<div style='background:white; border:1px solid #e3e6f0; border-radius:4px; padding:6px;'>")
            st.markdown("<div style='display:flex; gap:5px; align-items:center; color:#721c24; font-weight:bold; font-size:11px; border-bottom:1px dashed #e3e6f0; padding-bottom:4px; margin-bottom:4px;'>⚠️ MOVIMENTAÇÕES NEGATIVAS</div>")
            for idx, row in mov_neg.iterrows():
                nome = row[col_conta][:15] + "..." if len(row[col_conta]) > 15 else row[col_conta]
                st.markdown(f"<div class='mov-row'><span>• {nome}</span> <span style='color:#e74a3b;'>R$ {row['Saída']:,.2f}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em {data_hoje}</div>", unsafe_allow_html=True)
