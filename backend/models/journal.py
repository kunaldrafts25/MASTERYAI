# learner journal — persistent narrative memory of the learning journey

from pydantic import BaseModel, Field
import uuid


def _uuid() -> str:
    return str(uuid.uuid4())[:8]


class JournalEntry(BaseModel):
    entry_id: str = Field(default_factory=_uuid)
    timestamp: str = ""  # ISO format
    session_id: str = ""
    entry_type: str  # "session_summary" | "teaching_reflection" | "breakthrough" |
                      # "struggle" | "preference_discovered" | "misconception_pattern"
    content: str     # LLM-generated narrative (2-3 sentences max)
    concepts: list[str] = []  # Related concept IDs
    tags: list[str] = []  # Searchable: ["struggled", "analogy_worked", "closures"]


class LearnerJournal(BaseModel):
    learner_id: str
    entries: list[JournalEntry] = []

    def get_recent(self, limit: int = 10) -> list[JournalEntry]:
        return sorted(self.entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_for_concept(self, concept_id: str) -> list[JournalEntry]:
        return [e for e in self.entries if concept_id in e.concepts]

    def get_by_tag(self, tag: str) -> list[JournalEntry]:
        return [e for e in self.entries if tag in e.tags]

    def get_by_type(self, entry_type: str) -> list[JournalEntry]:
        return [e for e in self.entries if e.entry_type == entry_type]

    def search(self, query: str) -> list[JournalEntry]:
        query_lower = query.lower()
        return [e for e in self.entries if query_lower in e.content.lower()]
