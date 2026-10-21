"""Auditoria somente de leitura. Reutiliza as regras reais de Fluxo_de_Caixa.py."""
import ast
import os
import re
import unicodedata
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import pandas as pd

ABAS = ('Transações_FCx', 'FCx_Extrato', 'Base_Despesas', 'Fluxo_Despesas_Borderô',
        'Fluxo_Adiantamentos', 'Fluxo_Receita', 'Classificacao_FCx', 'Saldo_FCx',
        'Base_Saldo_FCx_Tasy', 'FCx_Devolução_Adiantamento')

class _SemInterface:
    def cache_data(self, *args, **kwargs):
        return lambda f: f


def carregar_regras(conn, arquivo=None):
    arquivo = Path(arquivo or Path(__file__).resolve().parents[1] / 'pages' / 'Fluxo_de_Caixa.py')
    arvore = ast.parse(arquivo.read_text(encoding='utf-8'))
    ns = dict(pd=pd, os=os, re=re, unicodedata=unicodedata, datetime=datetime,
              st=_SemInterface(), conectar_sheets=lambda: conn)
    # Não executa imports, interface, navegação ou operações no topo da página.
    for node in arvore.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    ns[target.id] = value
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for name, item in zip(target.elts, value):
                        if isinstance(name, ast.Name):
                            ns[name.id] = item
        elif isinstance(node, ast.FunctionDef) and node.name != 'conectar_sheets':
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(arquivo), 'exec'), ns)
    ns['parse_data'] = lru_cache(maxsize=10000)(ns['parse_data'])
    return ns


def efeito_dashboard(row):
    papel, valor = row['Papel'], float(row['Valor'])
    if papel == 'var_ap':
        return valor
    if papel == 'receita_op':
        return valor
    if papel == 'captacao':
        return valor if row['Tipo'] == 'Entrada' else 0.0
    if papel in ('custo_op', 'imposto', 'capex', 'amortizacao', 'juros'):
        return -valor
    return 0.0


