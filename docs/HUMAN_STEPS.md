# Human steps

Only Shreyas can do these. Do them in order.

Release commit: cf3d8a1348cda80f0c51602c67bfc7c3cb15dc72 on branch `claude/project-thread-kyehoy`.

1. Open a pull request from `claude/project-thread-kyehoy` into `main` on GitHub. Read the diff. Merge with a merge commit, so the release commit stays in the history of `main`. The project coordinator may already have done this.
2. Create the tag on the release commit. Either run `git fetch origin`, then `git tag -a v0.1.0-rc1 cf3d8a1348cda80f0c51602c67bfc7c3cb15dc72 -m "Release candidate 1"`, then `git push origin v0.1.0-rc1`, or create a pre-release with that tag on the GitHub releases page.
3. Run the secret scan once more: `gitleaks git -v .` in a fresh clone.
4. Check that the CI run on the merge commit is green on the Actions page. CI never ran during the build, because the build session could not read GitHub Actions. Every CI step was run locally instead (see [RELEASE_CHECK.md](RELEASE_CHECK.md)).
5. Done 2026-11-26: the repo is public.
6. Pages: optional. `docs/index.html` opens from disk. Turn on Pages from `/docs` only if you want it online.
7. Upload `docs/social-preview.png` in Settings, General, Social preview. Fill in the About box from [GITHUB_ABOUT.md](GITHUB_ABOUT.md) and the topics from [topics.txt](topics.txt) if the coordinator did not.
8. Pin the repo or list it in your profile README.
9. Publish to PyPI with trusted publishing, if you want the package public. The name `askledger` answered 404 on PyPI on 2026-11-21.
10. Record one free model. The build machine could not reach api.groq.com or openrouter.ai, and no key was set. On a machine with network access, copy `.env.example` to `.env`, put in a free key (for example `GROQ_API_KEY`), check the free limits on the provider's page, then run:

    ```bash
    set -a && . ./.env && set +a
    .venv/bin/askledger record
    .venv/bin/askledger eval
    .venv/bin/askledger readme
    ```

    The first command saves each answer in `fixtures/llm/`, so later runs replay it with no key. Only synthetic questions and the schema go to the provider. Commit `fixtures/llm/`, `results/`, `README.md` and `docs/index.html` together. Then set F16 to true in `feature_list.json` and remove its row from BLOCKERS.md.
11. Decide whether `docs/build/BUILD_PROMPT.md` stays public.
12. Rename: not needed. The repo name matches the package name.
13. Do the human checks in the README: read `src/askledger/safety.py` line by line, spot check ten gold queries against their questions, and try a few attacks of your own with `askledger sql`.
