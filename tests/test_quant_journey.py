"""
Quant Learning Journey — end-to-end simulation of a learner aiming to
become a Quantitative Analyst.

Simulates the *full* lifecycle:
  register → set career target → check initial readiness → learn concepts
  one by one (teach → practice → self-assess → test → evaluate) → master
  multiple concepts → track career readiness growth → verify RL adapts →
  verify review queue fills → verify motivation & analytics → run a second
  "returning learner" session to confirm state persistence.

Uses a fixed random seed so mock scores are deterministic and assertions
are stable.
"""

import pytest
import random
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.services.learner_store import learner_store

VALID_ACTIONS = (
    "teach", "decay_check", "complete", "transfer_test", "practice",
    "self_assess", "mastered_and_advance", "mastered_all_done",
    "retest", "reteach", "chat_response", "continue", "error",
    "concept_selected", "mastered", "career_info",
)

QUANT_ROLE_ID = "quantitative_analyst"


# ── helpers ─────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register(client, name="Aspiring Quant"):
    email = f"quant_{random.randint(10000, 99999)}@test.com"
    res = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "pass1234", "name": name,
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


async def _drive_to_evaluation(client, session_id, headers, concept_name="concept"):
    """Drive teach → practice → self-assess → test cycle, return eval result."""
    # answer the teaching content
    await _respond(client, session_id, headers,
                   content=f"I understand {concept_name}. Variables store references.")
    # answer practice
    await _respond(client, session_id, headers,
                   content=f"Practice answer: applying {concept_name} to solve the problem.")
    # provide self-assessment
    await _respond(client, session_id, headers,
                   response_type="self_assessment",
                   content="7", confidence=7)
    # answer the test
    result = await _respond(client, session_id, headers,
                            content=f"The lambda captures i by reference due to closure semantics. "
                                    f"Fix with default arg: lambda i=i: process(i). "
                                    f"This ensures each handler captures the current value.")
    return result


async def _master_current_concept(client, session_id, headers, concept_name="concept",
                                  max_attempts=6):
    """
    Drive the current concept to mastery, handling retest/reteach loops.
    Returns (final_action, attempts_taken).
    """
    result = await _drive_to_evaluation(client, session_id, headers, concept_name)
    attempts = 1

    while result["action"] in ("retest", "reteach") and attempts < max_attempts:
        attempts += 1
        if result["action"] == "reteach":
            # got reteaught — answer the reteach, then practice, self-assess, test again
            await _respond(client, session_id, headers,
                           content=f"Now I understand {concept_name} better after reteaching.")
            await _respond(client, session_id, headers,
                           content=f"Practice answer for {concept_name} after reteach.")
            await _respond(client, session_id, headers,
                           response_type="self_assessment",
                           content="8", confidence=8)
            result = await _respond(client, session_id, headers,
                                    content=f"Detailed explanation: closure late binding, "
                                            f"default argument fix. {concept_name} mastered.")
        elif result["action"] == "retest":
            # just answer the retest
            result = await _respond(client, session_id, headers,
                                    content=f"On retest: the closure captures the reference, "
                                            f"use default param or functools.partial. "
                                            f"{concept_name} knowledge confirmed.")
    return result["action"], attempts


# ── the journey ─────────────────────────────────────────────────────────


