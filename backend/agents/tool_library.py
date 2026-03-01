# extended tool library — new pedagogical primitives for richer teaching actions

import logging
from backend.services.llm_client import llm_client
from backend.services.knowledge_graph import knowledge_graph

logger = logging.getLogger(__name__)


async def tool_teach_with_analogy(*, session, learner, concept_id: str,
                                  analogy_source: str = "", **kwargs) -> dict:
    concept = knowledge_graph.get_concept(concept_id)
    source = knowledge_graph.get_concept(analogy_source)

    if not concept:
        return {"action": "error", "content": {"error": f"Concept {concept_id} not found"}}

    source_name = source.name if source else analogy_source

    system = f"""You are an expert teacher using the ANALOGY teaching method.
Teach the new concept by explicitly connecting it to something the learner already understands.

Rules:
- Start by referencing what they know: "{source_name}"
- Map each part of the new concept to a corresponding part in the familiar concept
- Use phrases like "Remember how {source_name} works? {concept.name} is similar, but..."
- Highlight where the analogy breaks down (important for avoiding misconceptions)
- End with a check question that tests whether they see the connection

Return JSON:
{{
    "teaching_content": "Your analogy-based explanation",
    "analogy_mapping": [{{"source": "concept A aspect", "target": "concept B aspect"}}],
    "check_question": "Question testing understanding of the connection",
    "expected_check_answer": "Expected answer",
    "strategy_used": "analogy"
}}"""

    prompt = f"""Target concept: {concept.name} ({concept_id})
Description: {concept.description}
Domain: {concept.domain}

Analogy source (learner already knows this): {source_name}
Transfer strength: {knowledge_graph.get_transfer_edge(analogy_source, concept_id)}

Learner: {learner.name}, experience: {learner.experience_level}"""

    result = await llm_client.generate(prompt, system=system)
    result["action"] = "teach"
    result["strategy_used"] = "analogy"
    result["concept_id"] = concept_id
    return {"action": "teach", "content": result, "_llm_calls": 1}


async def tool_composite_exercise(*, session, learner, concepts: list[str] | str = "",
                                  exercise_type: str = "mini_project", **kwargs) -> dict:
    if isinstance(concepts, str):
        concepts = [c.strip() for c in concepts.split(",") if c.strip()]
    if not concepts:
        concepts = [session.current_concept] if session.current_concept else []

    concept_names = []
    for cid in concepts:
        c = knowledge_graph.get_concept(cid)
        concept_names.append(c.name if c else cid)

    system = f"""You are creating a {exercise_type} that naturally requires multiple concepts.
The exercise should NOT be a disconnected set of problems — it should be ONE cohesive challenge
where the learner must apply all the concepts together to solve it.

Return JSON:
{{
    "title": "Exercise title",
    "description": "What the learner needs to build/solve",
    "requirements": ["Requirement 1 (uses concept A)", "Requirement 2 (uses concept B)"],
    "starter_code": "Optional starter code",
    "expected_approach": "How to solve it using all concepts",
    "hints": ["Hint 1", "Hint 2"],
    "concepts_tested": {concepts}
}}"""

    prompt = f"""Concepts to combine:
{chr(10).join(f'- {cid}: {name}' for cid, name in zip(concepts, concept_names))}

Exercise type: {exercise_type}
Learner: {learner.name}, experience: {learner.experience_level}
Mastered concepts: {list(k for k, v in learner.concept_states.items() if v.status == 'mastered')[:10]}"""

    result = await llm_client.generate(prompt, system=system)
    return {"action": "practice", "content": result, "_llm_calls": 1}


