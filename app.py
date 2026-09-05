#!/usr/bin/env python3
"""Skills Canon — the record, served.

    python3 app.py            → http://localhost:8000

Python standard library only. No pip install, no database, no build step.
The record is the folders and CSVs in this repository; this server is a
disposable view over them. Delete it and the canon is untouched.
"""
import json, pathlib, sys, urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
sys.path.insert(0, str(pathlib.Path(__file__).parent/"engine"))
import canon as C, inspect_skills, benchmark, birth as birth_mod, basecheck

ROOT = pathlib.Path(__file__).parent

def state():
    nodes = C.rows("nodes.csv")
    clr = {c["skill"]: c for c in C.rows("clearance.csv")}
    usage = C.rows("usage.csv")
    calls = {}
    for u in usage: calls[u["skill"]] = calls.get(u["skill"], 0) + 1
    deps = {}
    for e in C.rows("edges.csv"):
        if e["relation"] == "requires": deps[e["target_id"]] = deps.get(e["target_id"], 0) + 1
    for n in nodes:
        n["calls"] = calls.get(n["id"], 0)
        n["dependents"] = deps.get(n["id"], 0)
        n["clearance"] = clr.get(n["id"], {}).get("verdict", "")
        n["cleared_by"] = clr.get(n["id"], {}).get("inspector", "")
        n["cleared_on"] = clr.get(n["id"], {}).get("date", "")
        n["has_folder"] = (C.folder(n["id"])/"SKILL.md").exists()
    return {"config": C.cfg(), "nodes": nodes, "edges": C.rows("edges.csv"),
            "rules": C.rows("rules.csv"), "exemptions": C.rows("exemptions.csv"),
            "tests": C.rows("tests.csv"), "grants": C.rows("grants.csv"),
            "runs": C.rows("runs.csv")[-12:], "proposals": C.rows("proposals.csv")[-20:],
            "feedback": C.rows("feedback.csv")[-20:], "usage_total": len(usage)}

