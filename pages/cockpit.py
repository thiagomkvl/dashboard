from datetime import datetime, timedelta
import io  # <--- Manipulação de bytes na memória para download
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from database import conectar_sheets

# --- IMPORTAÇÃO SEGURA ---
try:
  from modules.cnab_engine import extrair_dados_protesto_pdf, gerar_cnab_pix
  from modules.utils import formatar_real, identificar_tipo_pagamento
except ImportError as e:
  st.error(f"Erro crítico nos módulos: {e}")
  st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Cockpit Financeiro - SOS Cardio", page_icon="🎛️", layout="wide"
)

# ==============================================================================
# 0. TELA DE LOGIN (AUTENTICAÇÃO)
# ==============================================================================
if "autenticado" not in st.session_state:
  st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
  col1, col2, col3 = st.columns([1, 2, 1])

  with col2:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align: center; color: #1e40af;'>🔒 Acesso"
        " Restrito</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #64748b;'>Insira a credencial de"
        " segurança para acessar o Cockpit Financeiro.</p>",
        unsafe_allow_html=True,
    )

    senha_input = st.text_input(
        "Senha", type="password", placeholder="Digite a senha..."
    )

    if st.button("Entrar no Sistema", type="primary", use_container_width=True):
      if senha_input == "@SOS2025":
        st.session_state["autenticado"] = True
        st.rerun()
      else:
        st.error("❌ Senha incorreta. Acesso negado.")

  st.stop()


