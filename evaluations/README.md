# Skill and pipeline evaluations

Run the following toolkit commands from the kit root. The offline checks need Python 3.11+ and make no model calls. Skill-creator, skilled and skill-eval-harness are [optional routes](../integrations/README.md); model-based runs need separately configured access and authorised usage.

For [Learn mode](../workflows/learn-mode.md), check explicit activation, truthful explanations, pause/off, fresh-session opt-in and project-local notes. Do not infer understanding just because the learner agrees. These require behavioral review; passing Python checks alone does not establish teaching quality or native-host activation.

The included offline foundation benchmark is executable: `python -B tools/evaluate.py --run`. It exercises fresh-process session recovery, scoped memory and verification behavior through actual CLI commands. `--status` checks whether the report still matches current tools/cases. Its receipt is private in `.workspace/evaluations/`. These are local contract checks, not measurements of model answer accuracy. The full release gate also runs the broader regression suite.

Use skill-creator to define behavior and examples. Use skilled for repeatable runs/comparisons, or skill-eval-harness for paired skill/no-skill research. Start with a small suite that reflects actual work.

Keep versioned cases and fixtures here (or beside the skill). Keep private outputs in `.workspace/reports/evaluations/`. See [the evaluation plan](../templates/evaluation-plan.json) for the planning record; it is not a skilled or harness runtime schema. The bundled skilled references contain the actual YAML schema.

Improvement loop: record a real failure, freeze baseline and cases, create a candidate outside vendor/, evaluate both with the same model/tools, run independent holdouts, compare regressions, review and promote within existing authority. Retain the previous skill for rollback. An optimiser must not edit its tests or permissions to obtain a pass. No scheduler or autonomous promotion daemon is installed.
