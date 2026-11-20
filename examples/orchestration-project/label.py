"""Synthetic task label with one deliberate whitespace defect."""


def task_label(title):
    if not isinstance(title, str) or not title.strip():
        raise ValueError('A nonblank title is required.')
    return 'Task: ' + title
