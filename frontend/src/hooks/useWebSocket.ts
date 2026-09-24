import { useEffect, useRef, useState, useCallback } from "react";
import { AgentEvent, AgentType } from "../types";

export interface StreamingState {
  agent: AgentType;
  content: string;
}

export function useWebSocket(taskId: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [streaming, setStreaming] = useState<StreamingState | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!taskId) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${taskId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const agentEvent: AgentEvent = JSON.parse(event.data);

      // Token events are streamed live: accumulate them into `streaming`
      // rather than appending each token to the timeline.
      if (agentEvent.event_type === "token") {
        setStreaming((prev) => {
          if (prev && prev.agent === agentEvent.agent) {
            return { agent: agentEvent.agent, content: prev.content + agentEvent.message };
          }
          return { agent: agentEvent.agent, content: agentEvent.message };
        });
        return;
      }

      // A non-token event means the current stream (if any) is finished.
      if (agentEvent.event_type === "completed" || agentEvent.event_type === "started") {
        setStreaming(null);
      }
      setEvents((prev) => [...prev, agentEvent]);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = () => {
      setIsConnected(false);
    };
  }, [taskId]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setStreaming(null);
  }, []);

  return { events, streaming, isConnected, clearEvents };
}