# agent deliberation protocol — structured multi-agent negotiation
# solicits opinions, detects conflicts, resolves via LLM only when needed

import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentOpinion(BaseModel):
    agent_name: str
    recommendation: str  # What action this agent recommends
    reasoning: str       # Why (1-2 sentences)
    confidence: float = 0.5  # 0.0-1.0 how sure the agent is
    priority: str = "advisory"  # "critical" | "important" | "advisory"
    constraints: list[str] = []  # Things this agent says MUST NOT happen


class Conflict(BaseModel):
    agents: list[str]
    nature: str  # Brief description of the conflict
    opinions: list[AgentOpinion]


class DeliberationResult(BaseModel):
    participating_agents: list[str] = []
    opinions: list[AgentOpinion] = []
    conflicts: list[Conflict] = []
    resolution: str = ""  # LLM-generated resolution reasoning (empty if no conflicts)
    resolved_recommendation: str = ""  # The final recommendation after resolution
    consensus: bool = True  # True if all agents agree


class DeliberationProtocol:

    # action categories for conflict detection
    EASE_ACTIONS = {"reduce_difficulty", "suggest_break", "switch_concept"}
    PUSH_ACTIONS = {"test", "review", "advance", "increase_difficulty"}

    async def deliberate(self, session, learner, trigger: str) -> DeliberationResult:
        # solicit -> detect -> resolve
        opinions = self._solicit_opinions(session, learner, trigger)

        if not opinions:
            return DeliberationResult()

        # Step 2: Detect conflicts
        conflicts = self._detect_conflicts(opinions)

        # Step 3: If conflicts exist, resolve via LLM (1 call)
        resolution = ""
        resolved_rec = ""
        if conflicts:
            resolution, resolved_rec = await self._resolve_conflicts(
                opinions, conflicts, session, learner
            )

        return DeliberationResult(
            participating_agents=[o.agent_name for o in opinions],
            opinions=opinions,
            conflicts=conflicts,
            resolution=resolution,
            resolved_recommendation=resolved_rec,
            consensus=len(conflicts) == 0,
        )

    def _solicit_opinions(self, session, learner, trigger) -> list[AgentOpinion]:
        opinions = []

        from backend.agents.motivation import motivation_agent
        opinions.append(motivation_agent.opine(session, learner))

        from backend.agents.curriculum import curriculum_agent
        opinions.append(curriculum_agent.opine(session, learner))

        from backend.agents.review_scheduler import review_scheduler
        opinions.append(review_scheduler.opine(session, learner))

        from backend.agents.analytics import analytics_agent
        opinions.append(analytics_agent.opine(session, learner))

        from backend.agents.teacher import teacher_agent
        opinions.append(teacher_agent.opine(session, learner))

        # Filter out None opinions (agent has nothing to say)
        return [o for o in opinions if o is not None]

    def _detect_conflicts(self, opinions: list[AgentOpinion]) -> list[Conflict]:
        conflicts = []

        # Check for ease vs push conflicts
        ease_opinions = [o for o in opinions if o.recommendation in self.EASE_ACTIONS]
        push_opinions = [o for o in opinions if o.recommendation in self.PUSH_ACTIONS]

        if ease_opinions and push_opinions:
            conflicts.append(Conflict(
                agents=[o.agent_name for o in ease_opinions + push_opinions],
                nature="Ease-off vs push-forward conflict",
                opinions=ease_opinions + push_opinions,
            ))

        # Check for priority conflicts (multiple "critical" with different recs)
        critical = [o for o in opinions if o.priority == "critical"]
        if len(critical) > 1:
            recs = set(o.recommendation for o in critical)
            if len(recs) > 1:
                conflicts.append(Conflict(
                    agents=[o.agent_name for o in critical],
                    nature="Multiple critical priorities with different recommendations",
                    opinions=critical,
                ))

        # Check for constraint violations
        all_constraints = []
        for o in opinions:
            all_constraints.extend(o.constraints)
        for o in opinions:
            for constraint in all_constraints:
                if o.recommendation.lower() in constraint.lower():
                    conflicts.append(Conflict(
                        agents=[o.agent_name],
                        nature=f"Recommendation '{o.recommendation}' violates constraint: {constraint}",
                        opinions=[o],
                    ))

        return conflicts

    async def _resolve_conflicts(self, opinions: list[AgentOpinion],
                                  conflicts: list[Conflict],
                                  session, learner) -> tuple[str, str]:
        from backend.services.llm_client import llm_client

        opinion_text = "\n".join(
            f"- {o.agent_name} (confidence={o.confidence}, priority={o.priority}): "
            f"Recommends '{o.recommendation}' because: {o.reasoning}"
            + (f" | Constraints: {o.constraints}" if o.constraints else "")
            for o in opinions
        )

        conflict_text = "\n".join(
            f"- CONFLICT: {c.nature} (agents: {c.agents})"
            for c in conflicts
        )

        system = """You are a mediator resolving conflicting recommendations from educational AI agents.
Each agent has expertise in a different area. Your job is to weigh their arguments
considering the learner's current state and find the best pedagogical path forward.

Principles:
- Learner wellbeing (motivation) overrides curriculum pressure in most cases
- Urgent reviews should not be indefinitely postponed
- Career goals matter but not at the cost of learner burnout
- When in doubt, follow the higher-confidence agent
- A frustrated learner cannot learn effectively — address frustration first

Return JSON:
{
    "reasoning": "2-3 sentence explanation of how you resolved the conflict",
    "recommendation": "the final recommended action"
}"""

        cid = session.current_concept or "none"
        prompt = f"""Learner: {learner.name}
Current concept: {cid}
Session state: {session.current_state}
Experience: {learner.experience_level}
Concepts mastered: {learner.learning_profile.total_concepts_mastered}

AGENT OPINIONS:
{opinion_text}

CONFLICTS:
{conflict_text}

What should we do?"""

        result = await llm_client.generate(prompt, system=system)
        return (
            result.get("reasoning", "No resolution reasoning"),
            result.get("recommendation", opinions[0].recommendation if opinions else "teach"),
        )


deliberation_protocol = DeliberationProtocol()
