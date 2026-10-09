---
name: xstar-news
description: Research and publish XSTAR automotive industry intelligence using verifiable multilingual sources and user-controlled editorial revisions.
---

# Input
Date interval (inclusive), optional clues/URLs, optional model credentials.

# Research
1. Search in Thai, Chinese, English, Japanese, Korean and other local languages according to `searching_rules/config.json`.
2. Target 80 unique candidate events, but report the actual count. Do not fill with weak or invented stories.
3. Prefer central banks, regulators, official announcements and established publicly accessible news. Resolve publisher URL when possible.
4. Treat discovery date as a hint. A confirmed date requires the original article date.
5. Verify figures, currencies and company names against article evidence. Unresolved facts must remain Pending.
6. Score: business relevance 30, industry impact 25, source credibility 20, timeliness 15, actionability 10.
7. Present up to 30 highest-value candidates, with stable IDs, score, status and source.

# Editing
- Accept unrestricted natural-language instructions.
- Deterministic fallback handles explicit numeric deletion only.
- Complex modifications require a connected LLM; validate every structured operation against existing IDs.
- For supplements, search only requested topics; never fabricate additions.
- Keep untouched rows and previous editorial decisions.
- Deletion must never invoke news discovery.

# Publishing
- Generate Excel and Outlook HTML from the same approved editorial state.
- Prefer uploaded original Excel master; without it, identify Excel as simplified fallback.
- HTML reference is not guaranteed pixel-identical to user's original until validated.
- Report inaccessible articles and unresolved verification openly.

# Acceptance
- No API key in code or logs.
- No research call when deleting IDs.
- Invalid ID fails without mutation.
- Missing 80 candidates is a coverage warning, not an exception or fabricated output.
- Both export files should open, and selected rows should match.