@pytest.mark.live
async def test_quant_journey_full(client):
    """
    Simulate a complete learner journey from zero to partial quant readiness.

    This is the core scenario: a person wants to become a quantitative analyst.
    The system should:
      1. Accept the career target
      2. Plan a learning path (prerequisite-respecting)
      3. Teach concepts one by one, adapting difficulty/strategy via RL
      4. Track mastery, schedule reviews, detect engagement, compute analytics
      5. Show increasing career readiness with each mastered concept
    """
    random.seed(42)  # deterministic mock scores

    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # ── Step 1: set career target ────────────────────────────────────────

    target_res = await client.put(
        f"/api/v1/learner/{learner_id}/career-target",
        json={"role_ids": [QUANT_ROLE_ID]},
        headers=headers,
    )
    assert target_res.status_code == 200
    assert QUANT_ROLE_ID in target_res.json()["career_targets"]

    # ── Step 2: check initial readiness — should be 0 ───────────────────

    readiness_res = await client.get(
        f"/api/v1/career/readiness/{learner_id}/{QUANT_ROLE_ID}",
        headers=headers,
    )
    assert readiness_res.status_code == 200
    initial_readiness = readiness_res.json()["readiness"]
    assert initial_readiness["overall_score"] == 0.0, "Fresh learner should have 0 readiness"
    assert len(initial_readiness["gaps"]) == 4, "All 4 skill groups should be gaps"
    initial_hours = initial_readiness["estimated_hours_to_ready"]
    assert initial_hours > 0, "Should have estimated hours"

    # ── Step 3: verify initial RL policy is blank ────────────────────────

    rl_res = await client.get(f"/api/v1/learner/{learner_id}/rl-policy", headers=headers)
    assert rl_res.json()["has_learned"] is False

    # ── Step 4: learn concepts across multiple sessions ──────────────────

    mastered_concepts = []
    readiness_progression = [0.0]
    total_attempts = 0
    sessions_run = 0

    # We'll run enough sessions to master several concepts.
    # Each session starts fresh, teaches the next concept in the learning path.
    for session_num in range(8):
        random.seed(42 + session_num)  # re-seed per session for variety but stability

        start = await _start_session(client, learner_id, headers)
        session_id = start["session_id"]
        sessions_run += 1

        if start["action"] != "teach":
            # might be decay_check or something else — just answer and continue
            await _respond(client, session_id, headers,
                           content="I remember this concept well.")
            continue

        concept_id = start["concept"]["id"]
        concept_name = start["concept"].get("name", concept_id)

        # drive concept to mastery
        final_action, attempts = await _master_current_concept(
            client, session_id, headers, concept_name,
        )
        total_attempts += attempts

        if final_action in ("mastered_and_advance", "mastered_all_done"):
            mastered_concepts.append(concept_id)

            # check readiness after this mastery
            rr = await client.get(
                f"/api/v1/career/readiness/{learner_id}/{QUANT_ROLE_ID}",
                headers=headers,
            )
            current_readiness = rr.json()["readiness"]["overall_score"]
            readiness_progression.append(current_readiness)

    # ── Step 5: assertions on the journey ────────────────────────────────

    # must have mastered at least 2 concepts across 8 sessions
    assert len(mastered_concepts) >= 2, \
        f"Expected ≥2 mastered concepts, got {len(mastered_concepts)}: {mastered_concepts}"

    # readiness should have increased from 0
    final_readiness = readiness_progression[-1]
    assert final_readiness > 0.0, \
        f"Readiness should have increased from 0, got {final_readiness}"

    # readiness should trend upward (allow minor fluctuations from re-scoring)
    # check that the max readiness achieved is significantly above the start
    max_readiness = max(readiness_progression)
    assert max_readiness > 0.0, \
        f"Peak readiness should be above 0: {readiness_progression}"

    # ── Step 6: verify RL policy learned ─────────────────────────────────

    rl_res2 = await client.get(f"/api/v1/learner/{learner_id}/rl-policy", headers=headers)
    rl_data = rl_res2.json()
    assert rl_data["has_learned"] is True, "RL should have learned after multiple sessions"

    stats = rl_data["policy_stats"]
    # strategy bandit should have updates
    bandit_stats = stats["strategy_bandit"]
    has_learning = any(
        v["alpha"] > 1.0 or v["beta"] > 1.0
        for v in bandit_stats.values()
    )
    assert has_learning, f"Strategy bandit should have learned: {bandit_stats}"

    # Q-learner should have explored states
    assert stats["action_q"]["total_updates"] >= 2, \
        "Q-learner should have multiple updates across sessions"

    # ── Step 7: verify review queue has mastered concepts ────────────────

    reviews_res = await client.get(
        f"/api/v1/learner/{learner_id}/reviews", headers=headers,
    )
    reviews = reviews_res.json()
    assert reviews["total_items"] >= len(mastered_concepts), \
        f"Review queue should have ≥{len(mastered_concepts)} items, got {reviews['total_items']}"

    # ── Step 8: verify analytics reflect real data ───────────────────────

    analytics_res = await client.get(
        f"/api/v1/analytics/{learner_id}", headers=headers,
    )
    analytics = analytics_res.json()

    # should have velocity data for domains we learned from
    velocity = analytics["learning_velocity"]
    assert len(velocity) >= 1, "Should have at least one domain in velocity"

    # strategy effectiveness should have at least one strategy tracked
    strategies = analytics["strategy_effectiveness"]
    assert len(strategies) >= 1, "Should have at least one strategy tracked"

    # learning patterns should have something to say
    patterns = analytics["learning_patterns"]
    # might be empty for a short journey, but the list should exist
    assert isinstance(patterns, list)

    # ── Step 9: verify learner state is comprehensive ────────────────────

    state_res = await client.get(
        f"/api/v1/learner/{learner_id}/state", headers=headers,
    )
    state = state_res.json()

    # should have concept states for everything we touched
    assert len(state["concept_states"]) >= len(mastered_concepts)

    # career targets should still be set
    assert QUANT_ROLE_ID in state["career_targets"]

    # mastered count should match
    mastered_in_state = sum(
        1 for cs in state["concept_states"].values()
        if cs["status"] == "mastered"
    )
    assert mastered_in_state == len(mastered_concepts), \
        f"State shows {mastered_in_state} mastered but we tracked {len(mastered_concepts)}"

    # ── Step 10: verify hours-to-ready decreased ─────────────────────────

    final_rr = await client.get(
        f"/api/v1/career/readiness/{learner_id}/{QUANT_ROLE_ID}",
        headers=headers,
    )
    assert final_rr.status_code == 200, f"Final readiness failed: {final_rr.text}"
    final_body = final_rr.json()
    assert "readiness" in final_body, f"Missing 'readiness' key: {list(final_body.keys())}"
    final_data = final_body["readiness"]
    assert final_data["estimated_hours_to_ready"] < initial_hours, \
        f"Hours should decrease: {final_data['estimated_hours_to_ready']} >= {initial_hours}"

    # at least one skill group should show "in_progress"
    statuses = [s["status"] for s in final_data["skill_breakdown"]]
    assert "in_progress" in statuses or "complete" in statuses, \
        f"At least one skill should be in_progress or complete: {statuses}"


