import logging
from backend.models.career import CareerRole, SkillRequirement
from backend.services.llm_client import llm_client
from backend.services.knowledge_graph import knowledge_graph
from backend.services.concept_generator import concept_generator

logger = logging.getLogger(__name__)


class CareerRoleGenerator:

    async def generate_role(self, role_description: str, level: str = "mid") -> tuple[CareerRole, dict]:
        existing_ids = sorted(c.id for c in knowledge_graph.get_all_concepts())

        system = (
            "You are an expert career and workforce analyst. Generate structured "
            "career role definitions that map to a knowledge graph of learning concepts. "
            "You must produce valid JSON matching the exact schema provided."
        )

        prompt = f"""Generate a career role definition for: {role_description}
TARGET LEVEL: {level} (entry | mid | senior)

EXISTING CONCEPT IDS IN THE KNOWLEDGE GRAPH (prefer these when mapping skills):
{chr(10).join(f'  - {cid}' for cid in existing_ids)}

For the role, provide:
- id: snake_case unique identifier (e.g., "quantitative_analyst", "devops_engineer")
- title: human-readable title
- description: 2-3 sentence description of the role
- level: one of "entry", "mid", "senior"
- required_skills: list of 3-5 skill groups, each with:
  - name: skill group name (e.g., "Python Fluency")
  - concept_ids: list of concept IDs (PREFER existing IDs listed above, but you may propose new ones using domain.concept_name format)
  - minimum_mastery: float 0.5-0.9
  - weight: float 0.0-1.0 (ALL weights across required_skills MUST sum to exactly 1.0)
- nice_to_have_skills: list of 0-2 optional skill groups (same format)
- market_demand: "high", "medium", or "low"
- salary_range: {{"min": int, "max": int, "currency": "USD"}}
- growth_trend: "growing", "stable", or "declining"
- related_roles: list of 1-3 related role IDs (snake_case)

CRITICAL RULES:
- Weights for required_skills MUST sum to 1.0
- Prefer existing concept IDs from the list above
- New concept IDs must follow domain.concept_name format (lowercase, underscores)
- Each skill group should have 2-10 concept IDs

Return JSON: {{"role": {{...}}}}"""

        result = await llm_client.generate(prompt=prompt, system=system)

        raw_role = result.get("role", result)
        role = self._parse_role(raw_role)
        metadata = await self._resolve_concepts(role)

        return role, metadata

    def _parse_role(self, raw: dict) -> CareerRole:
        required_skills = []
        for skill_raw in raw.get("required_skills", []):
            required_skills.append(SkillRequirement(
                name=skill_raw.get("name", "Unknown Skill"),
                concept_ids=skill_raw.get("concept_ids", []),
                minimum_mastery=max(0.5, min(0.9, float(skill_raw.get("minimum_mastery", 0.7)))),
                weight=max(0.0, min(1.0, float(skill_raw.get("weight", 0.25)))),
            ))

        nice_to_have = []
        for skill_raw in raw.get("nice_to_have_skills", []):
            nice_to_have.append(SkillRequirement(
                name=skill_raw.get("name", "Optional Skill"),
                concept_ids=skill_raw.get("concept_ids", []),
                minimum_mastery=max(0.3, min(0.7, float(skill_raw.get("minimum_mastery", 0.5)))),
                weight=max(0.0, min(0.5, float(skill_raw.get("weight", 0.05)))),
            ))

        # Normalize required_skills weights to sum to 1.0
        total_weight = sum(s.weight for s in required_skills)
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            for s in required_skills:
                s.weight = round(s.weight / total_weight, 2)
            if required_skills:
                diff = 1.0 - sum(s.weight for s in required_skills)
                required_skills[-1].weight = round(required_skills[-1].weight + diff, 2)

        return CareerRole(
            id=raw.get("id", "generated_role"),
            title=raw.get("title", "Generated Role"),
            description=raw.get("description", ""),
            level=raw.get("level", "mid"),
            required_skills=required_skills,
            nice_to_have_skills=nice_to_have,
            market_demand=raw.get("market_demand", "medium"),
            salary_range=raw.get("salary_range", {}),
            growth_trend=raw.get("growth_trend", "stable"),
            related_roles=raw.get("related_roles", []),
        )

    async def _resolve_concepts(self, role: CareerRole) -> dict:
        all_concept_ids = set()
        for skill in role.required_skills + role.nice_to_have_skills:
            all_concept_ids.update(skill.concept_ids)

        mapped = set()
        missing = set()
        for cid in all_concept_ids:
            if knowledge_graph.get_concept(cid):
                mapped.add(cid)
            else:
                missing.add(cid)

        generated = set()
        unmapped = set()

        if missing:
            by_domain = {}
            for cid in missing:
                parts = cid.split(".", 1)
                domain = parts[0] if len(parts) > 1 else "general"
                by_domain.setdefault(domain, []).append(cid)

            for domain, concept_ids in by_domain.items():
                try:
                    existing_domain = [
                        c for c in knowledge_graph.get_all_concepts()
                        if c.domain == domain
                    ]

                    if existing_domain:
                        parent = existing_domain[0]
                        new_concepts = await concept_generator.expand_concept(
                            parent, direction="lateral"
                        )
                    else:
                        topic = domain.replace("_", " ")
                        new_concepts = await concept_generator.generate_concept_tree(
                            topic=topic, depth=max(6, len(concept_ids))
                        )

                    if new_concepts:
                        knowledge_graph.add_concepts(new_concepts)
                        generated_ids = {c.id for c in new_concepts}
                        generated.update(generated_ids & missing)
                        still_missing = set(concept_ids) - generated_ids
                        unmapped.update(still_missing)
                    else:
                        unmapped.update(concept_ids)
                except Exception as e:
                    logger.warning(f"concept generation failed for domain {domain}: {e}")
                    unmapped.update(concept_ids)

        # Remove unmapped concept IDs from the role's skills
        if unmapped:
            for skill in role.required_skills + role.nice_to_have_skills:
                skill.concept_ids = [cid for cid in skill.concept_ids if cid not in unmapped]
            role.required_skills = [s for s in role.required_skills if s.concept_ids]

        total = len(all_concept_ids)
        coverage = (len(mapped) + len(generated)) / total if total > 0 else 1.0

        return {
            "concepts_mapped": len(mapped),
            "concepts_generated": len(generated),
            "concepts_unmapped": len(unmapped),
            "unmapped_ids": sorted(unmapped),
            "coverage_ratio": round(coverage, 2),
        }


career_role_generator = CareerRoleGenerator()
