import { useState, useEffect } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { CodeFile } from "../types";

interface CodeViewerProps {
  files: CodeFile[];
}

export function CodeViewer({ files }: CodeViewerProps) {
  const [activeFile, setActiveFile] = useState(0);

  // Reset tab when a new set of files arrives to avoid an out-of-bounds index.
  useEffect(() => {
    setActiveFile(0);
  }, [files]);

  if (files.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        Generated code will appear here...
      </div>
    );
  }

  const currentFile = files[activeFile];

  return (
    <div className="flex flex-col h-full">
      {/* File tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-gray-700 pb-1 mb-2">
        {files.map((file, index) => (
          <button
            key={file.path}
            onClick={() => setActiveFile(index)}
            className={`px-3 py-1.5 text-xs rounded-t font-mono whitespace-nowrap transition-colors ${
              index === activeFile
                ? "bg-gray-800 text-white border border-gray-700 border-b-0"
                : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            {file.path}
          </button>
        ))}
      </div>

      {/* Code content */}
      <div className="flex-1 overflow-auto rounded-lg">
        <SyntaxHighlighter
          language={currentFile.language}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            borderRadius: "0.5rem",
            fontSize: "0.8rem",
          }}
          showLineNumbers
        >
          {currentFile.content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}