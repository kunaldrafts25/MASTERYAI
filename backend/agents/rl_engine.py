# RL engine - 5 layers that replace hardcoded rules with learned policies

import random
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# dedicated RNG for RL decisions — keeps exploration reproducible
_rl_rng = random.Random(42)

ALL_STRATEGIES = ["socratic", "worked_examples", "analogy", "debugging_exercise", "explain_back"]
DIFFICULTY_LEVELS = [1, 2, 3]
MASTERY_THRESHOLDS = [0.55, 0.6, 0.65, 0.7, 0.75, 0.8]

# Q-Learning actions
QL_ACTIONS = ["teach", "practice", "test", "reteach", "skip_ahead", "ask_learner"]

# Retest multiplier options for DifficultyBandit
RETEST_MULTIPLIERS = [0.45, 0.50, 0.57, 0.65, 0.70]


# --- reward & hyperparameter config ---

@dataclass
class RewardConfig:
    mastery: float = 10.0
    test_pass_mult: float = 5.0
    test_fail: float = -1.0
    misconception: float = -2.0
    resolved: float = 3.0
    step_penalty: float = -0.5


@dataclass
class RLHyperConfig:
    alpha: float = 0.1
    gamma: float = 0.9
    epsilon: float = 0.15

    @classmethod
    def for_experience(cls, concepts_mastered: int) -> "RLHyperConfig":
        if concepts_mastered < 5:
            return cls(alpha=0.2, gamma=0.9, epsilon=0.3)
        elif concepts_mastered < 20:
            return cls(alpha=0.1, gamma=0.9, epsilon=0.15)
        else:
            return cls(alpha=0.05, gamma=0.9, epsilon=0.05)


# Module-level constants — aliases to RewardConfig defaults for backward compat
_REWARDS = RewardConfig()
REWARD_MASTERY = _REWARDS.mastery
REWARD_TEST_PASS_MULT = _REWARDS.test_pass_mult
REWARD_TEST_FAIL = _REWARDS.test_fail
REWARD_MISCONCEPTION = _REWARDS.misconception
REWARD_RESOLVED = _REWARDS.resolved
REWARD_STEP = _REWARDS.step_penalty


# --- layer 1: strategy bandit ---

