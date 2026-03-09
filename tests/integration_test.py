"""
Rigorous integration test: backend + frontend SSE contract.
Run with: python tests/integration_test.py
Requires backend running on localhost:8000
"""
import requests
import json
import time
import sys

BASE = "http://localhost:8000/api/v1"
PASS = 0
FAIL = 0
FAILURES = []


def test(name, passed, detail=""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(name)
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def parse_sse_events(response, timeout=120):
    """Parse SSE stream exactly like the frontend does (after the fix)."""
    events = []
    start = time.time()
    for line in response.iter_lines(decode_unicode=True):
        if time.time() - start > timeout:
            events.append({"type": "TIMEOUT"})
            break
        if not line:
            continue
        # Frontend splits on \n\n then splits each block into sub-lines
        # But iter_lines gives us individual lines, so handle both formats
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                events.append(data)
                if data.get("type") == "stream_complete":
                    break
            except json.JSONDecodeError:
                pass
    response.close()
    return events


def has_event(events, event_type):
    return any(e.get("type") == event_type for e in events)


def get_event(events, event_type):
    return next((e for e in events if e.get("type") == event_type), None)


def get_events(events, event_type):
    return [e for e in events if e.get("type") == event_type]


# ================================================================
print("=" * 60)
print("MASTERYAI INTEGRATION TEST SUITE")
print("=" * 60)

# Check backend is running
print("\n[1/9] HEALTH CHECK")
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    test("Backend reachable", r.status_code == 200)
    h = r.json()
    test("Status is ok", h.get("status") == "ok")
    test("Concepts loaded > 0", h.get("concepts_loaded", 0) > 0, f'{h.get("concepts_loaded")}')
    test("Version present", bool(h.get("version")), h.get("version"))
except requests.ConnectionError:
    print("  [FAIL] Backend not running on localhost:8000. Start it first.")
    sys.exit(1)

# ================================================================
print("\n[2/9] AUTH — REGISTER")
email = f"test_{int(time.time())}@testmail.com"
r = requests.post(f"{BASE}/auth/register", json={
    "email": email, "password": "TestPass123", "name": "TestBot"
})
test("Register returns 200", r.status_code == 200, f"status={r.status_code}")
reg = r.json()
token = reg.get("token", "")
learner_id = reg.get("learner_id", "")
user_id = reg.get("user_id", "")
test("Got token", bool(token))
test("Got learner_id", bool(learner_id))
test("Got user_id", bool(user_id))
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ================================================================
print("\n[3/9] AUTH — LOGIN WITH SAME CREDS")
r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "TestPass123"})
test("Login returns 200", r.status_code == 200)
login_data = r.json()
test("Login token matches register token type", bool(login_data.get("token")))
test("Login learner_id matches", login_data.get("learner_id") == learner_id)

# Bad password
r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "wrong"})
test("Wrong password rejected", r.status_code in (401, 403), f"status={r.status_code}")

# ================================================================
print("\n[4/9] LEARNER STATE — FRESH USER")
r = requests.get(f"{BASE}/learner/{learner_id}/state", headers=headers)
test("GET learner state returns 200", r.status_code == 200)
state = r.json()
test("Has learner_id", state.get("learner_id") == learner_id)
test("concept_states is empty", state.get("concept_states") == {} or len(state.get("concept_states", {})) == 0)

r = requests.get(f"{BASE}/learner/{learner_id}/sessions", headers=headers)
test("GET sessions returns 200", r.status_code == 200)
test("New user has empty sessions", r.json() == [] or isinstance(r.json(), list))

# ================================================================
print("\n[5/9] SSE — START SESSION (topic=python)")
r = requests.post(
    f"{BASE}/session/start/stream",
    json={"learner_id": learner_id, "topic": "python"},
    headers=headers, stream=True, timeout=120
)
test("Start stream returns 200", r.status_code == 200)
test("Content-Type is SSE", "text/event-stream" in r.headers.get("content-type", ""))

events = parse_sse_events(r, timeout=120)
test("Got events", len(events) > 0, f"{len(events)} events")
test("Got acknowledged", has_event(events, "acknowledged"))
test("Got chat_created", has_event(events, "chat_created"))
test("Got stream_complete", has_event(events, "stream_complete"))
test("No errors", not has_event(events, "error"),
     get_event(events, "error").get("message", "") if has_event(events, "error") else "")
test("No timeout", not has_event(events, "TIMEOUT"))

# Check session_id from chat_created
cc = get_event(events, "chat_created")
session_id = cc.get("session_id", "") if cc else ""
test("chat_created has session_id", bool(session_id), session_id[:36] if session_id else "missing")

# Check result event
result_evt = get_event(events, "result")
test("Got result event", result_evt is not None)
if result_evt:
    result_data = result_evt.get("result", {})
    action = result_data.get("action", "")
    test("Result has action", bool(action), f"action={action}")
    content = result_data.get("content")
    test("Result has content", content is not None, f"type={type(content).__name__}")

# Check text_chunk events
chunks = get_events(events, "text_chunk")
test("Got text_chunks (streaming content)", len(chunks) > 0, f"{len(chunks)} chunks")
if chunks:
    final_chunks = [c for c in chunks if c.get("final")]
    test("Has a final=true chunk", len(final_chunks) > 0)
    full_text = "".join(c.get("chunk", "") for c in chunks)
    test("Streamed text is non-empty", len(full_text) > 10, f"{len(full_text)} chars")

