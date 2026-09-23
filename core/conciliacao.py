import itertools
import pandas as pd
from datetime import datetime

def executar_conciliacao(
    df_rec: pd.DataFrame, 
    df_tasy: pd.DataFrame, 
    tolerancia: float = 0.01, 
    max_combinacao: int = 5
) -> pd.DataFrame:
    """Motor central de regras de conciliação."""
    matriz_resultados = []
    tasy_utilizados = set()
    
    mapa_tasy_chave = df_tasy.set_index('chave_conciliacao').to_dict('index')
    rec_pendentes = []
    
    # 1. Busca por Correspondência 1:1
    for _, rec in df_rec.iterrows():
        chave = rec['chave_conciliacao']
        
        if chave in mapa_tasy_chave and mapa_tasy_chave[chave]['tasy_id'] not in tasy_utilizados:
            tasy_match = mapa_tasy_chave[chave]
            tasy_utilizados.add(tasy_match['tasy_id'])
            
            matriz_resultados.append({
                'conciliacao_id': f"CONC-{rec['recebimento_id']}",
                'recebimento_id': rec['recebimento_id'],
                'data_recebimento': rec['data'].strftime('%Y-%m-%d'),
                'banco': rec['banco'],
                'valor_recebimento': rec['valor'],
                'tasy_ids': [tasy_match['tasy_id']],
                'quantidade_tasy': 1,
                'valor_tasy': tasy_match['valor'],
                'valor_conciliado': rec['valor'],
                'diferenca': 0.0,
                'tipo_conciliacao': '1:1',
                'status': 'CONCILIADO',
                'motivo': 'Correspondência exata (1:1)',
                'data_conciliacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            rec_pendentes.append(rec)
            
    # 2. Busca por Combinações 1:N no mesmo Banco + Data
    tasy_livres = df_tasy[~df_tasy['tasy_id'].isin(tasy_utilizados)].copy()
    
    for rec in rec_pendentes:
        banco_rec = rec['banco']
        data_rec = rec['data']
        valor_rec = rec['valor']
        
        candidatos = tasy_livres[
            (tasy_livres['banco'] == banco_rec) & 
            (tasy_livres['data'] == data_rec) & 
            (~tasy_livres['tasy_id'].isin(tasy_utilizados))
        ].to_dict('records')
        
        conciliado_1_n = False
        
        for k in range(2, max_combinacao + 1):
            if conciliado_1_n or len(candidatos) < k:
                break
                
            for comb in itertools.combinations(candidatos, k):
                if any(c['tasy_id'] in tasy_utilizados for c in comb):
                    continue
                    
                soma_comb = round(sum(c['valor'] for c in comb), 2)
                
                if abs(soma_comb - valor_rec) <= tolerancia:
                    ids_comb = [c['tasy_id'] for c in comb]
                    tasy_utilizados.update(ids_comb)
                    
                    matriz_resultados.append({
                        'conciliacao_id': f"CONC-{rec['recebimento_id']}",
                        'recebimento_id': rec['recebimento_id'],
                        'data_recebimento': rec['data'].strftime('%Y-%m-%d'),
                        'banco': rec['banco'],
                        'valor_recebimento': valor_rec,
                        'tasy_ids': ids_comb,
                        'quantidade_tasy': k,
                        'valor_tasy': soma_comb,
                        'valor_conciliado': valor_rec,
                        'diferenca': round(valor_rec - soma_comb, 2),
                        'tipo_conciliacao': f'1:{k}',
                        'status': 'CONCILIADO',
                        'motivo': f'Combinação 1:{k} no mesmo Banco e Data',
                        'data_conciliacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    conciliado_1_n = True
                    break
        
        if conciliado_1_n:
            continue
            
        # 3. Conciliação Parcial ou Pendente
        soma_candidatos = round(sum(c['valor'] for c in candidatos if c['tasy_id'] not in tasy_utilizados), 2)
        
        if 0 < soma_candidatos < valor_rec:
            ids_parciais = [c['tasy_id'] for c in candidatos if c['tasy_id'] not in tasy_utilizados]
            tasy_utilizados.update(ids_parciais)
            
            matriz_resultados.append({
                'conciliacao_id': f"CONC-{rec['recebimento_id']}",
                'recebimento_id': rec['recebimento_id'],
                'data_recebimento': rec['data'].strftime('%Y-%m-%d'),
                'banco': rec['banco'],
                'valor_recebimento': valor_rec,
                'tasy_ids': ids_parciais,
                'quantidade_tasy': len(ids_parciais),
                'valor_tasy': soma_candidatos,
                'valor_conciliado': soma_candidatos,
                'diferenca': round(valor_rec - soma_candidatos, 2),
                'tipo_conciliacao': 'PARCIAL',
                'status': 'PARCIAL',
                'motivo': 'Créditos cobrem apenas parte do valor esperado',
                'data_conciliacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            matriz_resultados.append({
                'conciliacao_id': f"CONC-{rec['recebimento_id']}",
                'recebimento_id': rec['recebimento_id'],
                'data_recebimento': rec['data'].strftime('%Y-%m-%d'),
                'banco': rec['banco'],
                'valor_recebimento': valor_rec,
                'tasy_ids': [],
                'quantidade_tasy': 0,
                'valor_tasy': 0.0,
                'valor_conciliado': 0.0,
                'diferenca': valor_rec,
                'tipo_conciliacao': 'NÃO ENCONTRADO',
                'status': 'PENDENTE',
                'motivo': 'Nenhum crédito localizado na Base_Tasy',
                'data_conciliacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    return pd.DataFrame(matriz_resultados)
