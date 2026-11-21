# Contributing

Thanks for looking. askledger is small on purpose, so changes should stay small too.

## Set up

```bash
./init.sh
```

It makes a virtual environment, installs the package with its test tools, runs ruff, checks links and runs every test offline. The tests block the network, so a test that needs the internet fails.

## Rules

- Do not edit `src/askledger/data/questions.jsonl`, `hostile.jsonl` or any gold SQL to make a score go up. The questions are frozen and a test checks their hash.
- Do not type numbers into the README. Run `askledger eval` and then `askledger readme`. A test fails if the README and `results/*.json` disagree.
- Templates come from dev questions only. Do not read the held-out questions when you tune them.
- Keep both the read-only connection and the authorizer on in `safety.run`. Only tests turn a layer off, through `safety.run_layers`.
- Every subprocess call needs a timeout. Tests that write files use `tmp_path`.
- Run `gitleaks git --pre-commit --redact --staged --verbose` before you commit.

## Adding an attack to the hostile suite

Add a row to `scripts/write_hostile.py` with the attack type, the question, the SQL a model might write and the block reason you expect. Run the script, then `./init.sh`. If the new attack gets through, that is a real finding: open an issue before you change the safety layer.

## Recording a model

See "Run it in 10 minutes" in the README. Commit the fixtures in `fixtures/llm/<model>/`, never a key.
