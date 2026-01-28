import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 1. CONFIGURAÇÃO, CSS E SEGURANÇA (LOGIN)
# ==========================================
st.set_page_config(page_title="SOS CARDIO - Gestão de Passivo", layout="wide")

def check_password():
    def password_entered():
        if "password" in st.session_state:
            if st.session_state["password"] == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False
    if st.session_state.get("password_correct"):
        return True
    st.markdown("<h1 style='text-align: center;'>🏥 SOS CARDIO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
    return False

# --- FUNÇÕES DE SUPORTE ---
def formatar_real(valor):
    try: return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_campo(texto, tamanho, preenchimento=' ', alinhar='esquerda'):
    texto = remover_acentos(str(texto))
    if alinhar == 'esquerda': return texto[:tamanho].ljust(tamanho, preenchimento)
    texto_num = "".join(filter(str.isdigit, str(texto)))
    return texto_num[:tamanho].rjust(tamanho, preenchimento)

# CSS ORIGINAL (MANTIDO)
st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 5px; background-color: white; }
    [data-testid="stVerticalBlock"] > div:nth-child(10) {
        max-height: 480px; overflow-y: auto; border: 1px solid #d1d5db; padding: 15px; border-radius: 10px; background-color: #f9fafb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR CNAB 240 (UNICRED) ---
def gerar_cnab240(df_sel, h):
    l = []
    hoje = datetime.now()
    l.append((f"00100000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000").ljust(240))
    l.append((f"00100011C2001046 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{' '*80}{hoje.strftime('%d%m%Y')}{'0'*8}").ljust(240))
    for i, r in df_sel.reset_index(drop=True).iterrows():
        v = int(float(r['VALOR_PAGAMENTO']) * 100)
        l.append((f"00100013{formatar_campo(i*2+1,5,'0','r')}A00001000{formatar_campo(r.get('BANCO_FAVORECIDO','001'),3,'0','r')}{formatar_campo(r.get('AGENCIA_FAVORECIDA','0'),5,'0','r')} {formatar_campo(r.get('CONTA_FAVORECIDA','0'),12,'0','r')}{formatar_campo(r.get('DIGITO','0'),1)} {formatar_campo(r['NOME_FAVORECIDO'],30)}{formatar_campo(r.get('Nr. Titulo',''),20)}{pd.to_datetime(r['DATA_PAGAMENTO']).strftime('%d%m%Y')}BRL{'0'*15}{formatar_campo(v,15,'0','r')}{' '*40}00").ljust(240))
        l.append((f"00100013{formatar_campo(i*2+2,5,'0','r')}B   2{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}{' '*100}{formatar_campo(r.get('CHAVE_PIX',''),35)}").ljust(240))
    l.append((f"00100015{' '*9}{formatar_campo(len(l)+1,6,'0','r')}{'0'*100}").ljust(240))
    l.append((f"00199999{' '*9}000001{formatar_campo(len(l)+1,6,'0','r')}").ljust(240))
    return "\r\n".join(l)

# ==========================================
# 3. LÓGICA DO APP
# ==========================================
if check_password():
    @st.cache_data(ttl=300)
    def carregar_dados_hist():
        try:
            conn = conectar_sheets()
            df = conn.read(worksheet="Historico", ttl=300)
            if not df.empty:
                df['Beneficiario'] = df['Beneficiario'].astype(str).str.strip()
                df['Saldo_Limpo'] = pd.to_numeric(df['Saldo Atual'], errors='coerce').fillna(0)
            return df
        except: return pd.DataFrame()

    df_hist = carregar_dados_hist()

    st.sidebar.title("Menu SOS CARDIO")
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Evolução Temporal", "Upload"])

    # ------------------------------------------
    # ABA: DASHBOARD PRINCIPAL (SEM ALTERAÇÕES)
    # ------------------------------------------
    if aba == "Dashboard Principal":
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
                sel_abc = st.multiselect("Filtrar Classes:", ['Classe A (80%)', 'Classe B (15%)', 'Classe C (5%)'], default=['Classe A (80%)', 'Classe B (15%)', 'Classe C (5%)'], key="f_abc")
                df_pie = df_hoje[df_hoje['Classe ABC'].isin(sel_abc)]
                fig_p = px.pie(df_pie, values='Saldo_Limpo', names='Classe ABC', hole=0.4, color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
                st.plotly_chart(fig_p, use_container_width=True)
            with c2:
                st.subheader("Volume por Faixa (Ageing)")
                ordem_cart = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                sel_cart = st.multiselect("Filtrar Faixas:", ordem_cart, default=ordem_cart, key="f_age")
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
                fig_forn = px.bar(df_mes, x='Data_Formatada', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=600, color_discrete_sequence=px.colors.qualitative.Prism)
                df_totais = df_mes.groupby('Data_Formatada')['Saldo_Limpo'].sum().reset_index()
                for i, row in df_totais.iterrows():
                    fig_forn.add_annotation(x=row['Data_Formatada'], y=row['Saldo_Limpo'], text=f"<b>{formatar_real(row['Saldo_Limpo'])}</b>", showarrow=False, yshift=12, font=dict(size=11))
                fig_forn.update_layout(xaxis_type='category', showlegend=False, xaxis=dict(tickangle=-45))
                st.plotly_chart(fig_forn, use_container_width=True)
                st.write("📋 **Top 15 Maiores Pagamentos Previstos**")
                df_maiores = df_futuro.sort_values('Saldo_Limpo', ascending=False).head(15)
                df_maiores['Valor'] = df_maiores['Saldo_Limpo'].apply(formatar_real)
                st.table(df_maiores[['Vencimento', 'Beneficiario', 'Valor', 'Classe ABC']])

    # ------------------------------------------
    # ABA: PAGAMENTOS UNICRED (LOGICA OTIMIZADA)
    # ------------------------------------------
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")
        st.sidebar.subheader("Configurações Hospital")
        h_d = {'cnpj': st.sidebar.text_input("CNPJ:"), 'convenio': st.sidebar.text_input("Convênio:"), 'ag': st.sidebar.text_input("Agência:"), 'cc': st.sidebar.text_input("Conta:")}

        # Carregamento Automático Único (Memória)
        if 'df_pagamentos' not in st.session_state:
            try:
                conn = conectar_sheets()
                df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
                if not df_p.empty:
                    if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                    st.session_state['df_pagamentos'] = df_p
                else:
                    st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'Nr. Titulo', 'DATA_PAGAMENTO', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO', 'cnpj_beneficiario', 'CHAVE_PIX'])
            except: st.error("Erro ao carregar dados.")

        if 'df_pagamentos' in st.session_state:
            st.info("💡 Edite ou adicione títulos abaixo. Clique em 'Salvar' para atualizar o Google Sheets.")
            
            # Editor Dinâmico (Permite adicionar linhas)
            df_editado = st.data_editor(st.session_state['df_pagamentos'], hide_index=True, use_container_width=True, num_rows="dynamic")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Salvar Alterações no Google Sheets"):
                    try:
                        conn = conectar_sheets()
                        conn.update(worksheet="Pagamentos_Dia", data=df_editado)
                        st.session_state['df_pagamentos'] = df_editado
                        st.success("✅ Google Sheets sincronizado!")
                    except: st.error("Erro ao salvar.")

            with col_btn2:
                df_final = df_editado[df_editado['Pagar?'] == True]
                if not df_final.empty:
                    total_rem = df_final['VALOR_PAGAMENTO'].astype(float).sum()
                    if st.button(f"🚀 Gerar Remessa ({formatar_real(total_rem)})"):
                        txt = gerar_cnab240(df_final, h_d)
                        st.download_button("📥 Baixar .REM", txt, f"REM_UNICRED_{datetime.now().strftime('%d%m')}.txt")

    elif aba == "Evolução Temporal":
        st.title("Evolução da Inadimplência")
        df_ev = df_hist.groupby('data_processamento')['Saldo_Limpo'].sum().reset_index()
        df_ev['dt_ordem'] = pd.to_datetime(df_ev['data_processamento'], format='%d/%m/%Y')
        fig_ev = px.line(df_ev.sort_values('dt_ordem'), x='data_processamento', y='Saldo_Limpo', markers=True)
        st.plotly_chart(fig_ev, use_container_width=True)

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Excel do Tasy", type=["xlsx"])
        if up and st.button("Salvar"):
            df_n = pd.read_excel(up)
            if salvar_no_historico(df_n): st.success("Ok!"); st.rerun()

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False
        st.rerun()
