import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 1. CONFIGURAÇÃO, CSS E FUNÇÕES DE FORMATAÇÃO
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

def formatar_real(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(str(texto))
    if alinhar == 'esquerda':
        return texto[:tamanho].ljust(tamanho, preenchimento)
    # Para números: remove pontos/vírgulas e alinha à direita com zeros
    texto_num = str(texto).replace('.', '').replace(',', '').replace('R$', '').strip()
    return texto_num[:tamanho].rjust(tamanho, preenchimento)

st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 5px; background-color: white; }
    [data-testid="stVerticalBlock"] > div:nth-child(10) {
        max-height: 480px; overflow-y: auto; border: 1px solid #d1d5db; padding: 15px; border-radius: 10px; background-color: #f9fafb;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE GERAÇÃO CNAB 240 (UNICRED)
# ==========================================
def gerar_cnab240(df_selecionado, dados_hospital):
    linhas = []
    hoje = datetime.now()
    
    # Registro 0: Header de Arquivo
    header_arq = (
        "001" + "0000" + "0" + " " * 9 + "2" + 
        formatar_campo(dados_hospital['cnpj'], 14, '0', 'direita') +
        formatar_campo(dados_hospital['convenio'], 20) +
        formatar_campo(dados_hospital['agencia'], 5, '0', 'direita') + " " +
        formatar_campo(dados_hospital['conta'], 12, '0', 'direita') + " " + " " +
        formatar_campo("SOS CARDIO SERVICOS HOSP", 30) +
        formatar_campo("UNICRED", 30) + " " * 10 + "1" +
        hoje.strftime("%d%m%Y") + hoje.strftime("%H%M%S") +
        "000001" + "103" + "00000" + " " * 69
    )
    linhas.append(header_arq)

    # Registro 1: Header de Lote (Pagamento de Títulos/Tributos/Transferências)
    header_lote = (
        "001" + "0001" + "1" + "C" + "20" + "01" + "046" + " " + "2" +
        formatar_campo(dados_hospital['cnpj'], 14, '0', 'direita') +
        formatar_campo(dados_hospital['convenio'], 20) +
        formatar_campo(dados_hospital['agencia'], 5, '0', 'direita') + " " +
        formatar_campo(dados_hospital['conta'], 12, '0', 'direita') + " " + " " +
        formatar_campo("SOS CARDIO SERVICOS HOSP", 30) + " " * 80 +
        hoje.strftime("%d%m%Y") + "0" * 8 + " " * 33
    )
    linhas.append(header_lote)

    for i, row in df_selecionado.iterrows():
        n_seq = i + 1
        valor_pag = int(float(row['VALOR_PAGAMENTO']) * 100)
        
        # Segmento A (Crédito em Conta / TED / PIX)
        seg_a = (
            "001" + "0001" + "3" + formatar_campo(n_seq * 2 - 1, 5, '0', 'direita') + "A" +
            "000" + "01" + "000" + formatar_campo(row['BANCO_FAVORECIDO'], 3, '0', 'direita') +
            formatar_campo(row['AGENCIA_FAVORECIDA'], 5, '0', 'direita') + " " +
            formatar_campo(row['CONTA_FAVORECIDA'], 12, '0', 'direita') + formatar_campo(row['DIGITO_CONTA_FAVORECIDA'], 1) + " " +
            formatar_campo(row['NOME_FAVORECIDO'], 30) +
            formatar_campo(row.get('INFORMACAO', ''), 20) + 
            pd.to_datetime(row['DATA_PAGAMENTO']).strftime("%d%m%Y") + "BRL" +
            "0" * 15 + formatar_campo(valor_pag, 15, '0', 'direita') + " " * 40 + "00" + " " * 10
        )
        linhas.append(seg_a)
        
        # Segmento B (Dados Complementares / Chave PIX)
        seg_b = (
            "001" + "0001" + "3" + formatar_campo(n_seq * 2, 5, '0', 'direita') + "B" +
            " " * 3 + "2" + formatar_campo(row.get('cnpj_beneficiario', '0'), 14, '0', 'direita') + 
            " " * 100 + formatar_campo(row.get('CHAVE_PIX', ''), 35) + " " * 21
        )
        linhas.append(seg_b)

    # Trailers de Lote e Arquivo
    linhas.append("00100015" + " " * 9 + formatar_campo(len(linhas) + 1, 6, '0', 'direita') + "0" * 100 + " " * 102)
    linhas.append("00199999" + " " * 9 + "000001" + formatar_campo(len(linhas) + 1, 6, '0', 'direita') + " " * 205)

    return "\r\n".join(linhas)

# ==========================================
# 3. CARREGAMENTO E NAVEGAÇÃO
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados_historico():
    try:
        conn = conectar_sheets()
        df = conn.read(worksheet="Historico", ttl=60)
        if not df.empty:
            df['Beneficiario'] = df['Beneficiario'].astype(str).str.strip()
            df['Saldo_Limpo'] = pd.to_numeric(df['Saldo Atual'], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

df_hist = carregar_dados_historico()

st.sidebar.title("Módulos SOS CARDIO")
aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Evolução Temporal", "Pagamentos Unicred", "Upload"])

# ==========================================
# 4. ABA: PAGAMENTOS UNICRED (NOVO)
# ==========================================
if aba == "Pagamentos Unicred":
    st.title("🔌 Gerador CNAB 240 - Unicred")
    
    st.sidebar.subheader("Dados Bancários Hospital")
    dados_hosp = {
        'cnpj': st.sidebar.text_input("CNPJ SOS Cardio:", "00000000000000"),
        'convenio': st.sidebar.text_input("Código Convênio:", "12345"),
        'agencia': st.sidebar.text_input("Agência:", "0000"),
        'conta': st.sidebar.text_input("Conta:", "00000")
    }

    try:
        conn = conectar_sheets()
        df_dia = conn.read(worksheet="Pagamentos_Dia", ttl=0)
        
        if not df_dia.empty:
            st.write(f"📋 **{len(df_dia)}** pagamentos carregados do Tasy/Sheets.")
            if 'Pagar?' not in df_dia.columns:
                df_dia.insert(0, 'Pagar?', True)
            
            edited_df = st.data_editor(df_dia, hide_index=True, use_container_width=True)
            df_para_pagar = edited_df[edited_df['Pagar?'] == True].copy()
            
            if not df_para_pagar.empty:
                st.metric("Total da Remessa", formatar_real(df_para_pagar['VALOR_PAGAMENTO'].sum()))
                if st.button("🚀 Gerar Arquivo de Remessa (.REM)"):
                    txt_cnab = gerar_cnab240(df_para_pagar, dados_hosp)
                    st.download_button(
                        label="📥 Baixar Arquivo Unicred",
                        data=txt_cnab,
                        file_name=f"REMESSA_UNICRED_{datetime.now().strftime('%d%m%Y_%H%M')}.txt",
                        mime="text/plain"
                    )
        else: st.warning("Nenhum pagamento pendente em 'Pagamentos_Dia'.")
    except: st.error("Erro ao conectar na aba 'Pagamentos_Dia'. Verifique seu Google Sheets.")

# ==========================================
# 5. ABA: DASHBOARD PRINCIPAL (SEU CÓDIGO ATUAL)
# ==========================================
elif aba == "Dashboard Principal":
    if not df_hist.empty:
        ultima_data = df_hist['data_processamento'].max()
        df_hoje = df_hist[df_hist['data_processamento'] == ultima_data].copy()

        df_abc = df_hoje.groupby('Beneficiario')['Saldo_Limpo'].sum().sort_values(ascending=False).reset_index()
        total_hoje = df_abc['Saldo_Limpo'].sum()
        df_abc['Acumulado'] = df_abc['Saldo_Limpo'].cumsum() / total_hoje
        df_abc['Classe ABC'] = df_abc['Acumulado'].apply(lambda x: 'Classe A (80%)' if x <= 0.8 else ('Classe B (15%)' if x <= 0.95 else 'Classe C (5%)'))
        df_hoje = df_hoje.merge(df_abc[['Beneficiario', 'Classe ABC']], on='Beneficiario', how='left')

        st.title("Gestão de Passivo - SOS CARDIO")
        m1, m2, m3, m4 = st.columns(4)
        total_vencido = df_hoje[df_hoje['Carteira'] != 'A Vencer']['Saldo_Limpo'].sum()
        m1.metric("Dívida Total", formatar_real(total_hoje))
        m2.metric("Total Vencido", formatar_real(total_vencido))
        m3.metric("Fornecedores", len(df_hoje['Beneficiario'].unique()))
        m4.metric("Qtd Classe A", len(df_abc[df_abc['Classe ABC'] == 'Classe A (80%)']))

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Curva ABC de Fornecedores")
            sel_abc = st.multiselect("Filtrar Classes:", ['Classe A (80%)', 'Classe B (15%)', 'Classe C (5%)'], default=['Classe A (80%)', 'Classe B (15%)', 'Classe C (5%)'])
            df_pie = df_hoje[df_hoje['Classe ABC'].isin(sel_abc)]
            fig_p = px.pie(df_pie, values='Saldo_Limpo', names='Classe ABC', hole=0.4, color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
            st.plotly_chart(fig_p, use_container_width=True)

        with c2:
            st.subheader("Volume por Faixa (Ageing)")
            ordem_cart = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
            sel_cart = st.multiselect("Filtrar Faixas:", ordem_cart, default=ordem_cart)
            df_bar = df_hoje[df_hoje['Carteira'].isin(sel_cart)].groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem_cart).reset_index().fillna(0)
            fig_b = px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s')
            st.plotly_chart(fig_b, use_container_width=True)

        st.divider()
        st.subheader("Detalhamento com Análise de Risco")
        with st.container(height=480):
            df_agrup = df_hoje.groupby(['Beneficiario', 'Classe ABC']).agg(
                Total_Aberto=('Saldo_Limpo', 'sum'),
                Total_Vencido=('Saldo_Limpo', lambda x: df_hoje.loc[x.index][df_hoje.loc[x.index, 'Carteira'] != 'A Vencer']['Saldo_Limpo'].sum())
            ).sort_values('Total_Aberto', ascending=False).reset_index()

            for _, row in df_agrup.iterrows():
                label = f"{row['Beneficiario']} ({row['Classe ABC']}) | Aberto: {formatar_real(row['Total_Aberto'])} | Vencido: {formatar_real(row['Total_Vencido'])}"
                with st.expander(label):
                    detalhe = df_hoje[df_hoje['Beneficiario'] == row['Beneficiario']].copy()
                    detalhe['Valor'] = detalhe['Saldo_Limpo'].apply(formatar_real)
                    st.table(detalhe[['Vencimento', 'Valor', 'Carteira']])

        # --- RADAR DE PAGAMENTOS ---
        st.divider()
        st.subheader("🎯 Radar de Pagamentos - Detalhamento Diário")
        hoje_dt = pd.Timestamp.now().normalize()
        df_hoje['Vencimento_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
        df_futuro = df_hoje[df_hoje['Vencimento_DT'] >= hoje_dt].copy()

        if not df_futuro.empty:
            df_futuro['Mes_Ref'] = df_futuro['Vencimento_DT'].dt.strftime('%m/%Y')
            meses_disp = sorted(df_futuro['Mes_Ref'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
            mes_sel = st.selectbox("Selecione o Mês:", meses_disp)
            
            df_mes = df_futuro[df_futuro['Mes_Ref'] == mes_sel].copy()
            df_mes['Data_Formatada'] = df_mes['Vencimento_DT'].dt.strftime('%d/%m/%Y')
            df_mes = df_mes.sort_values('Vencimento_DT')

            fig_forn = px.bar(df_mes, x='Data_Formatada', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=600)
            st.plotly_chart(fig_forn, use_container_width=True)
        else: st.info("Nenhum vencimento futuro.")

# ==========================================
# 6. ABAS: EVOLUÇÃO E UPLOAD (MANTIDOS)
# ==========================================
elif aba == "Evolução Temporal":
    st.title("Evolução da Inadimplência")
    if not df_hist.empty:
        df_ev = df_hist.groupby('data_processamento')['Saldo_Limpo'].sum().reset_index()
        df_ev['dt_ordem'] = pd.to_datetime(df_ev['data_processamento'], format='%d/%m/%Y')
        fig_ev = px.line(df_ev.sort_values('dt_ordem'), x='data_processamento', y='Saldo_Limpo', markers=True)
        st.plotly_chart(fig_ev, use_container_width=True)

elif aba == "Upload":
    st.title("Upload da Base")
    uploaded = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
    if uploaded and st.button("Salvar e Atualizar"):
        df_new = pd.read_excel(uploaded)
        df_push = df_new.copy()
        df_push.columns = df_push.columns.str.strip()
        if salvar_no_historico(df_push):
            st.success("Dados salvos!")
            st.rerun()

if df_hist.empty and aba != "Upload" and aba != "Pagamentos Unicred":
    st.warning("Aguardando upload inicial dos dados.")