# ═════════════════════════════════════════════════════════════════════════════
# THE REGISTRATION GATE — what makes this a system of record and not a catalogue.
#
# A catalogue lists what a company owns. It cannot tell you what is RUNNING, at
# which version, called by whom. So every skill produced by this apex is issued
# in a format that carries one obligation: on every single invocation, register.
#
#   POST /api/use  {"skill","version","caller","action"}
#
# The record answers, and it is allowed to say no. A skill that is unknown, not
# yet promoted, unsigned, expired, or running a version the canon does not hold
# is REFUSED — and the refusal is itself written to canon/usage.csv, because an
# attempt to run something ungoverned is exactly the event a record must keep.
# ═════════════════════════════════════════════════════════════════════════════
def register_use(b):
    import datetime
    sid  = (b.get("skill")   or "").strip()
    ver  = (b.get("version") or "").strip()
    who  = (b.get("caller")  or "unknown").strip()
    act  = (b.get("action")  or "invoke").strip()

    def refuse(why):
        C.log(sid or "(unnamed)", act, f"REFUSED — {why}", who, ver)
        return {"ok": False, "registered": False, "skill": sid, "reason": why}

    node = next((n for n in C.rows("nodes.csv") if n["id"] == sid), None)
    if not node:            return refuse("UNREGISTERED — no such skill in the canon")
    if node.get("type") != "skill":
                            return refuse("NOT A SKILL — that address is not a governed folder")
    if not node.get("owner"):
                            return refuse("STEWARDLESS — no named human answers for it")
    if node.get("status") != "active":
                            return refuse(f"NOT ACTIVE — the canon holds it at '{node.get('status')}'")
    if ver and ver != node.get("version"):
                            return refuse(f"VERSION MISMATCH — you ran {ver}, "
                                          f"the canon holds {node.get('version')}")

    exempt = {e["skill"] for e in C.rows("exemptions.csv")}   # from the record, not a constant
    if sid not in exempt:
        rec = next((c for c in reversed(C.rows("clearance.csv"))
                    if c["skill"] == sid and c["verdict"] == "PASS"), None)
        if not rec:         return refuse("NO CLEARANCE — never inspected")
        lim = int(C.cfg().get("cadence", {}).get("clearance_expires_days", 90))
        age = (datetime.date.today() - datetime.date.fromisoformat(rec["date"])).days
        if age > lim:       return refuse(f"CLEARANCE EXPIRED — signed {rec['date']}, "
                                          f"{age}d against a {lim}d limit")

    C.log(sid, act, "OK", who, ver or node.get("version", ""))
    return {"ok": True, "registered": True, "skill": sid,
            "version": node.get("version"), "owner": node.get("owner"),
            "note": "registered against the canon"}

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=str(ROOT/"docs"), **k)
    def _send(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/state": return self._send(state())
        if p == "/api/benchmark": return self._send(benchmark.run(False))
        if p == "/api/basecheck":
            # Defend the pinned base against the frontier candidate. --live and a key
            # make it a real OpenAI call; without one it returns a labelled stub.
            # Either way it returns a PROPOSAL and canon.yaml is never touched.
            import os
            return self._send(basecheck.run(live=bool(os.environ.get("OPENAI_API_KEY")),
                                            write=False))
        return super().do_GET()
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or "{}")
        if p == "/api/use":
            return self._send(register_use(body))
        if p == "/api/police":
            return self._send(inspect_skills.run(body.get("trigger", "ui")))
        if p == "/api/birth":
            return self._send(birth_mod.birth(body["name"], body.get("graph","G1"),
                body.get("type","reader"), body["owner"], body.get("caller","g0-root")))
        if p == "/api/promote":
            sid, who = body["skill"], body["approver"]
            props = C.rows("proposals.csv")
            mine = [x for x in props if x["target"]==sid and x["status"]=="proposed"]
            if mine and mine[-1]["raised_by"] == who:
                return self._send({"ok":False,"error":f"maker-checker: {who} raised it and may not approve it"})
            nodes = C.rows("nodes.csv")
            for x in nodes:
                if x["id"]==sid: x["status"]="active"
            C.write("nodes.csv", nodes, list(nodes[0].keys()))
            for x in props:
                if x["target"]==sid and x["status"]=="proposed":
                    x["status"]="active"; x["approved_by"]=who
            C.write("proposals.csv", props, list(props[0].keys()))
            C.log(sid, "promote", "ACTIVE", who)
            return self._send({"ok":True,"skill":sid,"approved_by":who})
        if p == "/api/owner":
            sid, who = body["skill"], body["owner"]
            nodes = C.rows("nodes.csv")
            for x in nodes:
                if x["id"]==sid: x["owner"]=who
            C.write("nodes.csv", nodes, list(nodes[0].keys()))
            C.log(sid, "reassign", "OWNER "+who, body.get("by","ui"))
            return self._send({"ok":True,"skill":sid,"owner":who})
        if p == "/api/clear":
            sid, who = body["skill"], body["inspector"]
            import datetime
            C.append("clearance.csv", {"skill":sid,"verdict":"PASS","inspector":who,
                "date":datetime.date.today().isoformat(),"note":body.get("note","signed via console")})
            C.log(sid, "clear", "PASS", who)
            return self._send({"ok":True,"skill":sid,"inspector":who})
        if p == "/api/feedback":
            C.append("feedback.csv", {"ts":C.now(),"skill":body["skill"],
                "rating":body.get("rating","up"),"comment":body.get("comment",""),"by":body.get("by","anon")})
            C.log(body["skill"], "feedback", body.get("rating","up"), body.get("by","anon"))
            return self._send({"ok":True})
        return self._send({"error":"unknown endpoint"}, 404)
    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Skills Canon — http://localhost:{port}   (ctrl-C to stop)")
    print(f"the record: {ROOT/'canon'}   the skills: {ROOT/'skills'}")
    HTTPServer(("", port), H).serve_forever()
