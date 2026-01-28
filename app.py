import streamlit as st
import pandas as pd
import plotly.express as px
from database import salvar_no_historico, conectar_sheets
from datetime import datetime
import unicodedata

# ==========================================
# 1. CONFIGURAÇÃO E SEGURANÇA
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
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")
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

# CSS PARA APROXIMAR COMPONENTES
st.markdown("""
    <style>
    .stMetric { background-color: white; padding: 10px; border-radius: 10px; border-left: 5px solid #004a99; }
    [data-testid="stVerticalBlock"] > div:nth-child(10) { max-height: 480px; overflow-y: auto; }
    /* Ajuste de margem dos botões */
    .stButton button { width: 100%; }
    div[data-testid="column"] { padding: 0 5px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR CNAB 240 ---
def gerar_cnab240(df_sel, h):
    l = []
    hoje = datetime.now()
    l.append((f"00100000{' '*9}2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{formatar_campo('UNICRED',30)}{' '*10}1{hoje.strftime('%d%m%Y%H%M%S')}00000110300000").ljust(240))
    l.append((f"00100011C2001046 2{formatar_campo(h['cnpj'],14,'0','r')}{formatar_campo(h.get('convenio','0'),20,'0','r')}{formatar_campo(h['ag'],5,'0','r')} {formatar_campo(h['cc'],12,'0','r')}  {formatar_campo('SOS CARDIO SERVICOS HOSP',30)}{' '*80}{hoje.strftime('%d%m%Y')}{'0'*8}").ljust(240))
    for i, r in df_sel.reset_index(drop=True).iterrows():
        v = int(float(str(r['VALOR_PAGAMENTO']).replace(',','.')) * 100)
        l.append((f"00100013{formatar_campo(i*2+1,5,'0','r')}A00001000{formatar_campo(r.get('BANCO_FAVORECIDO','001'),3,'0','r')}{formatar_campo(r.get('AGENCIA_FAVORECIDA','0'),5,'0','r')} {formatar_campo(r.get('CONTA_FAVORECIDA','0'),12,'0','r')}{formatar_campo(r.get('DIGITO_CONTA_FAVORECIDA','0'),1)} {formatar_campo(r['NOME_FAVORECIDO'],30)}{formatar_campo(r.get('Nr. Titulo',''),20)}{pd.to_datetime(r['DATA_PAGAMENTO']).strftime('%d%m%Y')}BRL{'0'*15}{formatar_campo(v,15,'0','r')}{' '*40}00").ljust(240))
        l.append((f"00100013{formatar_campo(i*2+2,5,'0','r')}B   2{formatar_campo(r['cnpj_beneficiario'],14,'0','r')}{' '*100}{formatar_campo(r.get('CHAVE_PIX',''),35)}").ljust(240))
    l.append((f"00100015{' '*9}{formatar_campo(len(l)+1,6,'0','r')}{'0'*100}").ljust(240))
    l.append((f"00199999{' '*9}000001{formatar_campo(len(l)+1,6,'0','r')}").ljust(240))
    return "\r\n".join(l)

if check_password():
    conn = conectar_sheets()
    aba = st.sidebar.radio("Navegação:", ["Dashboard Principal", "Pagamentos Unicred", "Evolução Temporal", "Upload"])

    # ------------------------------------------
    # ABA: DASHBOARD PRINCIPAL (ORIGINAL)
    # ------------------------------------------
    if aba == "Dashboard Principal":
        df_hist = conn.read(worksheet="Historico", ttl=300)
        if not df_hist.empty:
            df_hist['Saldo_Limpo'] = pd.to_numeric(df_hist['Saldo Atual'], errors='coerce').fillna(0)
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
                st.subheader("Curva ABC")
                fig_p = px.pie(df_hoje, values='Saldo_Limpo', names='Classe ABC', hole=0.4, color_discrete_map={'Classe A (80%)': '#004a99', 'Classe B (15%)': '#ffcc00', 'Classe C (5%)': '#d1d5db'})
                st.plotly_chart(fig_p, use_container_width=True)
            with c2:
                st.subheader("Ageing")
                ordem_cart = ['A Vencer', '0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '> 90 dias']
                df_bar = df_hoje.groupby('Carteira')['Saldo_Limpo'].sum().reindex(ordem_cart).reset_index().fillna(0)
                fig_b = px.bar(df_bar, x='Carteira', y='Saldo_Limpo', color_discrete_sequence=['#004a99'], text_auto='.2s')
                st.plotly_chart(fig_b, use_container_width=True)

            st.divider()
            st.subheader("Detalhamento por Fornecedor")
            with st.container(height=480):
                df_agrup = df_hoje.groupby(['Beneficiario', 'Classe ABC']).agg(
                    Total_Aberto=('Saldo_Limpo', 'sum'),
                    Total_Vencido=('Saldo_Limpo', lambda x: df_hoje.loc[x.index][df_hoje.loc[x.index, 'Carteira'] != 'A Vencer']['Saldo_Limpo'].sum())
                ).sort_values('Total_Aberto', ascending=False).reset_index()
                for _, row in df_agrup.iterrows():
                    label = f"{row['Beneficiario']} | Aberto: {formatar_real(row['Total_Aberto'])} | Vencido: {formatar_real(row['Total_Vencido'])}"
                    with st.expander(label):
                        detalhe = df_hoje[df_hoje['Beneficiario'] == row['Beneficiario']].copy()
                        detalhe['Valor'] = detalhe['Saldo_Limpo'].apply(formatar_real)
                        st.table(detalhe[['Vencimento', 'Valor', 'Carteira']])

            st.divider()
            st.subheader("🎯 Radar de Pagamentos")
            df_hoje['Vencimento_DT'] = pd.to_datetime(df_hoje['Vencimento'], dayfirst=True, errors='coerce')
            df_mes = df_hoje[df_hoje['Vencimento_DT'] >= pd.Timestamp.now().normalize()].copy()
            if not df_mes.empty:
                df_mes['Data_Formatada'] = df_mes['Vencimento_DT'].dt.strftime('%d/%m/%Y')
                fig_forn = px.bar(df_mes.sort_values('Vencimento_DT'), x='Data_Formatada', y='Saldo_Limpo', color='Beneficiario', barmode='stack', height=500)
                df_totais = df_mes.groupby('Data_Formatada')['Saldo_Limpo'].sum().reset_index()
                for i, row in df_totais.iterrows():
                    fig_forn.add_annotation(x=row['Data_Formatada'], y=row['Saldo_Limpo'], text=f"<b>{formatar_real(row['Saldo_Limpo'])}</b>", showarrow=False, yshift=12)
                st.plotly_chart(fig_forn, use_container_width=True)

    # ------------------------------------------
    # ABA: PAGAMENTOS UNICRED (OTIMIZADA)
    # ------------------------------------------
    elif aba == "Pagamentos Unicred":
        st.title("🔌 Conversor Unicred - Gestão de Remessa")

        # 1. Carregamento Único
        if 'df_pagamentos' not in st.session_state:
            df_p = conn.read(worksheet="Pagamentos_Dia", ttl=0)
            if not df_p.empty:
                # Garante que Pagar? seja booleano para o checklist aparecer
                if 'Pagar?' not in df_p.columns: df_p.insert(0, 'Pagar?', True)
                df_p['Pagar?'] = df_p['Pagar?'].astype(bool)
                st.session_state['df_pagamentos'] = df_p
            else:
                st.session_state['df_pagamentos'] = pd.DataFrame(columns=['Pagar?', 'NOME_FAVORECIDO', 'VALOR_PAGAMENTO', 'DATA_PAGAMENTO', 'CHAVE_PIX', 'BANCO_FAVORECIDO', 'AGENCIA_FAVORECIDA', 'CONTA_FAVORECIDA', 'DIGITO_CONTA_FAVORECIDA', 'cnpj_beneficiario'])

        # 2. Botões Aproximados e Harmonizados
        c_btn1, c_btn2, c_btn3, c_btn4 = st.columns([1, 1, 1, 1.5])
        
        with c_btn1:
            # JANELA FLUTUANTE PARA NOVO PAGAMENTO
            with st.popover("➕ Novo Título"):
                st.write("Inserir Dados do Fornecedor")
                n_fav = st.text_input("Nome Favorecido")
                n_val = st.number_input("Valor", min_value=0.0, format="%.2f")
                n_data = st.date_input("Vencimento", datetime.now())
                n_cnpj = st.text_input("CNPJ Favorecido")
                n_pix = st.text_input("Chave PIX")
                n_banco = st.text_input("Banco (ex: 001)", "001")
                n_ag = st.text_input("Agência", "0000")
                n_cc = st.text_input("Conta", "00000")
                n_dg = st.text_input("Dígito", "0")
                
                if st.button("Adicionar à Lista"):
                    novo_row = pd.DataFrame([{
                        'Pagar?': True, 'NOME_FAVORECIDO': n_fav, 'VALOR_PAGAMENTO': n_val,
                        'DATA_PAGAMENTO': n_data.strftime('%d/%m/%Y'), 'CHAVE_PIX': n_pix,
                        'BANCO_FAVORECIDO': n_banco, 'AGENCIA_FAVORECIDA': n_ag,
                        'CONTA_FAVORECIDA': n_cc, 'DIGITO_CONTA_FAVORECIDA': n_dg, 'cnpj_beneficiario': n_cnpj
                    }])
                    st.session_state['df_pagamentos'] = pd.concat([st.session_state['df_pagamentos'], novo_row], ignore_index=True)
                    st.rerun()

        with c_btn2:
            if st.button("💾 Salvar Planilha"):
                conn.update(worksheet="Pagamentos_Dia", data=st.session_state['df_pagamentos'])
                st.success("Sincronizado!")

        with c_btn3:
            if st.button("🔄 Atualizar"):
                del st.session_state['df_pagamentos']
                st.rerun()

        with c_btn4:
            df_final = st.session_state['df_pagamentos'][st.session_state['df_pagamentos']['Pagar?'] == True]
            if not df_final.empty:
                v_total = df_final['VALOR_PAGAMENTO'].astype(float).sum()
                st.download_button(f"🚀 Remessa ({formatar_real(v_total)})", 
                                 gerar_cnab240(df_final, {'cnpj': '00000000000000', 'convenio': '0', 'ag': '0', 'cc': '0'}),
                                 f"REM_{datetime.now().strftime('%d%m')}.txt")

        st.divider()

        # 3. Editor de Dados com Checklist
        st.session_state['df_pagamentos'] = st.data_editor(
            st.session_state['df_pagamentos'],
            column_config={"Pagar?": st.column_config.CheckboxColumn("Pagar?", default=True)},
            hide_index=True, use_container_width=True
        )

    elif aba == "Upload":
        st.title("Upload da Base")
        up = st.file_uploader("Arquivo Tasy", type=["xlsx"])
        if up and st.button("Processar"):
            if salvar_no_historico(pd.read_excel(up)): st.success("Ok!"); st.rerun()

    if st.sidebar.button("🔒 Sair"):
        st.session_state["password_correct"] = False
        st.rerun()