def auditar(conn, arquivo=None):
    ns = carregar_regras(conn, arquivo)
    norm, numero, data = ns['normalizar_chave'], ns['limpa_valor'], ns['parse_data']
    # Cache apenas deste ciclo: cada aba é lida uma vez e todas as comparações
    # utilizam o mesmo retrato, sem reaproveitar dados de uma execução anterior.
    class Retrato:
        def __init__(self):
            self.cache = {}
        def read(self, worksheet, ttl=0):
            if worksheet not in self.cache:
                self.cache[worksheet] = conn.read(worksheet=worksheet, ttl=0)
            return self.cache[worksheet].copy()
    retrato = Retrato()
    ns['conectar_sheets'] = lambda: retrato
    base, avisos = ns['carregar_fluxo']()
    if base.empty:
        raise ValueError('Dashboard sem dados: ' + '; '.join(avisos))
    mapa = ns['carregar_mapa_classificacao']()
    cls = base['Categoria'].map(lambda c: ns['aplicar_classificacao'](c, mapa))
    base['Classif'] = cls.map(lambda x: x[0])
    base['Fluxo'] = cls.map(lambda x: x[1])
    base['Papel'] = base.apply(lambda r: ns['papel_classif'](r['Classif'], r['Fluxo']), axis=1)
    base['Efeito dashboard'] = base.apply(efeito_dashboard, axis=1)
    def chave(grupo, cat):
        return grupo + ' | ' + norm(cat)
    def bucket_dashboard(r):
        g, c = r['Grupo'], r['Categoria']
        if g in ('Adiantamentos', 'Borderô'):
            return g
        if g == 'Receita' and norm(r['Classif']) in ('convenio', 'convenios'):
            return 'Receita | convenios'
        return chave(g, c)
    base['Destino'] = base.apply(bucket_dashboard, axis=1)
    from modules.ajustes_fcx import carregar_ajustes, linhas_dashboard
    ledger = carregar_ajustes(retrato)
    ajustes = linhas_dashboard(ledger)
    if not ajustes.empty:
        base = pd.concat([base, ajustes], ignore_index=True)
    raw = retrato.read('FCx_Extrato')
    if raw.shape[1] < 14:
        raise ValueError('FCx_Extrato precisa das colunas A:N, conforme estrutura validada.')
    extrato = pd.DataFrame({
        'Linha Sheets': range(2, len(raw) + 2), 'Banco': raw.iloc[:, 0],
        'Seq': raw.iloc[:, 1], 'Data': raw.iloc[:, 2].map(data),
        'Transação': raw.iloc[:, 7].fillna('').astype(str),
        'Classificação extrato': raw.iloc[:, 8].fillna('').astype(str),
        'Categoria extrato': raw.iloc[:, 9].fillna('').astype(str),
        'Valor extrato': raw.iloc[:, 10].map(numero),
        'Ação': raw.iloc[:, 11].fillna('').astype(str).str.strip().str.upper(),
        'Estornado': raw.iloc[:, 13].fillna('').astype(str),
    })
    extrato = extrato[extrato['Transação'].str.strip().ne('')].copy()
    extrato['Ref'] = extrato['Data'].dt.to_period('M').dt.to_timestamp()
    extrato['Chave'] = extrato['Transação'].map(norm)
    extrato['Efeito extrato'] = extrato['Valor extrato'] * extrato['Ação'].map({'D': 1, 'C': -1})
    if extrato['Efeito extrato'].isna().any():
        avisos.append('Há ações desconhecidas: sem efeito calculável, não considerar o mês conciliado.')
    if extrato['Data'].isna().any():
        avisos.append('Há datas inválidas: os registros aparecem nas pendências e não entram na soma mensal.')
    if extrato['Estornado'].str.strip().ne('').any():
        avisos.append('Campo Estornado preenchido: efeitos mantidos conforme relatório, revisar registros antes de excluir.')
    seq_validas = extrato['Seq'].notna() & extrato['Seq'].astype(str).str.strip().ne('')
    repetidas = extrato.loc[seq_validas].duplicated(['Banco', 'Seq'], keep=False)
    if repetidas.any():
        avisos.append(f'{int(repetidas.sum())} registros repetem Banco + Seq. Não foram removidos automaticamente; conferir a origem.')
    bancos_originais = set(extrato['Banco'].dropna().astype(str))
    if not bancos_originais:
        avisos.append('Extrato sem identificação de bancos; universo de contas não validado.')
    despesas = retrato.read('Base_Despesas')
    lookup = {}
    rastreio = []
    for _, r in despesas.iterrows():
        if len(r) <= 5 or ns['normalizar'](r.iloc[3]) not in ns['TRANSACOES_DESPESAS']:
            continue
        if ns['eh_linha_devolucao'](r.iloc[4]):
            continue
        dt, valor = data(r.iloc[1]), numero(r.iloc[5])
        if pd.isna(dt) or abs(valor) <= .005:
            continue
        lookup.setdefault(norm(r.iloc[2]), set()).add(str(r.iloc[4]))
        classificacao, fluxo, _ = ns['aplicar_classificacao'](r.iloc[4], mapa)
        item = {'Ref': pd.Timestamp(dt.year, dt.month, 1), 'Categoria': str(r.iloc[4]),
                'Valor': valor, 'Tipo': 'Saída', 'Grupo': 'Despesas',
                'Classif': classificacao, 'Fluxo': fluxo,
                'Papel': ns['papel_classif'](classificacao, fluxo),
                'Destino': chave('Despesas', r.iloc[2])}
        item['Efeito dashboard'] = efeito_dashboard(item)
        rastreio.append(item)
    rastreio = pd.DataFrame(rastreio)
    if not rastreio.empty:
        esperado = base.loc[base['Grupo'] == 'Despesas'].groupby('Ref')['Efeito dashboard'].sum()
        refeito = rastreio.groupby('Ref')['Efeito dashboard'].sum()
        delta = esperado.subtract(refeito, fill_value=0)
        if (delta.abs() > .01).any():
            raise ValueError('O rastreio de Base_Despesas não reproduziu o dashboard. Atualize o motor para as novas regras.')
        base = pd.concat([base[base['Grupo'] != 'Despesas'], rastreio], ignore_index=True)
    receita_cats = {norm(c): c for c in base.loc[base['Grupo'] == 'Receita', 'Categoria'].unique()}
    devol_cats = {norm(c): c for c in base.loc[base['Grupo'] == 'Devolução Adiantamento', 'Categoria'].unique()}
    def destino(r):
        n, c = r['Chave'], norm(r['Categoria extrato'])
        if n == norm('Adiantamento Fornecedores - BANCO'):
            return 'Adiantamentos', 'Agregado por conta contábil; validar o conjunto'
        if n == norm('Bx Borderô - BANCO'):
            return 'Borderô', 'Agregado por conta contábil; validar o conjunto'
        if n in devol_cats:
            return chave('Devolução Adiantamento', devol_cats[n]), 'Correspondência de transação'
        if n == norm('Devolução Conta Paciente - Banco') and norm('Devolução Adiantamento Conta Paciente - Banco') in devol_cats:
            return chave('Devolução Adiantamento', 'Devolução Adiantamento Conta Paciente - Banco'), 'Alias de devolução de paciente; conferir origem'
        if n in lookup:
            return chave('Despesas', r['Transação']), 'Rastreado pela transação original em Base_Despesas'
        if n in receita_cats:
            return chave('Receita', receita_cats[n]), 'Correspondência de transação'
        if c in ('convenio', 'convenios'):
            return 'Receita | convenios', 'Agregado por convênio; validar o conjunto'
        if c in ('particular banco', 'particular cartao', 'particular judicial'):
            label = {'particular banco': 'Particular - Banco', 'particular cartao': 'Particular - Cartão', 'particular judicial': 'Particular - Judicial'}[c]
            return chave('Receita', label), 'Agregado particular; validar o conjunto'
        if n.startswith('transferencia entre bancos'):
            return 'Sem vínculo | transferências internas (entradas e saídas)', 'Par interno: validar saldo líquido e universo de contas; não incluir valor bruto automaticamente'
        if n.startswith('aplicacao financeira banco') or n.startswith('resgate aplicacao financeira'):
            return 'Sem vínculo | aplicações e resgates (entradas e saídas)', 'Par interno: validar saldo líquido e universo de contas; não incluir valor bruto automaticamente'
        return 'Sem vínculo | ' + n, 'Não identificado nas fontes consumidas pelo dashboard' 
    destinos = extrato.apply(destino, axis=1)
    extrato['Destino'] = destinos.map(lambda x: x[0])
    extrato['Evidência'] = destinos.map(lambda x: x[1])
    mensal_tx = extrato.groupby(['Ref', 'Chave', 'Transação', 'Destino', 'Evidência'], dropna=False).agg(
        Valor_extrato=('Valor extrato', 'sum'), Efeito_extrato=('Efeito extrato', 'sum'), Registros=('Seq', 'size')).reset_index()
    quant_tx = extrato.groupby('Destino')['Chave'].nunique()
    valores_dashboard = base.groupby(['Ref', 'Destino'])['Efeito dashboard'].sum()
    mensal_tx['Transações no conjunto'] = mensal_tx['Destino'].map(quant_tx)
    mensal_tx['Efeito dashboard no conjunto'] = mensal_tx.apply(lambda r: float(valores_dashboard.get((r['Ref'], r['Destino']), 0)), axis=1)
    mensal_tx['Efeito dashboard individual'] = mensal_tx['Efeito dashboard no conjunto'].where(mensal_tx['Transações no conjunto'] == 1)
    mensal_tx['Diferença individual'] = mensal_tx['Efeito dashboard individual'] - mensal_tx['Efeito_extrato']
    mensal_tx['Nível de validação'] = mensal_tx['Transações no conjunto'].map(lambda n: 'Individual por transação' if n == 1 else 'Agregado: não há identificação individual na fonte complementar')
    # Confere a dinâmica independentemente da ação: a SUM da coluna K não é saldo líquido.
    dinamica = retrato.read('Transações_FCx')
    dinamica = pd.DataFrame({'Transação': dinamica.iloc[:, 0].fillna('').astype(str),
                            'Valor dinâmica': dinamica.iloc[:, 1].map(numero)})
    dinamica['Chave'] = dinamica['Transação'].map(norm)
    dinamica = dinamica[~dinamica['Chave'].isin(('', 'total', 'total geral'))]
    consolidado = dinamica.groupby('Chave', as_index=False).agg({'Transação': 'first', 'Valor dinâmica': 'sum'})
    origem = extrato.groupby('Chave', as_index=False).agg({'Transação': 'first', 'Valor extrato': 'sum', 'Efeito extrato': 'sum'})
    transacoes = consolidado.merge(origem, on='Chave', how='outer', suffixes=('', ' origem'))
    transacoes['Transação'] = transacoes['Transação'].fillna(transacoes['Transação origem'])
    transacoes['Presente dinâmica'] = transacoes['Valor dinâmica'].notna()
    transacoes['Presente extrato'] = transacoes['Valor extrato'].notna()
    transacoes['Diferença dinâmica'] = transacoes['Valor dinâmica'].fillna(0) - transacoes['Valor extrato'].fillna(0)
    rotas = extrato.groupby('Chave').agg({'Destino': lambda x: '; '.join(sorted(set(x))), 'Evidência': lambda x: '; '.join(sorted(set(x)))})
    transacoes = transacoes.merge(rotas, on='Chave', how='left')
    transacoes['Status dinâmica'] = transacoes.apply(lambda r: 'Confere' if r['Presente dinâmica'] and r['Presente extrato'] and abs(r['Diferença dinâmica']) < .01 else 'Divergente / ausente', axis=1)
    a = base.groupby(['Ref', 'Destino'])['Efeito dashboard'].sum()
    e = extrato.groupby(['Ref', 'Destino'])['Efeito extrato'].sum()
    cobertura = pd.concat([a, e], axis=1).fillna(0).reset_index()
    cobertura['Impacto na diferença'] = cobertura['Efeito dashboard'] - cobertura['Efeito extrato']
    cobertura['Status'] = cobertura.apply(lambda r: 'Sem vínculo no dashboard' if r['Destino'].startswith('Sem vínculo') else ('Confere agregado' if abs(r['Impacto na diferença']) < .01 else 'Divergência no agregado'), axis=1)
    i, f, avis_tasy = ns['carregar_saldos_tasy']()
    avisos.extend(avis_tasy)
    refs = sorted(set(base['Ref']) | set(extrato['Ref'].dropna()) | set(i) | set(f))
    mensal = pd.DataFrame(index=pd.DatetimeIndex(refs, name='Ref'))
    mensal['Saldo inicial Tasy'] = pd.Series(i)
    mensal['Saldo final Tasy'] = pd.Series(f)
    mensal['Movimento Tasy'] = mensal['Saldo final Tasy'] - mensal['Saldo inicial Tasy']
    mensal['Movimento dashboard'] = base.groupby('Ref')['Efeito dashboard'].sum()
    mensal['Movimento extrato'] = extrato.groupby('Ref')['Efeito extrato'].sum()
    mensal['Diferença dashboard − Tasy'] = mensal['Movimento dashboard'] - mensal['Movimento Tasy']
    mensal['Explicado: dashboard − extrato'] = mensal['Movimento dashboard'] - mensal['Movimento extrato']
    mensal['Residual: extrato − Tasy'] = mensal['Movimento extrato'] - mensal['Movimento Tasy']
    mensal['Teste da ponte'] = mensal['Diferença dashboard − Tasy'] - mensal['Explicado: dashboard − extrato'] - mensal['Residual: extrato − Tasy']
    mensal['Mês com dashboard'] = mensal['Movimento dashboard'].notna()
    for ref in refs:
        anterior = ref - pd.offsets.MonthBegin(1)
        if ref in i and anterior in f and abs(i[ref] - f[anterior]) > .01:
            avisos.append(f'Tasy: abertura de {ref:%m/%Y} difere do fechamento anterior em {i[ref] - f[anterior]:.2f}.')
    transacoes['Cobertura dashboard'] = transacoes['Destino'].fillna('').map(lambda d: 'Sem vínculo identificado' if d.startswith('Sem vínculo') or not d else 'Comparar agregado mensal (sem rateio por transação)')
    return dict(mensal=mensal.reset_index(), transacoes=transacoes, cobertura=cobertura,
                extrato=extrato, dashboard=base, mensal_transacoes=mensal_tx, ajustes=ledger, avisos=avisos)
