# Proposals

Ideas that are not built. Each one says what it would show.

- **Record a free model.** Fill the LLM rows with a small free model on a provider that offers a free tier. Shows the real gap between rules and a model on held-out.
- **Show your work mode.** `askledger ask --verbose` that prints the linked tables, every SQL attempt and every error. Helps a user trust or reject an answer.
- **Row level rules.** Let the authorizer read a per-user policy, for example "no email column", and return IGNORE for denied columns so they come back as NULL.
- **Prompt injection classifier.** Run a small classifier such as Prompt Guard on the question before generation and report how many hostile questions it flags. It would sit above the model as a warning, never as the safety layer.
- **Test suite accuracy.** Build a second, differently seeded database and score each prediction on both, as in the distilled test suite paper, to cut lucky matches.
