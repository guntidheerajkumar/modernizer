import contextlib
import subprocess
import time
import urllib.request
from pathlib import Path


@contextlib.contextmanager
def running(cmd: str, url: str, cwd: Path, timeout=120):
    proc = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                urllib.request.urlopen(url, timeout=3)
                break
            except Exception as e:
                if getattr(e, "code", None):   # an HTTP error still means the app is up
                    break
                time.sleep(2)
        else:
            raise RuntimeError(f"App did not start at {url} within {timeout}s")
        yield
    finally:
        proc.terminate()
