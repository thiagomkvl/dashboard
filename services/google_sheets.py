import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client
from datetime import datetime

def obter_config_gsheets():
    """Recupera as credenciais e a URL/ID da planilha dos Secrets."""
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        conf = dict(st.secrets["connections"]["gsheets"])
        spreadsheet_ref = conf.get("spreadsheet")
    elif "gcp_service_account" in st.secrets:
        conf = dict(st.secrets["gcp_service_account"])
        spreadsheet_ref = st.secrets.get("SPREADSHEET_ID")
    else:
        st.error("⚠️ Configuração do Google Sheets não encontrada nos Secrets!")
        st.stop()

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
        st.error("⚠️ URL ou ID da planilha não encontrado!")
        st.stop()
    try:
        client = Client(config=creds_dict)
        return Spread(ref_final, client=client)
    except Exception:
        return Spread(ref_final, config=creds_dict)

@st.cache_data(ttl=120)
def carregar_dados_sheets(spreadsheet_ref: str = None):
    """Carrega todas as abas necessárias para a conciliação."""
    try:
        spread = obter_spread(spreadsheet_ref)
        
        df_bancos = spread.sheet_to_df(sheet='Extratos_Bancos', index=None)
        df_tasy = spread.sheet_to_df(sheet='Base_Tasy', index=None)
        
        # Abas de controle (se não existirem, retornam dataframes vazios)
        try: df_matriz = spread.sheet_to_df(sheet='Matriz_Conciliacao', index=None)
        except: df_matriz = pd.DataFrame()
        
        try: df_config = spread.sheet_to_df(sheet='Configuracoes', index=None)
        except: df_config = pd.DataFrame(columns=['Chave', 'Valor'])
        
        try: df_fechados = spread.sheet_to_df(sheet='Fechamentos', index=None)
        except: df_fechados = pd.DataFrame(columns=['Mes_Ano', 'Data_Fechamento'])

        # Restaurar strings separadas por vírgula para listas na leitura da matriz
        if not df_matriz.empty and 'tasy_ids' in df_matriz.columns:
            df_matriz['tasy_ids'] = df_matriz['tasy_ids'].apply(lambda x: str(x).split(',') if pd.notna(x) and str(x).strip() else [])

        return df_bancos, df_tasy, df_matriz, df_config, df_fechados
    except Exception as e:
        st.error(f"⚠️ Erro ao ler as abas na planilha: {e}")
        st.stop()

def salvar_regras_sheets(transacoes: list, spreadsheet_ref: str = None):
    """Grava as regras de transação selecionadas de forma persistente."""
    try:
        spread = obter_spread(spreadsheet_ref)
        df_regras = pd.DataFrame([{'Chave': 'tipos_transacao', 'Valor': ",".join(transacoes)}])
        spread.df_to_sheet(df_regras, sheet='Configuracoes', index=False, replace=True)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"⚠️ Erro ao salvar regras: {e}")
        return False

def fechar_periodo_sheets(mes_ano: str, df_matriz_mes: pd.DataFrame, df_matriz_full: pd.DataFrame, df_fechados: pd.DataFrame, spreadsheet_ref: str = None):
    """Sela a conciliação gravando os resultados finais e marcando o período como fechado."""
    try:
        spread = obter_spread(spreadsheet_ref)
        
        # 1. Atualizar Matriz Completa (Remove dados anteriores do mesmo mês para evitar duplicidade)
        if not df_matriz_full.empty and 'data_recebimento' in df_matriz_full.columns:
            df_matriz_full['tmp_mes'] = pd.to_datetime(df_matriz_full['data_recebimento']).dt.strftime('%m/%Y')
            df_matriz_full = df_matriz_full[df_matriz_full['tmp_mes'] != mes_ano].drop(columns=['tmp_mes'])

        df_gravar = pd.concat([df_matriz_full, df_matriz_mes], ignore_index=True)
        if 'tasy_ids' in df_gravar.columns:
            df_gravar['tasy_ids'] = df_gravar['tasy_ids'].apply(lambda x: ",".join(x) if isinstance(x, list) else str(x))
        
        spread.df_to_sheet(df_gravar, sheet='Matriz_Conciliacao', index=False, replace=True)

        # 2. Registrar Fechamento
        novo_fechamento = pd.DataFrame([{'Mes_Ano': mes_ano, 'Data_Fechamento': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])
        df_fechados_novo = pd.concat([df_fechados, novo_fechamento], ignore_index=True)
        spread.df_to_sheet(df_fechados_novo, sheet='Fechamentos', index=False, replace=True)
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"⚠️ Erro ao gravar fechamento: {e}")
        return False