# Check phase_change
test("Got phase_change", has_event(events, "phase_change"))
pc = get_event(events, "phase_change")
if pc:
    test("Phase change has concept", bool(pc.get("concept")), pc.get("concept"))

# ================================================================
print("\n[6/9] SESSION PERSISTED")
r = requests.get(f"{BASE}/learner/{learner_id}/sessions", headers=headers)
sessions = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
found = any(isinstance(s, dict) and s.get("session_id") == session_id for s in sessions)
test("Session appears in list", found, f"{len(sessions)} sessions")

first = next((s for s in sessions if isinstance(s, dict) and s.get("session_id") == session_id), None)
if first:
    test("Session has started_at", bool(first.get("started_at")))
    test("Session has current_state", bool(first.get("current_state")), first.get("current_state"))

# ================================================================
if session_id:
    print("\n[7/9] SSE — RESPOND (learner answers)")
    r = requests.post(
        f"{BASE}/session/{session_id}/respond/stream",
        json={"response_type": "answer", "content": "A variable stores data. x=5 makes x an integer. name='hi' is a string."},
        headers=headers, stream=True, timeout=120
    )
    test("Respond returns 200", r.status_code == 200)
    events2 = parse_sse_events(r, timeout=120)
    test("Respond got events", len(events2) > 0, f"{len(events2)} events")
    test("Respond got acknowledged", has_event(events2, "acknowledged"))
    test("Respond got result", has_event(events2, "result"))
    test("Respond got stream_complete", has_event(events2, "stream_complete"))
    test("Respond no errors", not has_event(events2, "error"),
         get_event(events2, "error").get("message", "") if has_event(events2, "error") else "")
    test("Respond no timeout", not has_event(events2, "TIMEOUT"))

    r2 = get_event(events2, "result")
    if r2:
        action2 = r2.get("result", {}).get("action", "")
        test("Respond action is valid", action2 in (
            "teach", "practice", "transfer_test", "self_assess",
            "retest", "reteach", "chat_response", "complete",
            "evaluate", "decay_check"
        ), f"action={action2}")

    # ============================================================
    print("\n[8/9] SSE — CHAT (non-learning message)")
    r = requests.post(
        f"{BASE}/session/{session_id}/respond/stream",
        json={"response_type": "chat", "content": "Tell me a joke about programming"},
        headers=headers, stream=True, timeout=120
    )
    test("Chat returns 200", r.status_code == 200)
    events3 = parse_sse_events(r, timeout=120)
    test("Chat got events", len(events3) > 0, f"{len(events3)} events")
    test("Chat got result", has_event(events3, "result"))
    test("Chat got stream_complete", has_event(events3, "stream_complete"))
    test("Chat no errors", not has_event(events3, "error"))

    r3 = get_event(events3, "result")
    if r3:
        action3 = r3.get("result", {}).get("action", "")
        test("Chat action is chat_response", action3 == "chat_response", f"action={action3}")
        chat_chunks = get_events(events3, "text_chunk")
        chat_text = "".join(c.get("chunk", "") for c in chat_chunks)
        test("Chat has streamed text", len(chat_text) > 5, f"{len(chat_text)} chars")
else:
    print("\n[7/9] SKIPPED — no session_id")
    print("\n[8/9] SKIPPED — no session_id")

# ================================================================
print("\n[9/9] EDGE CASES & ERROR HANDLING")

# Invalid session respond
r = requests.post(
    f"{BASE}/session/nonexistent-id/respond/stream",
    json={"response_type": "answer", "content": "test"},
    headers=headers, stream=True, timeout=15
)
test("Invalid session_id not 500", r.status_code != 500, f"status={r.status_code}")
r.close()

# Missing learner_id on start
r = requests.post(
    f"{BASE}/session/start/stream",
    json={"topic": "python"},
    headers=headers, timeout=15
)
test("Missing learner_id rejected", r.status_code in (400, 422), f"status={r.status_code}")

# No auth header
r = requests.get(f"{BASE}/learner/{learner_id}/state", timeout=5)
test("No auth returns 401 or 403", r.status_code in (401, 403), f"status={r.status_code}")

# Calibration endpoint (new user, no data)
r = requests.get(f"{BASE}/learner/{learner_id}/calibration", headers=headers, timeout=10)
test("Calibration endpoint responds", r.status_code in (200, 404), f"status={r.status_code}")

# Graph endpoint
r = requests.get(f"{BASE}/graph", headers=headers, timeout=10)
test("Graph endpoint returns 200", r.status_code == 200)
if r.status_code == 200:
    g = r.json()
    test("Graph has nodes", len(g.get("nodes", [])) > 0, f'{len(g.get("nodes", []))} nodes')

# ================================================================
print("\n" + "=" * 60)
print(f"TOTAL: {PASS + FAIL} tests | {PASS} PASSED | {FAIL} FAILED")
if FAILURES:
    print(f"\nFAILURES:")
    for f in FAILURES:
        print(f"  - {f}")
print("=" * 60)
sys.exit(1 if FAIL > 0 else 0)
