"""COS full system test — all endpoints."""
import uvicorn, threading, time, urllib.request, urllib.parse, json

def run():
    uvicorn.run("cos.api.main:app", host="127.0.0.1", port=8770, log_level="error")
t = threading.Thread(target=run, daemon=True); t.start(); time.sleep(2)

BASE = "http://127.0.0.1:8770"
passed, failed, issues = 0, 0, []

def test(name, url, check_fn=None, method="GET", body=None):
    global passed, failed
    try:
        if method == "POST":
            req = urllib.request.Request(f"{BASE}{url}", data=json.dumps(body).encode() if body else b"",
                                         headers={"Content-Type": "application/json"})
        else:
            req = urllib.request.Request(f"{BASE}{url}")
        r = urllib.request.urlopen(req, timeout=10)
        data = json.loads(r.read())
        if check_fn:
            ok, detail = check_fn(data)
        else:
            ok, detail = True, "OK"
        if ok:
            passed += 1; print(f"  OK  {name}")
        else:
            failed += 1; issues.append(f"{name}: {detail}"); print(f"  FAIL {name} -- {detail}")
    except Exception as e:
        failed += 1; issues.append(f"{name}: {str(e)[:80]}"); print(f"  FAIL {name} -- {str(e)[:80]}")

def test_html(name, url, check_str):
    global passed, failed
    try:
        r = urllib.request.urlopen(f"{BASE}{url}", timeout=10)
        html = r.read().decode()
        if check_str in html:
            passed += 1; print(f"  OK  {name}")
        else:
            failed += 1; issues.append(f"{name}: missing '{check_str}'"); print(f"  FAIL {name}")
    except Exception as e:
        failed += 1; issues.append(f"{name}: {str(e)[:80]}"); print(f"  FAIL {name} -- {str(e)[:80]}")

print("=" * 60)
print("COS FULL SYSTEM TEST")
print("=" * 60)

# DASHBOARD
print("\n--- DASHBOARD ---")
test("Dashboard loads", "/api/dashboard", lambda d: (len(d.get("counts", {})) >= 8, f"{len(d.get('counts', {}))} counts"))
test("Entities > 0", "/api/dashboard", lambda d: (d["counts"].get("entities", 0) > 0, f"entities={d['counts'].get('entities')}"))
test("Notifications", "/api/dashboard", lambda d: (isinstance(d.get("notifications"), list), "ok"))
test("Recent activity", "/api/dashboard", lambda d: (isinstance(d.get("recent_activity"), list), "ok"))

# FRONTEND
print("\n--- FRONTEND ---")
test_html("Frontend loads", "/", "Cognitive Operating System")
test_html("React loaded", "/", "react")
test_html("Quick actions", "/", "Quick Actions")
test_html("SAR nav", "/", "SAR Analysis")
test_html("Report nav", "/", "Report")

# INGEST
print("\n--- INGEST ---")
test("Ingest valid file", "/api/ingest/path?file_path=C%3A%5CUsers%5CKerwyn%5CPycharmProjects%5Cmms-extractor%5Cdata%5Ccompounds.csv", None, "POST")
test("Ingest bad file", "/api/ingest/path?file_path=NONEXISTENT.csv", lambda d: (d.get("status") == "error", "correctly rejected"), "POST")

# CHAT LOCAL
print("\n--- CHAT (LOCAL) ---")
for q, label in [("what+is+CETP", "What is CETP"), ("tell+me+about+ind", "Tell me about ind"),
                  ("most+potent+compounds", "Most potent"), ("compare+benz+vs+ind", "Compare"),
                  ("show+me+hypotheses", "Hypotheses"), ("help", "Help"), ("xyzzy+foobar", "Gibberish")]:
    test(label, f"/api/chat?q={q}", lambda d: (d["answer_count"] > 0, f"{d['answer_count']} answers"))
test("Suggestions", "/api/chat/suggestions", lambda d: (len(d) >= 5, f"{len(d)} suggestions"))

# CHAT AI
print("\n--- CHAT (AI) ---")
test("AI cached", "/api/llm/ask?q=Which+scaffold+should+we+prioritize+and+why", lambda d: ("answer" in d, "has answer"))
test("AI spend", "/api/llm/spend", lambda d: ("total_spend" in d, f"spend={d.get('total_spend')}"))

# SAR
print("\n--- SAR ANALYSIS ---")
test("Scaffold profiles", "/api/sar/scaffolds", lambda d: (len(d) == 6, f"{len(d)} scaffolds"))
test("All have activity", "/api/sar/scaffolds", lambda d: (all(s.get("avg_pIC50") for s in d), "ok"))
test("Heatmap data", "/api/sar/heatmap", lambda d: (len(d) >= 30, f"{len(d)} points"))
test("Compare benz/ind", "/api/sar/compare/benz/ind", lambda d: (d.get("winner") == "ind", f"winner={d.get('winner')}"))
test("Compare quin/naph", "/api/sar/compare/quin/naph", lambda d: ("winner" in d, "ok"))

