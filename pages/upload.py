import streamlit as st
import pandas as pd
from database import salvar_no_historico

# --- BLOQUEIO DE SEGURANÇA ---
if not st.session_state.get("password_correct"):
    st.warning("🔒 Acesso restrito. Faça login.")
    st.stop()

st.title("📂 Upload de Base")
st.info("Utilize esta tela para atualizar o histórico financeiro.")

up = st.file_uploader("Arquivo Excel (.xlsx)", type=["xlsx"])

if up:
    if st.button("Processar Arquivo"):
        with st.spinner("Processando..."):
            try:
                df_new = pd.read_excel(up)
                if salvar_no_historico(df_new):
                    st.success("✅ Base atualizada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")
