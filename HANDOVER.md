# Handover

For the next session or person who picks this up.

- Branch: `claude/project-thread-kyehoy` on `shreyas-tech7/askledger`, merged into `main`.
- Start with `./init.sh`. Every test is offline.
- What works: database, frozen questions, safety layer, hostile suite, linking, template baseline, LLM replay and record (tested against a fake local server), repair loop, simulated-fault study, CLI, README and results page written from `results/*.json`.
- What is open: a real model run (F16, blocked on network and key). See docs/HUMAN_STEPS.md step 10.
- If you change code that moves a number, run `askledger eval` then `askledger readme`, and commit `results/`, `README.md` and `docs/index.html` together.
- Do not touch `questions.jsonl` or `hostile.jsonl`. They are frozen.
