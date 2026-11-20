# Two independent fixes

This synthetic project demonstrates coordinated workers and a fresh review. It
contains two deliberate defects. Its initial checks are expected to fail; it is
not evidence of a successful model run.

## Outcome

Repair `total.py` and `label.py`, then pass the unchanged checks in `test_demo.py`.
The two repairs are independent and may be proposed in parallel.

## Requirements

- `total_cents(amounts)` accepts a list of nonnegative integer amounts, sums every
  item exactly once and does not modify the list. An empty list totals zero.
  Reject a non-list, negative values, booleans and non-integer entries with
  `ValueError`.
- `task_label(title)` accepts a nonblank string, removes leading and trailing
  whitespace and prefixes it with `Task: `. Preserve internal whitespace. Reject
  other values and blank strings with `ValueError`.
- Use Python's standard library only. Preserve the public function names.

## Scope and acceptance

Only `total.py` and `label.py` may be replaced. The acceptance checks, configuration,
instructions and state are immutable during an orchestration run. A separate
reviewer must inspect the final candidate and the actual check evidence.

The source files remain unchanged while workers propose repairs. Applying an
accepted candidate is a separate explicit action. This project contains no real
customer information, credentials, accounts or external service calls.

Run the exercise from the kit root using
`config/orchestration.example.json` and `workflows/coordinated-build.md`.
