"""The one way the hub writes a JSON file to disk (profiles, the profile index, audio and display preferences).

A temp file is written first and then renamed over the real one, so a crash or a full disk in the middle of a
write leaves the previous file whole instead of half a file. Errors are raised (OSError): each caller decides
how to report a failed save (a console line, a log warning) and what to return.
"""
import json
import os


def write_json_atomic(path, data, indent=None, make_dirs=False):
    """Write `data` as JSON to `path` via `path + ".tmp"` and an atomic rename. `make_dirs` creates the folder
    first. Raises OSError when the disk refuses."""
    if make_dirs:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
    os.replace(tmp, path)
