import os

os.environ["DATABASE_URL"] = "sqlite:///test_masteryai.db"
os.environ["SQLITE_PATH"] = "test_masteryai.db"
import pytest

from backend.config import settings
settings.database_url = "sqlite:///test_masteryai.db"
settings.sqlite_path = "test_masteryai.db"

from backend.services.learner_store import learner_store
learner_store.db_path = "test_masteryai.db"

from backend.services.llm_client import llm_client
llm_client._client = None  # reset cached client


# ---------------------------------------------------------------------------
# Mock LLM for non-live tests — returns valid JSON responses so integration
# tests can exercise the full orchestration flow without real Bedrock access.
# ---------------------------------------------------------------------------

async def _mock_generate(system: str, prompt: str) -> dict:
    """Route mock responses by identifying the caller from its system prompt.

    Priority: system-prompt identification > content pattern matching.
    """
    sys_lower = system.lower()
    prompt_lower = prompt.lower()
    import re

    # ==================================================================
    # 1. ORCHESTRATOR — returns tool selection JSON
    # ==================================================================
    if "orchestrator of masteryai" in sys_lower:
        concept_match = re.search(r"current concept:.*?\(([^)]+)\)", prompt)
        concept_id = concept_match.group(1) if concept_match else "python.variables"

        # Chat messages take priority over UI state
        if "chat_message" in prompt_lower:
            return {"tool": "ask_learner", "args": {"question": "Great question! Let me explain differently.", "question_type": "chat"}, "reasoning": "Chat response.", "respond_to_learner": True}
        if "trigger: session_start" in prompt_lower:
            return {"tool": "teach", "args": {"concept_id": concept_id}, "reasoning": "Session start — teach.", "respond_to_learner": True}
        if "ui state: teaching" in prompt_lower or "ui state: reteaching" in prompt_lower:
            return {"tool": "generate_practice", "args": {"concept_id": concept_id}, "reasoning": "Generate practice.", "respond_to_learner": True}
        if "ui state: practicing" in prompt_lower:
            return {"tool": "ask_learner", "args": {"question": "Rate your confidence 1-10.", "question_type": "self_assess"}, "reasoning": "Ask self-assessment.", "respond_to_learner": True}
        if "ui state: self_assessing" in prompt_lower:
            return {"tool": "generate_test", "args": {"concept_id": concept_id, "difficulty": 2}, "reasoning": "Generate test.", "respond_to_learner": True}
        if "ui state: testing" in prompt_lower or "ui state: retesting" in prompt_lower:
            return {"tool": "evaluate_response", "args": {"response": "answer"}, "reasoning": "Evaluate.", "respond_to_learner": True}
        return {"tool": "teach", "args": {"concept_id": concept_id}, "reasoning": "Default teach.", "respond_to_learner": True}

    # ==================================================================
    # 2. CONCEPT GENERATOR — curriculum designer
    # ==================================================================
    if "curriculum designer" in sys_lower:
        domain = "python"
        if "machine learning" in prompt_lower:
            domain = "ml"
        elif "data structure" in prompt_lower:
            domain = "ds"
        elif "quant" in prompt_lower:
            domain = "quant"

        def _concept(suffix, tier, prereqs):
            return {
                "id": f"{domain}.{suffix}", "name": f"{domain.upper()} {suffix.title()}",
                "domain": domain, "description": f"{suffix.title()} concepts.", "difficulty_tier": tier,
                "prerequisites": [f"{domain}.{p}" for p in prereqs],
                "common_misconceptions": [{"id": f"{suffix}_misc", "description": f"Common {suffix} mistake", "indicators": ["sign1"], "remediation_strategy": "socratic", "example_trigger": "Explain"}],
                "teaching_contexts": ["Academic", "Tutorial"], "test_contexts": ["Industry", "Real-world"],
                "base_hours": float(tier), "tags": [domain, suffix],
            }
        return {
            "domain": domain, "domain_description": f"{domain} fundamentals",
            "concepts": [_concept("fundamentals", 1, []), _concept("intermediate", 2, ["fundamentals"]), _concept("advanced", 3, ["intermediate"])],
        }

    # ==================================================================
    # 3. CAREER ROLE GENERATOR — workforce analyst
    # ==================================================================
    if "workforce analyst" in sys_lower or "career role definition" in sys_lower:
        role_id, role_title = "generated_role", "Generated Role"
        if "quantitative analyst" in prompt_lower:
            role_id, role_title = "quantitative_analyst", "Junior Quantitative Analyst"
        # Use concept IDs that actually exist in the knowledge graph
        return {"role": {
            "id": role_id, "title": role_title, "description": "Dynamically generated role.", "level": "mid",
            "required_skills": [
                {"name": "Python Core", "concept_ids": ["python.variables", "python.functions", "python.scope"], "minimum_mastery": 0.7, "weight": 0.3},
                {"name": "Data Structures", "concept_ids": ["ds.arrays_lists", "ds.hash_maps", "ds.sorting"], "minimum_mastery": 0.7, "weight": 0.3},
                {"name": "Control Flow", "concept_ids": ["python.control_flow", "python.closures"], "minimum_mastery": 0.7, "weight": 0.2},
                {"name": "Advanced Python", "concept_ids": ["python.classes", "python.decorators"], "minimum_mastery": 0.7, "weight": 0.2},
            ],
            "nice_to_have_skills": [], "market_demand": "high",
            "salary_range": {"min": 80000, "max": 150000, "currency": "USD"},
            "growth_trend": "growing", "related_roles": ["data_scientist"],
        }}

    # ==================================================================
    # 4. TEACHER — teaching content or reflection
    # ==================================================================
    if "teaching_content" in sys_lower or "teach this concept" in sys_lower or "teach the concept" in sys_lower:
        return {
            "teaching_content": "Variables are named containers that store data in memory.",
            "check_question": "What happens when you assign x = 5 then x = 10?",
            "expected_check_answer": "x changes from 5 to 10.",
            "concepts_referenced": ["data_types"], "strategy_used": "analogy", "estimated_time_minutes": 3,
        }
    if "reflect" in sys_lower and "teaching" in sys_lower:
        return {"reflection": "Approach worked well.", "recommended_strategy": "socratic", "reasoning": "Deepen understanding.", "confidence": 0.8}

    # ==================================================================
    # 5. EXAMINER — validate, evaluate, generate test/practice/diagnostic
    # System prompts:
    #   evaluate_response: "You are evaluating a learner's response to a transfer test."
    #   generate_transfer_test: "You are an expert examiner validating deep understanding..."
    #   validate_test: "You are reviewing a test for quality..."
    #   generate_practice: "Generate practice problems..."
    #   diagnostic: "You are conducting a diagnostic..." / similar
    # ==================================================================
    if "evaluating" in sys_lower and "response" in sys_lower:
        return {
            "rubric_scores": [{"criterion": "Understanding", "score": 8, "evidence": "Good"}, {"criterion": "Application", "score": 9, "evidence": "Correct"}, {"criterion": "Edge cases", "score": 7, "evidence": "Partial"}],
            "total_score": 0.8, "misconceptions_detected": [], "understanding_level": "solid",
            "reasoning": "Clear understanding.", "recommended_focus": "Next concept.",
        }
    if "validate" in sys_lower or "review" in sys_lower and "test" in sys_lower:
        return {"is_valid": True, "issues": [], "quality_score": 0.9, "suggestion": "Good test."}
    if "examiner" in sys_lower or ("transfer" in sys_lower and "test" in sys_lower):
        return {
            "problem_statement": "Write code to update a nested config without overwriting siblings.",
            "context_description": "Web configuration management", "response_format": "Python function",
            "correct_approach": "Use dict.get() with defaults.", "misconception_traps": ["Overwrite dict"],
            "rubric": ["Key access (0.3)", "Preserve data (0.4)", "Edge cases (0.3)"],
            "follow_up_if_correct": "Handle deeply nested?", "estimated_time_minutes": 5, "difficulty_tier": 2,
        }
    if "practice" in sys_lower or "practice" in prompt_lower and "problem" in prompt_lower:
        return {"problems": [{"problem_id": "p1", "problem_statement": "Store age and print it.", "context": "User profile", "difficulty": "familiar", "hints": ["Data type", "print()"], "expected_approach": "age = 25; print(age)"}]}
    if "diagnostic" in sys_lower and "question" in sys_lower:
        return {"question": "What happens when you assign a list to two variables?", "key_indicators": ["reference", "mutable"], "concept_id": "python.variables"}
    if "diagnostic" in sys_lower:
        return {"score": 0.7, "understanding": "partial", "notes": "Basic understanding."}

    # ==================================================================
    # 6. MOTIVATION — emotional analysis / intervention
    # ==================================================================
    if "emotional" in sys_lower or "engagement" in sys_lower or "motivation" in sys_lower:
        if "intervention" in sys_lower:
            return {"type": "encouragement", "message": "Keep going!", "action": None, "engagement_state": "neutral", "personalized": True}
        return {"state": "neutral", "confidence": 0.8, "reasoning": "Steady engagement.", "nuances": ["Consistent"], "recommended_tone": "encouraging"}

    # ==================================================================
    # 7. MEMORY — session summary / teaching reflection
    # ==================================================================
    if "summary" in sys_lower and ("session" in sys_lower or "journal" in sys_lower):
        return {"summary": "Learner demonstrated understanding.", "tags": ["progress"], "entry_type": "session_summary"}
    if "reflection" in sys_lower or "journal" in sys_lower:
        return {"reflection": "Effective approach.", "tags": ["effective"], "next_suggestion": "Try Socratic next."}

    # ==================================================================
    # 8. PROACTIVE — career suggestion / session opener
    # ==================================================================
    if "career" in sys_lower and "direction" in sys_lower:
        return {"suggestion": "Explore backend dev.", "recommended_role": "Backend Developer", "reasoning": "Strong Python.", "strongest_domain": "python", "growth_area": "databases"}
    if "greeting" in sys_lower or "opener" in sys_lower or "welcome" in sys_lower:
        return {"greeting": "Welcome back!", "suggested_focus": "Continue where you left off."}

    # ==================================================================
    # 9. DELIBERATION — conflict resolution
    # ==================================================================
    if "conflict" in sys_lower or "deliberat" in sys_lower:
        return {"reasoning": "Curriculum recommendation is best.", "recommendation": "teach"}

    # ==================================================================
    # 10. FALLBACK — content-based pattern matching
    # ==================================================================
    combined = sys_lower + prompt_lower
    if "teaching_content" in combined:
        return {"teaching_content": "Explanation of the concept.", "check_question": "Test question?", "expected_check_answer": "Answer.", "strategy_used": "analogy", "estimated_time_minutes": 3}
    if "evaluate" in combined and "score" in combined:
        return {"rubric_scores": [{"criterion": "Overall", "score": 8, "evidence": "Good"}], "total_score": 0.8, "misconceptions_detected": [], "understanding_level": "solid", "reasoning": "Good.", "recommended_focus": "Next."}
    if "transfer" in combined and "test" in combined:
        return {"problem_statement": "Test problem.", "context_description": "Test context", "correct_approach": "Solution.", "difficulty_tier": 2}
    if "practice" in combined:
        return {"problems": [{"problem_id": "p1", "problem_statement": "Practice.", "context": "Context", "difficulty": "familiar", "hints": ["Hint"], "expected_approach": "Answer"}]}

    # Ultimate fallback
    return {"teaching_content": "Explanation.", "message": "OK.", "score": 0.75, "action": "continue"}


