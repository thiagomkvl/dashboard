import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { 
        background-color: #ffffff; padding: 15px; border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #004a99;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Dashboard Inteligente de Fornecedores - SOS CARDIO")

# 2. UPLOAD DO ARQUIVO (Aceita o original do hospital)
file = st.sidebar.file_uploader("Suba o arquivo original (fornecedores.csv)", type="csv")

if file:
    try:
        # Detecta separador e encoding automaticamente
        df = pd.read_csv(file, sep=None, encoding='latin-1', engine='python', on_bad_lines='skip')
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        st.stop()

    # --- PROCESSAMENTO AUTOMÁTICO (A IA faz o trabalho aqui) ---
    
    # Limpar nomes de colunas (tirar acentos e espaços)
    df.columns = df.columns.str.strip().str.replace('Ã¡', 'a').str.replace('Ã§Ã£', 'ca').str.replace('Ã­', 'i').str.replace('Ã³', 'o').str.replace('Ã©', 'e').str.replace('í', 'i').str.replace('á', 'a')
    
    # Identificar colunas corretas mesmo com variações de nome
    col_benef = 'Beneficiario' if 'Beneficiario' in df.columns else df.columns[0]
    col_saldo = 'Saldo Atual' if 'Saldo Atual' in df.columns else df.columns[1]
    col_dias = 'Dias venc.' if 'Dias venc.' in df.columns else 'Dias venc'

    # Função para limpar moeda (R$ 1.234,56 -> 1234.56)
    def clean_currency(x):
        if isinstance(x, str):
            x = x.replace('R$', '').replace('.', '').replace(',', '.').strip()
            try: return float(x)
            except: return 0.0
        return x

    df['Saldo_Limpo'] = df[col_saldo].apply(clean_currency)

    # Cálculo da Curva ABC (Rating)
    supplier_agg = df.groupby(col_benef)['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
    total_debt = supplier_agg['Saldo_Limpo'].sum()
    supplier_agg['Acumulado'] = supplier_agg['Saldo_Limpo'].cumsum() / total_debt
    
    def get_abc(pct):
        if pct <= 0.80: return 'Classe A'
        elif pct <= 0.95: return 'Classe B'
        return 'Classe C'
    
    supplier_agg['Classe ABC'] = supplier_agg['Acumulado'].apply(get_abc)
    df = df.merge(supplier_agg[[col_benef, 'Classe ABC']], on=col_benef, how='left')

    # Cálculo da Carteira de Atraso (Ageing)
    def get_ageing(days):
        try:
            d = int(days)
            if d < 0: return 'A Vencer'
            elif d <= 15: return '0-15 dias'
            elif d <= 30: return '16-30 dias'
            elif d <= 60: return '31-60 dias'
            elif d <= 90: return '61-90 dias'
            else: return '> 90 dias'
        except: return 'Indefinido'

    df['Carteira'] = df[col_dias].apply(get_ageing)

    # 3. EXIBIÇÃO DO DASHBOARD
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Dívida Total", f"R$ {total_debt:,.2f}")
    m2.metric("Fornecedores Críticos (A)", len(supplier_agg[supplier_agg['Classe ABC'] == 'Classe A']))
    m3.metric("Atraso > 90 dias", f"R$ {df[df['Carteira'] == '> 90 dias']['Saldo_Limpo'].sum():,.2f}")

    # Gráficos
    c1, c2 = st.columns(2)
    with c1:
        fig_pie = px.pie(df, values='Saldo_Limpo', names='Classe ABC', title="Distribuição por Rating", hole=.4)
        st.plotly_chart(fig_pie)
    with c2:
        ageing_order = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
        fig_bar = px.bar(df.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ageing_order).reset_index(), 
                         x='Carteira', y='Saldo_Limpo', title="Dívida por Tempo de Atraso")
        st.plotly_chart(fig_bar)

    st.subheader("📋 Lista de Prioridade para Negociação (Classe A)")
    st.dataframe(df[df['Classe ABC'] == 'Classe A'].sort_values('Saldo_Limpo', ascending=False)[[col_benef, 'Saldo_Limpo', 'Carteira', 'Vencimento']], use_container_width=True)

else:
    st.info("Aguardando o arquivo 'fornecedores.csv' para gerar o dashboard automaticamente.")
