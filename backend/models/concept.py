from pydantic import BaseModel, Field


class TransferEdge(BaseModel):
    target: str
    strength: float = Field(ge=0.0, le=1.0)
    type: str  # "analogous" | "prerequisite" | "reinforcing"
    description: str


class Misconception(BaseModel):
    id: str
    description: str
    indicators: list[str]
    remediation_strategy: str
    example_trigger: str


class MasteryCriteria(BaseModel):
    transfer_tests_required: int = 2
    minimum_score: float = 0.7
    explanation_required: bool = True
    time_decay_days: int = 30


class Concept(BaseModel):
    id: str
    name: str
    domain: str
    description: str
    difficulty_tier: int = Field(ge=1, le=5)
    prerequisites: list[str] = []
    transfers_to: list[TransferEdge] = []
    common_misconceptions: list[Misconception] = []
    mastery_criteria: MasteryCriteria = MasteryCriteria()
    teaching_contexts: list[str] = []
    test_contexts: list[str] = []
    tags: list[str] = []
    base_hours: float = 2.0
