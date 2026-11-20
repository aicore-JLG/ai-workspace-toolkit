# Test an actual client isolation boundary

This opt-in pilot uses synthetic data only. It checks a restricted Docker container, not the normal host process. It does not install or start Docker, pull an image, configure accounts, use model subscriptions or put the main orchestrator inside a container.

The helper only prepares files and validates reports you supply. Passing its unit tests proves the evidence contract, not an operating-system wall. A successful real run supports only the tested container/image/settings. It is not certification against a compromised host, daemon or runtime image.

## Prerequisites

- An already available, authorised Linux-container Docker engine. The generated commands use the default local Windows named pipe or Linux Unix socket, with a new empty Docker configuration directory. They never select a remote context.
- An approved local Linux image containing `python3`. Select its full `sha256:` image ID. Tags and registry references are refused; `--pull=never` prevents fallback downloads. Image installation is a separate decision.
- Permission to create and remove this one temporary synthetic container. Read the generated argument arrays before execution. Do not substitute real client files, home directories, credential stores or the Docker socket as mounts.

If the engine/image is absent or unusable, stop with **isolation unobserved**. WSL, a worktree, a separate folder or a Docker shortcut is not evidence that a restricted runtime is available. Do not silently restart a service, install software or fall back to an unrestricted local run.

## Prepare without running anything

Use a fresh directory inside your private working copy, with an existing parent. Substitute the actual local image ID:

```text
python -B tools/isolation_pilot.py --directory .workspace/my-isolation-pilot --image sha256:YOUR_64_HEX_IMAGE_ID
python -B tools/isolation_pilot.py --directory .workspace/my-isolation-pilot --image sha256:YOUR_64_HEX_IMAGE_ID --prepare
```

Preview creates nothing. Prepare refuses existing destinations and creates:

```text
my-isolation-pilot/
  client-a/allowed.txt       the only permitted input
  client-a/probe.py          fixed synthetic test, mounted read-only
  client-b/canary.txt        exists on host; never mounted
  account/canary.txt         synthetic credential-store stand-in; never mounted
  output/                   the only writable host mount
  docker-config/            empty; no account/context credentials
  pilot.json                root/run identity and fixture hashes
  commands.json             exact argument arrays; not executed by the helper
```

Only the new synthetic output directory is made writable to the container's non-root UID. Never point this preparation step at an existing project directory.

## Execute the reviewed commands deliberately

The generated container command requests a read-only root filesystem, non-root UID, dropped capabilities, no-new-privileges, no network, bounded CPU/memory/process count, private temporary storage and exactly two bind mounts. The other client and account canaries are outside both mounts.

Run the following local Python snippet only after reviewing `commands.json` and authorising the pilot. Set `root` to the prepared directory. It uses a minimal child environment and deliberately adds a **synthetic parent credential canary**. Without that canary, its absence inside the container would not test credential inheritance. This snippet does not change your persistent shell environment or any account.

```python
import json, os, subprocess, uuid
from pathlib import Path

root = Path(".workspace/my-isolation-pilot").resolve()
plan = json.loads((root / "commands.json").read_text())
env = {k: v for k, v in os.environ.items()
       if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR"}}
env["ISOLATION_PILOT_CREDENTIAL"] = "synthetic-only-" + uuid.uuid4().hex
# Local inspection only. Missing image/engine fails; no pull is attempted.
subprocess.run(plan["image_inspect"], env=env, check=True, timeout=15,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    result = subprocess.run(plan["run"], env=env, check=False, timeout=60)
finally:
    inspection = subprocess.run(plan["container_inspect"], env=env,
                                capture_output=True, check=True, timeout=15)
    with (root / "container-inspect.json").open("xb") as stream:
        stream.write(inspection.stdout)
```

This is a transparent manual recipe, not an automatically supervised container service. A timeout can leave the named container running. Inspect it and use the generated **exact-container** cleanup command; never remove unrelated containers, prune Docker or restart the daemon. Preserve the inspection report first. A running, failed or missing container/result cannot pass validation. Start a new pilot directory for a repeat rather than overwriting old evidence.

The probe attempts to read only synthetic paths, tries prohibited writes, confirms the allowed input/output path and checks that IPv4/IPv6 routing is unavailable. Its UDP `connect` calls use documentation-only addresses and send no data packets. It reads no real client file or credential value.

## Validate and clean up

```text
python -B tools/isolation_pilot.py --directory .workspace/my-isolation-pilot --validate
```

Validation requires every canary check, unchanged fixtures/commands, matching image/run/root identity, successful container exit, the restricted settings and exactly the intended mounts. Missing, stale, copied, failed or malformed evidence is refused. Unknown mount-path formats also refuse; investigate rather than weakening the check.

Success is labelled `synthetic_evidence_validated` and `runtime_observed: reported_by_local_receipt`. The helper never observes the container directly. Its reports and Docker inspection are local evidence that can be edited by the same user, not authenticated attestations. Record who ran/observed the pilot and that the parent credential canary was present. Do not turn synthetic unit-test fixtures into an observation claim.

After inspection, run only the `cleanup_after_inspection` argument array from the reviewed plan to remove this named pilot container. Keep the synthetic files/report until their review is complete. The helper performs no deletion.

## What this still does not protect

The normal `orchestrate.py` path and trusted candidate checks still run on the host. Passing this separate pilot does not isolate them, restrict host connectors, or migrate subscription authentication into a container. That integration needs a separate, reviewed design and tests covering the actual workload.

Do not mount an existing whole user profile to make subscription login work. A production client environment needs deliberately scoped files, separate credential/account access, controlled permitted networking and an audited way to return outputs. Network access for model calls changes this pilot's assumptions and must be tested separately. Keep [security boundaries](SECURITY-BOUNDARIES.md) and [orchestration evidence](ORCHESTRATION.md) explicit about these differences.
