# Worked example: task summary

This is a synthetic demonstration, not a real business or person's records.

## Outcome
Read a small task list and report how many tasks are done, how many are pending, and the pending titles in their original order.

## In scope
Local JSON input, a Python summary function, meaningful tests and a handoff.

## Out of scope
Accounts, notifications, scheduling and external services.

## Done when
- Done and pending totals match the input.
- Pending titles keep their original order.
- Invalid task records are rejected rather than silently counted.
- An empty list gives zero totals.

## Try it
From this folder run `python -B summary.py` and `python -B -m unittest test_summary.py`.
Follow `docs/WALKTHROUGH.md` from the kit root for verification, state saving and recovery.
