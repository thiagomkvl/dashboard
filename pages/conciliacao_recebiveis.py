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

# 1. Carregamento Geral do Google Sheets
df_bancos_raw, df_tasy_raw, df_matriz_full, df_config, df_fechados = carregar_dados_sheets()

if df_bancos_raw.empty or df_tasy_raw.empty:
    st.warning("Aguardando lançamentos nas abas Extratos_Bancos e Base_Tasy no Google Sheets.")
    st.stop()

# Normalização Base
df_rec = normalizar_recebimentos(df_bancos_raw)
df_tasy = normalizar_tasy(df_tasy_raw)

# Extração de Meses/Anos para o filtro
df_rec['Mes_Ano'] = df_rec['data'].dt.strftime('%m/%Y')
df_tasy['Mes_Ano'] = df_tasy['data'].dt.strftime('%m/%Y')
meses_disponiveis = sorted(df_rec['Mes_Ano'].unique(), reverse=True)

# -------------------------------------------------------------
# ⚙️ BLOCO VISÍVEL DE FILTROS E REGRAS NO TOPO DA TELA
# -------------------------------------------------------------
with st.expander("⚙️ CONFIGURAR REGRAS E FILTRAR PERÍODO", expanded=True):
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        st.markdown("#### 📅 Período")
        mes_selecionado = st.selectbox("Mês de Conciliação:", meses_disponiveis)
        
        # Verifica se o mês selecionado já foi fechado
        periodos_fechados = df_fechados['Mes_Ano'].tolist() if not df_fechados.empty else []
        is_fechado = mes_selecionado in periodos_fechados
        
    with col_f2:
        st.markdown("#### 🎯 Regras Globais")
        # Leitura das regras configuradas do Google Sheets (Aba Configuracoes)
        regras = dict(zip(df_config['Chave'], df_config['Valor'])) if not df_config.empty else {}
        transacoes_str = regras.get('tipos_transacao', '')
        transacoes_salvas = [x.strip() for x in transacoes_str.split(',') if x.strip()]
        
        todas_transacoes = sorted(df_rec['descricao'].unique().tolist())
        trans_validas = [t for t in transacoes_salvas if t in todas_transacoes]
        
        transacoes_selecionadas = st.multiselect(
            "Tipos de Transação a Conciliar:",
            options=todas_transacoes,
            default=trans_validas,
            help="Defina os tipos de transação operacionais (ex: PIX, TED, Adiantamento). Ficará salvo no Google Sheets."
        )
        
        if st.button("💾 Salvar Regras", type="primary"):
            if salvar_regras_sheets(transacoes_selecionadas):
                st.success("Regras fixadas para os próximos acessos!")

# -------------------------------------------------------------
# ⚙️ LÓGICA DO MOTOR DE CONCILIAÇÃO (ABERTO VS FECHADO)
# -------------------------------------------------------------
df_rec_mes = df_rec[df_rec['Mes_Ano'] == mes_selecionado].copy()
df_tasy_mes = df_tasy[df_tasy['Mes_Ano'] == mes_selecionado].copy()

if is_fechado:
    st.success(f"🔒 **PERÍODO CONSOLIDADO ({mes_selecionado})**: Este período já foi fechado. Exibindo resultados históricos congelados. O Motor de cálculo automático está desligado para este mês.")
    
    # Puxa os dados salvos da Matriz Completa do Sheets
    df_matriz_mes = df_matriz_full.copy()
    if not df_matriz_mes.empty and 'data_recebimento' in df_matriz_mes.columns:
        df_matriz_mes['tmp_mes'] = pd.to_datetime(df_matriz_mes['data_recebimento']).dt.strftime('%m/%Y')
        df_matriz_mes = df_matriz_mes[df_matriz_mes['tmp_mes'] == mes_selecionado].drop(columns=['tmp_mes'])
else:
    st.info(f"🟢 **PERÍODO EM ABERTO ({mes_selecionado})**: Motor executando a conciliação em tempo real com base nas regras ativas.")
    
    # Aplica o filtro de transações apenas se não estiver fechado
    if transacoes_selecionadas:
        df_rec_mes = df_rec_mes[df_rec_mes['descricao'].isin(transacoes_selecionadas)]
    
    # Motor calcula a conciliação do mês sob demanda
    df_matriz_mes = executar_conciliacao(df_rec_mes, df_tasy_mes)

