"""Step 2: build the knowledge base (KB) of the whole solution.

Deterministic facts come from static parsing; the LLM then adds a business/functional
summary per project. Everything lands in <repo>/.modernizer/kb/.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .config import NETFX_ORDER

SKIP_DIRS = {"bin", "obj", "packages", "node_modules", ".git", ".vs", ".modernizer"}
CODE_EXT = {".cs", ".vb", ".cshtml", ".aspx", ".ascx", ".master", ".svc", ".asmx", ".asax"}
SLN_RE = re.compile(r'Project\("\{[^}]+\}"\)\s*=\s*"([^"]+)",\s*"([^"]+\.(?:cs|vb)proj)"')
RISK_MARKERS = {
    "System.Web": "System.Web (not available in modern .NET)",
    "HttpContext.Current": "HttpContext.Current",
    "ConfigurationManager": "ConfigurationManager / web.config",
    "System.Data.Entity": "Entity Framework 6",
    "Microsoft.Owin": "OWIN/Katana",
    "System.ServiceModel": "WCF",
    "System.Runtime.Remoting": "Remoting",
    "AppDomain": "AppDomain",
    "System.Web.Services": "ASMX",
    "Session[": "ASP.NET Session",
    "BinaryFormatter": "BinaryFormatter",
    "System.Drawing": "System.Drawing",
}


def _tag(el): return el.tag.split("}")[-1]


def norm_tfm(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip()
    m = re.match(r"^v(\d)\.(\d)(?:\.(\d))?$", v)
    return "net" + "".join(g for g in m.groups() if g) if m else v.split(";")[0]


def _walk(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS):
            yield p


def parse_project(path: Path, root: Path) -> dict:
    r = ET.parse(path).getroot()
    props, refs, pkgs = {}, [], []
    for el in r.iter():
        t = _tag(el)
        if t in ("TargetFramework", "TargetFrameworks", "TargetFrameworkVersion",
                 "OutputType", "ProjectTypeGuids") and el.text:
            props[t] = el.text.strip()
        elif t == "ProjectReference" and el.get("Include"):
            refs.append(Path(el.get("Include").replace("\\", "/")).stem)
        elif t == "PackageReference":
            ver = el.get("Version") or next((c.text for c in el if _tag(c) == "Version"), None)
            pkgs.append({"id": el.get("Include"), "version": ver})
    pc = path.parent / "packages.config"
    if pc.exists():
        for el in ET.parse(pc).getroot():
            pkgs.append({"id": el.get("id"), "version": el.get("version")})
    tfm = norm_tfm(props.get("TargetFramework") or props.get("TargetFrameworks")
                   or props.get("TargetFrameworkVersion"))
    guids = props.get("ProjectTypeGuids", "").upper()
    is_web = "349C5851" in guids or "E3E379DF" in guids or (path.parent / "Web.config").exists()
    return {
        "name": path.stem, "path": str(path.relative_to(root)),
        "sdk_style": r.get("Sdk") is not None, "tfm": tfm,
        "output_type": props.get("OutputType", "Library"),
        "is_web": is_web, "is_test": "test" in path.stem.lower(),
        "project_refs": refs, "packages": pkgs,
    }


def scan_code(proj_dir: Path):
    info = {"controllers": [], "routes": [], "pages": [], "services": [], "risks": {}, "loc": 0}
    for f in _walk(proj_dir):
        if f.suffix.lower() not in CODE_EXT:
            continue
        text = f.read_text(errors="ignore")
        info["loc"] += text.count("\n")
        rel = str(f.relative_to(proj_dir))
        if f.suffix in (".aspx",):
            info["pages"].append("/" + rel.replace("\\", "/"))
        if f.suffix in (".svc", ".asmx"):
            info["services"].append(rel)
        for m in re.finditer(r"class\s+(\w+)Controller\b", text):
            ctrl = m.group(1)
            info["controllers"].append(ctrl)
            for a in re.finditer(r"public\s+(?:virtual\s+|async\s+)*(?:Task<)?"
                                 r"(?:ActionResult|ViewResult|IActionResult|JsonResult)>?\s+(\w+)\s*\(", text):
                info["routes"].append(f"/{ctrl}/{a.group(1)}")
        for m in re.finditer(r'\[Route\("([^"]+)"\)\]', text):
            info["routes"].append("/" + m.group(1).lstrip("/"))
        for marker, label in RISK_MARKERS.items():
            n = text.count(marker)
            if n:
                info["risks"][label] = info["risks"].get(label, 0) + n
    info["routes"] = sorted(set(info["routes"]))
    return info


def scan_config(root: Path):
    out = {"app_settings": [], "connection_strings": []}  # keys/names only, never values
    for f in _walk(root):
        if f.name.lower() in ("web.config", "app.config"):
            try:
                for el in ET.parse(f).getroot().iter():
                    if _tag(el) == "add" and el.get("key"):
                        out["app_settings"].append(el.get("key"))
                    elif _tag(el) == "add" and el.get("connectionString"):
                        out["connection_strings"].append(el.get("name"))
            except ET.ParseError:
                pass
    out["app_settings"] = sorted(set(out["app_settings"]))
    out["connection_strings"] = sorted(set(out["connection_strings"]))
    return out


def build(repo: Path) -> dict:
    slns = [str(p.relative_to(repo)) for p in _walk(repo) if p.suffix == ".sln"]
    csprojs = [p for p in _walk(repo) if p.suffix in (".csproj", ".vbproj")]
    projects = []
    for p in csprojs:
        d = parse_project(p, repo)
        d.update(scan_code(p.parent))
        projects.append(d)
    tfms = [p["tfm"] for p in projects if p["tfm"] in NETFX_ORDER]
    current = max(tfms, key=NETFX_ORDER.index) if tfms else None
    kb = {"solutions": slns, "current_tfm": current, "projects": projects,
          "config": scan_config(repo)}
    out = repo / ".modernizer" / "kb"
    out.mkdir(parents=True, exist_ok=True)
    (out / "kb.json").write_text(json.dumps(kb, indent=2))
    (out / "overview.md").write_text(render_overview(kb))
    return kb


def render_overview(kb: dict) -> str:
    L = ["# Solution knowledge base", f"Solutions: {', '.join(kb['solutions'])}",
         f"Current framework (highest): `{kb['current_tfm']}`", "", "## Projects"]
    for p in kb["projects"]:
        L += [f"### {p['name']}  (`{p['tfm']}`, {p['output_type']}{', web' if p['is_web'] else ''})",
              f"- path: `{p['path']}`  | LOC: {p['loc']} | SDK-style: {p['sdk_style']}",
              f"- depends on: {', '.join(p['project_refs']) or '—'}",
              f"- packages: {', '.join(f'{k['id']} {k['version']}' for k in p['packages']) or '—'}",
              f"- controllers: {', '.join(p['controllers']) or '—'}",
              f"- routes: {', '.join(p['routes'][:30]) or '—'}",
              f"- web forms pages: {len(p['pages'])} | WCF/ASMX: {len(p['services'])}",
              f"- migration risks: {p['risks'] or '—'}", ""]
    L += ["## Configuration (names only)", f"- appSettings: {kb['config']['app_settings']}",
          f"- connection strings: {kb['config']['connection_strings']}"]
    return "\n".join(L)
