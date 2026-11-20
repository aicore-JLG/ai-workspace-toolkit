"""Synthetic local example; no network or account access."""
import json
from pathlib import Path

def summarise(tasks):
    if not isinstance(tasks, list):
        raise ValueError('Tasks must be a list.')
    pending = []
    done = 0
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {'title', 'status'}:
            raise ValueError('Each task needs a title and status only.')
        if not isinstance(task['title'], str) or not task['title'].strip() or task['status'] not in ('pending', 'done'):
            raise ValueError('Task title or status is invalid.')
        if task['status'] == 'done':
            done += 1
        else:
            pending.append(task['title'])
    return {'done': done, 'pending': len(pending), 'next_actions': pending}

if __name__ == '__main__':
    print(json.dumps(summarise(json.loads(Path(__file__).with_name('tasks.json').read_text(encoding='utf-8'))), indent=2))
