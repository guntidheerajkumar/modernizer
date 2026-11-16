"""Target framework catalogue. Edit this list as new .NET versions ship."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    tfm: str          # target framework moniker
    label: str
    kind: str         # "netfx" (retarget) or "modern" (port to SDK-style .NET)
    note: str = ""


TARGETS = [
    Target("net48", ".NET Framework 4.8", "netfx", "retarget, lowest risk"),
    Target("net481", ".NET Framework 4.8.1", "netfx", "retarget"),
    Target("net6.0", ".NET 6", "modern", "out of support"),
    Target("net8.0", ".NET 8 (LTS)", "modern", "port"),
    Target("net10.0", ".NET 10 (LTS)", "modern", "port, newest LTS"),
]

# Used to rank "current" frameworks found in csproj files.
NETFX_ORDER = ["net40", "net45", "net451", "net452", "net46", "net461", "net462",
               "net47", "net471", "net472", "net48", "net481"]


def available_targets(current_tfm: str | None):
    """Only offer targets newer than what the solution already uses."""
    if current_tfm in NETFX_ORDER:
        idx = NETFX_ORDER.index(current_tfm)
        return [t for t in TARGETS
                if t.kind == "modern" or (t.tfm in NETFX_ORDER and NETFX_ORDER.index(t.tfm) > idx)]
    return TARGETS
