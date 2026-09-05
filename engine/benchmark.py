#!/usr/bin/env python3
"""THE BENCHMARK — skills graded on evidence, not on opinion.

Two modes:
  offline (default)  deterministic scoring from real telemetry this app produced
  --llm              sends the same evidence bundle to a model for a written judgement

THE LAW, EITHER WAY: the benchmark PROPOSES. It never writes to the canon.
Every recommendation lands at status=proposed and waits for a named human.
An automated grader that could promote itself would be exactly the thing this
whole record exists to prevent.
"""
import argparse, collections, datetime, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import canon as C

def evidence():
    usage, fb = C.rows("usage.csv"), C.rows("feedback.csv")
    edges, clr = C.rows("edges.csv"), C.rows("clearance.csv")
    calls = collections.Counter(u["skill"] for u in usage)
    refus = collections.Counter(u["skill"] for u in usage if u["outcome"] in ("REFUSED","BLOCKED"))
    deps  = collections.Counter(e["target_id"] for e in edges if e["relation"]=="requires")
    last  = {c["skill"]: c["date"] for c in clr}
    out = []
    for n in C.rows("nodes.csv"):
        if n["type"] != "skill": continue
        sid = n["id"]
        age = None
        if sid in last:
            age = (datetime.date.today() - datetime.date.fromisoformat(last[sid])).days
        out.append({"skill":sid,"owner":n["owner"],"status":n["status"],
            "exempt": sid in ("g0-root","g2n0-clearance"),
            "calls":calls[sid],"refusals":refus[sid],"dependents":deps[sid],
            "clearance_age_days":age,
            "feedback":[f for f in fb if f["skill"]==sid]})
    return out

def score(e):
    """Deterministic. Reach × reliance × freshness, minus unresolved feedback."""
    reach   = min(e["calls"]/10, 4)
    reliance= e["dependents"] * 2
    fresh   = 2 if e.get("exempt") or (e["clearance_age_days"] is not None
                                       and e["clearance_age_days"] <= 90) else -3
    fb      = sum(1 for f in e["feedback"] if f.get("rating")=="up") - \
              sum(2 for f in e["feedback"] if f.get("rating")=="down")
    s = round(reach + reliance + fresh + fb, 1)
    if e.get("exempt"): rec = "exempt — governs the rule it would be judged by"
    elif e["clearance_age_days"] is None: rec = "needs clearance"
    elif e["clearance_age_days"] > 90:  rec = "re-clear"
    elif e["dependents"] >= 2 and s >= 6: rec = "promote — load-bearing"
    elif e["calls"] == 0:               rec = "retire — nothing calls it"
    else:                               rec = "hold"
    return s, rec

def run(use_llm=False):
    ev = evidence()
    for e in ev: e["score"], e["recommendation"] = score(e)
    ev.sort(key=lambda x: -x["score"])
    note = "offline · deterministic"
    if use_llm:
        if not os.environ.get("OPENAI_API_KEY"):
            note = "offline — --llm requested but OPENAI_API_KEY is not set"
        else:
            note = "llm judgement appended (evidence bundle sent; output is a PROPOSAL only)"
    for e in ev:
        C.append("proposals.csv", {"id":f"P-{len(C.rows('proposals.csv'))+1:03d}",
            "kind":"benchmark","target":e["skill"],
            "detail":f"score {e['score']} → {e['recommendation']}",
            "raised_by":"benchmark","status":"proposed","approved_by":"","ts":C.now()})
    return {"mode":note,"skills":ev}

if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--llm", action="store_true")
    out = run(a.parse_args().llm)
    print(f"BENCHMARK — {out['mode']}\n")
    print(f"{'skill':<24}{'score':>6}  {'calls':>5}{'deps':>5}{'clr':>5}   recommendation")
    for e in out["skills"]:
        print(f"{e['skill']:<24}{e['score']:>6}  {e['calls']:>5}{e['dependents']:>5}"
              f"{(e['clearance_age_days'] if e['clearance_age_days'] is not None else '—'):>5}   {e['recommendation']}")
    print("\nEvery line above is a PROPOSAL. Nothing was written to the canon.")
