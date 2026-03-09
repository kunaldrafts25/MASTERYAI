# integration tests - real multi-turn learning scenarios end-to-end

import pytest
import random
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.services.learner_store import learner_store
from backend.agents.orchestrator import orchestrator
from backend.agents.motivation import motivation_agent

VALID_ACTIONS = (
    "teach", "decay_check", "complete", "transfer_test", "practice",
    "self_assess", "mastered_and_advance", "mastered_all_done",
    "retest", "reteach", "chat_response", "continue", "error",
    "concept_selected", "mastered", "career_info",
)


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register(client, email=None):
    email = email or f"integ_{random.randint(10000,99999)}@test.com"
    res = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "pass1234", "name": "Test Learner",
    })
    assert res.status_code == 200, f"Registration failed: {res.text}"
    data = res.json()
    return data["token"], data["learner_id"]


async def _start_session(client, learner_id, headers):
    res = await client.post(
        "/api/v1/session/start",
        json={"learner_id": learner_id},
        headers=headers,
    )
    assert res.status_code == 200, f"Start session failed: {res.text}"
    data = res.json()
    assert "session_id" in data
    assert data["action"] in VALID_ACTIONS
    return data


async def _respond(client, session_id, headers, response_type="answer",
                   content="test answer", confidence=None):
    body = {"response_type": response_type, "content": content}
    if confidence is not None:
        body["confidence"] = confidence
    res = await client.post(
        f"/api/v1/session/{session_id}/respond",
        json=body,
        headers=headers,
    )
    assert res.status_code == 200, f"Respond failed: {res.text}"
    data = res.json()
    assert data["action"] in VALID_ACTIONS
    return data


# --- scenario 1: full learning loop ---

async def test_full_learning_loop(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: start session → should teach
    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]
    assert start["action"] == "teach"
    assert start["concept"] is not None
    concept_id = start["concept"]["id"]

    # Step 2: answer teaching content → should move to practice
    step2 = await _respond(client, session_id, headers,
                           content="I understand that variables store values in named locations")
    assert step2["action"] == "practice"

    # Step 3: answer practice → should ask for self-assessment
    step3 = await _respond(client, session_id, headers,
                           content="x = 5 creates a variable x with value 5")
    assert step3["action"] == "self_assess"

    # Step 4: provide self-assessment → should generate test
    step4 = await _respond(client, session_id, headers,
                           response_type="self_assessment",
                           content="7", confidence=7)
    assert step4["action"] in ("transfer_test", "decay_check")

    # Step 5: answer the test → should evaluate and produce a result
    step5 = await _respond(client, session_id, headers,
                           content="The lambda captures i by reference so all handlers use final value. Fix with default arg: lambda i=i: process(i)")
    assert step5["action"] in ("mastered_and_advance", "mastered_all_done", "retest", "reteach")

    # Verify learner state was updated
    state_res = await client.get(f"/api/v1/learner/{learner_id}/state", headers=headers)
    assert state_res.status_code == 200
    state = state_res.json()
    # concept should appear in concept_states
    assert len(state["concept_states"]) >= 1


async def test_multi_turn_reteach_recovery(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]

    # go through teach → practice → self-assess → test
    await _respond(client, session_id, headers, content="My understanding of variables")
    await _respond(client, session_id, headers, content="Practice answer")
    await _respond(client, session_id, headers, response_type="self_assessment",
                   content="5", confidence=5)

    # answer test — the mock evaluator randomly scores, so we accept whatever path
    result = await _respond(client, session_id, headers,
                            content="I'm not sure about closures")

    if result["action"] == "reteach":
        # verify reteach content is present
        assert "content" in result
        # continue the reteach flow: answer reteach → practice → assess → test
        step_after_reteach = await _respond(client, session_id, headers,
                                            content="Now I understand closures capture variables by reference")
        assert step_after_reteach["action"] in VALID_ACTIONS

    elif result["action"] == "retest":
        # verify retest has new test content
        assert "content" in result
        retest_answer = await _respond(client, session_id, headers,
                                       content="Default argument captures current value of i")
        assert retest_answer["action"] in VALID_ACTIONS

    elif result["action"] in ("mastered_and_advance", "mastered_all_done"):
        # good — learner passed first try
        pass

    # Either way, session should have events
    events_res = await client.get(f"/api/v1/session/{session_id}/events", headers=headers)
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 3  # at minimum: teach + practice + test


