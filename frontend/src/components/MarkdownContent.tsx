"use client";
import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="px-2.5 py-1 rounded text-xs text-zinc-300 hover:text-white transition-colors"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

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
              <div className="relative group my-3 rounded-lg overflow-hidden bg-[#1e1e1e]">
                <div className="flex items-center justify-between px-4 py-2 bg-[#2d2d2d] border-b border-white/5">
                  <span className="text-xs text-zinc-400">{match[1]}</span>
                  <CopyButton text={code} />
                </div>
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    borderRadius: 0,
                    fontSize: "0.85rem",
                    padding: "1rem",
                    background: "transparent",
                  }}
                >
                  {code}
                </SyntaxHighlighter>
              </div>
            );
          }
          return (
            <code className="bg-[#2f2f2f] px-1.5 py-0.5 rounded text-sm text-[#ececec]" {...props}>
              {children}
            </code>
          );
        },
        p({ children }) {
          return <p className="mb-3 leading-relaxed">{children}</p>;
        },
        ul({ children }) {
          return <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>;
        },
        h1({ children }) {
          return <h1 className="text-xl font-semibold mb-3 mt-4">{children}</h1>;
        },
        h2({ children }) {
          return <h2 className="text-lg font-semibold mb-2 mt-4">{children}</h2>;
        },
        h3({ children }) {
          return <h3 className="text-base font-semibold mb-1 mt-3">{children}</h3>;
        },
        blockquote({ children }) {
          return (
            <blockquote className="border-l-2 border-zinc-600 pl-4 italic text-zinc-400 mb-3 ml-0">
              {children}
            </blockquote>
          );
        },
        strong({ children }) {
          return <strong className="font-semibold text-white">{children}</strong>;
        },
        hr() {
          return <hr className="border-white/10 my-4" />;
        },
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
