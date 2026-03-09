# tests for RL engine, review scheduler, motivation, analytics, diagnostic

import pytest
import random
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.agents.rl_engine import (
    StrategyBandit, DifficultyBandit, ActionQLearner, RLEngine, get_rl_engine,
    EngagementBandit, SchedulerBandit, RewardConfig, RLHyperConfig,
    ALL_STRATEGIES, DIFFICULTY_LEVELS, MASTERY_THRESHOLDS, RETEST_MULTIPLIERS,
    ENGAGEMENT_PROFILES, DEFAULT_ENGAGEMENT_PROFILE,
    SM2_PROFILES, DEFAULT_SM2_PROFILE,
)
from backend.agents.review_scheduler import ReviewSchedulerAgent, ReviewItem
from backend.agents.motivation import MotivationAgent, EngagementSignals
from backend.agents.analytics import AnalyticsAgent
from backend.agents.diagnostic import DiagnosticAgent
from backend.models.learner import LearnerState, ConceptMastery, LearningProfile


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register(client):
    res = await client.post("/api/v1/auth/register", json={
        "email": f"rl_{random.randint(1000,9999)}@test.com",
        "password": "pass1234",
        "name": "RL Tester",
    })
    data = res.json()
    return data["token"], data["learner_id"]


# --- RL engine: strategy bandit (Thompson sampling) ---

def test_bandit_selects_best_after_updates():
    bandit = StrategyBandit()

    # give worked_examples 20 high-score updates
    for _ in range(20):
        bandit.update("worked_examples", 0.9)
    # give others low scores
    for s in ["socratic", "analogy", "debugging_exercise", "explain_back"]:
        for _ in range(5):
            bandit.update(s, 0.3)

    # exploitation should return worked_examples
    assert bandit.get_best() == "worked_examples"

    # sampling should favor it heavily (check over 50 samples)
    selections = [bandit.select() for _ in range(50)]
    assert selections.count("worked_examples") > 25


def test_bandit_explores():
    bandit = StrategyBandit()
    selections = set(bandit.select() for _ in range(100))
    # should have selected at least 3 different strategies
    assert len(selections) >= 3


def test_bandit_exclude():
    bandit = StrategyBandit()
    for _ in range(20):
        selected = bandit.select(exclude=["socratic", "analogy"])
        assert selected not in ("socratic", "analogy")


# --- RL engine: difficulty bandit (contextual epsilon-greedy) ---

def test_difficulty_adapts():
    bandit = DifficultyBandit()

    # simulate: difficulty 2 always gets high reward in normal/calibrated/none context
    for _ in range(50):
        bandit.update(1.0, 0.0, 0, difficulty=2, threshold=0.7, reward=8.0)
        bandit.update(1.0, 0.0, 0, difficulty=1, threshold=0.7, reward=2.0)
        bandit.update(1.0, 0.0, 0, difficulty=3, threshold=0.7, reward=1.0)

    # after enough updates, epsilon should be low
    assert bandit.epsilon < 0.15

    # select difficulty many times — should mostly pick 2
    selections = [bandit.select_difficulty(1.0, 0.0, 0) for _ in range(50)]
    assert selections.count(2) > 30


def test_threshold_adapts():
    bandit = DifficultyBandit()

    for _ in range(50):
        bandit.update(1.0, 0.0, 0, difficulty=2, threshold=0.65, reward=9.0)
        bandit.update(1.0, 0.0, 0, difficulty=2, threshold=0.7, reward=3.0)
        bandit.update(1.0, 0.0, 0, difficulty=2, threshold=0.8, reward=1.0)

    selections = [bandit.select_threshold(1.0, 0.0, 0) for _ in range(50)]
    assert selections.count(0.65) > 25


def test_epsilon_decay():
    bandit = DifficultyBandit()
    assert bandit.epsilon == 0.2

    bandit.total_updates = 100
    assert bandit.epsilon < 0.15

    bandit.total_updates = 200
    assert abs(bandit.epsilon - 0.05) < 1e-10


# --- RL engine: action Q-learner (tabular Q-learning) ---