async def tool_socratic_dialogue(*, session, learner, concept_id: str,
                                 starting_question: str = "", **kwargs) -> dict:
    concept = knowledge_graph.get_concept(concept_id)
    if not concept:
        return {"action": "error", "content": {"error": f"Concept {concept_id} not found"}}

    cs = learner.concept_states.get(concept_id)
    prior_knowledge = ""
    if cs:
        prior_knowledge = f"Current mastery: {cs.mastery_score:.1f}, Status: {cs.status}"

    system = """You are a Socratic teacher. Instead of explaining, guide through questions.

Rules:
- Start with a thought-provoking question, NOT an explanation
- The question should make the learner think about the concept from their existing knowledge
- Include 2-3 follow-up questions for different answer directions
- Never give away the answer — guide them to discover it

Return JSON:
{
    "opening_question": "Your thought-provoking opening question",
    "follow_up_if_correct": "Question to deepen understanding if they get it right",
    "follow_up_if_partial": "Question to guide them closer if they're partially right",
    "follow_up_if_wrong": "Question that redirects without revealing the answer",
    "discovery_target": "What you want them to discover (not shown to learner)",
    "strategy_used": "socratic"
}"""

    prompt = f"""Concept: {concept.name} ({concept_id})
Domain: {concept.domain}
{prior_knowledge}
Starting question hint: {starting_question or 'Choose your own opening'}
Learner: {learner.name}"""

    result = await llm_client.generate(prompt, system=system)
    return {"action": "dialogue", "content": result, "_llm_calls": 1}


async def tool_address_misconception(*, session, learner, misconception_id: str = "",
                                     concept_id: str = "", **kwargs) -> dict:
    if not concept_id:
        concept_id = session.current_concept or ""
    concept = knowledge_graph.get_concept(concept_id)
    misconception = None
    if concept:
        for m in concept.common_misconceptions:
            if m.id == misconception_id:
                misconception = m
                break

    system = """You are addressing a specific misconception a learner has.

Rules:
- Name the misconception explicitly: "A common mistake is thinking that..."
- Explain WHY people make this mistake (it's intuitive but wrong because...)
- Show a concrete example where the misconception leads to wrong results
- Then show the correct understanding with the same example
- End with a quick check: "Can you explain why [misconception scenario] doesn't work?"

Return JSON:
{
    "misconception_explanation": "Why this is wrong and where it comes from",
    "wrong_example": "Code/scenario where the misconception leads to wrong results",
    "correct_explanation": "The right way to think about it",
    "correct_example": "Same scenario done correctly",
    "check_question": "Quick check that they've resolved the misconception",
    "strategy_used": "misconception_remediation"
}"""

    prompt = f"""Concept: {concept.name if concept else concept_id}
Misconception: {misconception_id}
Description: {misconception.description if misconception else 'Unknown misconception'}
Indicators: {misconception.indicators if misconception else []}
Learner: {learner.name}"""

    result = await llm_client.generate(prompt, system=system)
    return {"action": "teach", "content": result, "_llm_calls": 1}


async def tool_real_world_scenario(*, session, learner, concept_id: str = "",
                                   domain: str = "", **kwargs) -> dict:
    if not concept_id:
        concept_id = session.current_concept or ""
    concept = knowledge_graph.get_concept(concept_id)
    if not concept:
        return {"action": "error", "content": {"error": f"Concept {concept_id} not found"}}

    used_contexts = []
    cs = learner.concept_states.get(concept_id)
    if cs:
        used_contexts = cs.contexts_encountered or []

    system = """Create a realistic work scenario that naturally requires this concept.
The scenario should feel like something from an actual software engineering job,
not a textbook exercise.

Return JSON:
{
    "scenario_title": "Brief title",
    "context": "2-3 sentences setting up the scenario",
    "task": "What specifically needs to be done",
    "requirements": ["Specific requirement 1", "Specific requirement 2"],
    "why_this_concept": "Why this concept is essential for this task",
    "starter_code": "Optional starter code",
    "expected_solution_approach": "How to solve it",
    "strategy_used": "real_world_scenario"
}"""

    prompt = f"""Concept: {concept.name} ({concept_id})
Domain: {concept.domain}
Difficulty tier: {concept.difficulty_tier}
Application domain: {domain or 'web development'}
Already-used contexts (avoid these): {used_contexts}
Learner experience: {learner.experience_level}"""

    result = await llm_client.generate(prompt, system=system)
    return {"action": "practice", "content": result, "_llm_calls": 1}