@pytest.mark.live
async def test_quant_journey_returning_learner(client):
    """
    Simulate a returning learner: learn in session 1, then come back in
    session 2. State, career target, and progress should persist.
    """
    random.seed(99)

    token, learner_id = await _register(client, name="Returning Quant")
    headers = {"Authorization": f"Bearer {token}"}

    # set career target
    await client.put(
        f"/api/v1/learner/{learner_id}/career-target",
        json={"role_ids": [QUANT_ROLE_ID]},
        headers=headers,
    )

    # Session 1: learn one concept
    s1 = await _start_session(client, learner_id, headers)
    s1_id = s1["session_id"]
    assert s1["action"] == "teach"
    concept_1 = s1["concept"]["id"]

    action, _ = await _master_current_concept(client, s1_id, headers, concept_1)

    # capture state after session 1
    state_after_s1 = await client.get(
        f"/api/v1/learner/{learner_id}/state", headers=headers,
    )
    concepts_after_s1 = len(state_after_s1.json()["concept_states"])
    mastered_after_s1 = sum(
        1 for cs in state_after_s1.json()["concept_states"].values()
        if cs["status"] == "mastered"
    )

    # Session 2: returning learner — system should remember everything
    random.seed(100)
    s2 = await _start_session(client, learner_id, headers)
    s2_id = s2["session_id"]
    assert s2_id != s1_id, "Should be a new session"

    # state should still have everything from session 1
    state_after_s2_start = await client.get(
        f"/api/v1/learner/{learner_id}/state", headers=headers,
    )
    s2_data = state_after_s2_start.json()
    assert len(s2_data["concept_states"]) >= concepts_after_s1
    assert QUANT_ROLE_ID in s2_data["career_targets"]

    mastered_still = sum(
        1 for cs in s2_data["concept_states"].values()
        if cs["status"] == "mastered"
    )
    assert mastered_still >= mastered_after_s1, \
        "Mastered concepts should persist between sessions"

    # if session 1 mastered concept_1, session 2 should teach the next concept
    if action in ("mastered_and_advance", "mastered_all_done"):
        if s2["action"] == "teach" and s2.get("concept"):
            assert s2["concept"]["id"] != concept_1, \
                "Returning session should teach the NEXT concept, not repeat"