# -------------------------------------------------------------
# 📊 VISUALIZAÇÃO: DASHBOARD, KPIS E ABAS
# -------------------------------------------------------------
if not df_matriz_mes.empty:
    
    # Identificação Inversa (Créditos Tasy Sem Recebimento)
    tasy_utilizados = set()
    for lista in df_matriz_mes['tasy_ids']:
        if isinstance(lista, list):
            tasy_utilizados.update(lista)
        elif pd.notna(lista):
            # Caso os IDs tenham vindo do Sheets como String já pré-processada
            tasy_utilizados.update(str(lista).split(','))
            
    df_tasy_sem_rec = df_tasy_mes[~df_tasy_mes['tasy_id'].isin(tasy_utilizados)]

    # Cálculo dos KPIs
    tot_rec = df_rec_mes['valor'].sum()
    tot_tasy = df_tasy_mes['valor'].sum()
    tot_conc = df_matriz_mes[df_matriz_mes['status'] == 'CONCILIADO']['valor_conciliado'].sum()
    tot_pend = df_matriz_mes[df_matriz_mes['status'] == 'PENDENTE']['valor_recebimento'].sum()
    tot_parc = df_matriz_mes[df_matriz_mes['status'] == 'PARCIAL']['valor_conciliado'].sum()
    tot_tasy_sobra = df_tasy_sem_rec['valor'].sum()

    pct_conc = (tot_conc / tot_rec * 100) if tot_rec > 0 else 0

    # Renderizando Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Recebimentos", f"R$ {tot_rec:,.2f}")
    c2.metric("Total Tasy", f"R$ {tot_tasy:,.2f}")
    c3.metric("Conciliado", f"R$ {tot_conc:,.2f}", f"{pct_conc:.1f}%")
    c4.metric("Pendências", f"R$ {tot_pend:,.2f}", delta_color="inverse")
    c5.metric("Tasy Sem Recebimento", f"R$ {tot_tasy_sobra:,.2f}", delta_color="off")

    st.divider()

    # Abas para separação dos dados
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Validador (Matriz)", "⚠️ Pendências", "📊 Conferência Data+Banco", "🛡️ Integridade"
    ])

    with tab1:
        st.dataframe(df_matriz_mes, use_container_width=True)

    with tab2:
        df_pendencias = df_matriz_mes[df_matriz_mes['status'] != 'CONCILIADO']
        if df_pendencias.empty:
            st.success("Tudo conciliado! Nenhuma pendência financeira encontrada.")
        else:
            st.dataframe(df_pendencias, use_container_width=True)

    with tab3:
        agg1 = df_rec_mes.groupby(['data', 'banco'])['valor'].sum().reset_index(name='Recebimentos')
        agg2 = df_tasy_mes.groupby(['data', 'banco'])['valor'].sum().reset_index(name='Tasy')
        df_agg = pd.merge(agg1, agg2, on=['data', 'banco'], how='outer').fillna(0.0)
        df_agg['Diferença'] = (df_agg['Recebimentos'] - df_agg['Tasy']).round(2)
        df_agg['Status'] = df_agg['Diferença'].apply(lambda x: 'OK' if abs(x) < 0.01 else 'Divergente')
        st.dataframe(df_agg, use_container_width=True)

    with tab4:
        soma_matriz = round(tot_conc + tot_pend + tot_parc, 2)
        if abs(soma_matriz - tot_rec) < 0.01:
            st.success("✅ Validação Recebimentos = Matriz OK")
        else:
            st.error(f"❌ Divergência Matemática Detectada: Matriz ({soma_matriz}) vs Recebimentos ({tot_rec})")

# -------------------------------------------------------------
# 🔐 BOTÃO DE TRAVAMENTO (SÓ APARECE SE ESTIVER ABERTO)
# -------------------------------------------------------------
if not is_fechado and not df_matriz_mes.empty:
    st.divider()
    col_lock1, col_lock2, col_lock3 = st.columns([1,2,1])
    with col_lock2:
        if st.button("🔒 FECHAR CONCILIAÇÃO DO MÊS (Travar Período)", type="primary", use_container_width=True):
            with st.spinner(f"Consolidando e gravando o período {mes_selecionado} no Google Sheets..."):
                if fechar_periodo_sheets(mes_selecionado, df_matriz_mes, df_matriz_full, df_fechados):
                    st.success(f"Conciliação de {mes_selecionado} concluída e travada com sucesso!")
                    st.rerun()