# --- CUSTOM CSS ---
st.markdown(
    """
    <style>
    /* Estilo dos Cards de KPI Superiores */
    .kpi-card {
        background-color: #F8F9FA; 
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .kpi-title { font-size: 15px; color: #6c757d; text-align: center; margin-bottom: 5px;}
    .kpi-value { font-size: 28px; font-weight: bold; color: #343a40; text-align: center; margin-bottom: 15px;}
    .kpi-perc-text { font-size: 13px; color: #6c757d; margin-top: 5px; display: flex; justify-content: space-between;}
    
    /* Destaque do Topo da Tabela */
    [data-testid="stDataFrame"] > div:first-child {
        border-top: 4px solid #212529 !important;
        border-radius: 4px 4px 0 0;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# 1. CARGA DE DADOS (100% PLANILHA)
# ==============================================================================
@st.cache_data(ttl=60)
def carregar_dados_reais():
  try:
    conn = conectar_sheets()
    df = conn.read(worksheet="Pagamentos_Dia", ttl=0)
    if df.empty:
      return pd.DataFrame()

    if "Pagar?" not in df.columns:
      df.insert(0, "Pagar?", True)
    df["Pagar?"] = df["Pagar?"].astype(bool)

    if "VALOR_PAGAMENTO" in df.columns:
      df["VALOR_PAGAMENTO"] = pd.to_numeric(
          df["VALOR_PAGAMENTO"]
          .astype(str)
          .str.replace("R$", "", regex=False)
          .str.replace(".", "", regex=False)
          .str.replace(",", ".", regex=False)
          .str.strip(),
          errors="coerce",
      ).fillna(0.0)
    else:
      df["VALOR_PAGAMENTO"] = 0.0

    # Trata colunas faltantes com valores neutros/padrão
    if "Categoria" not in df.columns or df["Categoria"].isna().all():
      df["Categoria"] = "Geral"
    else:
      df["Categoria"] = df["Categoria"].fillna("Geral")

    if "OC" not in df.columns:
      df["OC"] = "-"
    if "NF" not in df.columns:
      df["NF"] = "-"
    if "Observação" not in df.columns:
      df["Observação"] = "-"
    if "Banco_Origem" not in df.columns:
      df["Banco_Origem"] = "Unicred"
    if "DATA_PAGAMENTO" not in df.columns:
      df["DATA_PAGAMENTO"] = datetime.now().strftime("%d/%m/%Y")
    else:
      df["DATA_PAGAMENTO"] = df["DATA_PAGAMENTO"].astype(str).fillna("-")

    return df
  except Exception as e:
    st.error(f"Erro ao carregar Sheets: {e}")
    return pd.DataFrame()


df_real = carregar_dados_reais()

# ==============================================================================
# 2. MÓDULO DE KPIs SUPERIORES (CALCULADOS VIA PLANILHA)
# ==============================================================================
if not df_real.empty:
  total_geral_planilha = df_real["VALOR_PAGAMENTO"].sum()
  qtd_total_titulos = len(df_real)

  df_selecionados = df_real[df_real["Pagar?"] == True]
  total_selecionado = df_selecionados["VALOR_PAGAMENTO"].sum()
  qtd_selecionados = len(df_selecionados)

  pct_comprometido = (
      round((total_selecionado / total_geral_planilha) * 100, 1)
      if total_geral_planilha > 0
      else 0
  )
  ticket_medio = (
      (total_selecionado / qtd_selecionados) if qtd_selecionados > 0 else 0
  )
else:
  total_geral_planilha = 0.0
  total_selecionado = 0.0
  qtd_total_titulos = 0
  qtd_selecionados = 0
  pct_comprometido = 0
  ticket_medio = 0.0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)


def gerar_html_kpi(titulo, valor, pct_progress, cor_barra, texto_rodape):
  return f"""
    <div class='kpi-card'>
        <div class='kpi-title'>{titulo}</div>
        <div class='kpi-value'>{valor}</div>
        <div class='kpi-perc-text'>
            <span>{texto_rodape}</span>
            <span>{pct_progress}%</span>
        </div>
        <div style='width: 100%; background-color: #E0E0E0; border-radius: 4px; height: 8px; margin-top: 5px;'>
            <div style='width: {min(pct_progress, 100)}%; background-color: {cor_barra}; height: 8px; border-radius: 4px;'></div>
        </div>
    </div>
    """


kpi1.markdown(
    gerar_html_kpi(
        "Total em Planilha",
        formatar_real(total_geral_planilha),
        100,
        "#4e73df",
        f"Total de {qtd_total_titulos} títulos",
    ),
    unsafe_allow_html=True,
)
kpi2.markdown(
    gerar_html_kpi(
        "Total Selecionado (CNAB)",
        formatar_real(total_selecionado),
        pct_comprometido,
        "#1cc88a",
        f"{qtd_selecionados} de {qtd_total_titulos} títulos marcados",
    ),
    unsafe_allow_html=True,
)
kpi3.markdown(
    gerar_html_kpi(
        "% Selecionado p/ Envio",
        f"{pct_comprometido}%",
        pct_comprometido,
        "#f6c23e",
        "Proporção do lote",
    ),
    unsafe_allow_html=True,
)
kpi4.markdown(
    gerar_html_kpi(
        "Ticket Médio / Título",
        formatar_real(ticket_medio),
        min(pct_comprometido, 100),
        "#36b9cc",
        "Média dos selecionados",
    ),
    unsafe_allow_html=True,
)

st.divider()

# ==============================================================================
# 3. CORPO PRINCIPAL (TABELA À ESQUERDA, GRÁFICOS À DIREITA)
# ==============================================================================
col_left, col_right = st.columns([1.3, 1])

# --- ESQUERDA: TABELA E GERAÇÃO CNAB ---
with col_left:
  tab1, tab2, tab3 = st.tabs([
      "Enviar Remessa de Pagamentos",
      "Títulos Vencidos",
      "📄 Auditoria de Protestos (PDF)",
  ])

  with tab1:
    if not df_real.empty:
      colunas_visuais = [
          "Pagar?",
          "NOME_FAVORECIDO",
          "Categoria",
          "OC",
          "NF",
          "Observação",
          "DATA_PAGAMENTO",
          "VALOR_PAGAMENTO",
          "Banco_Origem",
          "CHAVE_PIX_OU_COD_BARRAS",
          "cnpj_beneficiario",
      ]
      for col in colunas_visuais:
        if col not in df_real.columns:
          df_real[col] = ""

      df_display = df_real[colunas_visuais].copy()

      edited_df = st.data_editor(
          df_display,
          hide_index=True,
          use_container_width=True,
          height=680,
          column_config={
              "Pagar?": st.column_config.CheckboxColumn("Pagar", default=True),
              "NOME_FAVORECIDO": "Pagamento",
              "DATA_PAGAMENTO": "Venc. original",
              "VALOR_PAGAMENTO": st.column_config.NumberColumn(
                  "Valor", format="R$ %.2f"
              ),
              "Banco_Origem": "Banco",
              "CHAVE_PIX_OU_COD_BARRAS": None,
              "cnpj_beneficiario": None,
          },
      )

      st.markdown("---")

      # --- LÓGICA DE GERAÇÃO DO ARQUIVO CNAB COM SEQUENCIAL AJUSTÁVEL ---
      col_seq1, col_seq2 = st.columns([1, 2])
      with col_seq1:
        seq_arquivo = st.number_input(
            "Nº Sequencial do Arquivo (NSA)",
            min_value=1,
            value=17,  # Valor 17 configurado para evitar o erro do 16 duplicado
            step=1,
            help=(
                "Altere este número caso o banco informe que o arquivo já foi"
                " processado."
            ),
        )

      linhas_selecionadas = edited_df[edited_df["Pagar?"] == True].index

      if st.button("🚀 Gerar Arquivo de Remessa (CNAB 240)", type="primary"):
        if len(linhas_selecionadas) > 0:
          df_pagar_completo = df_real.loc[linhas_selecionadas].copy()

          # Arredondamento limpo em float com 2 casas decimais
          df_pagar_completo["VALOR_PAGAMENTO"] = df_pagar_completo[
              "VALOR_PAGAMENTO"
          ].round(2)

          # Passa o dataframe e o sequencial numérico para a função
          arquivo_cnab = gerar_cnab_pix(
              df_pagar_completo, sequencial=int(seq_arquivo)
          )

          if arquivo_cnab:
            st.download_button(
                label="📥 Baixar CNAB",
                data=arquivo_cnab,
                file_name=(
                    f"REM_{datetime.now().strftime('%d%m')}_SEQ{int(seq_arquivo)}.txt"
                ),
                mime="text/plain",
            )
        else:
          st.warning("Nenhum título selecionado para pagamento.")
    else:
      st.info("Nenhum dado encontrado na planilha.")

  with tab2:
    st.info(
        "Aqui entrará a query direta do banco de dados do Tasy listando os"
        " títulos vencidos."
    )

  # --- CONVERSOR DE PROTESTOS PDF ---
  with tab3:
    st.subheader("Conversor Inteligente de Certidões de Protesto")
    st.markdown(
        "Arraste e solte uma ou múltiplas certidões em PDF recebidas dos"
        " cartórios para estruturar em uma planilha limpa para a Controladoria."
    )

    arquivos_pdf = st.file_uploader(
        "Selecione os PDFs de Protesto",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader_protestos",
    )

    if arquivos_pdf:
      st.write("")
      if st.button(
          "📊 Processar PDFs e Estruturar Planilha", type="primary"
      ):
        with st.spinner("Escovando os bits dos arquivos PDF... Aguarde."):
          df_protestos = extrair_dados_protesto_pdf(arquivos_pdf)

          if not df_protestos.empty:
            st.success(
                f"Sucesso! {len(df_protestos)} registros de protesto"
                " identificados de forma estruturada."
            )
            st.data_editor(
                df_protestos,
                use_container_width=True,
                hide_index=True,
                height=450,
            )

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
              df_protestos.to_excel(
                  writer, index=False, sheet_name="Protestos"
              )
            processado_excel = output.getvalue()

            st.write("")
            st.download_button(
                label="📥 Baixar Planilha Pronta para Auditoria (.xlsx)",
                data=processado_excel,
                file_name=(
                    f"Protestos_Processados_{datetime.now().strftime('%d%m')}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )
          else:
            st.warning(
                "Nenhuma estrutura padrão de bloco de protesto foi reconhecida"
                " nos PDFs enviados."
            )

# --- DIREITA: GRÁFICOS E ANÁLISES BASEADOS NA PLANILHA ---
with col_right:
  if not df_real.empty and "Categoria" in df_real.columns:
    cat_summary = (
        df_real.groupby("Categoria")["VALOR_PAGAMENTO"]
        .sum()
        .sort_values(ascending=False)
    )
    top1_cat = cat_summary.index[0] if len(cat_summary) > 0 else "Geral"
    top1_val = cat_summary.iloc[0] if len(cat_summary) > 0 else 0.0

    top2_cat = cat_summary.index[1] if len(cat_summary) > 1 else "Outros"
    top2_val = cat_summary.iloc[1] if len(cat_summary) > 1 else 0.0
  else:
    top1_cat, top1_val = "Categoria A", 0.0
    top2_cat, top2_val = "Categoria B", 0.0

  st.markdown(
      f"""
    <div style="display: flex; gap: 15px; margin-top: 10px; margin-bottom: 20px;">
        <div style="flex: 1; background-color: #F8F9FA; padding: 15px; border-radius: 8px; border: 1px solid #E9ECEF; border-left: 5px solid #36b9cc;">
            <div style="font-size: 13px; color: #6c757d; font-weight: 600;">Top Categoria: {top1_cat}</div>
            <div style="font-size: 20px; color: #343a40; font-weight: bold;">{formatar_real(top1_val)}</div>
        </div>
        <div style="flex: 1; background-color: #F8F9FA; padding: 15px; border-radius: 8px; border: 1px solid #E9ECEF; border-left: 5px solid #f6c23e;">
            <div style="font-size: 13px; color: #6c757d; font-weight: 600;">Top Categoria: {top2_cat}</div>
            <div style="font-size: 20px; color: #343a40; font-weight: bold;">{formatar_real(top2_val)}</div>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  def form_k(valor):
    return f"{valor/1000:.1f}k" if valor >= 1000 else f"{valor:.0f}"

  chart_config = {"scrollZoom": False, "displayModeBar": False}

  # --- GRÁFICO 1: EVOLUÇÃO DIÁRIA ---
  if not df_real.empty:
    df_agrupado_dia = (
        df_real.groupby("DATA_PAGAMENTO")
        .agg(
            total_dia=("VALOR_PAGAMENTO", "sum"),
            selecionado_dia=(
                "VALOR_PAGAMENTO",
                lambda x: df_real.loc[x.index]
                .query("`Pagar?` == True")["VALOR_PAGAMENTO"]
                .sum(),
            ),
        )
        .reset_index()
    )

    dias = df_agrupado_dia["DATA_PAGAMENTO"].tolist()
    a_pagar = df_agrupado_dia["total_dia"].tolist()
    pago = df_agrupado_dia["selecionado_dia"].tolist()

    text_pagar = [form_k(v) for v in a_pagar]
    text_pago = [form_k(v) for v in pago]

    fig1 = go.Figure()
    fig1.add_trace(
        go.Bar(
            x=dias,
            y=a_pagar,
            name="Total Planilha",
            marker_color="#e74a3b",
            text=text_pagar,
            textposition="outside",
            textfont=dict(size=11),
        )
    )
    fig1.add_trace(
        go.Bar(
            x=dias,
            y=pago,
            name="Selecionado CNAB",
            marker_color="#1cc88a",
            text=text_pago,
            textposition="outside",
            textfont=dict(size=11),
        )
    )

    fig1.update_layout(
        title=dict(
            text="Evolução Diária de Pagamentos (Planilha vs CNAB)",
            font=dict(color="#4F4F4F", size=15),
            x=0.5,
        ),
        barmode="group",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
        paper_bgcolor="#F8F9FA",
        plot_bgcolor="#F8F9FA",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5
        ),
        dragmode="pan",
    )
    fig1.update_yaxes(
        fixedrange=True, range=[0, max(a_pagar + [100]) * 1.25]
    )

    st.plotly_chart(fig1, use_container_width=True, config=chart_config)

    # --- GRÁFICO 2: DESPESAS POR CATEGORIA ---
    pivot_cat = df_real.pivot_table(
        index="DATA_PAGAMENTO",
        columns="Categoria",
        values="VALOR_PAGAMENTO",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    fig2 = go.Figure()
    cores_categorias = [
        "#4e73df",
        "#36b9cc",
        "#f6c23e",
        "#858796",
        "#1cc88a",
        "#e74a3b",
    ]

    for idx, col_cat in enumerate(pivot_cat.columns):
      if col_cat != "DATA_PAGAMENTO":
        cor = cores_categorias[idx % len(cores_categorias)]
        fig2.add_trace(
            go.Bar(
                x=pivot_cat["DATA_PAGAMENTO"],
                y=pivot_cat[col_cat],
                name=str(col_cat),
                marker_color=cor,
            )
        )

    fig2.update_layout(
        title=dict(
            text="Distribuição por Categoria e Data",
            font=dict(color="#4F4F4F", size=15),
            x=0.5,
        ),
        barmode="stack",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
        paper_bgcolor="#F8F9FA",
        plot_bgcolor="#F8F9FA",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5
        ),
        dragmode="pan",
    )
    st.plotly_chart(fig2, use_container_width=True, config=chart_config)
  else:
    st.info("Aguardando dados da planilha para renderizar os gráficos.")
