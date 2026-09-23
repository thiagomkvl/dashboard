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

    # Chaves da Service Account aceitas pelo gspread / gspread_pandas
    sa_keys = [
        "type", "project_id", "private_key_id", "private_key",
        "client_email", "client_id", "auth_uri", "token_uri",
        "auth_provider_x509_cert_url", "client_x509_cert_url"
    ]
    creds_dict = {k: conf[k] for k in sa_keys if k in conf}
    
    return creds_dict, spreadsheet_ref

def obter_spread(spreadsheet_ref: str = None):
    """Instancia a classe Spread da biblioteca gspread_pandas com as credenciais."""
    creds_dict, ref_secret = obter_config_gsheets()
    ref_final = spreadsheet_ref or ref_secret

    if not ref_final:
        st.error("⚠️ URL ou ID da planilha não encontrado nos Secrets!")
        st.stop()

    try:
        # No gspread_pandas, o dicionário é passado via parâmetro config
        client = Client(config=creds_dict)
        return Spread(ref_final, client=client)
    except Exception as e:
        try:
            # Fallback passando o config diretamente para a Spread
            return Spread(ref_final, config=creds_dict)
        except Exception as ex:
            st.error(f"⚠️ Erro ao conectar ao Google Sheets: {e}")
            st.stop()

@st.cache_data(ttl=120)
def carregar_dados_sheets(spreadsheet_ref: str = None):
    """Carrega as abas Extratos_Bancos e Base_Tasy."""
    try:
        spread = obter_spread(spreadsheet_ref)
        
        df_bancos = spread.sheet_to_df(sheet='Extratos_Bancos', index=None)
        df_tasy = spread.sheet_to_df(sheet='Base_Tasy', index=None)
        
        return df_bancos, df_tasy
    except Exception as e:
        st.error(f"⚠️ Erro ao ler as abas 'Extratos_Bancos' ou 'Base_Tasy' na planilha: {e}")
        st.stop()

def salvar_matriz_sheets(df_matriz: pd.DataFrame, spreadsheet_ref: str = None):
    """Grava o resultado da conciliação na aba Matriz_Conciliacao."""
    try:
        spread = obter_spread(spreadsheet_ref)
        
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
