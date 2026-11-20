# Try the toolkit on a small project

Run these commands from the extracted kit root. They use synthetic files and local Python only. No account is needed and nothing is sent. Use `python3` instead of `python` if that is your executable name.

## 1. Inspect before acting

```text
python -B tools/preflight.py
python -B tools/workspace.py doctor
python -B tools/workspace.py context --scope examples/welcome-project
python -B examples/welcome-project/summary.py
```

The example reports one done task and two pending tasks. The context command selects only that project's entry instructions, brief and state. If it reports omitted files, read them separately; a context budget must not silently remove required instructions.

## 2. Check the work

```text
python -B tools/verify.py --root examples/welcome-project
python -B tools/verify.py --root examples/welcome-project --run
python -B tools/verify.py --root examples/welcome-project --status
```

Preview the command before using `--run`. The command runs trusted project code with your user permissions; it is not a sandbox. Successful status is bound to the configured files, configuration and verifier. Changing a declared input makes the old result stale. Include every dependency that matters in `checks.json`; undeclared dependencies are not covered. Command output is discarded; to diagnose a failure, run the displayed trusted check directly.

## 3. Save a safe handoff

```text
python -B tools/workspace.py state-hash --file examples/welcome-project/SESSION-STATE.md
```

Read the current state and write a truthful summary. `examples/welcome-project/next-state.md` is a starting example; it deliberately makes no invented test claims. Copy the returned hash into the commands below in place of HASH:

```text
python -B tools/workspace.py compact --file examples/welcome-project/SESSION-STATE.md --summary examples/welcome-project/next-state.md --expect-sha256 HASH
python -B tools/workspace.py compact --file examples/welcome-project/SESSION-STATE.md --summary examples/welcome-project/next-state.md --expect-sha256 HASH --write
```

The first previews. The second preserves the complete old state in the project's history and installs the summary. If the state changed meanwhile, it refuses; read the new state and revise the summary instead of forcing it.

## 4. Prepare a specialist and run a logged task

```text
python -B tools/workspace.py overview --scope examples/welcome-project
python -B tools/launch.py --department engineering --project examples/welcome-project --task "Explain the next change and its acceptance check."
python -B tools/run.py --root examples/welcome-project --config run.json
python -B tools/run.py --root examples/welcome-project --config run.json --run
python -B tools/run.py --root examples/welcome-project --config run.json --status
```

The launch command returns maker/reviewer briefs without starting an agent. The runner records the synthetic summary command's output locally. Its resource lease applies only to cooperating runner calls using the same root.

To see stale evidence rejected, after step 2 edit the example PROJECT.md, then repeat verification --status. It should refuse the old receipt. Rerun --run to check the changed declared inputs. Perform this only in your extracted working copy.

## 5. Start your own project

```text
python -B tools/workspace.py new-project Ventures/my-first-project
python -B tools/workspace.py new-project Ventures/my-first-project --write
```

The destination must be new. Personalise its brief and state with your AI, then use `workflows/build-and-review.md` for a substantial task. Do not give the AI a whole workspace of unrelated records when one project will do.

Files created under `.workspace/`, histories and test outputs belong to your private working copy. Share the untouched download, not a folder you have populated with your records.
