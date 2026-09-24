import time
from models.schemas import (
    PlanStep, CodeFile, ReviewIssue, TestResult,
    TaskMetrics, TokenUsage, AgentMessage
)


class SharedMemory:
    """Shared context/memory between agents in a single task execution."""

    def __init__(self, task_description: str, language: str = "python"):
        self.task_description = task_description
        self.language = language
        self.plan: list[PlanStep] = []
        self.code_files: list[CodeFile] = []
        self.review_issues: list[ReviewIssue] = []
        self.test_files: list[CodeFile] = []
        self.test_results: list[TestResult] = []
        self.test_commands: list[str] = []
        self.iteration: int = 0
        self.max_iterations: int = 3
        self.conversation: list[AgentMessage] = []

        # Metrics
        self.start_time: float = time.time()
        self.end_time: float = 0
        self.token_breakdown: list[TokenUsage] = []

    def add_conversation_message(self, message: AgentMessage):
        """Add a message to the agent conversation log."""
        self.conversation.append(message)

    def get_code_context(self) -> str:
        """Get all generated code as a string for context."""
        context = ""
        for file in self.code_files:
            context += f"\n--- {file.path} ---\n{file.content}\n"
        return context

    def get_review_feedback(self) -> str:
        """Get review issues formatted as feedback for the coder."""
        if not self.review_issues:
            return ""
        feedback = "Fix the following issues:\n"
        for issue in self.review_issues:
            feedback += f"- [{issue.severity}] {issue.file_path}"
            if issue.line_number:
                feedback += f" (line {issue.line_number})"
            feedback += f": {issue.message}\n"
            if issue.suggestion:
                feedback += f"  Suggestion: {issue.suggestion}\n"
        return feedback

    def get_test_feedback(self) -> str:
        """Get test failures formatted as feedback for the coder."""
        failures = [t for t in self.test_results if not t.passed]
        if not failures:
            return ""
        feedback = "Fix the following test failures:\n"
        for test in failures:
            feedback += f"- {test.test_name}: {test.error}\n"
        return feedback

    def get_metrics(self) -> TaskMetrics:
        """Calculate and return task metrics."""
        total_input = sum(t.input_tokens for t in self.token_breakdown)
        total_output = sum(t.output_tokens for t in self.token_breakdown)
        total_cost = sum(t.cost_usd for t in self.token_breakdown)
        total_loc = sum(
            len(f.content.split("\n")) for f in self.code_files
        )

        # Test files are appended to 'code_files' during execution, so counting
        # both 'code_files' and 'test_files' would double-count them. We de-dupe
        # by file path to report an accurate total.
        unique_paths = {f.path for f in self.code_files}
        unique_paths.update(f.path for f in self.test_files)

        return TaskMetrics(
            total_tokens=total_input + total_output,
            total_cost_usd=round(total_cost, 4),
            time_taken_seconds=round(self.end_time - self.start_time, 1) if self.end_time else round(time.time() - self.start_time, 1),
            review_iterations=self.iteration,
            files_generated=len(unique_paths),
            tests_passed=sum(1 for t in self.test_results if t.passed),
            tests_failed=sum(1 for t in self.test_results if not t.passed),
            lines_of_code=total_loc,
            token_breakdown=self.token_breakdown,
        )

    def to_dict(self) -> dict:
        """Serialize memory state for API responses."""
        return {
            "task_description": self.task_description,
            "language": self.language,
            "plan": [step.model_dump() for step in self.plan],
            "code_files": [f.model_dump() for f in self.code_files],
            "review_issues": [i.model_dump() for i in self.review_issues],
            "test_results": [t.model_dump() for t in self.test_results],
            "metrics": self.get_metrics().model_dump(),
            "conversation": [m.model_dump() for m in self.conversation],
            "iteration": self.iteration,
        }