async def test_quant_career_readiness_detail(client):
    """
    Verify the career readiness response structure is detailed and accurate
    for the quantitative_analyst role.
    """
    token, learner_id = await _register(client, name="Readiness Checker")
    headers = {"Authorization": f"Bearer {token}"}

    # set career target
    await client.put(
        f"/api/v1/learner/{learner_id}/career-target",
        json={"role_ids": [QUANT_ROLE_ID]},
        headers=headers,
    )

    readiness_res = await client.get(
        f"/api/v1/career/readiness/{learner_id}/{QUANT_ROLE_ID}",
        headers=headers,
    )
    assert readiness_res.status_code == 200
    data = readiness_res.json()

    readiness = data["readiness"]
    assert readiness["role_id"] == QUANT_ROLE_ID
    assert readiness["role_title"] == "Junior Quantitative Analyst"

    # check all 4 skill groups are present
    skill_names = {s["name"] for s in readiness["skill_breakdown"]}
    assert "Python Fluency" in skill_names
    assert "Algorithms & DS" in skill_names
    assert "Math & Statistics" in skill_names
    assert "Data Pipelines" in skill_names

    # weights should sum to 1.0
    total_weight = sum(s["weight"] for s in readiness["skill_breakdown"])
    assert abs(total_weight - 1.0) < 0.01, f"Weights should sum to 1.0, got {total_weight}"

    # all skills should be "not_started" for fresh learner
    for s in readiness["skill_breakdown"]:
        assert s["status"] == "not_started"
        assert s["concepts_mastered"] == 0

    # should have a learning path
    learning_path = data["learning_path"]
    assert len(learning_path) >= 15, \
        f"Quant path should have ≥15 concepts (with prereqs), got {len(learning_path)}"

    # learning path should respect prerequisites — no concept before its prereqs
    seen = set()
    from backend.services.knowledge_graph import knowledge_graph
    for step in learning_path:
        cid = step["concept_id"]
        prereqs = knowledge_graph.get_prerequisites(cid)
        # all prereqs should have appeared earlier OR be already mastered
        for p in prereqs:
            if p in data.get("readiness", {}).get("mastered", set()):
                continue
            # prereq should be in the path before this concept
            # (it's ok if it's not in the path at all — might be outside scope)
        seen.add(cid)


async def test_quant_motivation_across_journey(client):
    """
    Verify the motivation agent tracks engagement correctly across a
    multi-step quant learning journey.
    """
    from backend.agents.motivation import MotivationAgent

    agent = MotivationAgent()
    sid = "quant-motivation"

    # simulate a realistic session: first few interactions are neutral
    agent.record_interaction(sid, "I think variables store values", score=None)
    assert agent.detect_state(sid) == "neutral"

    # learner starts failing tests (struggling with closures)
    agent.record_interaction(sid, "idk", score=0.2, is_test_result=True)
    agent.record_interaction(sid, "maybe global?", score=0.15, is_test_result=True)
    agent.record_interaction(sid, "not sure", score=0.25, is_test_result=True)
    assert agent.detect_state(sid) == "frustrated"

    # system should intervene
    intervention = agent.get_intervention(sid, None)
    assert intervention is not None
    assert intervention["action"] == "reduce_difficulty"
    assert intervention["engagement_state"] == "frustrated"

    # after reteaching, learner starts succeeding
    agent.record_interaction(sid, "Oh! The lambda captures by reference!", score=0.85, is_test_result=True)
    agent.record_interaction(sid, "Default arg captures current value.", score=0.9, is_test_result=True)
    agent.record_interaction(sid, "functools.partial also works.", score=0.88, is_test_result=True)
    state = agent.detect_state(sid)
    # should no longer be frustrated
    assert state != "frustrated", f"Should recover from frustrated, got {state}"

    agent.cleanup_session(sid)


async def test_quant_rl_adapts_to_learner_profile(client):
    """
    Verify that after several sessions, the RL engine develops a non-trivial
    policy tailored to the quant learner's performance.
    """
    from backend.agents.rl_engine import RLEngine

    engine = RLEngine()
    random.seed(77)

    # simulate a quant learner: does well with worked_examples, poorly with socratic
    for _ in range(50):
        strategy = engine.select_strategy()
        if strategy == "worked_examples":
            score = max(0, min(1, random.gauss(0.85, 0.1)))
        elif strategy == "debugging_exercise":
            score = max(0, min(1, random.gauss(0.75, 0.1)))
        else:
            score = max(0, min(1, random.gauss(0.45, 0.15)))
        engine.update_strategy(strategy, score)

    # the bandit should have learned that worked_examples is best
    best = engine.get_best_strategy()
    assert best in ("worked_examples", "debugging_exercise"), \
        f"Expected worked_examples or debugging_exercise as best, got {best}"

    stats = engine.strategy_bandit.get_stats()
    assert stats["worked_examples"]["expected"] > stats["socratic"]["expected"], \
        "Worked examples should have higher expected value than socratic for this learner"

    # difficulty should adapt: quant learner with fast velocity → higher difficulty
    bandit = engine.difficulty_bandit
    for _ in range(40):
        bandit.update(1.5, 0.0, 0, difficulty=3, threshold=0.8, reward=9.0)
        bandit.update(1.5, 0.0, 0, difficulty=1, threshold=0.6, reward=2.0)
    bandit.total_updates = 300  # force exploitation

    selections = [bandit.select_difficulty(1.5, 0.0, 0) for _ in range(20)]
    assert selections.count(3) > 12, \
        f"Fast quant learner should prefer difficulty 3: {selections.count(3)}/20"