def test_q_learner_learns_mastery_path():
    ql = ActionQLearner(alpha=0.3, gamma=0.9, epsilon=0.0)  # no exploration

    # simulate: teach gets moderate reward, test after teach gets high reward
    for _ in range(30):
        ql.update("unknown|0|0|none|neutral", "teach", 1.0, "introduced|0|0|none|neutral")
        ql.update("introduced|0|0|none|neutral", "practice", 1.0, "practicing|0|0|none|neutral")
        ql.update("practicing|0|0|none|neutral", "test", 10.0, "mastered|1-2|0|none|neutral")

    # Q-value for test in practicing state should be high
    assert ql.q_table["practicing|0|0|none|neutral"]["test"] > 5.0

    # action selection should choose teach for unknown, test for practicing
    assert ql.select_action("unknown", 0, 0, [], "neutral") == "teach"
    assert ql.select_action("practicing", 0, 0, [], "neutral") == "test"


def test_q_learner_cold_start():
    ql = ActionQLearner(epsilon=0.0)

    assert ql.select_action("unknown", 0, 0, []) == "teach"
    assert ql.select_action("introduced", 0, 0, []) == "practice"
    assert ql.select_action("practicing", 0, 0, []) == "test"
    assert ql.select_action("mastered", 0, 0, []) == "skip_ahead"


# --- RL engine: full integration + serialization ---

def test_rl_serialization():
    engine = RLEngine()

    # make some updates
    engine.update_strategy("socratic", 0.8)
    engine.update_strategy("worked_examples", 0.6)
    engine.difficulty_bandit.update(1.0, 0.0, 0, 2, 0.7, 5.0)
    engine.action_q.update("s1", "teach", 3.0, "s2")

    # serialize
    data = engine.to_dict()
    assert "strategy_bandit" in data
    assert "difficulty_bandit" in data
    assert "action_q" in data

    # deserialize
    restored = RLEngine.from_dict(data)
    assert restored.strategy_bandit.arms["socratic"][0] > 1.0  # alpha increased
    assert restored.difficulty_bandit.total_updates == 1
    assert restored.action_q.total_updates == 1
    assert "s1" in restored.action_q.q_table


def test_get_rl_engine_from_learner():
    learner = LearnerState(learner_id="test-1")
    engine = get_rl_engine(learner)
    assert isinstance(engine, RLEngine)

    # update and persist
    engine.update_strategy("analogy", 0.9)
    learner.rl_policy = engine.to_dict()

    # restore
    restored = get_rl_engine(learner)
    assert restored.strategy_bandit.arms["analogy"][0] > 1.0


# --- review scheduler (SM-2) ---

def test_sm2_scheduling():
    scheduler = ReviewSchedulerAgent()
    learner = LearnerState(learner_id="test-2")
    learner.concept_states["python.variables"] = ConceptMastery(concept_id="python.variables")

    # first review with high score
    scheduler.schedule_review(learner, "python.variables", 0.9)
    assert len(learner.review_queue) == 1
    item_data = learner.review_queue[0]
    assert item_data["repetition_count"] == 1
    first_interval = item_data["interval_days"]
    assert 0.5 <= first_interval <= 1.5  # reset_interval varies by SM2 profile

    # second review with high score
    scheduler.schedule_review(learner, "python.variables", 0.85)
    item_data = learner.review_queue[0]
    assert item_data["repetition_count"] == 2
    second_interval = item_data["interval_days"]
    assert second_interval > first_interval  # should grow after second success

    # third review should multiply by easiness factor
    scheduler.schedule_review(learner, "python.variables", 0.8)
    item_data = learner.review_queue[0]
    assert item_data["repetition_count"] == 3
    assert item_data["interval_days"] > second_interval  # should keep growing


def test_sm2_failure_resets():
    scheduler = ReviewSchedulerAgent()
    learner = LearnerState(learner_id="test-3")
    learner.concept_states["python.loops"] = ConceptMastery(concept_id="python.loops")

    # build up intervals
    scheduler.schedule_review(learner, "python.loops", 0.9)
    scheduler.schedule_review(learner, "python.loops", 0.8)
    scheduler.schedule_review(learner, "python.loops", 0.85)

    # fail
    scheduler.schedule_review(learner, "python.loops", 0.2)
    item_data = learner.review_queue[0]
    assert item_data["repetition_count"] == 0
    assert 0.5 <= item_data["interval_days"] <= 1.5  # reset_interval varies by SM2 profile


