import streamlit as st
import pandas as pd
from core.normalizacao import normalizar_recebimentos, normalizar_tasy
from core.conciliacao import executar_conciliacao
from services.google_sheets import carregar_dados_sheets, salvar_matriz_sheets

SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID")

st.set_page_config(page_title="Conciliação de Recebíveis", layout="wide", page_icon="🏦")
st.title("🏦 Painel de Conciliação de Recebíveis")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Recarregar do GSheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

df_bancos_raw, df_tasy_raw = carregar_dados_sheets(SPREADSHEET_ID)

if df_bancos_raw.empty or df_tasy_raw.empty:
    st.warning("Aguardando lançamentos nas abas Extratos_Bancos e Base_Tasy no Google Sheets.")
    st.stop()

# Normalização e Processamento
df_rec = normalizar_recebimentos(df_bancos_raw)
df_tasy = normalizar_tasy(df_tasy_raw)
df_matriz = executar_conciliacao(df_rec, df_tasy)

# Identificação Inversa (Créditos Tasy Sem Recebimento)
tasy_utilizados = set([id_elem for lista in df_matriz['tasy_ids'] for id_elem in lista])
df_tasy_sem_rec = df_tasy[~df_tasy['tasy_id'].isin(tasy_utilizados)]

# Métricas Principais
tot_rec = df_rec['valor'].sum()
tot_tasy = df_tasy['valor'].sum()
tot_conc = df_matriz[df_matriz['status'] == 'CONCILIADO']['valor_conciliado'].sum()
tot_pend = df_matriz[df_matriz['status'] == 'PENDENTE']['valor_recebimento'].sum()
tot_parc = df_matriz[df_matriz['status'] == 'PARCIAL']['valor_conciliado'].sum()
tot_tasy_sobra = df_tasy_sem_rec['valor'].sum()

pct_conc = (tot_conc / tot_rec * 100) if tot_rec > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Recebimentos", f"R$ {tot_rec:,.2f}")
c2.metric("Total Tasy", f"R$ {tot_tasy:,.2f}")
c3.metric("Conciliado", f"R$ {tot_conc:,.2f}", f"{pct_conc:.1f}%")
c4.metric("Pendências", f"R$ {tot_pend:,.2f}", delta_color="inverse")
c5.metric("Tasy Sem Recebimento", f"R$ {tot_tasy_sobra:,.2f}", delta_color="off")

st.divider()

# Navegação interna por Abas
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Validador", "⚠️ Pendências", "📊 Data + Banco", "🛡️ Integridade"
])

with tab1:
    st.subheader("Validador Lançamento a Lançamento")
    f_banco = st.multiselect("Banco", options=df_matriz['banco'].unique())
    f_status = st.multiselect("Status", options=df_matriz['status'].unique())
    
    df_f = df_matriz.copy()
    if f_banco: df_f = df_f[df_f['banco'].isin(f_banco)]
    if f_status: df_f = df_f[df_f['status'].isin(f_status)]
    
    st.dataframe(df_f[['conciliacao_id', 'data_recebimento', 'banco', 'valor_recebimento', 'valor_tasy', 'diferenca', 'tipo_conciliacao', 'status', 'motivo']], use_container_width=True)

with tab2:
    st.subheader("Pendências Operacionais")
    df_p = df_matriz[df_matriz['status'] != 'CONCILIADO']
    if df_p.empty:
        st.success("Tudo conciliado! Nenhuma pendência encontrada.")
    else:
        st.dataframe(df_p[['recebimento_id', 'data_recebimento', 'banco', 'valor_recebimento', 'valor_tasy', 'diferenca', 'status', 'motivo']], use_container_width=True)

with tab3:
    st.subheader("Conferência Agregada por Data e Banco")
    agg1 = df_rec.groupby(['data', 'banco'])['valor'].sum().reset_index(name='Recebimentos')
    agg2 = df_tasy.groupby(['data', 'banco'])['valor'].sum().reset_index(name='Tasy')
    df_agg = pd.merge(agg1, agg2, on=['data', 'banco'], how='outer').fillna(0.0)
    df_agg['Diferença'] = (df_agg['Recebimentos'] - df_agg['Tasy']).round(2)
    df_agg['Status'] = df_agg['Diferença'].apply(lambda x: 'OK' if abs(x) < 0.01 else 'Divergente')
    st.dataframe(df_agg, use_container_width=True)

with tab4:
    st.subheader("Validação de Integridade Matemática")
    soma_matriz = round(tot_conc + tot_pend + tot_parc, 2)
    if abs(soma_matriz - tot_rec) < 0.01:
        st.success("✅ Validação Recebimentos = Matriz OK")
    else:
        st.error(f"❌ Divergência em Recebimentos: Matriz ({soma_matriz}) vs Extrato ({tot_rec})")

if st.sidebar.button("💾 Persistir Resultado no Google Sheets", use_container_width=True):
    salvar_matriz_sheets(SPREADSHEET_ID, df_matriz)
    st.sidebar.success("Matriz gravada com sucesso!")
