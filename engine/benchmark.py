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
    # Who is exempt is a row in canon/exemptions.csv naming who granted it and when it
    # expires — never a constant in this file. Delete the row and the exemption is gone.
    exempt = {e["skill"] for e in C.rows("exemptions.csv")}
    out = []
    for n in C.rows("nodes.csv"):
        if n["type"] != "skill": continue
        sid = n["id"]
        age = None
        if sid in last:
            age = (datetime.date.today() - datetime.date.fromisoformat(last[sid])).days
        out.append({"skill":sid,"owner":n["owner"],"status":n["status"],
            "exempt": sid in exempt,
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

def bundle(e):
    """The exact evidence a model would be sent. Nothing else is in scope."""
    return {"skill":e["skill"],"owner":e["owner"],"status":e["status"],"exempt":e["exempt"],
            "calls":e["calls"],"refusals":e["refusals"],"dependents":e["dependents"],
            "clearance_age_days":e["clearance_age_days"],
            "feedback":[{"rating":f.get("rating"),"note":f.get("note","")} for f in e["feedback"]]}

def judge(e):
    """LOCAL STAND-IN for the model call. This writes the sentence a grader would write,
    from the same bundle, with no network and no key. It is deliberately not a model:
    a benchmark that can reach the internet is a benchmark the record cannot audit.
    Swapping this for a real API call means replacing this one function — the bundle
    it receives and the proposal it must return are already fixed by the law below."""
    b, out = bundle(e), []
    if b["exempt"]:
        return ("Structurally exempt. It holds or issues the rule it would be judged by, so "
                "any score here would be self-issued. Not graded — by design.")
    if b["clearance_age_days"] is None:
        out.append("No signature on file: it has never been inspected, so nothing it does is "
                   "attributable to anyone. That alone disqualifies it from running.")
    elif b["clearance_age_days"] > 90:
        out.append(f"Its PASS is {b['clearance_age_days']} days old and has lapsed. An owner "
                   "who signed three months ago did not sign what is there now.")
    if b["dependents"] >= 2:
        out.append(f"{b['dependents']} other skills declare a hard requires-edge on it, so its "
                   "failure is not local — it is the graph's failure.")
    elif b["dependents"] == 1:
        out.append("One skill depends on it. Load-bearing, but narrowly.")
    if b["calls"] == 0:
        out.append("Zero calls in the telemetry. Nothing in this company reaches for it; the "
                   "honest recommendation is retirement, not improvement.")
    if b["refusals"]:
        out.append(f"{b['refusals']} of its {b['calls']} calls ended in a refusal or a block. "
                   "Read that as working, not failing: it declined rather than guessed.")
    down = [f for f in b["feedback"] if f["rating"] == "down"]
    if down:
        out.append(f"{len(down)} negative report(s) from named people, unresolved. "
                   "Human evidence outranks call volume.")
    return " ".join(out) or ("Signed, current, and used. Nothing in the evidence argues for a "
                             "change of status.")


# ─────────────────────────────────────────────────────────────────────────────
# THE REAL MODEL CALL. Stdlib only — urllib, no `pip install openai`.
# Set OPENAI_API_KEY and pass --llm --live. Without the key it falls back to
# judge() and says so. The law does not change: this returns PROSE that lands
# in proposals.csv as a PROPOSAL. It cannot promote, clear, or write the canon.
# ─────────────────────────────────────────────────────────────────────────────
import json, urllib.request

SYSTEM = (
 "You grade skills in a governed enterprise skill registry. You are given ONLY the "
 "evidence the system itself produced. Rules you must obey: (1) judge from the evidence "
 "given and never invent a fact; (2) a skill with no clearance may not run, whatever its "
 "usage; (3) a refusal is evidence of correct behaviour, not failure; (4) you PROPOSE — a "
 "named human disposes. Answer in 2-3 sentences of plain prose. No bullet points, no "
 "preamble, no score.")

def judge_openai(e, model="gpt-4o-mini", timeout=20):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return judge(e) + "  [no OPENAI_API_KEY — local stand-in used]"
    body = json.dumps({"model": model, "temperature": 0, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(bundle(e), ensure_ascii=False)}]}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception as ex:
        return judge(e) + f"  [model call failed: {type(ex).__name__} — local stand-in used]"

def run(use_llm=False, live=False):
    ev = evidence()
    for e in ev: e["score"], e["recommendation"] = score(e)
    ev.sort(key=lambda x: -x["score"])
    note = "offline · deterministic"
    if use_llm:
        if live and os.environ.get("OPENAI_API_KEY"):
            note = "written judgement · OpenAI · evidence bundle only · output is a PROPOSAL"
            for e in ev: e["judgement"] = judge_openai(e)
        else:
            note = "written judgement · LOCAL STAND-IN — no model was called"
            for e in ev: e["judgement"] = judge(e)
    for e in ev:
        C.append("proposals.csv", {"id":f"P-{len(C.rows('proposals.csv'))+1:03d}",
            "kind":"benchmark","target":e["skill"],
            "detail":f"score {e['score']} → {e['recommendation']}",
            "raised_by":"benchmark","status":"proposed","approved_by":"","ts":C.now()})
    return {"mode":note,"skills":ev}

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--llm", action="store_true", help="written judgement in prose")
    a.add_argument("--live", action="store_true", help="use OpenAI instead of the local stand-in")
    ns = a.parse_args()
    out = run(ns.llm, ns.live)
    print(f"BENCHMARK — {out['mode']}\n")
    print(f"{'skill':<24}{'score':>6}  {'calls':>5}{'deps':>5}{'clr':>5}   recommendation")
    for e in out["skills"]:
        print(f"{e['skill']:<24}{e['score']:>6}  {e['calls']:>5}{e['dependents']:>5}"
              f"{(e['clearance_age_days'] if e['clearance_age_days'] is not None else '—'):>5}   {e['recommendation']}")
    if out["skills"] and "judgement" in out["skills"][0]:
        print("\nWRITTEN JUDGEMENT — from the same evidence bundle, no model call:\n")
        for e in out["skills"]:
            print(f"  {e['skill']}\n      {e['judgement']}\n")
    print("\nEvery line above is a PROPOSAL. Nothing was written to the canon.")
