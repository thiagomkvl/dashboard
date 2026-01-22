import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets

# 1. CONFIGURAÇÃO E CSS
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# CSS para forçar o scroll interno e manter o bloco compacto
st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 5px; background-color: white; }
    
    /* BLOCO DE ROLAGEM FORÇADA */
    .scroll-box {
        height: 500px;
        overflow-y: scroll;
        overflow-x: hidden;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 15px;
        background-color: #f9fafb;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)

# --- CARREGAMENTO ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        conn = conectar_sheets()
        df = conn.read(worksheet="Historico", ttl=60)
        if not df.empty:
            df['Saldo_Limpo'] = pd.to_numeric(df['Saldo Atual'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

df_hist = carregar_dados()

# --- MENU LATERAL ---
st.sidebar.title("Dívida Fornecedores")
aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Evolução Temporal", "Upload"])

if not df_hist.empty:
    ultima_data = df_hist['data_processamento'].max()
    df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()

    # LÓGICA CURVA ABC
    df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
    total_hoje = df_abc['Saldo_Limpo'].sum()
    df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
    df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A (80%)' if x <= 0.8 else ('Classe B (15%)' if x <= 0.95 else 'Classe C (5%)'))
    df_hoje = df_hoje.merge(df_abc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

    if aba == "Dashboard Principal":
        st.title("Gestão de Passivo - SOS CARDIO")
        
        # Métricas
        m1, m2, m3, m4 = st.columns(4)
        total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
        
        m1.metric("Dívida Total", formatar_real(total_hoje))
        m2.metric("Total Vencido", formatar_real(total_vencido))
        m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
        m4.metric("Qtd Classe A", len(df_abc[df_abc['Classe ABC'] == 'Classe A (80%)']))

        st.divider()

        # --- GRÁFICOS ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Curva ABC de Fornecedores")
            opcoes_abc = ['Classe A (80%)', 'Classe B (15%)', 'Classe C (5%)']
            sel_abc = st.multiselect("Filtrar Classes:", opcoes_abc, default=opcoes_abc, key="f_abc_main")
            df_pie = df_hoje[df_hoje['Classe ABC'].isin(sel_abc)]
            fig_p = px.pie(df_pie, values='Saldo_Limpo', names='Classe ABC', hole=0.4,
                           color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
            st.plotly_chart(fig_p, use_container_width=True)

        with c2:
            st.subheader("Volume por Faixa (Ageing)")
            ordem_cart = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
            sel_cart = st.multiselect("Filtrar Faixas:", ordem_cart, default=ordem_cart, key="f_age_main")
            df_bar_filt = df_hoje[df_hoje['Carteira'].isin(sel_cart)]
            df_bar = df_bar_filt.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem_cart).reset_index().fillna(0)
            fig_b = px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'])
            st.plotly_chart(fig_b, use_container_width=True)

        st.divider()
        
        # --- BLOCO DE DETALHAMENTO COM ROLAGEM INTERNA ---
        st.subheader("Detalhamento com Análise de Risco")
        
        # Abertura da caixa de rolagem
        st.markdown('<div class="scroll-box">', unsafe_allow_html=True)
        
        # Dados agrupados para os cabeçalhos dos expanders
        df_agrup = df_hoje.groupby(['Beneficiario', 'Classe ABC']).agg(
            Total_Aberto=('Saldo_Limpo', 'sum'),
            Total_Vencido=('Saldo_Limpo', lambda x: df_hoje.loc[x.index][df_hoje.loc[x.index, 'Carteira'] != 'A Vencer']['Saldo_Limpo'].sum())
        ).sort_values('Total_Aberto', ascending=False).reset_index()

        # LOOP: Aqui todos os fornecedores são colocados dentro da DIV de scroll
        for _, row in df_agrup.iterrows():
            label = f"{row['Beneficiario']} ({row['Classe ABC']}) | Aberto: {formatar_real(row['Total_Aberto'])} | Vencido: {formatar_real(row['Total_Vencido'])}"
            
            with st.expander(label):
                detalhe = df_hoje[df_hoje['Beneficiario'] == row['Beneficiario']].copy()
                detalhe['Saldo Atual'] = detalhe['Saldo_Limpo'].apply(formatar_real)
                st.table(detalhe[['Vencimento', 'Saldo Atual', 'Carteira']])
        
        # Fechamento da caixa de rolagem (SÓ AQUI ELA FECHA)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- TUDO O QUE FOR COLOCADO ABAIXO DA DIV APARECERÁ NORMALMENTE NA PÁGINA ---
        st.divider()
        st.subheader("Resumo de Próximos Vencimentos")
        st.info("Indicadores adicionais que você queira incluir abaixo do bloco de fornecedores.")

    # --- ABAS ADICIONAIS ---
    elif aba == "Evolução Temporal":
        st.title("Evolução da Inadimplência")
        df_ev = df_hist.groupby('data_processamento')['Saldo_Limpo'].sum().reset_index()
        df_ev['dt_ordem'] = pd.to_datetime(df_ev['data_processamento'], format='%d/%m/%Y')
        df_ev = df_ev.sort_values('dt_ordem')
        fig_ev = px.line(df_ev, x='data_processamento', y='Saldo_Limpo', markers=True)
        st.plotly_chart(fig_ev, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        uploaded = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
        if uploaded and st.button("Salvar Dados"):
            df_new = pd.read_excel(uploaded)
            df_push = df_new.copy()
            df_push.columns = df_push.columns.str.strip()
            if salvar_no_historico(df_push):
                st.success("Dados salvos e histórico atualizado!")
                st.rerun()
else:
    st.warning("Sem dados históricos carregados.")
