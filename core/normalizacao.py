import pandas as pd
import hashlib
import unicodedata

def normalizar_texto_chave(txt) -> str:
    """Remove acentos, converte para minúsculas e remove espaços extras."""
    if pd.isna(txt) or txt is None:
        return ""
    return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()

def limpar_valor_monetario(valor) -> float:
    """Converte números ou strings monetárias (R$ 1.500,00 ou 1500.00) para float."""
    if pd.isna(valor) or valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    v_str = str(valor).strip().replace('R$', '').replace(' ', '')
    if not v_str or v_str in ['-', 'nan', 'None']:
        return 0.0
    if '.' in v_str and ',' in v_str:
        v_str = v_str.replace('.', '').replace(',', '.')
    elif ',' in v_str:
        v_str = v_str.replace(',', '.')
    try:
        return float(v_str)
    except ValueError:
        return 0.0

def encontrar_coluna(df: pd.DataFrame, palavras_chave: list, idx_fallback: int = 0) -> str:
    """Localiza o nome real da coluna no DataFrame ignorando maiúsculas, espaços e acentos."""
    cols_originais = [str(c).strip() for c in df.columns]
    df.columns = cols_originais
    cols_norm = {normalizar_texto_chave(c): c for c in cols_originais}
    
    # 1. Busca por correspondência exata normalizada
    for kw in palavras_chave:
        kw_norm = normalizar_texto_chave(kw)
        if kw_norm in cols_norm:
            return cols_norm[kw_norm]
            
    # 2. Busca por sub-string
    for kw in palavras_chave:
        kw_norm = normalizar_texto_chave(kw)
        for c_norm, c_orig in cols_norm.items():
            if kw_norm in c_norm:
                return c_orig
                
    # 3. Fallback para o índice da coluna
    if 0 <= idx_fallback < len(df.columns):
        return df.columns[idx_fallback]
    return df.columns[0]

def gerar_hash_linha(row: pd.Series, prefixo: str) -> str:
    """Gera ID único imutável para a linha."""
    banco_str = str(row.get('banco', ''))
    data_str = row['data'].strftime('%Y%m%d') if pd.notna(row.get('data')) else '00000000'
    val_float = float(row.get('valor', 0.0))
    desc_str = str(row.get('descricao', ''))
    
    string_base = f"{prefixo}_{banco_str}_{data_str}_{val_float:.2f}_{desc_str}"
    return hashlib.sha256(string_base.encode('utf-8')).hexdigest()[:16]

def normalizar_recebimentos(df_bancos: pd.DataFrame) -> pd.DataFrame:
    """Trata e normaliza a aba Extratos_Bancos."""
    if df_bancos is None or df_bancos.empty:
        return pd.DataFrame(columns=['data', 'banco', 'valor', 'descricao', 'recebimento_id', 'ocorrencia', 'chave_conciliacao'])
        
    df = df_bancos.copy()

    # Mapeamento com prioridade exata para as colunas da aba Extratos_Bancos
    col_data = encontrar_coluna(df, ['data', 'dt_movimento'], idx_fallback=1)
    col_banco = encontrar_coluna(df, ['banco', 'banco/agencia/conta'], idx_fallback=0)
    # Busca 'vl crédito' primeiro para pegar exclusivamente os recebimentos da aba
    col_valor = encontrar_coluna(df, ['vl credito', 'vl_credito', 'valor', 'credito', 'entradas'], idx_fallback=5)
    col_desc = encontrar_coluna(df, ['lancamento', 'transacao', 'historico', 'descricao'], idx_fallback=2)

    df['data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
    df['banco'] = df[col_banco].astype(str).str.strip()
    df['valor'] = df[col_valor].apply(limpar_valor_monetario).round(2)
    df['descricao'] = df[col_desc].astype(str).str.strip() if col_desc in df.columns else ""

    # Filtra apenas os créditos válidos (> 0) e com data válida
    df = df[(df['valor'] > 0) & (df['data'].notna())].copy()
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
    if df_tasy is None or df_tasy.empty:
        return pd.DataFrame(columns=['data', 'banco', 'valor', 'descricao', 'tasy_id', 'ocorrencia', 'chave_conciliacao'])

    df = df_tasy.copy()

    col_banco = encontrar_coluna(df, ['banco/agencia/conta', 'banco', 'conta'], idx_fallback=0)
    col_data = encontrar_coluna(df, ['data', 'dt_movimento'], idx_fallback=1)
    col_valor = encontrar_coluna(df, ['vl credito', 'vl_credito', 'valor', 'credito'], idx_fallback=4)
    col_desc = encontrar_coluna(df, ['transacao', 'lancamento', 'historico', 'descricao'], idx_fallback=2)

    df['data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
    df['banco'] = df[col_banco].astype(str).str.strip()
    df['valor'] = df[col_valor].apply(limpar_valor_monetario).round(2)
    df['descricao'] = df[col_desc].astype(str).str.strip() if col_desc in df.columns else ""

    df = df[(df['valor'] > 0) & (df['data'].notna())].copy()
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
