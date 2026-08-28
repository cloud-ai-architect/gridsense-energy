"""Main agent for GridSense."""

from src.common import BaseAgent, GridsenseTask


SYSTEM_PROMPT = """You are GridSense, an expert agent.

Your job: handle the task at hand using the tools available to you.
Be specific, accurate, and concise.
"""


class GridsenseAgent(BaseAgent):
    NAME = "langgraph"

    def handle(self, task: GridsenseTask, message: str = "") -> str:
        return self.invoke_claude(
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message or "Begin."}],
        )
