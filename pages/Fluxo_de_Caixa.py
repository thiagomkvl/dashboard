import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Fluxo de Caixa Detalhado", page_icon="📈", layout="wide")

# --- CUSTOM CSS (Para melhorar a visualização da tabela densa) ---
st.markdown("""
    <style>
    /* Destaque para colunas de Realizado */
    [data-testid="stDataFrame"] th:contains("(R)") {
        background-color: #e8f4f8 !important; /* Azul bem clarinho para destacar o Realizado */
        color: #0277bd !important;
    }
    /* Destaque para Saldos */
    [data-testid="stDataFrame"] th:contains("Saldo") {
        font-weight: 900 !important;
    }
    .status-dot { height: 12px; width: 12px; background-color: #00C851; border-radius: 50%; display: inline-block; margin-left: 5px; margin-right: 10px;}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. MOTOR DE GERAÇÃO DE DADOS FICTÍCIOS (SIMULAÇÃO PROJ x REAL)
# ==============================================================================
@st.cache_data
def gerar_fcx_detalhado(dias=31, saldo_inicial=17710825.46):
    """
    Gera um DataFrame complexo simulando um fluxo de caixa diário
    com colunas Projetadas (P) e Realizadas (R) via 'Open Finance'.
    """
    data_inicial = datetime(2026, 1, 1)
    datas = [data_inicial + timedelta(days=i) for i in range(dias)]
    
    # Estrutura base
    df = pd.DataFrame({'Data': datas})
    df['Dia da Semana'] = df['Data'].dt.day_name().map({
        'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua', 
        'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sáb', 'Sunday': 'Dom'
    })

    # --- RECEITAS (Variação positiva ou negativa no realizado) ---
    # Unimed (Recebimentos grandes e pontuais)
    df['Rec. Unimed (P)'] = np.where(df['Data'].dt.day.isin([5, 15, 25]), np.random.uniform(1.5e6, 2.5e6, len(df)), 0)
    df['Rec. Unimed (R)'] = df['Rec. Unimed (P)'] * np.random.uniform(0.98, 1.02, len(df)) # Variação de 2%

    # Bradesco Saúde (Recebimentos semanais)
    df['Rec. Bradesco (P)'] = np.where(df['Data'].dt.dayofweek == 4, np.random.uniform(800e3, 1.2e6, len(df)), 0) # Toda sexta
    df['Rec. Bradesco (R)'] = df['Rec. Bradesco (P)'] * np.random.uniform(0.95, 1.05, len(df)) # Variação de 5%
    
    # Particular/Outros (Diário, menor valor, alta volatilidade no realizado)
    df['Rec. Particular (P)'] = np.where(df['Data'].dt.dayofweek < 5, np.random.uniform(50e3, 150e3, len(df)), 10e3)
    df['Rec. Particular (R)'] = df['Rec. Particular (P)'] * np.random.uniform(0.80, 1.30, len(df)) # Variação de 20% a 30%

    # --- DESPESAS (Realizado geralmente igual ou maior que o projetado) ---
    # Folha de Pagamento (Dia 5 e 20)
    df['Pag. Folha (P)'] = np.where(df['Data'].dt.day.isin([5, 20]), np.random.uniform(2e6, 2.2e6, len(df)), 0)
    df['Pag. Folha (R)'] = df['Pag. Folha (P)'] # Folha geralmente bate exato

    # Fornecedores Médicos (Pagamentos toda terça e quinta)
    df['Pag. Fornecedores (P)'] = np.where(df['Data'].dt.dayofweek.isin([1, 3]), np.random.uniform(300e3, 600e3, len(df)), 0)
    df['Pag. Fornecedores (R)'] = df['Pag. Fornecedores (P)'] * np.random.uniform(1.00, 1.03, len(df)) # Tendência de pagar 3% a mais

    # Tributos e Impostos (Dia 20)
    df['Pag. Tributos (P)'] = np.where(df['Data'].dt.day == 20, np.random.uniform(1.1e6, 1.3e6, len(df)), 0)
    df['Pag. Tributos (R)'] = df['Pag. Tributos (P)']

    # Despesas Financeiras/Bancárias (Pico no início do mês conforme seu histórico)
    df['Pag. Financeiras (P)'] = np.where(df['Data'].dt.day == 2, 5966344.06, np.random.uniform(1000, 5000, len(df)))
    df['Pag. Financeiras (R)'] = df['Pag. Financeiras (P)'] * np.random.uniform(1.0, 1.01, len(df))

    # --- CÁLCULO DOS SALDOS (CORRIDA DE CAIXA) ---
    saldo_proj = saldo_inicial
    saldo_real = saldo_inicial
    
    saldos_p = []
    saldos_r = []
    
    cols_rec_p = [c for c in df.columns if 'Rec.' in c and '(P)' in c]
    cols_pag_p = [c for c in df.columns if 'Pag.' in c and '(P)' in c]
    cols_rec_r = [c for c in df.columns if 'Rec.' in c and '(R)' in c]
    cols_pag_r = [c for c in df.columns if 'Pag.' in c and '(R)' in c]

    for index, row in df.iterrows():
        # Total do dia Projetado
        tot_rec_p = sum([row[c] for c in cols_rec_p])
        tot_pag_p = sum([row[c] for c in cols_pag_p])
        saldo_proj = saldo_proj + tot_rec_p - tot_pag_p
        saldos_p.append(saldo_proj)
        
        # Total do dia Realizado (Open Finance)
        tot_rec_r = sum([row[c] for c in cols_rec_r])
        tot_pag_r = sum([row[c] for c in cols_pag_r])
        saldo_real = saldo_real + tot_rec_r - tot_pag_r
        saldos_r.append(saldo_real)

    df['Saldo Final (P)'] = saldos_p
    df['Saldo Final (R)'] = saldos_r

    # Limpeza e Organização das Colunas
    cols_order = ['Data', 'Dia da Semana'] + \
                 sorted([c for c in df.columns if 'Rec.' in c]) + \
                 sorted([c for c in df.columns if 'Pag.' in c]) + \
                 ['Saldo Final (P)', 'Saldo Final (R)']
    
    return df[cols_order]

# Gerar os dados
df_raw = gerar_fcx_detalhado()

# ==============================================================================
# 2. HEADER E FILTROS
# ==============================================================================
st.title("Fluxo de Caixa Detalhado (Projetado x Realizado)")
st.markdown("""
    <div style='display: flex; align-items: center; margin-bottom: 20px; font-size: 14px; color: #666;'>
        <span>(P) = Projetado no Planejamento</span><span class='status-dot' style='background-color: #ccc; margin-left: 5px;'></span>
        <span style='margin-left: 15px;'>(R) = Realizado via Open Finance</span><span class='status-dot' style='background-color: #0277bd; margin-left: 5px;'></span>
    </div>
""", unsafe_allow_html=True)

# Filtro de Data (Opcional, para focar em uma semana específica)
col_filtro, _ = st.columns([1, 3])
with col_filtro:
    date_range = st.date_input("Período de Visualização", value=(df_raw['Data'].min(), df_raw['Data'].max()), format="DD/MM/YYYY")

# Aplica filtro se selecionado
if len(date_range) == 2:
    mask = (df_raw['Data'].dt.date >= date_range[0]) & (df_raw['Data'].dt.date <= date_range[1])
    df_filtered = df_raw.loc[mask].copy()
else:
    df_filtered = df_raw.copy()

# ==============================================================================
# 3. FORMATAÇÃO PARA VISUALIZAÇÃO (R$)
# ==============================================================================
df_display = df_filtered.copy()

# Formata a data
df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')

# Função para formatar moeda brasileira
def to_brl(val):
    if pd.isna(val): return ""
    s = f"{val:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

# Aplica formatação em todas as colunas numéricas
numeric_cols = df_display.select_dtypes(include=['float64', 'int64']).columns
for col in numeric_cols:
    df_display[col] = df_display[col].apply(to_brl)

# ==============================================================================
# 4. EXIBIÇÃO DA TABELA DETALHADA
# ==============================================================================
# Configuração das colunas para o st.dataframe
column_config = {
    "Data": st.column_config.TextColumn("Data", width="medium", pinned=True),
    "Dia da Semana": st.column_config.TextColumn("Dia", width="small", pinned=True),
    "Saldo Final (P)": st.column_config.TextColumn("Saldo Final (P)", width="medium"),
    "Saldo Final (R)": st.column_config.TextColumn("Saldo Final (R)", width="medium"),
}

# Ajuste de largura para as colunas de valores
for col in numeric_cols:
    if "Saldo" not in col:
        column_config[col] = st.column_config.TextColumn(col, width="medium")

st.dataframe(
    df_display,
    hide_index=True,
    use_container_width=True,
    height=600, # Altura maior para ver vários dias
    column_config=column_config
)

st.caption("Nota: Os valores na coluna (R) são simulações de retorno de APIs bancárias (Open Finance), podendo apresentar variações em relação ao projetado (P).")
