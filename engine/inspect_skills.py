#!/usr/bin/env python3
"""THE POLICING — G2·N0 clearance inspects every governed skill.

Three passes, all deterministic. No model reads this; code decides.
  FORMAT      the folder exists and its card carries the required keys
  CONTENT     the graph vouches for it and it names a human
  CLEARANCE   a written PASS exists and has not expired
A skill that fails any pass is BLOCKED until a named human signs it.
"""
import datetime, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import canon as C

REQUIRED = ["version","address","type","skill-owner","status"]

def card(skill_id):
    p = C.folder(skill_id)/"SKILL.md"
    if not p.exists(): return None
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if ":" in line and line.startswith("  "):
            k,_,v = line.strip().partition(":"); out[k.strip()] = v.strip().strip('"')
    return out

EXEMPT = {
    "g0-root":       "the apex holds the law it applies — it cannot be judged by its own rule",
    "g2n0-clearance":"the clearance skill cannot clear itself — no self-approval, ever",
}

def inspect_one(node, clearance, expires_days, apex="g0-root"):
    sid, findings = node["id"], []
    if node["type"] != "skill": return None
    if sid in EXEMPT:
        return {"skill": sid, "owner": node.get("owner",""), "findings": [],
                "verdict": "EXEMPT", "why": EXEMPT[sid]}
    c = card(sid)
    if c is None: findings.append("NO FOLDER — the canon vouches for a skill nobody holds")
    else:
        for k in REQUIRED:
            if k not in c: findings.append(f"CARD MISSING {k}")
    if not node.get("owner","").strip(): findings.append("STEWARDLESS — no named human")
    cl = [x for x in clearance if x["skill"] == sid]
    if not cl:
        findings.append("NO CLEARANCE — never inspected")
    else:
        last = cl[-1]
        if last["verdict"] != "PASS": findings.append(f"CLEARANCE {last['verdict']}")
        else:
            age = (datetime.date.today() - datetime.date.fromisoformat(last["date"])).days
            if age > expires_days: findings.append(f"CLEARANCE EXPIRED — {age}d old, limit {expires_days}")
    return {"skill": sid, "owner": node.get("owner",""), "findings": findings,
            "verdict": "PASS" if not findings else "BLOCKED", "why": ""}

def run(trigger="manual"):
    conf = C.cfg()
    expires = int(conf.get("cadence",{}).get("clearance_expires_days", 90))
    nodes, clearance = C.rows("nodes.csv"), C.rows("clearance.csv")
    results = [r for r in (inspect_one(n, clearance, expires) for n in nodes) if r]
    passed = [r for r in results if r["verdict"] in ("PASS","EXEMPT")]
    blocked = [r for r in results if r["verdict"]=="BLOCKED"]
    run_id = f"R-{len(C.rows('runs.csv'))+1:04d}"
    C.append("runs.csv", {"run_id":run_id,"ts":C.now(),"trigger":trigger,
        "skills_checked":len(results),"passed":len(passed),"failed":0,
        "blocked":len(blocked),
        "note":"; ".join(f"{r['skill']}: {r['findings'][0]}" for r in blocked) or "all clear"})
    for r in results: C.log(r["skill"], "police", r["verdict"], "g2n0-clearance")
    return {"run_id":run_id,"results":results,"passed":len(passed),"blocked":len(blocked)}

if __name__ == "__main__":
    out = run("cli")
    print(f"{out['run_id']}  checked {len(out['results'])}  PASS {out['passed']}  BLOCKED {out['blocked']}")
    for r in out["results"]:
        mark = {"PASS":"✓","EXEMPT":"·","BLOCKED":"✗"}[r["verdict"]]
        print(f"  {mark} {r['skill']:<24} ◆ {r['owner']}")
        if r.get("why"): print(f"      → exempt: {r['why']}")
        for f in r["findings"]: print(f"      → {f}")
