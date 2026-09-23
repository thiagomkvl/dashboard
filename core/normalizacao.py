import pandas as pd
import hashlib

def gerar_hash_linha(row: pd.Series, prefixo: str) -> str:
    """Gera ID único imutável para a linha."""
    string_base = f"{prefixo}_{row['banco']}_{row['data'].strftime('%Y%m%d')}_{row['valor']:.2f}_{row['descricao']}"
    return hashlib.sha256(string_base.encode('utf-8')).hexdigest()[:16]

def normalizar_recebimentos(df_bancos: pd.DataFrame) -> pd.DataFrame:
    """Trata e normaliza a aba Extratos_Bancos."""
    df = df_bancos.copy()
    
    df['data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['banco'] = df['Banco'].astype(str).str.strip()
    df['valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0.0).round(2)
    df['descricao'] = df['Lançamento'].astype(str).str.strip() if 'Lançamento' in df.columns else ""
    
    df = df[df['valor'] > 0].dropna(subset=['data']).copy()
    df = df.sort_values(by=['banco', 'data', 'valor']).reset_index(drop=True)
    
    df['recebimento_id'] = df.apply(lambda r: gerar_hash_linha(r, 'REC'), axis=1)
    df['ocorrencia'] = df.groupby(['banco', df['data'].dt.strftime('%Y%m%d'), 'valor']).cumcount() + 1
    
    df['chave_conciliacao'] = (
        df['banco'] + '|' + 
        df['data'].dt.strftime('%Y%m%d') + '|' + 
        df['valor'].map('{:.2f}'.format) + '|' + 
        df['ocorrencia'].astype(str)
    )
    return df

def normalizar_tasy(df_tasy: pd.DataFrame) -> pd.DataFrame:
    """Trata e normaliza a aba Base_Tasy."""
    df = df_tasy.copy()
    
    col_banco = 'Banco/Agência/Conta' if 'Banco/Agência/Conta' in df.columns else df.columns[0]
    col_credito = 'Vl Crédito' if 'Vl Crédito' in df.columns else 'Valor'
    col_trans = 'Transação' if 'Transação' in df.columns else 'Descrição'
    
    df['data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['banco'] = df[col_banco].astype(str).str.strip()
    df['valor'] = pd.to_numeric(df[col_credito], errors='coerce').fillna(0.0).round(2)
    df['descricao'] = df[col_trans].astype(str).str.strip() if col_trans in df.columns else ""
    
    df = df[df['valor'] > 0].dropna(subset=['data']).copy()
    df = df.sort_values(by=['banco', 'data', 'valor']).reset_index(drop=True)
    
    df['tasy_id'] = df.apply(lambda r: gerar_hash_linha(r, 'TASY'), axis=1)
    df['ocorrencia'] = df.groupby(['banco', df['data'].dt.strftime('%Y%m%d'), 'valor']).cumcount() + 1
    
    df['chave_conciliacao'] = (
        df['banco'] + '|' + 
        df['data'].dt.strftime('%Y%m%d') + '|' + 
        df['valor'].map('{:.2f}'.format) + '|' + 
        df['ocorrencia'].astype(str)
    )
    return df
