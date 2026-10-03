import base64
import os
import textwrap

import streamlit as st

PAGE_TITLE = "Portal Financeiro Executivo"
PAGE_ICON = "🏢"
CARD_PREVIEW_PATHS = {
    "saldos": "assets/preview_saldos.png",
    "fluxo": "assets/preview_fluxo.png",
    "pagar": "assets/preview_pagar.png",
}
MODULES = [
    {
        "title": "Dashboard de Saldos",
        "description": (
            "Visão consolidada de todas as contas bancárias, aplicações e limites de "
            "crédito em tempo real."
        ),
        "href": "Dashboard_Saldo",
        "image": CARD_PREVIEW_PATHS["saldos"],
    },
    {
        "title": "Fluxo de Caixa Analítico",
        "description": (
            "Mapeamento da origem e destino do dinheiro, geração líquida e taxa de "
            "consumo sob a ótica de caixa."
        ),
        "href": "painel_fluxo_caixa",
        "image": CARD_PREVIEW_PATHS["fluxo"],
    },
    {
        "title": "Painel de Pagamentos",
        "description": (
            "Gestão de passivos, curva ABC de fornecedores, aging de vencimentos e "
            "controle de saídas."
        ),
        "href": "painel_pagar",
        "image": CARD_PREVIEW_PATHS["pagar"],
    },
]


def get_image_data_url(file_path: str) -> str:
    """Converte uma imagem local em um data URL válido para uso em HTML/CSS."""
    fallback = "linear-gradient(135deg, #eff6ff, #bfdbfe)"

    if not file_path or not os.path.exists(file_path):
        return fallback

    try:
        with open(file_path, "rb") as image_file:
            image_bytes = image_file.read()
    except OSError:
        return fallback

    extension = os.path.splitext(file_path)[1].lower().lstrip(".")
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/{extension};base64,{encoded}"


def get_background_style(image_data: str) -> str:
    """Retorna uma propriedade de background para uso em elementos HTML."""
    if image_data.startswith("linear-gradient"):
        return f"background: {image_data};"
    return f"background-image: url('{image_data}');"


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f4f6f9;
    --surface: #ffffff;
    --primary-dark: #1e40af;
    --primary: #3b82f6;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow-sm: 0 4px 10px rgba(30, 64, 175, 0.05);
    --shadow-md: 0 10px 20px rgba(30, 64, 175, 0.12);
}

html, body, [class*="css"] {
    font-family: "Inter", sans-serif;
    color: var(--text-main);
}

.stApp {
    background-color: var(--bg);
}

.main .block-container {
    max-width: 1100px;
    padding-top: 3rem;
    padding-bottom: 2rem;
}

header[data-testid="stHeader"] {
    display: none !important;
}

[data-testid="stSidebar"] {
    display: none !important;
}

.hub-header {
    text-align: center;
    margin-bottom: 40px;
}

.hub-header h1 {
    font-size: 32px;
    font-weight: 800;
    color: var(--primary-dark);
    margin-bottom: 8px;
    letter-spacing: -0.5px;
}

.hub-header p {
    font-size: 15px;
    color: var(--text-muted);
    font-weight: 500;
}

.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 30px;
    padding: 10px;
}

.hub-card {
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    text-decoration: none;
    display: flex;
    flex-direction: column;
    box-shadow: var(--shadow-sm);
    transition: all 0.3s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.hub-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-md);
    border-color: #bfdbfe;
}

.card-image {
    width: 100%;
    height: 160px;
    background-size: cover;
    background-position: top left;
    background-repeat: no-repeat;
    border-bottom: 1px solid var(--border);
    transition: transform 0.5s ease;
}

.hub-card:hover .card-image {
    transform: scale(1.03);
}

.image-container {
    width: 100%;
    height: 160px;
    overflow: hidden;
    border-radius: 12px 12px 0 0;
}

.card-content {
    padding: 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
}

.card-title {
    font-size: 16px;
    font-weight: 800;
    color: var(--primary-dark);
    margin-bottom: 8px;
}

.card-desc {
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.5;
    font-weight: 500;
    margin-bottom: 10px;
}

.card-arrow {
    margin-top: auto;
    align-self: flex-end;
    color: #cbd5e1;
    font-size: 16px;
    font-weight: bold;
    transition: color 0.3s ease;
}

.hub-card:hover .card-arrow {
    color: var(--primary);
}
</style>
"""


def render_module_cards() -> None:
    """Renderiza o hub principal com links para os módulos do portal."""
    cards_html = []

    for module in MODULES:
        image_data = get_image_data_url(module["image"])
        cards_html.append(
            f"""
            <a href="{module['href']}" target="_self" class="hub-card">
                <div class="image-container">
                    <div class="card-image" style="{get_background_style(image_data)}"></div>
                </div>
                <div class="card-content">
                    <div class="card-title">{module['title']}</div>
                    <div class="card-desc">{module['description']}</div>
                    <div class="card-arrow">➔</div>
                </div>
            </a>
            """
        )

    html_hub = f"""
    <div class="hub-header">
        <h1>{PAGE_TITLE}</h1>
        <p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>
    </div>
    <div class="card-grid">
        {''.join(cards_html)}
    </div>
    """

    st.markdown(textwrap.dedent(CSS), unsafe_allow_html=True)
    st.markdown(textwrap.dedent(html_hub), unsafe_allow_html=True)


def main() -> None:
    """Ponto de entrada do portal financeiro."""
    st.set_page_config(page_title=PAGE_TITLE, layout="wide", page_icon=PAGE_ICON)
    render_module_cards()


if __name__ == "__main__":
    main()