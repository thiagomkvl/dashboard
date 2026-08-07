import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
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

# --- CUSTOM CSS (ESTILO RÍGIDO E EXATO PARA PRINT) ---
st.markdown("""
    <style>
    /* Reset básico para garantir tamanhos fixos */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        max-width: 100%;
    }
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.5rem !important;
    }
    
    /* Cartões KPI */
    .kpi-card { background-color: white; padding: 10px 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; border-top: 4px solid #4e73df; height: 100%; border: 1px solid #e3e6f0; }
    .kpi-card.green { border-top-color: #1cc88a; }
    .kpi-card.purple { border-top-color: #6f42c1; }
    .kpi-card.cyan { border-top-color: #36b9cc; }
    .kpi-card.red { border-top-color: #e74a3b; }
    .kpi-card.orange { border-top-color: #f6c23e; }
    .kpi-icon { font-size: 24px; float: left; margin-right: 5px; }
    .kpi-title { font-size: 11px; font-weight: bold; color: #858796; text-transform: uppercase; margin-bottom: 2px; }
    .kpi-value { font-size: 22px; font-weight: bold; color: #5a5c69; }
    .kpi-subtitle { font-size: 10px; color: #b0b0b0; margin-top: 2px; }
    
    /* Títulos das seções */
    .section-title { font-size: 14px; font-weight: bold; color: #1a2035; margin-bottom: 5px; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    
    /* Tabela Estática */
    .tabela-container { border: 1px solid #e3e6f0; border-radius: 5px; overflow: hidden; background: white; }
    .tabela-financeira { width: 100%; border-collapse: collapse; font-family: 'Arial', sans-serif; font-size: 11px; background-color: #fff; }
    .tabela-financeira th { background-color: #f8f9fc; color: #858796; font-weight: bold; padding: 6px 8px; text-align: left; border-bottom: 1px solid #e3e6f0; }
    .tabela-financeira td { padding: 5px 8px; border-bottom: 1px solid #f6f6f6; color: #444; }
    .tabela-financeira tr:nth-child(even) { background-color: #fcfcfc; }
    .tabela-financeira .linha-total { background-color: #e2e6ea; font-weight: bold; border-top: 1px solid #ccc; }
    .tabela-financeira .valores { text-align: right; }
    .tabela-financeira .categoria { font-size: 10px; color: #777; }
    .legend-marker { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; }

    /* Side indicators */
    .liquidez-item { font-size: 12px; display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed #eee; }
    .liquidez-total { background: #f8f9fc; border: 1px solid #4e73df; border-radius: 5px; padding: 8px; text-align: center; margin-top: 5px; font-weight: bold; color: #4e73df; }
    .indicator-item { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }
    
    /* Alertas */
    .alert-box { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 8px 12px; border-radius: 4px; font-size: 12px; margin-bottom: 5px; }
    .alert-header { font-weight: bold; display: flex; align-items: center; }
    
    /* Headers */
    .header-top { display: flex; justify-content: space-between; align-items: center; background: white; padding: 10px 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 10px; border: 1px solid #e3e6f0; }
    .date-box { background: #f8f9fc; padding: 2px 10px; border-radius: 4px; }
    
    /* Ajuste dos gráficos estáticos */
    .chart-box { text-align: center; background: white; padding: 5px; border-radius: 5px; border: 1px solid #e3e6f0; }
    .chart-box img { max-width: 100%; height: auto; }
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

def formatar_moeda_curta(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

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
# 3. CÁLCULOS DOS KPIs
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
# 4. GERAÇÃO DOS GRÁFICOS COMO IMAGEM (PARA PRINT)
# ==============================================================================
def gerar_grafico_donut():
    if saldo_total <= 0: return None
    fig = go.Figure(data=[go.Pie(
        values=[saldo_aplicado, saldo_disponivel], 
        labels=['Aplicado', 'Disponível'], 
        hole=0.6, 
        marker=dict(colors=['#4e73df', '#1cc88a']),
        textinfo='none'
    )])
    fig.update_layout(
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=0.1, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(t=0, b=0, l=0, r=0), height=200,
        annotations=[dict(text=f"<b>R$ {saldo_total:,.2f}</b><br>Saldo Total", x=0.5, y=0.55, font_size=14, showarrow=False)]
    )
    return fig

def gerar_grafico_linha():
    if df_historico.empty or 'Saldo' not in df_historico.columns or df_historico['Saldo'].sum() == 0: return None
    fig = px.line(df_historico, x='Data', y='Saldo', markers=True)
    fig.update_traces(line_color='#4e73df', marker=dict(size=6, color='#4e73df'))
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=120, xaxis=dict(tickfont=dict(size=9)), yaxis=dict(showticklabels=False), showlegend=False)
    return fig

def gerar_grafico_barras():
    top5 = df_hoje.nlargest(5, 'Saldo Final')[[col_conta, 'Saldo Final']]
    if top5.empty or top5['Saldo Final'].sum() == 0: return None
    fig = px.bar(top5, x='Saldo Final', y=col_conta, orientation='h')
    fig.update_traces(marker_color='#4e73df', width=0.6)
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=150, xaxis=dict(showticklabels=False), yaxis=dict(tickfont=dict(size=9)), showlegend=False)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig

# Função para converter Plotly em HTML seguro (imagem embutida)
def plotly_to_html(fig):
    if fig is None: return "<div style='padding: 20px; color: #888; font-size: 12px;'>Aguardando dados...</div>"
    return fig.to_html(include_plotlyjs='cdn', config={'displayModeBar': False}, full_html=False)

# ==============================================================================
# 5. MONTAGEM DO PAINEL (HTML ESTRUTURADO PARA PRINT)
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')

# 5.1 HEADER
st.markdown(f"""
<div class="header-top">
    <div class="date-box"><span style="font-weight:bold;">📅 {data_hoje}</span><br><span style="font-size:10px; color:gray;">Data de referência</span></div>
    <div style="text-align:center;"><h2 style="margin:0; color:#1a2035;">PAINEL FINANCEIRO DIÁRIO</h2><p style="margin:0; font-size:12px; color:gray;">Controle Consolidado de Bancos</p></div>
    <div style="display:flex; gap:20px;">
        <div style="background:#d4edda; color:#155724; padding:2px 10px; border-radius:15px; font-size:10px; text-align:center;">Transf. Entrada<br><b>R$ 0,00</b></div>
        <div style="background:#f8d7da; color:#721c24; padding:2px 10px; border-radius:15px; font-size:10px; text-align:center;">Transf. Saída<br><b>R$ 0,00</b></div>
    </div>
</div>
""", unsafe_allow_html=True)

# 5.2 CARDS KPI
kpis = st.columns(7)
def draw_kpi(col, icon, title, value, subtitle, color_class):
    col.markdown(f"""
        <div class="kpi-card {color_class}">
            <div style="display:flex; align-items:center; justify-content:center; gap:5px; margin-bottom:2px;">
                <span style="color:{color_class.replace('green','#1cc88a').replace('purple','#6f42c1').replace('cyan','#36b9cc').replace('red','#e74a3b').replace('orange','#f6c23e')}; font-size:20px;">{icon}</span>
                <div class="kpi-title">{title}</div>
            </div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-subtitle">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

draw_kpi(kpis[0], "🏛️", "SALDO TOTAL", f"R$ {saldo_total:,.2f}", "Total Consolidado", "")
draw_kpi(kpis[1], "💳", "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "Disponível", "green")
draw_kpi(kpis[2], "📊", "SALDO APLICADO", f"R$ {saldo_aplicado:,.2f}", "Aplicações", "purple")
draw_kpi(kpis[3], "🛡️", "SALDO + LIMITES", f"R$ {saldo_com_limites:,.2f}", "Total com Limites", "cyan")
draw_kpi(kpis[4], "⬇️", "ENTRADAS DO DIA", f"R$ {entradas_dia:,.2f}", "Total de Entradas", "green")
draw_kpi(kpis[5], "⬆️", "SAÍDAS DO DIA", f"R$ {abs(saidas_dia):,.2f}", "Total de Saídas", "red")
draw_kpi(kpis[6], "⏰", "PENDÊNCIAS APROVAÇÃO", f"R$ {abs(pendencias_aprovacao):,.2f}", "Valores Pendentes", "orange")

st.markdown("<br>", unsafe_allow_html=True)

# 5.3 CORPO PRINCIPAL (3 COLUNAS)
col1, col2, col3 = st.columns([1, 1.3, 1])

# Coluna Esquerda
with col1:
    st.markdown("<div class='section-title'>Distribuição do Caixa</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-box'>{plotly_to_html(gerar_grafico_donut())}</div>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex; justify-content:space-between; font-size:11px; margin-top:2px;'><span><span class='legend-marker' style='background:#4e73df;'></span>Aplicado</span> <span style='float:right;'>100%</span></div>", unsafe_allow_html=True)

# Coluna Central
with col2:
    st.markdown("<div class='section-title'>Movimentação do Dia</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown("<div style='background:#d4edda; color:#155724; padding:8px; border-radius:4px; text-align:center; font-size:12px;'>⬇ ENTRADAS<br><b>R$ {:.2f}</b></div>".format(entradas_dia), unsafe_allow_html=True)
    m2.markdown("<div style='background:#f8d7da; color:#721c24; padding:8px; border-radius:4px; text-align:center; font-size:12px;'>⬆ SAÍDAS<br><b>R$ {:.2f}</b></div>".format(abs(saidas_dia)), unsafe_allow_html=True)
    m3.markdown("<div style='background:#fff3cd; color:#856404; padding:8px; border-radius:4px; text-align:center; font-size:12px;'>RESULTADO LÍQUIDO<br><b>R$ {:.2f}</b></div>".format(resultado_liquido), unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>Evolução Diária do Saldo Total (CONSOLIDADO)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-box'>{plotly_to_html(gerar_grafico_linha())}</div>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex; justify-content:space-between; font-size:10px; color:gray;'><span>01/08</span><span>02/08</span><span>03/08</span><span>04/08</span><span>05/08</span><span>06/08</span><span>07/08</span></div>", unsafe_allow_html=True)

# Coluna Direita
with col3:
    st.markdown("<div class='section-title'>Liquidez Bancária</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='liquidez-item'><span>Caixa Disponível:</span> <span>R$ {saldo_disponivel:,.2f}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='liquidez-item'><span>Limites Bancários:</span> <span>R$ {limites:,.2f}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='liquidez-total'>LIQUIDEZ TOTAL<br><span style='font-size:16px;'>R$ {saldo_com_limites:,.2f}</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:15px;'>Indicadores de Tesouraria</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='indicator-item'><span>Bancos monitorados</span> <b>{len(df_hoje)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='indicator-item'><span>Bancos com Aplicação</span> <b>{len(df_hoje[df_hoje['Tipo'] == 'Aplicação'])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='indicator-item'><span>Bancos com Limite</span> <b>{len(df_hoje[df_hoje['Conta Garantida']>0])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='indicator-item'><span style='color:#e74a3b;'>Pendências</span> <b style='color:#e74a3b;'>{len(df_hoje[df_hoje['Saída'] != 0])}</b></div>", unsafe_allow_html=True)
    
    st.markdown(f"<div style='background:#e2e6ea; border:1px solid #b0b0b0; border-radius:4px; padding:5px; text-align:center; margin-top:10px; font-size:12px;'><b>SALDO CONSOLIDADO</b><br>R$ {saldo_total:,.2f}</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# 5.4 ÁREA INFERIOR (Tabela Esquerda / Indicadores Direita)
col_tab, col_dir_inf = st.columns([1.6, 1])

# Tabela Inferior (Esquerda)
with col_tab:
    st.markdown("<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    
    # Gerando HTML da Tabela sem rolagem
    df_view = df_hoje[['Tipo', col_conta, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']].copy()
    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']}
    
    html_tabela = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th>SALDO INICIAL</th><th>ENTRADA</th><th>SAÍDA</th><th>SALDO FINAL</th><th>CONTA GARANTIDA</th><th>DISPONÍVEL</th></tr></thead><tbody>'
    for idx, row in df_view.iterrows():
        html_tabela += f'<tr><td>{idx+1}</td><td>{row[col_conta]}</td><td class="categoria">{row["Tipo"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(row["Entrada"])}</td><td class="valores">{formatar_moeda(row["Saída"])}</td><td class="valores">{formatar_moeda(row["Saldo Final"])}</td><td class="valores">{formatar_moeda(row["Conta Garantida"])}</td><td class="valores">{formatar_moeda(row["Disponível"])}</td></tr>'
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada"])}</td><td class="valores">{formatar_moeda(totais["Saída"])}</td><td class="valores">{formatar_moeda(totais["Saldo Final"])}</td><td class="valores">{formatar_moeda(totais["Conta Garantida"])}</td><td class="valores">{formatar_moeda(totais["Disponível"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)
    
    st.markdown("<div style='font-size:10px; color:gray; margin-top:4px;'>* Conta com TARIFA mensal. <span class='legend-marker' style='background:#1cc88a;'></span>Disponível <span class='legend-marker' style='background:#4e73df;'></span>Aplicação</div>", unsafe_allow_html=True)

# Indicadores e Gráficos Inferiores (Direita)
with col_dir_inf:
    c_graf, c_alert = st.columns([1, 1])
    
    with c_graf:
        st.markdown("<div class='section-title'>COMPOSIÇÃO DO PATRIMÔNIO FINANCEIRO</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='chart-box'>{plotly_to_html(gerar_grafico_donut())}</div>", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center; gap:20px; font-size:11px; margin-top:-15px;'><span><span class='legend-marker' style='background:#4e73df;'></span>Aplicado</span> <span><span class='legend-marker' style='background:#1cc88a;'></span>Disponível</span></div>", unsafe_allow_html=True)

    with c_alert:
        st.markdown("<div class='section-title'>ALERTAS E OBSERVAÇÕES</div>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="alert-box" style="background:#f8d7da; border-color:#f5c6cb; color:#721c24;">
            <div class="alert-header">⚠️ PENDÊNCIAS DE APROVAÇÃO</div>
            <div style="font-size:16px; font-weight:bold;">R$ {abs(pendencias_aprovacao):,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        mov_neg = df_hoje[df_hoje['Saída'] != 0][[col_conta, 'Saída']]
        if not mov_neg.empty:
            st.markdown("<div style='background:white; border:1px solid #f5c6cb; border-radius:4px; padding:8px; font-size:11px; margin-top:5px;'>")
            st.markdown("<b style='color:#721c24;'>⚠️ MOVIMENTAÇÕES NEGATIVAS</b>")
            for idx, row in mov_neg.iterrows():
                nome_banco = row[col_conta]
                if len(nome_banco) > 12: nome_banco = nome_banco[:12] + "..."
                st.markdown(f"<div style='display:flex; justify-content:space-between; border-bottom:1px dashed #eee;'><span>• {nome_banco}</span> <span style='color:red;'>R$ {row['Saída']:,.2f}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

# 5.5 RODAPÉ
st.markdown("<div style='display:flex; justify-content:space-between; font-size:10px; color:gray; margin-top:-10px;'>Valores em Reais (R$) | Dados atualizados em " + data_hoje + "</div>", unsafe_allow_html=True)
