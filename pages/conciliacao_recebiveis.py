import streamlit as st
import pandas as pd
from core.normalizacao import normalizar_recebimentos, normalizar_tasy
from core.conciliacao import executar_conciliacao
from services.google_sheets import carregar_dados_sheets, salvar_regras_sheets, fechar_periodo_sheets

st.set_page_config(page_title="Conciliação de Recebíveis", layout="wide", page_icon="🏦")
st.title("🏦 Painel de Conciliação de Recebíveis")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Recarregar Dados Base", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 1. Carregamento Geral
df_bancos_raw, df_tasy_raw, df_matriz_full, df_config, df_fechados = carregar_dados_sheets()

if df_bancos_raw.empty or df_tasy_raw.empty:
    st.warning("Aguardando lançamentos nas abas Extratos_Bancos e Base_Tasy no Google Sheets.")
    st.stop()

df_rec = normalizar_recebimentos(df_bancos_raw)
df_tasy = normalizar_tasy(df_tasy_raw)

# Extração de Meses/Anos
df_rec['Mes_Ano'] = df_rec['data'].dt.strftime('%m/%Y')
df_tasy['Mes_Ano'] = df_tasy['data'].dt.strftime('%m/%Y')
meses_disponiveis = sorted(df_rec['Mes_Ano'].unique(), reverse=True)

# -------------------------------------------------------------
# BARRA LATERAL: CONTROLES
# -------------------------------------------------------------
st.sidebar.markdown("### 📅 Filtro de Período")
mes_selecionado = st.sidebar.selectbox("Selecione o Mês para Conciliar:", meses_disponiveis)

periodos_fechados = df_fechados['Mes_Ano'].tolist() if not df_fechados.empty else []
is_fechado = mes_selecionado in periodos_fechados

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ Regras Globais")

# Lendo regras configuradas do Google Sheets
regras = dict(zip(df_config['Chave'], df_config['Valor'])) if not df_config.empty else {}
transacoes_str = regras.get('tipos_transacao', '')
transacoes_salvas = [x.strip() for x in transacoes_str.split(',') if x.strip()]

todas_transacoes = sorted(df_rec['descricao'].unique().tolist())
trans_validas = [t for t in transacoes_salvas if t in todas_transacoes]

transacoes_selecionadas = st.sidebar.multiselect(
    "Tipos de Transação a Conciliar:",
    options=todas_transacoes,
    default=trans_validas,
    help="Define quais tipos de lançamento (ex: PIX, TED, Adiantamento) serão validados pelo motor."
)

if st.sidebar.button("💾 Salvar Regras", use_container_width=True):
    if salvar_regras_sheets(transacoes_selecionadas):
        st.sidebar.success("Regras fixadas para os próximos acessos!")

# -------------------------------------------------------------
# LÓGICA DO MOTOR (ABERTO VS FECHADO)
# -------------------------------------------------------------
df_rec_mes = df_rec[df_rec['Mes_Ano'] == mes_selecionado].copy()
df_tasy_mes = df_tasy[df_tasy['Mes_Ano'] == mes_selecionado].copy()

if is_fechado:
    st.success(f"🔒 **PERÍODO CONSOLIDADO ({mes_selecionado})**: Este período já foi fechado. Exibindo resultados históricos congelados. Nenhuma alteração afetará este mês.")
    
    # Recupera apenas as linhas fechadas deste mês da Matriz Histórica
    df_matriz_mes = df_matriz_full.copy()
    if not df_matriz_mes.empty and 'data_recebimento' in df_matriz_mes.columns:
        df_matriz_mes['tmp_mes'] = pd.to_datetime(df_matriz_mes['data_recebimento']).dt.strftime('%m/%Y')
        df_matriz_mes = df_matriz_mes[df_matriz_mes['tmp_mes'] == mes_selecionado].drop(columns=['tmp_mes'])
    
    st.dataframe(df_matriz_mes, use_container_width=True)
else:
    st.info(f"🟢 **PERÍODO EM ABERTO ({mes_selecionado})**: Calculando conciliação em tempo real com base nas regras.")
    
    if transacoes_selecionadas:
        df_rec_mes = df_rec_mes[df_rec_mes['descricao'].isin(transacoes_selecionadas)]
    
    # Motor calcula sob demanda
    df_matriz_mes = executar_conciliacao(df_rec_mes, df_tasy_mes)
    
    st.dataframe(df_matriz_mes, use_container_width=True)
    
    st.divider()
    
    # Botão de travamento corrigido
    if st.button("🔒 Fechar Conciliação do Mês (Travar Período)", type="primary"):
        with st.spinner(f"Consolidando período {mes_selecionado}..."):
            if fechar_periodo_sheets(mes_selecionado, df_matriz_mes, df_matriz_full, df_fechados):
                st.success(f"Conciliação de {mes_selecionado} concluída e travada com sucesso!")
                st.rerun()
