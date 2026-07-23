# Sandoghchi Test Strategy

## Active Tests

Current production tests:

- API routes
- Health endpoint
- Authentication routes
- Portfolio routes
- Ranking routes
- Data validation

## Legacy Tests

Old experimental tests are stored in:

tests/legacy/

They belong to previous architecture versions.

They are not part of production verification.

## Before Commit

Run:

bash tools/pre_commit_check.sh

Required:

- compile OK
- agent verification OK
- production pytest OK
