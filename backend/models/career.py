from datetime import datetime
from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    name: str
    concept_ids: list[str]
    minimum_mastery: float = 0.7
    weight: float = Field(ge=0.0, le=1.0)


class CareerRole(BaseModel):
    id: str
    title: str
    description: str
    level: str  # entry | mid | senior
    required_skills: list[SkillRequirement]
    nice_to_have_skills: list[SkillRequirement] = []
    market_demand: str = "medium"  # high | medium | low
    salary_range: dict = {}
    growth_trend: str = "stable"  # growing | stable | declining
    related_roles: list[str] = []


class SkillGap(BaseModel):
    skill_name: str
    current_mastery: float
    required_mastery: float
    missing_concepts: list[str]
    estimated_hours: float


class CareerReadiness(BaseModel):
    role_id: str
    role_title: str
    overall_score: float = 0.0
    skill_breakdown: list[dict] = []
    gaps: list[SkillGap] = []
    estimated_hours_to_ready: float = 0.0
    recommended_next: str | None = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


