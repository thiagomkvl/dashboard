import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit as st
from datetime import datetime

def conectar_sheets():
    """Estabelece a conexão com o Google Sheets."""
    return st.connection("gsheets", type=GSheetsConnection)

def salvar_no_historico(df_novo):
    """
    Limpa os dados, adiciona data e anexa ao histórico no Google Sheets.
    """
    try:
        conn = conectar_sheets()
        
        # Limpeza de espaços inicial/final
        df_novo = df_novo.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
        # Carimbo da data de processamento
        df_novo['data_processamento'] = datetime.now().strftime('%d/%m/%Y')
        
        # Lê o histórico atual (ttl=0 para evitar dados antigos em cache)
        df_antigo = conn.read(worksheet="Historico", ttl=0)
        
        # Empilha os novos dados abaixo dos antigos
        df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
        
        # Sobrescreve a aba Historico com a lista atualizada
        conn.update(worksheet="Historico", data=df_final)
        return True
    
    except Exception as e:
        st.error(f"Erro ao salvar no Google Sheets: {e}")
        return False
