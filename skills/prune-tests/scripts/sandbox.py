"""Windows Low integrity for test runs: the process reads every file but writes only under LocalLow.
prune_plugin drops each pytest run to Low as it loads, so a planted bug that writes live data gets access denied."""
from __future__ import annotations

import ctypes
import os
import subprocess
import tempfile
from ctypes import wintypes as W
from pathlib import Path

# LocalLow carries an inherited Low label, so folders made in it stay writable at Low
LOW_ROOT = Path.home() / "AppData" / "LocalLow" / "prune-tests"
SCRIPTS = Path(__file__).resolve().parent


class _SidAttr(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", W.DWORD)]


def lower_self() -> None:
    """Drop this process to Low; children inherit it. Lowering needs no privilege and cannot be undone."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    k32.GetCurrentProcess.restype = W.HANDLE
    token, sid = W.HANDLE(), ctypes.c_void_p()
    label = _SidAttr(None, 0x20)  # SE_GROUP_INTEGRITY
    ok = (adv.OpenProcessToken(W.HANDLE(k32.GetCurrentProcess()), 0x80 | 0x8, ctypes.byref(token))
          and adv.ConvertStringSidToSidW("S-1-16-4096", ctypes.byref(sid)))
    if ok:
        label.Sid = sid
        ok = adv.SetTokenInformation(token, 25, ctypes.byref(label),
                                     ctypes.sizeof(label) + adv.GetLengthSid(sid))  # 25 = TokenIntegrityLevel
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error(), "could not drop to Low integrity")


def low_dir(prefix: str) -> tempfile.TemporaryDirectory:
    LOW_ROOT.mkdir(parents=True, exist_ok=True)
    # a timed-out run can leave a killed child holding a file; a leftover folder must not fail the lane
    return tempfile.TemporaryDirectory(prefix=prefix, dir=LOW_ROOT, ignore_cleanup_errors=True)


_proven: set[str] = set()


def prove(python: str) -> None:
    """The sandbox is the only thing between a planted bug and live data: refuse to run if it does not hold."""
    if os.name != "nt":
        raise SystemExit("prune-tests runs planted bugs only inside the Windows Low integrity sandbox.")
    if python in _proven:
        return
    probe = Path(tempfile.gettempdir()) / f"prune-sandbox-probe-{os.getpid()}"
    # exit 7 only when the drop worked and the write was then refused; a failed drop must not pass
    code = (f"import sandbox, sys; sandbox.lower_self()\ntry: open({str(probe)!r}, 'w').close()\n"
            "except PermissionError: sys.exit(7)")
    env = {**os.environ, "PYTHONPATH": str(SCRIPTS)}
    env.pop("VIRTUAL_ENV", None)
    run = subprocess.run([python, "-c", code], env=env, capture_output=True, text=True, timeout=120)
    if run.returncode != 7 or probe.exists():
        probe.unlink(missing_ok=True)
        raise SystemExit(f"Low integrity sandbox does not hold (rc {run.returncode}, write to {probe.parent}): "
                         f"{run.stderr.strip()[-300:]}; refusing to run tests.")
    _proven.add(python)
