import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client

def obter_cliente_gsheets():
    """Autentica via Service Account registrada no st.secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    return Client.from_json_dict(creds_dict)

@st.cache_data(ttl=300)
def carregar_dados_sheets(spreadsheet_id: str):
    """Carrega as abas Extratos_Bancos e Base_Tasy."""
    c = obter_cliente_gsheets()
    spread = Spread(spreadsheet_id, client=c)
    
    df_bancos = spread.sheet_to_df(sheet='Extratos_Bancos', index=None)
    df_tasy = spread.sheet_to_df(sheet='Base_Tasy', index=None)
    
    return df_bancos, df_tasy

def salvar_matriz_sheets(spreadsheet_id: str, df_matriz: pd.DataFrame):
    """Grava o resultado do processamento na aba Matriz_Conciliacao."""
    c = obter_cliente_gsheets()
    spread = Spread(spreadsheet_id, client=c)
    
    df_gravar = df_matriz.copy()
    df_gravar['tasy_ids'] = df_gravar['tasy_ids'].apply(
        lambda x: ",".join(x) if isinstance(x, list) else str(x)
    )
    
    spread.df_to_sheet(df_gravar, sheet='Matriz_Conciliacao', index=False, replace=True)
    st.cache_data.clear()
