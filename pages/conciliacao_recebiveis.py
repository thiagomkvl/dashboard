import streamlit as st
import pandas as pd
from core.normalizacao import normalizar_recebimentos, normalizar_tasy
from core.conciliacao import executar_conciliacao
from services.google_sheets import carregar_dados_sheets, salvar_regras_sheets, fechar_periodo_sheets

st.set_page_config(page_title="Conciliação de Recebíveis", layout="wide", page_icon="🏦")
st.title("🏦 Painel de Conciliação de Recebíveis")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Recarregar Dados Base", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 1. Carregamento Geral
df_bancos_raw, df_tasy_raw, df_matriz_full, df_config, df_fechados = carregar_dados_sheets()

if df_bancos_raw.empty or df_tasy_raw.empty:
    st.warning("Aguardando lançamentos nas abas Extratos_Bancos e Base_Tasy no Google Sheets.")
    st.stop()

df_rec = normalizar_recebimentos(df_bancos_raw)
df_tasy = normalizar_tasy(df_tasy_raw)

# Extração de Meses/Anos
df_rec['Mes_Ano'] = df_rec['data'].dt.strftime('%m/%Y')
df_tasy['Mes_Ano'] = df_tasy['data'].dt.strftime('%m/%Y')
meses_disponiveis = sorted(df_rec['Mes_Ano'].unique(), reverse=True)

# -------------------------------------------------------------
# BARRA LATERAL: CONTROLES
# -------------------------------------------------------------
st.sidebar.markdown("### 📅 Filtro de Período")
mes_selecionado = st.sidebar.selectbox("Selecione o Mês para Conciliar:", meses_disponiveis)

periodos_fechados = df_fechados['Mes_Ano'].tolist() if not df_fechados.empty else []
is_fechado = mes_selecionado in periodos_fechados

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ Regras Globais")

# Lendo regras configuradas do Google Sheets
regras = dict(zip(df_config['Chave'], df_config['Valor'])) if not df_config.empty else {}
transacoes_str = regras.get('tipos_transacao', '')
transacoes_salvas = [x.strip() for x in transacoes_str.split(',') if x.strip()]

todas_transacoes = sorted(df_rec['descricao'].unique().tolist())
trans_validas = [t for t in transacoes_salvas if t in todas_transacoes]

transacoes_selecionadas = st.sidebar.multiselect(
    "Tipos de Transação a Conciliar:",
    options=todas_transacoes,
    default=trans_validas,
    help="Define quais tipos de lançamento (ex: PIX, TED, Adiantamento) serão validados pelo motor."
)

if st.sidebar.button("💾 Salvar Regras", use_container_width=True):
    if salvar_regras_sheets(transacoes_selecionadas):
        st.sidebar.success("Regras fixadas para os próximos acessos!")

# -------------------------------------------------------------
# LÓGICA DO MOTOR (ABERTO VS FECHADO)
# -------------------------------------------------------------
df_rec_mes = df_rec[df_rec['Mes_Ano'] == mes_selecionado].copy()
df_tasy_mes = df_tasy[df_tasy['Mes_Ano'] == mes_selecionado].copy()

if is_fechado:
    st.success(f"🔒 **PERÍODO CONSOLIDADO ({mes_selecionado})**: Este período já foi fechado. Exibindo resultados históricos congelados. Nenhuma alteração afetará este mês.")
    # Recupera apenas as linhas fechadas deste mês da Matriz Histórica
    df_matriz_mes = df_matriz_full.copy()
    df_matriz_mes['tmp_mes'] = pd.to_datetime(df_matriz_mes['data_recebimento']).dt.strftime('%m/%Y')
    df_matriz_mes = df_matriz_mes[df_matriz_mes['tmp_mes'] == mes_selecionado].drop(columns=['tmp_mes'])
else:
    st.info(f"🟢 **PERÍODO EM ABERTO ({mes_selecionado})**: Calculando conciliação em tempo real com base nas regras.")
    
    if transacoes_selecionadas:
        df_rec_mes = df_rec_mes[df_rec_mes['descricao'].isin(transacoes_selecionadas)]
    
    # Motor calcula sob demanda
    df_matriz_mes = executar_conciliacao(df_rec_mes, df_tasy_mes)
    
    # Botão de travamento
    if st.button("🔒 Fechar Conciliação do Mês (Travar Período)"):
        with st.spinner(f"Consolidando período {mes_selecionado}..."):
            if fePara garantir que as regras da conciliação não se percam ao recarregar o painel no Streamlit e que os períodos fechados fiquem bloqueados para edição, a melhor arquitetura é utilizar um armazenamento local (como arquivos JSON ou um banco de dados SQLite/Oracle) integrado ao `st.session_state`.

Abaixo está a estrutura de código implementando essas funcionalidades. Dividi a navegação usando uma barra lateral para organizar as "Regras" separadas do "Painel" em si.

