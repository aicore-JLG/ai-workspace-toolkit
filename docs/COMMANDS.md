# Local command reference

Run from the kit root. All Python tools use the standard library and support Python 3.11 or newer. Use `python3` if needed on your system. `--help` prints each tool's arguments.

## Workspace

```text
python -B tools/workspace.py [--root ROOT] doctor [--scope RELATIVE-DIRECTORY]
python -B tools/workspace.py [--root ROOT] map [--scope RELATIVE-DIRECTORY]
python -B tools/workspace.py [--root ROOT] context [--scope RELATIVE-DIRECTORY] [--max-chars 12000]
python -B tools/workspace.py [--root ROOT] new-project RELATIVE-DESTINATION [--write]
python -B tools/workspace.py [--root ROOT] state-hash [--file SESSION-STATE.md]
python -B tools/workspace.py [--root ROOT] compact --file STATE --summary SUMMARY --expect-sha256 HASH [--write]
```

Brackets indicate optional arguments; do not type the brackets. Root defaults to this toolkit's folder. Paths for commands are relative to the selected root. `new-project` needs this kit's `templates/project/` inside that root.

Doctor/map skip hidden directories, client pools, private folders, histories and dependency/build folders. For authorised client work select that one project's scope explicitly. Hidden skill contents require explicit review; a doctor pass does not certify the entire download. The map prints names/sizes rather than rewriting the maintained navigation guide.

Context reads only named entry/rules/brief/state/map files in the selected directory. It reports duplicates and whole files omitted by the budget. Compaction preserves original bytes, refuses stale hashes and uses an exclusive cooperative writer lock. Filesystem checks are not protection against a hostile process changing paths concurrently.

## Verification

```text
python -B tools/verify.py --root PROJECT [--config checks.json]
python -B tools/verify.py --root PROJECT [--config checks.json] --run
python -B tools/verify.py --root PROJECT [--config checks.json] --status
```

Example configuration:

```json
{"command":["{python}","-B","-m","unittest","test_summary.py"],"inputs":["summary.py","test_summary.py"],"timeout_seconds":30}
```

Review commands before running them. Execution uses no shell but still runs trusted code with your permissions. Include all relevant dependencies in the explicit input list. Receipt status covers those files, the configuration and verifier contents; it does not prove UI quality, independent review, secrets isolation or deployment. The command's output is discarded. Receipts under `.workspace/verification/` are private working records. A timeout tries to terminate the ordinary process tree; deliberately detached children are not guaranteed contained.

## Launch, overview and logged commands

See [LAUNCHERS.md](LAUNCHERS.md) for task packets and live local overview, and [RUNNER.md](RUNNER.md) for guarded command execution with bounded logs and a cooperative lease.

```text
python -B tools/workspace.py overview --scope examples/welcome-project
python -B tools/launch.py --list
python -B tools/run.py --root examples/welcome-project --config run.json
```

## Discovery

`python -B tools/preflight.py` checks executable presence without subprocesses or network calls.

`python -B tools/agent_search.py "your topic" --limit 5` previews public GitHub discovery. Add `--run` to use your GitHub CLI. No installation, cloning or candidate execution occurs. Search descriptions remain untrusted source material.
