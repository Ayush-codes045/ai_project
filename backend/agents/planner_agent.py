import json
from .base_agent import BaseAgent
from .json_utils import extract_json
from models.schemas import AgentType, PlanStep


SYSTEM_PROMPT = """You are a senior software architect. Your job is to break down a user's software task into clear, actionable implementation steps.

Rules:
1. Break the task into 3-7 concrete steps
2. Each step should produce one or more files
3. Order steps logically (dependencies first)
4. Include file paths for each step
5. Be specific about what each file should contain
6. Consider error handling and edge cases

You MUST respond with valid JSON in this exact format:
{
    "plan": [
        {
            "step_number": 1,
            "title": "Short title",
            "description": "Detailed description of what to implement",
            "file_path": "path/to/file.py"
        }
    ],
    "summary": "Brief overview of the approach"
}"""


class PlannerAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            agent_type=AgentType.PLANNER,
            system_prompt=SYSTEM_PROMPT,
            model=model,
            json_mode=True,
        )

    async def create_plan(self, task_description: str, event_callback=None, language: str = "python") -> list[PlanStep]:
        """Takes a task description and returns a structured plan."""
        messages = [
            {"role": "user", "content": f"Create an implementation plan for: {task_description}\n\nTarget language: {language}\nUse appropriate file extensions and conventions."}
        ]

        result = await self.run(messages, event_callback)
        content = result["content"]

        # Parse JSON from response (robust against markdown fences / prose)
        try:
            parsed = extract_json(content)
            steps = [PlanStep(**step) for step in parsed["plan"]]
            return steps
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.emit_event("error", f"Failed to parse plan: {str(e)}")
            return []