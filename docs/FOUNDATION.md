# The foundation and the skills

The foundation stores state and applies checks. Skills tell an AI when and how to use it. Optional providers extend it. Installing more skills does not change the underlying model or make its answers automatically true.

```text
Your AI host                 model, actual permissions, account, sandbox
  Workspace foundation       tools/session.py, memory.py, run.py, verify.py
    Project                  PROJECT.md, rules, code, checks.json
      Memory/curated.json    confirmed facts plus separate proposals
      .workspace/session/    current task, decisions, blockers, next action
      .workspace/runs/       bounded private execution receipts/logs
      .workspace/verification/ content-bound check receipts
  Task skills                .agents/skills/ or .claude/skills/
  Optional services          Basic Memory, Claude-Mem, Doppler, research tools
```

The defaults require no account and make no model calls. `config/foundation.json` is active: integration executions consume its time/output limits, and health checks consume its state-length threshold. `run.json` continues to declare limits for the original general-purpose runner. The other example configurations remain inert.

For an explicitly requested multi-worker build, [subscription orchestration](ORCHESTRATION.md) uses the same project ownership model. Its fixed lifecycle gates validate scoped inputs before dispatch, validate worker proposals, check a staged candidate, require fresh review and recheck source/evidence before explicit application. These gates execute inside that tool; they are not global host hooks. Job state stays in the project's `.workspace/orchestration/`. Worker model/effort is explicit, but selecting the best profile still needs measured outcomes. Existing curated memory and session handoffs remain authoritative for their separate purposes.

## A daily session

Run commands from the known kit root, substituting your actual project. Read the selected project's instructions first.

```text
python -B tools/session.py --root Apps/my-app status
python -B tools/session.py --root Apps/my-app start --objective "Implement the requested change" --acceptance "Relevant checks pass" --input app.py --input test_app.py
python -B tools/session.py --root Apps/my-app resume --memory-query "project conventions"
python -B tools/health.py --root Apps/my-app
python -B tools/verify.py --root Apps/my-app --run
python -B tools/session.py --root Apps/my-app finish --expect CURRENT_REVISION --next-step "Review the result" --verified
```

`status` returning missing is normal for a new project. Select existing affected files at start; extend the declared input list as the work grows using the session CLI. Use actual acceptance criteria and meaningful project checks. The revision comes from the latest session response. Use checkpoint at meaningful progress boundaries. Finish without `--verified` when handing off incomplete work; keep blockers and an actionable next step. Existing active sessions must be resumed, not replaced. Read [session details](SESSION-CORE.md) for exact commands.

The resume packet can retrieve confirmed memory for an explicit query without copying it into the saved handoff. A host must actually invoke these commands: the kit does not silently install global hooks or guarantee that every AI follows instructions. A closed or interrupted host cannot save work it never checkpointed. `.workspace/session/current.json` is the canonical operational handoff; `SESSION-STATE.md` remains a short human-readable summary. Keep the summary consistent when it is useful, without duplicating private memory.

## Three kinds of memory

1. Current work: objective, decisions, blockers and next step in session state.
2. Curated knowledge: source-backed facts and lessons in this project's local memory store. Propose first, confirm deliberately, resolve conflicts explicitly, forget obsolete content. See [memory details](MEMORY-CORE.md).
3. Optional episode capture: services such as Claude-Mem may retain observations. Basic Memory can provide a richer knowledge interface. They can coexist only with clear ownership and scope; neither is required by the local core, and no sync or capture is enabled here.

Do not have several tools independently rewrite the same truth. Review useful observations before promoting them into curated memory. Forgetting the local store does not remove transcripts, proposal files, Git history or external provider indexes. Root-bound local state deliberately refuses copied data in a different project; moving a populated project needs a deliberate migration.

## Reliability and improvement

For factual answers, distinguish evidence, inference and uncertainty. Retrieve current authoritative sources when facts may have changed. A remembered assertion is a reference, not proof. For code and pipelines, run checks that could actually fail for the requested behavior, then use independent review for consequential changes. Keep source material and memory separate from permissions and instructions.

Run `python -B tools/evaluate.py --run` for the offline end-to-end foundation suite. `--status` rejects changed evidence. It checks local workflow behavior, not general model accuracy. Optional model evaluations use a frozen baseline, real task cases, held-out cases, fixed model/tool settings and an authorised budget. Keep failures visible; candidates cannot promote themselves or rewrite their tests to pass.

Health diagnosis is automatic when invoked, but does not delete files or change skills. `health.py` reports pending memory, oversized state, missing/stale/partial verification and interrupted locks. Apply scoped repairs, rerun affected checks, review the diff, retain rollback, and stop when acceptance passes. Scheduled maintenance, broad cleanup and background learning require their own deliberate setup.

## Boundaries that remain

Local receipts are self-reported evidence, not tamper-proof attestations. File checks and cooperative locks are not an operating-system sandbox. Static scans need source review. Credentials still require host/account isolation. Optional MCP, research channels, paid models and Doppler account behavior need recipient-specific testing. The toolkit does not guarantee universal model factual accuracy or autonomous reliability.
