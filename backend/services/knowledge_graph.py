import json
import heapq
import logging
from pathlib import Path
from backend.models.concept import Concept
from backend.config import settings

logger = logging.getLogger(__name__)


class KnowledgeGraphService:

    def __init__(self):
        self.concepts: dict[str, Concept] = {}
        self.domains: list[dict] = []
        self._prerequisite_cache: dict[str, set[str]] = {}

    def load(self, path: str | None = None):
        p = Path(path or settings.knowledge_graph_path)
        with open(p) as f:
            data = json.load(f)
        self.domains = data.get("domains", [])
        for raw in data["concepts"]:
            c = Concept(**raw)
            self.concepts[c.id] = c
        self._prerequisite_cache.clear()

    def add_concepts(self, concepts: list[Concept]) -> int:
        added = 0
        for c in concepts:
            if c.id not in self.concepts:
                self.concepts[c.id] = c
                added += 1
                # add domain if new
                if not any(d["id"] == c.domain for d in self.domains):
                    self.domains.append({
                        "id": c.domain,
                        "name": c.domain.replace("_", " ").title(),
                        "description": f"Dynamically generated concepts for {c.domain}",
                        "concept_count": 0,
                    })
            else:
                logger.debug(f"concept {c.id} already exists, skipping")
        # update domain counts
        for d in self.domains:
            d["concept_count"] = len(self.get_domain_concepts(d["id"]))
        self._prerequisite_cache.clear()
        logger.info(f"added {added} new concepts to knowledge graph (total: {len(self.concepts)})")
        return added

    def get_concept(self, concept_id: str) -> Concept | None:
        return self.concepts.get(concept_id)

    def get_all_concepts(self) -> list[Concept]:
        return list(self.concepts.values())

    def get_domain_concepts(self, domain: str) -> list[Concept]:
        return [c for c in self.concepts.values() if c.domain == domain]

    def get_prerequisites(self, concept_id: str) -> list[str]:
        c = self.concepts.get(concept_id)
        return c.prerequisites if c else []

    def get_all_prerequisites(self, concept_id: str) -> set[str]:
        if concept_id in self._prerequisite_cache:
            return self._prerequisite_cache[concept_id]

        result = set()
        stack = list(self.get_prerequisites(concept_id))
        while stack:
            pid = stack.pop()
            if pid not in result:
                result.add(pid)
                stack.extend(self.get_prerequisites(pid))

        self._prerequisite_cache[concept_id] = result
        return result

    def get_transfer_edge(self, source_id: str, target_id: str):
        c = self.concepts.get(source_id)
        if not c:
            return None
        for edge in c.transfers_to:
            if edge.target == target_id:
                return edge
        return None

    def get_graph_data(self, domains: list[str] | None = None, learner_states: dict | None = None):
        nodes = []
        edges = []

        for c in self.concepts.values():
            if domains and c.domain not in domains:
                continue

            node = {
                "id": c.id,
                "name": c.name,
                "domain": c.domain,
                "difficulty_tier": c.difficulty_tier,
                "status": "unknown",
                "mastery_score": 0.0,
            }
            if learner_states and c.id in learner_states:
                state = learner_states[c.id]
                node["status"] = state.get("status", "unknown")
                node["mastery_score"] = state.get("mastery_score", 0.0)
            nodes.append(node)

            for prereq in c.prerequisites:
                edges.append({"source": prereq, "target": c.id, "type": "prerequisite"})
            for te in c.transfers_to:
                edges.append({
                    "source": c.id,
                    "target": te.target,
                    "type": "transfer",
                    "strength": te.strength,
                })

        return {"nodes": nodes, "edges": edges}

    def compute_learning_path(
        self, target_concepts: set[str], mastered: set[str], learner_velocities: dict[str, float] | None = None
    ) -> list[dict]:
        velocities = learner_velocities or {}

        required = set()
        for cid in target_concepts:
            required.add(cid)
            required.update(self.get_all_prerequisites(cid))

        unmastered = required - mastered

        concept_weights = {}
        for cid in unmastered:
            c = self.concepts.get(cid)
            if not c:
                continue
            base = c.base_hours
            transfer_bonus = 0.0
            for mid in mastered:
                edge = self.get_transfer_edge(mid, cid)
                if edge:
                    transfer_bonus = max(transfer_bonus, edge.strength)
            vel = velocities.get(c.domain, 1.0)
            adjusted = base * (1.0 - transfer_bonus * 0.4) / max(vel, 0.1)
            concept_weights[cid] = adjusted

        return self._transfer_optimized_toposort(unmastered, concept_weights)

    def _transfer_optimized_toposort(self, concepts: set[str], weights: dict[str, float]) -> list[dict]:
        in_degree = {c: 0 for c in concepts}
        for cid in concepts:
            for prereq in self.get_prerequisites(cid):
                if prereq in concepts:
                    in_degree[cid] += 1

        queue = []
        for cid in concepts:
            if in_degree[cid] == 0:
                transfer_out = sum(
                    1 for other in concepts
                    if self.get_transfer_edge(cid, other)
                )
                heapq.heappush(queue, (-transfer_out, cid))

        result = []
        done = set()
        while queue:
            _, cid = heapq.heappop(queue)
            result.append({
                "concept_id": cid,
                "estimated_hours": round(weights.get(cid, 2.0), 1),
            })
            done.add(cid)

            for dep in concepts:
                if cid in self.get_prerequisites(dep) and dep not in done:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        transfer_out = sum(
                            1 for other in concepts
                            if self.get_transfer_edge(dep, other) and other not in done
                        )
                        heapq.heappush(queue, (-transfer_out, dep))

        return result


knowledge_graph = KnowledgeGraphService()
