# v2.6 Generic Fixture Date Resolver

The fixture resolver finds match dates from available v22 corpus/cache data when a user omits `--match-date`.

It matches exact normalized home and away teams. Reversed fixtures are reported but never guessed as the requested match. Multiple exact candidates return `AMBIGUOUS`.

The resolver is generic: known fixtures in tests are fixture rows, not hardcoded production logic.
