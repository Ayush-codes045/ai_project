import { AgentEvent } from "../types";
import { StreamingState } from "../hooks/useWebSocket";

interface AgentTimelineProps {
  events: AgentEvent[];
  streaming?: StreamingState | null;
}

const AGENT_COLORS: Record<string, string> = {
  planner: "text-purple-400 bg-purple-400/10 border-purple-400/30",
  coder: "text-green-400 bg-green-400/10 border-green-400/30",
  reviewer: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  tester: "text-cyan-400 bg-cyan-400/10 border-cyan-400/30",
  orchestrator: "text-blue-400 bg-blue-400/10 border-blue-400/30",
};

const AGENT_ICONS: Record<string, string> = {
  planner: "\ud83e\uddde",
  coder: "\ud83d\udcbb",
  reviewer: "\ud83d\udd0d",
  tester: "\ud83e\uddea",
  orchestrator: "\ud83c\udfaf",
};

const EVENT_ICONS: Record<string, string> = {
  started: "\u25b6\ufe0f",
  thinking: "\ud83d\udcad",
  action: "\u26a1",
  completed: "\u2705",
  error: "\u274c",
  status: "\ud83d\udce1",
};

export function AgentTimeline({ events, streaming }: AgentTimelineProps) {
  if (events.length === 0 && !streaming) {
    return (
      <div className="text-gray-500 text-center py-8">
        Submit a task to see agents working...
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto">
      {events.map((event, index) => (
        <div
          key={index}
          className={`flex items-start gap-3 p-3 rounded-lg border animate-slide-in ${AGENT_COLORS[event.agent] || "text-gray-400 bg-gray-800/50 border-gray-700"}`}
        >
          <span className="text-lg flex-shrink-0">
            {AGENT_ICONS[event.agent] || "\ud83e\udd16"}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium capitalize text-sm">
                {event.agent}
              </span>
              <span className="text-xs opacity-60">
                {EVENT_ICONS[event.event_type]} {event.event_type}
              </span>
            </div>
            <p className="text-sm opacity-80 mt-0.5 truncate">
              {event.message}
            </p>
            {typeof event.data?.tool === "string" && (
              <code className="text-xs opacity-60 mt-1 block">
                Tool: {event.data.tool}
              </code>
            )}
          </div>
          {event.event_type === "thinking" && (
            <span className="animate-pulse-dot text-lg">\u2022</span>
          )}
        </div>
      ))}

      {/* Live token stream from the currently active agent */}
      {streaming && streaming.content && (
        <div
          className={`flex items-start gap-3 p-3 rounded-lg border ${AGENT_COLORS[streaming.agent] || "text-gray-400 bg-gray-800/50 border-gray-700"}`}
        >
          <span className="text-lg flex-shrink-0">
            {AGENT_ICONS[streaming.agent] || "\ud83e\udd16"}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium capitalize text-sm">
                {streaming.agent}
              </span>
              <span className="text-xs opacity-60">\u270d\ufe0f streaming</span>
            </div>
            <pre className="text-xs opacity-80 mt-1 whitespace-pre-wrap break-words font-mono max-h-40 overflow-y-auto">
              {streaming.content}
              <span className="animate-pulse-dot">\u258b</span>
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}