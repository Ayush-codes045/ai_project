import json
import asyncio
from openai import AsyncOpenAI
from config import settings, get_model_pricing, supports_json_mode
from models.schemas import AgentEvent, AgentType, TokenUsage, AgentMessage


class BaseAgent:
    """Base class for all AI agents. Handles async OpenAI API communication with
    token tracking, per-model cost accounting, retry logic, optional JSON mode,
    and token-by-token streaming to the UI."""

    def __init__(
        self,
        agent_type: AgentType,
        system_prompt: str,
        tools: list[dict] = None,
        model: str = None,
        json_mode: bool = False,
    ):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model or settings.OPENAI_MODEL
        self.json_mode = json_mode
        self.events: list[AgentEvent] = []
        self.messages_log: list[AgentMessage] = []

        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @property
    def token_usage(self) -> TokenUsage:
        pricing = get_model_pricing(self.model)
        cost = (
            (self.total_input_tokens / 1000) * pricing["input"]
            + (self.total_output_tokens / 1000) * pricing["output"]
        )
        return TokenUsage(
            agent=self.agent_type.value,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            cost_usd=round(cost, 4),
        )

    def emit_event(self, event_type: str, message: str, data: dict = None) -> AgentEvent:
        event = AgentEvent(
            agent=self.agent_type,
            event_type=event_type,
            message=message,
            data=data,
        )
        self.events.append(event)
        return event

    def log_message(self, message: str, to_agent: AgentType = None, message_type: str = "info") -> AgentMessage:
        """Log an inter-agent message for the conversation view."""
        from datetime import datetime
        msg = AgentMessage(
            agent=self.agent_type,
            to_agent=to_agent,
            message=message,
            message_type=message_type,
            timestamp=datetime.now().isoformat(),
        )
        self.messages_log.append(msg)
        return msg

    async def _call_openai_with_retry(self, **kwargs) -> object:
        """Call OpenAI API with exponential backoff retry on rate limits."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                return response
            except Exception as e:
                error_str = str(e)
                # Retry on rate limit (429) or server errors (5xx)
                if ("429" in error_str or "500" in error_str or "503" in error_str) and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1  # 2s, 5s
                    self.emit_event("thinking", f"Rate limited, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def _stream_completion(self, event_callback=None, **kwargs) -> object:
        """Stream a chat completion token-by-token, emitting 'token' events.

        Returns an object exposing `.content` and `.usage` compatible with the
        non-streaming path so callers can treat both uniformly. Tool calls are
        not streamed (tool-enabled requests fall back to a normal call).
        Retries on rate-limit (429) and server errors (5xx) like the blocking path.
        """
        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                content_parts: list[str] = []
                usage = None

                stream = await self.client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    if chunk.usage:
                        usage = chunk.usage
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    token = getattr(delta, "content", None)
                    if token:
                        content_parts.append(token)
                        if event_callback:
                            await event_callback(AgentEvent(
                                agent=self.agent_type,
                                event_type="token",
                                message=token,
                                data={"streaming": True},
                            ))

                full_content = "".join(content_parts)

                class _StreamResult:
                    def __init__(self, content, usage):
                        self.content = content
                        self.usage = usage

                return _StreamResult(full_content, usage)

            except Exception as e:
                error_str = str(e)
                if ("429" in error_str or "500" in error_str or "503" in error_str) and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    self.emit_event("thinking", f"Rate limited, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def run(self, messages: list[dict], event_callback=None) -> dict:
        """Execute the agent with given messages. Returns the assistant's response."""
        self.events = []
        self.emit_event("started", f"{self.agent_type.value} agent started")

        if event_callback:
            await event_callback(self.events[-1])

        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        kwargs = {
            "model": self.model,
            "messages": full_messages,
            "temperature": 0.2,
        }

        if self.tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        # Enable structured JSON output when requested and supported by the model.
        use_json = self.json_mode and not self.tools and supports_json_mode(self.model)
        if use_json:
            kwargs["response_format"] = {"type": "json_object"}

        self.emit_event("thinking", f"{self.agent_type.value} is analyzing...")
        if event_callback:
            await event_callback(self.events[-1])

        # Stream when there are no tools (streaming + tool calls is more complex);
        # tool-enabled agents use the standard blocking call.
        if not self.tools:
            response = await self._stream_completion(event_callback=event_callback, **kwargs)
            content = response.content
            if response.usage:
                self.total_input_tokens += response.usage.prompt_tokens
                self.total_output_tokens += response.usage.completion_tokens

            self.emit_event("completed", f"{self.agent_type.value} finished")
            if event_callback:
                await event_callback(self.events[-1])
            return {"content": content, "events": self.events}

        # Tool-enabled path (non-streaming)
        response = await self._call_openai_with_retry(**kwargs)
        message = response.choices[0].message

        # Track tokens
        if response.usage:
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens

        # Handle tool calls if present
        if message.tool_calls:
            tool_results = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                self.emit_event(
                    "action",
                    f"Executing: {function_name}",
                    data={"tool": function_name, "args": arguments},
                )
                if event_callback:
                    await event_callback(self.events[-1])

                result = await self.handle_tool_call(function_name, arguments)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": json.dumps(result),
                })

            # Get final response after tool calls
            follow_up_messages = full_messages + [
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            ] + tool_results

            final_response = await self._call_openai_with_retry(
                model=self.model,
                messages=follow_up_messages,
                temperature=0.2,
            )
            message = final_response.choices[0].message

            # Track follow-up tokens
            if final_response.usage:
                self.total_input_tokens += final_response.usage.prompt_tokens
                self.total_output_tokens += final_response.usage.completion_tokens

        self.emit_event("completed", f"{self.agent_type.value} finished")
        if event_callback:
            await event_callback(self.events[-1])

        return {"content": message.content, "events": self.events}

    async def handle_tool_call(self, function_name: str, arguments: dict) -> dict:
        """Override in subclasses to handle specific tool calls."""
        return {"error": f"Unknown tool: {function_name}"}