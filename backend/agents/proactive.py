# proactive intelligence agent — anticipation and initiative
# predicts frustration, decay, opportunities, and generates session openers

import logging
from datetime import datetime, timedelta
from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ProactiveIntelligence(BaseAgent):
    name = "proactive"

    def predict_frustration_risk(self, session, learner) -> dict | None:
        risk_factors = []
        risk_score = 0.0

        cid = session.current_concept
        if cid:
            cs = learner.concept_states.get(cid)
            if cs:
                # declining signal quality
                signals = cs.understanding_signals[-5:] if hasattr(cs, 'understanding_signals') else []
                if len(signals) >= 3:
                    recent = [s.value for s in signals[-3:]]
                    earlier = [s.value for s in signals[:2]]
                    if recent and earlier:
                        trend = sum(recent) / len(recent) - sum(earlier) / len(earlier)
                        if trend < -0.15:
                            risk_score += 0.3
                            risk_factors.append(f"Declining performance: {trend:.2f} trend")

                # many active misconceptions
                if len(cs.misconceptions_active) >= 2:
                    risk_score += 0.2
                    risk_factors.append(f"{len(cs.misconceptions_active)} active misconceptions")

                # multiple failed strategies
                failed = [s for s, v in cs.teaching_strategies_tried.items() if v < 0.4]
                if len(failed) >= 2:
                    risk_score += 0.2
                    risk_factors.append(f"{len(failed)} strategies failed for this concept")

        # session fatigue
        if session.events and len(session.events) > 15:
            risk_score += 0.15
            risk_factors.append("Long session (15+ events)")

        # consecutive failures
        from backend.agents.motivation import motivation_agent
        signals = motivation_agent._get_signals(session.session_id)
        if signals.consecutive_failures >= 2:
            risk_score += 0.25
            risk_factors.append(f"{signals.consecutive_failures} consecutive failures")

        if risk_score < 0.3:
            return None

        suggestion = "Consider switching approach or taking a break."
        if risk_score > 0.7:
            suggestion = "High frustration risk — suggest a break or switch to an easier concept."
        elif "misconceptions" in str(risk_factors):
            suggestion = "Address misconceptions directly before continuing."

        return {
            "risk": min(risk_score, 1.0),
            "factors": risk_factors,
            "suggestion": suggestion,
        }

    def predict_decay_risk(self, learner) -> list[dict]:
        at_risk = []
        now = datetime.utcnow()

        for cid, cs in learner.concept_states.items():
            if cs.status != "mastered":
                continue

            for item in learner.review_queue or []:
                if isinstance(item, dict) and item.get("concept_id") == cid:
                    next_review_str = item.get("next_review", "")
                    if next_review_str:
                        try:
                            next_review = datetime.fromisoformat(next_review_str.replace("Z", ""))
                            days_until = (next_review - now).days
                            if days_until <= 7:
                                risk = max(0, 1.0 - (days_until / 7.0))
                                at_risk.append({
                                    "concept_id": cid,
                                    "days_until_due": days_until,
                                    "risk": round(risk, 2),
                                })
                        except (ValueError, TypeError):
                            pass
                    break

        return sorted(at_risk, key=lambda x: x["risk"], reverse=True)[:5]

    def suggest_study_schedule(self, learner) -> dict:
        sessions_data = []
        for cid, cs in learner.concept_states.items():
            for test in cs.transfer_tests:
                if hasattr(test, 'timestamp') and test.timestamp:
                    sessions_data.append({"score": test.score})

        if len(sessions_data) < 5:
            return {
                "has_enough_data": False,
                "message": "Need at least 5 learning interactions for study suggestions.",
            }

        total_score = sum(s["score"] for s in sessions_data)
        avg_score = total_score / len(sessions_data)

        return {
            "has_enough_data": True,
            "avg_performance": round(avg_score, 2),
            "total_sessions_analyzed": len(sessions_data),
            "suggestion": f"Based on {len(sessions_data)} interactions, your average score is {avg_score:.0%}. "
                          f"Keep sessions focused and take breaks when you notice declining performance.",
        }

    def identify_learning_opportunities(self, learner) -> list[dict]:
        from backend.services.knowledge_graph import knowledge_graph

        opportunities = []
        mastered = {cid for cid, cs in learner.concept_states.items()
                    if cs.status == "mastered"}

        # transfer opportunities from mastered concepts
        for cid in mastered:
            concept = knowledge_graph.get_concept(cid)
            if not concept:
                continue
            for edge in (concept.transfers_to or []):
                target_id = edge.target
                if target_id not in mastered and target_id not in learner.concept_states:
                    target_concept = knowledge_graph.get_concept(target_id)
                    if target_concept and edge.strength >= 0.6:
                        opportunities.append({
                            "type": "transfer",
                            "concept_id": target_id,
                            "concept_name": target_concept.name,
                            "reason": f"Strong transfer from mastered '{concept.name}' "
                                      f"(strength: {edge.strength:.0%})",
                            "estimated_advantage": f"{edge.strength:.0%} faster learning",
                        })

        # quick wins: low difficulty, all prerequisites met
        for concept in knowledge_graph.get_all_concepts():
            if concept.id in mastered or concept.id in learner.concept_states:
                continue
            prereqs = set(concept.prerequisites)
            if prereqs and prereqs.issubset(mastered):
                if concept.difficulty_tier <= 2:
                    opportunities.append({
                        "type": "quick_win",
                        "concept_id": concept.id,
                        "concept_name": concept.name,
                        "reason": f"All prerequisites mastered, difficulty tier {concept.difficulty_tier}",
                        "estimated_advantage": "~30% faster than average",
                    })

        # deduplicate
        seen = set()
        unique = []
        for opp in opportunities:
            if opp["concept_id"] not in seen:
                seen.add(opp["concept_id"])
                unique.append(opp)

        return unique[:5]

    async def suggest_career_direction(self, learner) -> dict | None:
        if learner.career_targets and learner.learning_profile.total_concepts_mastered < 10:
            return None

        from backend.services.llm_client import llm_client

        domain_stats = {}
        for cid, cs in learner.concept_states.items():
            domain = cid.split(".")[0] if "." in cid else "general"
            if domain not in domain_stats:
                domain_stats[domain] = {"mastered": 0, "total": 0, "scores": []}
            domain_stats[domain]["total"] += 1
            if cs.status == "mastered":
                domain_stats[domain]["mastered"] += 1
            if cs.transfer_tests:
                domain_stats[domain]["scores"].extend(t.score for t in cs.transfer_tests)

        for domain in domain_stats:
            scores = domain_stats[domain]["scores"]
            domain_stats[domain]["avg_score"] = round(sum(scores) / len(scores), 2) if scores else 0

        system = """Based on a learner's performance across different domains, suggest a career direction.

Return JSON:
{
    "suggestion": "1-2 sentence career direction suggestion",
    "recommended_role": "Suggested role title",
    "reasoning": "Why this role fits their strengths",
    "strongest_domain": "Their best-performing domain",
    "growth_area": "Domain they should develop more"
}"""

        prompt = f"""Learner: {learner.name}
Experience: {learner.experience_level}
Total concepts mastered: {learner.learning_profile.total_concepts_mastered}
Current career targets: {learner.career_targets or 'None set'}

Domain performance:
{chr(10).join(f'- {d}: {s["mastered"]}/{s["total"]} mastered, avg score {s["avg_score"]}' for d, s in domain_stats.items())}

Preferred strategy: {learner.learning_profile.preferred_strategy or 'none identified'}
Calibration: {learner.learning_profile.calibration_trend}"""

        return await llm_client.generate(prompt, system=system)

    async def generate_session_opener(self, learner, journal=None) -> str:
        from backend.services.llm_client import llm_client

        last_session_summary = ""
        if journal and journal.entries:
            recent = journal.get_recent(1)
            if recent:
                last_session_summary = recent[0].content

        decay_risks = self.predict_decay_risk(learner)
        opportunities = self.identify_learning_opportunities(learner)

        system = """Generate a warm, personalized "welcome back" message from a professor to a returning learner.
Keep it to 2-3 sentences. Reference specific things from their last session if available.
Be encouraging and forward-looking.

Return JSON:
{
    "greeting": "Your personalized welcome message",
    "suggested_focus": "What you recommend they focus on today"
}"""

        prompt = f"""Learner: {learner.name}
Total concepts mastered: {learner.learning_profile.total_concepts_mastered}
Last session: {last_session_summary or 'First session!'}
Concepts at risk of decay: {[d['concept_id'] for d in decay_risks[:2]]}
Learning opportunities: {[o['concept_name'] for o in opportunities[:2]]}
Career targets: {learner.career_targets or 'None set'}"""

        result = await llm_client.generate(prompt, system=system)
        return result.get("greeting", f"Welcome back, {learner.name}! Ready to continue learning?")

    def opine(self, session, learner):
        from backend.agents.deliberation import AgentOpinion

        frustration = self.predict_frustration_risk(session, learner)
        if frustration and frustration["risk"] > 0.6:
            return AgentOpinion(
                agent_name="proactive",
                recommendation="reduce_difficulty",
                reasoning=f"Frustration risk {frustration['risk']:.0%}: {'; '.join(frustration['factors'][:2])}",
                confidence=frustration["risk"],
                priority="important",
            )
        return None


proactive_agent = ProactiveIntelligence()
