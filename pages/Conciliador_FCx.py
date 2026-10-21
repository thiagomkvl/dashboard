import streamlit as st
st.set_page_config(page_title='Robô Conciliador FCx', page_icon='🔎', layout='wide')
import io
import zipfile
import pandas as pd
from modules.leitura_fcx import auditar_atual, QuotaLeitura
import time

st.title('Robô conciliador de fluxo de caixa')
st.caption('Confere a dinâmica, rastreia as fontes do dashboard e separa o residual entre extrato e saldos Tasy.')
st.info('A consulta é somente de leitura. Ajustes só são gravados após selecionar e aprovar o lote abaixo.')
aguardar = max(0, int(st.session_state.get('fcx_quota_ate', 0) - time.time()))
if aguardar:
    st.warning(f'Limite temporário do Sheets. Aguarde aproximadamente {aguardar} segundos e atualize a página.')
if st.button('Executar conciliação', type='primary', disabled=aguardar > 0):
    try:
        with st.spinner('Lendo as fontes em lote e conferindo as transações…'):
            novo = auditar_atual()
        st.session_state['conciliacao_fcx'] = novo
        st.session_state['conciliacao_fcx_em'] = pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%d/%m/%Y %H:%M:%S')
    except QuotaLeitura as e:
        st.session_state['fcx_quota_ate'] = time.time() + 60
        st.warning(str(e))
        if 'conciliacao_fcx' in st.session_state:
            st.info('A consulta anterior foi preservada. Não aprove ajustes até concluir uma nova consulta.')
        st.stop()
    except Exception as e:
        st.error(f'Conciliação não concluída: {e}')
        st.stop()
if 'conciliacao_fcx' not in st.session_state:
    st.write('Clique em Executar conciliação para consultar as abas usadas no fluxo e as duas abas de validação.')
    st.stop()
r = st.session_state['conciliacao_fcx']
st.caption('Consulta realizada em ' + st.session_state['conciliacao_fcx_em'] + ' · fontes reutilizadas por até 2 minutos; aprovação sempre revalida os dados.')
for aviso in r['avisos']:
    st.warning(aviso)
trans = r['transacoes']
c1, c2, c3 = st.columns(3)
c1.metric('Transações conferidas', len(trans))
c2.metric('Dinâmica × extrato divergentes', int((trans['Status dinâmica'] != 'Confere').sum()))
c3.metric('Sem vínculo identificado', int((trans['Cobertura dashboard'] == 'Sem vínculo identificado').sum()))
meses = r['mensal'].loc[r['mensal']['Mês com dashboard'], 'Ref'].tolist()
if not meses:
    st.warning('Nenhum mês com movimento no dashboard.')
    st.stop()
mes = st.selectbox('Mês para investigar', meses, format_func=lambda x: pd.Timestamp(x).strftime('%m/%Y'))
t1, t2, t3, t4 = st.tabs(['Conciliação mensal', 'Cada transação', 'Divergências das fontes', 'Lançamentos do extrato'])
with t1:
    st.write('Diferença dashboard − Tasy = (dashboard − extrato) + (extrato − Tasy).')
    st.dataframe(r['mensal'].round(2), hide_index=True, use_container_width=True)
    st.caption('Explicado mostra uma decomposição aritmética verificável; não autoriza corrigir todos os itens. '
               'O residual pode envolver escopo de contas, ajustes de saldo, datas ou dados do relatório. '
               'Meses sem dados no dashboard ficam vazios, nunca são tratados como conciliados.')
with t2:
    st.write('A dinâmica é conferida pelo valor original (soma da coluna K). O efeito de caixa considera D como entrada e C como saída, preservando valores negativos.')
    st.dataframe(trans.drop(columns=['Transação origem'], errors='ignore').round(2), hide_index=True, use_container_width=True)
    tx = r['mensal_transacoes']
    st.write('Detalhamento mensal por transação')
    st.dataframe(tx[tx['Ref'] == mes].round(2), hide_index=True, use_container_width=True)
    st.caption('Fontes agregadas não permitem afirmar cobertura individual. Nenhum valor é rateado ou atribuído artificialmente a uma transação.')
with t3:
    d = r['cobertura'];d = d[d['Ref'] == mes].copy()
    if st.checkbox('Mostrar somente diferenças', value=True):
        d = d[d['Impacto na diferença'].abs() >= .01]
    st.dataframe(d.sort_values('Impacto na diferença', key=abs, ascending=False).round(2), hide_index=True, use_container_width=True)
    st.caption('Impacto = contribuição do dashboard − efeito do extrato. Transferências e aplicações são agrupadas em pares para evidenciar o líquido; sua exclusão pode ser válida.')
    with st.expander('Rastreio dos valores que efetivamente entram no dashboard'):
        b = r['dashboard']
        st.dataframe(b[b['Ref'] == mes].round(2), hide_index=True, use_container_width=True)
