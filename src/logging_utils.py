import time

_START_TIME = time.perf_counter()


def cprint(*args, **kwargs):
    elapsed = time.perf_counter() - _START_TIME
    if not args:
        print(f"c [{elapsed:.2f}s]", **kwargs)
        return
    first = str(args[0])
    if first.startswith("c"):
        print(f"{first} [{elapsed:.2f}s]", *args[1:], **kwargs)
    else:
        print(f"[{elapsed:.2f}s]", *args, **kwargs)
