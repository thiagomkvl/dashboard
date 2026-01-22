import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit as st
from datetime import datetime

def conectar_sheets():
    """Função para estabelecer a conexão com o Google Sheets"""
    return st.connection("gsheets", type=GSheetsConnection)

def salvar_no_historico(df_novo):
    """
    Recebe o DataFrame do upload, limpa os espaços, 
    adiciona a data atual e apensa ao histórico no Google Sheets.
    """
    try:
        # Conecta ao Google Sheets usando as configurações dos Secrets
        conn = conectar_sheets()
        
        # 1. Limpeza de espaços (Strings)
        df_novo = df_novo.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
        # 2. Adiciona a data de hoje na coluna data_processamento
        df_novo['data_processamento'] = datetime.now().strftime('%d/%m/%Y')
        
        # 3. Lê o histórico existente (ttl=0 para evitar cache na hora de gravar)
        df_antigo = conn.read(worksheet="Historico", ttl=0)
        
        # 4. Empilha os novos dados
        df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
        
        # 5. Atualiza a planilha no Google
        conn.update(worksheet="Historico", data=df_final)
        return True
    
    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        return False
