"""Skills Canon — read and write the record. Folders are the unit; the canon is the record."""
import csv, datetime, pathlib, re, hashlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
CANON, SKILLS = ROOT/"canon", ROOT/"skills"

def now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def rows(name):
    p = CANON/name
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []
def write(name, data, fields):
    with (CANON/name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(data)
def append(name, row):
    p = CANON/name; new = not p.exists() or p.stat().st_size == 0
    with p.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row)); 
        if new: w.writeheader()
        w.writerow(row)
def log(skill, action, outcome, caller="ui"):
    append("usage.csv", {"ts":now(),"skill":skill,"action":action,"outcome":outcome,"caller":caller})

def cfg():
    """canon.yaml, read without a yaml dependency — flat two-level keys only."""
    out, sect = {}, None
    for line in (ROOT/"canon.yaml").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"): continue
        if not line.startswith(" "):
            k, _, v = line.partition(":"); sect = k.strip()
            v = v.split("#")[0].strip()
            out[sect] = v if v else {}
        else:
            k, _, v = line.strip().partition(":")
            if isinstance(out.get(sect), dict): out[sect][k.strip()] = v.strip().split("#")[0].strip()
    return out

def folder(skill_id): return SKILLS/skill_id
def content_hash(skill_id):
    d = folder(skill_id)
    if not d.exists(): return ""
    h = hashlib.sha256()
    for f in sorted(d.rglob("*")):
        if f.is_file(): h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()[:12]
