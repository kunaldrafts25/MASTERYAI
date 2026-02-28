from datetime import datetime
from pydantic import BaseModel, Field


class RubricScore(BaseModel):
    criterion: str
    score: int
    max_score: int = 10
    evidence: str = ""


class TestResult(BaseModel):
    test_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: str
    difficulty_tier: int = 2
    score: float = Field(ge=0.0, le=1.0)
    misconceptions_detected: list[str] = []
    rubric_scores: list[RubricScore] = []
    learner_response_summary: str = ""
    evaluator_reasoning: str = ""
    confidence_at_time: float = 0.0


class ConceptMastery(BaseModel):
    concept_id: str
    status: str = "unknown"  # unknown | introduced | practicing | testing | mastered | decayed
    mastery_score: float = Field(default=0.0, ge=0.0, le=1.0)
    self_reported_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    calibration_gap: float = 0.0
    misconceptions_active: list[str] = []
    misconceptions_resolved: list[str] = []
    transfer_tests: list[TestResult] = []
    teaching_strategies_tried: dict[str, float] = {}
    best_strategy: str | None = None
    last_validated: datetime | None = None
    contexts_encountered: list[str] = []
    introduced_at: datetime | None = None
    mastered_at: datetime | None = None


class LearningProfile(BaseModel):
    overall_velocity: float = 1.0
    domain_velocities: dict[str, float] = {}
    preferred_strategy: str | None = None
    calibration_trend: str = "unknown"  # improving | stable | overconfident | unknown
    engagement_pattern: str = "unknown"
    total_concepts_mastered: int = 0
    total_misconceptions_resolved: int = 0
    total_sessions: int = 0
    total_hours: float = 0.0
    strengths: list[str] = []
    weaknesses: list[str] = []


class LearnerState(BaseModel):
    learner_id: str
    name: str = ""
    experience_level: str = "beginner"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    concept_states: dict[str, ConceptMastery] = {}
    learning_profile: LearningProfile = LearningProfile()
    career_targets: list[str] = []
    sessions: list[str] = []  # session IDs
    rl_policy: dict = {}  # serialized RLEngine state
    review_queue: list[dict] = []  # serialized ReviewItems for spaced repetition
