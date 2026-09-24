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

# -------------------------------------------------------------
# 1. CARREGAMENTO GERAL DO GOOGLE SHEETS
# -------------------------------------------------------------
df_bancos_raw, df_tasy_raw, df_matriz_full, df_config, df_fechados = carregar_dados_sheets()

if df_bancos_raw.empty or df_tasy_raw.empty:
    st.warning("Aguardando lançamentos nas abas Extratos_Bancos e Base_Tasy no Google Sheets.")
    st.stop()

# Normalização Base (apenas para créditos/recebimentos do Motor)
df_rec = normalizar_recebimentos(df_bancos_raw)
df_tasy = normalizar_tasy(df_tasy_raw)

# Extração de Meses/Anos para o filtro
if not df_rec.empty:
    df_rec['Mes_Ano'] = df_rec['data'].dt.strftime('%m/%Y')
else:
    df_rec['Mes_Ano'] = []
    
if not df_tasy.empty:
    df_tasy['Mes_Ano'] = df_tasy['data'].dt.strftime('%m/%Y')
else:
    df_tasy['Mes_Ano'] = []
    
meses_disponiveis = sorted(list(set(df_rec['Mes_Ano'].unique().tolist() + df_tasy['Mes_Ano'].unique().tolist())), reverse=True)

if not meses_disponiveis:
    st.info("Nenhum dado válido encontrado para conciliação.")
    st.stop()

