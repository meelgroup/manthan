import atexit
import os
import tempfile

_RUN_TEMP = tempfile.TemporaryDirectory(prefix="manthan_run_")
atexit.register(_RUN_TEMP.cleanup)


def temp_path(name):
    return os.path.join(_RUN_TEMP.name, name)
