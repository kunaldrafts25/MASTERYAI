"use client";

import { useRef, useEffect, useCallback } from "react";
import { CONFIDENCE, TIMING, PLACEHOLDERS, APP_DISCLAIMER } from "@/lib/constants";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  placeholder?: string;
  isSelfAssess: boolean;
  confidence: number;
  onConfidenceChange: (value: number) => void;
}

export default function ChatInput({
  value, onChange, onSubmit, disabled,
  placeholder = PLACEHOLDERS.DEFAULT_INPUT,
  isSelfAssess, confidence, onConfidenceChange,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, TIMING.TEXTAREA_MAX_HEIGHT) + "px";
  }, [value]);

  useEffect(() => {
    if (!isSelfAssess) {
      textareaRef.current?.focus();
    }
  }, [isSelfAssess]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSubmit();
      }
    },
    [onSubmit]
  );

  if (isSelfAssess) {
    return (
      <div className="border-t border-white/5">
        <div className="max-w-chat mx-auto px-3 md:px-4 py-4">
          <div className="bg-input-bg rounded-2xl p-4 md:p-5 space-y-4">
            <label className="text-sm text-zinc-400">
              How confident do you feel about this concept? ({confidence}/{CONFIDENCE.MAX})
            </label>
            <div className="flex items-center gap-4">
              <span className="text-2xl font-semibold text-foreground w-10 text-center">
                {confidence}
              </span>
              <input
                type="range"
                min={CONFIDENCE.MIN}
                max={CONFIDENCE.MAX}
                value={confidence}
                onChange={(e) => onConfidenceChange(Number(e.target.value))}
                className="flex-1 h-2 accent-accent cursor-pointer"
              />
            </div>
            <button
              onClick={onSubmit}
              disabled={disabled}
              className="w-full bg-accent text-white text-sm font-medium py-3 rounded-xl
                         hover:bg-accent-hover transition-colors disabled:opacity-50"
            >
              Submit Confidence
            </button>
          </div>
          <p className="text-xs text-zinc-500 text-center mt-2">
            {APP_DISCLAIMER}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-white/5">
      <div className="max-w-chat mx-auto px-3 md:px-4 py-3">
        <div className="relative bg-input-bg rounded-2xl border border-white/10
                        focus-within:border-white/20 transition-colors">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={disabled}
            className="w-full bg-transparent px-4 py-3.5 pr-12
                       text-[15px] text-foreground placeholder-zinc-500
                       focus:outline-none resize-none
                       disabled:opacity-50 overflow-y-auto"
            style={{ maxHeight: TIMING.TEXTAREA_MAX_HEIGHT }}
          />
          <button
            onClick={onSubmit}
            disabled={disabled || !value.trim()}
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
        <p className="text-xs text-zinc-500 text-center mt-2">
          {APP_DISCLAIMER}
        </p>
      </div>
    </div>
  );
}
