import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit as st
from datetime import datetime

def salvar_no_historico(df_novo):
    """
    Recebe o DataFrame do upload, limpa os espaços, 
    adiciona a data atual e apensa ao histórico no Google Sheets.
    """
    try:
        # Conecta ao Google Sheets usando as configurações dos Secrets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Limpeza de espaços (Strings)
        # Remove espaços no início e fim de todas as células de texto
        df_novo = df_novo.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
        # 2. Adiciona a data de hoje na coluna data_processamento
        # Isso garante que cada linha saiba quando foi inserida
        df_novo['data_processamento'] = datetime.now().strftime('%d/%m/%Y')
        
        # 3. Lê o histórico existente
        # O ttl=0 garante que ele pegue a versão mais recente, sem cache
        df_antigo = conn.read(worksheet="Historico", ttl=0)
        
        # 4. Empilha os novos dados
        # Certifique-se de que os nomes das colunas são IDÊNTICOS
        df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
        
        # 5. Atualiza a planilha no Google
        conn.update(worksheet="Historico", data=df_final)
        return True
    
    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        return False
