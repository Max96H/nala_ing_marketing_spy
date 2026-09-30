const SECTIONS = [
  {
    title: 'Is this trustworthy? (LLM-generated fields)',
    body: [
      `Tone, value proposition, and topics come from an LLM reading each page's text — so yes, that part could in principle be wrong or invented. Two different safeguards handle that, matched to what each part of the tool actually does:`,
    ],
    bullets: [
      `Extraction (tone, value proposition): the model is required to quote an exact, verbatim snippet from the source text backing each judgment. That quote is checked against the real page text after the call — if it doesn't actually appear there, it's flagged as unverified rather than silently trusted. This is a real substring check, not a cosmetic field.`,
      `Chat answers: a conversational answer can't be checked the same mechanical way, so the system prompt instead requires every claim to name which bank/page it comes from, forbids relying on general brand reputation, and requires an explicit "not in the data" answer when the context doesn't cover the question. Temperature is kept low for both extraction and chat, favoring consistency over creativity.`,
    ],
  },
  {
    title: 'What is deterministic vs. LLM-based',
    body: [
      `Not everything here comes from an LLM. Colour palette, image count, CTA count, and whether a numeric offer appears are all computed directly from the page's HTML/screenshot — no model involved, nothing to hallucinate. Only tone, value proposition, and topics are LLM-generated, and those are the ones with the verification described above.`,
    ],
  },
  {
    title: 'Radar dimensions — what each one actually measures',
    body: [
      `The brief asks for five dimensions: tone & messaging, visuals & illustrations, colour & design, layout & structure, and topics & value proposition. These aren't directly measurable as single numbers, so each is proxied by something concrete:`,
    ],
    bullets: [
      `Promotional intensity — proxy for tone & messaging. Share of pages with a numeric offer (€, %, a concrete number) — a deterministic, LLM-free signal of how promotional a bank's messaging leans.`,
      `Visual richness — proxy for visuals & illustrations. Average image count per page.`,
      `Colour vibrancy — proxy for colour & design. Average saturation across each page's extracted dominant colours.`,
      `Content density — proxy for layout & structure. Average word count per page.`,
      `Topic diversity — proxy for topics & value proposition. Distinct topics used, relative to page count.`,
    ],
  },
  {
    title: 'Positioning map',
    body: [
      `Each page's tone, value proposition, and topics are combined into one text blob, converted to TF-IDF vectors, then reduced to two dimensions with PCA. Distance on the map reflects textual similarity in how campaigns are described — not a literal, physical, or brand-strength metric. Two pages landing close together means their tone/value-proposition/topic wording came out similar, nothing more.`,
    ],
  },
  {
    title: 'Gap finder',
    body: [
      `Flags topics that appear on at least one competitor's page but never on ING's. This is a candidate list for a human to look at, not an automatic recommendation — a topic showing up here doesn't mean ING should copy it, just that it's worth a look.`,
    ],
  },
  {
    title: 'Compare Products — UI/UX score and recommendations',
    body: [
      `Each product category lets you pick which of ING's pages to anchor the comparison on, then shows the best (most substantial) page from each competitor — "best" is judged by content length, a proxy for the real flagship page rather than a thin stub the classifier happened to catch.`,
      `The UI/UX score (0-10) comes from a dedicated, deterministic pipeline (ux_score.py) — no LLM involved, so nothing here can be hallucinated. It's built from six sub-scores, each grounded in a named, established principle rather than an arbitrary number: value clarity (2 pts — a concrete, quantified offer reduces ambiguity), CTA clarity (2 pts — a clear call-to-action helps orientation, but too many competing ones score lower per Hick's Law), content hierarchy (1 pt — a headline plus a supporting subtitle, per Nielsen's heuristics), scannability (1 pt — body text in a healthy length range), visual balance (2 pts — supporting imagery without an overwhelming wall of it, Nielsen's "aesthetic and minimalist design"), and accessibility contrast (2 pts — the WCAG 2.1 contrast ratio between the page's two most dominant colours, scored against the same 4.5:1 / 3:1 thresholds real accessibility audits use). Every sub-score is stored, not just the total, so any number on screen can be traced back to exactly why it landed where it did.`,
      `The "Recommendation for ING" column is rule-based, not LLM-generated — it compares a competitor's real score and specific signals (offer, CTA) against the currently selected ING product and phrases the gap cautiously. It only appears when a competitor genuinely outscores ING; otherwise it says plainly that no action is needed.`,
    ],
  },
  {
    title: 'Scope and legal grounds',
    body: [
      `Every bank's robots.txt was checked before scraping, and only pages/paths it permits are crawled. Data collection is limited to publicly available marketing pages — no personal data, no login-gated content, no bypassing of access restrictions.`,
    ],
  },
]

export default function Methodology() {
  return (
    <div>
      {SECTIONS.map((section) => (
        <div className="panel" key={section.title}>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>{section.title}</h2>
          {section.body.map((p, i) => (
            <p key={i} style={{ color: 'var(--color-ink-soft)', fontSize: 14, lineHeight: 1.6, margin: '0 0 10px' }}>
              {p}
            </p>
          ))}
          {section.bullets && (
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {section.bullets.map((b, i) => (
                <li key={i} style={{ color: 'var(--color-ink-soft)', fontSize: 14, lineHeight: 1.6, marginBottom: 8 }}>
                  {b}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  )
}