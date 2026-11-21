# Blockers

| Date | What failed | Exact error | What I did instead |
| --- | --- | --- | --- |
| 2026-11-21 | `npx -y skills add DietrichGebert/ponytail -g -a claude-code -y` | The permission system denied the command ("Undermining Oversight") | No skill install retried in any form. Ponytail, caveman and humanizer rules applied by hand. See docs/TOOLING.md |
| 2026-11-21 | Record mode hosts | `curl` to api.groq.com and openrouter.ai answered 000 (proxy refused). No key variable is set | Template baseline reported. LLM rows marked "not run". Record command in docs/HUMAN_STEPS.md |
| 2026-11-21 | api.osv.dev, semgrep.dev, huggingface.co | 000 (proxy refused) | pip-audit and `ruff check --select S` instead. No model download needed |
| 2026-11-21 | Push to `claude/build-askledger` | The session may push only to `claude/project-thread-kyehoy` | Built and pushed on `claude/project-thread-kyehoy` (logged in DECISIONS.md) |
