import streamlit as st
from streamlit_gsheets import GSheetsConnection

def conectar_sheets():
    """
    Conecta ao Google Sheets utilizando as credenciais salvas no Streamlit (secrets.toml).
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"⚠️ Erro ao conectar ao Google Sheets: {e}")
        return None
