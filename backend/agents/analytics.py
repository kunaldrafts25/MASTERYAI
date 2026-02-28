# analytics agent - computes velocity, strategy effectiveness, and patterns from learner data

import logging
from datetime import datetime
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage

logger = logging.getLogger(__name__)


class AnalyticsAgent(BaseAgent):
    name = "analytics"

    def compute_learning_velocity(self, learner) -> dict:
        domain_stats: dict[str, dict] = {}

        for cid, cs in learner.concept_states.items():
            domain = cid.split(".")[0] if "." in cid else "general"
            if domain not in domain_stats:
                domain_stats[domain] = {"mastered": 0, "total": 0, "hours": 0.0}
            domain_stats[domain]["total"] += 1
            if cs.status == "mastered":
                domain_stats[domain]["mastered"] += 1
                # estimate hours from test count
                domain_stats[domain]["hours"] += len(cs.transfer_tests) * 0.25

        velocities = {}
        for domain, stats in domain_stats.items():
            if stats["mastered"] > 0:
                velocities[domain] = {
                    "concepts_mastered": stats["mastered"],
                    "total_concepts": stats["total"],
                    "avg_hours_per_concept": round(stats["hours"] / stats["mastered"], 2),
                    "mastery_rate": round(stats["mastered"] / max(stats["total"], 1), 2),
                }
            else:
                velocities[domain] = {
                    "concepts_mastered": 0,
                    "total_concepts": stats["total"],
                    "avg_hours_per_concept": 0.0,
                    "mastery_rate": 0.0,
                }

        return velocities

    def compute_strategy_effectiveness(self, learner) -> dict:
        strategy_data: dict[str, list[float]] = {}

        for cid, cs in learner.concept_states.items():
            for strategy, score in cs.teaching_strategies_tried.items():
                if strategy not in strategy_data:
                    strategy_data[strategy] = []
                strategy_data[strategy].append(score)

        result = {}
        for strategy, scores in strategy_data.items():
            result[strategy] = {
                "usage_count": len(scores),
                "avg_score": round(sum(scores) / len(scores), 3),
                "min_score": round(min(scores), 3),
                "max_score": round(max(scores), 3),
            }

        return result

    def compute_misconception_patterns(self, learner) -> dict:
        active: dict[str, int] = {}
        resolved: dict[str, int] = {}
        recurring: list[str] = []

        for cid, cs in learner.concept_states.items():
            for mid in cs.misconceptions_active:
                active[mid] = active.get(mid, 0) + 1
            for mid in cs.misconceptions_resolved:
                resolved[mid] = resolved.get(mid, 0) + 1
                # recurring: resolved but still appears active elsewhere
                if mid in active:
                    recurring.append(mid)

        return {
            "active_count": sum(active.values()),
            "resolved_count": sum(resolved.values()),
            "active_misconceptions": active,
            "resolved_misconceptions": resolved,
            "recurring": list(set(recurring)),
        }

    def compute_session_engagement(self, learner, sessions: list) -> dict:
        if not sessions:
            return {"total_sessions": 0, "avg_concepts_per_session": 0.0, "pass_rate": 0.0}

        total_tests = 0
        total_passed = 0
        total_concepts = 0

        for s in sessions:
            if hasattr(s, "total_transfer_tests"):
                total_tests += s.total_transfer_tests
                total_passed += s.tests_passed
                total_concepts += len(s.concepts_mastered)
            elif isinstance(s, dict):
                total_tests += s.get("total_transfer_tests", 0)
                total_passed += s.get("tests_passed", 0)
                total_concepts += len(s.get("concepts_mastered", []))

        return {
            "total_sessions": len(sessions),
            "avg_concepts_per_session": round(total_concepts / max(len(sessions), 1), 2),
            "pass_rate": round(total_passed / max(total_tests, 1), 2),
            "total_tests": total_tests,
            "total_passed": total_passed,
        }

    def compute_full_analytics(self, learner, sessions: list | None = None) -> dict:
        return {
            "learning_velocity": self.compute_learning_velocity(learner),
            "strategy_effectiveness": self.compute_strategy_effectiveness(learner),
            "misconception_patterns": self.compute_misconception_patterns(learner),
            "session_engagement": self.compute_session_engagement(learner, sessions or []),
            "learning_patterns": self.identify_learning_patterns(learner),
        }

    def identify_learning_patterns(self, learner) -> list[str]:
        patterns = []

        # strategy preference
        effectiveness = self.compute_strategy_effectiveness(learner)
        if effectiveness:
            best = max(effectiveness.items(), key=lambda x: x[1]["avg_score"])
            if best[1]["usage_count"] >= 2:
                patterns.append(f"Best performing strategy: {best[0]} (avg score: {best[1]['avg_score']:.2f})")

            worst = min(effectiveness.items(), key=lambda x: x[1]["avg_score"])
            if worst[1]["usage_count"] >= 2 and worst[1]["avg_score"] < 0.5:
                patterns.append(f"Struggling with strategy: {worst[0]} (avg score: {worst[1]['avg_score']:.2f})")

        # calibration
        cal_trend = learner.learning_profile.calibration_trend
        if cal_trend == "overconfident":
            patterns.append("Tends to overestimate understanding — calibration exercises recommended")
        elif cal_trend == "improving":
            patterns.append("Calibration improving — self-assessment becoming more accurate")

        # velocity
        velocity = self.compute_learning_velocity(learner)
        for domain, stats in velocity.items():
            if stats["mastery_rate"] > 0.8:
                patterns.append(f"Strong in {domain} — {stats['mastery_rate']*100:.0f}% mastery rate")
            elif stats["mastery_rate"] < 0.3 and stats["total_concepts"] >= 3:
                patterns.append(f"Needs support in {domain} — only {stats['mastery_rate']*100:.0f}% mastery rate")

        # misconceptions
        misconceptions = self.compute_misconception_patterns(learner)
        if misconceptions["recurring"]:
            patterns.append(f"Recurring misconceptions: {misconceptions['recurring'][:3]}")
        if misconceptions["resolved_count"] > 3:
            patterns.append(f"Strong misconception resolution: {misconceptions['resolved_count']} resolved")

        return patterns

    def post_analytics_observation(self, learner, session_id: str):
        patterns = self.identify_learning_patterns(learner)
        if not patterns:
            return

        effectiveness = self.compute_strategy_effectiveness(learner)
        best_strategy = None
        if effectiveness:
            best = max(effectiveness.items(), key=lambda x: x[1]["avg_score"])
            if best[1]["usage_count"] >= 2:
                best_strategy = best[0]

        message_bus.post(AgentMessage(
            source_agent="analytics",
            target_agent="orchestrator",
            message_type="observation",
            content=f"Patterns: {'; '.join(patterns[:3])}",
            metadata={
                "patterns": patterns,
                "best_strategy": best_strategy,
                "strategy_effectiveness": effectiveness,
            },
            session_id=session_id,
        ))


analytics_agent = AnalyticsAgent()