class StrategyBandit:

    def __init__(self):
        # Beta distribution params: alpha=successes+1, beta=failures+1
        self.arms: dict[str, list[float]] = {
            s: [1.0, 1.0] for s in ALL_STRATEGIES
        }

    def select(self, exclude: list[str] | None = None) -> str:
        # thompson sample from Beta(a,b) for each arm
        best_strategy = ALL_STRATEGIES[0]
        best_sample = -1.0
        for strategy, (alpha, beta) in self.arms.items():
            if exclude and strategy in exclude:
                continue
            sample = random.betavariate(alpha, beta)
            if sample > best_sample:
                best_sample = sample
                best_strategy = strategy
        return best_strategy

    def get_best(self) -> str:
        # pure exploitation - highest expected value
        best_strategy = ALL_STRATEGIES[0]
        best_ev = -1.0
        for strategy, (alpha, beta) in self.arms.items():
            ev = alpha / (alpha + beta)
            if ev > best_ev:
                best_ev = ev
                best_strategy = strategy
        return best_strategy

    def update(self, strategy: str, score: float):
        # alpha += score, beta += (1 - score)
        if strategy not in self.arms:
            self.arms[strategy] = [1.0, 1.0]
        self.arms[strategy][0] += score
        self.arms[strategy][1] += (1.0 - score)

    def get_exclusion_set(self) -> list[str]:
        # exclude strategies >1 std dev below mean
        evs = []
        for s, (a, b) in self.arms.items():
            if a + b > 3:
                evs.append((s, a / (a + b)))
        if len(evs) < 2:
            return []
        mean_ev = sum(ev for _, ev in evs) / len(evs)
        std_ev = (sum((ev - mean_ev) ** 2 for _, ev in evs) / len(evs)) ** 0.5
        threshold = max(0.15, mean_ev - std_ev)
        return [s for s, ev in evs if ev < threshold]

    def get_stats(self) -> dict:
        return {
            s: {"alpha": a, "beta": b, "expected": round(a / (a + b), 3)}
            for s, (a, b) in self.arms.items()
        }

    def to_dict(self) -> dict:
        return {"arms": {s: [a, b] for s, (a, b) in self.arms.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> "StrategyBandit":
        bandit = cls()
        for s, (a, b) in data.get("arms", {}).items():
            bandit.arms[s] = [a, b]
        return bandit


# --- layer 2: difficulty bandit ---

def _discretize_velocity(velocity: float) -> str:
    if velocity < 0.7:
        return "slow"
    elif velocity > 1.3:
        return "fast"
    return "normal"


def _discretize_calibration(cal_gap: float) -> str:
    if cal_gap > 0.15:
        return "over"
    elif cal_gap < -0.15:
        return "under"
    return "calibrated"


def _discretize_misconceptions(count: int) -> str:
    if count == 0:
        return "none"
    elif count <= 2:
        return "some"
    return "many"


class DifficultyBandit:

    def __init__(self):
        # {context_key: {action_key: [total_reward, count]}}
        self.difficulty_table: dict[str, dict[int, list[float]]] = {}
        self.threshold_table: dict[str, dict[float, list[float]]] = {}
        self.retest_table: dict[str, dict[float, list[float]]] = {}
        self.total_updates: int = 0

    @property
    def epsilon(self) -> float:
        return max(0.05, 0.2 - (self.total_updates / 200) * 0.15)

    def _context_key(self, velocity: float, cal_gap: float, miscon_count: int) -> str:
        return f"{_discretize_velocity(velocity)}_{_discretize_calibration(cal_gap)}_{_discretize_misconceptions(miscon_count)}"

    def select_difficulty(self, velocity: float, cal_gap: float, miscon_count: int) -> int:
        ctx = self._context_key(velocity, cal_gap, miscon_count)
        if random.random() < self.epsilon:
            return random.choice(DIFFICULTY_LEVELS)
        table = self.difficulty_table.get(ctx, {})
        if not table:
            return 2  # default
        best_d = 2
        best_avg = -999.0
        for d, (total, count) in table.items():
            avg = total / max(count, 1)
            if avg > best_avg:
                best_avg = avg
                best_d = d
        return best_d

    def select_threshold(self, velocity: float, cal_gap: float, miscon_count: int) -> float:
        ctx = self._context_key(velocity, cal_gap, miscon_count)
        if random.random() < self.epsilon:
            return random.choice(MASTERY_THRESHOLDS)
        table = self.threshold_table.get(ctx, {})
        if not table:
            return 0.7  # default
        best_t = 0.7
        best_avg = -999.0
        for t, (total, count) in table.items():
            avg = total / max(count, 1)
            if avg > best_avg:
                best_avg = avg
                best_t = t
        return best_t

    def select_retest_multiplier(self, velocity: float, cal_gap: float, miscon_count: int) -> float:
        ctx = self._context_key(velocity, cal_gap, miscon_count)
        if _rl_rng.random() < self.epsilon:
            return _rl_rng.choice(RETEST_MULTIPLIERS)
        table = self.retest_table.get(ctx, {})
        if not table:
            return 0.57  # default
        best_m = 0.57
        best_avg = -999.0
        for m, (total, count) in table.items():
            avg = total / max(count, 1)
            if avg > best_avg:
                best_avg = avg
                best_m = m
        return best_m

    def update_retest(self, velocity: float, cal_gap: float, miscon_count: int,
                      multiplier: float, reward: float):
        ctx = self._context_key(velocity, cal_gap, miscon_count)
        if ctx not in self.retest_table:
            self.retest_table[ctx] = {}
        if multiplier not in self.retest_table[ctx]:
            self.retest_table[ctx][multiplier] = [0.0, 0]
        self.retest_table[ctx][multiplier][0] += reward
        self.retest_table[ctx][multiplier][1] += 1

    def update(self, velocity: float, cal_gap: float, miscon_count: int,
               difficulty: int, threshold: float, reward: float):
        ctx = self._context_key(velocity, cal_gap, miscon_count)
        self.total_updates += 1

        if ctx not in self.difficulty_table:
            self.difficulty_table[ctx] = {}
        if difficulty not in self.difficulty_table[ctx]:
            self.difficulty_table[ctx][difficulty] = [0.0, 0]
        self.difficulty_table[ctx][difficulty][0] += reward
        self.difficulty_table[ctx][difficulty][1] += 1

        if ctx not in self.threshold_table:
            self.threshold_table[ctx] = {}
        if threshold not in self.threshold_table[ctx]:
            self.threshold_table[ctx][threshold] = [0.0, 0]
        self.threshold_table[ctx][threshold][0] += reward
        self.threshold_table[ctx][threshold][1] += 1

    def get_stats(self) -> dict:
        return {
            "epsilon": round(self.epsilon, 3),
            "total_updates": self.total_updates,
            "contexts_seen": len(self.difficulty_table),
        }

    def to_dict(self) -> dict:
        return {
            "difficulty_table": {
                ctx: {str(d): v for d, v in actions.items()}
                for ctx, actions in self.difficulty_table.items()
            },
            "threshold_table": {
                ctx: {str(t): v for t, v in actions.items()}
                for ctx, actions in self.threshold_table.items()
            },
            "retest_table": {
                ctx: {str(m): v for m, v in actions.items()}
                for ctx, actions in self.retest_table.items()
            },
            "total_updates": self.total_updates,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DifficultyBandit":
        bandit = cls()
        bandit.total_updates = data.get("total_updates", 0)
        for ctx, actions in data.get("difficulty_table", {}).items():
            bandit.difficulty_table[ctx] = {int(d): v for d, v in actions.items()}
        for ctx, actions in data.get("threshold_table", {}).items():
            bandit.threshold_table[ctx] = {float(t): v for t, v in actions.items()}
        for ctx, actions in data.get("retest_table", {}).items():
            bandit.retest_table[ctx] = {float(m): v for m, v in actions.items()}
        return bandit


# --- layer 3: action q-learner ---

def _bucket_test_count(count: int) -> str:
    if count == 0:
        return "0"
    elif count <= 2:
        return "1-2"
    return "3+"


def _bucket_fail_streak(streak: int) -> str:
    if streak == 0:
        return "0"
    elif streak == 1:
        return "1"
    return "2+"


def _bucket_score_trend(scores: list[float]) -> str:
    if len(scores) < 2:
        return "none"
    recent = scores[-3:]
    if len(recent) >= 2 and recent[-1] > recent[0] + 0.1:
        return "improving"
    elif len(recent) >= 2 and recent[-1] < recent[0] - 0.1:
        return "declining"
    return "stable"


class ActionQLearner:

    def __init__(self, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.15):
        self.q_table: dict[str, dict[str, float]] = {}
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.total_updates: int = 0

    def _state_key(self, concept_status: str, test_count: int,
                   fail_streak: int, recent_scores: list[float],
                   engagement: str = "neutral") -> str:
        return (
            f"{concept_status}|"
            f"{_bucket_test_count(test_count)}|"
            f"{_bucket_fail_streak(fail_streak)}|"
            f"{_bucket_score_trend(recent_scores)}|"
            f"{engagement}"
        )

    def select_action(self, concept_status: str, test_count: int,
                      fail_streak: int, recent_scores: list[float],
                      engagement: str = "neutral") -> str:
        state = self._state_key(concept_status, test_count, fail_streak, recent_scores, engagement)

        # epsilon-greedy
        if random.random() < self.epsilon:
            return random.choice(QL_ACTIONS)

        q_values = self.q_table.get(state, {})
        if not q_values:
            # cold start: return sensible default based on concept status
            defaults = {
                "unknown": "teach",
                "introduced": "practice",
                "practicing": "test",
                "testing": "test",
                "mastered": "skip_ahead",
                "decayed": "test",
            }
            return defaults.get(concept_status, "teach")

        return max(q_values, key=q_values.get)

    def update(self, state_key: str, action: str, reward: float, next_state_key: str):
        # Q(s,a) += alpha * (reward + gamma * max Q(s') - Q(s,a))
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        if action not in self.q_table[state_key]:
            self.q_table[state_key][action] = 0.0

        current_q = self.q_table[state_key][action]
        next_q_values = self.q_table.get(next_state_key, {})
        max_next_q = max(next_q_values.values()) if next_q_values else 0.0

        self.q_table[state_key][action] = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )
        self.total_updates += 1

    def get_state_key(self, concept_status: str, test_count: int,
                      fail_streak: int, recent_scores: list[float],
                      engagement: str = "neutral") -> str:
        return self._state_key(concept_status, test_count, fail_streak, recent_scores, engagement)

    def get_stats(self) -> dict:
        return {
            "states_explored": len(self.q_table),
            "total_updates": self.total_updates,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
        }

    def to_dict(self) -> dict:
        return {
            "q_table": self.q_table,
            "total_updates": self.total_updates,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActionQLearner":
        learner = cls(
            alpha=data.get("alpha", 0.1),
            gamma=data.get("gamma", 0.9),
            epsilon=data.get("epsilon", 0.15),
        )
        learner.q_table = data.get("q_table", {})
        learner.total_updates = data.get("total_updates", 0)
        return learner


# --- layer 4: engagement bandit ---

# Each profile is: (frustration_failures, boredom_speed_s, flow_range, session_max_min, decline_threshold, short_answer_chars)
ENGAGEMENT_PROFILES = [
    (2, 10, (20, 120), 45, -0.10, 15),   # sensitive
    (3, 15, (30, 180), 60, -0.15, 20),   # default (matches original hardcoded)
    (4, 20, (30, 240), 90, -0.20, 10),   # tolerant
    (3, 12, (25, 150), 50, -0.12, 18),   # moderate-sensitive
    (4, 18, (35, 200), 75, -0.18, 15),   # moderate-tolerant
]

DEFAULT_ENGAGEMENT_PROFILE = ENGAGEMENT_PROFILES[1]  # matches original hardcoded values


def _bucket_session_duration(minutes: float) -> str:
    if minutes < 15:
        return "short"
    elif minutes < 45:
        return "medium"
    return "long"


def _bucket_performance(scores: list[float]) -> str:
    if not scores:
        return "unknown"
    avg = sum(scores[-5:]) / len(scores[-5:])
    if avg < 0.4:
        return "low"
    elif avg > 0.7:
        return "high"
    return "medium"


def _bucket_pace(response_times: list[float]) -> str:
    if not response_times:
        return "unknown"
    avg = sum(response_times[-5:]) / len(response_times[-5:])
    if avg < 20:
        return "fast"
    elif avg > 120:
        return "slow"
    return "normal"


class EngagementBandit:

    def __init__(self):
        self.profile_table: dict[str, dict[int, list[float]]] = {}
        self.total_updates: int = 0

    @property
    def epsilon(self) -> float:
        return max(0.05, 0.2 - (self.total_updates / 200) * 0.15)

    def _context_key(self, session_minutes: float, scores: list[float],
                     response_times: list[float]) -> str:
        return (
            f"{_bucket_session_duration(session_minutes)}_"
            f"{_bucket_performance(scores)}_"
            f"{_bucket_pace(response_times)}"
        )

    def select_profile(self, session_minutes: float = 0, scores: list[float] | None = None,
                       response_times: list[float] | None = None) -> tuple:
        ctx = self._context_key(session_minutes, scores or [], response_times or [])
        if _rl_rng.random() < self.epsilon:
            idx = _rl_rng.randrange(len(ENGAGEMENT_PROFILES))
            return ENGAGEMENT_PROFILES[idx]
        table = self.profile_table.get(ctx, {})
        if not table:
            return DEFAULT_ENGAGEMENT_PROFILE
        best_idx = 1  # default profile index
        best_avg = -999.0
        for idx, (total, count) in table.items():
            avg = total / max(count, 1)
            if avg > best_avg:
                best_avg = avg
                best_idx = idx
        if 0 <= best_idx < len(ENGAGEMENT_PROFILES):
            return ENGAGEMENT_PROFILES[best_idx]
        return DEFAULT_ENGAGEMENT_PROFILE

    def update(self, session_minutes: float, scores: list[float],
               response_times: list[float], profile_idx: int, reward: float):
        ctx = self._context_key(session_minutes, scores, response_times)
        self.total_updates += 1
        if ctx not in self.profile_table:
            self.profile_table[ctx] = {}
        if profile_idx not in self.profile_table[ctx]:
            self.profile_table[ctx][profile_idx] = [0.0, 0]
        self.profile_table[ctx][profile_idx][0] += reward
        self.profile_table[ctx][profile_idx][1] += 1

    def get_stats(self) -> dict:
        return {
            "epsilon": round(self.epsilon, 3),
            "total_updates": self.total_updates,
            "contexts_seen": len(self.profile_table),
        }

    def to_dict(self) -> dict:
        return {
            "profile_table": {
                ctx: {str(idx): v for idx, v in actions.items()}
                for ctx, actions in self.profile_table.items()
            },
            "total_updates": self.total_updates,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EngagementBandit":
        bandit = cls()
        bandit.total_updates = data.get("total_updates", 0)
        for ctx, actions in data.get("profile_table", {}).items():
            bandit.profile_table[ctx] = {int(idx): v for idx, v in actions.items()}
        return bandit


# --- layer 5: scheduler bandit ---

# Each profile: (init_ef, min_ef, ef_coefficients, miscon_penalty, reset_interval_days)
SM2_PROFILES = [
    (2.5, 1.3, (0.1, 0.08, 0.02), 0.15, 1.0),    # standard (matches original)
    (2.3, 1.2, (0.12, 0.10, 0.03), 0.20, 0.5),    # aggressive
    (2.7, 1.4, (0.08, 0.06, 0.01), 0.10, 1.5),    # gentle
    (2.5, 1.3, (0.1, 0.08, 0.02), 0.25, 1.0),     # high misconception penalty
    (2.4, 1.2, (0.11, 0.09, 0.025), 0.15, 0.75),   # moderate-aggressive
]

DEFAULT_SM2_PROFILE = SM2_PROFILES[0]


def _bucket_review_success(scores: list[float]) -> str:
    if not scores:
        return "unknown"
    avg = sum(scores) / len(scores)
    if avg < 0.5:
        return "low"
    elif avg > 0.8:
        return "high"
    return "medium"


def _bucket_easiness(efs: list[float]) -> str:
    if not efs:
        return "unknown"
    avg = sum(efs) / len(efs)
    if avg < 2.0:
        return "hard"
    elif avg > 2.8:
        return "easy"
    return "normal"


def _bucket_misconception_density(count: int, total: int) -> str:
    if total == 0:
        return "unknown"
    ratio = count / total
    if ratio == 0:
        return "none"
    elif ratio < 0.3:
        return "some"
    return "many"


class SchedulerBandit:

    def __init__(self):
        self.profile_table: dict[str, dict[int, list[float]]] = {}
        self.total_updates: int = 0

    @property
    def epsilon(self) -> float:
        return max(0.05, 0.2 - (self.total_updates / 200) * 0.15)

    def _context_key(self, review_scores: list[float], easiness_factors: list[float],
                     miscon_count: int, total_concepts: int) -> str:
        return (
            f"{_bucket_review_success(review_scores)}_"
            f"{_bucket_easiness(easiness_factors)}_"
            f"{_bucket_misconception_density(miscon_count, total_concepts)}"
        )

    def select_profile(self, review_scores: list[float] | None = None,
                       easiness_factors: list[float] | None = None,
                       miscon_count: int = 0, total_concepts: int = 0) -> tuple:
        ctx = self._context_key(
            review_scores or [], easiness_factors or [],
            miscon_count, total_concepts
        )
        if _rl_rng.random() < self.epsilon:
            idx = _rl_rng.randrange(len(SM2_PROFILES))
            return SM2_PROFILES[idx]
        table = self.profile_table.get(ctx, {})
        if not table:
            return DEFAULT_SM2_PROFILE
        best_idx = 0
        best_avg = -999.0
        for idx, (total, count) in table.items():
            avg = total / max(count, 1)
            if avg > best_avg:
                best_avg = avg
                best_idx = idx
        if 0 <= best_idx < len(SM2_PROFILES):
            return SM2_PROFILES[best_idx]
        return DEFAULT_SM2_PROFILE

    def update(self, review_scores: list[float], easiness_factors: list[float],
               miscon_count: int, total_concepts: int, profile_idx: int, reward: float):
        ctx = self._context_key(review_scores, easiness_factors, miscon_count, total_concepts)
        self.total_updates += 1
        if ctx not in self.profile_table:
            self.profile_table[ctx] = {}
        if profile_idx not in self.profile_table[ctx]:
            self.profile_table[ctx][profile_idx] = [0.0, 0]
        self.profile_table[ctx][profile_idx][0] += reward
        self.profile_table[ctx][profile_idx][1] += 1

    def get_stats(self) -> dict:
        return {
            "epsilon": round(self.epsilon, 3),
            "total_updates": self.total_updates,
            "contexts_seen": len(self.profile_table),
        }

    def to_dict(self) -> dict:
        return {
            "profile_table": {
                ctx: {str(idx): v for idx, v in actions.items()}
                for ctx, actions in self.profile_table.items()
            },
            "total_updates": self.total_updates,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SchedulerBandit":
        bandit = cls()
        bandit.total_updates = data.get("total_updates", 0)
        for ctx, actions in data.get("profile_table", {}).items():
            bandit.profile_table[ctx] = {int(idx): v for idx, v in actions.items()}
        return bandit


# --- top-level engine ---

class RLEngine:

    def __init__(self):
        self.strategy_bandit = StrategyBandit()
        self.difficulty_bandit = DifficultyBandit()
        self.action_q = ActionQLearner()
        self.engagement_bandit = EngagementBandit()
        self.scheduler_bandit = SchedulerBandit()

    # -- Strategy selection (Layer 1) --

    def select_strategy(self, exclude: list[str] | None = None) -> str:
        return self.strategy_bandit.select(exclude)

    def get_best_strategy(self) -> str:
        return self.strategy_bandit.get_best()

    def update_strategy(self, strategy: str, score: float):
        self.strategy_bandit.update(strategy, score)

    # -- Difficulty + threshold selection (Layer 2) --

    def select_difficulty(self, learner, concept_id: str) -> int:
        velocity = learner.learning_profile.overall_velocity
        cs = learner.concept_states.get(concept_id)
        cal_gap = cs.calibration_gap if cs else 0.0
        miscon_count = len(cs.misconceptions_active) if cs else 0
        return self.difficulty_bandit.select_difficulty(velocity, cal_gap, miscon_count)

    def select_mastery_threshold(self, learner, concept_id: str) -> float:
        velocity = learner.learning_profile.overall_velocity
        cs = learner.concept_states.get(concept_id)
        cal_gap = cs.calibration_gap if cs else 0.0
        miscon_count = len(cs.misconceptions_active) if cs else 0
        return self.difficulty_bandit.select_threshold(velocity, cal_gap, miscon_count)

    def update_difficulty(self, learner, concept_id: str,
                          difficulty: int, threshold: float, reward: float):
        velocity = learner.learning_profile.overall_velocity
        cs = learner.concept_states.get(concept_id)
        cal_gap = cs.calibration_gap if cs else 0.0
        miscon_count = len(cs.misconceptions_active) if cs else 0
        self.difficulty_bandit.update(velocity, cal_gap, miscon_count,
                                     difficulty, threshold, reward)

    # -- Action selection (Layer 3) --

    def select_next_action(self, learner, session, concept_id: str) -> str:
        cs = learner.concept_states.get(concept_id)
        status = cs.status if cs else "unknown"
        test_count = len(cs.transfer_tests) if cs else 0
        fail_streak = session.tests_failed
        recent_scores = [t.score for t in cs.transfer_tests[-5:]] if cs else []
        engagement = getattr(session, "engagement_state", "neutral")
        return self.action_q.select_action(status, test_count, fail_streak,
                                           recent_scores, engagement)

    def get_action_state_key(self, learner, session, concept_id: str) -> str:
        cs = learner.concept_states.get(concept_id)
        status = cs.status if cs else "unknown"
        test_count = len(cs.transfer_tests) if cs else 0
        fail_streak = session.tests_failed
        recent_scores = [t.score for t in cs.transfer_tests[-5:]] if cs else []
        engagement = getattr(session, "engagement_state", "neutral")
        return self.action_q.get_state_key(status, test_count, fail_streak,
                                           recent_scores, engagement)

    def update_action(self, prev_state_key: str, action: str,
                      reward: float, next_state_key: str):
        self.action_q.update(prev_state_key, action, reward, next_state_key)

    # -- Retest multiplier (Layer 2 extension) --

    def select_retest_multiplier(self, learner, concept_id: str) -> float:
        velocity = learner.learning_profile.overall_velocity
        cs = learner.concept_states.get(concept_id)
        cal_gap = cs.calibration_gap if cs else 0.0
        miscon_count = len(cs.misconceptions_active) if cs else 0
        return self.difficulty_bandit.select_retest_multiplier(velocity, cal_gap, miscon_count)

    # -- Engagement profile (Layer 4) --

    def select_engagement_profile(self, session_minutes: float = 0,
                                   scores: list[float] | None = None,
                                   response_times: list[float] | None = None) -> tuple:
        return self.engagement_bandit.select_profile(session_minutes, scores, response_times)

    # -- Scheduler profile (Layer 5) --

    def select_sm2_profile(self, learner) -> tuple:
        review_scores = []
        easiness_factors = []
        miscon_count = 0
        for item_data in learner.review_queue:
            review_scores.append(item_data.get("last_score", 0.0))
            easiness_factors.append(item_data.get("easiness_factor", 2.5))
        for cs in learner.concept_states.values():
            miscon_count += len(cs.misconceptions_active)
        total_concepts = len(learner.concept_states)
        return self.scheduler_bandit.select_profile(
            review_scores, easiness_factors, miscon_count, total_concepts
        )

    # -- Serialization --

    def to_dict(self) -> dict:
        return {
            "strategy_bandit": self.strategy_bandit.to_dict(),
            "difficulty_bandit": self.difficulty_bandit.to_dict(),
            "action_q": self.action_q.to_dict(),
            "engagement_bandit": self.engagement_bandit.to_dict(),
            "scheduler_bandit": self.scheduler_bandit.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RLEngine":
        engine = cls()
        if "strategy_bandit" in data:
            engine.strategy_bandit = StrategyBandit.from_dict(data["strategy_bandit"])
        if "difficulty_bandit" in data:
            engine.difficulty_bandit = DifficultyBandit.from_dict(data["difficulty_bandit"])
        if "action_q" in data:
            engine.action_q = ActionQLearner.from_dict(data["action_q"])
        if "engagement_bandit" in data:
            engine.engagement_bandit = EngagementBandit.from_dict(data["engagement_bandit"])
        if "scheduler_bandit" in data:
            engine.scheduler_bandit = SchedulerBandit.from_dict(data["scheduler_bandit"])
        return engine

    def get_policy_stats(self) -> dict:
        return {
            "strategy_bandit": self.strategy_bandit.get_stats(),
            "difficulty_bandit": self.difficulty_bandit.get_stats(),
            "action_q": self.action_q.get_stats(),
            "engagement_bandit": self.engagement_bandit.get_stats(),
            "scheduler_bandit": self.scheduler_bandit.get_stats(),
        }


# --- helper ---

def get_rl_engine(learner) -> RLEngine:
    if learner.rl_policy:
        try:
            return RLEngine.from_dict(learner.rl_policy)
        except Exception as e:
            logger.warning(f"Failed to load RL policy, creating fresh: {e}")
    return RLEngine()
