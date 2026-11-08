# Contributing

Thank you for helping improve TraderDesk V2.

1. Create a branch from `main`.
2. Keep credentials and account data out of commits.
3. Add or update offline tests for behavior changes.
4. Run `python -m pytest` before opening a pull request.
5. Describe trading-impacting changes, failure behavior, and manual verification clearly.

Pull requests must not contact live broker or notification services during test collection. External integrations should be mocked by default and enabled only through an explicit opt-in test command.
