"use client";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function MarkdownContent({ content }: { content: string }) {
  const text = typeof content === "string" ? content : (content ? JSON.stringify(content, null, 2) : "");
  return (
    <ReactMarkdown
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const code = String(children).replace(/\n$/, "");
          if (match) {
            return (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                customStyle={{ margin: "0.5rem 0", borderRadius: "6px", fontSize: "0.85rem" }}
              >
                {code}
              </SyntaxHighlighter>
            );
          }
          return (
            <code className="bg-zinc-800 px-1.5 py-0.5 rounded text-sm text-green-400" {...props}>
              {children}
            </code>
          );
        },
        p({ children }) {
          return <p className="mb-2 leading-relaxed">{children}</p>;
        },
        ul({ children }) {
          return <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>;
        },
        h1({ children }) {
          return <h1 className="text-xl font-bold mb-2 mt-3">{children}</h1>;
        },
        h2({ children }) {
          return <h2 className="text-lg font-bold mb-2 mt-3">{children}</h2>;
        },
        h3({ children }) {
          return <h3 className="text-base font-semibold mb-1 mt-2">{children}</h3>;
        },
        blockquote({ children }) {
          return <blockquote className="border-l-2 border-zinc-600 pl-3 italic text-zinc-400 mb-2">{children}</blockquote>;
        },
        strong({ children }) {
          return <strong className="font-semibold text-white">{children}</strong>;
        },
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
