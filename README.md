# XSTAR Global Automotive News Agent — Keyless Research

**No Serper or OpenRouter keys required.** The default research mode uses public GDELT DOC API and Google News RSS for discovery, requests the original article, and requires a publication date in the requested interval. The app preserves candidate rows for human review; it does not claim that RSS snippets or automated excerpts are fully verified.

## Use
1. Open the Streamlit app and choose start/end dates.
2. Optionally upload your reference Excel or paste article titles/URLs.
3. Keep **免费摘录（无需任何 API Key）** and click **免费搜索 / 补充研究**.
4. Review candidates and their original URLs, publication dates, evidence, access status and scores. **Select** verified articles manually; the free mode does not invent Chinese summaries or automatically approve extracted claims.
5. Edit Chinese titles, tags and summaries in the data editor. Preview and export Outlook HTML and Excel.

## Optional local AI
Choose **Ollama（自建模型）** and supply the URL of your own securely hosted Ollama server and model name. It calls Ollama `/api/chat` with JSON output. It does not use OpenRouter or Serper. Streamlit Cloud cannot access your laptop's `localhost` Ollama; a reachable private service is necessary. Do not publicly expose an unauthenticated Ollama endpoint.

## Files
- `app.py`: Streamlit app and export UI
- `free_research.py`: free GDELT and Google News RSS discovery; deterministic fallback; optional Ollama
- `searching_rules/config.json`: topics, markets, source hierarchy and search budgets
- `searching_rules/RESEARCH_RULES.md`: editorial rules
- `templates/HTML_Reference.html`: Outlook-compatible base HTML
- `templates/XSTAR_Excel_Master.xlsx`: required for exporting Excel when the user did not upload an original Excel. **This binary template must be uploaded manually to the repository.**

## Limitations
- Free sources can throttle requests, omit local-language news or redirect to inaccessible publisher pages. Results are not exhaustive.
- Extractive fallback is not a full LLM. It cannot guarantee Chinese translation, independently validate figures or replace human editorial review.
- This repository's current HTML reference is not proven pixel-identical to the supplied XSTAR Outlook example. The original HTML template and a visual regression test are still needed.
- Never commit API keys, private model credentials, or paid article content.