def test_due_reviews():
    scheduler = ReviewSchedulerAgent()
    learner = LearnerState(learner_id="test-4")

    # manually create a review item that's overdue
    past = (datetime.utcnow() - timedelta(days=5)).isoformat()
    learner.review_queue = [{
        "concept_id": "python.variables",
        "easiness_factor": 2.5,
        "repetition_count": 1,
        "interval_days": 1.0,
        "next_review": past,
        "last_score": 0.8,
        "misconception_count": 0,
    }]

    due = scheduler.get_due_reviews(learner)
    assert len(due) == 1
    assert due[0]["concept_id"] == "python.variables"
    assert due[0]["overdue_days"] > 4

    assert scheduler.has_urgent_reviews(learner)


def test_retention_curve():
    scheduler = ReviewSchedulerAgent()
    learner = LearnerState(learner_id="test-5")

    # no review data
    curve = scheduler.get_retention_curve(learner, "python.variables")
    assert curve["retention"] == 0.0

    # with review data
    learner.review_queue = [{
        "concept_id": "python.variables",
        "easiness_factor": 2.5,
        "repetition_count": 2,
        "interval_days": 6.0,
        "next_review": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        "last_score": 0.85,
        "misconception_count": 0,
    }]

    curve = scheduler.get_retention_curve(learner, "python.variables")
    assert 0.0 < curve["retention"] <= 1.0
    assert curve["stability"] > 0


# --- motivation agent ---

def test_motivation_frustration_detection():
    agent = MotivationAgent()
    sid = "test-session-1"

    # 3 failures
    agent.record_interaction(sid, "wrong answer", score=0.2, is_test_result=True)
    agent.record_interaction(sid, "still wrong", score=0.3, is_test_result=True)
    agent.record_interaction(sid, "nope", score=0.1, is_test_result=True)

    assert agent.detect_state(sid) == "frustrated"


def test_motivation_intervention():
    agent = MotivationAgent()
    sid = "test-session-2"
    learner = LearnerState(learner_id="test-6")

    for _ in range(3):
        agent.record_interaction(sid, "x", score=0.2, is_test_result=True)

    intervention = agent.get_intervention(sid, learner)
    assert intervention is not None
    assert intervention["type"] == "encouragement"
    assert intervention["action"] == "reduce_difficulty"


def test_motivation_flow_no_interrupt():
    agent = MotivationAgent()
    sid = "test-session-3"
    learner = LearnerState(learner_id="test-7")

    # simulate flow: correct answers in 30-180s range
    signals = agent._get_signals(sid)
    signals.consecutive_successes = 4
    signals.response_times = [60, 90, 45, 120]  # all in 30-180 range
    signals.scores = [0.8, 0.9, 0.85, 0.9]

    assert agent.detect_state(sid) == "flow"
    assert agent.get_intervention(sid, learner) is None


def test_motivation_bored_detection():
    agent = MotivationAgent()
    sid = "test-session-4"

    signals = agent._get_signals(sid)
    signals.consecutive_successes = 4
    signals.response_times = [5, 8, 3, 10]  # all < 15s
    signals.scores = [0.9, 0.95, 0.9, 1.0]

    state = agent.detect_state(sid)
    assert state == "bored"

    learner = LearnerState(learner_id="test-8")
    intervention = agent.get_intervention(sid, learner)
    assert intervention is not None
    assert intervention["action"] == "increase_difficulty"


def test_motivation_cleanup():
    agent = MotivationAgent()
    sid = "test-session-5"
    agent.record_interaction(sid, "test", score=0.5, is_test_result=True)
    assert sid in agent._sessions

    agent.cleanup_session(sid)
    assert sid not in agent._sessions


# --- analytics agent ---

