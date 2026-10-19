def melt_matriz(raw, col_label_idx, header_row_idx, start_col_idx, tipo, ano_ref=None):
    """
    Converte matriz mensal em formato longo.
    Suporta cabeçalhos de seção no meio da aba (ex.: Captações com maio|setembro|Total geral).
    Colunas de total NUNCA entram como mês.
    """
    cols_out = ["Ref", "Categoria", "Valor", "Tipo"]
    if raw is None or raw.empty:
        return pd.DataFrame(columns=cols_out)

    ano = ano_ref or ANO_REF
    col_headers = [str(c) if c is not None else "" for c in raw.columns]
    data = [col_headers] + raw.astype(object).where(pd.notna(raw), None).values.tolist()
    n_rows = len(data)
    n_cols = max((len(r) for r in data), default=0)
    if n_cols == 0:
        return pd.DataFrame(columns=cols_out)

    grid = []
    for r in data:
        row = list(r) + [None] * (n_cols - len(r))
        grid.append(row[:n_cols])

    def montar_mapa_mes(header_row):
        """Mapeia colunas → mês; ignora total / vazio."""
        m = {}
        for j in range(start_col_idx, n_cols):
            h = header_row[j] if j < len(header_row) else None
            nt = normalizar(h) if h is not None else ""
            if not nt or "total" in nt or nt in SKIP_HEADER:
                continue
            ref = parse_mes_header(h, ano)
            if ref is not None:
                m[j] = ref
        return m

    def score_header(row):
        return len(montar_mapa_mes(row))

    # mapa inicial (cabeçalho global)
    hr0 = 0
    best_s = score_header(grid[0])
    for i in range(min(8, n_rows)):
        s = score_header(grid[i])
        if s > best_s:
            hr0, best_s = i, s
    if 0 <= header_row_idx < n_rows and score_header(grid[header_row_idx]) >= 3:
        if score_header(grid[header_row_idx]) >= best_s:
            hr0 = header_row_idx

    mapa_atual = montar_mapa_mes(grid[hr0])
    if not mapa_atual:
        return pd.DataFrame(columns=cols_out)

    li = col_label_idx if 0 <= col_label_idx < n_cols else 0
    reg = []

    for i in range(hr0 + 1, n_rows):
        row = grid[i]

        # Nova linha de cabeçalho de seção? (ex.: "maio | setembro | Total geral")
        s_local = score_header(row)
        if s_local >= 2:
            # só troca o mapa se parecer cabeçalho (poucos labels de categoria / muitos meses)
            cat_test = row[li] if li < len(row) else None
            ncat_test = normalizar(cat_test) if cat_test is not None else ""
            # cabeçalho de meses costuma ter "mês", nome de mês na linha, ou label vazio/captações/pmts
            if (
                s_local >= 2
                and (
                    not ncat_test
                    or ncat_test in ("mes", "mês", "captacoes", "captacao", "pmts", "alugueis", "outras receitas")
                    or ncat_test in SKIP_LABELS
                    or parse_mes_header(cat_test, ano) is not None
                )
            ):
                novo = montar_mapa_mes(row)
                if novo:
                    mapa_atual = novo
                continue

        cat = row[li] if li < len(row) else None
        if cat is None or (isinstance(cat, float) and pd.isna(cat)):
            continue
        cat_s = str(cat).strip()
        ncat = normalizar(cat_s)
        if not ncat or ncat in SKIP_LABELS or ncat.startswith("total"):
            continue
        if "adiantamento fornecedores" in ncat and "total" in ncat:
            continue
        # ignora linhas que são só título de seção
        if ncat in ("pmts", "captacoes", "captacao", "alugueis", "outras receitas", "convenio", "particular"):
            # só pula se não houver valor numérico na linha
            if not any(abs(limpa_valor(row[j] if j < len(row) else 0)) > 0.005 for j in mapa_atual):
                continue

        for j, ref in mapa_atual.items():
            val = limpa_valor(row[j] if j < len(row) else 0)
            if abs(val) <= 0.005:
                continue
            reg.append({"Ref": ref, "Categoria": cat_s, "Valor": val, "Tipo": tipo})

    if not reg:
        return pd.DataFrame(columns=cols_out)
    return pd.DataFrame(reg)[cols_out]
