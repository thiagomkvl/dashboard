import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import conectar_sheets

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Diário", layout="wide", page_icon="📊")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .kpi-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 4px solid #4e73df;
        height: 100%;
    }
    .kpi-card.green { border-top-color: #1cc88a; }
    .kpi-card.purple { border-top-color: #6f42c1; }
    .kpi-card.cyan { border-top-color: #36b9cc; }
    .kpi-card.red { border-top-color: #e74a3b; }
    .kpi-card.orange { border-top-color: #f6c23e; }
    
    .kpi-title { font-size: 12px; font-weight: bold; color: #5a5c69; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { font-size: 24px; font-weight: bold; color: #3a3b45; }
    .kpi-subtitle { font-size: 11px; color: #858796; margin-top: 5px; }
    
    .section-title { font-size: 16px; font-weight: bold; color: #1a2035; margin-bottom: 15px; text-transform: uppercase; }
    .alert-box { background-color: #ffeeba; border-left: 4px solid #ffc107; padding: 15px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        conn = conectar_sheets()
        
        # 1. Carrega as abas do Google Sheets
        # (Altere "Saldos_Bancos" se a sua aba tiver um nome ligeiramente diferente)
        df_bancos = conn.read(worksheet="Saldos_Bancos", ttl=0)
        df_historico = conn.read(worksheet="Historico_Saldos", ttl=0)
        
        # --- PROTEÇÃO CONTRA PLANILHA VAZIA ---
        if df_bancos.empty:
            st.warning("A aba 'Saldos_Bancos' está vazia ou não foi encontrada.")
            return pd.DataFrame(), pd.DataFrame()
        
        # --- TRATAMENTO DOS DADOS DOS BANCOS ---
        # Ajuste dinâmico de nome de coluna caso no sheets esteja "Contas Bancárias" no plural
        if 'Contas Bancárias' in df_bancos.columns:
            df_bancos.rename(columns={'Contas Bancárias': 'Conta Bancária'}, inplace=True)
            
        colunas_financeiras = ['Saldo Inicial', 'Entrada', 'Saída', 'Conta Garantida']
        for col in colunas_financeiras:
            if col in df_bancos.columns:
                # Limpa R$, pontos e vírgulas (Padrão BR) para converter em Float puro
                df_bancos[col] = df_bancos[col].astype(str).str.replace('R\$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                df_bancos[col] = pd.to_numeric(df_bancos[col], errors='coerce').fillna(0.0)
            else:
                df_bancos[col] = 0.0

        # Recalcula o saldo final e disponível na hora para não depender de fórmula do Sheets
        df_bancos['Saldo Final'] = df_bancos['Saldo Inicial'] + df_bancos['Entrada'] + df_bancos['Saída']
        df_bancos['Disponível'] = df_bancos['Saldo Final'] + df_bancos['Conta Garantida']
            
        # --- TRATAMENTO DOS DADOS DO HISTÓRICO ---
        if not df_historico.empty:
            if 'Saldo' in df_historico.columns:
                df_historico['Saldo'] = df_historico['Saldo'].astype(str).str.replace('R\$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                df_historico['Saldo'] = pd.to_numeric(df_historico['Saldo'], errors='coerce').fillna(0.0)
            
            # Ordena pelo índice para a linha do gráfico não embaralhar as datas
            df_historico = df_historico.sort_index()
        else:
            # Mock de segurança se a aba de histórico estiver criada, mas vazia
            hoje = datetime.now()
            dias = [(hoje - timedelta(days=i)).strftime('%d/%m') for i in range(6, -1, -1)]
            df_historico = pd.DataFrame({'Data': dias, 'Saldo': [0]*7})

        return df_bancos, df_historico
        
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_bancos, df_historico = carregar_dados()

# Proteção de parada dura se a tabela principal não subir
if df_bancos.empty:
    st.stop()

# ==============================================================================
# 2. CÁLCULOS DOS KPIs
# ==============================================================================
# Garante que a coluna 'Tipo' exista para os filtros (Aplicação x Disponível)
if 'Tipo' not in df_bancos.columns:
    df_bancos['Tipo'] = 'Disponível'

saldo_aplicado = df_bancos[df_bancos['Tipo'].str.contains('Aplicação', case=False, na=False)]['Saldo Final'].sum()
saldo_disponivel = df_bancos[df_bancos['Tipo'].str.contains('Disponível', case=False, na=False)]['Saldo Final'].sum()
saldo_total = saldo_aplicado + saldo_disponivel
limites = df_bancos['Conta Garantida'].sum()
saldo_com_limites = saldo_total + limites

entradas_dia = df_bancos['Entrada'].sum()
saidas_dia = df_bancos['Saída'].sum()
resultado_liquido = entradas_dia + saidas_dia

# Verifica pendências (Tratando a string igual fizemos com o saldo)
if 'Pendentes de aprovação' in df_bancos.columns:
    pendencias_str = df_bancos['Pendentes de aprovação'].astype(str).str.replace('R\$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
    pendencias_aprovacao = pd.to_numeric(pendencias_str, errors='coerce').sum()
else:
    pendencias_aprovacao = 0.0

# ==============================================================================
# 3. HEADER PRINCIPAL
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')
col_data, col_title, col_transf_in, col_transf_out = st.columns([1, 2, 1, 1])

with col_data:
    st.markdown(f"**📅 {data_hoje}**<br><span style='color:gray; font-size:12px;'>Data de referência</span>", unsafe_allow_html=True)
with col_title:
    st.markdown("<h2 style='text-align: center; color: #1a2035; margin:0;'>PAINEL FINANCEIRO DIÁRIO</h2><p style='text-align: center; color: gray; margin:0;'>Controle Consolidado de Bancos</p>", unsafe_allow_html=True)
with col_transf_in:
    st.success("Transf. Entrada\n\n**R$ 0,00**")
with col_transf_out:
    st.error("Transf. Saída\n\n**R$ 0,00**")

st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# ==============================================================================
# 4. CARDS DE KPI (TOP ROW)
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
# 5. CORPO DO DASHBOARD (3 COLUNAS)
# ==============================================================================
col_grafico1, col_meio, col_dir = st.columns([1, 1.5, 1])

# --- ESQUERDA: Distribuição do Caixa (Gráfico Donut) ---
with col_grafico1:
    st.markdown("<div class='section-title'>Distribuição do Caixa</div>", unsafe_allow_html=True)
    if saldo_total > 0:
        fig_donut1 = px.pie(
            values=[saldo_aplicado, saldo_disponivel], 
            names=['Aplicado', 'Disponível'], 
            hole=0.6,
            color_discrete_sequence=['#4e73df', '#1cc88a']
        )
        fig_donut1.update_layout(
            showlegend=True, 
            legend=dict(orientation="v", yanchor="top", y=0.5, xanchor="left", x=1),
            margin=dict(t=0, b=0, l=0, r=0),
            annotations=[dict(text=f"<b>R$ {saldo_total/1000000:.2f} Mi</b><br>Saldo Total", x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        st.plotly_chart(fig_donut1, use_container_width=True)
    else:
        st.info("Sem saldo para exibir distribuição.")

# --- MEIO: Movimentação Rápida e Gráfico de Linha ---
with col_meio:
    st.markdown("<div class='section-title'>Movimentação do Dia</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.success(f"⬇ ENTRADAS\n\n**R$ {entradas_dia:,.2f}**")
    m2.error(f"⬆ SAÍDAS\n\n**R$ {abs(saidas_dia):,.2f}**")
    m3.warning(f"RESULTADO LÍQUIDO\n\n**R$ {resultado_liquido:,.2f}**")
    
    st.markdown("<div class='section-title' style='margin-top:20px;'>Evolução Diária do Saldo Total</div>", unsafe_allow_html=True)
    if not df_historico.empty and 'Data' in df_historico.columns and 'Saldo' in df_historico.columns:
        fig_linha = px.line(df_historico, x='Data', y='Saldo', markers=True)
        fig_linha.update_traces(line_color='#4e73df', marker=dict(size=8, color='#4e73df'))
        fig_linha.update_layout(margin=dict(t=10, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None, height=200)
        st.plotly_chart(fig_linha, use_container_width=True)
    else:
        st.info("Aguardando dados históricos...")

# --- DIREITA: Indicadores de Tesouraria ---
with col_dir:
    st.markdown("<div class='section-title'>Liquidez Bancária</div>", unsafe_allow_html=True)
    st.markdown(f"**Caixa Disponível:** <span style='float:right;'>R$ {saldo_disponivel:,.2f}</span>", unsafe_allow_html=True)
    st.markdown(f"**Limites Bancários:** <span style='float:right;'>R$ {limites:,.2f}</span>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"<h4 style='text-align:center; color:#4e73df;'>LIQUIDEZ TOTAL<br>R$ {saldo_com_limites:,.2f}</h4>", unsafe_allow_html=True)
    
    st.markdown("<div class='section-title' style='margin-top:20px;'>Indicadores de Tesouraria</div>", unsafe_allow_html=True)
    st.markdown(f"Bancos monitorados: <span style='float:right; font-weight:bold;'>{len(df_bancos)}</span>", unsafe_allow_html=True)
    st.markdown(f"Bancos com Aplicação: <span style='float:right; font-weight:bold;'>{len(df_bancos[df_bancos['Tipo'].str.contains('Aplicação', na=False)])}</span>", unsafe_allow_html=True)
    st.markdown(f"Bancos com Limite: <span style='float:right; font-weight:bold;'>{len(df_bancos[df_bancos['Conta Garantida']>0])}</span>", unsafe_allow_html=True)
    
    pendencias_qtd = len(df_bancos[df_bancos['Saída'] < 0])
    st.markdown(f"<span style='color:red;'>Linhas Negativas:</span> <span style='float:right; font-weight:bold; color:red;'>{pendencias_qtd}</span>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ==============================================================================
# 6. TABELA INFERIOR E ALERTAS
# ==============================================================================
col_tab, col_alertas = st.columns([2, 1])

with col_tab:
    st.markdown("<div class='section-title'>Saldo de Todos os Bancos</div>", unsafe_allow_html=True)
    
    # Criamos uma cópia para exibição
    df_view = df_bancos.copy()
    
    # Garante que a coluna de nome do banco existe, independente do nome plural ou singular
    conta_col = 'Conta Bancária' if 'Conta Bancária' in df_view.columns else df_view.columns[1]
    
    colunas_exibir = ['Tipo', conta_col, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']
    colunas_exibir = [c for c in colunas_exibir if c in df_view.columns]
    
    df_view = df_view[colunas_exibir]
    
    # Formata de volta para R$ na visualização da tabela (se for diferente de zero)
    for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']:
        if col in df_view.columns:
            df_view[col] = df_view[col].apply(lambda x: f"R$ {x:,.2f}" if x != 0 else "-")
    
    st.dataframe(df_view, hide_index=True, use_container_width=True, height=350)

with col_alertas:
    st.markdown("<div class='section-title'>Top 5 Bancos por Saldo Final</div>", unsafe_allow_html=True)
    if 'Conta Bancária' in df_bancos.columns:
        top5 = df_bancos.nlargest(5, 'Saldo Final')[['Conta Bancária', 'Saldo Final']]
        if not top5.empty and top5['Saldo Final'].sum() > 0:
            fig_bar = px.bar(top5, x='Saldo Final', y='Conta Bancária', orientation='h')
            fig_bar.update_traces(marker_color='#4e73df')
            fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None, height=150, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sem saldos para rankear.")
    
    st.markdown("<div class='section-title' style='margin-top:10px;'>Alertas e Observações</div>", unsafe_allow_html=True)
    st.error(f"⚠ PENDÊNCIAS DE APROVAÇÃO\n\n**R$ {abs(pendencias_aprovacao):,.2f}**")
    
    if 'Conta Bancária' in df_bancos.columns:
        mov_neg = df_bancos[df_bancos['Saída'] < 0][['Conta Bancária', 'Saída']]
        if not mov_neg.empty:
            st.markdown("**Movimentações Negativas do Dia**")
            for idx, row in mov_neg.iterrows():
                st.markdown(f"• {row['Conta Bancária']}: <span style='float:right; color:red;'>R$ {row['Saída']:,.2f}</span>", unsafe_allow_html=True)
