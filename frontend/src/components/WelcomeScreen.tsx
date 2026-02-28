"use client";

import { useState } from "react";

interface WelcomeScreenProps {
  onStartSession: (topic: string) => void;
  loading: boolean;
  userName?: string;
}

export default function WelcomeScreen({ onStartSession, loading, userName }: WelcomeScreenProps) {
  const [input, setInput] = useState("");

  function handleSubmit() {
    const text = input.trim();
    if (text) {
      onStartSession(text);
      setInput("");
    }
  }

  const greeting = userName
    ? `Hello ${userName}! I'm your personal professor.`
    : "Hello! I'm your personal professor.";

  return (
    <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto px-4">
      {/* Professor avatar */}
      <div className="w-16 h-16 rounded-full bg-emerald-600 flex items-center justify-center mb-6">
        <span className="text-white text-2xl font-bold">P</span>
      </div>

      {/* Greeting */}
      <h1 className="text-2xl font-semibold text-white mb-2 text-center">
        {greeting}
      </h1>
      <p className="text-zinc-400 text-center mb-10 max-w-md">
        Tell me what you&apos;d like to learn and I&apos;ll build a personalized lesson just for you.
        Any topic, any level.
      </p>

      {/* Input */}
      <div className="w-full max-w-lg">
        <div className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit();
            }}
            placeholder="What do you want to learn?"
            disabled={loading}
            autoFocus
            className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3.5 pr-12
                       text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500
                       disabled:opacity-50 transition-colors"
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg
                       bg-emerald-600 hover:bg-emerald-500 text-white transition-colors
                       disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
        {loading && (
          <p className="text-xs text-zinc-500 text-center mt-3 animate-pulse">
            Preparing your lesson...
          </p>
        )}
      </div>
    </div>
  );
}
