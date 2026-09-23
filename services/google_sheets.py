import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client

def obter_config_gsheets():
    """Recupera as credenciais e a URL/ID da planilha dos Secrets."""
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        conf = dict(st.secrets["connections"]["gsheets"])
        spreadsheet_ref = conf.get("spreadsheet")
    elif "gcp_service_account" in st.secrets:
        conf = dict(st.secrets["gcp_service_account"])
        spreadsheet_ref = st.secrets.get("SPREADSHEET_ID")
    else:
        st.error(
            "⚠️ **Configuração do Google Sheets não encontrada nos Secrets!**\n\n"
            "Certifique-se de que o bloco `[connections.gsheets]` está presente no `secrets.toml`."
        )
        st.stop()

    # Filtra apenas as chaves da Service Account aceitas pelo gspread
    sa_keys = [
        "type", "project_id", "private_key_id", "private_key",
        "client_email", "client_id", "auth_uri", "token_uri",
        "auth_provider_x509_cert_url", "client_x509_cert_url"
    ]
    creds_dict = {k: conf[k] for k in sa_keys if k in conf}
    
    return creds_dict, spreadsheet_ref

def obter_cliente_gsheets():
    """Autentica o cliente gspread com base nas credenciais salvas."""
    try:
        creds_dict, _ = obter_config_gsheets()
        return Client.from_json_dict(creds_dict)
    except Exception as e:
        st.error(f"⚠️ Erro ao autenticar no Google Sheets: {e}")
        st.stop()

@st.cache_data(ttl=120)
def carregar_dados_sheets(spreadsheet_ref: str = None):
    """Carrega as abas Extratos_Bancos e Base_Tasy."""
    creds_dict, ref_secret = obter_config_gsheets()
    ref_final = spreadsheet_ref or ref_secret

    if not ref_final:
        st.error("⚠️ URL ou ID da planilha não encontrado nos Secrets!")
        st.stop()

    try:
        c = Client.from_json_dict(creds_dict)
        spread = Spread(ref_final, client=c)
        
        df_bancos = spread.sheet_to_df(sheet='Extratos_Bancos', index=None)
        df_tasy = spread.sheet_to_df(sheet='Base_Tasy', index=None)
        
        return df_bancos, df_tasy
    except Exception as e:
        st.error(f"⚠️ Erro ao ler as abas 'Extratos_Bancos' ou 'Base_Tasy' na planilha: {e}")
        st.stop()

def salvar_matriz_sheets(df_matriz: pd.DataFrame, spreadsheet_ref: str = None):
    """Grava o resultado da conciliação na aba Matriz_Conciliacao."""
    try:
        creds_dict, ref_secret = obter_config_gsheets()
        ref_final = spreadsheet_ref or ref_secret

        c = Client.from_json_dict(creds_dict)
        spread = Spread(ref_final, client=c)
        
        df_gravar = df_matriz.copy()
        if 'tasy_ids' in df_gravar.columns:
            df_gravar['tasy_ids'] = df_gravar['tasy_ids'].apply(
                lambda x: ",".join(x) if isinstance(x, list) else str(x)
            )
        
        spread.df_to_sheet(df_gravar, sheet='Matriz_Conciliacao', index=False, replace=True)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"⚠️ Erro ao salvar na aba 'Matriz_Conciliacao': {e}")
        return False
