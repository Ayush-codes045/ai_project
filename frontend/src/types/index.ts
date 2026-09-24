export type AgentType = "planner" | "coder" | "reviewer"
  | "tester" | "orchestrator";

export type EventType = "started" | "thinking" | "action" |
  "completed" | "error" | "status" | "message" | "token";

export interface ModelInfo {
  id: string;
  input_per_1k: number;
  output_per_1k: number;
  is_default: boolean;
}

export interface ModelsResponse {
  models: ModelInfo[];
  default: string;
  budget_cap_usd: number;
}

export interface AgentEvent {
  agent: AgentType;
  event_type: EventType;
  message: string;
  data?: Record<string, unknown>;
}

export interface CodeFile {
  path: string;
  content: string;
  language: string;
}

export interface ReviewIssue {
  severity: "critical" | "warning" | "info";
  file_path: string;
  line_number?: number;
  message: string;
  suggestion?: string;
}

export interface TestResult {
  test_name: string;
  passed: boolean;
  output: string;
  error?: string;
}

export interface PlanStep {
  step_number: number;
  title: string;
  description: string;
  file_path?: string;
}

export interface TokenUsage {
  agent: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface TaskMetrics {
  total_tokens: number;
  total_cost_usd: number;
  time_taken_seconds: number;
  review_iterations: number;
  files_generated: number;
  tests_passed: number;
  tests_failed: number;
  lines_of_code: number;
  token_breakdown: TokenUsage[];
}

export interface AgentMessage {
  agent: AgentType;
  to_agent?: AgentType;
  message: string;
  message_type: "info" | "request" | "response" | "handoff";
  timestamp?: string;
}

export interface TaskData {
  task_description: string;
  language: string;
  plan: PlanStep[];
  code_files: CodeFile[];
  review_issues: ReviewIssue[];
  test_results: TestResult[];
  metrics: TaskMetrics;
  conversation: AgentMessage[];
  iteration: number;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  data?: TaskData;
  error?: string;
}

export interface HistoryItem {
  task_id: string;
  description: string;
  status: string;
  language: string;
  files_count: number;
  total_tokens: number;
  cost_usd: number;
  created_at: string;
}