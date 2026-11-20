# Run a trusted local task

The runner gives one trusted foreground command a timeout, bounded private output log, clear exit status and a cooperative workspace lease. It does not install hooks, configure an AI provider, run scheduled jobs or connect services. Commands that start background children or services are unsupported; use commands that wait for all their work before exiting.

## Prepare a command

Create `run.json` in the selected workspace. Use an argument array, not a shell command string:

```json
{
  "command": ["{python}", "task.py"],
  "inputs": ["task.py"],
  "timeout_seconds": 30,
  "max_output_bytes": 65536
}
```

Replace `task.py` with a script you have read and trust. Include every file that affects the result in `inputs`; the runner cannot infer undeclared dependencies. `{python}` means the Python interpreter running the toolkit. Other executable names resolve through your PATH.

```text
python tools/run.py --config run.json
python tools/run.py --config run.json --run
python tools/run.py --config run.json --status
```

The first command only previews. `--run` explicitly executes. Use `--root PATH` when the task belongs to a different selected workspace; all declared input paths are relative to that root. This is a local filesystem selection, not permission to read someone else's project.

The foreground-process timeout must be greater than zero and at most 600 seconds. Captured output defaults to 64 KiB and may be configured between 1 KiB and 1 MiB. Exceeding the limit attempts to stop the command and records `output_limit`, not success. Timeout handling attempts to stop the active process tree/group, followed by bounded cleanup and output collection, so total elapsed time can exceed the configured foreground timeout. It does not guarantee that all descendants stop, especially after the parent has exited.

If a foreground process exits while a child keeps an output pipe open, the runner records `incomplete_output` and retains the resource lease. It does not claim that the child was stopped. Inspect and stop any remaining work before manually removing the lease. Background work that closes its inherited pipes cannot reliably be detected; a `completed` result describes the foreground process's exit only. Do not use the runner to launch background work.

## What is recorded

Private logs and receipts go under `.workspace/runs/`, which the kit ignores in Git. They contain a bounded, redacted stdout/stderr log, elapsed time, exit code, selected-input/configuration/tool fingerprint and status. Raw command arguments and the environment are not written into receipts. Configuration stays in your local `run.json`.

The redactor recognises common credential formats, key/password assignments and inherited environment values whose names suggest secrets. It does **not** remove every kind of personal or client information. Do not publish logs or include `.workspace` in a shared kit.

`--status` refuses an old success when declared inputs, configuration or runner/helper code change. A nonzero exit stays a failure. A command changing its declared inputs records `changed_during_run`; rerun against the final inputs when appropriate. Successful execution does not imply independent review, deployment or correctness of an unchecked result. Use the verification tool for a declared acceptance check.

## Coordination and limits

One cooperative resource lease is available per selected workspace. A second runner invocation refuses while `.workspace/runs/resource.lock` exists. The lock records its runner PID and start time for inspection; these are clues, not proof that a process is still the same owner. Direct commands and different workspace roots do not participate. Incomplete output and unexpected interruptions retain the lock. Inspect the running processes and files before manually removing it; the tool never guesses that a lease is safe to delete.

The partial guard refuses common shell executables, inline-code arguments, direct destructive commands, selected destructive/publishing Git operations and obvious credential paths/options. It cannot inspect the meaning of every executable or script. A trusted script can still read files, use inherited credentials, access the network or change your computer with your account permissions. This tool is **not a sandbox**, an approval system or a replacement for your AI tool's real permissions. No provider hooks are installed.

Keep commands short, scoped and reviewable. Do not use the runner to execute downloaded or untrusted code.