def test_analytics_strategy_effectiveness():
    agent = AnalyticsAgent()
    learner = LearnerState(learner_id="test-9")

    learner.concept_states["python.variables"] = ConceptMastery(
        concept_id="python.variables",
        teaching_strategies_tried={"socratic": 0.8, "worked_examples": 0.9},
    )
    learner.concept_states["python.loops"] = ConceptMastery(
        concept_id="python.loops",
        teaching_strategies_tried={"socratic": 0.6, "analogy": 0.7},
    )

    result = agent.compute_strategy_effectiveness(learner)
    assert "socratic" in result
    assert result["socratic"]["usage_count"] == 2
    assert result["socratic"]["avg_score"] == 0.7  # (0.8 + 0.6) / 2
    assert result["worked_examples"]["usage_count"] == 1


def test_analytics_learning_velocity():
    agent = AnalyticsAgent()
    learner = LearnerState(learner_id="test-10")

    learner.concept_states["python.variables"] = ConceptMastery(
        concept_id="python.variables", status="mastered",
    )
    learner.concept_states["python.loops"] = ConceptMastery(
        concept_id="python.loops", status="introduced",
    )

    velocity = agent.compute_learning_velocity(learner)
    assert "python" in velocity
    assert velocity["python"]["concepts_mastered"] == 1
    assert velocity["python"]["total_concepts"] == 2
    assert velocity["python"]["mastery_rate"] == 0.5


def test_analytics_patterns():
    agent = AnalyticsAgent()
    learner = LearnerState(learner_id="test-11")

    learner.concept_states["python.variables"] = ConceptMastery(
        concept_id="python.variables", status="mastered",
        teaching_strategies_tried={"socratic": 0.9, "worked_examples": 0.85},
    )
    learner.concept_states["python.loops"] = ConceptMastery(
        concept_id="python.loops", status="mastered",
        teaching_strategies_tried={"socratic": 0.8},
    )

    patterns = agent.identify_learning_patterns(learner)
    assert isinstance(patterns, list)
    assert len(patterns) >= 1
    # should mention socratic as best strategy
    assert any("socratic" in p.lower() for p in patterns)


def test_analytics_misconception_patterns():
    agent = AnalyticsAgent()
    learner = LearnerState(learner_id="test-12")

    learner.concept_states["python.closures"] = ConceptMastery(
        concept_id="python.closures",
        misconceptions_active=["late_binding"],
        misconceptions_resolved=["scope_confusion"],
    )

    result = agent.compute_misconception_patterns(learner)
    assert result["active_count"] == 1
    assert result["resolved_count"] == 1
    assert "late_binding" in result["active_misconceptions"]


# --- diagnostic agent ---

def test_diagnostic_should_run():
    agent = DiagnosticAgent()

    beginner = LearnerState(learner_id="test-13", experience_level="beginner")
    assert agent.should_run_diagnostic(beginner) is False

    intermediate = LearnerState(learner_id="test-14", experience_level="intermediate")
    assert agent.should_run_diagnostic(intermediate) is True


def test_diagnostic_probe_selection():
    agent = DiagnosticAgent()
    learner = LearnerState(learner_id="test-15", experience_level="intermediate")

    probes = agent.select_probe_concepts(learner, domain="python")
    assert isinstance(probes, list)
    assert len(probes) >= 1


def test_diagnostic_adaptive_next():
    agent = DiagnosticAgent()
    learner = LearnerState(learner_id="test-16")

    probes = ["python.variables", "python.loops", "python.closures"]

    # no results yet → pick middle
    first = agent.adaptive_next_probe(probes, [], learner)
    assert first is not None

    # correct → should go to harder
    next_probe = agent.adaptive_next_probe(
        ["python.variables", "python.closures"],
        [{"concept_id": "python.loops", "score": 0.9}],
        learner,
    )
    assert next_probe is not None


def test_diagnostic_mastery_inference():
    agent = DiagnosticAgent()
    learner = LearnerState(learner_id="test-17")

    results = [
        {"concept_id": "python.closures", "score": 0.85},
        {"concept_id": "python.variables", "score": 0.3},
    ]

    inferred = agent.infer_mastery_from_diagnostics(results, learner)
    assert inferred["python.closures"] == "mastered"
    assert inferred["python.variables"] == "unknown"
    # prerequisites of closures should also be inferred mastered
    # (depends on knowledge graph having prereqs for closures)


# --- integration: API endpoints ---

