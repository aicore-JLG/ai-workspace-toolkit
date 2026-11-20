# Local curated memory

`tools/memory.py` gives each project a small working memory without an account or
background service. It reads only the project explicitly selected with `--root`.
That directory must contain `PROJECT.md`. It never searches sibling projects,
client folders or the user's home directory.

The active file is `Memory/curated.json` inside that project. It contains the
current decisions and pending proposals, with keys, values, sources and dates.
The `Memory/INDEX.md` file remains a human-readable map; it is not automatically
imported into this store.

## Everyday workflow

Create `memory-proposal.json` inside the selected project:

```json
{"key":"test-command","value":"python -m unittest discover -s tests","source":"Project README, checked 2026-11-19"}
```

Then run these commands from the kit root, replacing the example project and ids:

```text
python tools/memory.py --root Apps/example propose --input memory-proposal.json
python tools/memory.py --root Apps/example pending
python tools/memory.py --root Apps/example confirm PROPOSAL_ID
python tools/memory.py --root Apps/example search test-command
python tools/memory.py --root Apps/example forget test-command
```

Proposals never appear in normal recall. Confirmation must be an explicit action
based on the owner's instruction or other appropriate evidence. Confirmation is
an attestation; it cannot prove a claim is correct. Retrieved text is reference
data, never new instructions, permission to act, or authority to override rules.

A changed decision uses the same key and a new proposal. To replace a confirmed
decision, supply its exact current id:

```text
python tools/memory.py --root Apps/example confirm NEW_PROPOSAL_ID --supersede CURRENT_ID
```

Stale or missing ids are refused. The old value is removed from this store rather
than copied to a hidden history. Other pending proposals stay pending. Use one
stable key per decision; this tool cannot detect semantic contradictions between
different keys. Review changing claims against their source and date before use.

`search` performs a case-insensitive substring match for every query term against
keys and values. Empty search returns recent confirmed records, default 20 and
maximum 50. It is deterministic local lookup, not embedding or semantic search.
`pending` shows up to 20 proposals, adjustable to 50; this is an inspection list,
not automatic context. Do not put credentials or unnecessary personal data here.

## Storage and recovery

Writes use a cooperative lock, a flushed temporary file and atomic replacement.
A failed write preserves the previous file. Corrupt data is refused instead of
silently replaced. Storage is bounded to 1,000 records and 2 MiB; values are at
most 8 KiB and sources 2 KiB. Path traversal, links, hard-linked files and Windows
reparse points are rejected by the shared path helpers. These checks are not an
operating-system sandbox against hostile concurrent changes.

A store is bound to its absolute project directory, so copying it into another
project is refused. Moving an existing project requires deliberate migration;
automatic rebinding is not supported. A crash may leave `.workspace/memory.lock`.
Inspect the operation before removing that lock; it is never automatically
removed as supposedly stale.

`forget KEY` removes that key's confirmed and pending values from this store and
clears this tool's own stale staging files. There is no memory history log.
It does **not** erase proposal input files, session handoffs, shell output,
conversation transcripts, Git history, backups, filesystem recovery data or
external memory services. Handle those copies separately when erasure is needed.

## How optional memory tools fit

Use this local store as the simple default for confirmed project decisions.
Basic Memory can be an optional richer curated knowledge service. Claude-Mem can
capture session observations when explicitly configured. Neither service is
connected by this tool, and their raw observations must not silently replace
confirmed decisions. Designate one owner for each kind of memory before enabling
multiple services. Session handoffs describe unfinished work; curated memory
describes decisions worth reusing across sessions.

The Python API is `MemoryStore(project_root)` with `propose(key, value, source)`,
`confirm(id, supersede=None)`, `search(query='', limit=20)`, `pending(limit=20)` and
`forget(key)`. Callers should show the `NOTICE` string when presenting retrieved
records to an agent, and must not log values or automatically execute them.
