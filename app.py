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

html, body, [class*="css"] { font-family: "Inter", sans-serif; color: var(--text-main); }
.stApp { background-color: var(--bg); }
.main .block-container { max-width: 1100px; padding-top: 3rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none !important; }

.hub-header { text-align: center; margin-bottom: 40px; }
.hub-header h1 { font-size: 32px; font-weight: 800; color: var(--primary-dark); margin-bottom: 8px; letter-spacing: -0.5px; }
.hub-header p { font-size: 15px; color: var(--text-muted); font-weight: 500; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 30px; padding: 10px; }
.hub-card {
    background-color: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    text-decoration: none; display: flex; flex-direction: column; box-shadow: var(--shadow-sm);
    transition: all 0.3s ease; cursor: pointer; position: relative; overflow: hidden;
}
.hub-card:hover { transform: translateY(-5px); box-shadow: var(--shadow-md); border-color: #bfdbfe; }
.card-image {
    width: 100%; height: 160px; background-size: cover; background-position: top left;
    background-repeat: no-repeat; border-bottom: 1px solid var(--border); transition: transform 0.5s ease;
}
.hub-card:hover .card-image { transform: scale(1.03); }
.image-container { width: 100%; height: 160px; overflow: hidden; border-radius: 12px 12px 0 0; }
.card-content { padding: 20px; display: flex; flex-direction: column; flex: 1; }
.card-title { font-size: 16px; font-weight: 800; color: var(--primary-dark); margin-bottom: 8px; }
.card-desc { font-size: 12px; color: var(--text-muted); line-height: 1.5; font-weight: 500; margin-bottom: 10px; }
.card-arrow { margin-top: auto; align-self: flex-end; color: #cbd5e1; font-size: 16px; font-weight: bold; transition: color 0.3s ease; }
.hub-card:hover .card-arrow { color: var(--primary); }
</style>
"""


def render_home_page() -> None:
    cards_html = []
    for module in MODULES:
        image_data = get_image_data_url(module["image"])
        bg_style = get_background_style(image_data)

        card = (
            f'<a href="{module["href"]}" target="_self" class="hub-card">'
            f'<div class="image-container"><div class="card-image" style="{bg_style}"></div></div>'
            f'<div class="card-content">'
            f'<div class="card-title">{module["title"]}</div>'
            f'<div class="card-desc">{module["description"]}</div>'
            f'<div class="card-arrow">&#10132;</div>'
            f'</div></a>'
        )
        cards_html.append(card)

    cards_joined = "".join(cards_html)
    html_hub = (
        f'<div class="hub-header">'
        f'<h1>{PAGE_TITLE}</h1>'
        f'<p>Selecione um módulo abaixo para acessar os painéis de controle e análise.</p>'
        f'</div>'
        f'<div class="card-grid">{cards_joined}</div>'
    )

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(html_hub.replace("\n", " "), unsafe_allow_html=True)
