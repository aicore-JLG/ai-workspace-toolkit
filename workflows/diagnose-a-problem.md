# Diagnose a recurring problem

Use `roles/debugger.md`. Record the symptom, expected behaviour and smallest reproduction. Capture relevant evidence without credentials or unrelated records.

Form one testable explanation at a time. Check the evidence before editing. For a code bug, add a meaningful regression test that fails for the defect, make the smallest justified change, then rerun the affected checks.

If the same attempt fails twice with unchanged inputs, inspect the cause before another retry. Distinguish authentication, quota, network and implementation errors. Never switch accounts or spend money to bypass an unresolved failure.

Record the confirmed cause, changed files, verification and remaining limits in the project's state. Do not claim the whole system is healthy because one test passes.
