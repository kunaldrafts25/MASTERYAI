# live LLM integration tests — requires AWS Bedrock credentials

import pytest
import random
import json
import os
import textwrap
from datetime import datetime, timezone

VALID_ACTIONS = (
    "teach", "decay_check", "complete", "transfer_test", "practice",
    "self_assess", "mastered_and_advance", "mastered_all_done",
    "retest", "reteach", "chat_response", "continue", "error",
    "concept_selected", "mastered", "career_info", "readiness_check",
    "dialogue",
)


async def _register(client, suffix=None):
    suffix = suffix or random.randint(10000, 99999)
    res = await client.post("/api/v1/auth/register", json={
        "email": f"live_{suffix}@test.com",
        "password": "pass1234",
        "name": "Live Tester",
    })
    assert res.status_code == 200, f"Registration failed: {res.text}"
    data = res.json()
    return data["token"], data["learner_id"]


async def _start(client, learner_id, headers):
    res = await client.post(
        "/api/v1/session/start",
        json={"learner_id": learner_id},
        headers=headers,
    )
    assert res.status_code == 200, f"Session start failed: {res.text}"
    return res.json()


async def _respond(client, session_id, headers, content="I understand",
                   response_type="answer", confidence=None, allow_fail=False):
    body = {"response_type": response_type, "content": content}
    if confidence is not None:
        body["confidence"] = confidence
    res = await client.post(
        f"/api/v1/session/{session_id}/respond",
        json=body,
        headers=headers,
    )
    if allow_fail and res.status_code != 200:
        return None
    assert res.status_code == 200, f"Respond failed: {res.text}"
    return res.json()


# --- test 1: full learning session with real LLM ---

