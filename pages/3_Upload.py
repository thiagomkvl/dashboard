import streamlit as st
import pandas as pd
from database import salvar_no_historico

st.set_page_config(page_title="Upload", layout="wide", page_icon="📂")

# --- BLOQUEIO DE SEGURANÇA ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Por favor, faça login na página inicial.")
    st.stop()

# --- CÓDIGO DE UPLOAD ---
st.title("📂 Upload de Base")
st.info("Utilize esta tela para atualizar o histórico financeiro.")

up = st.file_uploader("Arquivo Excel (.xlsx)", type=["xlsx"])
if up and st.button("Processar Arquivo"):
    with st.spinner("Processando..."):
        if salvar_no_historico(pd.read_excel(up)):
            st.success("✅ Base atualizada!")
