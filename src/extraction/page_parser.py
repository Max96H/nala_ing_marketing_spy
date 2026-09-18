from bs4 import BeautifulSoup


def extract_page(html: str) -> dict:

    soup = BeautifulSoup(html, "lxml")

    title = None

    if soup.title:
        title = soup.title.get_text(" ", strip=True)

    meta_description = None

    meta = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta:
        meta_description = meta.get("content")

    headings = [
        h.get_text(" ", strip=True)
        for h in soup.find_all(["h1", "h2", "h3"])
    ]

    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
    ]

    links = []

    for a in soup.find_all("a", href=True):

        links.append({
            "text": a.get_text(" ", strip=True),
            "href": a["href"],
        })

    images = []

    for img in soup.find_all("img"):

        images.append({
            "src": img.get("src"),
            "alt": img.get("alt"),
        })

    return {
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "paragraphs": paragraphs,
        "links": links,
        "images": images,
    }

def extract_main_text(html: str) -> str:

    soup = BeautifulSoup(html, "lxml")

    for element in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
        element.decompose()

    return soup.get_text(
        " ",
        strip=True
    )