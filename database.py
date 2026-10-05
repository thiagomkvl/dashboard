import streamlit as st
from streamlit_gsheets import GSheetsConnection

def conectar_sheets():

    """
    try:
        # Inicializa o conector usando o bloco [connections.gsheets] do Secrets
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"⚠️ Erro ao conectar ao Google Sheets. Verifique o secrets.toml no Streamlit. Detalhe: {e}")
        return None
