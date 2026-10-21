"""Ajustes aprovados e estornos, com escrita atômica e trilha imutável."""
import hashlib
import json
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

PLANILHA = '1J_UpsTsTHK_rIE48MlwwCSZjGgMVdR19N3YTAXLRIZ4'
ABA_AJUSTES = 'Ajustes_FCx'
ABA_LOGS = 'Logs_Conciliacao_FCx'
COLUNAS = ['ID', 'Chave', 'Mês', 'Banco', 'Transação', 'Destino origem', 'Valor assinado',
           'Papel', 'Classificação FCx', 'Fluxo', 'Motivo', 'Evidência hash',
           'Criado em', 'Responsável', 'Evento', 'Referência']
LOG_COLUNAS = ['ID evento', 'Data/hora', 'Responsável', 'Identificação', 'Ação', 'ID ajuste',
               'Chave', 'Mês', 'Valor anterior', 'Valor novo', 'Valor lançado',
               'Diferença antes', 'Diferença prevista depois', 'Motivo', 'Evidência hash']
PAPEIS = {'receita_op': ('Receitas operacionais', 'Fluxo de Caixa Operacional'),
          'custo_op': ('Despesas Administrativas e Gerais', 'Fluxo de Caixa Operacional'),
          'imposto': ('Impostos Correntes', 'Fluxo de Caixa Operacional'),
          'var_ap': ('Variações de Ativos e Passivos', 'Fluxo de Caixa Operacional'),
          'capex': ('Investimentos / CAPEX', 'Fluxo de Caixa de Investimentos'),
          'captacao': ('Captações', 'Fluxo de Caixa de Financiamento'),
          'amortizacao': ('Amortização de Empréstimos', 'Fluxo de Caixa de Financiamento'),
          'juros': ('Juros e Encargos Financeiros', 'Fluxo de Caixa de Financiamento')}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

def metadata_id(key):
    return int(digest(key)[:8], 16) % 2147483646 + 1

