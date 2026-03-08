"use client";

import { useState, useRef, useEffect } from "react";
import { LEARNING_SUGGESTIONS, PLACEHOLDERS, TIMING, APP_NAME, APP_DISCLAIMER } from "@/lib/constants";

interface WelcomeScreenProps {
  onStartSession: (topic: string) => void;
  loading: boolean;
  userName?: string;
}

export default function WelcomeScreen({ onStartSession, loading, userName }: WelcomeScreenProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, TIMING.TEXTAREA_MAX_HEIGHT) + "px";
  }, [input]);

  function handleSubmit() {
    const text = input.trim();
    if (text && !loading) {
      onStartSession(text);
      setInput("");
    }
  }

  return (
    <div className="flex flex-col items-center justify-center h-full px-4">
      <h1 className="text-3xl md:text-4xl font-semibold text-foreground mb-2">
        {APP_NAME}
      </h1>
      <p className="text-zinc-500 mb-10">
        {userName ? `Hi ${userName}! ` : ""}What do you want to learn today?
      </p>

      <div className="w-full max-w-chat">
        <div className="relative bg-input-bg rounded-2xl border border-white/10
                        focus-within:border-white/20 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={PLACEHOLDERS.DEFAULT_INPUT}
            rows={1}
            disabled={loading}
            autoFocus
            className="w-full bg-transparent px-4 py-3.5 pr-12
                       text-[15px] text-foreground placeholder-zinc-500
                       focus:outline-none resize-none
                       disabled:opacity-50 overflow-y-auto"
            style={{ maxHeight: TIMING.TEXTAREA_MAX_HEIGHT }}
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            className="absolute right-2 bottom-2.5 p-2 rounded-lg
                       bg-foreground text-background
                       hover:bg-white transition-colors
                       disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>

        {loading && (
          <p className="text-sm text-zinc-500 text-center mt-3 animate-pulse">
            Preparing your lesson...
          </p>
        )}

        {!loading && (
          <div className="grid grid-cols-2 gap-2 mt-4">
            {LEARNING_SUGGESTIONS.map((s) => (
              <button
                key={s.label}
                onClick={() => onStartSession(s.label)}
                className="text-left px-4 py-3 rounded-xl border border-white/10 bg-transparent
                           hover:bg-white/5 transition-colors group"
              >
                <span className="text-sm text-foreground group-hover:text-white">{s.label}</span>
                <span className="block text-xs text-zinc-500 mt-0.5">{s.desc}</span>
              </button>
            ))}
          </div>
        )}

        <p className="text-xs text-zinc-500 text-center mt-4">
          {APP_DISCLAIMER}
        </p>
      </div>
    </div>
  );
}
