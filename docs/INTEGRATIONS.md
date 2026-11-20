# Set up integrations

Run from the extracted workspace root. The offline core works before optional runtime installation.

```text
python -B tools/integrations.py list
python -B tools/integrations.py verify
python -B tools/integrations.py doctor
python -B tools/integrations.py install skills-cli
python -B tools/integrations.py install skills-cli --run
python -B tools/integrations.py run skills-cli -- --version
python -B tools/integrations.py activate skill-creator skill-creator --host claude
python -B tools/skill_review.py scan skill-creator skill-creator
```

Before adding `--write` to activation, inspect every selected source file and the scan findings. Record `python -B tools/skill_review.py accept INTEGRATION SKILL --fingerprint CURRENT_HASH --reviewer REVIEWER --rationale "Source reviewed for this project"`, adding `--ack FINDING_ID` for every reported finding. Use an actual rationale resolving the findings. `status INTEGRATION SKILL` checks the receipt. Source or scanner changes invalidate it. This is self-attested review, not a security certification; use SkillSpector and manual inspection for deeper checks.

Use `--host codex` for project `.agents/skills/`. Existing destinations are preserved and reported as conflicts. Select names from `list`; full plugins and agent-only definitions are not SKILL.md directories.

`install` previews; `--run` downloads and executes the selected third-party installer/build in `.workspace/tools/`. `run` executes a locally installed CLI immediately and may have external effects according to the arguments you choose. Integration subprocesses use the shared runner's lease, time/output limits and private receipt. Ordinary output is in the receipt's bounded redacted log; installer and Doppler output are discarded. This is not a sandbox. npm lifecycle scripts are disabled; integrations needing separate onboarding retain that step in their guide. No install command logs in, configures host hooks, starts observers or enables channels. See `docs/EXECUTION-CORE.md`.

Bundle verification compares all files with the release lock and rejects unexpected additions. Hashes prove correspondence to this kit, not that source is harmless. Review scanner findings before activating a skill. Pins do not freeze every transitive dependency; npm writes package-lock.json in the local installation.

Install failures retain their partial directory, without a ready marker. Do not blindly retry into it. Diagnose first and preserve it outside that integration's destination before reinstalling. Existing successful installations are never overwritten. Updating requires a new reviewed catalog, a candidate runtime and repeat checks; no background updater is shipped.

The offline memory default is `tools/memory.py`. Basic Memory can add a richer knowledge interface and Claude-Mem can capture episodes; avoid multiple writers owning the same facts. ECC observation is a separate opt-in learning stream. Configuration examples remain inert. `config/foundation.json` is the active local execution/health policy. Read `docs/FOUNDATION.md` for ownership and the daily workflow.

Read the per-tool setup guide in the integration directory for prerequisites, platform limits, data access and usage costs. Source bundles with home-folder assumptions need their documented paths adapted to the selected project before execution.
