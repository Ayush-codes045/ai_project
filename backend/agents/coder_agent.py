import json
from .base_agent import BaseAgent
from .json_utils import extract_json
from models.schemas import AgentType, CodeFile, PlanStep


SYSTEM_PROMPT = """You are an expert software developer. Your job is to write clean, production-quality code based on the given plan steps.

Rules:
1. Write complete, working code (no placeholders or TODOs)
2. Follow best practices for the language being used
3. Include proper imports and dependencies
4. Add brief comments only where logic is complex
5. Handle edge cases and errors appropriately

You MUST respond with valid JSON in this exact format:
{
    "files": [
        {
            "path": "filename.py",
            "content": "full file content here",
            "language": "python"
        }
    ]
}

Write ALL necessary files to make the code functional."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new code file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "File content"},
                    "language": {"type": "string", "description": "Programming language"},
                },
                "required": ["path", "content", "language"],
            },
        },
    }
]


class CoderAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            agent_type=AgentType.CODER,
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            model=model,
        )
        self.generated_files: list[CodeFile] = []

    async def handle_tool_call(self, function_name: str, arguments: dict) -> dict:
        if function_name == "create_file":
            file = CodeFile(
                path=arguments["path"],
                content=arguments["content"],
                language=arguments.get("language", "python"),
            )
            self.generated_files.append(file)
            return {"status": "success", "message": f"Created {file.path}"}
        return {"error": f"Unknown tool: {function_name}"}

    async def generate_code(
        self,
        plan_steps: list[PlanStep],
        context: str = "",
        review_feedback: str = "",
        event_callback=None,
    ) -> list[CodeFile]:
        """Generate code based on plan steps."""
        self.generated_files = []

        prompt = f"Implement the following plan:\n\n"
        for step in plan_steps:
            prompt += f"Step {step.step_number}: {step.title}\n"
            prompt += f"  Description: {step.description}\n"
            if step.file_path:
                prompt += f"  File: {step.file_path}\n"
            prompt += "\n"

        if context:
            prompt += f"\nExisting context:\n{context}\n"

        if review_feedback:
            prompt += f"\nFix these review issues:\n{review_feedback}\n"

        messages = [{"role": "user", "content": prompt}]
        result = await self.run(messages, event_callback)

        # If files were created via tool calls, return those
        if self.generated_files:
            return self.generated_files

        # Otherwise parse from JSON response (robust against markdown / prose)
        content = result["content"]
        try:
            parsed = extract_json(content)
            return [CodeFile(**f) for f in parsed["files"]]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.emit_event("error", "Failed to parse code output")
            return []