# GRAPH
print("\n--- GRAPH ---")
test("Graph stats", "/api/graph/stats", lambda d: (d.get("nodes", 0) > 0, f"nodes={d.get('nodes')}"))
test("Subgraph benz d1", "/api/graph/benz?depth=1", lambda d: (d.get("node_count", 0) > 5, f"{d.get('node_count')} nodes"))
test("Subgraph ind d2", "/api/graph/ind?depth=2", lambda d: (d.get("node_count", 0) > 0, f"{d.get('node_count')} nodes"))
test("Neighbors benz_001_F", "/api/graph/neighbors/benz_001_F", lambda d: (len(d) >= 1, f"{len(d)} neighbors"))

# MEMORY
print("\n--- MEMORY ---")
test("Entities", "/api/entities", lambda d: (len(d) >= 44, f"{len(d)} entities"))
test("Concepts", "/api/concepts", lambda d: (len(d) >= 5, f"{len(d)} concepts"))
test("Gaps", "/api/gaps", lambda d: ("total_gaps" in d, f"gaps={d.get('total_gaps')}"))
test("Domains", "/api/domains", lambda d: (len(d) >= 1, f"{len(d)} domains"))
test("Search CETP", "/api/search?q=CETP&top_k=5", lambda d: (len(d) >= 1, f"{len(d)} results"))
test("Scores", "/api/memory/scores?limit=5", lambda d: (len(d) >= 1, f"{len(d)} scores"))

# PROVENANCE
print("\n--- PROVENANCE ---")
test("Provenance stats", "/api/provenance/stats", lambda d: (d.get("total", 0) > 100, f"total={d.get('total')}"))
test("Provenance recent", "/api/provenance/recent", lambda d: (len(d) >= 10, f"{len(d)} links"))

# REASONING
print("\n--- REASONING ---")
test("Hypotheses", "/api/hypotheses", lambda d: (len(d) >= 6, f"{len(d)} hypotheses"))
test("Insights", "/api/insights", lambda d: (len(d) >= 1, f"{len(d)} insights"))
test("Uncertainty", "/api/uncertainty", lambda d: (d.get("overall_confidence", 0) > 0.5, f"conf={d.get('overall_confidence')}"))
test("Patterns", "/api/patterns", lambda d: (len(d.get("scaffold_patterns", [])) >= 5, f"{len(d.get('scaffold_patterns', []))} patterns"))
test("Contradictions", "/api/contradictions", lambda d: (isinstance(d, list), f"{len(d)} items"))

# DECISIONS
print("\n--- DECISIONS ---")
test("Decisions list", "/api/decisions", lambda d: (len(d) >= 1, f"{len(d)} decisions"))
test("Decision board", "/api/decisions/board/view", lambda d: (isinstance(d, list), f"{len(d)} on board"))
test("Generate actions", "/api/decisions/generate-actions", lambda d: (len(d) >= 1, f"{len(d)} actions"), "POST")

# WORKFLOWS
print("\n--- WORKFLOWS ---")
test("Templates", "/api/workflows/templates", lambda d: (len(d) >= 3, f"{len(d)} templates"))
test("Runs", "/api/workflows/runs", lambda d: (isinstance(d, list), f"{len(d)} runs"))
test("Stats", "/api/workflows/stats", lambda d: ("total_runs" in d, "ok"))

# AUTONOMOUS
print("\n--- AUTONOMOUS ---")
test("Monitor", "/api/auto/monitor", lambda d: ("overall" in d, f"status={d.get('overall')}"))
test("Priorities", "/api/auto/priorities", lambda d: (isinstance(d, list), f"{len(d)} priorities"))
test("Cost optimize", "/api/auto/optimize", lambda d: ("total_cost" in d, "ok"))

# INTELLIGENCE
print("\n--- INTELLIGENCE ---")
test("Agents", "/api/intel/agents", lambda d: (len(d) >= 3, f"{len(d)} agents"))
test("Meta reasoning", "/api/intel/meta", lambda d: ("meta_score" in d, f"score={d.get('meta_score')}"))

# REPORT
print("\n--- REPORT ---")
test("Report gen", "/api/report/default", lambda d: (len(d.get("sections", [])) >= 4, f"{len(d.get('sections', []))} sections"))

# NOTIFICATION DETAILS
print("\n--- NOTIFICATIONS ---")
test("Conflicts", "/api/conflicts", lambda d: (isinstance(d, list), f"{len(d)} conflicts"))
test("Low confidence", "/api/low-confidence", lambda d: (isinstance(d, list), f"{len(d)} items"))

# HEALTH
print("\n--- HEALTH ---")
test("System health", "/api/health", lambda d: ("modules" in d, "ok"))

# DATA PAGES
print("\n--- DATA PAGES ---")
test("Episodes", "/api/episodes", lambda d: (isinstance(d, list), f"{len(d)} episodes"))
test("Documents", "/api/documents", lambda d: (isinstance(d, list), f"{len(d)} documents"))
test("Artifacts", "/api/artifacts", lambda d: (isinstance(d, list), f"{len(d)} artifacts"))
test("Investigations", "/api/investigations", lambda d: (isinstance(d, list), f"{len(d)} investigations"))

# SUMMARY
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
print("=" * 60)
if issues:
    print(f"\nISSUES ({len(issues)}):")
    for i in issues:
        print(f"  - {i}")
else:
    print("\nALL TESTS PASSED")
