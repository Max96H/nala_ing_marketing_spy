def extract_page(page) -> dict:
    """
    Extract structured information directly from a Playwright page.

    The page has already been loaded and rendered by Playwright.

    Missing HTML elements are handled gracefully.
    """

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title = page.title()

    # --------------------------------------------------------
    # META DESCRIPTION
    # --------------------------------------------------------

    meta_description = None

    meta = page.locator(
        'meta[name="description"]'
    )

    if meta.count() > 0:
        meta_description = meta.first.get_attribute(
            "content"
        )

    # --------------------------------------------------------
    # HEADINGS
    # --------------------------------------------------------

    headings = page.locator(
        "h1, h2, h3"
    ).all_inner_texts()

    headings = [
        heading.strip()
        for heading in headings
        if heading.strip()
    ]

    # --------------------------------------------------------
    # PARAGRAPHS
    # --------------------------------------------------------

    paragraphs = page.locator(
        "p"
    ).all_inner_texts()

    paragraphs = [
        paragraph.strip()
        for paragraph in paragraphs
        if paragraph.strip()
    ]

    # --------------------------------------------------------
    # LINKS
    # --------------------------------------------------------

    links = []

    link_elements = page.locator(
        "a[href]"
    )

    for i in range(
        link_elements.count()
    ):

        link = link_elements.nth(i)

        links.append({
            "text": link.inner_text().strip(),
            "href": link.get_attribute("href"),
        })

    # --------------------------------------------------------
    # IMAGES
    # --------------------------------------------------------

    images = []

    image_elements = page.locator(
        "img"
    )

    for i in range(
        image_elements.count()
    ):

        image = image_elements.nth(i)

        images.append({
            "src": image.get_attribute("src"),
            "alt": image.get_attribute("alt"),
        })

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "paragraphs": paragraphs,
        "links": links,
        "images": images,
    }