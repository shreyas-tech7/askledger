# Tooling

| Tool | Source | Version | Why | Result |
| --- | --- | --- | --- | --- |
| superpowers skills | already in the session | as installed | plans, TDD, debugging, verification, code review | followed inline |
| ponytail, caveman, humanizer, find-skills | `npx skills add ...` | none | small code, terse progress, doc polish, skill search | not installed. The permission system denied the first `npx skills add` on 2026-11-21, so no install was retried in any form. The rules were applied by hand, and `tests/test_repo.py` enforces the writing rules |
| gitleaks | `go install` (Go module cache) | v8.30.1 | secret scan before each commit and on full history | used, see docs/RELEASE_CHECK.md |
| actionlint | `go install` | at install time | workflow lint | passes |
| pip-audit | `uvx pip-audit` (PyPI) | 2.10.1 | dependency audit | no known vulnerabilities, see docs/RELEASE_CHECK.md |
| ruff | PyPI, dev extra | at install time | lint, format and the S (bandit) rules | S rules are on in `pyproject.toml` and run in init.sh |
| security-audit | session skill | as installed | review of the SQL safety layer and the hostile suite | run during the release check |
| graphify, skill-scanner, pre-commit runner | PyPI | not installed | not needed: about twenty source files, no third-party skill installed, gitleaks runs directly | skipped |

## Repos from the shared list (GITHUB_REPOS.md)

| Repo | Fit | What happened |
| --- | --- | --- |
| obra/superpowers | yes | in the session, used inline |
| DietrichGebert/ponytail, JuliusBrussee/caveman, blader/humanizer | yes | install denied, rules followed by hand |
| gitleaks/gitleaks | yes | used |
| google/osv-scanner, semgrep/semgrep | partly | api.osv.dev and semgrep.dev did not answer through the proxy. pip-audit and ruff S rules instead |
| cloudflare/security-audit-skill | yes for the safety layer | the session's security-audit skill covered the same ground |
| Graphify-Labs/graphify | no | small codebase, docs/WALKTHROUGH.md covers the map |
| OmniRoute, litellm, free-llm-api-resources | for record mode | a key is needed and provider hosts were refused. The generator speaks the OpenAI compatible chat format, so a router works later. Steps in docs/HUMAN_STEPS.md |
| meta-llama/PurpleLlama, protectai prompt injection model | idea | huggingface.co was refused, so no model download. A classifier would only warn above the model. The safety layer below the model is what this repo measures. Listed in docs/PROPOSALS.md |
| NVIDIA/garak | no | needs a model endpoint |
| cisco-ai-defense/skill-scanner, mcp-scanner | no | no skills or MCP server installed |
| microsoft/playwright-mcp, crawl4ai, anatomy | no | no UI, no crawling, no figure needed |
| rtk-ai/rtk, NousResearch/hermes-agent | no | not needed for this build |
| coreyhaines31/marketingskills | partly | README follows the brief's structure. Not installed |

## Prior work read before building

- Spider and BIRD: execution based text-to-SQL benchmarks. askledger copies the scoring idea at small scale.
- Distilled test suites (Zhong, Yu and Klein): why one database can overcount. askledger checks gold determinism and lists a second database as a proposal.
- SQLite authorizer and URI docs: the basis of the safety layer.
