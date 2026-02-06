import re
import time

_START_TIME = time.perf_counter()
_C_TAG_RE = re.compile(r"^c\s+(\[[^\]]+\])\s*(.*)$")


def cprint(*args, **kwargs):
    elapsed = time.perf_counter() - _START_TIME
    if not args:
        print(f"c [{elapsed:.2f}s]", **kwargs)
        return
    first = str(args[0])
    if first.startswith("c"):
        match = _C_TAG_RE.match(first)
        if match:
            tag, rest = match.groups()
            prefix = f"c {tag} [{elapsed:.2f}s]"
            if rest:
                prefix = f"{prefix} {rest}"
            print(prefix, *args[1:], **kwargs)
        else:
            rest = first[1:].lstrip()
            prefix = f"c [{elapsed:.2f}s]"
            if rest:
                prefix = f"{prefix} {rest}"
            print(prefix, *args[1:], **kwargs)
    else:
        print(f"[{elapsed:.2f}s]", *args, **kwargs)
