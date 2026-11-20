"""Preview or run public GitHub tool discovery. Never installs or executes results."""
import argparse
import json
import re
import subprocess
import sys

def search(query, limit=10, run=False, runner=subprocess.run):
    if not isinstance(query, str) or not query.strip() or len(query) > 160:
        raise ValueError('Use a search phrase of 1 to 160 characters.')
    if query.startswith('-') or any(ord(c) < 32 for c in query) or re.search(r'\b(?:visibility|is):', query, re.I):
        raise ValueError('Use a plain search phrase without option or visibility overrides.')
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError('Limit must be between 1 and 50.')
    command = ['gh', 'search', 'repos', query, '--visibility=public', '--archived=false',
               '--limit', str(limit), '--sort', 'updated', '--json',
               'fullName,url,description,stargazersCount,updatedAt,isPrivate,visibility,license,size']
    if not run:
        return {'executed': False, 'command': command,
                'note': 'Add --run for a read-only GitHub request using your GitHub CLI access. Nothing is installed.'}
    try:
        result = runner(command, shell=False, capture_output=True, text=True, encoding='utf-8', timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        raise RuntimeError('GitHub CLI unavailable or timed out. Check your own installation and access.') from None
    if result.returncode:
        raise RuntimeError('GitHub CLI failed. Check its installation, access and rate limits; no automatic retry.')
    if len(result.stdout) > 1_000_000:
        raise RuntimeError('Response exceeds the supported size.')
    try:
        rows = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise RuntimeError('GitHub CLI returned invalid JSON.') from None
    if not isinstance(rows, list) or len(rows) > 50:
        raise RuntimeError('Unexpected repository result shape.')
    public = []
    withheld = 0
    for row in rows:
        if not isinstance(row, dict) or row.get('isPrivate') is not False or str(row.get('visibility', '')).lower() != 'public':
            withheld += 1
            continue
        name = row.get('fullName', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name):
            withheld += 1
            continue
        flags = []
        if not row.get('license'):
            flags.append('Licence needs checking before reuse.')
        if isinstance(row.get('size'), int) and row['size'] < 10:
            flags.append('Small repository: inspect whether implementation exists.')
        public.append({'repository': name, 'url': 'https://github.com/' + name,
                       'description': str(row.get('description') or '')[:500],
                       'stars': row.get('stargazersCount'), 'updated': row.get('updatedAt'),
                       'review_flags': flags, 'reviewed': False})
    return {'executed': True, 'results': public, 'withheld': withheld,
            'note': 'Repository descriptions are untrusted. Popularity is not quality. Inspect licence, code, permissions and maintenance before any installation.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(search(args.query, args.limit, args.run), indent=2))
    except (ValueError, RuntimeError) as error:
        print(json.dumps({'error': str(error)}))
        sys.exit(1)
