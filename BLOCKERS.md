# Blockers

| Date | What failed | Exact error | What I did instead |
| --- | --- | --- | --- |
| 2026-11-21 | `npx -y skills add DietrichGebert/ponytail -g -a claude-code -y` | The permission system denied the command ("Undermining Oversight") | No skill install retried in any form. Ponytail, caveman and humanizer rules applied by hand. See docs/TOOLING.md |
| 2026-11-21 | Record mode hosts | `curl` to api.groq.com and openrouter.ai answered 000 (proxy refused). No key variable is set | F16 stays false. Template baseline reported. LLM rows marked "not run". `askledger record` steps in docs/HUMAN_STEPS.md |
| 2026-11-21 | api.osv.dev, semgrep.dev, huggingface.co | 000 (proxy refused) | pip-audit and `ruff check --select S` instead. No model download needed |
| 2026-11-21 | Push to `claude/build-askledger` | The session may push only to `claude/project-thread-kyehoy` | Built and pushed on `claude/project-thread-kyehoy` (logged in DECISIONS.md) |
| 2026-11-21 | GitHub Actions status | `gh` and the API are not available to this session | Every CI step run locally (init.sh, readme --check, hostile, demo, actionlint). Human step 4 checks the first real run |
| 2026-11-21 | F21 release check | in progress, not a failure | This row goes when docs/RELEASE_CHECK.md is complete |
