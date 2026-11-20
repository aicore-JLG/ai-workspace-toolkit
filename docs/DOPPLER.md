# Doppler setup

Doppler keeps secret values outside the workspace and injects selected values into a child process. Each recipient uses their own account and project. No author account IDs, tokens or configs are distributed.

1. Install the CLI using the [official platform instructions](https://docs.doppler.com/docs/cli). On Windows, the documented package is `winget install doppler.doppler`.
2. Run `doppler login` interactively. Select or create the appropriate project/config in your account; use separate scopes for clients and environments. Add values through Doppler, not through an AI chat.
3. Preview a run with explicit scope and variable names:

```text
python -B tools/integrations.py doppler --project my-app --config dev --only API_KEY -- python app.py
```

4. Add `--run` before the separator when the child command and scope are correct:

```text
python -B tools/integrations.py doppler --project my-app --config dev --only API_KEY --run -- python app.py
```

The wrapper uses `--no-fallback` to avoid reading/writing an encrypted fallback file and `--only-secrets` to request just the named values. It does not fetch, display or save values itself. Its shared runner discards all child stdout/stderr and keeps only a hashed operation receipt, with bounded execution time and a cooperative lease. It inherits the process environment and does not isolate unrelated credentials already present there. Run in a clean environment when isolation is needed. The child and its descendants can read injected variables and write their own files or network logs; the wrapper cannot prevent those effects. No shell-string execution, auto-retry, `.env` export or production write is added.

`config/doppler.example.yaml` contains only placeholders and is not active configuration. The explicit wrapper does not require a doppler.yaml file. Login, project access, service tokens and CI configuration remain recipient-specific setup. Neither a successful CLI version check nor an offline test proves account access.