# --- scenario 2: RL policy evolves after real interactions ---

async def test_rl_policy_updates_after_session(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # check initial policy — should be empty
    policy_res = await client.get(f"/api/v1/learner/{learner_id}/rl-policy", headers=headers)
    assert policy_res.status_code == 200
    initial = policy_res.json()
    assert initial["has_learned"] is False

    # run a session through to evaluation
    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]

    await _respond(client, session_id, headers, content="Variable answer")
    await _respond(client, session_id, headers, content="Practice answer")
    await _respond(client, session_id, headers, response_type="self_assessment",
                   content="8", confidence=8)
    await _respond(client, session_id, headers,
                   content="Closures capture by reference, fix with default param")

    # check policy again — should now have learning data
    policy_res2 = await client.get(f"/api/v1/learner/{learner_id}/rl-policy", headers=headers)
    assert policy_res2.status_code == 200
    updated = policy_res2.json()
    assert updated["has_learned"] is True
    stats = updated["policy_stats"]

    # strategy bandit should have been updated (at least one strategy got a score)
    bandit_stats = stats["strategy_bandit"]
    has_update = any(
        v["alpha"] > 1.0 or v["beta"] > 1.0
        for v in bandit_stats.values()
    )
    assert has_update, f"Strategy bandit should have learned: {bandit_stats}"

    # difficulty bandit should have at least 1 update
    assert stats["difficulty_bandit"]["total_updates"] >= 1

    # Q-learner should have explored at least 1 state
    assert stats["action_q"]["total_updates"] >= 1


# --- scenario 3: review scheduling after mastery ---

async def test_review_queue_populates_after_mastery(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # run a session
    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]
    await _respond(client, session_id, headers, content="Variable answer")
    await _respond(client, session_id, headers, content="Practice answer")
    await _respond(client, session_id, headers, response_type="self_assessment",
                   content="9", confidence=9)
    result = await _respond(client, session_id, headers,
                            content="Closures capture by reference. Fix: lambda i=i: process(i)")

    # check review queue
    reviews_res = await client.get(f"/api/v1/learner/{learner_id}/reviews", headers=headers)
    assert reviews_res.status_code == 200
    reviews = reviews_res.json()

    if result["action"] in ("mastered_and_advance", "mastered_all_done"):
        # concept was mastered → review queue should have it
        assert reviews["total_items"] >= 1, "Mastered concept should be in review queue"
        assert reviews["due_now"] == 0, "Just-mastered concept shouldn't be due yet"
    # if reteach/retest, review queue stays empty — that's fine


# --- scenario 4: analytics reflect real session data ---