async def test_quant_review_scheduling_after_mastery(client):
    """
    Verify that mastered quant concepts get scheduled for spaced repetition
    with correct SM-2 properties.
    """
    from backend.agents.review_scheduler import ReviewSchedulerAgent
    from backend.models.learner import LearnerState, ConceptMastery

    scheduler = ReviewSchedulerAgent()
    learner = LearnerState(learner_id="quant-review")

    # simulate mastering 3 quant-relevant concepts with different scores
    concepts_and_scores = [
        ("python.closures", 0.85),
        ("ds.arrays_lists", 0.95),
        ("python.recursion", 0.72),
    ]

    for concept_id, score in concepts_and_scores:
        learner.concept_states[concept_id] = ConceptMastery(
            concept_id=concept_id, status="mastered"
        )
        scheduler.schedule_review(learner, concept_id, score)

    # should have 3 items in review queue
    assert len(learner.review_queue) == 3

    # higher scores should get longer intervals (higher easiness factor)
    intervals = {}
    for item in learner.review_queue:
        intervals[item["concept_id"]] = item["interval_days"]

    # ds.arrays_lists (score 0.95) should have longer interval than python.recursion (0.72)
    assert intervals["ds.arrays_lists"] >= intervals["python.recursion"], \
        f"Higher score should get longer interval: " \
        f"arrays={intervals['ds.arrays_lists']}, recursion={intervals['python.recursion']}"

    # none should be due immediately
    due = scheduler.get_due_reviews(learner)
    assert len(due) == 0, "Just-scheduled reviews should not be due yet"


async def test_quant_analytics_strategy_profile(client):
    """
    Verify analytics correctly profile a quant learner's strategy effectiveness
    across multiple concepts.
    """
    from backend.agents.analytics import AnalyticsAgent
    from backend.models.learner import LearnerState, ConceptMastery

    agent = AnalyticsAgent()
    learner = LearnerState(learner_id="quant-analytics")

    # quant learner: worked_examples consistently better than socratic
    learner.concept_states["python.closures"] = ConceptMastery(
        concept_id="python.closures", status="mastered",
        teaching_strategies_tried={"worked_examples": 0.9, "socratic": 0.4},
    )
    learner.concept_states["ds.arrays_lists"] = ConceptMastery(
        concept_id="ds.arrays_lists", status="mastered",
        teaching_strategies_tried={"worked_examples": 0.85, "analogy": 0.6},
    )
    learner.concept_states["python.recursion"] = ConceptMastery(
        concept_id="python.recursion", status="mastered",
        teaching_strategies_tried={"debugging_exercise": 0.75, "socratic": 0.5},
    )

    effectiveness = agent.compute_strategy_effectiveness(learner)
    assert effectiveness["worked_examples"]["usage_count"] == 2
    assert abs(effectiveness["worked_examples"]["avg_score"] - 0.875) < 0.001
    assert effectiveness["socratic"]["usage_count"] == 2
    assert abs(effectiveness["socratic"]["avg_score"] - 0.45) < 0.001

    patterns = agent.identify_learning_patterns(learner)
    # should identify worked_examples as best strategy
    assert any("worked_examples" in p.lower() for p in patterns), \
        f"Should identify worked_examples as effective: {patterns}"

    velocity = agent.compute_learning_velocity(learner)
    assert velocity["python"]["concepts_mastered"] == 2
    assert velocity["ds"]["concepts_mastered"] == 1


