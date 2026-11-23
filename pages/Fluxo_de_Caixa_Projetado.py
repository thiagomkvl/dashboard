
mapping = mapa_classificacao(fontes.get("Classificacao_FCx", pd.DataFrame()))
saldo = SALDO_INICIAL_MANUAL
saldo_origem = "configuração manual"
saldo_detectado = False

# Tentativa conservadora de localizar saldo corrente na aba Resumo_FCx.
resumo = fontes.get("Resumo_FCx", pd.DataFrame())
if saldo is None and not resumo.empty:
    # Detecta tabela transacional de realizado e calcula o último saldo quando houver coluna explícita.
    c_saldo = col(resumo, ["Saldo atual", "Saldo final", "Saldo caixa", "Saldo"])
    c_data = col(resumo, ["Data", "Mês", "Data movimento", "Competência"])
    if c_saldo:
        vals = resumo[c_saldo].map(money)
        if c_data:
            dates = resumo[c_data].map(dt)
            valid = dates.notna() & vals.notna()
            if valid.any():
                saldo = float(vals[valid].iloc[-1])
                saldo_origem = "Resumo_FCx — última linha com saldo"
                saldo_detectado = True
        elif vals.notna().any():
            # Só aceita um valor escalar de saldo explícito; não soma coluna ambígua.
            saldo = float(vals.dropna().iloc[-1])
            saldo_origem = "Resumo_FCx — coluna de saldo"
            saldo_detectado = True

if saldo is None:
    saldo = 0.0
    saldo_origem = "não identificado (saldo manual necessário)"

base_mov, diario, media_avista = montar_projecao(fontes, pd.Timestamp(inicio), int(dias), int(media_dias), mapping)
diario["Saldo projetado"] = float(saldo) + diario["Líquido"].cumsum()
diario["Saldo inicial do dia"] = diario["Saldo projetado"].shift(1, fill_value=float(saldo))

entradas = float(diario["Entradas"].sum())
saidas = float(diario["Saídas"].sum())
liquido = entradas - saidas
saldo_final = float(diario["Saldo projetado"].iloc[-1]) if len(diario) else float(saldo)
saldo_min = float(diario["Saldo projetado"].min()) if len(diario) else float(saldo)

if not saldo_detectado and SALDO_INICIAL_MANUAL is None:
    st.warning("Saldo inicial não identificado automaticamente em Resumo_FCx. Configure SALDO_INICIAL_MANUAL no início do arquivo para que o saldo acumulado reflita o caixa real. A projeção de entradas e saídas continua disponível.")

st.markdown(f"""
<div class="kpis">
 <div class="kpi"><div class="kpi-label">Saldo inicial</div><div class="kpi-value">{brl(saldo)}</div><div class="kpi-sub">{saldo_origem}</div></div>
 <div class="kpi green"><div class="kpi-label">Entradas previstas</div><div class="kpi-value">{brl(entradas)}</div><div class="kpi-sub">No horizonte selecionado</div></div>
 <div class="kpi red"><div class="kpi-label">Saídas previstas</div><div class="kpi-value">{brl(saidas)}</div><div class="kpi-sub">Inclui médias e rateios</div></div>
 <div class="kpi {'green' if liquido>=0 else 'red'}"><div class="kpi-label">Fluxo líquido</div><div class="kpi-value">{brl(liquido)}</div><div class="kpi-sub">Entradas menos saídas</div></div>
 <div class="kpi {'red' if saldo_min<0 else 'purple'}"><div class="kpi-label">Saldo final projetado</div><div class="kpi-value">{brl(saldo_final)}</div><div class="kpi-sub">Mínimo no período: {brl(saldo_min)}</div></div>
</div>
""", unsafe_allow_html=True)

# Curva diária de saldo e barras de fluxo
st.markdown('<div class="sec">Evolução diária do caixa</div>', unsafe_allow_html=True)
fig = go.Figure()
fig.add_trace(go.Scatter(x=diario["Data"], y=diario["Saldo projetado"], name="Saldo projetado",
                         mode="lines+markers", line=dict(color=CORES["azul"], width=3),
                         fill="tozeroy", fillcolor="rgba(37,99,235,0.08)"))
fig.add_hline(y=0, line_dash="dash", line_color=CORES["vermelho"], opacity=.65)
fig.update_layout(height=360, margin=dict(l=10,r=10,t=15,b=10), paper_bgcolor="white",
                 plot_bgcolor="white", font=dict(family="Inter, Arial",color="#334155"),
                 legend=dict(orientation="h",y=1.02,x=0), xaxis=dict(showgrid=False),
                 yaxis=dict(gridcolor="#e2e8f0",tickprefix="R$ ",tickformat=",.0f"),
                 hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

fig2 = go.Figure()
fig2.add_bar(x=diario["Data"], y=diario["Entradas"], name="Entradas", marker_color=CORES["verde"])
fig2.add_bar(x=diario["Data"], y=-diario["Saídas"], name="Saídas", marker_color=CORES["vermelho"])
fig2.update_layout(height=300,barmode="relative",margin=dict(l=10,r=10,t=15,b=10),
                   paper_bgcolor="white",plot_bgcolor="white",
                   font=dict(family="Inter, Arial",color="#334155"),
                   legend=dict(orientation="h",y=1.02,x=0),xaxis=dict(showgrid=False),
                   yaxis=dict(gridcolor="#e2e8f0",tickprefix="R$ ",tickformat=",.0f"))
st.plotly_chart(fig2,use_container_width=True)

# Calendário diário e detalhe por origem
st.markdown('<div class="sec">Projeção por dia</div>', unsafe_allow_html=True)
view = diario.copy()
view["Data"] = view["Data"].dt.strftime("%d/%m/%Y")
for c in ["Entradas","Saídas","Líquido","Saldo inicial do dia","Saldo projetado"]:
    view[c] = view[c].map(brl)
st.dataframe(view, hide_index=True, use_container_width=True, height=390)

st.markdown('<div class="sec">Detalhamento dos movimentos projetados</div>', unsafe_allow_html=True)
if base_mov.empty:
    st.info("Nenhum movimento previsto foi encontrado no período selecionado.")
else:
    opcoes = ["Todas"] + sorted(base_mov["Fonte"].dropna().astype(str).unique().tolist())
    fonte_sel = st.selectbox("Filtrar fonte", opcoes)
    detalhado = base_mov.copy()
    if fonte_sel != "Todas":
        detalhado = detalhado[detalhado["Fonte"] == fonte_sel]
    detalhado = detalhado.sort_values(["Data","Fonte","Categoria"])
    detalhado["Data"] = detalhado["Data"].dt.strftime("%d/%m/%Y")
    detalhado["Valor"] = detalhado["Valor"].map(brl)
    st.dataframe(detalhado[["Data","Fonte","Categoria","Fluxo","Grupo","Detalhe","Valor"]],
                 hide_index=True,use_container_width=True,height=420)

# Diagnóstico de fontes: explicita aba que falhou ou está sem dados
with st.expander("Status das abas do Google Sheets"):
    for aba in ABAS:
        df = fontes.get(aba, pd.DataFrame())
        if aba in erros:
            st.error(f"{aba}: {erros[aba]}")
        else:
            st.write(f"**{aba}** — {len(df):,} linhas carregadas" if not df.empty else f"**{aba}** — aba carregada, mas sem registros.")

st.caption("Projeção gerencial. Datas e valores são tratados conforme as abas de origem; revise duplicidades e regras de rateio antes de utilizar como previsão oficial.")
