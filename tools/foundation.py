"""Strict active local policy. No provider, permission or spending configuration."""
import json
from verify import read_bytes, safe_path, strict_root


def load_policy(root):
    root = strict_root(root)
    defaults = {'schema_version': 1,
                'execution': {'timeout_seconds': 120, 'max_output_bytes': 65536},
                'maintenance': {'state_line_limit': 150}}
    path = safe_path(root, 'config/foundation.json', must_exist=False)
    if not path.exists():
        return defaults
    policy = json.loads(read_bytes(root, 'config/foundation.json', 8192))
    if not isinstance(policy, dict) or set(policy) != set(defaults) or type(policy['schema_version']) is not int or policy['schema_version'] != 1:
        raise ValueError('Unsupported foundation policy schema.')
    for group in ('execution', 'maintenance'):
        if not isinstance(policy[group], dict) or set(policy[group]) != set(defaults[group]):
            raise ValueError('Unsupported foundation policy fields.')
    limits = [('execution', 'timeout_seconds', 1, 600),
              ('execution', 'max_output_bytes', 1024, 1048576),
              ('maintenance', 'state_line_limit', 20, 500)]
    for group, name, minimum, maximum in limits:
        value = policy[group][name]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError('Invalid foundation limit: ' + name)
    return policy