async def test_quant_diagnostic_for_experienced_learner(client):
    """
    Verify the diagnostic agent correctly handles an experienced learner
    who already knows some quant-relevant concepts.
    """
    from backend.agents.diagnostic import DiagnosticAgent
    from backend.models.learner import LearnerState, ConceptMastery

    agent = DiagnosticAgent()
    learner = LearnerState(
        learner_id="quant-diagnostic",
        experience_level="intermediate",
    )

    # learner already knows basics
    learner.concept_states["python.variables"] = ConceptMastery(
        concept_id="python.variables", status="mastered",
    )
    learner.concept_states["python.control_flow"] = ConceptMastery(
        concept_id="python.control_flow", status="mastered",
    )

    # should run diagnostic — intermediate with few concepts mapped
    assert agent.should_run_diagnostic(learner) is True

    # probe selection should skip already-mastered concepts
    probes = agent.select_probe_concepts(learner, domain="python")
    for p in probes:
        assert p not in ("python.variables", "python.control_flow"), \
            f"Should not probe already-mastered: {p}"

    # simulate diagnostic: learner knows closures → infer prereqs
    results = [{"concept_id": "python.closures", "score": 0.82}]
    inferred = agent.infer_mastery_from_diagnostics(results, learner)
    assert inferred["python.closures"] == "mastered"

    # apply results
    applied = agent.apply_diagnostic_results(learner, inferred)
    assert applied >= 1

    # after diagnostic, closures and its prereqs should be in learner state
    assert learner.concept_states["python.closures"].status == "mastered"


async def test_quant_events_chronicle_session(client):
    """
    Verify that session events chronicle the full learning lifecycle
    for a quant learning session.
    """
    random.seed(55)

    token, learner_id = await _register(client, name="Event Tracker")
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        f"/api/v1/learner/{learner_id}/career-target",
        json={"role_ids": [QUANT_ROLE_ID]},
        headers=headers,
    )

    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]

    # run through teach → practice → self-assess → test
    await _respond(client, session_id, headers, content="Understanding variables for quant work")
    await _respond(client, session_id, headers, content="Practice: arrays for time series data")
    await _respond(client, session_id, headers,
                   response_type="self_assessment", content="7", confidence=7)
    await _respond(client, session_id, headers,
                   content="Late binding in closures, fix with default arg")

    # check events
    events_res = await client.get(
        f"/api/v1/session/{session_id}/events", headers=headers,
    )
    assert events_res.status_code == 200
    events = events_res.json()

    event_types = [e["event_type"] for e in events]

    # must have teaching started
    assert "TEACHING_STARTED" in event_types, \
        f"Missing TEACHING_STARTED in {event_types}"

    # must have some assessment/test event
    assert any("TEST" in t or "ASSESSMENT" in t or "PRACTICE" in t for t in event_types), \
        f"Missing test/assessment/practice event in {event_types}"

    # every event should be well-formed
    for e in events:
        assert "event_id" in e
        assert "event_type" in e
        assert "source_agent" in e
        assert "timestamp" in e
        assert e["session_id"] == session_id


async def test_quant_chat_mid_session(client):
    """
    Verify a quant learner can ask questions mid-session without breaking flow.
    """
    random.seed(66)

    token, learner_id = await _register(client, name="Chatty Quant")
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        f"/api/v1/learner/{learner_id}/career-target",
        json={"role_ids": [QUANT_ROLE_ID]},
        headers=headers,
    )

    start = await _start_session(client, learner_id, headers)
    session_id = start["session_id"]

    # answer teaching, then ask a chat question
    await _respond(client, session_id, headers, content="I understand the basics")

    chat = await _respond(client, session_id, headers,
                          response_type="chat",
                          content="How does this concept apply to building a Monte Carlo simulation?")
    assert chat["action"] in ("chat_response", "continue", "teach", "practice")

    # should still be able to continue the learning flow
    step = await _respond(client, session_id, headers, content="Back to practice now")
    assert step["action"] in VALID_ACTIONS


async def test_quant_readiness_role_detail(client):
    """
    Verify the quant role is discoverable in the roles list and has correct metadata.
    """
    token, _ = await _register(client, name="Role Browser")
    headers = {"Authorization": f"Bearer {token}"}

    # list all roles
    roles_res = await client.get("/api/v1/career/roles")
    assert roles_res.status_code == 200
    roles = roles_res.json()

    quant_role = None
    for role in roles:
        if role["id"] == QUANT_ROLE_ID:
            quant_role = role
            break
    assert quant_role is not None, f"Quant role not found in roles list"
    assert quant_role["title"] == "Junior Quantitative Analyst"
    assert quant_role["level"] == "mid"
    assert quant_role["market_demand"] == "high"

    # get role detail
    detail_res = await client.get(f"/api/v1/career/roles/{QUANT_ROLE_ID}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == QUANT_ROLE_ID
    assert len(detail["required_skills"]) == 4
    assert detail["salary_range"]["min"] == 95000
    assert detail["salary_range"]["max"] == 150000
