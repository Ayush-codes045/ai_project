import { PlanStep, ReviewIssue } from "../types";

interface AgentPanelProps {
  plan: PlanStep[];
  reviewIssues: ReviewIssue[];
}

export function AgentPanel({ plan, reviewIssues }: AgentPanelProps) {
  return (
    <div className="space-y-4">
      {/* Plan section */}
      {plan.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-purple-400 mb-2 flex items-center gap-2">
            <span>\ud83d\udcdd</span> Plan
          </h3>
          <div className="space-y-1.5">
            {plan.map((step) => (
              <div
                key={step.step_number}
                className="flex items-start gap-2 text-sm p-2 rounded bg-gray-800/50"
              >
                <span className="text-purple-400 font-mono text-xs mt-0.5">
                  {step.step_number}.
                </span>
                <div>
                  <span className="text-gray-200">{step.title}</span>
                  {step.file_path && (
                    <code className="text-xs text-gray-500 block mt-0.5">
                      {step.file_path}
                    </code>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review issues section */}
      {reviewIssues.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-yellow-400 mb-2 flex items-center gap-2">
            <span>\ud83d\udd0d</span> Review Issues
          </h3>
          <div className="space-y-1.5">
            {reviewIssues.map((issue, index) => (
              <div
                key={index}
                className={`text-sm p-2 rounded border-l-2 ${
                  issue.severity === "critical"
                    ? "border-red-500 bg-red-500/5"
                    : issue.severity === "warning"
                    ? "border-yellow-500 bg-yellow-500/5"
                    : "border-blue-500 bg-blue-500/5"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-medium uppercase ${
                      issue.severity === "critical"
                        ? "text-red-400"
                        : issue.severity === "warning"
                        ? "text-yellow-400"
                        : "text-blue-400"
                    }`}
                  >
                    {issue.severity}
                  </span>
                  <span className="text-gray-500 text-xs">• {issue.file_path}</span>
                </div>
                <p className="text-gray-300 mt-1">{issue.message}</p>
                {issue.suggestion && (
                  <p className="text-gray-500 text-xs mt-1">
                    Fix: {issue.suggestion}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}