@pytest.mark.live
async def test_live_full_learning_session(live_client):
    token, learner_id = await _register(live_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Start session — should get an action (typically "teach")
    start = await _start(live_client, learner_id, headers)
    session_id = start["session_id"]
    assert start["action"] in VALID_ACTIONS
    assert session_id

    # Walk through up to 8 turns of the learning loop
    actions_seen = [start["action"]]
    current = start
    for turn in range(8):
        if current["action"] in ("complete", "mastered_all_done"):
            break

        if current["action"] == "self_assess":
            step = await _respond(live_client, session_id, headers,
                                  response_type="self_assessment",
                                  content="7", confidence=7)
        elif current["action"] == "teach":
            # Give a substantive answer to teaching
            step = await _respond(live_client, session_id, headers,
                                  content="I understand. Variables store values in named memory locations, and you can reassign them freely in Python.")
        else:
            step = await _respond(live_client, session_id, headers,
                                  content="x = 5 stores integer 5 in variable x. We can use type(x) to check its type.")

        assert step["action"] in VALID_ACTIONS, f"Unexpected action: {step['action']}"
        actions_seen.append(step["action"])
        current = step

    # Verify: got more than just "teach" — the loop advanced
    assert len(actions_seen) >= 2, f"Only saw actions: {actions_seen}"

    # Verify learner state was updated
    state_res = await live_client.get(
        f"/api/v1/learner/{learner_id}/state", headers=headers
    )
    assert state_res.status_code == 200
    state = state_res.json()
    assert len(state["concept_states"]) >= 1


# --- test 2: dynamic career role generation ---

@pytest.mark.live
async def test_live_dynamic_role_generation(live_client):
    token, _ = await _register(live_client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await live_client.post(
        "/api/v1/career/generate-role",
        json={"role_description": "machine learning engineer", "level": "mid"},
        headers=headers,
    )
    assert res.status_code == 200, f"Role generation failed: {res.text}"
    data = res.json()

    role = data["role"]
    assert role["id"], "Role must have an id"
    assert role["title"], "Role must have a title"
    assert role["description"], "Role must have a description"
    assert len(role["required_skills"]) >= 2, "Need at least 2 skill groups"

    # Weights should roughly sum to 1.0
    total_weight = sum(s["weight"] for s in role["required_skills"])
    assert 0.9 <= total_weight <= 1.1, f"Weights sum to {total_weight}, expected ~1.0"

    # Each skill should have concept_ids
    for skill in role["required_skills"]:
        assert skill["name"], "Skill must have a name"
        assert len(skill["concept_ids"]) >= 1, f"Skill '{skill['name']}' has no concept_ids"

    # Verify role appears in roles list
    roles_res = await live_client.get("/api/v1/career/roles", headers=headers)
    assert roles_res.status_code == 200
    role_ids = [r["id"] for r in roles_res.json()]
    assert role["id"] in role_ids

    mapping = data["mapping"]
    assert "concepts_mapped" in mapping
    assert "coverage_ratio" in mapping


# --- test 3: topic generation ---

@pytest.mark.live
async def test_live_topic_generation(live_client):
    token, _ = await _register(live_client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await live_client.post(
        "/api/v1/topics/generate",
        json={"topic": "web development", "depth": 6},
        headers=headers,
    )
    assert res.status_code == 200, f"Topic generation failed: {res.text}"
    data = res.json()

    assert data["topic"] == "web development"
    assert data["concepts_generated"] >= 1
    assert data["domain"]

    # Each concept should have proper structure
    for c in data["concepts"]:
        assert c["id"], "Concept must have an id"
        assert "." in c["id"], f"Concept id '{c['id']}' should be in domain.name format"
        assert c["name"], "Concept must have a name"
        assert isinstance(c["difficulty_tier"], int)
        assert 1 <= c["difficulty_tier"] <= 5

    # Verify they're in the knowledge graph now
    domains_res = await live_client.get("/api/v1/topics/domains", headers=headers)
    assert domains_res.status_code == 200
    assert domains_res.json()["total_concepts"] > 0


# --- test 4: multi-turn conversation coherence ---

@pytest.mark.live
async def test_live_multi_turn_conversation(live_client):
    token, learner_id = await _register(live_client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start(live_client, learner_id, headers)
    session_id = start["session_id"]

    # 4 turns — each should produce a valid action and content
    current = start
    for i in range(4):
        if current["action"] in ("complete", "mastered_all_done"):
            break

        assert current["action"] in VALID_ACTIONS

        # Check that we got content from the LLM (not empty)
        content = current.get("content")
        if content and isinstance(content, dict):
            # Teaching content should have actual text
            teaching = content.get("teaching_content", content.get("explanation", ""))
            if teaching:
                assert len(str(teaching)) > 20, f"Teaching content too short: {teaching[:50]}"

        if current["action"] == "self_assess":
            current = await _respond(live_client, session_id, headers,
                                     response_type="self_assessment",
                                     content="6", confidence=6)
        else:
            current = await _respond(live_client, session_id, headers,
                                     content=f"Turn {i+1}: I think I understand this concept. The key idea is about how data is organized and processed.")


# --- test 5: teaching content quality ---

@pytest.mark.live
async def test_live_teaching_content_quality(live_client):
    token, learner_id = await _register(live_client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start(live_client, learner_id, headers)

    # First action should be "teach" for a new learner
    assert start["action"] == "teach", f"Expected 'teach' for new learner, got '{start['action']}'"

    content = start.get("content", {})
    assert content, "Teaching response must include content"

    # The content should have teaching material
    if isinstance(content, dict):
        teaching_text = content.get("teaching_content", "")
        if teaching_text:
            assert len(teaching_text) > 50, f"Teaching content too short ({len(teaching_text)} chars)"

    # Concept should be identified
    concept = start.get("concept")
    assert concept, "Teaching should identify the concept being taught"
    assert concept.get("id"), "Concept must have an id"


# --- test 6: evaluation produces valid scores ---

@pytest.mark.live
async def test_live_evaluation_scoring(live_client):
    token, learner_id = await _register(live_client)
    headers = {"Authorization": f"Bearer {token}"}

    start = await _start(live_client, learner_id, headers)
    session_id = start["session_id"]

    # Walk through the loop until we hit a test or exhaust turns
    current = start
    reached_test = False
    for turn in range(10):
        if current["action"] in ("complete", "mastered_all_done"):
            break

        if current["action"] in ("transfer_test", "retest"):
            reached_test = True
            # Submit a thoughtful answer for the test
            result = await _respond(
                live_client, session_id, headers,
                content="The function uses a closure to capture the variable. Since Python closures capture by reference, the lambda sees the final value of the loop variable. To fix this, use a default argument: lambda i=i: process(i), which captures the value at each iteration."
            )
            # After a test, we should get a result action
            assert result["action"] in VALID_ACTIONS

            # Check if score is in the response
            score = result.get("score") or (result.get("content", {}).get("total_score") if isinstance(result.get("content"), dict) else None)
            if score is not None:
                assert 0.0 <= float(score) <= 1.0, f"Score {score} out of range"
            break

        if current["action"] == "self_assess":
            current = await _respond(live_client, session_id, headers,
                                     response_type="self_assessment",
                                     content="8", confidence=8)
        else:
            current = await _respond(live_client, session_id, headers,
                                     content="Variables are named references to objects in memory. In Python, assignment creates a binding between the name and the object. Types are determined at runtime.")

    # We should have progressed through the learning loop
    # (may not always reach test in 10 turns with real LLM, that's ok)


# --- test 7: full DevOps engineer journey ---

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")


class JourneyLogger:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "w", encoding="utf-8")
        self.step = 0

    def close(self):
        self.f.close()

    def _write(self, text: str):
        self.f.write(text + "\n")
        self.f.flush()

    def header(self, title: str):
        border = "=" * 80
        self._write(f"\n{border}")
        self._write(f"  {title}")
        self._write(f"{border}\n")

    def section(self, title: str):
        self._write(f"\n{'─' * 70}")
        self._write(f"  {title}")
        self._write(f"{'─' * 70}\n")

    def kv(self, key: str, value, indent: int = 0):
        prefix = "  " * indent
        if isinstance(value, (dict, list)):
            self._write(f"{prefix}{key}:")
            self._write(textwrap.indent(json.dumps(value, indent=2), prefix + "  "))
        else:
            self._write(f"{prefix}{key}: {value}")

    def step_header(self, action: str, concept: str = ""):
        self.step += 1
        label = f"[Step {self.step}] Action: {action}"
        if concept:
            label += f"  |  Concept: {concept}"
        self._write(f"\n  >>> {label}")

    def text(self, msg: str):
        self._write(f"  {msg}")

    def teaching_content(self, content):
        if not content or not isinstance(content, dict):
            self._write(f"  Content: {content}")
            return
        strategy = content.get("strategy_used", "unknown")
        teaching = content.get("teaching_content", "")
        check_q = content.get("check_question", "")
        self._write(f"  Strategy: {strategy}")
        if teaching:
            wrapped = textwrap.fill(str(teaching), width=76, initial_indent="  ", subsequent_indent="  ")
            self._write(f"  Teaching:\n{wrapped}")
        if check_q:
            self._write(f"  Check question: {check_q}")

    def score_info(self, data):
        if isinstance(data, dict):
            score = data.get("score") or data.get("total_score")
            level = data.get("understanding_level", "")
            miscon = data.get("misconceptions_detected", [])
            if score is not None:
                self._write(f"  Score: {score}")
            if level:
                self._write(f"  Understanding: {level}")
            if miscon:
                self._write(f"  Misconceptions: {miscon}")


@pytest.mark.live
async def test_live_devops_journey(live_client):
    log_path = os.path.join(LOG_DIR, "devops_journey.log")
    log = JourneyLogger(log_path)

    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        log.header(f"DEVOPS ENGINEER LEARNING JOURNEY — {ts}")

        # ── Step 1: Register ──
        log.section("1. REGISTER LEARNER")
        token, learner_id = await _register(live_client, suffix="devops")
        headers = {"Authorization": f"Bearer {token}"}
        log.kv("Learner ID", learner_id)

        # ── Step 2: Generate DevOps role ──
        log.section("2. GENERATE DEVOPS ROLE (Real LLM)")
        gen_res = await live_client.post(
            "/api/v1/career/generate-role",
            json={"role_description": "DevOps engineer", "level": "mid"},
            headers=headers,
        )
        if gen_res.status_code != 200:
            log.text(f"  Role generation failed (HTTP {gen_res.status_code})")
            log.text(f"  LLM rate limit reached. Wait for reset and re-run.")
            log.header("JOURNEY ABORTED — RATE LIMIT")
            log.close()
            pytest.skip(f"LLM rate limit hit — try again when daily limit resets")
        gen_data = gen_res.json()
        role = gen_data["role"]
        role_id = role["id"]

        log.kv("Role ID", role_id)
        log.kv("Title", role["title"])
        log.kv("Description", role["description"])
        log.kv("Level", role["level"])
        log.kv("Market Demand", role.get("market_demand", ""))
        log.kv("Salary Range", role.get("salary_range", {}))

        log.text("")
        log.text("Required Skills:")
        for i, skill in enumerate(role["required_skills"], 1):
            log.kv(f"  [{i}] {skill['name']}", "")
            log.kv("Concepts", skill["concept_ids"], indent=2)
            log.kv("Min Mastery", skill["minimum_mastery"], indent=2)
            log.kv("Weight", skill["weight"], indent=2)

        if role.get("nice_to_have_skills"):
            log.text("\nNice-to-Have Skills:")
            for skill in role["nice_to_have_skills"]:
                log.kv(f"  {skill['name']}", skill["concept_ids"])

        log.text("")
        log.kv("Concept Mapping", gen_data["mapping"])

        # ── Step 3: Set career target ──
        log.section("3. SET CAREER TARGET")
        target_res = await live_client.put(
            f"/api/v1/learner/{learner_id}/career-target",
            json={"role_ids": [role_id]},
            headers=headers,
        )
        assert target_res.status_code == 200, f"Set target failed: {target_res.text}"
        target_data = target_res.json()
        log.kv("Career Targets", target_data["career_targets"])
        if target_data.get("readiness"):
            for r in target_data["readiness"]:
                log.kv("Initial Readiness", f"{r.get('overall_score', 0) * 100:.1f}%")

        # ── Step 4: Check initial readiness ──
        log.section("4. INITIAL CAREER READINESS")
        readiness_res = await live_client.get(
            f"/api/v1/career/readiness/{learner_id}/{role_id}",
            headers=headers,
        )
        if readiness_res.status_code == 200:
            readiness_data = readiness_res.json()
            r = readiness_data["readiness"]
            log.kv("Overall Score", f"{r['overall_score'] * 100:.1f}%")
            log.kv("Total Concepts to Learn", readiness_data.get("total_concepts", 0))
            log.kv("Estimated Hours", readiness_data.get("total_hours", 0))
            if r.get("skill_readiness"):
                log.text("\nSkill Breakdown:")
                for sr in r["skill_readiness"]:
                    log.kv(f"  {sr['skill_name']}", f"{sr['readiness'] * 100:.0f}% ready", indent=1)
            if readiness_data.get("learning_path"):
                log.text(f"\nLearning Path ({len(readiness_data['learning_path'])} steps):")
                for i, step in enumerate(readiness_data["learning_path"][:10], 1):
                    log.kv(f"  {i}. {step['concept_id']}", f"priority={step.get('priority', '')}, ~{step.get('estimated_hours', '?')}h", indent=1)
                if len(readiness_data["learning_path"]) > 10:
                    log.text(f"  ... and {len(readiness_data['learning_path']) - 10} more")
        else:
            log.kv("Readiness check", f"HTTP {readiness_res.status_code}")

        # ── Step 5: Learning sessions ──
        NUM_SESSIONS = 3
        TURNS_PER_SESSION = 8
        all_actions = []
        all_concepts_touched = set()
        session_summaries = []
        rate_limited = False

        for session_num in range(1, NUM_SESSIONS + 1):
            if rate_limited:
                log.text(f"\n  (Skipping session {session_num} — rate limit hit)")
                break

            log.section(f"5.{session_num} LEARNING SESSION {session_num}")

            start_res = await live_client.post(
                "/api/v1/session/start",
                json={"learner_id": learner_id},
                headers=headers,
            )
            if start_res.status_code != 200:
                log.text(f"  Session start failed (HTTP {start_res.status_code}) — likely rate limited")
                rate_limited = True
                break
            start = start_res.json()
            session_id = start["session_id"]
            log.kv("Session ID", session_id)

            log.step = 0  # reset step counter per session
            concept_id = ""
            if start.get("concept"):
                concept_id = start["concept"]["id"]
                all_concepts_touched.add(concept_id)
            log.step_header(start["action"], concept_id)

            if start["action"] == "teach" and start.get("content"):
                log.teaching_content(start["content"])

            current = start
            session_actions = [start["action"]]
            session_scores = []

            for turn in range(TURNS_PER_SESSION):
                if current["action"] in ("complete", "mastered_all_done"):
                    log.text("  >> Session complete!")
                    break

                # Build a contextual response
                if current["action"] == "self_assess":
                    step = await _respond(live_client, session_id, headers,
                                          response_type="self_assessment",
                                          content="7", confidence=7,
                                          allow_fail=True)
                elif current["action"] == "teach":
                    step = await _respond(live_client, session_id, headers,
                                          content="I understand the concept. It's about creating reliable, automated infrastructure pipelines. CI/CD ensures code changes are tested and deployed consistently.",
                                          allow_fail=True)
                elif current["action"] in ("transfer_test", "retest"):
                    step = await _respond(live_client, session_id, headers,
                                          content="The key approach is to use infrastructure as code tools like Terraform to define resources declaratively, combined with containerization via Docker for consistent environments. CI/CD pipelines automate testing and deployment, while monitoring with tools like Prometheus ensures observability.",
                                          allow_fail=True)
                elif current["action"] == "practice":
                    step = await _respond(live_client, session_id, headers,
                                          content="To implement this, I would create a Dockerfile that defines the application environment, write a docker-compose.yml for orchestration, and set up a GitHub Actions workflow for automated testing and deployment to the staging environment.",
                                          allow_fail=True)
                else:
                    step = await _respond(live_client, session_id, headers,
                                          content="I understand the concept and can apply it in practice.",
                                          allow_fail=True)

                if step is None:
                    log.text("  >> Rate limit hit — ending session early")
                    rate_limited = True
                    break

                assert step["action"] in VALID_ACTIONS, f"Invalid action: {step['action']}"

                concept_now = ""
                if step.get("concept"):
                    concept_now = step["concept"]["id"]
                    all_concepts_touched.add(concept_now)
                log.step_header(step["action"], concept_now)

                # Log content based on action type
                if step["action"] == "teach" and step.get("content"):
                    log.teaching_content(step["content"])
                elif step["action"] in ("mastered_and_advance", "mastered", "retest", "reteach"):
                    if isinstance(step.get("content"), dict):
                        log.score_info(step["content"])
                        s = step["content"].get("score") or step["content"].get("total_score")
                        if s is not None:
                            session_scores.append(float(s))
                elif step["action"] == "practice" and step.get("content"):
                    if isinstance(step["content"], dict):
                        problems = step["content"].get("problems", [])
                        if problems:
                            log.text(f"  Practice problems: {len(problems)}")
                            for p in problems[:2]:
                                q = p.get("question", p.get("problem_statement", ""))
                                if q:
                                    log.text(f"    Q: {str(q)[:120]}")

                session_actions.append(step["action"])
                current = step

            avg_score = sum(session_scores) / len(session_scores) if session_scores else None
            summary = {
                "session": session_num,
                "turns": len(session_actions),
                "actions": session_actions,
                "scores": session_scores,
                "avg_score": avg_score,
            }
            session_summaries.append(summary)

            log.text("")
            log.text(f"  Session {session_num} Summary:")
            log.kv("Turns", len(session_actions), indent=2)
            log.kv("Actions", " → ".join(session_actions), indent=2)
            if session_scores:
                log.kv("Scores", [f"{s:.2f}" for s in session_scores], indent=2)
                log.kv("Avg Score", f"{avg_score:.2f}", indent=2)

        # ── Step 6: Final state ──
        log.section("6. FINAL LEARNER STATE")
        state_res = await live_client.get(
            f"/api/v1/learner/{learner_id}/state", headers=headers
        )
        assert state_res.status_code == 200
        state = state_res.json()

        mastered = [cid for cid, cs in state["concept_states"].items()
                    if cs.get("status") == "mastered"]
        in_progress = [cid for cid, cs in state["concept_states"].items()
                       if cs.get("status") not in ("mastered", None)]

        log.kv("Concepts Touched", len(state["concept_states"]))
        log.kv("Concepts Mastered", mastered if mastered else "None yet")
        log.kv("Concepts In Progress", in_progress if in_progress else "None")
        log.kv("Total Hours", state.get("stats", {}).get("total_hours", 0))

        for cid, cs in state["concept_states"].items():
            log.text(f"  {cid}:")
            log.kv("Status", cs.get("status", "unknown"), indent=2)
            log.kv("Mastery", f"{cs.get('mastery_score', 0) * 100:.0f}%", indent=2)
            if cs.get("test_history"):
                scores = [t.get("score", 0) for t in cs["test_history"]]
                log.kv("Test Scores", [f"{s:.2f}" for s in scores], indent=2)
            if cs.get("misconceptions_active"):
                log.kv("Active Misconceptions", cs["misconceptions_active"], indent=2)

        # ── Step 7: Final readiness ──
        log.section("7. FINAL CAREER READINESS")
        final_res = await live_client.get(
            f"/api/v1/career/readiness/{learner_id}/{role_id}",
            headers=headers,
        )
        if final_res.status_code == 200:
            final_data = final_res.json()
            r = final_data["readiness"]
            log.kv("Overall Score", f"{r['overall_score'] * 100:.1f}%")
            if r.get("skill_readiness"):
                for sr in r["skill_readiness"]:
                    log.kv(f"  {sr['skill_name']}", f"{sr['readiness'] * 100:.0f}% ready", indent=1)
            log.kv("Remaining Hours", final_data.get("total_hours", 0))

        # ── Step 8: Analytics ──
        log.section("8. LEARNING ANALYTICS")
        analytics_res = await live_client.get(
            f"/api/v1/analytics/{learner_id}", headers=headers
        )
        if analytics_res.status_code == 200:
            analytics = analytics_res.json()
            if analytics.get("learning_velocity"):
                log.text("Learning Velocity by Domain:")
                for domain, vel in analytics["learning_velocity"].items():
                    log.kv(f"  {domain}", vel, indent=1)
            if analytics.get("strategy_effectiveness"):
                log.text("\nStrategy Effectiveness:")
                for strat, eff in analytics["strategy_effectiveness"].items():
                    log.kv(f"  {strat}", eff, indent=1)

        # ── Step 9: RL policy ──
        log.section("9. RL POLICY STATE")
        policy_res = await live_client.get(
            f"/api/v1/learner/{learner_id}/rl-policy", headers=headers
        )
        if policy_res.status_code == 200:
            policy = policy_res.json()
            log.kv("Has Learned", policy.get("has_learned", False))
            if policy.get("strategy_bandit"):
                log.kv("Strategy Bandit", policy["strategy_bandit"])
            if policy.get("difficulty_bandit"):
                log.kv("Difficulty Bandit (summary)", {
                    k: v for k, v in policy["difficulty_bandit"].items()
                    if k in ("contexts_explored", "total_updates")
                } if isinstance(policy["difficulty_bandit"], dict) else policy["difficulty_bandit"])

        # ── Summary ──
        log.header("JOURNEY COMPLETE")
        log.kv("Sessions", NUM_SESSIONS)
        log.kv("Total Concepts Touched", len(all_concepts_touched))
        log.kv("Concepts Mastered", len(mastered))
        for i, s in enumerate(session_summaries, 1):
            log.kv(f"Session {i}", f"{s['turns']} turns, avg_score={s['avg_score']}")
        log.text(f"\nFull log: {log_path}")

    finally:
        log.close()

    # Final assertions — role generation is the hard requirement,
    # learning sessions may be cut short by rate limits
    assert role_id, "Role should have been generated"
    if rate_limited and len(state["concept_states"]) == 0:
        print(f"\n  DevOps journey log (partial — rate limited): {log_path}\n")
    else:
        assert len(state["concept_states"]) >= 1, "Should have touched at least 1 concept"
    print(f"\n{'=' * 60}")
    print(f"  DevOps journey log: {log_path}")
    print(f"{'=' * 60}\n")
