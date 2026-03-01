# pedagogy engine - evidence aggregation, readiness estimation, confidence, test difficulty
# no LLM calls, pure computation that feeds into orchestrator context

import logging
from backend.models.learner import LearnerState, UnderstandingSignal

logger = logging.getLogger(__name__)


class PedagogyEngine:

    def build_evidence_summary(self, learner: LearnerState, concept_id: str | None) -> str:
        if not concept_id:
            return "  No concept selected yet."

        cs = learner.concept_states.get(concept_id)
        if not cs:
            return "  No evidence collected yet."

        lines = []

        # Recent signals
        for sig in cs.understanding_signals[-5:]:
            lines.append(f"  [{sig.signal_type}] {sig.value:.2f} — {sig.evidence}")

        # Teaching history
        if cs.teaching_strategies_tried:
            tried = ", ".join(f"{s} ({v:.2f})" for s, v in cs.teaching_strategies_tried.items())
            lines.append(f"  Strategies tried: {tried}")

        # Misconceptions
        if cs.misconceptions_active:
            lines.append(f"  Active misconceptions: {cs.misconceptions_active}")

        # Confidence
        if cs.confidence > 0:
            lines.append(f"  Computed confidence: {cs.confidence:.2f}")

        # Readiness
        readiness = self.compute_readiness_estimate(learner, concept_id)
        lines.append(f"  Readiness estimate: {readiness:.2f}")

        return "\n".join(lines) if lines else "  No evidence collected yet."

    def compute_readiness_estimate(self, learner: LearnerState, concept_id: str) -> float:
        cs = learner.concept_states.get(concept_id)
        if not cs or not cs.understanding_signals:
            return 0.0

        # Weight recent signals more heavily
        signals = cs.understanding_signals[-10:]
        if not signals:
            return 0.0

        weighted_sum = 0.0
        weight_total = 0.0
        for i, sig in enumerate(signals):
            weight = 1.0 + (i / len(signals))  # more recent = higher weight
            weighted_sum += sig.value * weight
            weight_total += weight

        return round(weighted_sum / weight_total, 3) if weight_total > 0 else 0.0

    def suggest_approach(self, learner: LearnerState, concept_id: str | None) -> str:
        if not concept_id:
            return "No concept selected yet."

        readiness = self.compute_readiness_estimate(learner, concept_id)
        cs = learner.concept_states.get(concept_id)

        if readiness > 0.8:
            return "Learner shows strong understanding — ASK if they're ready to test."
        elif readiness > 0.5:
            return "Moderate understanding — practice or targeted questions would help."
        elif cs and len(cs.teaching_strategies_tried) >= 2:
            return "Multiple strategies tried with low signal — consider switching concept or trying dialogue."
        else:
            return "Building understanding — continue with teaching or scaffolded practice."

    # blend test scores (50%), self-assessment (25%), teaching response quality (25%)
    def compute_confidence(self, learner: LearnerState, concept_id: str) -> float:
        cs = learner.concept_states.get(concept_id)
        if not cs or not cs.understanding_signals:
            return 0.0

        test_scores = [s.value for s in cs.understanding_signals if s.signal_type == "test_score"]
        self_assessments = [s.value for s in cs.understanding_signals if s.signal_type == "self_assessment"]
        teaching_responses = [s.value for s in cs.understanding_signals if s.signal_type == "teaching_response"]

        # Weighted blend: tests matter most, then self-assessment, then engagement
        components = []
        if test_scores:
            recent = test_scores[-3:]
            components.append(("test", sum(recent) / len(recent), 0.5))
        if self_assessments:
            recent = self_assessments[-3:]
            components.append(("self", sum(recent) / len(recent), 0.25))
        if teaching_responses:
            recent = teaching_responses[-3:]
            components.append(("engagement", sum(recent) / len(recent), 0.25))

        if not components:
            return 0.0

        # Normalize weights to sum to 1.0
        total_weight = sum(w for _, _, w in components)
        confidence = sum(val * (w / total_weight) for _, val, w in components)

        # Store on concept state
        cs.confidence = round(confidence, 3)
        return cs.confidence

    # high confidence (>0.7) → harder, medium → standard, low (<0.4) → easier
    def select_test_difficulty(self, learner: LearnerState, concept_id: str) -> int:
        confidence = self.compute_confidence(learner, concept_id)

        if confidence > 0.7:
            return 3
        elif confidence > 0.4:
            return 2
        else:
            return 1

    # quick heuristic for response quality — length, explanation markers, curiosity
    def estimate_response_quality(self, response: str) -> float:
        if not response:
            return 0.0

        # Length score — longer usually means more engaged
        length_score = min(len(response) / 200, 1.0)

        # Explanation markers — signs of deeper thinking
        explanation_markers = ["because", "since", "means that", "so", "works by",
                               "example", "like", "think", "understand", "reason"]
        marker_count = sum(1 for m in explanation_markers if m in response.lower())
        marker_score = min(marker_count / 3, 1.0)

        # Question marks — engagement/curiosity
        question_bonus = 0.1 if "?" in response else 0.0

        return round(min(length_score * 0.3 + marker_score * 0.6 + question_bonus, 1.0), 2)


pedagogy_engine = PedagogyEngine()
