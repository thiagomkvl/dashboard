import streamlit as st
import pandas as pd
import plotly.express as px
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

# --- CUSTOM CSS (Incluindo o estilo da nova tabela) ---
st.markdown("""
    <style>
    .kpi-card { background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border-top: 4px solid #4e73df; height: 100%; }
    .kpi-card.green { border-top-color: #1cc88a; }
    .kpi-card.purple { border-top-color: #6f42c1; }
    .kpi-card.cyan { border-top-color: #36b9cc; }
    .kpi-card.red { border-top-color: #e74a3b; }
    .kpi-card.orange { border-top-color: #f6c23e; }
    .kpi-title { font-size: 12px; font-weight: bold; color: #5a5c69; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { font-size: 24px; font-weight: bold; color: #3a3b45; }
    .kpi-subtitle { font-size: 11px; color: #858796; margin-top: 5px; }
    .section-title { font-size: 16px; font-weight: bold; color: #1a2035; margin-bottom: 15px; text-transform: uppercase; }
    
    /* ESTILO DA NOVA TABELA HTML (SEM ROLAGEM E COM TOTAL) */
    .tabela-financeira {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Arial', sans-serif;
        font-size: 13px;
        border: 1px solid #dee2e6;
        background-color: #fff;
    }
    .tabela-financeira th {
        background-color: #f1f3f5;
        color: #495057;
        font-weight: bold;
        padding: 8px 10px;
        text-align: left;
        border: 1px solid #dee2e6;
    }
    .tabela-financeira td {
        padding: 8px 10px;
        border: 1px solid #dee2e6;
        color: #212529;
    }
    .tabela-financeira tr:nth-child(even) {
        background-color: #f8f9fa; /* Zebrado leve */
    }
    .tabela-financeira .linha-total {
        background-color: #e9ecef;
        font-weight: bold;
    }
    .tabela-financeira .valores {
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÕES AUXILIARES
# ==============================================================================
def limpa_moeda_br(valor_str):
    if pd.isna(valor_str):
        return 0.0
    valor_str = str(valor_str).strip()
    if valor_str in ["", "-", ".", ","]:
        return 0.0
    valor_str = re.sub(r'[R$\s]', '', valor_str)
    valor_str = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(valor_str)
    except ValueError:
        return 0.0

def formatar_moeda(valor):
    """Formata float para R$ 1.234,56 ou '-' se for zero"""
    if valor == 0:
        return "-"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# ==============================================================================
# 2. CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    conn = conectar_sheets()
    if conn is None:
        return pd.DataFrame(), pd.DataFrame()
        
    try:
        df_bancos = conn.read(worksheet="Saldos_Bancos", ttl=0)
        df_historico = conn.read(worksheet="Historico_Saldos", ttl=0)
        
        if df_bancos.empty:
            return pd.DataFrame(), pd.DataFrame()

        df_bancos.columns = [c.strip() for c in df_bancos.columns]
        
        col_conta = 'Contas Bancárias' if 'Contas Bancárias' in df_bancos.columns else 'Conta Bancária'
        col_entrada = 'Entrada'
        col_saida = 'Saída'
        col_inicial = 'Saldo Inicial'
        col_final = 'Saldo Final'
        col_garantida = 'Conta Garantida'
        col_disponivel = 'Disponível'
        col_pendencias = 'Pendentes de aprovação'
        col_data = 'Data'

        if col_conta not in df_bancos.columns:
            st.error(f"Coluna '{col_conta}' não encontrada na planilha.")
            return pd.DataFrame(), pd.DataFrame()

        for col in [col_inicial, col_entrada, col_saida, col_final, col_garantida, col_disponivel, col_pendencias]:
            if col in df_bancos.columns:
                df_bancos[col] = df_bancos[col].apply(limpa_moeda_br)
            else:
                df_bancos[col] = 0.0

        df_bancos[col_saida] = df_bancos[col_saida].apply(lambda x: -abs(x) if x != 0 else 0)
        df_bancos[col_entrada] = df_bancos[col_entrada].apply(lambda x: abs(x))

        def definir_tipo(nome_banco):
            nome = str(nome_banco).lower()
            if 'aplicação' in nome or 'investimentos' in nome:
                return 'Aplicação'
            return 'Disponível'
        df_bancos['Tipo'] = df_bancos[col_conta].apply(definir_tipo)

        df_bancos[col_data] = pd.to_datetime(df_bancos[col_data], format='%d/%m/%Y', errors='coerce')
        hoje = datetime.now().date()
        df_hoje = df_bancos[df_bancos[col_data].dt.date == hoje]
        
        if df_hoje.empty:
            ultima_data = df_bancos[col_data].max()
            df_hoje = df_bancos[df_bancos[col_data] == ultima_data]

        # --- TRATAMENTO DO HISTÓRICO ---
        if not df_historico.empty:
            df_historico.columns = [c.strip() for c in df_historico.columns]
            col_saldo_historico = None
            for col in df_historico.columns:
                if 'saldo' in col.lower():
                    col_saldo_historico = col
                    break
            if col_saldo_historico:
                df_historico.rename(columns={col_saldo_historico: 'Saldo'}, inplace=True)
                df_historico['Saldo'] = df_historico['Saldo'].apply(limpa_moeda_br)
            if 'Data' in df_historico.columns:
                df_historico = df_historico.sort_values('Data')
        else:
            hoje = datetime.now()
            dias = [(hoje - timedelta(days=i)).strftime('%d/%m') for i in range(6, -1, -1)]
            df_historico = pd.DataFrame({'Data': dias, 'Saldo': [0]*7})

        return df_bancos, df_historico, df_hoje, col_conta
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), ""

df_bancos, df_historico, df_hoje, col_conta = carregar_dados()

if df_bancos.empty:
    st.warning("Nenhum dado foi encontrado na aba 'Saldos_Bancos'.")
    st.stop()

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
# 4. HEADER (ENXUTO)
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div><span style="font-size: 24px; font-weight: bold;">📅 {data_hoje}</span><br><span style='color:gray; font-size:12px;'>Data de referência</span></div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. CARDS DE KPI
# ==============================================================================
kpis = st.columns(7)
def draw_kpi(col, title, value, subtitle, color_class):
    col.markdown(f"""
        <div class="kpi-card {color_class}">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">R$ {value:,.2f}</div>
            <div class="kpi-subtitle">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

draw_kpi(kpis[0], "Saldo Total", saldo_total, "Total Consolidado", "")
draw_kpi(kpis[1], "Saldo Disponível", saldo_disponivel, "Disponível", "green")
draw_kpi(kpis[2], "Saldo Aplicado", saldo_aplicado, "Aplicações", "purple")
draw_kpi(kpis[3], "Saldo + Limites", saldo_com_limites, "Total com Limites", "cyan")
draw_kpi(kpis[4], "Entradas do Dia", entradas_dia, "Total de Entradas", "green")
draw_kpi(kpis[5], "Saídas do Dia", abs(saidas_dia), "Total de Saídas", "red")
draw_kpi(kpis[6], "Pendências Aprovação", abs(pendencias_aprovacao), "Valores Pendentes", "orange")
st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 6. CORPO DO DASHBOARD
# ==============================================================================
col_grafico1, col_meio, col_dir = st.columns([1, 1.5, 1])

with col_grafico1:
    st.markdown("<div class='section-title'>Distribuição do Caixa</div>", unsafe_allow_html=True)
    if saldo_total > 0:
        fig_donut1 = px.pie(
            values=[saldo_aplicado, saldo_disponivel], names=['Aplicado', 'Disponível'], hole=0.6,
            color_discrete_sequence=['#4e73df', '#1cc88a']
        )
        fig_donut1.update_layout(
            showlegend=True, legend=dict(orientation="v", yanchor="top", y=0.5, xanchor="left", x=1),
            margin=dict(t=0, b=0, l=0, r=0),
            annotations=[dict(text=f"<b>R$ {saldo_total:,.2f}</b><br>Saldo Total", x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        st.plotly_chart(fig_donut1, use_container_width=True)
    else:
        st.info("Sem saldo para exibir distribuição.")

with col_meio:
    st.markdown("<div class='section-title'>Movimentação do Dia</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.success(f"⬇ ENTRADAS\n\n**R$ {entradas_dia:,.2f}**")
    m2.error(f"⬆ SAÍDAS\n\n**R$ {abs(saidas_dia):,.2f}**")
    m3.warning(f"RESULTADO LÍQUIDO\n\n**R$ {resultado_liquido:,.2f}**")
    
    st.markdown("<div class='section-title' style='margin-top:20px;'>Evolução Diária do Saldo Total</div>", unsafe_allow_html=True)
    if not df_historico.empty and 'Saldo' in df_historico.columns and df_historico['Saldo'].sum() != 0:
        fig_linha = px.line(df_historico, x='Data', y='Saldo', markers=True)
        fig_linha.update_traces(line_color='#4e73df', marker=dict(size=8, color='#4e73df'))
        fig_linha.update_layout(margin=dict(t=10, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None, height=200)
        st.plotly_chart(fig_linha, use_container_width=True)
    else:
        st.info("Aguardando dados históricos...")

with col_dir:
    st.markdown("<div class='section-title'>Liquidez Bancária</div>", unsafe_allow_html=True)
    st.markdown(f"**Caixa Disponível:** <span style='float:right;'>R$ {saldo_disponivel:,.2f}</span>", unsafe_allow_html=True)
    st.markdown(f"**Limites Bancários:** <span style='float:right;'>R$ {limites:,.2f}</span>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"<h4 style='text-align:center; color:#4e73df;'>LIQUIDEZ TOTAL<br>R$ {saldo_com_limites:,.2f}</h4>", unsafe_allow_html=True)
    
    st.markdown("<div class='section-title' style='margin-top:20px;'>Indicadores de Tesouraria</div>", unsafe_allow_html=True)
    st.markdown(f"Bancos monitorados: <span style='float:right; font-weight:bold;'>{len(df_hoje)}</span>", unsafe_allow_html=True)
    st.markdown(f"Bancos com Aplicação: <span style='float:right; font-weight:bold;'>{len(df_hoje[df_hoje['Tipo'] == 'Aplicação'])}</span>", unsafe_allow_html=True)
    st.markdown(f"Bancos com Limite: <span style='float:right; font-weight:bold;'>{len(df_hoje[df_hoje['Conta Garantida']>0])}</span>", unsafe_allow_html=True)
    pendencias_qtd = len(df_hoje[df_hoje['Saída'] != 0])
    st.markdown(f"<span style='color:red;'>Bancos c/ Mov. Saída:</span> <span style='float:right; font-weight:bold; color:red;'>{pendencias_qtd}</span>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ==============================================================================
# 7. TABELA INFERIOR (REFORMULADA COM HTML E SEM ROLAGEM)
# ==============================================================================
col_tab, col_alertas = st.columns([2, 1])

with col_tab:
    st.markdown("<div class='section-title'>Saldo de Todos os Bancos (Dia de Hoje)</div>", unsafe_allow_html=True)
    
    # 1. Prepara os dados
    df_view = df_hoje.copy()
    colunas_exibir = ['Tipo', col_conta, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']
    df_view = df_view[colunas_exibir]

    # 2. Calcula o TOTAL
    totais = {col: df_view[col].sum() for col in colunas_exibir if col not in ['Tipo', col_conta]}
    
    # 3. Gera o HTML da tabela
    html_tabela = '<table class="tabela-financeira">'
    
    # Cabeçalho
    html_tabela += '<thead><tr>'
    for col in colunas_exibir:
        html_tabela += f'<th>{col}</th>'
    html_tabela += '</tr></thead><tbody>'

    # Linhas de dados
    for idx, row in df_view.iterrows():
        html_tabela += '<tr>'
        for col in colunas_exibir:
            if col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']:
                html_tabela += f'<td class="valores">{formatar_moeda(row[col])}</td>'
            else:
                html_tabela += f'<td>{row[col]}</td>'
        html_tabela += '</tr>'

    # Linha de TOTAL
    html_tabela += '<tr class="linha-total">'
    for col in colunas_exibir:
        if col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']:
            html_tabela += f'<td class="valores">{formatar_moeda(totais[col])}</td>'
        elif col == 'Tipo':
            html_tabela += '<td>TOTAL</td>'
        else:
            html_tabela += '<td></td>'
    html_tabela += '</tr>'

    html_tabela += '</tbody></table>'

    # 4. Exibe a tabela HTML no Streamlit (Sem barra de rolagem!)
    st.markdown(html_tabela, unsafe_allow_html=True)

with col_alertas:
    st.markdown("<div class='section-title'>Top 5 Bancos por Saldo Final</div>", unsafe_allow_html=True)
    top5 = df_hoje.nlargest(5, 'Saldo Final')[[col_conta, 'Saldo Final']]
    if not top5.empty and top5['Saldo Final'].sum() > 0:
        fig_bar = px.bar(top5, x='Saldo Final', y=col_conta, orientation='h')
        fig_bar.update_traces(marker_color='#4e73df')
        fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None, height=150, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem saldos para rankear.")
    
    st.markdown("<div class='section-title' style='margin-top:10px;'>Alertas e Observações</div>", unsafe_allow_html=True)
    st.error(f"⚠ PENDÊNCIAS DE APROVAÇÃO\n\n**R$ {abs(pendencias_aprovacao):,.2f}**")
    
    mov_neg = df_hoje[df_hoje['Saída'] != 0][[col_conta, 'Saída']]
    if not mov_neg.empty:
        st.markdown("**Movimentações de Saída do Dia**")
        for idx, row in mov_neg.iterrows():
            st.markdown(f"• {row[col_conta]}: <span style='float:right; color:red;'>R$ {row['Saída']:,.2f}</span>", unsafe_allow_html=True)
