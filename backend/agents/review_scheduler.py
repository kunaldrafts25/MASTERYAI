# SM-2 spaced repetition scheduler - pure math, no LLM calls

import logging
import math
from datetime import datetime, timedelta
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage

logger = logging.getLogger(__name__)


class ReviewItem:
    def __init__(self, concept_id: str, easiness_factor: float = 2.5,
                 repetition_count: int = 0, interval_days: float = 1.0,
                 next_review: str | None = None, last_score: float = 0.0,
                 misconception_count: int = 0):
        self.concept_id = concept_id
        self.easiness_factor = easiness_factor
        self.repetition_count = repetition_count
        self.interval_days = interval_days
        self.next_review = next_review or datetime.utcnow().isoformat()
        self.last_score = last_score
        self.misconception_count = misconception_count

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "easiness_factor": round(self.easiness_factor, 3),
            "repetition_count": self.repetition_count,
            "interval_days": round(self.interval_days, 1),
            "next_review": self.next_review,
            "last_score": round(self.last_score, 3),
            "misconception_count": self.misconception_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewItem":
        return cls(
            concept_id=data["concept_id"],
            easiness_factor=data.get("easiness_factor", 2.5),
            repetition_count=data.get("repetition_count", 0),
            interval_days=data.get("interval_days", 1.0),
            next_review=data.get("next_review"),
            last_score=data.get("last_score", 0.0),
            misconception_count=data.get("misconception_count", 0),
        )


