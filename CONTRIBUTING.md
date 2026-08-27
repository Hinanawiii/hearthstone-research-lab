# Contributing

Thank you for improving CardLab. Contributions should preserve the distinction between a correct
environment, a mutable candidate, and an empirical claim.

## Development setup

```bash
git clone https://github.com/Hinanawiii/hearthstone-research-lab.git
cd hearthstone-research-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[train,dev]'
make check
```

## Before opening a pull request

- Add or update tests for every rule change.
- Update `CARD_POOL_VERSION` when observable rule or card behavior changes.
- Keep protected evaluator changes separate from candidate-policy changes.
- State the seeds, episode budget, opponent set, and metric for performance claims.
- Report inconclusive and negative results honestly.
- Do not commit generated checkpoints, API credentials, Blizzard assets, or extracted client data.
- Run `make check` and include the commands and results in the pull request.

Rule-engine pull requests should include a minimal reproduction and at least one edge-case test.
Research-control pull requests should explain the game concept represented, how it is computed
without hidden information, and what evidence would make the control misleading.

## Commit and review scope

Prefer small, reviewable commits. One pull request should not simultaneously rewrite the rules,
change the evaluator, and announce a stronger model. Maintainers may ask for those changes to be
split so that results remain attributable.

By contributing, you agree that your contribution is licensed under the repository's MIT License
and that you will follow the Code of Conduct.
