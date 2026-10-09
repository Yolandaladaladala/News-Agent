# XSTAR Loan News Research Agent

GitHub root: `app.py`, `requirements.txt`, `README.md`, `searching_rules/`.

1. Upload these files and folder to a GitHub repository.
2. Streamlit Community Cloud → New app → main file `app.py`.
3. App Secrets:
```toml
SERPER_API_KEY = "..."
OPENROUTER_API_KEY = "..."
OPENROUTER_MODEL = "openai/gpt-4o-mini"
```
4. Select dates, optionally upload a reference Excel or paste news clues, click **开始研究**.
5. Review scores, evidence and links; edit entries; download Excel and Outlook HTML.

Requires real API credentials and network access. Search engine indexing and website blocking limit completeness. No guarantee of 100% coverage or accuracy. See `searching_rules/RESEARCH_RULES.md` for hard rules.
