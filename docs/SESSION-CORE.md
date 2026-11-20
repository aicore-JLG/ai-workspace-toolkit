# Daily session lifecycle

`tools/session.py` saves a concise handoff inside the selected project and returns a bounded packet for the next AI session. It runs with Python's standard library, without a provider account or background service.

Always pass the actual owning project as `--root`; its own `PROJECT.md` marker is required. The tool never searches sibling projects or follows Markdown imports. Run the commands from the kit directory, replacing the example project and filenames with your own.

```sh
python tools/session.py --root Apps/example start --objective "Repair the export" --acceptance "Export regression passes" --input app.py --input test_export.py
python tools/session.py --root Apps/example resume
```

For relevant confirmed project memory, use `resume --memory-query "export format"` (also supported by `status`). Recall requires a nonempty query, returns at most eight records and 8 KiB of record content, and labels those records as untrusted reference data. Results are read fresh and never copied into the stored handoff: forgetting a memory removes it from the next recall packet. Without a query, no memory values are loaded. A corrupt or copied memory store refuses requested recall. `memory.truncated` signals that some matching records did not fit; narrow the query if necessary.

The result includes `revision`, a content hash of the stored handoff. Copy that exact value into subsequent writes. A second writer with an older revision is refused.

```sh
python tools/session.py --root Apps/example checkpoint --expect REVISION --next-step "Review the export change" --decision "Keep the existing output format"
python tools/session.py --root Apps/example finish --expect NEW_REVISION --next-step "Run the missing regression" --blocker "Regression not run"
```

Checkpoint keeps the session active. Finish without `--verified` creates an honest unfinished handoff (`handed_off`). `resume` is read-only and works in a fresh process after a crash or thread change. `active` means unfinished work; it does not prove an agent is running. No automatic host startup, shutdown or compaction hooks are installed. The calling agent must use these commands.

`--decision` and `--blocker` replace their respective concise lists; repeat an option for multiple entries. Omitting them preserves the current lists. Use `--clear-blockers` once blockers are resolved. A new session requires the prior session to be closed and its current `--expect` revision, preventing accidental replacement of active work. Preserve any longer history you need in the project's existing history workflow before starting a new objective.

## Verified completion

Declare all files relevant to the outcome using repeated `--input`. Initial files must already exist. When work creates new files, use `checkpoint --input new-file.py` (or `finish --input new-file.py`) to add them to the required scope; earlier inputs remain required. The existing project `checks.json` must cover every one of those inputs. Run the trusted check, then finish:

```sh
python tools/verify.py --root Apps/example --run
python tools/session.py --root Apps/example finish --expect REVISION --verified --next-step "Review for release"
```

Verified finish requires a current passing receipt, coverage of all declared session inputs and no unresolved blockers. Missing, failed, running or stale checks refuse the write. A checkpoint does not run a check or grant a verification result. An alternative check configuration can be selected with `finish --config path/to/checks.json`.

`verification_current` is recalculated on resume. If files or checks change after completion, a historical `verified` status remains in the handoff but `verification_current` becomes false. `check_status` reports the current declared check's state even before finishing, including missing, failed, stale or incomplete coverage. `changed_inputs` and `missing_inputs` show changes since the last saved checkpoint. The tests cover only the declared inputs and command; this is not proof of complete test coverage, factual accuracy, independent review, authorization or release.

## Where the state lives

- `.workspace/session/current.json` is the current machine-readable handoff: objective, acceptance, decisions, blockers, next step, declared inputs, fingerprints and verification reference. A canonical project-root fingerprint rejects copied handoffs from another project. Moving a project requires explicit migration of its lifecycle state; this tool does not automatically adopt it.
- `.workspace/session/write.lock` protects cooperative writes. It is normally removed when a command exits. A hard interruption can leave it behind; inspect the operation before explicitly recovering it. The tool never silently removes someone else's lock.
- Existing `SESSION-STATE.md` is read as additional project context and is never overwritten. If it conflicts with the saved session, resolve the conflict explicitly; the JSON handoff records this CLI's latest checkpoint, not a new authority level.

The packet reads only named files directly at the selected root: `AGENTS.md`, `CLAUDE.md`, `WORKSPACE-RULES.md`, `PROJECT-RULES.md`, `PROJECT.md` and `SESSION-STATE.md`. The default file-content budget is 32 KiB; `resume --context-budget 8192` changes it. Oversized files are omitted whole and listed in `context.omitted`; required omitted instructions still need explicit scoped reading before work. Input files are hashed, not included in the packet. Session text is limited to 64 KiB, 20 entries per list and 4 KiB per entry.

Do not store secrets in handoffs. Output contains project text and belongs only in the owning project's conversation. Atomic replacement and file hashes protect ordinary cooperative use, not malicious processes running with your permissions. Local handoff data and any interrupted temporary files remain private runtime files and are excluded from the release package. No long-term memory, backup service, scheduler or external synchronization is implied.
