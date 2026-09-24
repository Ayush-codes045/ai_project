import json
from .base_agent import BaseAgent
from .json_utils import extract_json
from models.schemas import AgentType, ReviewIssue, CodeFile


SYSTEM_PROMPT = """You are a senior code reviewer with expertise in security, performance, and best practices.

Your job is to review code and identify:
1. Bugs and logical errors
2. Security vulnerabilities (injection, XSS, hardcoded secrets, etc.)
3. Performance issues
4. Code style and readability problems
5. Missing error handling

Be thorough but fair. Only flag real issues, not style preferences.

You MUST respond with valid JSON in this exact format:
{
    "issues": [
        {
            "severity": "critical|warning|info",
            "file_path": "filename.py",
            "line_number": 10,
            "message": "Description of the issue",
            "suggestion": "How to fix it"
        }
    ],
    "summary": "Overall assessment",
    "approved": true/false
}

Set "approved" to true if the code is ready (minor issues only), false if critical issues exist."""


class ReviewerAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            agent_type=AgentType.REVIEWER,
            system_prompt=SYSTEM_PROMPT,
            model=model,
            json_mode=True,
        )

    async def review_code(self, code_files: list[CodeFile], task_description: str, event_callback=None) -> tuple[list[ReviewIssue], bool]:
        """Review code files and return issues + approval status."""
        prompt = f"Review the following code for the task: {task_description}\n\n"

        for file in code_files:
            prompt += f"--- {file.path} ({file.language}) ---\n"
            prompt += f"```{file.language}\n{file.content}\n```\n\n"

        messages = [{"role": "user", "content": prompt}]
        result = await self.run(messages, event_callback)
        content = result["content"]

        try:
            parsed = extract_json(content)
            issues = [ReviewIssue(**issue) for issue in parsed.get("issues", [])]
            approved = parsed.get("approved", False)
            return issues, approved
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.emit_event("error", f"Failed to parse review: {str(e)}")
            return [], True  # Approve if parsing fails to avoid infinite loops