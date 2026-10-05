import streamlit as st
import pandas as pd
import datetime
from database import conectar_sheets

st.set_page_config(page_title="Extrato Inteligente", page_icon="🧠", layout="wide")

# Nome da aba na sua planilha do Google Sheets que guardará tudo
WORKSHEET_NAME = "Extratos_Consolidados"

def carregar_base_historica(conn):
    """Lê os dados já salvos para criar a trava de meses importados."""
    try:
        df_hist = conn.read(worksheet=WORKSHEET_NAME, ttl=0)
        return df_hist
    except:
        # Se a aba não existir ou estiver vazia, cria um DataFrame zerado
        return pd.DataFrame(columns=["Banco", "Mes_Referencia", "Data", "Historico", "Valor", "Categoria", "Tipo_Operacao"])

def padronizar_extrato(file, banco):
    """Lê o arquivo do banco e padroniza para 3 colunas: Data, Historico, Valor"""
    try:
        if banco == "Banco do Brasil":
            # BB tem cabeçalho na linha 1
            df = pd.read_excel(file, header=1)
            df = df.dropna(subset=['Data', 'Historico'])
            # Trata valor C/D
            df['Valor R$ '] = df['Valor R$ '].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
            df['Valor'] = df.apply(lambda x: x['Valor R$ '] if x['Inf.'] == 'C' else -x['Valor R$ '], axis=1)
            df = df[['Data', 'Historico', 'Valor']]
            
        elif "Bradesco" in banco:
            # Bradesco tem cabeçalho na linha 7
            df = pd.read_excel(file, header=7)
            df = df.dropna(subset=['Data', 'Lançamento'])
            df = df[df['Lançamento'] != 'SALDO ANTERIOR']
            # Junta Crédito e Débito
            df['Crédito (R$)'] = pd.to_numeric(df['Crédito (R$)'].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
            df['Débito (R$)'] = pd.to_numeric(df['Débito (R$)'].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
            df['Valor'] = df['Crédito (R$)'] - df['Débito (R$)']
            df = df.rename(columns={'Lançamento': 'Historico'})[['Data', 'Historico', 'Valor']]
            
        elif banco == "Caixa Econômica":
            # Caixa é direto, valores já vêm negativos
            df = pd.read_excel(file)
            df = df.dropna(subset=['Data Movimento', 'Histórico'])
            df = df.rename(columns={'Data Movimento': 'Data', 'Histórico': 'Historico', 'Valor Lançamento': 'Valor'})
            df = df[['Data', 'Historico', 'Valor']]
            
        else:
            # Padrão genérico (Itaú, Santander, Unicred, Uniprime)
            # Lê tudo, acha onde está a palavra 'Data' e refaz o cabeçalho
            df_temp = pd.read_excel(file, header=None)
            header_idx = df_temp[df_temp.eq('Data').any(axis=1)].index[0]
            df = pd.read_excel(file, header=header_idx)
            # Você precisará ajustar aqui caso algum banco específico fuja do padrão Data/Historico/Valor
            col_historico = [c for c in df.columns if 'Histórico' in c or 'Lançamento' in c or 'Descrição' in c][0]
            col_valor = [c for c in df.columns if 'Valor' in c or 'Saldo' not in c and 'R$' in c][0]
            df = df.rename(columns={col_historico: 'Historico', col_valor: 'Valor'})
            df = df[['Data', 'Historico', 'Valor']]

        # Limpeza final
        df['Banco'] = banco
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        df = df.dropna(subset=['Valor'])
        return df

    except Exception as e:
        st.error(f"Erro ao ler formato do {banco}: {e}")
        return None

def classificar_lancamentos(df):
    """Aplica as regras de negócio de classificação"""
    def regra_categoria(hist):
        hist = str(hist).upper()
        # Transferências Internas
        if any(x in hist for x in ['TRANSF', 'TED', 'TEV', 'PIX ENVIADO', 'PIX RECEBIDO']):
            return 'Transferência Interna'
        # Aplicações e Resgates
        elif any(x in hist for x in ['RESGATE', 'APLICA', 'CDB', 'POUPANCA', 'FUNDO', 'COMPROMISSADA']):
            return 'Aplicações Financeiras'
        # Tarifas
        elif any(x in hist for x in ['TARIFA', 'MENSALIDADE', 'TAXA']):
            return 'Tarifas Bancárias'
        else:
            return 'Despesa/Receita Geral'

    def regra_operacional(cat):
        if cat in ['Transferência Interna', 'Aplicações Financeiras']:
            return 'Não Operacional'
        return 'Operacional'

    df['Categoria'] = df['Historico'].apply(regra_categoria)
    df['Tipo_Operacao'] = df['Categoria'].apply(regra_operacional)
    return df


# ==============================================================================
# INTERFACE DO USUÁRIO
# ==============================================================================
st.title("🧠 Extrato Inteligente")
st.markdown("Faça o upload do fechamento mensal. O sistema classificará os lançamentos e salvará na base de dados, **evitando duplicações**.")

conn = conectar_sheets()

if conn is not None:
    df_historico = carregar_base_historica(conn)
    
    col1, col2 = st.columns(2)
    with col1:
        banco_selecionado = st.selectbox("Selecione o Banco:", ["Banco do Brasil", "Bradesco", "Caixa Econômica", "Itaú", "Santander", "Unicred", "Uniprime"])
    with col2:
        mes_ref = st.text_input("Mês/Ano de Referência (Ex: 01/2026):", value="01/2026")

    # TRAVA DE SEGURANÇA
    if not df_historico.empty:
        ja_importado = df_historico[(df_historico['Banco'] == banco_selecionado) & (df_historico['Mes_Referencia'] == mes_ref)]
        if not ja_importado.empty:
            st.warning(f"⚠️ Atenção: O fechamento de **{banco_selecionado}** para **{mes_ref}** já foi importado! A importação está travada para evitar duplicidade.")
            st.stop()

    arquivo_extrato = st.file_uploader("Anexe o arquivo Excel (.xls ou .xlsx)", type=['xls', 'xlsx'])

    if arquivo_extrato is not None:
        with st.spinner("Analisando extrato..."):
            df_processado = padronizar_extrato(arquivo_extrato, banco_selecionado)
            
            if df_processado is not None:
                df_processado['Mes_Referencia'] = mes_ref
                df_processado = classificar_lancamentos(df_processado)

                st.success("Extrato processado com sucesso! Revise os dados abaixo:")
                
                # Resumo
                total_op = df_processado[df_processado['Tipo_Operacao'] == 'Operacional']['Valor'].sum()
                total_nao_op = df_processado[df_processado['Tipo_Operacao'] == 'Não Operacional']['Valor'].sum()
                
                st.write(f"**Total Operacional:** R$ {total_op:,.2f}")
                st.write(f"**Total Não Operacional:** R$ {total_nao_op:,.2f}")
                
                st.dataframe(df_processado, use_container_width=True)

                if st.button("💾 Gravar no Banco de Dados (Google Sheets)", type="primary"):
                    with st.spinner("Salvando na nuvem..."):
                        # Junta os dados novos com os dados históricos
                        if df_historico.empty:
                            df_final = df_processado
                        else:
                            df_final = pd.concat([df_historico, df_processado], ignore_index=True)
                        
                        # Atualiza a aba do Google Sheets
                        conn.update(worksheet=WORKSHEET_NAME, data=df_final)
                        st.success(f"Fechamento {mes_ref} de {banco_selecionado} salvo! A base foi atualizada com sucesso.")
                        st.rerun()
