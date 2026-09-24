import json
from .base_agent import BaseAgent
from .json_utils import extract_json
from models.schemas import AgentType, CodeFile, TestResult


SYSTEM_PROMPT = """You are a QA engineer who writes comprehensive test cases.

Your job is to:
1. Write unit tests for the given code
2. Cover edge cases and error scenarios
3. Use appropriate testing frameworks (pytest for Python, jest for JS, etc.)
4. Make tests clear and descriptive

You MUST respond with valid JSON in this exact format:
{
    "test_files": [
        {
            "path": "test_filename.py",
            "content": "full test file content",
            "language": "python"
        }
    ],
    "test_commands": ["pytest test_filename.py -v"]
}"""


class TesterAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            agent_type=AgentType.TESTER,
            system_prompt=SYSTEM_PROMPT,
            model=model,
            json_mode=True,
        )

    async def generate_tests(self, code_files: list[CodeFile], task_description: str, event_callback=None) -> tuple[list[CodeFile], list[str]]:
        """Generate test files and return them with test commands."""
        prompt = f"Write tests for the following code (task: {task_description}):\n\n"

        for file in code_files:
            prompt += f"--- {file.path} ({file.language}) ---\n"
            prompt += f"```{file.language}\n{file.content}\n```\n\n"

        messages = [{"role": "user", "content": prompt}]
        result = await self.run(messages, event_callback)
        content = result["content"]

        try:
            parsed = extract_json(content)
            test_files = [CodeFile(**f) for f in parsed.get("test_files", [])]
            test_commands = parsed.get("test_commands", [])
            return test_files, test_commands
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.emit_event("error", f"Failed to parse tests: {str(e)}")
            return [], []

    def parse_test_output(self, output: str) -> list[TestResult]:
        """Parse test execution output into structured results."""
        results = []
        lines = output.strip().split("\n")

        for line in lines:
            if "PASSED" in line or "FAILED" in line:
                test_name = line.split("::")[0] if "::" in line else line
                passed = "PASSED" in line
                results.append(TestResult(
                    test_name=test_name,
                    passed=passed,
                    output=line,
                    error=None if passed else line,
                ))

        # If no structured output found, create a single result
        if not results:
            passed = "error" not in output.lower() and "failed" not in output.lower()
            results.append(TestResult(
                test_name="test_suite",
                passed=passed,
                output=output[:500],
                error=None if passed else output[:500],
            ))

        return results