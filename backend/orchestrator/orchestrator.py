import time
import uuid
from typing import Callable, Awaitable
from datetime import datetime

from agents import PlannerAgent, CoderAgent, ReviewerAgent, TesterAgent
from sandbox import SandboxExecutor
from models.schemas import AgentEvent, AgentMessage, AgentType, TaskStatus
from .memory import SharedMemory
from config import settings

_MEMORY_CACHE_MAX = 200


class Orchestrator:
    """
    State machine that coordinates the multi-agent workflow.

    Flow: Plan -> Code -> Review -> (Fix if needed) -> Test -> (Fix if needed) -> Done
    Includes inter-agent conversation tracking and metrics.
    """

    def __init__(self):
        self.tasks: dict[str, SharedMemory] = {}

    def _evict_oldest_tasks(self):
        """Drop the oldest completed-task memory once the cache exceeds its limit."""
        while len(self.tasks) > _MEMORY_CACHE_MAX:
            self.tasks.pop(next(iter(self.tasks)))

    def _log_handoff(self, memory: SharedMemory, from_agent: AgentType, to_agent: AgentType, message: str):
        """Log a handoff message between agents."""
        memory.add_conversation_message(AgentMessage(
            agent=from_agent,
            to_agent=to_agent,
            message=message,
            message_type="handoff",
            timestamp=datetime.now().isoformat(),
        ))

    def _log_agent_message(self, memory: SharedMemory, agent: AgentType, message: str, msg_type: str = "info"):
        """Log an agent's internal message."""
        memory.add_conversation_message(AgentMessage(
            agent=agent,
            message=message,
            message_type=msg_type,
            timestamp=datetime.now().isoformat(),
        ))

    def _current_cost(self, memory: SharedMemory) -> float:
        """Total USD spent so far across all recorded token usage."""
        return round(sum(t.cost_usd for t in memory.token_breakdown), 4)

    def _budget_exceeded(self, memory: SharedMemory, budget_cap_usd: float) -> bool:
        """Whether the running cost has exceeded the configured budget cap."""
        if not budget_cap_usd or budget_cap_usd <= 0:
            return False
        return self._current_cost(memory) >= budget_cap_usd

    async def execute_task(
        self,
        task_description: str,
        language: str = "python",
        event_callback: Callable[[AgentEvent], Awaitable[None]] = None,
        task_id: str = None,
        model: str = None,
        budget_cap_usd: float = None,
    ) -> dict:
        """Execute a full task through the agent pipeline.
        
        If a `task_id` is supplied by the caller (e.g. the API layer that also
        manages the WebSocket channel and history), it is reused so that events,
        results and persistence all share the same identifier. Otherwise a new
        id is generated.

        `model` selects the LLM for every agent in this task. `budget_cap_usd`
        optionally halts execution early once the running cost exceeds the cap.
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        model = model or settings.OPENAI_MODEL
        if budget_cap_usd is None:
            budget_cap_usd = settings.BUDGET_CAP_USD
        memory = SharedMemory(task_description, language)

        self.tasks[task_id] = memory
        self._evict_oldest_tasks()

        # Create fresh agents for each task, all using the selected model
        planner = PlannerAgent(model=model)
        coder = CoderAgent(model=model)
        reviewer = ReviewerAgent(model=model)
        tester = TesterAgent(model=model)

        try:
            # === Phase 1: Planning ===
            await self._emit_status(event_callback, TaskStatus.PLANNING, "Starting planning phase...")
            self._log_agent_message(
                memory, AgentType.ORCHESTRATOR,
                f"New task received: '{task_description}'. Assigning to Planner Agent.",
                "info"
            )
            self._log_handoff(
                memory, AgentType.ORCHESTRATOR, AgentType.PLANNER,
                f"Please break down this task into implementation steps: {task_description}"
            )

            memory.plan = await planner.create_plan(task_description, event_callback, language)

            if not memory.plan:
                await self._emit_status(event_callback, TaskStatus.FAILED, "Planning failed - could not generate a plan")
                return {"task_id": task_id, "status": "failed", "error": "Planning failed"}

            # Log planner output
            plan_summary = ", ".join([f"{s.step_number}. {s.title}" for s in memory.plan])
            self._log_agent_message(
                memory, AgentType.PLANNER,
                f"Plan created with {len(memory.plan)} steps: {plan_summary}",
                "response"
            )
            memory.token_breakdown.append(planner.token_usage)

            # === Phase 2: Coding ===
            await self._emit_status(event_callback, TaskStatus.CODING, "Generating code...")
            self._log_handoff(
                memory, AgentType.PLANNER, AgentType.CODER,
                f"Here's the plan with {len(memory.plan)} steps. Please implement each step."
            )

            memory.code_files = await coder.generate_code(
                memory.plan, event_callback=event_callback
            )

            if not memory.code_files:
                await self._emit_status(event_callback, TaskStatus.FAILED, "Code generation failed")
                return {"task_id": task_id, "status": "failed", "error": "Code generation failed"}

            files_list = ", ".join([f.path for f in memory.code_files])
            self._log_agent_message(
                memory, AgentType.CODER,
                f"Code generated: {files_list} ({sum(len(f.content.split(chr(10))) for f in memory.code_files)} lines total)",
                "response"
            )
            memory.token_breakdown.append(coder.token_usage)

            # === Phase 3: Review loop ===
            for iteration in range(settings.MAX_ITERATIONS):
                # Stop early if we've blown the budget
                if self._budget_exceeded(memory, budget_cap_usd):
                    self._log_agent_message(
                        memory, AgentType.ORCHESTRATOR,
                        f"Budget cap of ${budget_cap_usd} reached (spent ${self._current_cost(memory)}). "
                        f"Stopping review loop early.",
                        "info"
                    )
                    break

                memory.iteration = iteration + 1

                await self._emit_status(event_callback, TaskStatus.REVIEWING, f"Review iteration {iteration + 1}...")
                
                self._log_handoff(
                    memory, AgentType.CODER, AgentType.REVIEWER,
                    f"Code is ready for review. {len(memory.code_files)} files generated."
                )

                issues, approved = await reviewer.review_code(
                    memory.code_files, task_description, event_callback
                )
                memory.review_issues = issues
                memory.token_breakdown.append(reviewer.token_usage)

                if approved:
                    self._log_agent_message(
                        memory, AgentType.REVIEWER,
                        f"Code approved! Found {len(issues)} minor issues (non-blocking).",
                        "response"
                    )
                    break
                
                # Not approved - need fixes
                critical_count = sum(1 for i in issues if i.severity == "critical")
                self._log_agent_message(
                    memory, AgentType.REVIEWER,
                    f"Code NOT approved. Found {len(issues)} issues ({critical_count} critical). Sending back for fixes.",
                    "response"
                )
                
                self._log_handoff(
                    memory, AgentType.REVIEWER, AgentType.CODER,
                    f"Please fix these {len(issues)} issues: {memory.get_review_feedback()[:200]}..."
                )

                # Fix issues
                await self._emit_status(event_callback, TaskStatus.FIXING, f"Fixing {len(issues)} issues...")

                # Create fresh coder for fix iteration (same model as the task)
                fix_coder = CoderAgent(model=model)
                memory.code_files = await fix_coder.generate_code(
                    memory.plan,
                    context=memory.get_code_context(),
                    review_feedback=memory.get_review_feedback(),
                    event_callback=event_callback,
                )
                memory.token_breakdown.append(fix_coder.token_usage)
                
                self._log_agent_message(
                    memory, AgentType.CODER,
                    f"Fixed {len(issues)} issues. Code updated.",
                    "response"
                )

            # === Phase 4: Testing ===
            await self._emit_status(event_callback, TaskStatus.TESTING, "Generating tests...")
            self._log_handoff(
                memory, AgentType.REVIEWER, AgentType.TESTER,
                "Code is approved. Please write comprehensive tests."
            )

            test_files, test_commands = await tester.generate_tests(
                memory.code_files, task_description, event_callback
            )
            memory.test_files = test_files
            memory.test_commands = test_commands
            memory.token_breakdown.append(tester.token_usage)

            if test_files:
                self._log_agent_message(
                    memory, AgentType.TESTER,
                    f"Generated {len(test_files)} test file(s). Commands: {', '.join(test_commands)}",
                    "response"
                )

                # Add test files to code_files for complete output
                memory.code_files.extend(test_files)

                sandbox = SandboxExecutor()

                # === Phase 4.5: Self-healing test loop ===
                # Run tests; if any fail, hand the failures back to the Coder to
                # fix, then re-run. Repeat up to MAX_TEST_FIX_ITERATIONS times or
                # until all tests pass / budget is exhausted.
                for test_attempt in range(settings.MAX_TEST_FIX_ITERATIONS + 1):
                    await self._emit_status(
                        event_callback, TaskStatus.TESTING,
                        f"Running tests in sandbox (attempt {test_attempt + 1})..."
                    )
                    self._log_agent_message(
                        memory, AgentType.TESTER,
                        "Executing tests in sandboxed environment...",
                        "info"
                    )

                    # Fresh results for this attempt
                    memory.test_results = []
                    all_files = memory.code_files # includes test files

                    for command in test_commands:
                        exec_result = await sandbox.execute_code(all_files, command)
                        output = exec_result["stdout"] + "\n" + exec_result["stderr"]

                        test_results = tester.parse_test_output(output)
                        memory.test_results.extend(test_results)

                        engine = exec_result.get("engine", "unknown")
                        passed = sum(1 for t in test_results if t.passed)
                        failed = sum(1 for t in test_results if not t.passed)

                        self._log_agent_message(
                            memory, AgentType.TESTER,
                            f"Tests executed ({engine}): {passed} passed, {failed} failed",
                            "response"
                        )
                        
                        if event_callback:
                            await event_callback(AgentEvent(
                                agent=AgentType.TESTER,
                                event_type="action",
                                message=f"Test results: {passed} passed, {failed} failed",
                                data={"passed": passed, "failed": failed, "engine": engine},
                            ))

                    # All passing? We're done.
                    failures = [t for t in memory.test_results if not t.passed]
                    if not failures:
                        if test_attempt > 0:
                            self._log_agent_message(
                                memory, AgentType.ORCHESTRATOR,
                                f"All tests passing after {test_attempt} fix iteration(s).",
                                "info"
                            )
                        break

                    # No more fix attempts left, or budget exhausted -> stop.
                    if test_attempt >= settings.MAX_TEST_FIX_ITERATIONS:
                        self._log_agent_message(
                            memory, AgentType.ORCHESTRATOR,
                            f"{len(failures)} test(s) still failing after "
                            f"{settings.MAX_TEST_FIX_ITERATIONS} fix attempt(s). Reporting as-is.",
                            "info"
                        )
                        break
                    if self._budget_exceeded(memory, budget_cap_usd):
                        self._log_agent_message(
                            memory, AgentType.ORCHESTRATOR,
                            f"Budget cap of ${budget_cap_usd} reached. Skipping further test fixes.",
                            "info"
                        )
                        break
                    
                    # === Self-heal: hand failures back to the Coder ===
                    await self._emit_status(
                        event_callback, TaskStatus.FIXING,
                        f"Auto-fixing {len(failures)} failing test(s)..."
                    )
                    self._log_handoff(
                        memory, AgentType.TESTER, AgentType.CODER,
                        f"{len(failures)} test(s) failed. Please fix the implementation "
                        f"so these tests pass."
                    )

                    test_fix_coder = CoderAgent(model=model)
                    combined_feedback = (
                        memory.get_review_feedback() + "\n" + memory.get_test_feedback()
                    ).strip()
                    memory.code_files = await test_fix_coder.generate_code(
                        memory.plan,
                        context=memory.get_code_context(),
                        review_feedback=combined_feedback,
                        event_callback=event_callback,
                    )
                    memory.token_breakdown.append(test_fix_coder.token_usage)

                    # Re-attach test files (regenerated code_files replaced them)
                    existing_paths = {f.path for f in memory.code_files}
                    for tf in test_files:
                        if tf.path not in existing_paths:
                            memory.code_files.append(tf)

                    self._log_agent_message(
                        memory, AgentType.CODER,
                        f"Applied fixes for {len(failures)} failing test(s). Re-running tests...",
                        "response"
                    )

            # === Phase 5: Complete ===

            memory.end_time = time.time()
            metrics = memory.get_metrics()

            await self._emit_status(event_callback, TaskStatus.COMPLETED, "Task completed successfully!")
            self._log_agent_message(
                memory, AgentType.ORCHESTRATOR,
                f"Task complete! Generated {metrics.files_generated} files, "
                f"{metrics.lines_of_code} lines of code in {metrics.time_taken_seconds}s. "
                f"Cost: ${metrics.total_cost_usd}",
                "info"
            )

            return {
                "task_id": task_id,
                "status": "completed",
                "data": memory.to_dict(),
            }

        except Exception as e:
            memory.end_time = time.time()
            await self._emit_status(event_callback, TaskStatus.FAILED, f"Error: {str(e)}")
            self._log_agent_message(
                memory, AgentType.ORCHESTRATOR,
                f"Task failed with error: {str(e)}",
                "info"
            )
            return {"task_id": task_id, "status": "failed", "error": str(e)}

    async def _emit_status(self, callback, status: TaskStatus, message: str):
        """Emit a status update event."""
        if callback:
            event = AgentEvent(
                agent=AgentType.ORCHESTRATOR,
                event_type="status",
                message=message,
                data={"status": status.value},
            )
            await callback(event)

    def get_task_status(self, task_id: str) -> dict | None:
        """Get current state of a task."""
        memory = self.tasks.get(task_id)
        if not memory:
            return None
        return memory.to_dict()