# -------------------------------------------------------------
# 2. BLOCO VISÍVEL DE FILTROS E REGRAS NO TOPO DA TELA
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
        # Leitura das regras configuradas
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
# 3. LÓGICA DO MOTOR DE CONCILIAÇÃO (ABERTO VS FECHADO)
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
# 4. VISUALIZAÇÃO: DASHBOARD, KPIS E ABAS
# -------------------------------------------------------------
if not df_matriz_mes.empty:
    
    # Identificação Inversa (Créditos Tasy Sem Recebimento)
    tasy_utilizados = set()
    if 'tasy_ids' in df_matriz_mes.columns:
        for lista in df_matriz_mes['tasy_ids']:
            if isinstance(lista, list):
                tasy_utilizados.update(lista)
            elif pd.notna(lista):
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
        "🔍 Validador (Matriz)", "⚠️ Pendências", "📊 Conferência Data+Banco (Geral)", "🛡️ Integridade"
    ])

    with tab1:
        st.dataframe(df_matriz_mes, use_container_width=True)

    with tab2:
        df_pendencias = df_matriz_mes[df_matriz_mes['status'] != 'CONCILIADO']
        if df_pendencias.empty:
            st.success("Tudo conciliado! Nenhuma pendência financeira encontrada.")
        else:
            st.dataframe(df_pendencias, use_container_width=True)

    # Nova Lógica de Conferência Data + Banco (Aba 3)
    with tab3:
        st.subheader("Conferência Agregada por Data e Banco (Entradas e Saídas)")
        
        # 1. Função auxiliar de limpeza financeira
        def calc_val(v):
            try:
                if pd.isna(v): return 0.0
                if isinstance(v, (int, float)): return float(v)
                return float(str(v).replace('R$', '').replace('.', '').replace(',', '.').strip())
            except:
                return 0.0

        df_b_raw = df_bancos_raw.copy()
        df_t_raw = df_tasy_raw.copy()

        # 2. Prepara colunas padrões independente de espaços no cabeçalho
        for d in [df_b_raw, df_t_raw]:
            d.columns = [str(c).strip() for c in d.columns]
            col_banco = d.columns[0] # Pela imagem, Banco/Agência/Conta é a Coluna A
            
            d['Banco_Calc'] = d[col_banco].astype(str).str.strip()
            
            # Encontrar colunas de Data, Débito e Crédito dinamicamente
            col_data = next((c for c in d.columns if 'data' in c.lower() or 'dt' in c.lower()), d.columns[1])
            col_deb = next((c for c in d.columns if 'débito' in c.lower() or 'debito' in c.lower()), 'Vl Débito' if 'Vl Débito' in d.columns else None)
            col_cred = next((c for c in d.columns if 'crédito' in c.lower() or 'credito' in c.lower() or 'valor' in c.lower()), 'Vl Crédito' if 'Vl Crédito' in d.columns else None)
            
            d['Data_Calc'] = pd.to_datetime(d[col_data], dayfirst=True, errors='coerce')
            d['Vl_Deb'] = d[col_deb].apply(calc_val) if col_deb else 0.0
            d['Vl_Cred'] = d[col_cred].apply(calc_val) if col_cred else 0.0

        # 3. Filtra o mês selecionado no painel
        df_b_raw = df_b_raw[df_b_raw['Data_Calc'].dt.strftime('%m/%Y') == mes_selecionado]
        df_t_raw = df_t_raw[df_t_raw['Data_Calc'].dt.strftime('%m/%Y') == mes_selecionado]

        # 4. Agrupa TASY
        agg_tasy = df_t_raw.groupby(['Data_Calc', 'Banco_Calc']).agg(
            EntrTasy=('Vl_Cred', 'sum'),
            SaidaTasy=('Vl_Deb', 'sum')
        ).reset_index()

        # 5. Agrupa BANCOS
        agg_bancos = df_b_raw.groupby(['Data_Calc', 'Banco_Calc']).agg(
            EntrBanco=('Vl_Cred', 'sum'),
            SaidaBanco=('Vl_Deb', 'sum')
        ).reset_index()

        # 6. Cruza os dados
        df_resumo = pd.merge(agg_tasy, agg_bancos, on=['Data_Calc', 'Banco_Calc'], how='outer').fillna(0.0)

        # 7. Executa os cálculos (Diferenças e Movimentos)
        df_resumo['Dif Entr'] = df_resumo['EntrTasy'] - df_resumo['EntrBanco']
        df_resumo['Dif Saída'] = df_resumo['SaidaTasy'] - df_resumo['SaidaBanco']
        
        df_resumo['Mov Tasy'] = df_resumo['EntrTasy'] - df_resumo['SaidaTasy']
        df_resumo['Mov Banco'] = df_resumo['EntrBanco'] - df_resumo['SaidaBanco']
        df_resumo['Dif Mov'] = df_resumo['MovTasy'] - df_resumo['MovBanco']

        # 8. Define Status
        df_resumo['Status'] = df_resumo.apply(
            lambda r: "OK" if abs(r['Dif Entr']) < 0.01 and abs(r['Dif Saída']) < 0.01 else "DIVERGENTE", 
            axis=1
        )

        # 9. Formata e exibe
        df_resumo['Data'] = df_resumo['Data_Calc'].dt.strftime('%d/%m/%Y')
        
        colunas_finais = [
            'Data', 'Banco_Calc', 'EntrTasy', 'EntrBanco', 'Dif Entr', 
            'SaidaTasy', 'SaidaBanco', 'Dif Saída', 'Mov Tasy', 'Mov Banco', 'Dif Mov', 'Status'
        ]
        
        df_view = df_resumo[colunas_finais].sort_values(['Data_Calc', 'Banco_Calc']).rename(columns={'Banco_Calc': 'Banco'})
        
        # Função para pintar divergentes de vermelho
        def colorir_tabela(val):
            if val == 'DIVERGENTE':
                return 'background-color: #ffeaea; color: #d63031; font-weight: bold;'
            elif val == 'OK':
                return 'color: #00b894; font-weight: bold;'
            return ''
            
        # Aplicação segura da estilização (compatível com Pandas > 2.0)
        estilo = df_view.style
        if hasattr(estilo, 'map'):
            estilo = estilo.map(colorir_tabela, subset=['Status'])
        else:
            estilo = estilo.applymap(colorir_tabela, subset=['Status'])
            
        estilo = estilo.format({
            'EntrTasy': '{:,.2f}', 'EntrBanco': '{:,.2f}', 'Dif Entr': '{:,.2f}',
            'SaidaTasy': '{:,.2f}', 'SaidaBanco': '{:,.2f}', 'Dif Saída': '{:,.2f}',
            'Mov Tasy': '{:,.2f}', 'Mov Banco': '{:,.2f}', 'Dif Mov': '{:,.2f}'
        })
        
        st.dataframe(estilo, use_container_width=True, height=500)

    with tab4:
        soma_matriz = round(tot_conc + tot_pend + tot_parc, 2)
        if abs(soma_matriz - tot_rec) < 0.01:
            st.success("✅ Validação Recebimentos = Matriz OK")
        else:
            st.error(f"❌ Divergência Matemática Detectada: Matriz ({soma_matriz}) vs Recebimentos ({tot_rec})")

# -------------------------------------------------------------
# 5. BOTÃO DE TRAVAMENTO (SÓ APARECE SE ESTIVER ABERTO)
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
