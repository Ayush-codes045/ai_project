import { HistoryItem } from "../types";

interface TaskHistoryProps {
  history: HistoryItem[];
  onSelect: (taskId: string) => void;
}

export function TaskHistory({ history, onSelect }: TaskHistoryProps) {
  if (history.length === 0) {
    return (
      <div className="text-gray-500 text-center py-4 text-sm">
        No previous tasks yet.
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-60 overflow-y-auto">
      {history.map((item) => (
        <button
          key={item.task_id}
          onClick={() => onSelect(item.task_id)}
          className="w-full text-left p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-blue-500/50 hover:bg-gray-800 transition-all"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-200 truncate flex-1">
              {item.description}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ml-2 ${
                item.status === "completed"
                  ? "bg-green-500/20 text-green-400"
                  : "bg-red-500/20 text-red-400"
              }`}
            >
              {item.status}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span>{item.files_count} files</span>
            <span>{item.total_tokens.toLocaleString()} tokens</span>
            <span>${item.cost_usd.toFixed(4)}</span>
            <span className="ml-auto">
              {new Date(item.created_at).toLocaleDateString()}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}