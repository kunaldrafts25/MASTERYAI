from dataclasses import dataclass, field
from typing import Callable, Any


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


tool_registry = ToolRegistry()
