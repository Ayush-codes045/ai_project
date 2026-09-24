import { useState, useEffect, useRef, useCallback } from "react";
import { ChatInput } from "./components/ChatInput";
import { AgentTimeline } from "./components/AgentTimeline";
import { CodeViewer } from "./components/CodeViewer";
import { AgentPanel } from "./components/AgentPanel";
import { TestResults } from "./components/TestResults";
import { AgentConversation } from "./components/AgentConversation";
import { MetricsDashboard } from "./components/MetricsDashboard";
import { TaskHistory } from "./components/TaskHistory";
import { useWebSocket } from "./hooks/useWebSocket";
import { apiFetch } from "./lib/apiClient";
import { TaskData, HistoryItem, ModelInfo } from "./types";

type Tab = "timeline" | "conversation" | "metrics" | "history";

function App() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("timeline");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaultModel, setDefaultModel] = useState<string>("gpt-4o");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { events, streaming, isConnected, clearEvents } = useWebSocket(taskId);

  // Load history + available models on mount
  useEffect(() => {
    fetchHistory();
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const res = await apiFetch("/api/models");
      const data = await res.json();
      setModels(data.models || []);
      if (data.default) setDefaultModel(data.default);
    } catch {
      // Backend not available yet
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await apiFetch("/api/history");
      const data = await res.json();
      setHistory(data.history || []);
    } catch {
      // Backend not available yet
    }
  };

  const handleSubmit = async (task: string, language: string, model: string) => {
    setIsLoading(true);
    setError(null);
    setTaskData(null);
    clearEvents();
    setActiveTab("timeline");

    // Clear previous polling
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    try {
      const response = await apiFetch("/api/task", {
        method: "POST",
        body: JSON.stringify({ description: task, language, model }),
      });

      const data = await response.json();

      if (data.error) {
        setError(data.error);
        setIsLoading(false);
        return;
      }

      setTaskId(data.task_id);
      pollTask(data.task_id);
    } catch {
      setError("Failed to submit task. Is the backend running on port 8000?");
      setIsLoading(false);
    }
  };

  const pollTask = (id: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const response = await apiFetch(`/api/task/${id}`);
        const data = await response.json();

        if (data.status === "completed") {
          setTaskData(data.data);
          setIsLoading(false);
          setActiveTab("conversation");
          fetchHistory();
          if (pollRef.current) clearInterval(pollRef.current);
        } else if (data.status === "failed") {
          setError(data.error || "Task failed");
          setIsLoading(false);
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // Continue polling
      }
    }, 2000);
  };

  const handleCancel = useCallback(async () => {
    if (taskId) {
      try {
        await apiFetch(`/api/task/${taskId}/cancel`, { method: "POST" });
      } catch {
        // Ignore cancel errors
      }

      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      setIsLoading(false);
      setError("Task cancelled by user");
    }
  }, [taskId]);

  const handleHistorySelect = async (selectedTaskId: string) => {
    try {
      const res = await apiFetch(`/api/history/${selectedTaskId}`);
      const data = await res.json();
      if (data.data) {
        setTaskData(data.data);
        setTaskId(selectedTaskId);
        setActiveTab("conversation");
        setError(null);
      }
    } catch {
      setError("Failed to load task from history");
    }
  };

  const handleDownload = () => {
    if (taskId) {
      window.open(`/api/task/${taskId}/download`, "_blank");
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span className="text-xl">\ud83e\udd16</span>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                AI Software Engineer
              </h1>
              <p className="text-xs text-gray-500">
                Multi-agent system powered by GPT-4
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {taskData && (
              <button
                onClick={handleDownload}
                className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <span>\ud83d\udce5</span> Download ZIP
              </button>
            )}
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  isConnected ? "bg-green-500 animate-pulse" : "bg-gray-600"
                }`}
              />
              <span className="text-xs text-gray-500">
                {isConnected ? "Live" : "Offline"}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        {/* Input */}
        <div className="mb-6">
          <ChatInput
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            isLoading={isLoading}
            models={models}
            defaultModel={defaultModel}
          />
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center gap-2">
            <span>\u26a0\ufe0f</span> {error}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-6 bg-gray-900 rounded-lg p-1 w-fit">
          {(
            [
              { id: "timeline", label: "Activity", icon: "\u26a1" },
              { id: "conversation", label: "Conversation", icon: "\ud83d\udcac" },
              { id: "metrics", label: "Metrics", icon: "\ud83d\udcca" },
              { id: "history", label: "History", icon: "\ud83d\udcda" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm rounded-md transition-all ${
                activeTab === tab.id
                  ? "bg-gray-800 text-white shadow-sm"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <span className="mr-1.5">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel */}
          <div className="lg:col-span-1">
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              {activeTab === "timeline" && (
                <AgentTimeline events={events} streaming={streaming} />
              )}

              {activeTab === "conversation" && (
                <AgentConversation messages={taskData?.conversation || []} />
              )}
              {activeTab === "metrics" && taskData?.metrics && (
                <MetricsDashboard metrics={taskData.metrics} />
              )}
              {activeTab === "metrics" && !taskData?.metrics && (
                <div className="text-gray-500 text-center py-8 text-sm">
                  Complete a task to see metrics...
                </div>
              )}
              {activeTab === "history" && (
                <TaskHistory history={history} onSelect={handleHistorySelect} />
              )}
            </div>

            {/* Plan & Review (always visible when data exists) */}
            {taskData && activeTab !== "history" && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 mt-4">
                <AgentPanel
                  plan={taskData.plan}
                  reviewIssues={taskData.review_issues}
                />
              </div>
            )}
          </div>

          {/* Right: Code & Tests */}
          <div className="lg:col-span-2 space-y-4">
            {/* Code Viewer */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 min-h-[400px]">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                  Generated Code
                </h2>
                {taskData && (
                  <span className="text-xs text-gray-500">
                    {taskData.code_files.length} files |{" "}
                    {taskData.metrics?.lines_of_code || 0} lines
                  </span>
                )}
              </div>
              <CodeViewer files={taskData?.code_files || []} />
            </div>

            {/* Test Results */}
            {taskData?.test_results && taskData.test_results.length > 0 && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <TestResults results={taskData.test_results} />
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-12 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-gray-600">
          <span>Built with FastAPI + React + GPT-4</span>
          <span>Multi-Agent Orchestration System v1.0</span>
        </div>
      </footer>
    </div>
  );
}

export default App;