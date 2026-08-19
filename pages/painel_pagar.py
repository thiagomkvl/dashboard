import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re
import unicodedata
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import io

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Contas a Pagar", layout="wide", page_icon="💸")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    :root {
        --bg: #f5f7fb; --surface: #ffffff; --border: #e7ebf2;
        --text: #172033; --muted: #6b7280; --primary: #d53157; /* Vermelho/Rosa para CP */
        --success: #159570; --danger: #d94a4a; --warning: #c58a16;
        --shadow: 0 4px 15px rgba(213, 49, 87, 0.08);
    }
    html, body, [class*="css"] { font-family: "Inter", sans-serif; }
    .main .block-container { padding-top: 1rem; max-width: 98%; }
    
    .kpi-card { position: relative; overflow: hidden; min-height: 85px; padding: 14px 18px 12px; border-radius: 10px; box-shadow: var(--shadow); border: none; }
    .kpi-card.aberto { background: linear-gradient(135deg, #1f2937, #374151); }
    .kpi-card.vencido { background: linear-gradient(135deg, #b91c1c, #ef4444); }
    .kpi-card.avencer { background: linear-gradient(135deg, #d97706, #f59e0b); }
    .kpi-card.pago { background: linear-gradient(135deg, #047857, #10b981); }
    
    .kpi-icon { width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 6px; border-radius: 7px; background: rgba(255,255,255,0.2); font-size: 14px; color: white; }
    .kpi-title { font-size: 10px; font-weight: 750; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
    .kpi-value { font-size: 24px; font-weight: 800; color: #ffffff; white-space: nowrap; }
    
    .section-title { font-size: 13px; font-weight: 800; text-transform: uppercase; color: var(--text); border-bottom: 2px solid var(--border); padding-bottom: 5px; margin-bottom: 15px; }
    .mini-kpi { padding: 10px; border: 1px solid var(--border); border-radius: 8px; background: #fff; text-align: center; }
    .mini-kpi-title { font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; }
    .mini-kpi-val { font-size: 18px; font-weight: 800; color: #172033; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES UTILITÁRIAS
# ==============================================================================
def limpa_valor(valor):
    try:
        if pd.isna(valor): return 0.0
        v_str = str(valor).replace('R$', '').strip()
        if '.' in v_str and ',' in v_str: v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str: v_str = v_str.replace(',', '.')
        return float(v_str)
    except: return 0.0

def formata_brl(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def normalizar_coluna(cols):
    # Facilita encontrar as colunas mesmo que o nome mude um pouco na planilha
    return {c: unicodedata.normalize('NFKD', str(c)).encode('ASCII', 'ignore').decode('utf-8').lower().strip() for c in cols}

# ==============================================================================
# CARGA DE DADOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_base_titulos():
    conn = conectar_sheets()
    if not conn: return pd.DataFrame()
    
    try:
        df = conn.read(worksheet="Base_Títulos", ttl=0)
        if df.empty: return df
        
        # Mapa de colunas dinâmico
        mapa_cols = normalizar_coluna(df.columns)
        
        def acha_col(chaves):
            for col_orig, col_norm in mapa_cols.items():
                if any(k in col_norm for k in chaves): return col_orig
            return None

        # Identifica colunas chave
        c_benef = acha_col(['beneficiari'])
        c_venc = acha_col(['vencimento'])
        c_emissao = acha_col(['emissao'])
        c_liq = acha_col(['liquida'])
        c_saldo = acha_col(['saldo atual', 'a pagar']) or acha_col(['valor orig'])
        c_pago = acha_col(['vl pago', 'pago'])
        c_sit = acha_col(['situacao'])
        c_nota = acha_col(['nota', 'nr. nota', 'documento'])

        # Limpeza e Tipagem
        df['Beneficiário'] = df[c_benef].astype(str).str.strip().str.upper() if c_benef else "DESCONHECIDO"
        df['Nr. Nota'] = df[c_nota].astype(str).str.strip() if c_nota else "-"
        df['Situação'] = df[c_sit].astype(str).str.strip().str.upper() if c_sit else "ABERTO"
        
        # Datas
        df['Vencimento'] = pd.to_datetime(df[c_venc], dayfirst=True, errors='coerce') if c_venc else pd.NaT
        df['Dt. Emissão'] = pd.to_datetime(df[c_emissao], dayfirst=True, errors='coerce') if c_emissao else pd.NaT
        df['Dt. Liquidação'] = pd.to_datetime(df[c_liq], dayfirst=True, errors='coerce') if c_liq else pd.NaT
        
        # Valores
        df['Saldo Atual'] = df[c_saldo].apply(limpa_valor) if c_saldo else 0.0
        df['Valor Pago'] = df[c_pago].apply(limpa_valor) if c_pago else 0.0

        # Identifica status lógico
        hoje_pd = pd.to_datetime(datetime.now().date())
        df['Status Real'] = 'PAGO'
        mask_aberto = (df['Saldo Atual'] > 0) | (df['Situação'].str.contains('ABERTO|PENDENTE|LIBERADO', na=False))
        df.loc[mask_aberto & (df['Vencimento'] >= hoje_pd), 'Status Real'] = 'A VENCER'
        df.loc[mask_aberto & (df['Vencimento'] < hoje_pd), 'Status Real'] = 'VENCIDO'

        return df
    except Exception as e:
        st.error(f"Erro ao ler Base_Títulos: {e}")
        return pd.DataFrame()

df_base = carregar_base_titulos()
if df_base.empty:
    st.warning("Base de Títulos vazia ou não encontrada.")
    st.stop()

# ==============================================================================
# BARRA LATERAL & FILTROS
# ==============================================================================
with st.sidebar:
    st.markdown("### Filtros de Busca")
    
    lista_fornecedores = ["TODOS"] + sorted([f for f in df_base['Beneficiário'].unique() if f and f != 'NAN'])
    fornecedor_sel = st.selectbox("🔍 Fornecedor / Beneficiário:", lista_fornecedores)
    
    situacao_sel = st.multiselect("📌 Status do Título:", ['A VENCER', 'VENCIDO', 'PAGO'], default=['A VENCER', 'VENCIDO'])
    
    hoje = datetime.now().date()
    data_sel = st.date_input("🗓️ Período de Vencimento:", value=(hoje.replace(day=1), hoje + timedelta(days=30)), format="DD/MM/YYYY")

# Aplicação dos filtros
df_filtro = df_base.copy()

if isinstance(data_sel, tuple) and len(data_sel) == 2:
    dt_ini, dt_fim = data_sel
    df_filtro = df_filtro[(df_filtro['Vencimento'].dt.date >= dt_ini) & (df_filtro['Vencimento'].dt.date <= dt_fim)]

if situacao_sel:
    df_filtro = df_filtro[df_filtro['Status Real'].isin(situacao_sel)]

if fornecedor_sel != "TODOS":
    df_filtro = df_filtro[df_filtro['Beneficiário'] == fornecedor_sel]

# ==============================================================================
# CABEÇALHO & KPIs MACRO
# ==============================================================================
st.markdown("""
<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;'>
    <div><h2 style='margin:0; font-weight:800; color:#172033;'>CONTAS A PAGAR</h2><p style='margin:0; font-size:12px; color:#6b7280;'>Controle de Passivos, Prazos e Acordos</p></div>
</div>
""", unsafe_allow_html=True)

df_abertos = df_filtro[df_filtro['Status Real'].isin(['A VENCER', 'VENCIDO'])]
total_aberto = df_abertos['Saldo Atual'].sum()
total_vencido = df_abertos[df_abertos['Status Real'] == 'VENCIDO']['Saldo Atual'].sum()

proximos_7d = df_abertos[(df_abertos['Vencimento'].dt.date >= hoje) & (df_abertos['Vencimento'].dt.date <= hoje + timedelta(days=7))]['Saldo Atual'].sum()
total_pago = df_filtro[df_filtro['Status Real'] == 'PAGO']['Valor Pago'].sum()

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card aberto'><div class='kpi-icon'>📄</div><div class='kpi-title'>TOTAL EM ABERTO</div><div class='kpi-value'>{formata_brl(total_aberto)}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card vencido'><div class='kpi-icon'>🚨</div><div class='kpi-title'>VENCIDO (RISCO)</div><div class='kpi-value'>{formata_brl(total_vencido)}</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi-card avencer'><div class='kpi-icon'>⏳</div><div class='kpi-title'>VENCE EM 7 DIAS</div><div class='kpi-value'>{formata_brl(proximos_7d)}</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi-card pago'><div class='kpi-icon'>✅</div><div class='kpi-title'>VOLUME PAGO (Filtro)</div><div class='kpi-value'>{formata_brl(total_pago)}</div></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

# ==============================================================================
# VISÃO MICRO (FORNECEDOR SELECIONADO) E MOTOR DE ACORDOS
# ==============================================================================
if fornecedor_sel != "TODOS":
    st.markdown(f"<h3 style='color:#172033;'>🏢 Raio-X: {fornecedor_sel}</h3>", unsafe_allow_html=True)
    
    # Cálculos PMP Efetivo e Negociado
    df_forn = df_base[df_base['Beneficiário'] == fornecedor_sel].copy()
    
    df_forn['Prazo_Negociado'] = (df_forn['Vencimento'] - df_forn['Dt. Emissão']).dt.days
    df_forn['Prazo_Efetivo'] = (df_forn['Dt. Liquidação'] - df_forn['Dt. Emissão']).dt.days
    
    pm_negociado = df_forn['Prazo_Negociado'].mean()
    pm_efetivo = df_forn['Prazo_Efetivo'].mean()
    ultima_liq = df_forn['Dt. Liquidação'].max()
    vl_ultimo_pago = df_forn[df_forn['Dt. Liquidação'] == ultima_liq]['Valor Pago'].sum() if pd.notnull(ultima_liq) else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='mini-kpi'><div class='mini-kpi-title'>Prazo Médio Original</div><div class='mini-kpi-val'>{pm_negociado:.0f} dias</div></div>", unsafe_allow_html=True)
    cor_pm = "#10b981" if pm_efetivo >= pm_negociado else "#ef4444"
    m2.markdown(f"<div class='mini-kpi'><div class='mini-kpi-title'>Prazo Médio Efetivo (Pago)</div><div class='mini-kpi-val' style='color:{cor_pm};'>{pm_efetivo:.0f} dias</div></div>", unsafe_allow_html=True)
    
    dt_str = ultima_liq.strftime('%d/%m/%Y') if pd.notnull(ultima_liq) else "-"
    m3.markdown(f"<div class='mini-kpi'><div class='mini-kpi-title'>Último Pagamento</div><div class='mini-kpi-val'>{dt_str}</div></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='mini-kpi'><div class='mini-kpi-title'>Valor Último Pag.</div><div class='mini-kpi-val'>{formata_brl(vl_ultimo_pago)}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Títulos & Gráficos", "🤝 Motor de Acordos"])
    
    with tab1:
        c_graf, c_tab = st.columns([1, 1.5])
        with c_graf:
            st.markdown("<div class='section-title'>PROJEÇÃO DE DESEMBOLSOS (A Vencer)</div>", unsafe_allow_html=True)
            df_proj = df_abertos[df_abertos['Status Real'] == 'A VENCER'].groupby('Vencimento')['Saldo Atual'].sum().reset_index()
            if not df_proj.empty:
                fig = px.bar(df_proj, x='Vencimento', y='Saldo Atual', color_discrete_sequence=['#d53157'])
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum título a vencer neste período.")
        
        with c_tab:
            st.markdown("<div class='section-title'>LISTA DE TÍTULOS (FILTRADOS)</div>", unsafe_allow_html=True)
            df_view = df_filtro[['Nr. Nota', 'Dt. Emissão', 'Vencimento', 'Status Real', 'Saldo Atual']].copy()
            df_view['Dt. Emissão'] = df_view['Dt. Emissão'].dt.strftime('%d/%m/%Y')
            df_view['Vencimento'] = df_view['Vencimento'].dt.strftime('%d/%m/%Y')
            df_view['Saldo Atual'] = df_view['Saldo Atual'].apply(formata_brl)
            st.dataframe(df_view, hide_index=True, use_container_width=True, height=280)

    with tab2:
        st.markdown("<div class='section-title'>SIMULADOR DE RENEGOCIAÇÃO</div>", unsafe_allow_html=True)
        
        df_abertos_forn = df_forn[df_forn['Status Real'].isin(['A VENCER', 'VENCIDO'])].copy()
        
        if df_abertos_forn.empty:
            st.success("Não há títulos em aberto para este fornecedor para realizar acordos.")
        else:
            st.write("1. Selecione os títulos que farão parte do acordo:")
            df_abertos_forn['Selecionar'] = False
            
            # Editor de dados interativo
            edited_df = st.data_editor(
                df_abertos_forn[['Selecionar', 'Nr. Nota', 'Dt. Emissão', 'Vencimento', 'Status Real', 'Saldo Atual']],
                column_config={
                    "Selecionar": st.column_config.CheckboxColumn("Add", default=False),
                    "Saldo Atual": st.column_config.NumberColumn(format="R$ %.2f")
                },
                disabled=["Nr. Nota", "Dt. Emissão", "Vencimento", "Status Real", "Saldo Atual"],
                hide_index=True,
                use_container_width=True
            )
            
            titulos_selecionados = edited_df[edited_df['Selecionar']]
            valor_original_acordo = titulos_selecionados['Saldo Atual'].sum()
            
            if valor_original_acordo > 0:
                st.markdown(f"**Total Selecionado:** `{formata_brl(valor_original_acordo)}` ({len(titulos_selecionados)} notas)")
                st.markdown("---")
                st.write("2. Configure as condições do novo acordo:")
                
                col_param1, col_param2, col_param3, col_param4 = st.columns(4)
                juros_pct = col_param1.number_input("Juros (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
                desconto_pct = col_param2.number_input("Desconto (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
                num_parcelas = col_param3.number_input("Nº Parcelas", min_value=1, max_value=120, value=1, step=1)
                recorrencia = col_param4.selectbox("Recorrência", ["Mensal (30d)", "Quinzenal (15d)", "Semanal (7d)"])
                
                data_primeira_parc = st.date_input("Data da 1ª Parcela", value=hoje + timedelta(days=1))
                
                # Matemática do Acordo
                fator_juros = 1 + (juros_pct/100)
                fator_desc = 1 - (desconto_pct/100)
                valor_final_acordo = valor_original_acordo * fator_juros * fator_desc
                valor_parcela = valor_final_acordo / num_parcelas
                
                passo_dias = 30 if "Mensal" in recorrencia else (15 if "Quinzenal" in recorrencia else 7)
                
                # Gera Cronograma
                cronograma = []
                data_atual = pd.to_datetime(data_primeira_parc)
                hoje_pd = pd.to_datetime(hoje)
                soma_dias_peso = 0
                
                for i in range(1, num_parcelas + 1):
                    cronograma.append({
                        "Parcela": f"{i}/{num_parcelas}",
                        "Vencimento": data_atual.strftime('%d/%m/%Y'),
                        "Valor (R$)": valor_parcela
                    })
                    # Calculo do novo prazo médio a partir de hoje
                    dias_pra_frente = (data_atual - hoje_pd).days
                    soma_dias_peso += (valor_parcela * dias_pra_frente)
                    
                    data_atual = data_atual + timedelta(days=passo_dias)
                
                df_cronograma = pd.DataFrame(cronograma)
                novo_prazo_medio = soma_dias_peso / valor_final_acordo if valor_final_acordo > 0 else 0
                
                # Layout Resultado
                st.markdown("<br>", unsafe_allow_html=True)
                r1, r2, r3 = st.columns(3)
                r1.markdown(f"<div class='mini-kpi'><div class='mini-kpi-title'>Total do Acordo</div><div class='mini-kpi-val'>{formata_brl(valor_final_acordo)}</div></div>", unsafe_allow_html=True)
                r2.markdown(f"<div class='mini-kpi'><div class='mini-kpi-title'>Valor da Parcela</div><div class='mini-kpi-val'>{formata_brl(valor_parcela)}</div></div>", unsafe_allow_html=True)
                r3.markdown(f"<div class='mini-kpi'><div class='mini-kpi-title'>Novo Prazo Médio (a partir de hoje)</div><div class='mini-kpi-val' style='color:#3157d5;'>{novo_prazo_medio:.0f} dias</div></div>", unsafe_allow_html=True)
                
                st.dataframe(df_cronograma, hide_index=True, use_container_width=True)
                
                # Exportação para Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_origens_export = df_abertos_forn.loc[df_abertos_forn['Selecionar']][['Nr. Nota', 'Dt. Emissão', 'Vencimento', 'Saldo Atual']].copy()
                    df_origens_export.to_excel(writer, index=False, sheet_name='Títulos Incorporados')
                    df_cronograma.to_excel(writer, index=False, sheet_name='Novo Cronograma')
                
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Baixar Acordo em Excel",
                    data=excel_data,
                    file_name=f"Proposta_Acordo_{fornecedor_sel}_{hoje.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

# ==============================================================================
# VISÃO MACRO (TODOS OS FORNECEDORES)
# ==============================================================================
else:
    c_graf, c_tab = st.columns([1.5, 1])
    with c_graf:
        st.markdown("<div class='section-title'>LINHA DO TEMPO DE VENCIMENTOS (Geral)</div>", unsafe_allow_html=True)
        df_proj = df_abertos[df_abertos['Status Real'] == 'A VENCER'].groupby('Vencimento')['Saldo Atual'].sum().reset_index()
        if not df_proj.empty:
            fig = px.area(df_proj, x='Vencimento', y='Saldo Atual', color_discrete_sequence=['#d53157'], markers=True)
            fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="R$ a Pagar")
            st.plotly_chart(fig, use_container_width=True)
            
    with c_tab:
        st.markdown("<div class='section-title'>MAIORES EXPOSIÇÕES (Top Fornecedores em Aberto)</div>", unsafe_allow_html=True)
        df_top = df_abertos.groupby('Beneficiário')['Saldo Atual'].sum().reset_index().sort_values('Saldo Atual', ascending=False).head(10)
        df_top['Saldo Atual'] = df_top['Saldo Atual'].apply(formata_brl)
        st.dataframe(df_top, hide_index=True, use_container_width=True, height=320)
        
    st.markdown("<div class='section-title'>TABELA OPERACIONAL DE TÍTULOS</div>", unsafe_allow_html=True)
    df_view = df_filtro[['Beneficiário', 'Nr. Nota', 'Dt. Emissão', 'Vencimento', 'Status Real', 'Saldo Atual']].copy()
    df_view['Dt. Emissão'] = df_view['Dt. Emissão'].dt.strftime('%d/%m/%Y')
    df_view['Vencimento'] = df_view['Vencimento'].dt.strftime('%d/%m/%Y')
    df_view['Saldo Atual'] = df_view['Saldo Atual'].apply(formata_brl)
    st.dataframe(df_view, hide_index=True, use_container_width=True)

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:20px; text-align:right;'>Módulo Contas a Pagar | Dados atualizados em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>", unsafe_allow_html=True)
