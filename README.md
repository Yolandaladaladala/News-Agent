# XSTAR Global Automotive News Agent

Streamlit entrypoint: `app.py`. This repository is the only target for these changes.

## Inputs
- Required: start date and end date for research.
- Optional: upload an existing XSTAR Excel workbook with `meta` and `news` sheets.
- Optional: paste one headline, article URL, WeChat article, Xiaohongshu lead, or industry report clue per line.
- Optional: issue label.
- API research only: each user enters their own Serper and OpenRouter API keys in the Streamlit sidebar.

## Modes
1. **Excel-only**: Upload Excel, click **加载 Excel 并立即预览**, edit news, preview HTML, export Excel and HTML. No API key is required.
2. **AI research**: Select dates, optionally add clues or Excel, enter your own keys, click **AI 搜索 / 补充研究**, review evidence and candidate selection, export.
3. **Human editorial review**: News without verifiable source dates or locatable evidence remains unselected by default. User-imported news is preserved, but is not automatically AI-verified.

## Files
- `app.py`: Streamlit app, research, editing, preview and export.
- `searching_rules/config.json`: research settings.
- `searching_rules/RESEARCH_RULES.md`: editorial requirements.
- `templates/HTML_Reference.html`: HTML structure used by the app.
- `templates/XSTAR_Excel_Master.xlsx`: **required for Excel export when no workbook was uploaded**. Upload the original XSTAR workbook here to preserve its existing format.

## Important limitations
- The HTML reference is an Outlook-compatible baseline, **not a pixel-identical reproduction of an original report**. The original Outlook HTML generator needs a dedicated regression test before exact-match claims.
- Source numeric matching is only a conservative validation gate, not independent fact-checking.
- Search coverage is limited by indexing, paywalls, access restrictions and API budget.
- A complete live research and Outlook rendering acceptance test requires real user API credentials and a reference HTML artifact.
- Never commit API keys or put them in Streamlit Secrets for a bring-your-own-key deployment.

## Deployment
Streamlit Community Cloud → repository `Yolandaladaladala/News-Agent` → branch `main` → entrypoint `app.py`. Keep `requirements.txt` at repository root.
