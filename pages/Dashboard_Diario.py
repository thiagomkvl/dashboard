import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Tente importar a conexão
try:
    from database import conectar_sheets
except ImportError:
    def conectar_sheets():
        st.error("Arquivo 'database.py' não encontrado.")
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Financeiro Mensal", layout="wide", page_icon="📊")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 95%; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
    
    .stPlotlyChart { background-color: transparent !important; }
    .js-plotly-plot, .plot-container { margin: 0 auto; }
    
    .kpi-card { background: white; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 10px; text-align: center; }
    .kpi-card.total { border-top: 4px solid #4e73df; background: #f8faff; }
    .kpi-card.disponivel { border-top: 4px solid #1cc88a; background: #f4fdf6; }
    .kpi-card.limites { border-top: 4px solid #36b9cc; background: #f4fcfe; }
    .kpi-card.aplicacoes { border-top: 4px solid #6f42c1; background: #fbf8ff; }
    
    .kpi-title { font-size: 11px; font-weight: bold; color: #858796; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { font-size: 20px; font-weight: bold; color: #3a3b45; }
    
    .section-title { font-size: 13px; font-weight: bold; color: #1a2035; text-transform: uppercase; margin-bottom: 6px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
    .section-title-inline { font-size: 10px; font-weight: bold; color: #858796; text-transform: uppercase; }

    /* Tabela Padrão */
    .tabela-container { border: 1px solid #e3e6f0; border-radius: 4px; background: white; font-size: 14px; width: 100%; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .tabela-financeira { width: 100%; border-collapse: collapse; }
    .tabela-financeira th { background-color: #4e73df; color: white; font-weight: bold; text-align: left; padding: 10px 12px; border-bottom: 1px solid #e3e6f0; }
    .tabela-financeira td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; font-weight: 500; color: #1a202c; }
    .tabela-financeira .linha-total { background-color: #e2e6ea; font-weight: bold; border-top: 2px solid #ccc; }
    .tabela-financeira .valores { text-align: left; font-weight: bold; color: #2d3748; }
    
    .ind-item { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; }
    
    /* Estilo do Resumo de Rendimentos (Sutil) */
    .rend-box { background: white; padding: 0 0 10px 0; font-size: 14px; }
    .rend-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #eee; }
    .rend-item:last-child { border-bottom: none; }
    
    .rend-total { background: #fffbeb; border-left: 3px solid #f6c23e; padding: 6px 10px; margin-top: 8px; border-radius: 4px; display: flex; justify-content: space-between; }
    .rend-total span { font-weight: bold; }

    .custo-oportunidade { background: #f0f5ff; border-left: 3px solid #e74a3b; padding: 6px 10px; margin-top: 8px; border-radius: 4px; display: flex; justify-content: space-between; }
    .custo-oportunidade span { font-weight: bold; color: #e74a3b; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÃO DE LEITURA E LIMPEZA BLINDADA
# ==============================================================================
def limpa_valor_bruto(valor):
    """Lida perfeitamente com valores que já são números, strings vazias, e formatações contábeis."""
    if pd.isna(valor) or str(valor).strip() in ["", "-"]:
        return 0.0
    
    if isinstance(valor, (int, float)):
        return float(valor)
        
    try:
        v_str = str(valor).strip()
        v_str = re.sub(r'^\s*\((.*?)\)\s*$', r'-\1', v_str)
        v_str = v_str.replace('R$', '').strip()
        
        if '.' in v_str and ',' in v_str:
            v_str = v_str.replace('.', '').replace(',', '.')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
            
        return float(v_str)
    except ValueError:
        return 0.0

def formatar_moeda(valor):
    if valor == 0: return "-"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# ==============================================================================
# 2. CARGA DE DADOS COM INTEGRAÇÃO DE EXTRATOS
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados():
    conn = conectar_sheets()
    if conn is None: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, ""
    try:
        # =========================================================
        # 1. Carrega Histórico de Saldos
        # =========================================================
        df_saldos = conn.read(worksheet="Historico_Saldos", ttl=0)
        if df_saldos.empty:
            st.warning("A aba 'Historico_Saldos' está vazia.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, ""
        
        df_saldos.columns = [str(c).strip() for c in df_saldos.columns]
        col_conta = 'Contas Bancárias' if 'Contas Bancárias' in df_saldos.columns else 'Conta Bancária'
        col_data = 'Data'
        
        df_saldos[col_data] = pd.to_datetime(df_saldos[col_data], format='%d/%m/%Y', errors='coerce')
        for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']:
            if col in df_saldos.columns:
                df_saldos[col] = df_saldos[col].apply(limpa_valor_bruto)

        ultima_data = df_saldos[col_data].dropna().max()
        if pd.isna(ultima_data):
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, ""
            
        mes_referencia = ultima_data.replace(day=1)
        proximo_mes = mes_referencia + relativedelta(months=1)
        df_mes = df_saldos[(df_saldos[col_data] >= mes_referencia) & (df_saldos[col_data] < proximo_mes)].copy()

        # DEFINIR O TIPO
        def definir_tipo(nome): 
            if 'getnet' in str(nome).lower(): return 'Limite'
            return 'Aplicação' if ('aplicação' in str(nome).lower() or 'investimentos' in str(nome).lower()) else 'Disponível'
        df_mes['Tipo'] = df_mes[col_conta].apply(definir_tipo)

        # =========================================================
        # CORREÇÃO: INTEGRAÇÃO COM A ABA EXTRATOS
        # =========================================================
        # Verifica se as colunas Entrada e Saída estão zeradas na aba Historico
        if df_mes['Entrada'].sum() == 0 and df_mes['Saída'].sum() == 0:
            try:
                # Tenta carregar os extratos
                df_extratos = conn.read(worksheet="Extratos_Bancos", ttl=0)
                if not df_extratos.empty:
                    df_extratos.columns = [str(c).strip() for c in df_extratos.columns]
                    
                    # Mapeia colunas do Extrato (baseado na sua imagem)
                    col_ext_conta = next((c for c in df_extratos.columns if 'banco' in c.lower() or 'conta' in c.lower()), 'Banco')
                    col_ext_data = next((c for c in df_extratos.columns if 'data' in c.lower()), 'Data')
                    col_ext_credito = next((c for c in df_extratos.columns if 'crédito' in c.lower() or 'credito' in c.lower()), 'Vlr Crédito')
                    col_ext_debito = next((c for c in df_extratos.columns if 'débito' in c.lower() or 'debito' in c.lower()), 'Vlr Débito')

                    # Prepara o DataFrame de Extratos (Limpeza e Filtro de Mês)
                    df_extratos[col_ext_data] = pd.to_datetime(df_extratos[col_ext_data], format='%d/%m/%Y', errors='coerce')
                    df_extratos = df_extratos[(df_extratos[col_ext_data] >= mes_referencia) & (df_extratos[col_ext_data] < proximo_mes)]
                    
                    # Soma Crédito e Débito por Banco e Data
                    df_extratos_grouped = df_extratos.groupby([col_ext_conta, col_ext_data]).agg({
                        col_ext_credito: 'sum',
                        col_ext_debito: 'sum'
                    }).reset_index().rename(columns={
                        col_ext_conta: col_conta,
                        col_ext_data: col_data
                    })
                    
                    # Converte para float
                    df_extratos_grouped[col_ext_credito] = df_extratos_grouped[col_ext_credito].apply(limpa_valor_bruto)
                    df_extratos_grouped[col_ext_debito] = df_extratos_grouped[col_ext_debito].apply(limpa_valor_bruto)

                    # Mescla os dados de Extrato no df_mes (Atualiza Entrada e Saída)
                    df_mes = df_mes.merge(df_extratos_grouped, on=[col_conta, col_data], how='left')
                    df_mes['Entrada'] = df_mes[col_ext_credito].fillna(0)
                    df_mes['Saída'] = df_mes[col_ext_debito].fillna(0)
                    
                    # Remove colunas extras do merge
                    df_mes = df_mes.drop(columns=[col_ext_credito, col_ext_debito])
                    
            except Exception as e:
                # Se falhar a leitura do Extrato, mantém os zeros e continua
                pass

        # Cálculo de Variação Mensal para a Tabela de Bancos
        # Usa Entrada e Saída (que podem ter vindo do Extrato ou da própria aba)
        df_fim_mes = df_mes.sort_values(by=[col_data, col_conta]).drop_duplicates(subset=[col_conta], keep='last').copy()
        df_inicio_mes = df_mes.sort_values(by=[col_data, col_conta]).drop_duplicates(subset=[col_conta], keep='first').copy()
        df_inicio_mes_dict = df_inicio_mes.set_index(col_conta)['Saldo Final'].to_dict()
        df_fim_mes['Saldo Inicial'] = df_fim_mes[col_conta].map(df_inicio_mes_dict).fillna(0)

        # =========================================================
        # Agrupamento para Gráfico Diário
        # =========================================================
        df_graficos = df_mes.groupby(col_data).agg({
            'Saldo Final': 'sum',
            'Saldo Inicial': 'sum',
            'Entrada': 'sum',
            'Saída': 'sum'
        }).reset_index().sort_values(col_data)
        
        df_graficos['Data_Label'] = df_graficos[col_data].dt.strftime('%d/%m')
        df_graficos['Variação %'] = df_graficos['Saldo Final'].pct_change() * 100
        df_graficos['Variação %'] = df_graficos['Variação %'].fillna(0)

        # =========================================================
        # 2. Carrega a aba RENDIMENTOS
        # =========================================================
        df_rend_resumo = pd.DataFrame()
        rendimento_total_mes = 0.0
        
        try:
            df_rend = conn.read(worksheet="Rendimentos", ttl=0)
            if not df_rend.empty:
                df_rend.columns = [str(c).strip() for c in df_rend.columns]
                
                col_conta_rend = next((c for c in df_rend.columns if 'conta' in c.lower() or 'banco' in c.lower()), None)
                col_rendimento = next((c for c in df_rend.columns if 'rendimento' in c.lower() or 'l\u00edquido' in c.lower() or 'liquido' in c.lower()), None)
                
                if col_rendimento:
                    df_rend[col_rendimento] = df_rend[col_rendimento].apply(limpa_valor_bruto)
                    
                    if col_conta_rend:
                        df_rend_resumo = df_rend.groupby(col_conta_rend)[col_rendimento].sum().reset_index()
                        df_rend_resumo.rename(columns={col_conta_rend: col_conta, col_rendimento: 'Valor Líquido'}, inplace=True)
                    else:
                        rend_sum = df_rend[col_rendimento].sum()
                        df_rend_resumo = pd.DataFrame({col_conta: ['Aplicações Consolidadas'], 'Valor Líquido': [rend_sum]})

                    rendimento_total_mes = df_rend_resumo['Valor Líquido'].sum()
        except Exception as e:
            pass

        # =========================================================
        # 3. LER A ABA DE CUSTO DE OPORTUNIDADE
        # =========================================================
        custo_oportunidade_total = 0.0
        try:
            df_custos = conn.read(worksheet="Custo_Oportunidade", ttl=0)
            if not df_custos.empty:
                df_custos.columns = [str(c).strip() for c in df_custos.columns]
                col_custo = next((c for c in df_custos.columns if 'custo' in c.lower()), None)
                if col_custo:
                    df_custos[col_custo] = df_custos[col_custo].apply(limpa_valor_bruto)
                    custo_oportunidade_total = df_custos[col_custo].sum()
        except Exception as e:
            pass

        return df_fim_mes, df_graficos, df_rend_resumo, rendimento_total_mes, custo_oportunidade_total, col_conta
        
    except Exception as e:
        st.error(f"Erro fatal: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0, 0.0, ""

# ==============================================================================
# CHAMADA PRINCIPAL E MONTAGEM DO PAINEL
# ==============================================================================
df_consolidado, df_graficos, df_rend_resumo, rendimento_total_mes, custo_oportunidade_total, col_conta = carregar_dados()
if not col_conta: col_conta = 'Contas Bancárias'
if df_consolidado.empty: st.stop()

# ==============================================================================
# 3. CÁLCULOS DOS KPIs MENSAIS
# ==============================================================================
saldo_aplicado = df_consolidado[df_consolidado['Tipo'] == 'Aplicação']['Saldo Final'].sum()
saldo_disponivel = df_consolidado[df_consolidado['Tipo'] == 'Disponível']['Saldo Final'].sum()

limite_getnet = df_consolidado[df_consolidado['Tipo'] == 'Limite']['Disponível'].sum()
limites_garantidos = df_consolidado['Conta Garantida'].sum()
limites_totais = limite_getnet + limites_garantidos

saldo_total = saldo_disponivel + limites_totais + saldo_aplicado

entradas_mes = df_consolidado['Entrada'].sum()
saidas_mes = df_consolidado['Saída'].sum()
resultado_liquido_mes = entradas_mes - saidas_mes

# ==============================================================================
# 4. GRÁFICOS
# ==============================================================================
# Donut
fig_donut = go.Figure(data=[go.Pie(
    values=[saldo_aplicado, saldo_disponivel], 
    labels=['Aplicado', 'Disponível'], 
    hole=0.6, 
    marker=dict(colors=['#4e73df', '#1cc88a']),
    textinfo='percent',
    texttemplate='%{percent:.1%}',
    hoverinfo='label+percent'
)])
fig_donut.update_layout(
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
    margin=dict(t=10, b=40, l=0, r=0), height=320,
    annotations=[dict(text=f"<b>R$ {saldo_total/1000000:,.1f}M</b><br>Saldo Total", x=0.5, y=0.48, font_size=12, showarrow=False)]
)

# Gráfico de Barras + Linha de Tendência
fig_combinado = go.Figure()
fig_combinado.add_trace(go.Bar(
    x=df_graficos['Data_Label'],
    y=df_graficos['Saldo Final'],
    name='Saldo Total',
    marker_color='#dbe4ff',
    opacity=0.85,
    width=0.5
))
fig_combinado.add_trace(go.Scatter(
    x=df_graficos['Data_Label'],
    y=df_graficos['Saldo Final'],
    name='Tendência',
    mode='lines+markers+text',
    line=dict(color='#1a3b7c', width=2.5),
    marker=dict(size=7, color='#1a3b7c', line=dict(width=2, color='white')),
    text=[f"{((df_graficos['Saldo Final'].iloc[i] - df_graficos['Saldo Final'].iloc[i-1])/df_graficos['Saldo Final'].iloc[i-1])*100:.2f}%" if i > 0 and df_graficos['Saldo Final'].iloc[i-1] != 0 else "" for i in range(len(df_graficos))],
    textposition="top center",
    textfont=dict(size=11, color="#333", weight="bold"),
))
fig_combinado.update_layout(
    margin=dict(t=35, b=15, l=5, r=5), height=190, 
    xaxis=dict(tickfont=dict(size=10), showgrid=False), 
    yaxis=dict(showticklabels=False, showgrid=False),
    barmode='overlay',
    showlegend=False,
    plot_bgcolor='#f1f5f9', paper_bgcolor='#f1f5f9',
    hovermode='x unified'
)

# ==============================================================================
# 5. MONTAGEM DO PAINEL
# ==============================================================================
data_hoje = datetime.now().strftime('%d/%m/%Y')
mes_referencia_nome = df_graficos['Data_Label'].iloc[-1] if not df_graficos.empty else ""

st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; margin-bottom: 5px; border-bottom: 1px solid #e3e6f0;">
    <div><b style="font-size:18px;">📅 Agosto/2026</b><br><span style="font-size:10px; color:gray;">Período de referência</span></div>
    <div style="text-align:center;"><h2 style="margin:0; color:#1a2035; font-size:22px;">PAINEL FINANCEIRO MENSAL</h2><p style="margin:0; font-size:11px; color:gray;">Controle Consolidado de Bancos</p></div>
    <div style="display:flex; gap:10px;">
        <div style="background:#d4edda; border-radius:12px; padding:1px 15px; text-align:center;"><span style="font-size:10px;">Atualização</span><br><b style="font-size:14px;">{data_hoje}</b></div>
    </div>
</div>
""", unsafe_allow_html=True)

# KPIs
kpi_row = st.columns(4)
kp_data = [
    (kpi_row[0], "🏛️", "SALDO TOTAL", f"R$ {saldo_total:,.2f}", "total"),
    (kpi_row[1], "💳", "SALDO DISPONÍVEL", f"R$ {saldo_disponivel:,.2f}", "disponivel"),
    (kpi_row[2], "🛡️", "LIMITES TOTAIS", f"R$ {limites_totais:,.2f}", "limites"),
    (kpi_row[3], "📊", "APLICAÇÕES", f"R$ {saldo_aplicado:,.2f}", "aplicacoes")
]
for col, icon, title, val, color in kp_data:
    col.markdown(f"<div class='kpi-card {color}'><div style='font-size:12px;'>{icon}</div><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.1, 1.4, 1])

with c1:
    st.markdown("<div class='section-title'>DISTRIBUIÇÃO DO CAIXA</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

with c2:
    st.markdown("<div class='section-title'>MOVIMENTAÇÃO DO MÊS</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div style='padding:6px;'><div class='section-title-inline' style='color:#1cc88a;'>⬇ ENTRADAS</div><div style='font-size:16px; font-weight:bold;'>R$ {entradas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div style='padding:6px;'><div class='section-title-inline' style='color:#e74a3b;'>⬆ SAÍDAS</div><div style='font-size:16px; font-weight:bold;'>R$ {saidas_mes:,.2f}</div></div>", unsafe_allow_html=True)
    
    if resultado_liquido_mes >= 0:
        m3.markdown(f"<div style='padding:6px;'><div class='section-title-inline' style='color:#1cc88a;'>✅ RESULTADO LÍQUIDO</div><div style='font-size:16px; font-weight:bold; color:#1cc88a;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)
    else:
        m3.markdown(f"<div style='padding:6px;'><div class='section-title-inline' style='color:#e74a3b;'>🔻 RESULTADO LÍQUIDO</div><div style='font-size:16px; font-weight:bold; color:#e74a3b;'>R$ {resultado_liquido_mes:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:10px;'>EVOLUÇÃO DIÁRIA DO SALDO TOTAL</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_combinado, use_container_width=True, config={'displayModeBar': False})

with c3:
    st.markdown("<div class='section-title'>RESUMO DE RENDIMENTOS</div>", unsafe_allow_html=True)
    
    if not df_rend_resumo.empty:
        st.markdown("<div class='rend-box'>", unsafe_allow_html=True)
        for _, row in df_rend_resumo.iterrows():
            valor = row['Valor Líquido']
            cor = "#1cc88a" if valor >= 0 else "#e74a3b"
            
            st.markdown(f"""
            <div class='rend-item'>
                <span style='font-weight:500;'>{row[col_conta]}</span>
                <span style='font-weight:bold; color:{cor};'>{formatar_moeda(valor)}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class='rend-total'>
            <span>💰 TOTAL RENDIMENTOS</span>
            <span>{formatar_moeda(rendimento_total_mes)}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='padding: 10px; text-align:center; color: #888; font-size: 13px; border: 1px dashed #ccc; border-radius: 8px;'>
            Nenhum dado de rendimento formatado encontrado.
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='custo-oportunidade'>
        <span>🔻 PERDA MENSAL (NÃO APLICADO)</span>
        <span>- {formatar_moeda(custo_oportunidade_total)}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

col_tab, col_diario = st.columns([1.6, 1])

with col_tab:
    st.markdown(f"<div class='section-title'>SALDO DE TODOS OS BANCOS</div>", unsafe_allow_html=True)
    df_view = df_consolidado[['Tipo', col_conta, 'Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']].copy()
    totais = {col: df_view[col].sum() for col in ['Saldo Inicial', 'Entrada', 'Saída', 'Saldo Final', 'Conta Garantida', 'Disponível']}
    
    html_tabela = '<div class="tabela-container"><table class="tabela-financeira"><thead><tr><th>#</th><th>'+col_conta+'</th><th>TIPO</th><th>SALDO INICIAL</th><th>ENTRADA</th><th>SAÍDA</th><th class="valores">SALDO FINAL</th><th>CONTA GARANTIDA</th><th>DISPONÍVEL</th></tr></thead><tbody>'
    for idx, row in df_view.iterrows():
        html_tabela += f'<tr><td>{idx+1}</td><td>{row[col_conta]}</td><td style="font-size:12px; font-weight:bold; color:#555;">{row["Tipo"]}</td><td class="valores">{formatar_moeda(row["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(row["Entrada"])}</td><td class="valores">{formatar_moeda(row["Saída"])}</td><td class="valores">{formatar_moeda(row["Saldo Final"])}</td><td class="valores">{formatar_moeda(row["Conta Garantida"])}</td><td class="valores">{formatar_moeda(row["Disponível"])}</td></tr>'
    html_tabela += f'<tr class="linha-total"><td></td><td>TOTAL</td><td></td><td class="valores">{formatar_moeda(totais["Saldo Inicial"])}</td><td class="valores">{formatar_moeda(totais["Entrada"])}</td><td class="valores">{formatar_moeda(totais["Saída"])}</td><td class="valores">{formatar_moeda(totais["Saldo Final"])}</td><td class="valores">{formatar_moeda(totais["Conta Garantida"])}</td><td class="valores">{formatar_moeda(totais["Disponível"])}</td></tr>'
    html_tabela += '</tbody></table></div>'
    st.markdown(html_tabela, unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; color:gray; margin-top:2px;'><span style='display:inline-block; width:10px; height:10px; background:#1cc88a; border-radius:2px; margin-right:4px;'></span> Disponível <span style='display:inline-block; width:10px; height:10px; background:#4e73df; border-radius:2px; margin-left:15px; margin-right:4px;'></span> Aplicação</div>", unsafe_allow_html=True)

with col_diario:
    st.markdown("<div class='section-title'>SALDO DIÁRIO CONSOLIDADO</div>", unsafe_allow_html=True)
    
    df_diario_view = df_graficos[['Data_Label', 'Saldo Final', 'Variação %']].copy()
    df_diario_view = df_diario_view.sort_values(by='Data_Label', ascending=False)
    
    html_diario = '<div class="tabela-container" style="font-size:13px;"><table class="tabela-financeira"><thead><tr><th>DATA</th><th class="valores">SALDO FINAL</th><th class="valores">VARIAÇÃO</th></tr></thead><tbody>'
    
    for _, row in df_diario_view.iterrows():
        variacao = row['Variação %']
        cor = "#1cc88a" if variacao >= 0 else "#e74a3b"
        html_diario += f'<tr><td style="font-weight:bold; color:#333;">{row["Data_Label"]}</td><td class="valores">{formatar_moeda(row["Saldo Final"])}</td><td class="valores" style="color:{cor}; font-weight:bold;">{variacao:.2f}%</td></tr>'
    html_diario += '</tbody></table></div>'
    st.markdown(html_diario, unsafe_allow_html=True)

st.markdown(f"<div style='font-size:9px; color:gray; margin-top:10px; text-align:right;'>Valores em Reais (R$) | Dados atualizados em {data_hoje}</div>", unsafe_allow_html=True)