async def test_analytics_after_session(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # run through a session
    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]
    await _respond(client, session_id, headers, content="Variable answer")
    await _respond(client, session_id, headers, content="Practice answer")
    await _respond(client, session_id, headers, response_type="self_assessment",
                   content="6", confidence=6)
    await _respond(client, session_id, headers,
                   content="Detailed closure explanation with default argument fix")

    # check analytics
    analytics_res = await client.get(f"/api/v1/analytics/{learner_id}", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()

    # should have data in at least one domain
    velocity = analytics["learning_velocity"]
    assert len(velocity) >= 1, "Should have at least one domain in velocity"

    # strategy effectiveness should have at least the strategy used in this session
    strategies = analytics["strategy_effectiveness"]
    # might be empty if concept wasn't mastered, but should at least have the dict
    assert isinstance(strategies, dict)

    # misconception patterns should be a valid dict
    misconceptions = analytics["misconception_patterns"]
    assert "active_count" in misconceptions
    assert "resolved_count" in misconceptions


# --- scenario 5: chat interaction during a session ---

async def test_chat_during_session(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]

    # send a chat message
    chat = await _respond(client, session_id, headers,
                          response_type="chat",
                          content="I'm confused about this concept, can you explain differently?")
    assert chat["action"] in ("chat_response", "continue", "teach")


# --- scenario 6: state persists across sessions ---

async def test_state_persists_across_sessions(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Session 1: go through the full flow
    s1 = await _start_session(client, learner_id, headers)
    s1_id = s1["session_id"]
    await _respond(client, s1_id, headers, content="Variable answer")
    await _respond(client, s1_id, headers, content="Practice answer")
    await _respond(client, s1_id, headers, response_type="self_assessment",
                   content="7", confidence=7)
    s1_eval = await _respond(client, s1_id, headers,
                             content="Closure explanation with fix")

    # capture state after session 1
    state1 = await client.get(f"/api/v1/learner/{learner_id}/state", headers=headers)
    concepts_after_s1 = len(state1.json()["concept_states"])

    # Session 2: start a new session — should see previous state
    s2 = await _start_session(client, learner_id, headers)
    assert s2["session_id"] != s1_id, "Should be a new session"
    assert s2["action"] in VALID_ACTIONS

    # state should still have the concepts from session 1
    state2 = await client.get(f"/api/v1/learner/{learner_id}/state", headers=headers)
    assert len(state2.json()["concept_states"]) >= concepts_after_s1


# --- scenario 7: calibration tracking through self-assessment ---

async def test_calibration_gap_tracked(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]

    # teach → practice → self-assess with HIGH confidence → test
    await _respond(client, session_id, headers, content="Variable answer")
    await _respond(client, session_id, headers, content="Practice answer")
    await _respond(client, session_id, headers, response_type="self_assessment",
                   content="9", confidence=9)
    await _respond(client, session_id, headers,
                   content="Closure captures by reference")

    # check calibration endpoint
    cal_res = await client.get(f"/api/v1/learner/{learner_id}/calibration", headers=headers)
    assert cal_res.status_code == 200
    cal = cal_res.json()
    assert "overall_calibration" in cal
    assert "per_concept" in cal
    # at least one concept should have calibration data
    if cal["per_concept"]:
        c = cal["per_concept"][0]
        assert "confidence" in c
        assert "mastery" in c
        assert "gap" in c


# --- scenario 8: dynamic topic generation ---

async def test_generate_topic_then_full_session(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # generate concepts
    gen_res = await client.post(
        "/api/v1/topics/generate",
        json={"topic": "data structures", "depth": 6},
        headers=headers,
    )
    assert gen_res.status_code == 200
    gen = gen_res.json()
    assert gen["concepts_generated"] >= 3

    # verify domains updated
    domains_res = await client.get("/api/v1/topics/domains")
    assert domains_res.status_code == 200
    domains = domains_res.json()
    assert domains["total_concepts"] > 0

    # now run a full session — should teach something
    start = await _start_session(client, learner_id, headers)
    assert start["action"] in ("teach", "concept_selected", "transfer_test", "decay_check")

    session_id = start["session_id"]
    if start["action"] == "teach":
        # continue the flow
        await _respond(client, session_id, headers, content="Data structures answer")
        step = await _respond(client, session_id, headers, content="Practice answer")
        assert step["action"] in VALID_ACTIONS


# --- scenario 9: career target integration ---

async def test_career_target_affects_session(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # get available roles
    roles_res = await client.get("/api/v1/career/roles")
    assert roles_res.status_code == 200
    roles = roles_res.json()
    assert len(roles) > 0

    # set career target
    role_id = roles[0]["id"]
    target_res = await client.put(
        f"/api/v1/learner/{learner_id}/career-target",
        json={"role_ids": [role_id]},
        headers=headers,
    )
    assert target_res.status_code == 200
    assert target_res.json()["career_targets"] == [role_id]

    # start session — should get a relevant concept
    start = await _start_session(client, learner_id, headers)
    assert start["action"] in ("teach", "concept_selected", "transfer_test", "decay_check")


# --- scenario 10: retention endpoint with real data ---

async def test_retention_with_mastered_concept(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # run a session
    start = await _start_session(client, learner_id, headers)
    concept_id = start["concept"]["id"] if start.get("concept") else "python.variables"
    session_id = start["session_id"]
    await _respond(client, session_id, headers, content="Answer")
    await _respond(client, session_id, headers, content="Practice")
    await _respond(client, session_id, headers, response_type="self_assessment",
                   content="8", confidence=8)
    result = await _respond(client, session_id, headers,
                            content="Detailed explanation of closure capture semantics")

    # check retention for the concept
    ret_res = await client.get(
        f"/api/v1/learner/{learner_id}/retention/{concept_id}",
        headers=headers,
    )
    assert ret_res.status_code == 200
    ret = ret_res.json()
    assert ret["concept_id"] == concept_id

    if result["action"] in ("mastered_and_advance", "mastered_all_done"):
        # mastered — should have retention data
        assert ret["stability"] > 0, "Mastered concept should have stability"
        assert 0 < ret["retention"] <= 1.0


# --- scenario 11: events contain expected lifecycle entries ---

async def test_session_events_lifecycle(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]
    await _respond(client, session_id, headers, content="Variable answer")
    await _respond(client, session_id, headers, content="Practice answer")
    await _respond(client, session_id, headers, response_type="self_assessment",
                   content="7", confidence=7)
    await _respond(client, session_id, headers,
                   content="Test answer about closures")

    events_res = await client.get(f"/api/v1/session/{session_id}/events", headers=headers)
    assert events_res.status_code == 200
    events = events_res.json()

    event_types = [e["event_type"] for e in events]
    # should have at minimum: teaching started, test generated
    assert "TEACHING_STARTED" in event_types, f"Missing TEACHING_STARTED in {event_types}"
    assert any("TEST" in t or "PRACTICE" in t or "ASSESSMENT" in t for t in event_types), \
        f"Missing test/practice/assessment event in {event_types}"

    # every event should have required fields
    for e in events:
        assert "event_id" in e
        assert "event_type" in e
        assert "source_agent" in e
        assert "timestamp" in e
        assert e["session_id"] == session_id


# --- scenario 12: concurrent learner isolation ---

async def test_two_learners_isolated(client):
    token_a, learner_a = await _register(client, email=f"a_{random.randint(10000,99999)}@test.com")
    token_b, learner_b = await _register(client, email=f"b_{random.randint(10000,99999)}@test.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # start sessions
    start_a = await _start_session(client, learner_a, headers_a)
    start_b = await _start_session(client, learner_b, headers_b)
    assert start_a["session_id"] != start_b["session_id"]

    # both do teach responses
    resp_a = await _respond(client, start_a["session_id"], headers_a, content="Learner A answer")
    resp_b = await _respond(client, start_b["session_id"], headers_b, content="Learner B answer")
    assert resp_a["action"] in VALID_ACTIONS
    assert resp_b["action"] in VALID_ACTIONS

    # verify states are separate
    state_a = await client.get(f"/api/v1/learner/{learner_a}/state", headers=headers_a)
    state_b = await client.get(f"/api/v1/learner/{learner_b}/state", headers=headers_b)
    assert state_a.json()["learner_id"] == learner_a
    assert state_b.json()["learner_id"] == learner_b

    # learner A cannot access learner B's data
    cross_res = await client.get(f"/api/v1/learner/{learner_b}/state", headers=headers_a)
    assert cross_res.status_code == 403


# --- scenario 13: RL bandit convergence under realistic reward distribution ---

def test_rl_bandit_convergence_realistic():
    from backend.agents.rl_engine import RLEngine

    engine = RLEngine()
    random.seed(42)

    # simulate: socratic works great (avg 0.8), analogy works ok (avg 0.5),
    # debugging_exercise works poorly (avg 0.3) for this learner profile
    reward_distributions = {
        "socratic": (0.8, 0.1),
        "worked_examples": (0.65, 0.15),
        "analogy": (0.5, 0.2),
        "debugging_exercise": (0.3, 0.15),
        "explain_back": (0.6, 0.1),
    }

    for _ in range(100):
        strategy = engine.select_strategy()
        mean, std = reward_distributions[strategy]
        score = max(0.0, min(1.0, random.gauss(mean, std)))
        engine.update_strategy(strategy, score)

    # after 100 interactions, best strategy should be socratic
    assert engine.get_best_strategy() == "socratic"

    # check that strategy stats reflect the learning
    stats = engine.strategy_bandit.get_stats()
    assert stats["socratic"]["expected"] > stats["debugging_exercise"]["expected"]


def test_rl_q_learner_avoids_bad_path():
    from backend.agents.rl_engine import ActionQLearner

    ql = ActionQLearner(alpha=0.2, gamma=0.9, epsilon=0.0)

    # simulate: reteach in "introduced" state always leads to -2 reward
    for _ in range(50):
        ql.update("introduced|0|2+|declining|neutral", "reteach", -2.0,
                  "introduced|0|2+|declining|neutral")
        ql.update("introduced|0|2+|declining|neutral", "ask_learner", 3.0,
                  "introduced|0|1|stable|neutral")
        ql.update("introduced|0|2+|declining|neutral", "teach", 1.0,
                  "introduced|0|0|improving|neutral")

    # should prefer ask_learner over reteach when frustrated
    state = "introduced|0|2+|declining|neutral"
    assert ql.q_table[state]["ask_learner"] > ql.q_table[state]["reteach"]
    assert ql.select_action("introduced", 0, 3, [0.3, 0.2, 0.1], "neutral") == "ask_learner"


# --- scenario 14: SM-2 interval progression over many reviews ---

def test_sm2_interval_growth_realistic():
    from backend.agents.review_scheduler import ReviewSchedulerAgent
    from backend.models.learner import LearnerState, ConceptMastery

    scheduler = ReviewSchedulerAgent()
    learner = LearnerState(learner_id="sm2-test")
    learner.concept_states["python.closures"] = ConceptMastery(concept_id="python.closures")

    intervals = []
    for review_num in range(8):
        # consistently score 0.8-0.9
        score = 0.85
        scheduler.schedule_review(learner, "python.closures", score)
        item = learner.review_queue[0]
        intervals.append(item["interval_days"])

    # intervals should be non-decreasing after the first 2
    for i in range(2, len(intervals)):
        assert intervals[i] >= intervals[i - 1], \
            f"Interval should grow: {intervals[i]} < {intervals[i-1]} at review {i}"

    # after 8 consistent correct reviews, interval should be > 30 days
    assert intervals[-1] > 30, f"Expected > 30 days after 8 reviews, got {intervals[-1]}"


def test_sm2_misconception_penalty_effect():
    from backend.agents.review_scheduler import ReviewSchedulerAgent
    from backend.models.learner import LearnerState, ConceptMastery

    scheduler = ReviewSchedulerAgent()

    # learner A: no misconceptions
    learner_a = LearnerState(learner_id="sm2-a")
    learner_a.concept_states["c1"] = ConceptMastery(concept_id="c1", misconceptions_active=[])
    for _ in range(5):
        scheduler.schedule_review(learner_a, "c1", 0.8)
    interval_a = learner_a.review_queue[0]["interval_days"]

    # learner B: 2 active misconceptions
    learner_b = LearnerState(learner_id="sm2-b")
    learner_b.concept_states["c1"] = ConceptMastery(
        concept_id="c1", misconceptions_active=["m1", "m2"]
    )
    for _ in range(5):
        scheduler.schedule_review(learner_b, "c1", 0.8)
    interval_b = learner_b.review_queue[0]["interval_days"]

    # misconception-heavy learner should have shorter intervals
    assert interval_b < interval_a, \
        f"Misconception penalty failed: {interval_b} should be < {interval_a}"


# --- scenario 15: motivation state transitions ---

def test_motivation_state_transitions():
    from backend.agents.motivation import MotivationAgent

    agent = MotivationAgent()
    sid = "motivation-transitions"

    # start neutral
    assert agent.detect_state(sid) == "neutral"

    # fail 3 times → frustrated
    for _ in range(3):
        agent.record_interaction(sid, "short", score=0.2, is_test_result=True)
    assert agent.detect_state(sid) == "frustrated"

    # succeed once → shouldn't immediately leave frustrated (still has 2 consecutive fails
    # after the success resets to 0 failures)
    agent.record_interaction(sid, "got it right this time!", score=0.8, is_test_result=True)
    state = agent.detect_state(sid)
    # after 1 success, no longer 3 consecutive failures
    assert state != "frustrated", "Single success should break frustration"

    # clean up
    agent.cleanup_session(sid)


def test_motivation_multiple_sessions_isolated():
    from backend.agents.motivation import MotivationAgent

    agent = MotivationAgent()

    # session 1: frustrated
    for _ in range(3):
        agent.record_interaction("s1", "wrong", score=0.1, is_test_result=True)
    assert agent.detect_state("s1") == "frustrated"

    # session 2: should start neutral
    assert agent.detect_state("s2") == "neutral"
    agent.record_interaction("s2", "correct!", score=0.9, is_test_result=True)
    assert agent.detect_state("s2") != "frustrated"

    # session 1 should still be frustrated
    assert agent.detect_state("s1") == "frustrated"

    agent.cleanup_session("s1")
    agent.cleanup_session("s2")


# --- scenario 16: analytics accuracy with known data ---

def test_analytics_full_computation_accuracy():
    from backend.agents.analytics import AnalyticsAgent
    from backend.models.learner import LearnerState, ConceptMastery, TestResult, LearningProfile

    agent = AnalyticsAgent()
    learner = LearnerState(
        learner_id="analytics-test",
        learning_profile=LearningProfile(calibration_trend="overconfident"),
    )

    # build known state: 3 concepts, 2 mastered
    learner.concept_states["python.variables"] = ConceptMastery(
        concept_id="python.variables", status="mastered",
        teaching_strategies_tried={"socratic": 0.9, "worked_examples": 0.7},
        misconceptions_active=[], misconceptions_resolved=["var_scope"],
        transfer_tests=[TestResult(test_id="t1", context="ctx1", score=0.9)],
    )
    learner.concept_states["python.loops"] = ConceptMastery(
        concept_id="python.loops", status="mastered",
        teaching_strategies_tried={"socratic": 0.75, "analogy": 0.6},
        misconceptions_active=["off_by_one"],
        transfer_tests=[
            TestResult(test_id="t2", context="ctx2", score=0.5),
            TestResult(test_id="t3", context="ctx3", score=0.8),
        ],
    )
    learner.concept_states["python.closures"] = ConceptMastery(
        concept_id="python.closures", status="introduced",
        teaching_strategies_tried={"debugging_exercise": 0.3},
        misconceptions_active=["late_binding", "scope_confusion"],
    )

    # test velocity
    velocity = agent.compute_learning_velocity(learner)
    assert velocity["python"]["concepts_mastered"] == 2
    assert velocity["python"]["total_concepts"] == 3
    assert abs(velocity["python"]["mastery_rate"] - 0.67) < 0.01

    # test strategy effectiveness — exact values
    effectiveness = agent.compute_strategy_effectiveness(learner)
    assert effectiveness["socratic"]["usage_count"] == 2
    assert abs(effectiveness["socratic"]["avg_score"] - 0.825) < 0.001  # (0.9 + 0.75) / 2
    assert effectiveness["debugging_exercise"]["usage_count"] == 1
    assert effectiveness["debugging_exercise"]["avg_score"] == 0.3

    # test misconception patterns
    misconceptions = agent.compute_misconception_patterns(learner)
    assert misconceptions["active_count"] == 3  # off_by_one + late_binding + scope_confusion
    assert misconceptions["resolved_count"] == 1  # var_scope

    # test patterns — should detect overconfident calibration
    patterns = agent.identify_learning_patterns(learner)
    assert any("overestimate" in p.lower() or "overconfident" in p.lower() for p in patterns)
    # should identify socratic as best strategy
    assert any("socratic" in p.lower() for p in patterns)


# --- scenario 17: diagnostic agent binary search behavior ---

def test_diagnostic_binary_search_skips_mapped():
    from backend.agents.diagnostic import DiagnosticAgent
    from backend.models.learner import LearnerState, ConceptMastery

    agent = DiagnosticAgent()
    learner = LearnerState(learner_id="diag-test", experience_level="intermediate")

    # map some concepts as already known
    learner.concept_states["python.variables"] = ConceptMastery(
        concept_id="python.variables", status="mastered"
    )
    learner.concept_states["python.data_types"] = ConceptMastery(
        concept_id="python.data_types", status="introduced"
    )

    probes = agent.select_probe_concepts(learner, domain="python")
    # probes should NOT include already-mapped concepts
    for probe in probes:
        assert probe not in ("python.variables", "python.data_types"), \
            f"Probe {probe} should not be in already-mapped concepts"


def test_diagnostic_mastery_inference_cascades():
    from backend.agents.diagnostic import DiagnosticAgent
    from backend.models.learner import LearnerState

    agent = DiagnosticAgent()
    learner = LearnerState(learner_id="diag-cascade")

    # python.closures has prerequisites in the knowledge graph
    results = [{"concept_id": "python.closures", "score": 0.85}]
    inferred = agent.infer_mastery_from_diagnostics(results, learner)

    assert inferred["python.closures"] == "mastered"
    # closures prereqs (functions, scope) should also be inferred
    from backend.services.knowledge_graph import knowledge_graph
    prereqs = knowledge_graph.get_prerequisites("python.closures")
    for prereq in prereqs:
        assert prereq in inferred, f"Prerequisite {prereq} should be inferred"
        assert inferred[prereq] == "mastered"


def test_diagnostic_apply_changes_learner_state():
    from backend.agents.diagnostic import DiagnosticAgent
    from backend.models.learner import LearnerState

    agent = DiagnosticAgent()
    learner = LearnerState(learner_id="diag-apply", experience_level="intermediate")

    inferred = {
        "python.closures": "mastered",
        "python.functions": "mastered",
        "python.variables": "introduced",
        "python.classes": "unknown",
    }

    applied = agent.apply_diagnostic_results(learner, inferred)
    assert applied >= 3  # closures, functions, variables should all change

    assert learner.concept_states["python.closures"].status == "mastered"
    assert learner.concept_states["python.functions"].status == "mastered"
    assert learner.concept_states["python.variables"].status == "introduced"
    # unknown should not create "unknown" status — it should still be whatever default
    assert learner.concept_states["python.classes"].status == "unknown"


# --- scenario 18: error handling & edge cases ---

async def test_respond_to_nonexistent_session(client):
    token, _ = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/session/00000000-0000-0000-0000-000000000000/respond",
        json={"response_type": "answer", "content": "test"},
        headers=headers,
    )
    assert res.status_code == 404


async def test_analytics_empty_learner(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/analytics/{learner_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["learning_velocity"] == {}
    assert data["strategy_effectiveness"] == {}
    assert data["misconception_patterns"]["active_count"] == 0
    assert data["learning_patterns"] == []


async def test_rl_policy_fresh_learner(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/learner/{learner_id}/rl-policy", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_learned"] is False

    # should still return valid stats with defaults
    stats = data["policy_stats"]
    assert all(
        stats["strategy_bandit"][s]["expected"] == 0.5
        for s in stats["strategy_bandit"]
    ), "Fresh bandit should have 0.5 expected value (uniform prior)"


async def test_empty_content_response(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]

    res = await client.post(
        f"/api/v1/session/{session_id}/respond",
        json={"response_type": "answer", "content": ""},
        headers=headers,
    )
    assert res.status_code == 200


# --- scenario 19: difficulty bandit adapts to different learner contexts ---

def test_difficulty_bandit_context_sensitivity():
    from backend.agents.rl_engine import DifficultyBandit

    bandit = DifficultyBandit()

    # slow learner + many misconceptions → difficulty 1 works best
    for _ in range(40):
        bandit.update(0.5, 0.0, 3, difficulty=1, threshold=0.6, reward=8.0)
        bandit.update(0.5, 0.0, 3, difficulty=2, threshold=0.7, reward=2.0)
        bandit.update(0.5, 0.0, 3, difficulty=3, threshold=0.8, reward=0.5)

    # fast learner + no misconceptions → difficulty 3 works best
    for _ in range(40):
        bandit.update(1.5, 0.0, 0, difficulty=3, threshold=0.8, reward=9.0)
        bandit.update(1.5, 0.0, 0, difficulty=2, threshold=0.7, reward=4.0)
        bandit.update(1.5, 0.0, 0, difficulty=1, threshold=0.6, reward=1.0)

    # force exploitation by bumping updates past epsilon decay
    bandit.total_updates = 300

    # slow+misconceptions should get difficulty 1
    slow_selections = [bandit.select_difficulty(0.5, 0.0, 3) for _ in range(30)]
    assert slow_selections.count(1) > 20, \
        f"Slow learner should prefer difficulty 1: {slow_selections.count(1)}/30"

    # fast+clean should get difficulty 3
    fast_selections = [bandit.select_difficulty(1.5, 0.0, 0) for _ in range(30)]
    assert fast_selections.count(3) > 20, \
        f"Fast learner should prefer difficulty 3: {fast_selections.count(3)}/30"
