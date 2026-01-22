import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico  # Importando a função de salvamento

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

# 2. UPLOAD DO ARQUIVO
file = st.sidebar.file_uploader("Suba o arquivo original (fornecedores.csv ou .xlsx)", type=["csv", "xlsx"])

if file:
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, sep=None, encoding='latin-1', engine='python', on_bad_lines='skip')
        else:
            df = pd.read_excel(file)
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        st.stop()

    # --- PROCESSAMENTO AUTOMÁTICO ---
    df.columns = df.columns.str.strip()
    
    # Identificar colunas (mapeamento para o banco de dados)
    col_benef = 'Beneficiario' if 'Beneficiario' in df.columns else df.columns[0]
    col_saldo = 'Saldo Atual' if 'Saldo Atual' in df.columns else df.columns[1]
    col_venc = 'Vencimento' if 'Vencimento' in df.columns else 'Vencimento'
    col_dias = 'Dias venc.' if 'Dias venc.' in df.columns else 'Dias venc'

    def clean_currency(x):
        if isinstance(x, str):
            x = x.replace('R$', '').replace('.', '').replace(',', '.').strip()
            try: return float(x)
            except: return 0.0
        return x

    df['Saldo_Limpo'] = df[col_saldo].apply(clean_currency)

    # Ageing (Carteira de Atraso)
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

    # --- BOTÃO DE SALVAMENTO NO HISTÓRICO (GOOGLE SHEETS) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Armazenamento")
    
    # Preparar DF para o Banco (apenas as colunas necessárias)
    df_para_banco = df[[col_benef, col_saldo, col_venc, 'Carteira']].copy()
    df_para_banco.columns = ['Beneficiario', 'Saldo Atual', 'Vencimento', 'Carteira']

    if st.sidebar.button("🚀 Salvar no Histórico"):
        with st.spinner("Enviando para o Google Sheets..."):
            sucesso = salvar_no_historico(df_para_banco)
            if sucesso:
                st.sidebar.success("Dados arquivados!")
                st.balloons()

    # --- EXIBIÇÃO DO DASHBOARD ---
    total_debt = df['Saldo_Limpo'].sum()
    
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Dívida Total", f"R$ {total_debt:,.2f}")
    m2.metric("Total de Lançamentos", len(df))
    m3.metric("Atraso > 90 dias", f"R$ {df[df['Carteira'] == '> 90 dias']['Saldo_Limpo'].sum():,.2f}")

    # Gráficos
    c1, c2 = st.columns(2)
    with c1:
        # Rating simplificado para o gráfico
        fig_pie = px.pie(df, values='Saldo_Limpo', names='Carteira', title="Distribuição por Vencimento", hole=.4)
        st.plotly_chart(fig_pie)
    with c2:
        ageing_order = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
        chart_data = df.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ageing_order).reset_index()
        fig_bar = px.bar(chart_data, x='Carteira', y='Saldo_Limpo', title="Dívida por Tempo de Atraso")
        st.plotly_chart(fig_bar)

    st.subheader("📋 Detalhamento dos Fornecedores")
    st.dataframe(df[[col_benef, col_saldo, 'Carteira', col_venc]], use_container_width=True)

else:
    st.info("Aguardando o upload do arquivo para gerar o dashboard e habilitar o salvamento.")
