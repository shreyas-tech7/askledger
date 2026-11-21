# Environment

Probed on 2026-11-21 with `curl -sS -o /dev/null -w '%{http_code}' -m 10 <url>`.

| Host | Answer | Used for |
| --- | --- | --- |
| https://pypi.org/pypi/askledger/json | 404 (reachable, name free) | Name check |
| https://registry.npmjs.org/askledger | 404 (reachable, name free) | Name check |
| https://huggingface.co | 000 (proxy refused) | Not needed |
| https://api.groq.com/openai/v1/models | 000 (proxy refused) | Record mode. Blocked |
| https://openrouter.ai/api/v1/models | 000 (proxy refused) | Record mode. Blocked |
| https://api.osv.dev | 000 (proxy refused) | Not used. pip-audit instead |
| https://semgrep.dev | 000 (proxy refused) | Not used. ruff S rules instead |
| https://agentskills.io | 000 (proxy refused) | Not used |
| https://raw.githubusercontent.com/cheahjs/free-llm-api-resources/main/README.md | 404 | Free limits list. Not read |

Machine: Intel(R) Xeon(R) Processor @ 2.30GHz, 4 cores, Python 3.13.18 locally, SQLite 3.45.1, uv 0.11.32. CI uses Python 3.11.
No provider key variables were set (`GROQ_API_KEY`, `OPENROUTER_API_KEY` absent).
