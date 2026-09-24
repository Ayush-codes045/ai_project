from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime


class AgentType(str, Enum):
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    ORCHESTRATOR = "orchestrator"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    CODING = "coding"
    REVIEWING = "reviewing"
    TESTING = "testing"
    FIXING = "fixing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskRequest(BaseModel):
    description: str
    language: str = "python"  # Target programming language
    model: Optional[str] = None  # Override the LLM model for this task
    budget_cap_usd: Optional[float] = None  # Optional per-task USD budget cap


class PlanStep(BaseModel):
    step_number: int
    title: str
    description: str
    file_path: Optional[str] = None


class CodeFile(BaseModel):
    path: str
    content: str
    language: str


class ReviewIssue(BaseModel):
    severity: str  # "critical", "warning", "info"
    file_path: str
    line_number: Optional[int] = None
    message: str
    suggestion: Optional[str] = None


class TestResult(BaseModel):
    test_name: str
    passed: bool
    output: str
    error: Optional[str] = None


class TokenUsage(BaseModel):
    agent: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class AgentMessage(BaseModel):
    """Represents a message in the agent conversation."""
    agent: AgentType
    to_agent: Optional[AgentType] = None
    message: str
    message_type: str = "info"  # "info", "request", "response", "handoff"
    timestamp: Optional[str] = None


class AgentEvent(BaseModel):
    agent: AgentType
    event_type: str  # "started", "thinking", "action", "completed", "error", "message"
    message: str
    data: Optional[dict] = None


class TaskMetrics(BaseModel):
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    time_taken_seconds: float = 0.0
    review_iterations: int = 0
    files_generated: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    lines_of_code: int = 0
    token_breakdown: list[TokenUsage] = []


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    description: str = ""
    language: str = "python"
    plan: Optional[list[PlanStep]] = None
    code_files: Optional[list[CodeFile]] = None
    review_issues: Optional[list[ReviewIssue]] = None
    test_results: Optional[list[TestResult]] = None
    metrics: Optional[TaskMetrics] = None
    conversation: Optional[list[AgentMessage]] = None
    created_at: Optional[str] = None


class TaskHistoryItem(BaseModel):
    task_id: str
    description: str
    status: str
    language: str
    files_count: int
    total_tokens: int
    cost_usd: float
    created_at: str