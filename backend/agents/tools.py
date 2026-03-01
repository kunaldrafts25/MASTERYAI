import logging
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    handler: Callable | None = None


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_tool_descriptions(self) -> str:
        lines = []
        for t in self._tools.values():
            params = ", ".join(f"{k}: {v}" for k, v in t.parameters.items()) if t.parameters else "none"
            lines.append(f"- {t.name}({params}): {t.description}")
        return "\n".join(lines)


class ToolComposer:
    # breaks a natural language action into 1-3 primitive tool calls

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def compose(self, description: str, session, learner) -> list[dict]:
        from backend.services.llm_client import llm_client

        tool_descs = self.registry.get_tool_descriptions()

        system = f"""You are decomposing a teaching action into a sequence of tool calls.

Available tools:
{tool_descs}

Rules:
- Return 1-3 tool calls maximum
- Each tool call must use an available tool name
- Arguments must match the tool's expected parameters
- The sequence should achieve the described goal

Return JSON:
{{
    "steps": [
        {{"tool": "tool_name", "args": {{"param": "value"}}}},
    ],
    "reasoning": "Why this sequence achieves the goal"
}}"""

        prompt = f"""Goal: {description}
Current concept: {session.current_concept}
Mastered concepts: {[k for k, v in learner.concept_states.items() if v.status == 'mastered'][:10]}
Current state: {session.current_state}"""

        result = await llm_client.generate(prompt, system=system)
        steps = result.get("steps", [])

        # Validate: max 3 steps, all tools must exist
        validated = []
        for step in steps[:3]:
            tool_name = step.get("tool", "")
            if tool_name in self.registry._tools:
                validated.append(step)
            else:
                logger.warning("Compose: unknown tool '%s', skipping", tool_name)

        if not validated:
            validated = [{"tool": "teach", "args": {"concept_id": session.current_concept or ""}}]

        return validated


tool_registry = ToolRegistry()