def cell(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if not math.isfinite(float(v)):
            raise ValueError('Valor não finito.')
        return {'userEnteredValue': {'numberValue': float(v)}}
    return {'userEnteredValue': {'stringValue': str(v)}}

def validar_ledger(df):
    if list(df.columns) != COLUNAS:
        raise ValueError('Cabeçalho de Ajustes_FCx incompatível; não foi possível aplicar os ajustes.')
    if df.empty:
        return df
    df = df.fillna('').copy()
    df['ID'] = df['ID'].astype(str)
    if df['ID'].duplicated().any() or df['ID'].eq('').any():
        raise ValueError('Ledger com IDs vazios ou duplicados.')
    def valor_numerico(v):
        if isinstance(v, (int, float)):
            return float(v)
        t = str(v).strip().replace('R$', '').replace(' ', '')
        negativo = t.startswith('(') and t.endswith(')')
        t = t.strip('()')
        if ',' in t:
            t = t.replace('.', '').replace(',', '.')
        return float(t) * (-1 if negativo else 1)
    df['Valor assinado'] = df['Valor assinado'].map(valor_numerico)
    if not df['Valor assinado'].map(lambda v: math.isfinite(v)).all():
        raise ValueError('Ledger com valor inválido.')
    if not df['Evento'].isin(['APROVAR', 'ESTORNAR']).all() or not df['Papel'].isin(PAPEIS).all():
        raise ValueError('Evento ou papel inválido no ledger.')
    originais = df[df['Evento'] == 'APROVAR'].set_index('ID')
    estornos = df[df['Evento'] == 'ESTORNAR']
    if estornos['Referência'].duplicated().any():
        raise ValueError('Mesmo ajuste estornado mais de uma vez.')
    for _, row in estornos.iterrows():
        if row['Referência'] not in originais.index:
            raise ValueError('Estorno sem ajuste original.')
        original = originais.loc[row['Referência']]
        for c in ('Chave', 'Mês', 'Papel', 'Destino origem'):
            if str(original[c]) != str(row[c]):
                raise ValueError('Estorno não corresponde ao ajuste original.')
        if abs(float(original['Valor assinado']) + float(row['Valor assinado'])) > .005:
            raise ValueError('Valor do estorno inválido.')
    ativos = originais[~originais.index.isin(estornos['Referência'])]
    if ativos['Chave'].duplicated().any():
        raise ValueError('Há mais de um ajuste ativo para a mesma causa.')
    return df

def ativos(df):
    df = validar_ledger(df)
    return df[(df['Evento'] == 'APROVAR') & ~df['ID'].isin(df.loc[df['Evento'] == 'ESTORNAR', 'Referência'])].copy()

def carregar_ajustes(conn):
    # Falha explícita evita exibir um saldo sem ajustes quando a leitura falhar.
    return validar_ledger(conn.read(worksheet=ABA_AJUSTES, ttl=0))

def linhas_dashboard(df):
    df = validar_ledger(df)
    linhas = []
    for _, r in df.iterrows():
        efeito = float(r['Valor assinado'])
        if abs(efeito) < .005:
            continue
        ref = pd.Timestamp(str(r['Mês']) + '-01')
        papel = r['Papel']
        # A fórmula do fluxo subtrai custos; manter sinal para estornos corretamente.
        valor = efeito if papel in ('receita_op', 'captacao', 'var_ap') else -efeito
        linhas.append(dict(Ref=ref, Categoria='Ajuste ' + str(r['ID'])[:12] + ' · ' + r['Transação'],
                           Valor=valor, Tipo='Entrada' if papel in ('receita_op', 'captacao') else 'Saída',
                           Grupo='Ajustes aprovados', Classif=r['Classificação FCx'], Fluxo=r['Fluxo'],
                           Papel=papel, Detalhe=r['Motivo'], Destino=r['Destino origem'],
                           **{'Efeito dashboard': efeito}))
    return pd.DataFrame(linhas)

def propostas(resultado, ledger):
    abertos = ativos(ledger)
    rows = []
    for _, c in resultado['cobertura'].iterrows():
        if str(c['Destino']).startswith('Ajustes aprovados'):
            continue
        delta = round(-float(c['Impacto na diferença']), 2)
        if abs(delta) < .01:
            continue
        ref = pd.Timestamp(c['Ref']);dest = c['Destino']
        origem = resultado['extrato'];origem = origem[(origem['Ref'] == ref) & (origem['Destino'] == dest)]
        atual = resultado['dashboard'];atual = atual[(atual['Ref'] == ref) & (atual['Destino'] == dest) & (atual['Grupo'] != 'Ajustes aprovados')]
        evid = {'origem': origem[['Banco', 'Seq', 'Data', 'Transação', 'Valor extrato', 'Ação']].astype(str).sort_values(['Banco', 'Seq', 'Transação']).to_dict('records'),
                'dashboard': atual[['Categoria', 'Valor', 'Tipo', 'Papel', 'Efeito dashboard']].astype(str).sort_values(['Categoria', 'Valor']).to_dict('records')}
        hash_evid = digest(evid)
        chave = digest([ref.strftime('%Y-%m'), dest])
        possui = not abertos[abertos['Chave'] == chave].empty
        txs = sorted(set(origem['Transação'].astype(str)))
        n = len(txs)
        # Ajustes de saldo, pares internos, agregados e fonte sem correspondência
        # sempre ficam para revisão, sem selecionar automaticamente.
        cautela = any(t in dest.lower() for t in ('ajuste de saldo', 'aplicações e resgates', 'transferências internas'))
        invalida = (not origem.empty) and (origem['Efeito extrato'].isna().any() or origem['Data'].isna().any())
        revisao = possui or n != 1 or cautela or origem.empty
        if not atual.empty and len(set(atual['Papel'])) == 1:
            papel = atual['Papel'].iloc[0]
        elif n == 1 and delta > 0:
            papel = 'receita_op'
        else:
            papel = 'custo_op'
        if papel not in PAPEIS:
            papel = 'var_ap'
        geracao = int((ledger['Chave'] == chave).sum())
        rows.append({'Selecionar': False, 'Chave': chave, 'ID proposta': digest([chave, hash_evid, geracao]),
                     'Mês': ref.strftime('%Y-%m'), 'Banco': '; '.join(sorted(set(origem['Banco'].astype(str)))),
                     'Transação': '; '.join(txs) or dest, 'Destino origem': dest, 'Valor assinado': delta,
                     'Papel': papel, 'Motivo': '', 'Evidência hash': hash_evid,
                     'Situação': 'Dados de origem inválidos' if invalida else ('Ajuste ativo: revisar/estornar' if possui else ('Revisão necessária' if revisao else 'Proposta com transação identificada')),
                     'Valor anterior': round(float(c['Efeito dashboard']), 2),
                     'Valor novo': round(float(c['Efeito extrato']), 2)})
    return pd.DataFrame(rows)

class SheetsStore:
    def __init__(self, session, spreadsheet_id=PLANILHA):
        self.session, self.id = session, spreadsheet_id
        self.url = 'https://sheets.googleapis.com/v4/spreadsheets/' + spreadsheet_id
    @classmethod
    def streamlit(cls):
        import streamlit as st
        from google.oauth2.service_account import Credentials
        from google.auth.transport.requests import AuthorizedSession
        conf = dict(st.secrets.get('connections', {}).get('gsheets', {}))
        cfg = dict(st.secrets.get('conciliacao', {}))
        info = conf.get('service_account_info', conf)
        if isinstance(info, str):
            info = json.loads(info)
        if not isinstance(info, dict) or not info.get('private_key'):
            info = dict(st.secrets.get('gcp_service_account', {}))
        if not info.get('private_key'):
            raise ValueError('Gravação exige conta de serviço com acesso de Editor nos secrets. Consulte LEIA-ME-AJUSTES.md.')
        target = str(cfg.get('spreadsheet_id', PLANILHA))
        fonte = str(conf.get('spreadsheet', ''))
        match = re.search(r'/spreadsheets/d/([^/]+)', fonte)
        id_fonte = match.group(1) if match else (fonte if re.fullmatch(r'[A-Za-z0-9_-]{20,}', fonte) else '')
        if id_fonte and id_fonte != target:
            raise ValueError('A planilha de leitura difere da planilha de ajustes. Confira a configuração.')
        cred = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        return cls(AuthorizedSession(cred), target)
    def request(self, method, suffix='', **kwargs):
        response = self.session.request(method, self.url + suffix, timeout=60, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f'Google Sheets recusou a operação (HTTP {response.status_code}). Confira acesso, duplicidade e integridade das abas. Nenhuma tentativa automática será feita.')
        return response.json()
    def metadata(self):
        return self.request('GET', params={'fields': 'sheets.properties,developerMetadata'})
    def ledger(self):
        v = self.request('GET', '/values/Ajustes_FCx!A:P', params={'valueRenderOption': 'UNFORMATTED_VALUE'}).get('values', [])
        if not v or v[0] != COLUNAS:
            raise ValueError('Cabeçalhos de Ajustes_FCx não conferem.')
        return validar_ledger(pd.DataFrame([r + ['']*(len(COLUNAS)-len(r)) for r in v[1:]], columns=COLUNAS))
    def batch(self, requests):
        return self.request('POST', ':batchUpdate', json={'requests': requests})

def guard(key):
    return {'createDeveloperMetadata': {'developerMetadata': {'metadataId': metadata_id(key),
            'metadataKey': 'fcx:' + key, 'metadataValue': digest(key),
            'location': {'spreadsheet': True}, 'visibility': 'DOCUMENT'}}}

def preparar_lote(store, selecionadas, fresh, responsavel, identificacao='Declarado pelo operador', estornar=False):
    if len(responsavel.strip()) < 3:
        raise ValueError('Informe o responsável pelo lançamento.')
    if not selecionadas or len(selecionadas) > 1000:
        raise ValueError('Selecione de 1 a 1000 ajustes por lote.')
    ledger = store.ledger();meta = store.metadata()
    ids = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    if not all(x in ids for x in (ABA_AJUSTES, ABA_LOGS)):
        raise ValueError('As duas abas de ajustes e logs são obrigatórias.')
    if not estornar:
        validas = propostas(fresh, ledger)
        validas = validas.set_index('ID proposta') if not validas.empty else pd.DataFrame()
    header_log = store.request('GET', '/values/Logs_Conciliacao_FCx!A1:O1').get('values', [])
    if not header_log or header_log[0] != LOG_COLUNAS:
        raise ValueError('Cabeçalhos de Logs_Conciliacao_FCx não conferem.')
    eventos, logs, requests = [], [], []
    now = datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')
    current_ativos = ativos(ledger)
    vistos = set()
    saldos_lote = {}
    for sel in selecionadas:
        motivo = str(sel.get('Motivo', '')).strip()
        if len(motivo) < 10:
            raise ValueError('Descreva o motivo com pelo menos 10 caracteres para cada ajuste.')
        if estornar:
            found = current_ativos[current_ativos['ID'] == sel['ID']]
            if len(found) != 1:
                raise ValueError('Ajuste já estornado ou inexistente. Atualize a consulta.')
            old = found.iloc[0].to_dict();key=old['Chave'];event_id=digest(['ESTORNAR', old['ID']])
            row = dict(old);row.update({'ID':event_id, 'Valor assinado':-float(old['Valor assinado']),
                'Evento':'ESTORNAR','Referência':old['ID'], 'Motivo':motivo, 'Criado em':now,'Responsável':responsavel})
            requests.append({'deleteDeveloperMetadata': {'dataFilter': {'developerMetadataLookup': {'metadataId': metadata_id('active:'+key)}}}})
            anterior=float(old['Valor assinado']);novo=0.0
        else:
            pid=sel['ID proposta']
            if pid not in validas.index:
                raise ValueError('A origem mudou desde a proposta. Execute novamente a conciliação.')
            v=validas.loc[pid].to_dict();key=v['Chave'];event_id=pid
            if not current_ativos[current_ativos['Chave'] == key].empty:
                raise ValueError('Já existe ajuste ativo para essa causa. Revise ou estorne antes.')
            if v['Situação'] == 'Dados de origem inválidos':
                raise ValueError('Corrija data e ação da origem antes de aprovar.')
            if v['Situação'] == 'Revisão necessária' and not sel.get('Revisão confirmada', False):
                raise ValueError('Confirme a revisão dos ajustes de saldo, transferências ou valores agregados.')
            papel=str(sel.get('Papel',v['Papel']))
            if papel not in PAPEIS:
                raise ValueError('Selecione um papel de fluxo válido.')
            classificacao,fluxo=PAPEIS[papel]
            row={c:v.get(c,'') for c in COLUNAS};row.update({'ID':event_id,'Papel':papel,
                'Classificação FCx':classificacao,'Fluxo':fluxo,'Motivo':motivo,
                'Criado em':now,'Responsável':responsavel,'Evento':'APROVAR','Referência':''})
            anterior=float(v['Valor anterior']);novo=float(v['Valor novo'])
            requests.append(guard('active:'+key))
        if key in vistos or event_id in set(ledger['ID']):
            raise ValueError('Ajuste duplicado no lote ou já registrado.')
        vistos.add(key);requests.append(guard('event:'+event_id));eventos.append(row)
        mm=fresh['mensal'];mes=pd.Timestamp(row['Mês']+'-01')
        diff=mm.loc[mm['Ref']==mes,'Diferença dashboard − Tasy']
        antes=saldos_lote.get(row['Mês'], float(diff.iloc[0]) if len(diff) and pd.notna(diff.iloc[0]) else None)
        if antes is not None:
            saldos_lote[row['Mês']] = round(antes + float(row['Valor assinado']), 2)
        logs.append(dict(zip(LOG_COLUNAS,[event_id,now,responsavel,identificacao,row['Evento'],event_id,
            key,row['Mês'],anterior,novo,row['Valor assinado'],'' if antes is None else antes,
            '' if antes is None else round(antes+float(row['Valor assinado']),2),motivo,row['Evidência hash']])))
    # Ajuste, log e travas participam do mesmo batch: todos gravam ou nenhum grava.
    for aba, cols, rows in ((ABA_AJUSTES,COLUNAS,eventos),(ABA_LOGS,LOG_COLUNAS,logs)):
        requests.append({'appendCells': {'sheetId': ids[aba], 'rows': [{'values': [cell(r[c]) for c in cols]} for r in rows], 'fields': 'userEnteredValue'}})
    if len(json.dumps({"requests": requests}, ensure_ascii=False).encode("utf-8")) > 1_800_000:
        raise ValueError("O lote excede o tamanho permitido. Reduza a seleção e tente novamente; nada foi gravado.")
    return requests,eventos

def gravar_lote(store, selecionadas, fresh, responsavel, identificacao='Declarado pelo operador', estornar=False):
    requests,eventos=preparar_lote(store,selecionadas,fresh,responsavel,identificacao,estornar)
    store.batch(requests)
    saved=store.ledger()
    if not set(e['ID'] for e in eventos).issubset(set(saved['ID'])):
        raise RuntimeError('Escrita enviada, mas não confirmada. Consulte os logs antes de tentar novamente.')
    return eventos
