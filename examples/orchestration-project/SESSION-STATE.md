# Orchestration exercise state

## Objective
Repair the two deliberate defects through scoped proposals and independent review.

## Decisions
`total.py` and `label.py` are separate worker outputs. Acceptance tests and project
instructions are fixed for a run. Source application is a separate explicit step.

## Next action
Preview `config/orchestration.example.json` from the kit root, then inspect the
read-only provider preflight before considering a live subscription run.

## Blockers
Live execution requires a supported recipient CLI, subscription authentication
without conflicting API overrides, and explicit model/effort choices.

## Verification
This untouched fixture is deliberately failing. No recipient model run, successful
review or applied repair has been recorded. Local contract tests elsewhere in the
kit do not establish a live provider outcome for this copy.
