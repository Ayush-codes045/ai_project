import { TaskMetrics } from "../types";

interface MetricsDashboardProps {
  metrics: TaskMetrics;
}

export function MetricsDashboard({ metrics }: MetricsDashboardProps) {
  return (
    <div className="space-y-4">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Total Tokens"
          value={metrics.total_tokens.toLocaleString()}
          icon="\ud83d\udcca"
          color="text-blue-400"
        />
        <StatCard
          label="Cost"
          value={`$${metrics.total_cost_usd.toFixed(4)}`}
          icon="\ud83d\udcb8"
          color="text-green-400"
        />
        <StatCard
          label="Time"
          value={`${metrics.time_taken_seconds}s`}
          icon="\u23f1\ufe0f"
          color="text-yellow-400"
        />
        <StatCard
          label="Lines of Code"
          value={metrics.lines_of_code.toString()}
          icon="\ud83d\udcc4"
          color="text-purple-400"
        />
      </div>

      {/* Secondary stats */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard
          label="Files Generated"
          value={metrics.files_generated.toString()}
          icon="\ud83d\udcc1"
          color="text-cyan-400"
        />
        <StatCard
          label="Review Iterations"
          value={metrics.review_iterations.toString()}
          icon="\ud83d\udd04"
          color="text-orange-400"
        />
        <StatCard
          label="Tests"
          value={`${metrics.tests_passed}/${metrics.tests_passed + metrics.tests_failed}`}
          icon="\u2705"
          color="text-emerald-400"
        />
      </div>

      {/* Token breakdown by agent */}
      {metrics.token_breakdown.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
            Token Usage by Agent
          </h4>
          <div className="space-y-2">
            {metrics.token_breakdown.map((usage, index) => {
              const total = usage.input_tokens + usage.output_tokens;
              const maxTokens = Math.max(
                ...metrics.token_breakdown.map((t) => t.input_tokens + t.output_tokens)
              );
              const percentage = maxTokens > 0 ? (total / maxTokens) * 100 : 0;

              return (
                <div key={index} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-16 capitalize">
                    {usage.agent}
                  </span>
                  <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-20 text-right">
                    {total.toLocaleString()} (${usage.cost_usd})
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon: string;
  color: string;
}) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm">{icon}</span>
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <span className={`text-lg font-bold ${color}`}>{value}</span>
    </div>
  );
}