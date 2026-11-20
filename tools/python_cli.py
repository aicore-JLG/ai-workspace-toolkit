"""Launch a local environment's console entry point with Windows long-path imports."""
import os
from pathlib import Path
import sys

def long_paths(paths):
    result=[]
    for value in paths:
        if value.startswith('\\\\?\\'):result.append(value);continue
        # Preserve UNC spelling before Path interpretation on non-Windows test hosts.
        path=value if value.startswith('\\\\') else str(Path(value or '.').absolute())
        result.append('\\\\?\\UNC\\'+path[2:] if path.startswith('\\\\') else '\\\\?\\'+path)
    return result

def main():
    if len(sys.argv)<2:raise ValueError('Console entry point name required.')
    if os.name=='nt':sys.path[:]=long_paths(sys.path)
    from importlib.metadata import entry_points
    name=sys.argv[1]
    matches=list(entry_points(group='console_scripts',name=name))
    if len(matches)!=1:raise ValueError('Expected one installed console entry point.')
    sys.argv=[name,*sys.argv[2:]]
    return matches[0].load()()

if __name__=='__main__':sys.exit(main())
