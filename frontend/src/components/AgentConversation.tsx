import { AgentMessage } from "../types";

interface AgentConversationProps {
  messages: AgentMessage[];
}

const AGENT_STYLES: Record<string, { color: string; bg: string; icon: string }> = {
  orchestrator: { color: "text-blue-400", bg: "bg-blue-400/10", icon: "\ud83c\udfaf" },
  planner: { color: "text-purple-400", bg: "bg-purple-400/10", icon: "\ud83d\udcdd" },
  coder: { color: "text-green-400", bg: "bg-green-400/10", icon: "\ud83d\udcbb" },
  reviewer: { color: "text-yellow-400", bg: "bg-yellow-400/10", icon: "\ud83d\udd0d" },
  tester: { color: "text-cyan-400", bg: "bg-cyan-400/10", icon: "\ud83e\uddea" },
};

export function AgentConversation({ messages }: AgentConversationProps) {
  if (messages.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8 text-sm">
        Agent conversations will appear here as they collaborate...
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
      {messages.map((msg, index) => {
        const style = AGENT_STYLES[msg.agent] || AGENT_STYLES.orchestrator;
        const isHandoff = msg.message_type === "handoff";

        return (
          <div key={index} className="animate-slide-in">
            {isHandoff && (
              <div className="flex items-center gap-2 mb-1 ml-8">
                <div className="h-px flex-1 bg-gray-700" />
                <span className="text-xs text-gray-400">
                  {msg.agent} - {msg.to_agent}
                </span>
                <div className="h-px flex-1 bg-gray-700" />
              </div>
            )}
            <div className={`flex items-start gap-3 p-3 rounded-lg ${style.bg}`}>
              <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gray-800 text-sm">
                {style.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-semibold uppercase ${style.color}`}>
                    {msg.agent}
                  </span>
                  {msg.to_agent && (
                    <>
                      <span className="text-gray-600 text-xs">-</span>
                      <span className="text-xs text-gray-400 uppercase">
                        {msg.to_agent}
                      </span>
                    </>
                  )}
                  {msg.timestamp && (
                    <span className="text-xs text-gray-600 ml-auto">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-300 leading-relaxed">
                  {msg.message.length > 300
                    ? msg.message.substring(0, 300) + "..."
                    : msg.message}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}