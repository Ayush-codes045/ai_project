import { TestResult } from "../types";

interface TestResultsProps {
  results: TestResult[];
}

export function TestResults({ results }: TestResultsProps) {
  if (results.length === 0) return null;

  const passed = results.filter((r) => r.passed).length;
  const failed = results.filter((r) => !r.passed).length;

  return (
    <div>
      <h3 className="text-sm font-semibold text-cyan-400 mb-2 flex items-center gap-2">
        <span>\ud83e\uddea</span> Test Results
        <span className="text-xs font-normal text-gray-400">
          | {passed} passed, {failed} failed
        </span>
      </h3>

      {/* Summary bar */}
      <div className="flex h-2 rounded-full overflow-hidden mb-3 bg-gray-800">
        {passed > 0 && (
          <div
            className="bg-green-500"
            style={{ width: `${(passed / results.length) * 100}%` }}
          />
        )}
        {failed > 0 && (
          <div
            className="bg-red-500"
            style={{ width: `${(failed / results.length) * 100}%` }}
          />
        )}
      </div>

      {/* Individual results */}
      <div className="space-y-1.5">
        {results.map((result, index) => (
          <div
            key={index}
            className={`flex items-center gap-2 text-sm p-2 rounded ${
              result.passed ? "bg-green-500/5" : "bg-red-500/5"
            }`}
          >
            <span>{result.passed ? "\u2705" : "\u274c"}</span>
            <span className="text-gray-300 font-mono text-xs">
              {result.test_name}
            </span>
            {result.error && (
              <span className="text-red-400 text-xs ml-auto truncate max-w-[200px]">
                {result.error}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}