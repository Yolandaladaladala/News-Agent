# XSTAR News Agent — Execution Contract

Read `skills/xstar-news/SKILL.md` before changing research, editorial or publishing behavior.

Do not claim ChatGPT-level analysis in the keyless mode: it is deterministic extraction, not a language model. BYOK OpenAI-compatible endpoints and self-hosted Ollama are optional.

Workflow: multilingual discovery → deduplicate → verify original publication date and accessible article evidence → score → Top 30 shortlist → natural-language edits → Excel + Outlook HTML.

Never fabricate missing candidates to reach 80. Never silently label extracted content as verified. Preserve stable news IDs during edits. Search only for new user-specified topics during supplementation. Never persist or log API keys.

Before releasing: run `python -m compileall -q app.py free_research.py agent_workflow.py model_gateway.py` and `python -m unittest discover -s tests -v`. Do not ask the user to spend API tokens to test basic Python correctness. Report any failed checks and template fidelity gaps.
