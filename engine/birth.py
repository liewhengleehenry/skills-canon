#!/usr/bin/env python3
"""THE BIRTH KIT — only the apex may bring a skill into being.

    python3 engine/birth.py --name tariff-checker --graph G1 --type reader --owner "L. Haddad"

A birth compiles a real FOLDER from the template, writes its card, and lands it at
status=proposed with no clearance. It is not part of the canon until a named human
promotes it, and it cannot run until the clearance skill signs it.
"""
import argparse, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import canon as C

CARD = '''---
name: {sid}
description: "{addr} · {kind} — {problem}"
metadata:
  version: "{ver}"
  address: "{addr}"
  type: "{kind}"
  skill-owner: "{owner}"
  steward-type: "human"
  status: "proposed"
  problem: "{problem}"
---

# {sid}

Born by the apex on {ver}. Proposed, not active: it does not run until
{owner} is confirmed as its named human and the clearance skill has signed it.
'''

def birth(name, graph, kind, owner, caller, problem=""):
    conf = C.cfg()
    apex = conf.get("apex", "g0-root")
    if caller != apex:
        return {"ok": False, "error": f"only the apex ({apex}) may birth a skill — {caller} may not"}
    nodes = C.rows("nodes.csv")
    ns = [int(n["n"][1:]) for n in nodes if n.get("g")==graph and n.get("n","").startswith("N")]
    n = f"N{max(ns)+1 if ns else 0}"
    sid = f"{graph.lower()}{n.lower()}-{name}"
    if any(x["id"]==sid for x in nodes):
        return {"ok": False, "error": f"{sid} already exists"}
    d = C.folder(sid); d.mkdir(parents=True, exist_ok=True)
    addr = f"{graph} · {n}"
    (d/"SKILL.md").write_text(CARD.format(sid=sid, addr=addr, kind=kind, owner=owner,
        ver=C.now()[:10], problem=problem or "stated at birth by the apex"), encoding="utf-8")
    (d/"record").mkdir(exist_ok=True) if kind.startswith("steward") else None
    nodes.append({"id":sid,"prefLabel":sid,"type":"skill","g":graph,"n":n,
        "role":kind,"owner":owner,"owner_role":"business","status":"proposed","version":C.now()[:10]})
    C.write("nodes.csv", nodes, list(nodes[0].keys()))
    edges = C.rows("edges.csv")
    master = next((x["id"] for x in nodes if x.get("g")==graph and x.get("n")=="N0"), None)
    if master: edges.append({"source_id":sid,"target_id":master,"relation":"broader",
        "meaning":f"member of {graph} — born {n}"})
    # WHICH skill inspects is a setting, not a constant — the same one the sweep reads.
    # Point canon.yaml at a different skill and newly born skills declare an edge to that.
    inspector = C.cfg().get("inspector", "")
    if inspector:
        edges.append({"source_id":sid,"target_id":inspector,"relation":"requires",
            "meaning":"its scripts run only after a written PASS from"})
    C.write("edges.csv", edges, list(edges[0].keys()))
    C.append("proposals.csv", {"id":f"P-{len(C.rows('proposals.csv'))+1:03d}","kind":"birth",
        "target":sid,"detail":f"{kind} owned by {owner}","raised_by":caller,
        "status":"proposed","approved_by":"","ts":C.now()})
    C.log(sid, "birth", "PROPOSED", caller)
    return {"ok": True, "skill": sid, "folder": str(d.relative_to(C.ROOT)), "status": "proposed"}

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    for x in ("name","graph","type","owner"): a.add_argument("--"+x, required=True)
    a.add_argument("--caller", default="g0-root")
    r = birth(a.parse_args().name, a.parse_args().graph, a.parse_args().type,
              a.parse_args().owner, a.parse_args().caller)
    print(r)
