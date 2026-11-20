# Workspace memory

Start with the offline memory core; optional memory services are not required. [Learn mode](../workflows/learn-mode.md) keeps optional learning recaps separately at the selected project's `.workspace/learning/notes.md`. Those notes are not confirmed project facts, do not replace `SESSION-STATE.md`, and never reactivate teaching in a new conversation.

Keep only explicitly approved, non-confidential preferences and reusable lessons here. Project/client decisions belong in that project's `Memory/` and `SESSION-STATE.md`. Folder placement is not an access-control boundary.

Use a source, date, scope and status (confirmed, inferred, superseded, expired) for each durable note. Resolve contradictions explicitly. Capture only relevant material; never record credentials. Use `templates/memory-note.md` for a new note. No indexer or capture service is running by default.

The offline default is `tools/memory.py`, operating only inside an explicitly selected project containing PROJECT.md. It stores proposals and confirmed records in `Memory/curated.json`, resolves replacements by exact record id, and supports local forgetting. Read [the memory core](../docs/MEMORY-CORE.md). Root reusable notes remain manual; project stores are never automatically merged here.

Basic Memory can provide a richer knowledge interface; Claude-Mem can capture episodes. They have different roles and can coexist with explicit ownership, retention and retrieval scope. No capture or sync is configured. Export/forget operations must include each configured provider's database/index, not just visible Markdown. See [the architecture](../docs/FOUNDATION.md).