# Patch the LLM client for all non-live tests
_original_real_generate = llm_client._real_generate
llm_client._real_generate = _mock_generate

from backend.services.knowledge_graph import knowledge_graph
from backend.services.career_service import career_service
knowledge_graph.load()
career_service.load()

# Raise rate limit for tests — integration tests make many requests per test
import backend.middleware as _mw
_mw.RATE_LIMIT = 10000


from backend.agents.message_bus import message_bus
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def live_client():
    """Client for live tests — restores real Bedrock LLM."""
    llm_client._real_generate = _original_real_generate
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    llm_client._real_generate = _mock_generate


@pytest.fixture(autouse=True)
def reset_db():
    learner_store._ensure_tables()
    yield
    message_bus._messages.clear()
    # cleanup motivation agent session signals
    from backend.agents.motivation import motivation_agent
    motivation_agent._sessions.clear()
    # clear LLM cache to prevent cross-test pollution
    from backend.services.llm_client import llm_client
    llm_client._cache = type(llm_client._cache)(llm_client._cache._maxsize)
    # clear orchestrator active sessions
    from backend.agents.orchestrator import orchestrator
    orchestrator.active_sessions.clear()
    # reset rate limiter to prevent 429s across tests
    from backend.main import app
    for middleware in app.user_middleware:
        pass  # starlette stores middleware differently
    # Direct reset: clear the rate limiter state on the app
    _reset_rate_limiter()
    # reload career roles to reset any dynamically added roles
    career_service.load()
    try:
        os.remove("test_masteryai.db")
    except (PermissionError, FileNotFoundError):
        pass


def _reset_rate_limiter():
    from backend.middleware import RateLimitMiddleware
    from backend.main import app
    # Walk the middleware stack to find and reset the rate limiter
    middleware = app.middleware_stack
    while middleware is not None:
        if isinstance(middleware, RateLimitMiddleware):
            middleware.requests.clear()
            return
        middleware = getattr(middleware, "app", None)