```python
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Caminhos dos arquivos para persistência
ARQUIVO_REGRAS = 'regras_conciliacao.json'
ARQUIVO_FECHAMENTOS = 'historico_fechamentos.json'

# --- 1. FUNÇÕES DE PERSISTÊNCIA ---
def carregar_dados(arquivo, default_data):
    if os.path.exists(arquivo):
        with open(arquivo, 'r') as f:
            return json.load(f)
    return default_data

def salvar_dados(arquivo, dados):
    with open(arquivo, 'w') as f:
        json.dump(dados, f, indent=4)

# Carrega os estados salvos antes de renderizar a tela
regras_iniciais = {"tipos_transacao": ["PIX", "Cartão de Crédito", "Convênio"]}
regras_atuais = carregar_dados(ARQUIVO_REGRAS, regras_iniciais)
fechamentos_atuais = carregar_dados(ARQUIVO_FECHAMENTOS, {})

# --- 2. MENU LATERAL ---
st.sidebar.title("Menu de Conciliação")
menu = st.sidebar.radio("Navegação", ["📊 Painel de Conciliação", "⚙️ Regras"])

# --- 3. TELA DE REGRAS ---
if menu == "⚙️ Regras":
    st.header("Configuração de Regras")
    st.write("Defina os parâmetros fixos. Eles serão salvos e aplicados automaticamente nas próximas sessões.")
    
    tipos_disponiveis = ["PIX", "Cartão de Crédito", "Cartão de Débito", "Boleto", "Convênio", "TED/DOC", "Dinheiro"]
    
    tipos_selecionados = st.multiselect(
        "Tipos de Transação a Conciliar:",
        options=tipos_disponiveis,
        default=[t for t in regras_atuais.get("tipos_transacao", []) if t in tipos_disponiveis]
    )
    
    if st.button("Salvar Regras", type="primary"):
        regras_atuais["tipos_transacao"] = tipos_selecionados
        salvar_dados(ARQUIVO_REGRAS, regras_atuais)
        st.success("Regras salvas! Elas já estão ativas para os cruzamentos.")

# --- 4. TELA DO PAINEL PRINCIPAL ---
elif menu == "📊 Painel de Conciliação":
    st.header("Painel de Conciliação Financeira")
    
    # Filtro de Período
    col1, col2 = st.columns(2)
    meses = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    anos = ["2025", "2026", "2027"]
    
    with col1:
        mes_selecionado = st.selectbox("Mês", meses, index=datetime.now().month - 1)
    with col2:
        ano_selecionado = st.selectbox("Ano", anos, index=1)
        
    periodo_atual = f"{ano_selecionado}-{mes_selecionado}"
    
    # Verifica se o período já foi fechado
    is_fechado = fechamentos_atuais.get(periodo_atual, {}).get("status") == "Fechado"
    
    if is_fechado:
        st.warning(f"🔒 A conciliação de {periodo_atual} está FECHADA. Edições estão bloqueadas.")
        st.info("Mostrando dados consolidados e gravados.")
        
        # Exemplo: Carregar o dataframe que foi salvo estaticamente no fechamento
        arquivo_consolidado = f"conciliacao_fechada_{periodo_atual}.csv"
        if os.path.exists(arquivo_consolidado):
            df_fechado = pd.read_csv(arquivo_consolidado)
            st.dataframe(df_fechado, use_container_width=True)
            
    else:
        st.success(f"🔓 Período {periodo_atual} em aberto. Aplicando regras atuais.")
        st.caption(f"Regras ativas: {', '.join(regras_atuais['tipos_transacao'])}")
        
        # ---------------------------------------------------------
        # AQUI ENTRA SUA LÓGICA ATUAL DO PANDAS (Cruzamento de dados)
        # df_resultado = cruzar_dados(df_extrato, df_sistema)
        # st.dataframe(df_resultado)
        # ---------------------------------------------------------
        
        st.divider()
        st.subheader("Finalização")
        st.write("Ao fechar a conciliação, o resultado será gravado estaticamente para fins de auditoria.")
        
        if st.button("🔐 Fechar Conciliação do Mês", type="primary"):
            # 1. Atualiza o status do período no JSON de controle
            fechamentos_atuais[periodo_atual] = {
                "status": "Fechado",
                "data_fechamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            salvar_dados(ARQUIVO_FECHAMENTOS, fechamentos_atuais)
            
            # 2. Grava a "fotografia" dos dados conciliados (CSV, Excel ou Banco SQL)
            # df_resultado.to_csv(f"conciliacao_fechada_{periodo_atual}.csv", index=False)
            
            st.success(f"Conciliação de {periodo_atual} concluída e travada com sucesso!")
            st.rerun() # Força o recarregamento da tela para aplicar o bloqueio visual imediatamente
