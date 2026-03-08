# backward compat — career_mapper merged into curriculum agent
from backend.agents.curriculum import curriculum_agent as career_mapper_agent  # noqa: F401

__all__ = ["career_mapper_agent"]