class ReviewSchedulerAgent(BaseAgent):
    name = "review_scheduler"

    def _get_sm2_profile(self, learner) -> tuple:
        from backend.agents.rl_engine import DEFAULT_SM2_PROFILE, get_rl_engine
        try:
            engine = get_rl_engine(learner)
            return engine.select_sm2_profile(learner)
        except Exception:
            return DEFAULT_SM2_PROFILE

    # run SM-2 after a test result
    def schedule_review(self, learner, concept_id: str, score: float):
        queue = self._load_queue(learner)
        item = queue.get(concept_id)
        if not item:
            item = ReviewItem(concept_id=concept_id)
            queue[concept_id] = item

        # Load adaptive SM-2 parameters from RL engine
        init_ef, min_ef, ef_coeffs, miscon_penalty, reset_interval = self._get_sm2_profile(learner)
        ef_a, ef_b, ef_c = ef_coeffs

        # SM-2 quality scale: 0-5
        quality = score * 5.0
        item.last_score = score

        # count active misconceptions
        cs = learner.concept_states.get(concept_id)
        miscon_count = len(cs.misconceptions_active) if cs else 0
        item.misconception_count = miscon_count

        # update easiness factor using profile parameters
        item.easiness_factor = max(
            min_ef,
            item.easiness_factor + ef_a - (5 - quality) * (ef_b + (5 - quality) * ef_c)
        )

        if quality >= 3:
            # successful recall
            if item.repetition_count == 0:
                item.interval_days = reset_interval
            elif item.repetition_count == 1:
                item.interval_days = reset_interval * 6.0
            else:
                item.interval_days = item.interval_days * item.easiness_factor
            item.repetition_count += 1
        else:
            # failed recall — reset
            item.interval_days = reset_interval
            item.repetition_count = 0

        # misconception penalty using profile parameter
        if miscon_count > 0:
            item.interval_days *= (1.0 - miscon_penalty * min(miscon_count, 3))

        # set next review date
        next_dt = datetime.utcnow() + timedelta(days=item.interval_days)
        item.next_review = next_dt.isoformat()

        logger.info(
            f"SM-2 scheduled {concept_id}: interval={item.interval_days:.1f}d, "
            f"EF={item.easiness_factor:.2f}, rep={item.repetition_count}, "
            f"next={item.next_review[:10]}"
        )

        self._save_queue(learner, queue)

    # most overdue first
    def get_due_reviews(self, learner, limit: int = 5) -> list[dict]:
        queue = self._load_queue(learner)
        now = datetime.utcnow()
        due = []

        for cid, item in queue.items():
            try:
                next_dt = datetime.fromisoformat(item.next_review)
            except (ValueError, TypeError):
                continue

            if next_dt <= now:
                overdue_days = (now - next_dt).total_seconds() / 86400
                urgency = overdue_days / max(item.interval_days, 1.0)
                due.append({
                    "concept_id": cid,
                    "overdue_days": round(overdue_days, 1),
                    "urgency": round(urgency, 2),
                    "last_score": item.last_score,
                    "easiness_factor": item.easiness_factor,
                    "repetition_count": item.repetition_count,
                })

        due.sort(key=lambda x: x["urgency"], reverse=True)
        return due[:limit]

    def has_urgent_reviews(self, learner) -> bool:
        due = self.get_due_reviews(learner, limit=1)
        return bool(due) and due[0]["urgency"] > 1.5

    # R = e^(-t/S) where S = interval * EF
    def get_retention_curve(self, learner, concept_id: str) -> dict:
        queue = self._load_queue(learner)
        item = queue.get(concept_id)
        if not item:
            return {"concept_id": concept_id, "retention": 0.0, "stability": 0.0}

        stability = item.interval_days * item.easiness_factor
        try:
            next_dt = datetime.fromisoformat(item.next_review)
            last_review = next_dt - timedelta(days=item.interval_days)
            days_since = (datetime.utcnow() - last_review).total_seconds() / 86400
        except (ValueError, TypeError):
            days_since = 0

        retention = math.exp(-days_since / max(stability, 0.1))

        return {
            "concept_id": concept_id,
            "retention": round(retention, 3),
            "stability": round(stability, 1),
            "days_since_review": round(days_since, 1),
            "interval_days": item.interval_days,
            "easiness_factor": item.easiness_factor,
        }

    def get_queue_summary(self, learner) -> dict:
        queue = self._load_queue(learner)
        due = self.get_due_reviews(learner, limit=20)
        upcoming = []
        now = datetime.utcnow()

        for cid, item in queue.items():
            try:
                next_dt = datetime.fromisoformat(item.next_review)
            except (ValueError, TypeError):
                continue
            if next_dt > now:
                days_until = (next_dt - now).total_seconds() / 86400
                upcoming.append({
                    "concept_id": cid,
                    "days_until": round(days_until, 1),
                    "easiness_factor": item.easiness_factor,
                })

        upcoming.sort(key=lambda x: x["days_until"])

        return {
            "total_items": len(queue),
            "due_now": len(due),
            "due_reviews": due[:5],
            "upcoming": upcoming[:10],
        }

    def predict_at_risk(self, learner, days_ahead: int = 7) -> list[dict]:
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)
        at_risk = []

        for item in (learner.review_queue or []):
            if not isinstance(item, dict):
                continue
            next_review_str = item.get("next_review", "")
            if not next_review_str:
                continue
            try:
                next_review = datetime.fromisoformat(next_review_str.replace("Z", ""))
                if next_review <= cutoff:
                    days_until = max(0, (next_review - now).days)
                    at_risk.append({
                        "concept_id": item.get("concept_id", "unknown"),
                        "days_until_due": days_until,
                        "overdue": next_review < now,
                    })
            except (ValueError, TypeError):
                pass

        return sorted(at_risk, key=lambda x: x["days_until_due"])

    def opine(self, session, learner):
        from backend.agents.deliberation import AgentOpinion

        due = self.get_due_reviews(learner)
        if not due:
            return None

        urgent = [r for r in due if r.get("urgency", 0) > 1.5]
        if urgent:
            return AgentOpinion(
                agent_name="review_scheduler",
                recommendation="review",
                reasoning=f"{len(urgent)} concept(s) significantly overdue. Most urgent: '{urgent[0]['concept_id']}'.",
                confidence=0.85,
                priority="critical",
            )
        return AgentOpinion(
            agent_name="review_scheduler",
            recommendation="review",
            reasoning=f"{len(due)} concept(s) due for review.",
            confidence=0.5,
            priority="advisory",
        )

    def post_review_recommendations(self, learner, session_id: str):
        due = self.get_due_reviews(learner, limit=3)
        if not due:
            return

        urgent = [d for d in due if d["urgency"] > 1.5]
        if urgent:
            message_bus.post(AgentMessage(
                source_agent="review_scheduler",
                target_agent="orchestrator",
                message_type="warning",
                content=f"{len(urgent)} concepts urgently need review: {[d['concept_id'] for d in urgent]}",
                metadata={"urgent_reviews": urgent},
                session_id=session_id,
            ))
        elif due:
            message_bus.post(AgentMessage(
                source_agent="review_scheduler",
                target_agent="orchestrator",
                message_type="recommendation",
                content=f"{len(due)} concepts due for review: {[d['concept_id'] for d in due]}",
                metadata={"due_reviews": due},
                session_id=session_id,
            ))

    # -- persistence helpers --

    def _load_queue(self, learner) -> dict[str, ReviewItem]:
        queue = {}
        for item_data in learner.review_queue:
            try:
                item = ReviewItem.from_dict(item_data)
                queue[item.concept_id] = item
            except Exception:
                continue
        return queue

    def _save_queue(self, learner, queue: dict[str, ReviewItem]):
        learner.review_queue = [item.to_dict() for item in queue.values()]


review_scheduler = ReviewSchedulerAgent()
