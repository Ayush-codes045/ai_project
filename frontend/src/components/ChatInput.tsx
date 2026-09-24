import { useState } from "react";
import { ModelInfo } from "../types";

interface ChatInputProps {
  onSubmit: (task: string, language: string, model: string) => void;
  onCancel: () => void;
  isLoading: boolean;
  models: ModelInfo[];
  defaultModel: string;
}

const LANGUAGES = [
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "go", label: "Go" },
  { value: "java", label: "Java" },
  { value: "rust", label: "Rust" },
];

export function ChatInput({ onSubmit, onCancel, isLoading, models, defaultModel }: ChatInputProps) {
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("python");
  const [model, setModel] = useState(defaultModel);

  // Keep the selected model in sync once the models list loads.
  const effectiveModel = models.some((m) => m.id === model) ? model : defaultModel;

  const selected = models.find((m) => m.id === effectiveModel);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSubmit(input.trim(), language, effectiveModel);
      setInput("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-3">
        <div className="flex-1 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe what you want to build... (e.g., 'Create a REST API for a todo app')"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            disabled={isLoading}
          />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-3 text-white text-sm focus:outline-none focus:border-blue-500 cursor-pointer"
            disabled={isLoading}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value}>
                {lang.label}
              </option>
            ))}
          </select>
          <select
            value={effectiveModel}
            onChange={(e) => setModel(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-3 text-white text-sm focus:outline-none focus:border-blue-500 cursor-pointer"
            disabled={isLoading || models.length === 0}
            title="Select the LLM model to power the agents"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.id}
                {m.is_default ? " (default)" : ""}
              </option>
            ))}
          </select>
        </div>
        {isLoading ? (
          <button
            type="button"
            onClick={onCancel}
            className="bg-red-600 hover:bg-red-700 px-5 py-3 rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="1" />
            </svg>
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-3 rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
            Build
          </button>
        )}
      </div>
      {selected && !isLoading && (
        <div className="mt-2 text-xs text-gray-500">
          {selected.id}: ${selected.input_per_1k}/1K in &middot; ${selected.output_per_1k}/1K out
        </div>
      )}
      {isLoading && (
        <div className="mt-3 flex items-center gap-2">
          <div className="flex gap-1">
            <span className="h-2 w-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="h-2 w-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="h-2 w-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
          <span className="text-xs text-gray-300">Agents are working on your task...</span>
        </div>
      )}
    </form>
  );
}