async def test_rl_policy_endpoint(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/learner/{learner_id}/rl-policy", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "policy_stats" in data
    assert "strategy_bandit" in data["policy_stats"]
    assert "difficulty_bandit" in data["policy_stats"]
    assert "action_q" in data["policy_stats"]


async def test_reviews_endpoint(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/learner/{learner_id}/reviews", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_items" in data
    assert "due_now" in data


async def test_analytics_endpoint(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/analytics/{learner_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "learning_velocity" in data
    assert "strategy_effectiveness" in data
    assert "misconception_patterns" in data
    assert "learning_patterns" in data


async def test_analytics_patterns_endpoint(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/analytics/{learner_id}/patterns", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "patterns" in data
    assert isinstance(data["patterns"], list)


async def test_retention_endpoint(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(
        f"/api/v1/learner/{learner_id}/retention/python.variables",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "retention" in data
    assert "concept_id" in data


# --- phase G: new tests for added RL layers and features ---


def test_engagement_bandit_default_matches_current():
    profile = DEFAULT_ENGAGEMENT_PROFILE
    frust_failures, bored_speed, flow_range, session_max, decline_thresh, short_len = profile
    assert frust_failures == 3
    assert bored_speed == 15
    assert flow_range == (30, 180)
    assert session_max == 60
    assert decline_thresh == -0.15
    assert short_len == 20


def test_engagement_bandit_learns_profile():
    bandit = EngagementBandit()
    # Heavily reward profile 0 (sensitive) in a specific context
    for _ in range(30):
        bandit.update(10.0, [0.5], [30.0], 0, 5.0)
        bandit.update(10.0, [0.5], [30.0], 1, -2.0)  # penalize default
    # With enough data and low epsilon, should prefer profile 0
    selections = [bandit.select_profile(10.0, [0.5], [30.0]) for _ in range(20)]
    profile_0_count = sum(1 for s in selections if s == ENGAGEMENT_PROFILES[0])
    assert profile_0_count > 5, "Bandit should learn to prefer rewarded profile"


def test_scheduler_bandit_default_matches_sm2():
    profile = DEFAULT_SM2_PROFILE
    init_ef, min_ef, ef_coeffs, miscon_penalty, reset_interval = profile
    assert init_ef == 2.5
    assert min_ef == 1.3
    assert ef_coeffs == (0.1, 0.08, 0.02)
    assert miscon_penalty == 0.15
    assert reset_interval == 1.0


def test_scheduler_bandit_learns_aggressive():
    bandit = SchedulerBandit()
    # Reward aggressive profile (index 1) heavily
    for _ in range(30):
        bandit.update([0.3], [1.5], 3, 10, 1, 5.0)   # aggressive rewarded
        bandit.update([0.3], [1.5], 3, 10, 0, -2.0)   # standard penalized
    selections = [bandit.select_profile([0.3], [1.5], 3, 10) for _ in range(20)]
    aggressive_count = sum(1 for s in selections if s == SM2_PROFILES[1])
    assert aggressive_count > 5, "Bandit should learn to prefer aggressive profile"


def test_retest_multiplier_adapts():
    bandit = DifficultyBandit()
    # Reward multiplier 0.65 heavily at a specific context
    for _ in range(30):
        bandit.update_retest(1.0, 0.0, 0, 0.65, 5.0)
        bandit.update_retest(1.0, 0.0, 0, 0.57, -1.0)
    # Should prefer 0.65 now
    bandit.total_updates = 300  # lower epsilon
    selections = [bandit.select_retest_multiplier(1.0, 0.0, 0) for _ in range(20)]
    count_065 = sum(1 for s in selections if s == 0.65)
    assert count_065 > 10, "Bandit should learn to prefer rewarded multiplier"


def test_strategy_exclusion_adaptive():
    bandit = StrategyBandit()
    # Make 'analogy' perform terribly
    for _ in range(20):
        bandit.update("analogy", 0.1)
        bandit.update("socratic", 0.8)
        bandit.update("worked_examples", 0.7)
    excluded = bandit.get_exclusion_set()
    assert "analogy" in excluded, "analogy should be excluded with low scores"
    assert "socratic" not in excluded, "socratic should not be excluded with high scores"


def test_reward_config_dataclass():
    config = RewardConfig()
    assert config.mastery == 10.0
    assert config.test_pass_mult == 5.0
    assert config.test_fail == -1.0
    assert config.misconception == -2.0
    assert config.resolved == 3.0
    assert config.step_penalty == -0.5


def test_hyperconfig_experience_scheduling():
    new_learner = RLHyperConfig.for_experience(2)
    assert new_learner.alpha == 0.2
    assert new_learner.epsilon == 0.3

    mid_learner = RLHyperConfig.for_experience(10)
    assert mid_learner.alpha == 0.1
    assert mid_learner.epsilon == 0.15

    expert = RLHyperConfig.for_experience(30)
    assert expert.alpha == 0.05
    assert expert.epsilon == 0.05


def test_rl_engine_5_layers_serialization():
    engine = RLEngine()
    engine.strategy_bandit.update("socratic", 0.8)
    engine.difficulty_bandit.update(1.0, 0.0, 0, 2, 0.7, 5.0)
    engine.engagement_bandit.update(10.0, [0.5], [30.0], 1, 3.0)
    engine.scheduler_bandit.update([0.7], [2.5], 0, 5, 0, 4.0)
    engine.action_q.update("test_state", "teach", 3.0, "next_state")

    data = engine.to_dict()
    restored = RLEngine.from_dict(data)

    assert restored.strategy_bandit.arms["socratic"][0] > 1.0
    assert restored.difficulty_bandit.total_updates == 1
    assert restored.engagement_bandit.total_updates == 1
    assert restored.scheduler_bandit.total_updates == 1
    assert restored.action_q.total_updates == 1


def test_rl_engine_policy_stats_includes_all():
    engine = RLEngine()
    stats = engine.get_policy_stats()
    assert "strategy_bandit" in stats
    assert "difficulty_bandit" in stats
    assert "action_q" in stats
    assert "engagement_bandit" in stats
    assert "scheduler_bandit" in stats


async def test_dynamic_career_role_generation(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Remove the static quant role to prove dynamic generation works
    from backend.services.career_service import career_service
    original_role = career_service.roles.pop("quantitative_analyst", None)

    try:
        # Verify it's gone
        roles_res = await client.get("/api/v1/career/roles")
        role_ids = [r["id"] for r in roles_res.json()]
        assert "quantitative_analyst" not in role_ids

        # Generate it dynamically
        gen_res = await client.post(
            "/api/v1/career/generate-role",
            json={"role_description": "quantitative analyst", "level": "mid"},
            headers=headers,
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()

        role = gen_data["role"]
        assert role["id"] == "quantitative_analyst"
        assert role["title"] == "Junior Quantitative Analyst"
        assert len(role["required_skills"]) == 4

        # Mapping should show full coverage (mock uses existing concepts)
        mapping = gen_data["mapping"]
        assert mapping["concepts_unmapped"] == 0
        assert mapping["coverage_ratio"] == 1.0

        # Now it should appear in roles list
        roles_res2 = await client.get("/api/v1/career/roles")
        role_ids2 = [r["id"] for r in roles_res2.json()]
        assert "quantitative_analyst" in role_ids2

        # Set as career target and check readiness
        await client.put(
            f"/api/v1/learner/{learner_id}/career-target",
            json={"role_ids": ["quantitative_analyst"]},
            headers=headers,
        )

        readiness_res = await client.get(
            f"/api/v1/career/readiness/{learner_id}/quantitative_analyst",
            headers=headers,
        )
        assert readiness_res.status_code == 200
        readiness = readiness_res.json()["readiness"]
        assert readiness["overall_score"] == 0.0
        assert len(readiness["gaps"]) == 4

        # Weights should sum to 1.0
        total_weight = sum(s["weight"] for s in readiness["skill_breakdown"])
        assert abs(total_weight - 1.0) < 0.01

    finally:
        if original_role:
            career_service.roles["quantitative_analyst"] = original_role


async def test_generic_role_generation(client):
    token, _ = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    gen_res = await client.post(
        "/api/v1/career/generate-role",
        json={"role_description": "backend web developer", "level": "entry"},
        headers=headers,
    )
    assert gen_res.status_code == 200
    role = gen_res.json()["role"]
    assert role["id"] == "generated_role"
    assert len(role["required_skills"]) >= 2
