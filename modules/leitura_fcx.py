"""Retrato das fontes do conciliador com metadata + values.batchGet."""
import random
import time
import pandas as pd
from modules.ajustes_fcx import SheetsStore

LARGURAS = {'Transações_FCx': 'B', 'FCx_Extrato': 'N', 'Base_Despesas': 'G',
            'Fluxo_Despesas_Borderô': None, 'Fluxo_Adiantamentos': None,
            'Fluxo_Receita': None, 'Classificacao_FCx': 'C', 'Saldo_FCx': None,
            'Base_Saldo_FCx_Tasy': None, 'FCx_Devolução_Adiantamento': None,
            'Ajustes_FCx': 'P'}

class QuotaLeitura(RuntimeError):
    pass

def letra(n):
    s = ''
    while n:
        n, r = divmod(n-1,26); s = chr(65+r)+s
    return s

def get_com_retry(store, suffix='', params=None, esperar=time.sleep):
    # Somente GET tem repetição automática. As gravações nunca são repetidas.
    for tentativa in range(4):
        response = store.session.request('GET', store.url + suffix, params=params, timeout=60)
        if response.status_code == 429:
            if tentativa == 3:
                raise QuotaLeitura('O Google Sheets ainda está com o limite de leituras ocupado. Aguarde cerca de 1 minuto e execute novamente. Evite atualizar outros painéis durante esse intervalo.')
            esperar(min(2**tentativa + random.random(), 8))
            continue
        if response.status_code >= 400:
            raise RuntimeError(f'Falha na leitura do Google Sheets (HTTP {response.status_code}). Confira o acesso da conta de serviço e as abas do projeto.')
        return response.json()

class RetratoLote:
    def __init__(self, tabelas):
        self.tabelas=tabelas
    def read(self, worksheet, ttl=0):
        if worksheet not in self.tabelas:
            raise ValueError(f'Aba não incluída no retrato: {worksheet}')
        return self.tabelas[worksheet].copy(deep=True)

def buscar_lote(store):
    meta=get_com_retry(store, params={'fields':'sheets.properties'})
    sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}
    nomes=[];ranges=[]
    for nome, last in LARGURAS.items():
        real=nome
        if nome=='FCx_Devolução_Adiantamento' and nome not in sheets and 'FCx_Devolucao_Adiantamento' in sheets:
            real='FCx_Devolucao_Adiantamento'
        if real not in sheets:
            raise ValueError(f'Aba obrigatória ausente: {nome}. Confira a planilha configurada.')
        grid=sheets[real]['gridProperties'];fim=last or letra(grid['columnCount'])
        ranges.append("'"+real.replace("'","''")+"'!A1:"+fim+str(grid['rowCount']))
        nomes.append((nome,real))
    payload=get_com_retry(store, '/values:batchGet', params={'ranges':ranges,
            'valueRenderOption':'UNFORMATTED_VALUE','dateTimeRenderOption':'SERIAL_NUMBER'})
    values=payload.get('valueRanges',[])
    if len(values)!=len(nomes):
        raise ValueError('O Google retornou um retrato incompleto. Nenhuma conciliação foi calculada.')
    tabelas={}
    for (nome,real),item in zip(nomes,values):
        rows=item.get('values',[])
        if not rows:
            raise ValueError(f'Aba vazia ou sem cabeçalho: {real}.')
        width=max(map(len,rows));rows=[r+['']*(width-len(r)) for r in rows]
        # Preserva cabeçalhos vazios/repetidos: as matrizes são lidas por posição.
        tabelas[nome]=pd.DataFrame(rows[1:],columns=rows[0])
        if real!=nome:tabelas[real]=tabelas[nome]
    return tabelas

def obter_retrato(fresco=False):
    import streamlit as st
    @st.cache_data(ttl=120, show_spinner=False, max_entries=4)
    def _cached(planilha, identidade, _store):
        return buscar_lote(_store)
    store=SheetsStore.streamlit()
    if fresco:
        return RetratoLote(buscar_lote(store))
    email=getattr(getattr(store.session,'credentials',None),'service_account_email','configurada')
    return RetratoLote(_cached(store.id,email,store))

def auditar_atual(fresco=False):
    from modules.conciliador_fcx import auditar
    return auditar(obter_retrato(fresco=fresco))
