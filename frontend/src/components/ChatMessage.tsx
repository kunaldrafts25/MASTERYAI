"use client";

import { memo } from "react";
import MarkdownContent from "./MarkdownContent";
import { PHASE_LABELS } from "@/lib/constants";

interface ChatMessageProps {
  role: "professor" | "learner" | "system";
  content: string;
  action?: string;
  streaming?: boolean;
}

function PhaseBadge({ action }: { action: string }) {
  const phase = PHASE_LABELS[action];
  if (!phase) return null;
  return (
    <span className={`inline-block text-xs font-medium mb-1 ${phase.color}`}>
      {phase.label}
    </span>
  );
}

function ChatMessage({ role, content, action, streaming }: ChatMessageProps) {
  if (role === "learner") {
    return (
      <div className="group py-3 md:py-4">
        <div className="flex gap-3 md:gap-4 max-w-chat mx-auto px-3 md:px-4">
          <div className="w-7 h-7 rounded-full bg-input-bg flex items-center justify-center flex-shrink-0 mt-0.5 border border-white/10">
            <span className="text-xs font-medium text-foreground">U</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm md:text-[15px] text-foreground whitespace-pre-wrap leading-relaxed">
              {content}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (role === "system") {
    return (
      <div className="py-2">
        <div className="max-w-chat mx-auto flex gap-3 md:gap-4 px-3 md:px-4">
          <div className="w-7 flex-shrink-0" />
          <div className="flex-1">
            {action && <PhaseBadge action={action} />}
            <div className="text-sm text-zinc-400">
              <MarkdownContent content={content} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="group py-3 md:py-4">
      <div className="flex gap-3 md:gap-4 max-w-chat mx-auto px-3 md:px-4">
        <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-white text-xs font-bold">P</span>
        </div>
        <div className="flex-1 min-w-0">
          {action && <PhaseBadge action={action} />}
          <div className="text-sm md:text-[15px] text-foreground leading-relaxed">
            <MarkdownContent content={content} />
            {streaming && <span className="streaming-cursor" />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default memo(ChatMessage);
