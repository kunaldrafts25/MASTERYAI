# backward compat — diagnostic merged into examiner agent
from backend.agents.examiner import examiner_agent as diagnostic_agent  # noqa: F401
from backend.agents.examiner import ExaminerAgent as DiagnosticAgent  # noqa: F401

__all__ = ["diagnostic_agent", "DiagnosticAgent"]
