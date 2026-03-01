# memory agent — cross-session narrative memory
# summaries, reflections, context recall, pattern detection

import logging
from backend.agents.base import BaseAgent
from backend.models.journal import JournalEntry, LearnerJournal

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    name = "memory"

    async def generate_session_summary(self, session, learner) -> JournalEntry:
        from backend.services.llm_client import llm_client
        from datetime import datetime

        concepts = session.concepts_covered or []
        mastered = session.concepts_mastered or []
        misconceptions = session.misconceptions_detected or []
        resolved = session.misconceptions_resolved or []
        strategies = set()
        for event in session.events:
            if event.payload and "strategy" in event.payload:
                strategies.add(event.payload["strategy"])

        system = """Summarize this learning session in 2-3 concise sentences.
Focus on: what was studied, what the learner struggled with, what worked,
and any breakthroughs. Write from the perspective of a professor reviewing notes.

Return JSON:
{
    "summary": "2-3 sentence narrative summary",
    "tags": ["tag1", "tag2"],
    "entry_type": "session_summary"
}

Tags should be descriptive: "struggled_with_closures", "analogy_worked",
"breakthrough_recursion", "frustrated_early", "strong_finish", etc."""

        prompt = f"""Session for {learner.name}:
- Concepts covered: {concepts}
- Concepts mastered: {mastered}
- Misconceptions detected: {misconceptions}
- Misconceptions resolved: {resolved}
- Teaching strategies used: {list(strategies)}
- Tests passed: {session.tests_passed}, failed: {session.tests_failed}
- Duration: {len(session.events)} events
- Engagement: {session.engagement_state}"""

        result = await llm_client.generate(prompt, system=system)

        return JournalEntry(
            timestamp=datetime.utcnow().isoformat(),
            session_id=session.session_id,
            entry_type=result.get("entry_type", "session_summary"),
            content=result.get("summary", "Session completed."),
            concepts=concepts,
            tags=result.get("tags", []),
        )

    async def generate_teaching_reflection(self, concept_id: str,
                                            strategy: str,
                                            score: float,
                                            session, learner) -> JournalEntry:
        from backend.services.llm_client import llm_client
        from datetime import datetime

        cs = learner.concept_states.get(concept_id)
        strategies_tried = dict(cs.teaching_strategies_tried) if cs else {}
        misconceptions = list(cs.misconceptions_active) if cs else []

        system = """You are reflecting on a teaching attempt. In 2 sentences:
1. Evaluate whether the strategy worked (based on the test score)
2. Suggest what to try differently next time if the score was low

Return JSON:
{
    "reflection": "2 sentence reflection",
    "tags": ["tag1", "tag2"],
    "next_suggestion": "brief suggestion for next attempt"
}"""

        prompt = f"""Concept: {concept_id}
Strategy used: {strategy}
Test score: {score:.2f}
Strategies previously tried: {strategies_tried}
Active misconceptions: {misconceptions}
Learner: {learner.name}"""

        result = await llm_client.generate(prompt, system=system)

        tags = result.get("tags", [])
        if score < 0.4:
            tags.append("strategy_failed")
        elif score > 0.8:
            tags.append("strategy_succeeded")

        return JournalEntry(
            timestamp=datetime.utcnow().isoformat(),
            session_id=session.session_id,
            entry_type="teaching_reflection",
            content=result.get("reflection", f"Strategy '{strategy}' scored {score:.2f}."),
            concepts=[concept_id],
            tags=tags,
        )

    def recall_relevant_context(self, journal: LearnerJournal,
                                 concept_id: str | None = None,
                                 limit: int = 5) -> str:
        entries = []

        if concept_id:
            entries.extend(journal.get_for_concept(concept_id))

        entries.extend(journal.get_by_type("session_summary")[:3])
        entries.extend(journal.get_by_type("teaching_reflection")[:3])

        # Deduplicate and sort by timestamp
        seen = set()
        unique = []
        for e in entries:
            if e.entry_id not in seen:
                seen.add(e.entry_id)
                unique.append(e)
        unique.sort(key=lambda e: e.timestamp, reverse=True)
        unique = unique[:limit]

        if not unique:
            return ""

        lines = ["LEARNER MEMORY (from previous sessions):"]
        for e in unique:
            date = e.timestamp[:10] if e.timestamp else "unknown"
            lines.append(f"  [{date}] ({e.entry_type}): {e.content}")

        return "\n".join(lines)

    def detect_patterns(self, journal: LearnerJournal) -> list[str]:
        patterns = []

        tag_counts: dict[str, int] = {}
        for entry in journal.entries:
            for tag in entry.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        struggle_tags = [t for t, c in tag_counts.items()
                         if c >= 2 and ("struggled" in t or "failed" in t)]
        if struggle_tags:
            patterns.append(f"Recurring struggles: {', '.join(struggle_tags)}")

        success_tags = [t for t, c in tag_counts.items()
                        if c >= 2 and ("worked" in t or "succeeded" in t)]
        if success_tags:
            patterns.append(f"Effective approaches: {', '.join(success_tags)}")

        concept_mentions: dict[str, int] = {}
        for entry in journal.get_by_type("teaching_reflection"):
            for cid in entry.concepts:
                concept_mentions[cid] = concept_mentions.get(cid, 0) + 1
        repeat_concepts = [c for c, n in concept_mentions.items() if n >= 3]
        if repeat_concepts:
            patterns.append(f"Concepts needing extra attention: {', '.join(repeat_concepts)}")

        return patterns


memory_agent = MemoryAgent()