with t4:
    e = r['extrato'];e = e[(e['Ref'] == mes) | e['Ref'].isna()].copy()
    bancos = st.multiselect('Banco', sorted(e['Banco'].dropna().astype(str).unique()))
    if bancos:
        e = e[e['Banco'].isin(bancos)]
    busca = st.text_input('Buscar transação ou sequência')
    if busca:
        e = e[e['Transação'].str.contains(busca, case=False, regex=False) | e['Seq'].astype(str).str.contains(busca, regex=False)]
    st.dataframe(e.round(2), hide_index=True, use_container_width=True)

buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
    for nome, tabela in r.items():
        if isinstance(tabela, pd.DataFrame):
            z.writestr(nome + '.csv', tabela.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'))
st.download_button('Baixar relatórios da conciliação (CSV)', buffer.getvalue(), 'conciliacao_fcx.zip', 'application/zip')


st.divider()
st.subheader('Ajustes propostos e aprovação em lote')
from modules.ajustes_fcx import propostas, ativos, SheetsStore, gravar_lote, PAPEIS
propostas_atual = propostas(r, r['ajustes'])
st.caption('O valor proposto corresponde à diferença comprovada entre uma fonte e o extrato. '
           'O residual extrato × Tasy não gera lançamento. Confira a evidência e a classificação antes de aprovar.')
login = getattr(st, 'user', None)
auth_email = login.get('email', '') if login is not None and getattr(login, 'is_logged_in', False) else ''
responsavel = st.text_input('Responsável pelos ajustes', value=auth_email)
identificacao = 'Login autenticado' if auth_email else 'Declarado pelo operador'
if not auth_email:
    st.caption('Sem login individual configurado: o nome informado será registrado como declarado pelo operador.')
else:
    responsavel = auth_email
if not propostas_atual.empty:
    visiveis = propostas_atual[propostas_atual['Mês'] == pd.Timestamp(mes).strftime('%Y-%m')].copy()
    visiveis['Revisão confirmada'] = False
    st.write('Propostas do mês selecionado')
    edit = st.data_editor(visiveis, hide_index=True, use_container_width=True,
        disabled=[c for c in visiveis.columns if c not in ('Selecionar','Papel','Motivo','Revisão confirmada')],
        column_config={'Papel': st.column_config.SelectboxColumn(options=list(PAPEIS), required=True),
                       'Selecionar': st.column_config.CheckboxColumn(),
                       'Revisão confirmada': st.column_config.CheckboxColumn()},
        key='propostas_edicao_' + st.session_state['conciliacao_fcx_em'])
    escolhas = edit[edit['Selecionar']].to_dict('records')
    if escolhas:
        previa = sum(float(x['Valor assinado']) for x in escolhas)
        atual_mes = r['mensal'].loc[r['mensal']['Ref'] == mes, 'Diferença dashboard − Tasy'].iloc[0]
        st.write(f'Lote: {len(escolhas)} ajuste(s) · efeito {previa:,.2f} · diferença prevista {atual_mes + previa:,.2f}')
    if st.button('Aprovar e gravar ajustes selecionados', type='primary', disabled=not escolhas):
        try:
            with st.spinner('Revalidando as fontes e gravando ajuste e log…'):
                fresh = auditar_atual(fresco=True)
                eventos = gravar_lote(SheetsStore.streamlit(), escolhas, fresh, responsavel, identificacao)
                st.cache_data.clear()
                st.session_state['conciliacao_fcx'] = auditar_atual(fresco=True)
                st.session_state['conciliacao_fcx_em'] = pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%d/%m/%Y %H:%M:%S')
            st.success(f'{len(eventos)} ajuste(s) confirmado(s) no Sheets. Atualize a consulta para visualizar os novos valores.')
        except Exception as e:
            st.error(str(e))
else:
    st.write('Nenhuma proposta de ajuste neste retrato.')

st.subheader('Ajustes ativos e estorno')
abertos = ativos(r['ajustes'])
st.dataframe(abertos, hide_index=True, use_container_width=True)
if not abertos.empty:
    ids_estorno = st.multiselect('Selecionar ajustes para estornar', abertos['ID'].tolist(),
        format_func=lambda x: x[:12] + ' · ' + abertos.set_index('ID').loc[x,'Transação'])
    motivo_estorno = st.text_input('Motivo do estorno')
    if st.button('Estornar selecionados e registrar logs', disabled=not ids_estorno):
        try:
            fresh = auditar_atual(fresco=True)
            gravar_lote(SheetsStore.streamlit(), [{'ID': x, 'Motivo': motivo_estorno} for x in ids_estorno],
                        fresh, responsavel, identificacao, estornar=True)
            st.cache_data.clear()
            st.session_state.pop('conciliacao_fcx', None)
            st.success('Estornos registrados. Execute novamente a conciliação.')
        except Exception as e:
            st.error(str(e))
with st.expander('Histórico completo de ajustes e estornos'):
    st.dataframe(r['ajustes'], hide_index=True, use_container_width=True)
