import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Diário", layout="wide", page_icon="📊")

# --- CUSTOM CSS (LAYOUT ESTÁTICO E RÍGIDO PARA PRINT) ---
st.markdown("""
    <style>
    /* Reset de espaçamentos do Streamlit */
    .main .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 95%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
    
    /* Estilos Globais dos Cartões */
    .box-card { background: white; border: 1px solid #e3e6f0; border-radius: 6px; padding: 10px 15px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    
    /* HEADER */
    .header-top { display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; margin-bottom: 10px; border-bottom: 2px solid #e3e6f0; }
    .date-badge { background: #f8f9fc; padding: 4px 12px; border-radius: 20px; border: 1px solid #e3e6f0; }
    .transfer-badge { padding: 2px 15px; border-radius: 15px; text-align: center; }
    
    /* KPI Cards */
    .kpi-card { background: white; border-radius: 6px; border-top: 4px solid #4e73df; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 10px; text-align: center; }
    .kpi-card.green { border-top-color: #1cc88a; }
    .kpi-card.purple { border-top-color: #6f42c1; }
    .kpi-card.cyan { border-top-color: #36b9cc; }
    .kpi-card.red { border-top-color: #e74a3b; }
    .kpi-card.orange { border-top-color: #f6c23e; }
    .kpi-title { font-size: 10px; font-weight: bold; color: #858796; text-transform: uppercase; }
    .kpi-value { font-size: 20px; font-weight: bold; color: #3a3b45; margin-top: 2px; }
    
    /* Títulos Seções */
    .section-title { font-size: 13px; font-weight: bold; color: #1a2035; text-transform: uppercase; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
    
    /* Layout Flex das colunas inferiores */
    .flex-row { display: flex; gap: 15px; width: 100%; }
    .col-1 { flex: 1.3; }
    .col-2 { flex: 1; }
    .col-3 { flex: 1; }
    
    /* Tabela Estática */
    .tabela-container { border: 1px solid #e3e6f0; border-radius: 4px; background: white; font-size: 11px; width: 100%; }
    .tabela-financeira { width: 100%; border-collapse: collapse; }
    .tabela-financeira th { background-color: #f8f9fc; color: #858796; font-weight: bold; text-align: left; padding: 6px 6px; border-bottom: 1px solid #e3e6f0; }
    .tabela-financeira td { padding: 5px 6px; border-bottom: 1px solid #f6f6f6; }
    .tabela-financeira .linha-total { background-color: #e2e6ea; font-weight: bold; border-top: 2px solid #ccc; }
    .tabela-financeira .valores { text-align: right; font-family: 'Courier New', monospace; }
    
    /* Legenda */
    .legenda-item { display: flex; align-items: center; font-size: 11px; margin-bottom: 3px; gap: 8px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    
    /* Alertas */
    .alert-red { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 10px; border-radius: 4px; font-size: 13px; font-weight: bold; }
    .alert-header-2 { display: flex; align-items: center; gap: 5px; font-weight: bold; font-size: 11px; color: #721c24; border-bottom: 1px dashed #f5c6cb; padding-bottom: 5px; margin-bottom: 5px; }
    .mov-row { display: flex; justify-content: space-between; font-size: 11px; padding: 2px 0; border-bottom: 1px solid #f1f1f1; }
    
    /* Indicadores Direita */
    .ind-item { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; }
    .box-total-blue { background: #f8f9fc; border: 1px solid #4e73df; border-radius: 4px; padding: 8px; text-align: center; margin: 5px 0; }
    .box-total-grey { background: #e2e6ea; border: 1px solid #d1d3e2; border-radius: 4px; padding: 8px; text-align: center; margin: 5px 0; }
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
            
        # Ordena a tabela para impressão
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
# 4. MONTAGEM HTML ESTRUTURADA
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')

# CABEÇALHO
st.markdown(f"""
<div class="header-top">
    <div class="date-badge"><b>📅 {data_hoje}</b><br><span style="font-size:10px; color:gray;">Data de referência</span></div>
    <div style="text-align:center;"><h2 style="margin:0; color:#1a2035;">PAINEL FINANCEIRO DIÁRIO</h2><p style="margin:0; font-size:12px; color:gray;">Controle Consolidado de Bancos</p></div>
    <div style="display:flex; gap:15px;">
        <div class="transfer-badge" style="background:#d4edda; color:#155724;"><span style="font-size:10px;">Transferências Entrada</span><br><b>R$ 0,00</b></div>
        <div class="transfer-badge" style="background:#f8d7da; color:#721c24;"><span style="font-size:10px;">Transferências Saída</span><br><b>R$ 0,00</b></div>
    </div>
</div>
""", unsafe_allow_html=True)

# CARDS KPI
kpi_row = st.columns(7)
kpis = [
    (kpi_row[0], "🏛️", "SALDO TOTAL", f"R$ {saldo_total:,.2f}", "Total Consolidado", ""),
    (kpi_row[1], "💳", "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "Disponível", "green"),
    (kpi_row[2], "📊", "SALDO APLICADO", f"R$ {saldo_aplicado:,.2f}", "Aplicações", "purple"),
    (kpi_row[3], "🛡️", "SALDO + LIMITES", f"R$ {saldo_com_limites:,.2f}", "Total com Limites", "cyan"),
    (kpi_row[4], "⬇️", "ENTRADAS DO DIA", f"R$ {entradas_dia:,.2f}", "Total de Entradas", "green"),
    (kpi_row[5], "⬆️", "SAÍDAS DO DIA", f"R$ {abs(saidas_dia):,.2f}", "Total de Saídas", "red"),
    (kpi_row[6], "⏰", "PENDÊNCIAS APROVAÇÃO", f"R$ {abs(pendencias_aprovacao):,.2f}", "Valores Pendentes", "orange")
]

for col, icon, title, val, sub, color in kpis:
    col.markdown(f"""
        <div class="kpi-card {color}">
            <div style="display:flex; justify-content:center; align-items:center; gap:5px;">
                <span style="font-size:16px;">{icon}</span>
                <div class="kpi-title">{title}</div>
            </div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-title" style="color:#858796; margin-top:3px;">{sub}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# CORPO PRINCIPAL (3 COLUNAS FLEX)
col1_html, col2_html, col3_html = st.columns([1, 1.2, 1])

# ESQUERDA (DISTRIBUIÇÃO)
with col1_html:
    st.markdown("<div class='section-title'>Distribuição do Caixa</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="box-card" style="display:flex; flex-direction:column; justify-content:center; align-items:center; padding:20px;">
        <div style="font-size:40px; color:#4e73df; margin-bottom:5px;">🍩</div>
        <div style="font-size:20px; font-weight:bold;">R$ {saldo_total:,.2f}</div>
        <div style="font-size:12px; color:gray;">Saldo Total</div>
        <div style="margin-top:10px; width:100%; border-top:1px solid #eee; padding-top:10px;">
            <div class="legenda-item"><span class="dot" style="background:#4e73df;"></span> <b>Aplicado</b> <span style="margin-left:auto;">{saldo_aplicado/saldo_total*100:.1f}%</span></div>
            <div class="legenda-item"><span class="dot" style="background:#1cc88a;"></span> <b>Disponível</b> <span style="margin-left:auto;">{saldo_disponivel/saldo_total*100:.1f}%</span></div>
        </div>
        <div style="width:100%; border-top:1px solid #eee; margin-top:5px; padding-top:5px; display:flex; justify-content:space-between; font-size:11px; color:gray;">
            <span>Total</span> <span>100%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# MEIO (MOVIMENTAÇÃO E EVOLUÇÃO)
with col2_html:
    st.markdown("<div class='section-title'>Movimentação do Dia</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div style='background:#d4edda; border-radius:4px; padding:8px; text-align:center;'><span style='font-size:12px;'>⬇ ENTRADAS</span><br><b>R$ {entradas_dia:,.2f}</b></div>", unsafe_allow_html=True)
    m2.markdown(f"<div style='background:#f8d7da; border-radius:4px; padding:8px; text-align:center;'><span style='font-size:12px;'>⬆ SAÍDAS</span><br><b>R$ {abs(saidas_dia):,.2f}</b></div>", unsafe_allow_html=True)
    m3.markdown(f"<div style='background:#fff3cd; border-radius:4px; padding:8px; text-align:center;'><span style='font-size:12px;'>RESULTADO LÍQUIDO</span><br><b>R$ {resultado_liquido:,.2f}</b></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:15px;'>Evolução Diária do Saldo Total (CONSOLIDADO)</div>", unsafe_allow_html=True)
    if not df_historico.empty and 'Saldo' in df_historico.columns:
        st.markdown(f"""
        <div class="box-card" style="height:90px; display:flex; align-items:flex-end; justify-content:space-around; padding:0 10px 10px;">
            {''.join([f'<div style="height:{int((row["Saldo"]/df_historico["Saldo"].max())*70)}px; width:15px; background:#4e73df; border-radius:3px 3px 0 0;"></div>' for _, row in df_historico.iterrows()])}
        </div>
        <div style="display:flex; justify-content:space-between; font-size:9px; color:gray; margin-top:2px;">
            {''.join([f'<div>{row["Data"]}</div>' for _, row in df_historico.iterrows()])}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Aguardando dados históricos...")

# DIREITA (LIQUIDEZ)
with col3_html:
    st.markdown("<div class='section-title'>Liquidez Bancária</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Caixa Disponível:</span> <b>R$ {saldo_disponivel:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Limites Bancários:</span> <b>R$ {limites:,.2f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='box-total-blue'><b>LIQUIDEZ TOTAL</b><br><span style='font-size:16px;'>R$ {saldo_com_limites:,.2f}</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:15px;'>Indicadores de Tesouraria</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos monitorados</span> <b>{len(df_hoje)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Aplicação</span> <b>{len(df_hoje[df_hoje['Tipo'] == 'Aplicação'])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span>Bancos com Limite</span> <b>{len(df_hoje[df_hoje['Conta Garantida']>0])}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ind-item'><span style='color:#e74a3b;'>Pendências</span> <b style='color:#e74a3b;'>{len(df_hoje[df_hoje['Saída'] != 0])}</b></div>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='box-total-grey'><b>SALDO CONSOLIDADO</b><br><span style='font-size:14px;'>R$ {saldo_total:,.2f}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

# ÁREA INFERIOR (TABELA E ALERTAS)
col_tab, col_alert_inf = st.columns([1.5, 1])

# TABELA
with col_tab:
    st.markdown("<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    df_view = df_hoje[['Tipo', col_conta, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']].copy()
    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']}
    
    html_tabela = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th>SALDO INICIAL</th><th>ENTRADA</th><th>SAÍDA</th><th>SALDO FINAL</th><th>CONTA GARANTIDA</th><th>DISPONÍVEL</th></tr></thead><tbody>'
    for idx, row in df_view.iterrows():
        html_tabela += f'<tr><td>{idx+1}</td><td>{row[col_conta]}</td><td style="font-size:10px; color:#555;">{row["Tipo"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(row["Entrada"])}</td><td class="valores">{formatar_moeda(row["Saída"])}</td><td class="valores">{formatar_moeda(row["Saldo Final"])}</td><td class="valores">{formatar_moeda(row["Conta Garantida"])}</td><td class="valores">{formatar_moeda(row["Disponível"])}</td></tr>'
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada"])}</td><td class="valores">{formatar_moeda(totais["Saída"])}</td><td class="valores">{formatar_moeda(totais["Saldo Final"])}</td><td class="valores">{formatar_moeda(totais["Conta Garantida"])}</td><td class="valores">{formatar_moeda(totais["Disponível"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; color:gray; margin-top:4px;'><span class='dot' style='background:#1cc88a;'></span> Disponível <span class='dot' style='background:#4e73df; margin-left:15px;'></span> Aplicação</div>", unsafe_allow_html=True)

# ALERTAS E PATRIMÔNIO
with col_alert_inf:
    g1, g2 = st.columns([1, 1])
    
    # Gráfico de Patrimônio (Simplificado para caber no print)
    with g1:
        st.markdown("<div class='section-title'>COMPOSIÇÃO DO PATRIMÔNIO</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="box-card" style="padding:15px;">
            <div style="display:flex; align-items:center; justify-content:center; flex-direction:column;">
                <div style="width:60px; height:60px; border-radius:50%; background: conic-gradient(#4e73df 0% {saldo_aplicado/saldo_total*100}%, #1cc88a {saldo_aplicado/saldo_total*100}% 100%); margin-bottom:10px;"></div>
                <div style="font-size:12px;"><b>R$ {saldo_total:,.2f}</b></div>
                <div style="font-size:10px; color:gray;">Saldo Total</div>
            </div>
            <div style="margin-top:10px; border-top:1px solid #eee; padding-top:5px; display:flex; justify-content:center; gap:15px; font-size:10px;">
                <div><span class="dot" style="background:#4e73df;"></span> Aplicado <b>{saldo_aplicado/saldo_total*100:.1f}%</b></div>
                <div><span class="dot" style="background:#1cc88a;"></span> Disponível <b>{saldo_disponivel/saldo_total*100:.1f}%</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Alertas
    with g2:
        st.markdown("<div class='section-title'>ALERTAS E OBSERVAÇÕES</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="alert-red">
            <div style="display:flex; gap:10px; align-items:center;">
                <span style="font-size:20px;">🚨</span>
                <div><span style="font-size:12px; font-weight:normal;">PENDÊNCIAS DE APROVAÇÃO</span><br><span style="font-size:16px;">R$ {abs(pendencias_aprovacao):,.2f}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        mov_neg = df_hoje[df_hoje['Saída'] != 0][[col_conta, 'Saída']]
        if not mov_neg.empty:
            st.markdown("<div style='background:white; border:1px solid #e3e6f0; border-radius:4px; padding:8px; margin-top:5px;'>")
            st.markdown("<div class='alert-header-2'>⚠️ MOVIMENTAÇÕES NEGATIVAS</div>")
            for idx, row in mov_neg.iterrows():
                st.markdown(f"<div class='mov-row'><span>• {row[col_conta]}</span> <span style='color:#e74a3b;'>R$ {row['Saída']:,.2f}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='font-size:10px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em " + data_hoje + "</div>", unsafe_allow_html=True)
